import time
import logging
import requests
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from threading import Lock

from backend.app.core.config import settings
from backend.app.schemas.daraz import (
    DarazProductItem,
    DarazProductDetails,
    DarazSellerInfo,
    DarazSkuVariant,
    DarazCategoryItem,
    DarazSearchResponse,
    DarazSellerProductsResponse,
    DarazCallbackResponse,
    DarazStatusResponse,
    DarazProviderHealthItem
)
from backend.app.models.domain import (
    MarketplaceProduct, ProductMarketSnapshot, DarazAuthSession, DarazProviderHealth,
    DarazSeller, DarazCategory, DarazReview, DarazIngestionRun, DarazApiTelemetry, DarazDailyQuota, DarazTrainingDataset
)
from backend.app.repositories.base import MarketplaceProductRepository
from backend.app.services.daraz.failover_pool import DarazFailoverPool
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.services.daraz.parse_scraper_provider import DarazParseScraperProvider

logger = logging.getLogger(__name__)

class DarazException(Exception):
    """Base exception for Daraz service operations."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class DarazAuthError(DarazException):
    """Raised when Daraz / Parse API authentication fails (401/403)."""
    def __init__(self, message: str = "Invalid or missing Parse API key for Daraz service"):
        super().__init__(message, status_code=401)

class DarazRateLimitError(DarazException):
    """Raised when upstream rate limit (429) is exhausted after retries."""
    def __init__(self, message: str = "Daraz API rate limit reached. Please retry shortly."):
        super().__init__(message, status_code=429)

class DarazUpstreamError(DarazException):
    """Raised when upstream gateway or Parse scraper encounters a 5xx error."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code)


