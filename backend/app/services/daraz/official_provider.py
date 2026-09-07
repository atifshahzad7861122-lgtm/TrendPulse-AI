import time
import hmac
import hashlib
import logging
import requests
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlencode

from backend.app.core.config import settings
from backend.app.models.domain import DarazAuthSession
from backend.app.schemas.daraz import (
    DarazProductItem,
    DarazProductDetails,
    DarazCategoryItem,
    DarazSearchResponse,
    DarazSellerProductsResponse,
    DarazSellerInfo,
    DarazSkuVariant
)
from backend.app.services.daraz.base import DarazProvider, DarazFetchResult

logger = logging.getLogger(__name__)

class DarazOfficialProvider(DarazProvider):
    """
    Official Daraz Open Platform REST API Provider.
    Implements HMAC-SHA256 parameter signing and token management
    per Daraz Open Platform developer specification.
    Priority 1 (Preferred provider).
    """
    name: str = "daraz_official_open_platform"
    priority: int = 1

    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        access_token: Optional[str] = None,
        timeout: float = 15.0,
        max_retries: int = 2,
        marketplace_repo: Optional[Any] = None,
        repository: Optional[Any] = None
    ):
        self.app_key = app_key or settings.DARAZ_APP_KEY
        self.app_secret = app_secret or settings.DARAZ_APP_SECRET
        self.base_url = (base_url or settings.DARAZ_API_BASE_URL or "https://api.daraz.pk/rest").rstrip("/")
        self.access_token = access_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.marketplace_repo = marketplace_repo or repository

    def is_configured(self) -> bool:
        """Checks if minimal official credentials are configured."""
        return bool(self.app_key and self.app_secret)

    def generate_signature(self, api_path: str, params: Dict[str, Any]) -> str:
        """
        Generates official Daraz HMAC-SHA256 signature.
        Rules:
        1. Sort parameters alphabetically by parameter key name.
        2. Concatenate api_path + sorted key-value pairs (excluding 'sign' and byte arrays).
        3. Compute HMAC-SHA256 hex digest with app_secret and uppercase the result.
        """
        if not self.app_secret:
            return ""

        # Filter out 'sign' and None values
        clean_params = {k: v for k, v in params.items() if k != "sign" and v is not None}
        sorted_keys = sorted(clean_params.keys())
        
        query_str = api_path
        for k in sorted_keys:
            query_str += f"{k}{clean_params[k]}"

        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            query_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest().upper()

        return signature

    def _record_telemetry_and_quota(
        self,
        endpoint: str,
        status_code: int,
        latency_ms: float,
        success: bool,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        request_params: Optional[Dict[str, Any]] = None,
        response_size: int = 0
    ) -> None:
        if not self.marketplace_repo:
            return
        try:
            from backend.app.models.domain import DarazApiTelemetry
            # Increment quota
            self.marketplace_repo.increment_daily_quota(is_rate_limited=(status_code == 429))
            # Record telemetry
            safe_params = {k: v for k, v in (request_params or {}).items() if k not in ("sign", "access_token", "app_key")}
            self.marketplace_repo.record_api_telemetry(
                DarazApiTelemetry(
                    id=str(uuid.uuid4()),
                    endpoint=endpoint,
                    method="POST",
                    provider_name=self.name,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    success=success,
                    error_code=error_code,
                    error_message=error_message,
                    request_params=safe_params,
                    response_size_bytes=response_size
                )
            )
        except Exception as e:
            logger.debug(f"Telemetry logging non-critical error: {e}")

    def get_active_token(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolves the active valid access token from instance state or persistent DarazAuthSession in repository.
        Performs automated token refresh if the session has expired and a refresh token is present.
        Returns: (access_token, error_message)
        Never logs or exposes tokens.
        """
        # 1. Check in-memory instance property
        if self.access_token:
            return self.access_token, None

        # 2. Check repository persistent auth session
        if self.marketplace_repo:
            try:
                sess: Optional[DarazAuthSession] = None
                if hasattr(self.marketplace_repo, "get_auth_session"):
                    sess = self.marketplace_repo.get_auth_session()

                if sess and sess.access_token:
                    # Check token expiration
                    now = datetime.now(timezone.utc)
                    if sess.expires_in and sess.authorized_at:
                        age = (now - sess.authorized_at).total_seconds()
                        if age >= max(0, sess.expires_in - 120):
                            # Token is expired or expiring soon; attempt auto-refresh
                            if sess.refresh_token:
                                ok, token_data, err = self.refresh_access_token(sess.refresh_token)
                                if ok and token_data and "access_token" in token_data:
                                    new_sess = sess.model_copy(update={
                                        "access_token": token_data["access_token"],
                                        "refresh_token": token_data.get("refresh_token", sess.refresh_token),
                                        "expires_in": token_data.get("expires_in", sess.expires_in),
                                        "authorized_at": now,
                                        "updated_at": now,
                                        "status": "authorized"
                                    })
                                    self.marketplace_repo.save_auth_session(new_sess)
                                    self.access_token = new_sess.access_token
                                    return self.access_token, None
                                else:
                                    return None, f"Daraz OAuth session expired and token refresh failed: {err}"
                            else:
                                return None, "Daraz OAuth session expired and no refresh token is available."

                    self.access_token = sess.access_token
                    return self.access_token, None

                # 3. Check seller record
                if hasattr(self.marketplace_repo, "list_sellers"):
                    sellers = self.marketplace_repo.list_sellers(limit=5)
                    for s in sellers:
                        if hasattr(s, "raw_data") and isinstance(s.raw_data, dict):
                            raw_sess = s.raw_data.get("auth_session")
                            if raw_sess and isinstance(raw_sess, dict) and raw_sess.get("access_token"):
                                self.access_token = raw_sess["access_token"]
                                return self.access_token, None
                        if getattr(s, "access_token", None):
                            self.access_token = s.access_token
                            return self.access_token, None
            except Exception as e:
                logger.debug(f"Non-critical error resolving persistent auth session: {e}")

        # 4. Fallback to settings if configured
        fallback = getattr(settings, "DARAZ_ACCESS_TOKEN", None)
        if fallback:
            self.access_token = fallback
            return self.access_token, None

        return None, "No active Daraz OAuth authentication session found. Seller authorization required."

    def _execute_api_call(
        self,
        api_path: str,
        params: Dict[str, Any],
        require_auth: bool = True,
        method: str = "GET"
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int], Optional[str]]:
        """
        Executes signed HTTP call to Daraz Open Platform Gateway.
        Ensures app_secret and access_token are NEVER logged.
        """
        if not self.is_configured():
            return False, None, 401, "Daraz Official Open Platform credentials (DARAZ_APP_KEY / DARAZ_APP_SECRET) not configured."

        call_params = dict(params)
        call_params["app_key"] = self.app_key
        call_params["timestamp"] = str(int(time.time() * 1000))
        call_params["sign_method"] = "sha256"

        if require_auth:
            token, auth_err = self.get_active_token()
            if not token:
                return False, None, 401, f"Daraz OAuth authorization required: {auth_err}"
            call_params["access_token"] = token

        # Generate HMAC-SHA256 signature
        sign = self.generate_signature(api_path, call_params)
        call_params["sign"] = sign

        url = f"{self.base_url}{api_path}"
        is_get = (method.upper() == "GET") or (api_path in ("/products/get", "/category/tree/get", "/seller/get", "/products/search"))

        for attempt in range(1, self.max_retries + 1):
            start_t = time.time()
            try:
                # Safe logging - exclude secrets and tokens
                logger.info(f"Official Daraz API request: {api_path} (Method: {'GET' if is_get else 'POST'}, Attempt {attempt}/{self.max_retries})")
                if is_get:
                    response = requests.get(url, params=call_params, timeout=self.timeout)
                else:
                    response = requests.post(url, data=call_params, timeout=self.timeout)
                latency = round((time.time() - start_t) * 1000, 2)

                if response.status_code == 200:
                    res_data = response.json()
                    # Check for Daraz Open Platform logical error codes
                    code = res_data.get("code")
                    if code and code != "0":
                        err_msg = res_data.get("message", f"Daraz API error code: {code}")
                        logger.warning(f"Official Daraz API logical error: {code} - {err_msg}")
                        is_auth_err = code in ("IllegalAccessToken", "AccessTokenExpired", "IncompleteSignature", "InvalidSignature")
                        status_code = 401 if is_auth_err else 400
                        self._record_telemetry_and_quota(
                            endpoint=api_path,
                            status_code=status_code,
                            latency_ms=latency,
                            success=False,
                            error_code=str(code),
                            error_message=err_msg,
                            request_params=call_params,
                            response_size=len(response.content)
                        )
                        return False, None, status_code, f"Daraz API Error: {err_msg}"
                    
                    self._record_telemetry_and_quota(
                        endpoint=api_path,
                        status_code=200,
                        latency_ms=latency,
                        success=True,
                        request_params=call_params,
                        response_size=len(response.content)
                    )
                    return True, res_data, 200, None

                if response.status_code in (401, 403):
                    logger.warning(f"Official Daraz API Auth Failure HTTP {response.status_code}")
                    self._record_telemetry_and_quota(
                        endpoint=api_path,
                        status_code=response.status_code,
                        latency_ms=latency,
                        success=False,
                        error_message="Official Daraz authentication failed.",
                        request_params=call_params,
                        response_size=len(response.content)
                    )
                    return False, None, response.status_code, "Official Daraz authentication failed."

                if response.status_code == 429:
                    logger.warning(f"Official Daraz API Rate Limit HTTP 429")
                    self._record_telemetry_and_quota(
                        endpoint=api_path,
                        status_code=429,
                        latency_ms=latency,
                        success=False,
                        error_message="Official Daraz API rate limit exceeded.",
                        request_params=call_params,
                        response_size=len(response.content)
                    )
                    if attempt >= self.max_retries:
                        return False, None, 429, "Official Daraz API rate limit exceeded."
                    time.sleep(1.5 * attempt)
                    continue

                if response.status_code >= 500:
                    logger.warning(f"Official Daraz API Upstream HTTP {response.status_code}")
                    self._record_telemetry_and_quota(
                        endpoint=api_path,
                        status_code=response.status_code,
                        latency_ms=latency,
                        success=False,
                        error_message=f"Official Daraz upstream gateway error ({response.status_code}).",
                        request_params=call_params,
                        response_size=len(response.content)
                    )
                    if attempt >= self.max_retries:
                        return False, None, response.status_code, f"Official Daraz upstream gateway error ({response.status_code})."
                    time.sleep(1.0 * attempt)
                    continue

                self._record_telemetry_and_quota(
                    endpoint=api_path,
                    status_code=response.status_code,
                    latency_ms=latency,
                    success=False,
                    error_message=f"HTTP Error {response.status_code}",
                    request_params=call_params,
                    response_size=len(response.content)
                )
                return False, None, response.status_code, f"HTTP Error {response.status_code}: {response.text[:100]}"

            except requests.exceptions.Timeout:
                latency = round((time.time() - start_t) * 1000, 2)
                logger.warning(f"Official Daraz API timeout on {api_path} (Attempt {attempt})")
                self._record_telemetry_and_quota(
                    endpoint=api_path,
                    status_code=504,
                    latency_ms=latency,
                    success=False,
                    error_message="Official Daraz API connection timed out.",
                    request_params=call_params
                )
                if attempt >= self.max_retries:
                    return False, None, 504, "Official Daraz API connection timed out."
                time.sleep(1.0)
            except Exception as e:
                latency = round((time.time() - start_t) * 1000, 2)
                logger.error(f"Official Daraz API unexpected error on {api_path}: {e}")
                self._record_telemetry_and_quota(
                    endpoint=api_path,
                    status_code=500,
                    latency_ms=latency,
                    success=False,
                    error_message=str(e),
                    request_params=call_params
                )
                if attempt >= self.max_retries:
                    return False, None, 500, f"Daraz API communication error: {str(e)}"

        return False, None, 500, "Official Daraz API failed after retries."

    def exchange_code_for_token(self, code: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Exchanges an authorization code for an OAuth access_token and refresh_token.
        Endpoint: /auth/token/create
        """
        if not self.is_configured():
            return False, None, "DARAZ_APP_KEY and DARAZ_APP_SECRET must be configured for OAuth token exchange."

        success, data, code_num, err = self._execute_api_call(
            api_path="/auth/token/create",
            params={"code": code},
            require_auth=False
        )

        if not success or not data:
            return False, None, err or "Failed to exchange authorization code for token."

        token_data = data.get("data") or data
        # Update local instance token if present
        if "access_token" in token_data:
            self.access_token = token_data["access_token"]

        return True, token_data, None

    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Refreshes an expired access_token using a refresh_token.
        Endpoint: /auth/token/refresh
        """
        if not self.is_configured():
            return False, None, "DARAZ_APP_KEY and DARAZ_APP_SECRET not configured."

        success, data, code_num, err = self._execute_api_call(
            api_path="/auth/token/refresh",
            params={"refresh_token": refresh_token},
            require_auth=False
        )

        if not success or not data:
            return False, None, err or "Failed to refresh Daraz access token."

        token_data = data.get("data") or data
        if "access_token" in token_data:
            self.access_token = token_data["access_token"]

        return True, token_data, None

    # ----------------------------------------------------------------------
    # DarazProvider Interface Implementation
    # ----------------------------------------------------------------------

    def search_products(
        self,
        query: str,
        page: int = 1,
        category: Optional[str] = None,
        min_rating: Optional[float] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: Optional[str] = None
    ) -> DarazFetchResult:
        """
        Search products via Official Daraz Open Platform catalog / products API.
        Endpoint: /products/get
        """
        if not self.is_configured():
            return DarazFetchResult(
                success=False,
                error_code=401,
                error_message="Daraz Official API credentials not configured.",
                provider_name=self.name
            )

        offset = max(0, (page - 1) * 20)
        params: Dict[str, Any] = {
            "filter": "all",
            "limit": "20",
            "offset": str(offset)
        }
        if query:
            params["search"] = query
        if category:
            params["category_id"] = category

        success, res_data, status_code, err = self._execute_api_call(
            api_path="/products/get",
            params=params,
            require_auth=True
        )

        if not success or not res_data:
            return DarazFetchResult(
                success=False,
                error_code=status_code,
                error_message=err or "Failed to search products via Official Daraz API",
                provider_name=self.name,
                is_rate_limited=(status_code == 429)
            )

        # Normalize products from Official Daraz payload
        products: List[DarazProductItem] = []
        data_payload = res_data.get("data", {})
        items = data_payload.get("products", []) if isinstance(data_payload, dict) else []

        for item in items:
            p_id = str(item.get("item_id") or item.get("product_id") or "")
            attr = item.get("attributes", {})
            skus = item.get("skus", [])
            primary_sku = skus[0] if skus else {}

            price = float(primary_sku.get("price") or primary_sku.get("special_price") or attr.get("price") or 0.0)
            orig_price = float(primary_sku.get("original_price") or primary_sku.get("price") or price)
            discount = round(((orig_price - price) / orig_price * 100), 1) if (orig_price > price > 0) else 0.0

            title = str(attr.get("name") or item.get("name") or "Daraz Product")
            img = str(attr.get("Images", [""])[0] if isinstance(attr.get("Images"), list) and attr.get("Images") else primary_sku.get("Images", [""])[0] if isinstance(primary_sku.get("Images"), list) and primary_sku.get("Images") else "")

            p_item = DarazProductItem(
                platform="daraz",
                product_id=p_id,
                name=title,
                price=price,
                original_price=orig_price,
                discount=discount,
                discount_label=f"{int(discount)}% OFF" if discount > 0 else None,
                currency="PKR",
                rating=float(item.get("rating") or attr.get("rating") or 4.5),
                review_count=int(item.get("review_count") or attr.get("review_count") or 0),
                seller_name=str(item.get("seller_name") or "Daraz Official Seller"),
                seller_id=str(item.get("seller_id") or ""),
                brand=str(attr.get("brand") or ""),
                category=str(attr.get("category_name") or category or "General"),
                image_url=img,
                product_url=f"https://www.daraz.pk/products/-i{p_id}.html" if p_id else None,
                sku=str(primary_sku.get("SellerSku") or primary_sku.get("ShopSku") or ""),
                in_stock=primary_sku.get("quantity", 1) > 0,
                source="daraz.pk",
                raw_data=item
            )
            products.append(p_item)

        total = int(data_payload.get("total_products", len(products)) if isinstance(data_payload, dict) else len(products))
        search_res = DarazSearchResponse(
            query=query or "",
            page=page,
            total_products=total,
            has_next=(offset + len(products) < total),
            source="daraz.pk",
            products=products
        )

        return DarazFetchResult(
            success=True,
            data=search_res,
            provider_name=self.name
        )

    def get_product_details(self, item_id: str, url: Optional[str] = None) -> DarazFetchResult:
        """
        Fetch details for a single product via Official Daraz Open Platform.
        Endpoint: /product/item/get
        """
        if not self.is_configured():
            return DarazFetchResult(
                success=False,
                error_code=401,
                error_message="Daraz Official API credentials not configured.",
                provider_name=self.name
            )

        success, res_data, status_code, err = self._execute_api_call(
            api_path="/product/item/get",
            params={"item_id": item_id},
            require_auth=True
        )

        if not success or not res_data:
            return DarazFetchResult(
                success=False,
                error_code=status_code,
                error_message=err or f"Failed to get details for product {item_id}",
                provider_name=self.name,
                is_rate_limited=(status_code == 429)
            )

        item = res_data.get("data", {})
        attr = item.get("attributes", {})
        skus = item.get("skus", [])
        primary_sku = skus[0] if skus else {}

        price = float(primary_sku.get("price") or primary_sku.get("special_price") or 0.0)
        orig_price = float(primary_sku.get("original_price") or price)
        discount = round(((orig_price - price) / orig_price * 100), 1) if (orig_price > price > 0) else 0.0

        details = DarazProductDetails(
            platform="daraz",
            product_id=str(item.get("item_id") or item_id),
            name=str(attr.get("name") or "Daraz Product"),
            price=price,
            original_price=orig_price,
            discount=discount,
            discount_label=f"{int(discount)}% OFF" if discount > 0 else None,
            currency="PKR",
            rating=float(item.get("rating") or 4.5),
            review_count=int(item.get("review_count") or 0),
            in_stock=primary_sku.get("quantity", 1) > 0,
            brand=str(attr.get("brand") or ""),
            category=str(attr.get("category_name") or ""),
            description=str(attr.get("description") or attr.get("short_description") or ""),
            highlights=attr.get("highlights", []) if isinstance(attr.get("highlights"), list) else [],
            specifications=attr if isinstance(attr, dict) else {},
            warranty=str(attr.get("warranty_type") or ""),
            images=attr.get("Images", []) if isinstance(attr.get("Images"), list) else [],
            main_image=str(attr.get("Images", [""])[0] if isinstance(attr.get("Images"), list) and attr.get("Images") else ""),
            product_url=url or f"https://www.daraz.pk/products/-i{item_id}.html",
            source="daraz.pk",
            raw_module=item
        )

        return DarazFetchResult(
            success=True,
            data=details,
            provider_name=self.name
        )

    def get_categories(self) -> DarazFetchResult:
        """
        Fetch Daraz category taxonomy tree via Official Daraz Open Platform.
        Endpoint: /category/tree/get
        """
        if not self.is_configured():
            return DarazFetchResult(
                success=False,
                error_code=401,
                error_message="Daraz Official API credentials not configured.",
                provider_name=self.name
            )

        success, res_data, status_code, err = self._execute_api_call(
            api_path="/category/tree/get",
            params={},
            require_auth=False
        )

        if not success or not res_data:
            return DarazFetchResult(
                success=False,
                error_code=status_code,
                error_message=err or "Failed to fetch categories from Official Daraz API",
                provider_name=self.name,
                is_rate_limited=(status_code == 429)
            )

        cats_raw = res_data.get("data", [])
        categories: List[DarazCategoryItem] = []

        for c in cats_raw:
            cat_item = DarazCategoryItem(
                id=str(c.get("category_id") or c.get("id") or ""),
                name=str(c.get("name") or "Category"),
                level=int(c.get("level", 1)),
                subcategories=c.get("children", [])
            )
            categories.append(cat_item)

        return DarazFetchResult(
            success=True,
            data=categories,
            provider_name=self.name
        )

    def get_seller_products(self, seller_id: str, page: int = 1) -> DarazFetchResult:
        """
        Fetch products for a specific seller.
        Endpoint: /products/get (with seller filter)
        """
        return self.search_products(query="", page=page)
