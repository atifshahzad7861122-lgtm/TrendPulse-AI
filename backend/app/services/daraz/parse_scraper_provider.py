import time
import logging
import requests
import re
from typing import Dict, Any, List, Optional, Tuple

from backend.app.core.config import settings
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

class DarazParseScraperProvider(DarazProvider):
    """
    Parse Scraper API Provider for Daraz Pakistan.
    Priority 2 (Secondary provider).
    """
    name: str = "parse_daraz_api"
    priority: int = 2

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ):
        self.api_key = api_key or settings.PARSE_API_KEY
        self.base_url = (base_url or settings.PARSE_DARAZ_API_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key or "",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _clean_html(self, text: str) -> str:
        if not text:
            return ""
        clean = re.sub(r'<[^>]+>', ' ', text)
        clean = clean.replace('&ndash;', '-').replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _parse_float(self, val: Any, default: float = 0.0) -> float:
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
        if val is None:
            return default
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        try:
            s = str(val).lower().replace(",", "").strip()
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

    def _execute_request(self, endpoint_name: str, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int], Optional[str]]:
        url = f"{self.base_url}/{endpoint_name}"
        headers = self._get_headers()
        attempt = 0

        while attempt < self.max_retries:
            attempt += 1
            try:
                logger.debug(f"Parse Daraz Scraper request: {endpoint_name} (Attempt {attempt}/{self.max_retries})")
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

                if response.status_code in (401, 403):
                    logger.error(f"Parse Daraz Auth Failed: HTTP {response.status_code}")
                    return False, None, 401, "Parse API Authentication Failed."

                if response.status_code == 429:
                    if attempt >= self.max_retries:
                        return False, None, 429, "Parse API rate limit reached."
                    time.sleep(self.backoff_factor ** attempt)
                    continue

                if response.status_code in (500, 502, 503, 504):
                    if attempt >= self.max_retries:
                        return False, None, response.status_code, f"Parse API gateway error {response.status_code}."
                    time.sleep(self.backoff_factor ** attempt)
                    continue

                response.raise_for_status()
                return True, response.json(), 200, None

            except requests.exceptions.Timeout:
                if attempt >= self.max_retries:
                    return False, None, 504, "Parse Daraz scraper timed out."
                time.sleep(self.backoff_factor ** attempt)
            except Exception as e:
                if attempt >= self.max_retries:
                    return False, None, 500, f"Parse scraper error: {str(e)}"
                time.sleep(1.0)

        return False, None, 500, "Parse API request failed."

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
        if not self.is_configured():
            return DarazFetchResult(
                success=False,
                error_code=401,
                error_message="PARSE_API_KEY not configured.",
                provider_name=self.name
            )

        payload: Dict[str, Any] = {"page": page}
        if query:
            payload["query"] = query
        elif category:
            payload["query"] = category
        else:
            payload["query"] = "daraz"

        success, res_json, status_code, err = self._execute_request("search_products", payload)
        if not success or not res_json:
            return DarazFetchResult(
                success=False,
                error_code=status_code,
                error_message=err or "Failed to search Parse Daraz scraper",
                provider_name=self.name,
                is_rate_limited=(status_code == 429)
            )

        # Parse products from response
        items: List[Dict[str, Any]] = []
        if isinstance(res_json, dict):
            data_block = res_json.get("data", {})
            if isinstance(data_block, dict):
                for k in ["products", "items", "result", "list"]:
                    if k in data_block and isinstance(data_block[k], list):
                        items = data_block[k]
                        break
            elif isinstance(data_block, list):
                items = data_block
            
            if not items:
                for k in ["products", "items", "data", "result", "list"]:
                    if k in res_json and isinstance(res_json[k], list):
                        items = res_json[k]
                        break
        elif isinstance(res_json, list):
            items = res_json

        parsed_products: List[DarazProductItem] = []
        for raw in items:
            name = self._clean_html(str(raw.get("name") or raw.get("title") or ""))
            p_id = str(raw.get("itemId") or raw.get("nid") or raw.get("item_id") or raw.get("product_id") or raw.get("id") or "")
            if not p_id and not name:
                continue

            price = self._parse_float(raw.get("price") or raw.get("sale_price") or raw.get("price_raw") or raw.get("priceShow"))
            orig_price = self._parse_float(raw.get("originalPrice") or raw.get("original_price") or raw.get("price_before_discount") or raw.get("originalPriceShow") or price)
            discount = self._parse_float(raw.get("discount") or raw.get("discount_percentage"))
            if discount == 0.0 and orig_price > price > 0:
                discount = round(((orig_price - price) / orig_price) * 100, 1)

            rating = self._parse_float(raw.get("ratingScore") or raw.get("rating") or raw.get("stars") or raw.get("rating_score"), default=0.0)
            review_count = self._parse_int(raw.get("review") or raw.get("review_count") or raw.get("reviews") or raw.get("ratings_count"))
            url = raw.get("itemUrl") or raw.get("url") or raw.get("product_url") or (f"https://www.daraz.pk/products/-i{p_id}.html" if p_id else None)
            if url and url.startswith("//"):
                url = "https:" + url
            img = raw.get("image") or raw.get("image_url") or raw.get("main_image")
            if img and img.startswith("//"):
                img = "https:" + img

            cat_val = None
            if isinstance(raw.get("categories"), list) and raw.get("categories"):
                cat_val = str(raw.get("categories")[0])
            else:
                cat_val = category or raw.get("category")

            seller_name = raw.get("sellerName") or raw.get("seller_name") or raw.get("shop_name")
            seller_id = str(raw.get("sellerId") or raw.get("seller_id") or "") if (raw.get("sellerId") or raw.get("seller_id")) else None

            item = DarazProductItem(
                platform="daraz",
                product_id=p_id or f"dp_{hash(name) % 1000000}",
                name=name or "Daraz Product",
                price=price,
                original_price=orig_price,
                discount=discount,
                discount_label=raw.get("discount_label") or (f"{int(discount)}% OFF" if discount > 0 else None),
                currency="PKR",
                rating=rating,
                review_count=review_count,
                seller_name=seller_name,
                seller_id=seller_id,
                brand=raw.get("brandName") or raw.get("brand") or raw.get("brand_name"),
                category=cat_val,
                image_url=img,
                product_url=url,
                sku=str(raw.get("sku") or raw.get("cheapest_sku") or "") if (raw.get("sku") or raw.get("cheapest_sku")) else None,
                in_stock=raw.get("inStock", raw.get("in_stock", True)),
                source="daraz.pk",
                raw_data=raw
            )
            parsed_products.append(item)

        search_res = DarazSearchResponse(
            query=query or category or "daraz",
            page=page,
            total_products=len(parsed_products),
            has_next=len(parsed_products) >= 20,
            source="daraz.pk",
            products=parsed_products
        )

        return DarazFetchResult(
            success=True,
            data=search_res,
            provider_name=self.name
        )

    def get_product_details(self, item_id: str, url: Optional[str] = None) -> DarazFetchResult:
        if not self.is_configured():
            return DarazFetchResult(
                success=False,
                error_code=401,
                error_message="PARSE_API_KEY not configured.",
                provider_name=self.name
            )

        payload: Dict[str, Any] = {}
        if item_id:
            payload["item_id"] = item_id
        if url:
            payload["url"] = url

        success, res_json, status_code, err = self._execute_request("get_item_details", payload)
        if not success or not res_json:
            return DarazFetchResult(
                success=False,
                error_code=status_code,
                error_message=err or f"Failed to get details for item {item_id}",
                provider_name=self.name,
                is_rate_limited=(status_code == 429)
            )

        data = res_json.get("data") if isinstance(res_json, dict) and "data" in res_json else res_json
        name = self._clean_html(str(data.get("name") or data.get("title") or "Daraz Product"))
        price = self._parse_float(data.get("price") or data.get("sale_price"))
        orig_price = self._parse_float(data.get("original_price") or price)
        discount = self._parse_float(data.get("discount"))
        if discount == 0.0 and orig_price > price > 0:
            discount = round(((orig_price - price) / orig_price) * 100, 1)

        details = DarazProductDetails(
            platform="daraz",
            product_id=str(item_id or data.get("item_id") or "0"),
            name=name,
            price=price,
            original_price=orig_price,
            discount=discount,
            discount_label=f"{int(discount)}% OFF" if discount > 0 else None,
            currency="PKR",
            rating=self._parse_float(data.get("rating"), default=0.0),
            review_count=self._parse_int(data.get("review_count")),
            in_stock=data.get("in_stock", True),
            brand=data.get("brand"),
            category=data.get("category"),
            description=self._clean_html(str(data.get("description") or "")),
            highlights=self._extract_highlights(data.get("highlights")),
            specifications=self._extract_specifications(data.get("specifications")),
            warranty=data.get("warranty"),
            images=data.get("images", []),
            main_image=data.get("image") or data.get("main_image"),
            product_url=url or f"https://www.daraz.pk/products/-i{item_id}.html",
            source="daraz.pk",
            raw_module=data
        )

        return DarazFetchResult(
            success=True,
            data=details,
            provider_name=self.name
        )

    def get_categories(self) -> DarazFetchResult:
        if not self.is_configured():
            return DarazFetchResult(
                success=False,
                error_code=401,
                error_message="PARSE_API_KEY not configured.",
                provider_name=self.name
            )

        success, res_json, status_code, err = self._execute_request("get_categories", {})
        if not success or not res_json:
            return DarazFetchResult(
                success=False,
                error_code=status_code,
                error_message=err or "Failed to fetch categories from Parse Daraz scraper",
                provider_name=self.name,
                is_rate_limited=(status_code == 429)
            )

        cats_raw = res_json.get("categories", []) if isinstance(res_json, dict) else res_json
        categories: List[DarazCategoryItem] = []
        for c in (cats_raw if isinstance(cats_raw, list) else []):
            cat_item = DarazCategoryItem(
                id=str(c.get("id") or c.get("category_id") or ""),
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
        if not self.is_configured():
            return DarazFetchResult(
                success=False,
                error_code=401,
                error_message="PARSE_API_KEY not configured.",
                provider_name=self.name
            )

        success, res_json, status_code, err = self._execute_request("get_seller_products", {"seller_id": seller_id, "page": page})
        if not success or not res_json:
            return DarazFetchResult(
                success=False,
                error_code=status_code,
                error_message=err or f"Failed to get seller products for {seller_id}",
                provider_name=self.name,
                is_rate_limited=(status_code == 429)
            )

        # Build seller response
        search_res = self.search_products(query="", page=page)
        return search_res