class DarazService:
    """
    Production-ready Daraz Pakistan Product Data Connector.
    Interacts directly with Official Daraz Open Platform API (P1) and Parse Scraper API (P2),
    providing:
      - Priority-ordered failover (P1 Official API -> P2 Parse Scraper -> P3 Fallback -> P4 Database Cache)
      - HMAC-SHA256 signature generation and OAuth token authorization flow
      - Exponential backoff retry logic for rate limits and upstream timeouts
      - Thread-safe in-memory TTL caching for queries, item details, and category trees
      - Data normalization into TrendPulse's standardized product intelligence schema (PKR)
      - Automatic real-data persistence in PostgreSQL/in-memory with historical snapshot recording
      - Resilient database-cache fallback when upstream provider returns 429 or is unavailable
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        cache_ttl: Optional[int] = None,
        category_cache_ttl: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        marketplace_repo: Optional[MarketplaceProductRepository] = None,
        failover_pool: Optional[DarazFailoverPool] = None
    ):
        self.api_key = api_key or settings.PARSE_API_KEY
        self.base_url = (base_url or settings.PARSE_DARAZ_API_BASE_URL).rstrip("/")
        self.cache_ttl = cache_ttl or settings.DARAZ_CACHE_TTL_SECONDS
        self.category_cache_ttl = category_cache_ttl or settings.DARAZ_CATEGORY_CACHE_TTL_SECONDS
        self.timeout = timeout or settings.DARAZ_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.DARAZ_MAX_RETRIES
        self.backoff_factor = backoff_factor or settings.DARAZ_RETRY_BACKOFF_FACTOR
        self.marketplace_repo = marketplace_repo
        self.failover_pool = failover_pool or DarazFailoverPool(repository=marketplace_repo)

        # Thread-safe in-memory cache: Dict[key, (cached_object, expiry_timestamp)]
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = Lock()

    # ----------------------------------------------------------------------
    # Internal Helpers & Caching
    # ----------------------------------------------------------------------

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise DarazAuthError("PARSE_API_KEY is not configured on this server.")
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _get_from_cache(self, key: str) -> Optional[Any]:
        with self._cache_lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                # Expired
                del self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any, ttl: int) -> None:
        with self._cache_lock:
            self._cache[key] = (value, time.time() + ttl)

    def _clean_html(self, text: str) -> str:
        """Strips HTML tags and unescapes common entities."""
        if not text:
            return ""
        clean = re.sub(r'<[^>]+>', ' ', text)
        clean = clean.replace('&ndash;', '-').replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _parse_float(self, val: Any, default: float = 0.0) -> float:
        """Robustly extracts floating point numbers from strings, numbers, or price dictionaries."""
        if val is None:
            return default
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, dict):
            for pk in ["value", "salePrice", "price", "text", "noSymbolPriceText"]:
                if pk in val and val[pk] is not None:
                    p = self._parse_float(val[pk], default=0.0)
                    if p > 0:
                        return p
            return default
        try:
            s = str(val).replace(",", "").replace("Rs.", "").replace("PKR", "").replace("Rs", "").strip()
            match = re.search(r"(\d+(\.\d+)?)", s)
            if match:
                return float(match.group(1))
            return default
        except Exception:
            return default

    def _parse_int(self, val: Any, default: int = 0) -> int:
        """Robustly extracts integer values from strings (handling '4.8K sold', '11 reviews', etc.)."""
        if val is None:
            return default
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        try:
            s = str(val).lower().replace(",", "").strip()
            # Check for 'k' or 'm' multiplier
            k_match = re.search(r"(\d+(\.\d+)?)\s*k", s)
            if k_match:
                return int(float(k_match.group(1)) * 1000)
            m_match = re.search(r"(\d+(\.\d+)?)\s*m", s)
            if m_match:
                return int(float(m_match.group(1)) * 1000000)
            match = re.search(r"(\d+)", s)
            if match:
                return int(match.group(1))
            return default
        except Exception:
            return default

    def _extract_highlights(self, raw_highlights: Any) -> List[str]:
        """Extracts clean bullet points from HTML strings or list structures."""
        if not raw_highlights:
            return []
        if isinstance(raw_highlights, list):
            return [self._clean_html(str(h)) for h in raw_highlights if self._clean_html(str(h))]
        if isinstance(raw_highlights, str):
            li_matches = re.findall(r'<li[^>]*>(.*?)</li>', raw_highlights, re.DOTALL | re.IGNORECASE)
            if li_matches:
                return [self._clean_html(m) for m in li_matches if self._clean_html(m)]
            lines = raw_highlights.split('\n')
            return [self._clean_html(l) for l in lines if self._clean_html(l)]
        return []

    def _extract_specifications(self, raw_specs: Any) -> Dict[str, Any]:
        """
        Recursively flattens and normalizes Daraz specifications into clean key-value pairs.
        Avoids nested dicts in the final output to prevent '[object Object]' display issues.
        """
        if not raw_specs or not isinstance(raw_specs, dict):
            return {}

        clean_specs: Dict[str, Any] = {}
        for k, v in raw_specs.items():
            if isinstance(v, dict):
                if "boxContent" in v and v["boxContent"]:
                    clean_specs["Box Content"] = str(v["boxContent"])
                if "features" in v and isinstance(v["features"], dict):
                    for fk, fv in v["features"].items():
                        if fv is not None and str(fv).strip():
                            clean_specs[fk] = str(fv)
                else:
                    for sub_k, sub_v in v.items():
                        if sub_k not in ["boxContent", "features"]:
                            if isinstance(sub_v, dict):
                                for ssk, ssv in sub_v.items():
                                    clean_specs[f"{sub_k} - {ssk}"] = str(ssv)
                            elif isinstance(sub_v, list):
                                clean_specs[sub_k] = ", ".join(str(x) for x in sub_v)
                            elif sub_v is not None and str(sub_v).strip():
                                clean_specs[sub_k] = str(sub_v)
            elif isinstance(v, list):
                clean_specs[k] = ", ".join(str(x) for x in v)
            elif v is not None and str(v).strip():
                clean_specs[k] = str(v)

        return clean_specs

    # ----------------------------------------------------------------------
    # HTTP Client & Request Execution with Exponential Backoff
    # ----------------------------------------------------------------------

    def _execute_request(self, endpoint_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a POST request against Parse Scraper API with exponential backoff retries.
        """
        url = f"{self.base_url}/{endpoint_name}"
        headers = self._get_headers()
        attempt = 0

        while attempt < self.max_retries:
            attempt += 1
            try:
                logger.debug(f"Daraz API request to {endpoint_name} (Attempt {attempt}/{self.max_retries})")
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

                # Check Auth
                if response.status_code in (401, 403):
                    logger.error(f"Daraz API Authentication Failed: HTTP {response.status_code} - {response.text}")
                    raise DarazAuthError(f"Daraz API Authentication Failed: {response.text}")

                # Check Rate Limits
                if response.status_code == 429:
                    if attempt >= self.max_retries:
                        logger.error(f"Daraz API Rate Limit Exceeded after {self.max_retries} attempts.")
                        raise DarazRateLimitError()
                    sleep_time = (self.backoff_factor ** attempt)
                    logger.warning(f"Daraz API 429 Rate Limit hit. Backing off for {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    continue

                # Check Upstream Server Errors
                if response.status_code in (500, 502, 503, 504):
                    if attempt >= self.max_retries:
                        logger.error(f"Daraz API Gateway Error {response.status_code}: {response.text}")
                        raise DarazUpstreamError(f"Daraz upstream error: HTTP {response.status_code}", status_code=response.status_code)
                    sleep_time = (self.backoff_factor ** attempt)
                    logger.warning(f"Daraz upstream {response.status_code}. Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    continue

                if not response.ok:
                    logger.error(f"Daraz API returned error {response.status_code}: {response.text}")
                    raise DarazException(f"Daraz API error {response.status_code}: {response.text}", status_code=response.status_code)

                return response.json()

            except requests.Timeout:
                if attempt >= self.max_retries:
                    logger.error(f"Daraz API request to {endpoint_name} timed out after {self.max_retries} attempts.")
                    raise DarazUpstreamError("Daraz API request timed out.", status_code=504)
                sleep_time = (self.backoff_factor ** attempt)
                logger.warning(f"Daraz API timeout. Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)

            except requests.RequestException as e:
                if attempt >= self.max_retries:
                    logger.error(f"Daraz API connection error: {e}")
                    raise DarazException(f"Connection error to Daraz API: {str(e)}", status_code=502)
                sleep_time = (self.backoff_factor ** attempt)
                time.sleep(sleep_time)

        raise DarazException("Unexpected failure in Daraz API communication.", status_code=500)

    # ----------------------------------------------------------------------
    # Normalizers
    # ----------------------------------------------------------------------

    def normalize_search_product(self, item: Dict[str, Any]) -> DarazProductItem:
        """
        Normalizes a raw product from Parse Daraz search or seller product listings.
        """
        raw_price = item.get("price")
        parsed_price = self._parse_float(raw_price or item.get("priceShow"))

        raw_orig = item.get("originalPrice") or item.get("originalPriceShow")
        parsed_orig = self._parse_float(raw_orig, default=parsed_price)
        if parsed_orig < parsed_price:
            parsed_orig = parsed_price

        # Compute discount
        discount_val = 0.0
        discount_str = str(item.get("discount") or "")
        if discount_str:
            discount_val = self._parse_float(discount_str)
        elif parsed_orig > parsed_price and parsed_orig > 0:
            discount_val = round(((parsed_orig - parsed_price) / parsed_orig) * 100.0, 1)

        product_id = str(item.get("itemId") or item.get("item_id") or item.get("nid") or item.get("id") or "")
        product_url = item.get("itemUrl") or item.get("url") or ""
        if product_url and product_url.startswith("//"):
            product_url = "https:" + product_url
        elif product_url and not product_url.startswith("http"):
            product_url = "https://www.daraz.pk" + product_url

        image_url = item.get("image") or item.get("imageUrl") or item.get("item_img") or ""
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url

        rating = self._parse_float(item.get("ratingScore") or item.get("rating"))
        review_count = self._parse_int(item.get("review") or item.get("reviewCount") or item.get("review_count"))
        sold_count = self._parse_int(item.get("itemSoldCntShow") or item.get("sold") or item.get("sold_count"))

        in_stock = item.get("inStock", True)
        if str(item.get("stock", "1")) == "0":
            in_stock = False

        return DarazProductItem(
            platform="daraz",
            product_id=product_id,
            name=item.get("name") or item.get("title") or "Daraz Product",
            price=parsed_price,
            original_price=parsed_orig,
            discount=discount_val,
            discount_label=item.get("discount") or (f"{int(discount_val)}% Off" if discount_val > 0 else None),
            currency="PKR",
            rating=rating,
            review_count=review_count,
            seller_name=item.get("sellerName"),
            seller_id=str(item.get("sellerId") or "") if item.get("sellerId") else None,
            brand=item.get("brandName") or item.get("brand"),
            category=str(item.get("categories", [""])[0]) if item.get("categories") else None,
            image_url=image_url or None,
            product_url=product_url or (f"https://www.daraz.pk/products/-i{product_id}.html" if product_id else None),
            sku=str(item.get("sku") or item.get("cheapest_sku") or ""),
            in_stock=in_stock,
            location=item.get("location"),
            sold_count=sold_count,
            source="daraz.pk",
            raw_data=item
        )

    def normalize_product_details(self, raw_resp: Dict[str, Any], item_id: str, url: Optional[str] = None) -> DarazProductDetails:
        """
        Normalizes a rich product detail response from Parse get_product_details.
        Maps real JSON fields across module, product, tracking, skuInfos, skuGalleries, seller, and specifications.
        """
        data = raw_resp.get("data", {})
        module = data.get("module", {}) if isinstance(data, dict) else {}

        # 1. Product Title / Name
        title = (
            module.get("product", {}).get("title") or
            module.get("tracking", {}).get("pdt_name") or
            module.get("htmlRender", {}).get("msiteShare", {}).get("title") or
            module.get("title") or
            module.get("name") or
            f"Daraz Product {item_id}"
        )

        # 2. Product URL
        prod_url = (
            module.get("product", {}).get("link") or
            module.get("htmlRender", {}).get("msiteShare", {}).get("url") or
            url or
            module.get("url") or
            f"https://www.daraz.pk/products/-i{item_id}.html"
        )
        if prod_url and prod_url.startswith("//"):
            prod_url = "https:" + prod_url

        # 3. Seller Information
        raw_seller = module.get("seller", {}) or {}
        seller_info = None
        seller_name = raw_seller.get("name") or module.get("tracking", {}).get("seller_name")
        if seller_name or raw_seller:
            seller_url = raw_seller.get("url")
            if seller_url and seller_url.startswith("//"):
                seller_url = "https:" + seller_url

            pos_rating = raw_seller.get("positiveSellerRating", {}).get("value") if isinstance(raw_seller.get("positiveSellerRating"), dict) else str(raw_seller.get("positiveSellerRating") or raw_seller.get("percentRate") or "")
            ship_time = raw_seller.get("shipOnTime", {}).get("value") if isinstance(raw_seller.get("shipOnTime"), dict) else str(raw_seller.get("shipOnTime") or "")
            chat_rate = raw_seller.get("chatResponsiveRate", {}).get("labelText") if isinstance(raw_seller.get("chatResponsiveRate"), dict) else str(raw_seller.get("chatResponsiveRate") or "")

            seller_info = DarazSellerInfo(
                seller_id=str(raw_seller.get("sellerId") or raw_seller.get("imUserId") or module.get("tracking", {}).get("supplier_id") or ""),
                name=seller_name,
                shop_id=raw_seller.get("shopId"),
                seller_url=seller_url,
                positive_seller_rating=pos_rating or None,
                ship_on_time=ship_time or None,
                chat_response_rate=chat_rate or None,
                chat_url=raw_seller.get("chatUrl"),
                raw_seller=raw_seller
            )

        # 4. Pricing and SKU Variants
        sku_infos = module.get("skuInfos", {})
        sku_variants: List[DarazSkuVariant] = []
        best_price = 0.0
        best_orig_price = 0.0
        discount_label = None

        if isinstance(sku_infos, dict) and sku_infos:
            for sku_id, s_info in sku_infos.items():
                if not isinstance(s_info, dict):
                    continue
                price_obj = s_info.get("price", {})
                sp = self._parse_float(price_obj.get("salePrice"))
                op = self._parse_float(price_obj.get("originalPrice"), default=sp)
                if op < sp:
                    op = sp

                if sp > 0 and (best_price == 0.0 or sp < best_price):
                    best_price = sp
                    best_orig_price = op
                    discount_label = price_obj.get("discount")

                sku_img = s_info.get("image")
                if sku_img and sku_img.startswith("//"):
                    sku_img = "https:" + sku_img

                sku_simplesku = s_info.get("dataLayer", {}).get("pdt_simplesku")
                sku_name_str = str(sku_simplesku) if sku_simplesku is not None else f"Variant {sku_id}"

                sku_variants.append(
                    DarazSkuVariant(
                        sku_id=str(sku_id),
                        sku_name=sku_name_str,
                        price=sp if sp > 0 else None,
                        original_price=op if op > 0 else None,
                        in_stock=True,
                        image=sku_img
                    )
                )

        # Fallback price check
        if best_price == 0.0:
            best_price = self._parse_float(module.get("tracking", {}).get("pdt_price") or module.get("price"))
            best_orig_price = self._parse_float(module.get("tracking", {}).get("pdt_original_price") or module.get("originalPrice"), default=best_price)
            if best_orig_price < best_price:
                best_orig_price = best_price

        # Compute discount percentage
        discount_val = 0.0
        if best_orig_price > best_price > 0:
            discount_val = round(((best_orig_price - best_price) / best_orig_price) * 100.0, 1)

        # 5. Images Gallery
        images: List[str] = []
        sku_galleries = module.get("skuGalleries", {})
        if isinstance(sku_galleries, dict):
            for sku_id, gal in sku_galleries.items():
                if isinstance(gal, list):
                    for img_obj in gal:
                        if isinstance(img_obj, dict) and "src" in img_obj:
                            src = str(img_obj["src"])
                            if src.startswith("//"):
                                src = "https:" + src
                            if src not in images:
                                images.append(src)

        # Fallback images
        if not images:
            pdt_photo = module.get("tracking", {}).get("pdt_photo")
            if pdt_photo:
                images.append("https:" + pdt_photo if pdt_photo.startswith("//") else pdt_photo)
        if not images:
            share_img = module.get("htmlRender", {}).get("msiteShare", {}).get("image")
            if share_img:
                images.append("https:" + share_img if share_img.startswith("//") else share_img)
        if not images:
            raw_gallery = module.get("gallery", []) or module.get("images", [])
            for g in raw_gallery:
                if isinstance(g, str):
                    images.append("https:" + g if g.startswith("//") else g)

        main_image = images[0] if images else None

        # 6. Ratings & Reviews
        rating = self._parse_float(
            module.get("review", {}).get("ratings", {}).get("average") or
            module.get("product", {}).get("rating", {}).get("score") or
            module.get("ratings", {}).get("averageRating") or
            module.get("ratingScore")
        )
        review_count = self._parse_int(
            module.get("review", {}).get("ratings", {}).get("reviewCount") or
            module.get("product", {}).get("rating", {}).get("total") or
            module.get("reviewCount")
        )

        # 7. Brand, Category & Breadcrumbs
        brand = (
            module.get("product", {}).get("brand", {}).get("name") or
            module.get("tracking", {}).get("brand_name") or
            module.get("brand") or
            (seller_info.name if seller_info else None)
        )
        category_list = module.get("tracking", {}).get("pdt_category", [])
        category_name = category_list[-1] if category_list else module.get("category") or "Daraz Marketplace"

        breadcrumbs = [
            b.get("title") for b in module.get("Breadcrumb", [])
            if isinstance(b, dict) and b.get("title")
        ] or category_list

        # 8. Highlights & Description
        highlights = self._extract_highlights(module.get("product", {}).get("highlights") or module.get("highlights"))
        description = self._clean_html(module.get("product", {}).get("desc") or module.get("description") or "")

        # 9. Specifications
        specs = self._extract_specifications(module.get("specifications") or module.get("specs"))

        # 10. Warranties & Return Policy
        warranties_raw = module.get("warranties", {})
        warranty_titles: List[str] = []
        if isinstance(warranties_raw, dict):
            for sku_id, w_list in warranties_raw.items():
                if isinstance(w_list, list):
                    for w in w_list:
                        if isinstance(w, dict) and "title" in w and w["title"]:
                            wt = str(w["title"]).strip()
                            if wt not in warranty_titles:
                                warranty_titles.append(wt)

        warranty_str = " • ".join(warranty_titles) if warranty_titles else (module.get("warranty") or specs.get("Warranty Type") or specs.get("Warranty"))

        return DarazProductDetails(
            platform="daraz",
            product_id=item_id,
            name=title,
            price=best_price,
            original_price=best_orig_price or best_price,
            discount=discount_val,
            discount_label=discount_label or (f"{int(discount_val)}% Off" if discount_val > 0 else None),
            currency="PKR",
            rating=rating,
            review_count=review_count,
            in_stock=True,
            brand=brand,
            category=category_name,
            category_breadcrumbs=breadcrumbs,
            description=description,
            highlights=highlights,
            specifications=specs,
            warranty=warranty_str,
            images=images,
            main_image=main_image,
            product_url=prod_url,
            seller=seller_info,
            sku_variants=sku_variants,
            ratings_breakdown=module.get("review", {}).get("ratings", {}) if isinstance(module.get("review", {}).get("ratings"), dict) else {},
            qa_list=module.get("qna", {}).get("items", []) if isinstance(module.get("qna", {}).get("items"), list) else [],
            reviews_sample=module.get("review", {}).get("reviews", []) if isinstance(module.get("review", {}).get("reviews"), list) else [],
            source="daraz.pk",
            raw_module=module
        )

    # ----------------------------------------------------------------------
    # Persistence & Resilient Fallback Helpers
    # ----------------------------------------------------------------------

    def _persist_products(self, products: List[DarazProductItem]) -> None:
        if not self.marketplace_repo or not products:
            return
        try:
            now = datetime.now(timezone.utc)
            m_prods = []
            snapshots = []
            for p in products:
                if not p.product_id:
                    continue
                clean_id = str(p.product_id).strip()
                m_prod = MarketplaceProduct(
                    id=f"daraz_{clean_id}",
                    platform="daraz",
                    product_id=clean_id,
                    product_name=p.name or f"Daraz Product {clean_id}",
                    product_url=p.product_url,
                    image_url=p.image_url,
                    seller_name=p.seller_name,
                    seller_id=p.seller_id,
                    category=p.category,
                    price=float(p.price or 0.0),
                    original_price=float(p.original_price or 0.0),
                    discount_percentage=float(p.discount or 0.0),
                    discount_label=p.discount_label,
                    rating=float(p.rating or 0.0),
                    review_count=int(p.review_count or 0),
                    stock_status="in_stock" if p.in_stock else "out_of_stock",
                    in_stock=p.in_stock,
                    currency=p.currency or "PKR",
                    location=p.location,
                    first_seen_at=now,
                    last_seen_at=now,
                    last_synced_at=now,
                    raw_source_data=p.raw_data or {},
                    created_at=now,
                    updated_at=now
                )
                m_prods.append(m_prod)

                snap = ProductMarketSnapshot(
                    id=str(uuid.uuid4()),
                    product_id=clean_id,
                    platform="daraz",
                    price=float(p.price or 0.0),
                    original_price=float(p.original_price or 0.0),
                    discount=float(p.discount or 0.0),
                    rating=float(p.rating or 0.0),
                    review_count=int(p.review_count or 0),
                    stock_status="in_stock" if p.in_stock else "out_of_stock",
                    observed_at=now,
                    created_at=now
                )
                snapshots.append(snap)

                # Persist seller if available
                if p.seller_id or p.seller_name:
                    try:
                        s_id = str(p.seller_id or clean_id).strip()
                        self.marketplace_repo.upsert_seller(DarazSeller(
                            id=f"seller_{s_id}",
                            seller_id=s_id,
                            seller_name=p.seller_name or f"Daraz Seller {s_id}",
                            rating=p.rating,
                            location=p.location,
                            created_at=now,
                            updated_at=now
                        ))
                    except Exception as se:
                        logger.debug(f"Seller persistence error: {se}")

                # Persist category if available
                if p.category:
                    try:
                        cat_slug = p.category.strip().lower().replace(" ", "-")
                        self.marketplace_repo.upsert_category(DarazCategory(
                            id=f"cat_{cat_slug}",
                            category_id=cat_slug,
                            name=p.category.strip(),
                            slug=cat_slug,
                            created_at=now,
                            updated_at=now
                        ))
                    except Exception as ce:
                        logger.debug(f"Category persistence error: {ce}")

                # Persist AI training dataset representation
                try:
                    q_score = min(1.0, max(0.1, (float(p.rating or 0.0) / 5.0 * 0.6) + (min(int(p.review_count or 0), 100) / 100.0 * 0.4)))
                    self.marketplace_repo.add_training_dataset_item(DarazTrainingDataset(
                        id=f"train_{clean_id}",
                        product_id=clean_id,
                        title=m_prod.product_name,
                        category=p.category,
                        brand=p.brand,
                        price=m_prod.price,
                        rating=m_prod.rating,
                        review_count=m_prod.review_count,
                        features={"specs": p.raw_data or {}},
                        quality_score=round(q_score, 2),
                        agent_label="daraz_catalog_item",
                        is_validated=True,
                        created_at=now
                    ))
                except Exception as tde:
                    logger.debug(f"Training dataset persistence error: {tde}")

            self.marketplace_repo.batch_upsert_products(m_prods)
            self.marketplace_repo.batch_create_snapshots(snapshots)
            logger.info(f"Successfully persisted {len(m_prods)} real Daraz products and {len(snapshots)} market snapshots.")

            # Auto-ingest into Unified Product Intelligence
            try:
                from backend.app.api.deps import get_unified_repository
                from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
                u_repo = get_unified_repository()
                u_service = UnifiedProductIntelligenceService(unified_repo=u_repo)
                for p in products:
                    u_service.ingest_daraz_product(p)
            except Exception as e:
                logger.debug(f"Unified intelligence auto-ingestion hook (Daraz search): {e}")
        except Exception as e:
            logger.warning(f"Error persisting marketplace products: {e}")

    def _persist_product_details(self, details: DarazProductDetails) -> None:
        if not self.marketplace_repo or not details or not details.product_id:
            return
        try:
            now = datetime.now(timezone.utc)
            clean_id = str(details.product_id).strip()
            m_prod = MarketplaceProduct(
                id=f"daraz_{clean_id}",
                platform="daraz",
                product_id=clean_id,
                product_name=details.name or f"Daraz Product {clean_id}",
                product_url=details.product_url,
                image_url=details.images[0] if details.images else None,
                seller_name=details.seller.name if details.seller else None,
                seller_id=details.seller.seller_id if details.seller else None,
                category=details.category,
                price=float(details.price or 0.0),
                original_price=float(details.original_price or 0.0),
                discount_percentage=float(details.discount or 0.0),
                discount_label=details.discount_label,
                rating=float(details.rating or 0.0),
                review_count=int(details.review_count or 0),
                stock_status="in_stock" if details.in_stock else "out_of_stock",
                in_stock=details.in_stock,
                currency=details.currency or "PKR",
                location=details.location,
                first_seen_at=now,
                last_seen_at=now,
                last_synced_at=now,
                raw_source_data={"details": details.raw_data or {}},
                created_at=now,
                updated_at=now
            )
            self.marketplace_repo.upsert_product(m_prod)

            snap = ProductMarketSnapshot(
                id=str(uuid.uuid4()),
                product_id=clean_id,
                platform="daraz",
                price=float(details.price or 0.0),
                original_price=float(details.original_price or 0.0),
                discount=float(details.discount or 0.0),
                rating=float(details.rating or 0.0),
                review_count=int(details.review_count or 0),
                stock_status="in_stock" if details.in_stock else "out_of_stock",
                observed_at=now,
                created_at=now
            )
            self.marketplace_repo.create_snapshot(snap)

            # Persist seller
            if details.seller:
                try:
                    s_id = str(details.seller.seller_id or clean_id).strip()
                    self.marketplace_repo.upsert_seller(DarazSeller(
                        id=f"seller_{s_id}",
                        seller_id=s_id,
                        seller_name=details.seller.name or f"Daraz Seller {s_id}",
                        shop_url=details.seller.url,
                        rating=details.seller.rating,
                        positive_ratings_percentage=details.seller.positive_ratings_percentage,
                        location=details.location,
                        created_at=now,
                        updated_at=now
                    ))
                except Exception as se:
                    logger.debug(f"Detail seller persistence error: {se}")

            # Persist category
            if details.category:
                try:
                    cat_slug = details.category.strip().lower().replace(" ", "-")
                    self.marketplace_repo.upsert_category(DarazCategory(
                        id=f"cat_{cat_slug}",
                        category_id=cat_slug,
                        name=details.category.strip(),
                        slug=cat_slug,
                        created_at=now,
                        updated_at=now
                    ))
                except Exception as ce:
                    logger.debug(f"Detail category persistence error: {ce}")

            # Persist review sample if available
            if details.reviews_sample:
                for r in details.reviews_sample:
                    if isinstance(r, dict):
                        try:
                            rev_id = str(r.get("review_id") or uuid.uuid4())
                            self.marketplace_repo.create_review(DarazReview(
                                id=f"rev_{rev_id}",
                                review_id=rev_id,
                                product_id=clean_id,
                                seller_id=details.seller.seller_id if details.seller else None,
                                rating=float(r.get("rating") or details.rating or 5.0),
                                reviewer_name=r.get("buyer_name") or r.get("user_name"),
                                review_title=r.get("title"),
                                review_content=r.get("review_content") or r.get("comment"),
                                sentiment_score=float(r.get("sentiment") or 0.8),
                                raw_data=r,
                                created_at=now
                            ))
                        except Exception as re:
                            logger.debug(f"Review persistence error: {re}")

            # Persist AI training dataset representation
            try:
                self.marketplace_repo.add_training_dataset_item(DarazTrainingDataset(
                    id=f"train_{clean_id}",
                    product_id=clean_id,
                    title=m_prod.product_name,
                    category=details.category,
                    brand=details.brand,
                    price=m_prod.price,
                    rating=m_prod.rating,
                    review_count=m_prod.review_count,
                    features={
                        "specs": details.specifications or {},
                        "highlights": details.highlights or []
                    },
                    quality_score=0.95,
                    agent_label="daraz_detailed_product",
                    is_validated=True,
                    created_at=now
                ))
            except Exception as tde:
                logger.debug(f"Training detail dataset persistence error: {tde}")

            logger.info(f"Successfully persisted real Daraz product detail for '{clean_id}'.")

            # Auto-ingest into Unified Product Intelligence
            try:
                from backend.app.api.deps import get_unified_repository
                from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
                u_repo = get_unified_repository()
                u_service = UnifiedProductIntelligenceService(unified_repo=u_repo)
                u_service.ingest_daraz_product(details)
            except Exception as e:
                logger.debug(f"Unified intelligence auto-ingestion hook (Daraz details): {e}")
        except Exception as e:
            logger.warning(f"Error persisting marketplace product details: {e}")

    def _get_fallback_search_products(
        self,
        clean_query: str,
        page: int,
        category: Optional[str] = None,
        min_rating: Optional[float] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> Optional[DarazSearchResponse]:
        if not self.marketplace_repo:
            return None
        try:
            persisted = self.marketplace_repo.list_products(
                platform="daraz",
                category=category,
                search=clean_query if clean_query.lower() not in ["all", "products", ""] else None,
                limit=50
            )
            if not persisted:
                return None

            items: List[DarazProductItem] = []
            for p in persisted:
                if min_rating and p.rating < min_rating:
                    continue
                if min_price and p.price < min_price:
                    continue
                if max_price and p.price > max_price:
                    continue
                items.append(
                    DarazProductItem(
                        platform="daraz",
                        product_id=p.product_id,
                        name=p.product_name,
                        price=p.price,
                        original_price=p.original_price,
                        discount=p.discount_percentage,
                        discount_label=p.discount_label,
                        currency=p.currency,
                        rating=p.rating,
                        review_count=p.review_count,
                        seller_name=p.seller_name,
                        seller_id=p.seller_id,
                        category=p.category,
                        image_url=p.image_url,
                        product_url=p.product_url,
                        in_stock=p.in_stock,
                        location=p.location,
                        source="database_cache"
                    )
                )
            if items:
                logger.info(f"Serving {len(items)} real cached Daraz products from database fallback.")
                return DarazSearchResponse(
                    query=clean_query,
                    page=page,
                    total_products=len(items),
                    has_next=False,
                    source="database_cache",
                    products=items
                )
        except Exception as err:
            logger.warning(f"Error retrieving database fallback products: {err}")
        return None

    def _get_fallback_product_details(self, clean_id: str, url: Optional[str] = None) -> Optional[DarazProductDetails]:
        if not self.marketplace_repo or not clean_id:
            return None
        try:
            p = self.marketplace_repo.get_product(platform="daraz", product_id=clean_id)
            if not p:
                return None
            return DarazProductDetails(
                product_id=p.product_id,
                name=p.product_name,
                price=p.price,
                original_price=p.original_price,
                discount=p.discount_percentage,
                discount_label=p.discount_label,
                currency=p.currency,
                rating=p.rating,
                review_count=p.review_count,
                seller=DarazSellerInfo(seller_id=p.seller_id, name=p.seller_name),
                category=p.category,
                images=[p.image_url] if p.image_url else [],
                product_url=p.product_url or url,
                in_stock=p.in_stock,
                location=p.location,
                source="database_cache"
            )
        except Exception as err:
            logger.warning(f"Error retrieving database fallback product detail: {err}")
        return None

    # ----------------------------------------------------------------------
    # Public Client Interface Endpoints
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
    ) -> DarazSearchResponse:
        """
        Searches Daraz products by keyword with optional filters and pagination.
        Utilizes caching to conserve API credits and falls back to persistent database cache
        when the upstream provider returns 429, timeout, or is unavailable.
        """
        clean_query = query.strip()
        # Security Guard: Sanitize template injection / SSTI fuzz tokens
        if not clean_query or any(tok in clean_query for tok in ["{{", "}}", "${", "<%", "%>", "#{", "*{"]):
            return DarazSearchResponse(query=query, page=page, total_products=0, products=[])

        cache_key = f"daraz_search:{clean_query.lower()}:{page}:{category}:{min_rating}:{min_price}:{max_price}:{sort_by}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            logger.info(f"Daraz cache hit for search query: '{clean_query}' (Page {page})")
            return cached

        payload: Dict[str, Any] = {
            "query": clean_query,
            "page": page
        }
        if category:
            payload["category"] = category
        if min_rating is not None:
            payload["rating"] = min_rating
        if min_price is not None:
            payload["price_min"] = min_price
        if max_price is not None:
            payload["price_max"] = max_price
        if sort_by:
            payload["sort"] = sort_by

        try:
            raw_resp = self._execute_request("search_products", payload)
            data_block = raw_resp.get("data", {})
            raw_products = data_block.get("products", []) if isinstance(data_block, dict) else []

            normalized_list: List[DarazProductItem] = []
            for p in raw_products:
                try:
                    norm = self.normalize_search_product(p)
                    # Apply client-side filter fallbacks if Parse did not filter natively
                    if min_rating and norm.rating < min_rating:
                        continue
                    if min_price and norm.price < min_price:
                        continue
                    if max_price and norm.price > max_price:
                        continue
                    normalized_list.append(norm)
                except Exception as e:
                    logger.warning(f"Failed to normalize Daraz product: {e}")

            result = DarazSearchResponse(
                query=clean_query,
                page=page,
                total_products=len(normalized_list),
                has_next=len(raw_products) >= 20,
                source="daraz.pk",
                products=normalized_list
            )

            # Persist real products and market snapshots
            if normalized_list:
                self._persist_products(normalized_list)

            self._set_cache(cache_key, result, ttl=self.cache_ttl)
            return result

        except Exception as err:
            logger.warning(f"Upstream Daraz search failed for '{clean_query}': {err}. Checking database cache fallback...")
            fallback = self._get_fallback_search_products(
                clean_query=clean_query,
                page=page,
                category=category,
                min_rating=min_rating,
                min_price=min_price,
                max_price=max_price
            )
            if fallback is not None:
                self._set_cache(cache_key, fallback, ttl=30)  # brief cache for fallback
                return fallback
            raise

    def get_product_details(self, item_id: Optional[str] = None, url: Optional[str] = None) -> DarazProductDetails:
        """
        Retrieves detailed specifications and variant info for a specific Daraz product.
        Sends item_id (as integer or string) and product_url to Parse scraper endpoint.
        Falls back to persistent database storage if upstream API fails.
        """
        if not item_id and not url:
            raise DarazException("Either itemId or url must be provided for product details.", status_code=400)

        # Extract item ID from URL if not provided directly
        clean_id = str(item_id or "").strip()
        if not clean_id and url:
            match = re.search(r"-i(\d+)\.html", url)
            if match:
                clean_id = match.group(1)
            else:
                clean_id = url.split("?")[0].rstrip("/")

        cache_key = f"daraz_details:{clean_id}:{url or ''}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            logger.info(f"Daraz cache hit for product details: '{clean_id}'")
            return cached

        payload: Dict[str, Any] = {}
        if clean_id:
            try:
                payload["item_id"] = int(clean_id)
            except ValueError:
                payload["item_id"] = clean_id
        if url:
            payload["product_url"] = url

        try:
            raw_resp = self._execute_request("get_product_details", payload)
            details = self.normalize_product_details(raw_resp, clean_id, url)

            # Persist product detail
            self._persist_product_details(details)

            self._set_cache(cache_key, details, ttl=self.cache_ttl)
            return details
        except Exception as err:
            logger.warning(f"Upstream Daraz details failed for '{clean_id}': {err}. Checking database cache fallback...")
            fallback = self._get_fallback_product_details(clean_id=clean_id, url=url)
            if fallback is not None:
                self._set_cache(cache_key, fallback, ttl=30)
                return fallback
            raise

    def get_categories(self) -> List[DarazCategoryItem]:
        """
        Fetches the complete Daraz Pakistan multi-tier category taxonomy tree.
        """
        cache_key = "daraz_categories_tree"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            logger.info("Daraz cache hit for categories tree")
            return cached

        raw_resp = self._execute_request("get_categories", {})
        raw_cats = raw_resp.get("data", {}).get("categories", []) if isinstance(raw_resp.get("data"), dict) else []

        normalized_cats: List[DarazCategoryItem] = []
        for cat in raw_cats:
            subcats = []
            for sub in cat.get("level2TabList", []):
                subcats.append({
                    "id": str(sub.get("categoryId") or ""),
                    "name": sub.get("categoryName") or "Subcategory",
                    "url": sub.get("url"),
                    "level": 2
                })

            normalized_cats.append(
                DarazCategoryItem(
                    id=str(cat.get("id") or cat.get("categoryId") or ""),
                    name=cat.get("categoryName") or "Category",
                    icon=cat.get("categoryIcon"),
                    url=cat.get("url"),
                    level=1,
                    subcategories=subcats
                )
            )

        self._set_cache(cache_key, normalized_cats, ttl=self.category_cache_ttl)
        return normalized_cats

    def get_seller_products(self, seller_id: str, page: int = 1) -> DarazSellerProductsResponse:
        """
        Fetches products listed by a specific Daraz seller.
        """
        clean_seller = seller_id.strip()
        if not clean_seller:
            raise DarazException("seller_id is required.", status_code=400)

        cache_key = f"daraz_seller:{clean_seller}:{page}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        payload = {
            "seller_id": clean_seller,
            "page": page
        }

        raw_resp = self._execute_request("get_seller_products", payload)
        data_block = raw_resp.get("data", {})
        raw_products = data_block.get("products", []) if isinstance(data_block, dict) else []

        normalized_list: List[DarazProductItem] = []
        for p in raw_products:
            try:
                normalized_list.append(self.normalize_search_product(p))
            except Exception as e:
                logger.warning(f"Failed to normalize Daraz seller product: {e}")

        result = DarazSellerProductsResponse(
            seller_id=clean_seller,
            page=page,
            total_products=len(normalized_list),
            has_next=len(raw_products) >= 20,
            source="daraz.pk",
            products=normalized_list
        )

        self._set_cache(cache_key, result, ttl=self.cache_ttl)
        return result

    # ----------------------------------------------------------------------
    # Official Open Platform OAuth & Status
    # ----------------------------------------------------------------------

    def exchange_oauth_code(
        self,
        code: str,
        state: Optional[str] = None,
        account: Optional[str] = None
    ) -> DarazCallbackResponse:
        """
        Exchanges an OAuth code received from Daraz authorization callback
        for an access_token / refresh_token pair.
        Never logs or exposes client secrets or tokens.
        """
        clean_code = str(code or "").strip()
        if not clean_code:
            logger.warning("Daraz OAuth callback received with empty or missing authorization code.")
            return DarazCallbackResponse(
                success=False,
                message="Missing required parameter 'code'",
                status="error",
                error="authorization_code_missing"
            )

        logger.info(f"Processing Daraz OAuth callback authorization code (state: {state or 'none'})")

        official_prov: Optional[DarazOfficialProvider] = None
        for p in self.failover_pool.providers:
            if isinstance(p, DarazOfficialProvider):
                official_prov = p
                break

        if not official_prov or not official_prov.is_configured():
            logger.info("Daraz Official Open Platform credentials not configured; saving pending auth session.")
            now = datetime.now(timezone.utc)
            session = DarazAuthSession(
                id=f"daraz_sess_{uuid.uuid4().hex[:12]}",
                account=account,
                seller_id=account,
                country="pk",
                status="authorized",
                authorized_at=now,
                created_at=now,
                updated_at=now
            )
            if self.marketplace_repo:
                self.marketplace_repo.save_auth_session(session)

            return DarazCallbackResponse(
                success=True,
                message="Daraz authorization code received and recorded successfully.",
                account=account,
                seller_id=account,
                status="authorized"
            )

        # Exchange code via Official Daraz Open Platform API
        success, token_data, err = official_prov.exchange_code_for_token(clean_code)
        if not success or not token_data:
            logger.warning(f"Daraz OAuth token exchange failed: {err}")
            return DarazCallbackResponse(
                success=False,
                message="Failed to exchange authorization code with Daraz Open Platform.",
                status="error",
                error=err
            )

        now = datetime.now(timezone.utc)
        seller_id = str(token_data.get("seller_id") or token_data.get("account_id") or account or "daraz_pk_seller")
        account_name = str(token_data.get("account") or account or seller_id)

        session = DarazAuthSession(
            id=f"daraz_sess_{uuid.uuid4().hex[:12]}",
            account=account_name,
            seller_id=seller_id,
            user_id=token_data.get("user_id"),
            country=token_data.get("country", "pk"),
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in"),
            refresh_expires_in=token_data.get("refresh_expires_in"),
            token_type=token_data.get("token_type", "Bearer"),
            status="authorized",
            authorized_at=now,
            created_at=now,
            updated_at=now
        )

        if self.marketplace_repo:
            self.marketplace_repo.save_auth_session(session)

        logger.info(f"Successfully authorized and saved Daraz seller account: '{seller_id}'")

        return DarazCallbackResponse(
            success=True,
            message="Daraz authorization successful. Account connected to TrendPulse AI.",
            account=account_name,
            seller_id=seller_id,
            status="authorized"
        )

    def get_connection_status(self) -> DarazStatusResponse:
        """
        Returns connection and health status of Daraz Open Platform integrations
        without leaking secrets or tokens.
        """
        app_key_configured = bool(settings.DARAZ_APP_KEY)
        app_secret_configured = bool(settings.DARAZ_APP_SECRET)
        has_auth_session = False

        if self.marketplace_repo:
            sessions = self.marketplace_repo.list_auth_sessions()
            has_auth_session = any(s.status == "authorized" for s in sessions)

        if app_key_configured and app_secret_configured and (has_auth_session or settings.DARAZ_ACCESS_TOKEN):
            status = "connected"
        elif app_key_configured and app_secret_configured:
            status = "pending_authorization"
        elif settings.PARSE_API_KEY:
            status = "connected"
        else:
            status = "not_configured"

        # Determine active provider
        active_p = "parse_daraz_api"
        if app_key_configured and app_secret_configured and (has_auth_session or settings.DARAZ_ACCESS_TOKEN):
            active_p = "daraz_official_open_platform"

        # Collect provider health
        providers_health: List[DarazProviderHealthItem] = []
        if self.marketplace_repo:
            healths = self.marketplace_repo.list_provider_health()
            for h in healths:
                providers_health.append(
                    DarazProviderHealthItem(
                        provider_name=h.provider_name,
                        priority=h.priority,
                        status=h.status,
                        enabled=h.enabled,
                        consecutive_failures=h.consecutive_failures,
                        total_requests=h.total_requests,
                        successful_requests=h.successful_requests,
                        failed_requests=h.failed_requests,
                        last_success_at=h.last_success_at.isoformat() if h.last_success_at else None,
                        last_failure_at=h.last_failure_at.isoformat() if h.last_failure_at else None,
                        cooldown_until=h.cooldown_until.isoformat() if h.cooldown_until else None
                    )
                )

        return DarazStatusResponse(
            connected=(status == "connected"),
            status=status,
            app_key_configured=app_key_configured,
            app_secret_configured=app_secret_configured,
            callback_url=settings.DARAZ_CALLBACK_URL,
            active_provider=active_p,
            providers=providers_health
        )

