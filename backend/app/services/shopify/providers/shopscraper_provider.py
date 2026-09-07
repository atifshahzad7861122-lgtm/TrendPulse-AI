import urllib.request
import urllib.error
import json
from typing import Optional
from backend.app.models.domain import ShopifyProduct
from backend.app.services.shopify.base import ShopifyProvider, ShopifyFetchResult
from backend.app.services.shopify.providers.scout_provider import clean_domain, parse_shopify_product_json

class ShopScraperProvider(ShopifyProvider):
    name = "shopscraper"
    priority = 2
    display_name = "ShopScraper"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }

    def validate_store(self, store_domain: str) -> bool:
        domain = clean_domain(store_domain)
        url = f"https://{domain}/collections/all/products.json?limit=1"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return "products" in data
        except Exception:
            return False
        return False

    def fetch_products(
        self,
        store_domain: str,
        limit: int = 50,
        page: int = 1,
        collection: Optional[str] = None
    ) -> ShopifyFetchResult:
        domain = clean_domain(store_domain)
        coll_path = f"collections/{collection.strip()}" if collection else "collections/all"
        url = f"https://{domain}/{coll_path}/products.json?limit={limit}&page={page}"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.status
                if status_code == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw_prods = data.get("products", [])
                    if not isinstance(raw_prods, list):
                        return ShopifyFetchResult(
                            success=False,
                            error_code=502,
                            error_message="Malformed products list in ShopScraper"
                        )
                    
                    products = [parse_shopify_product_json(p, domain, self.name) for p in raw_prods]
                    return ShopifyFetchResult(
                        success=True,
                        products=products,
                        total_count=len(products),
                        has_next=len(products) >= limit,
                        is_empty_valid=len(products) == 0,
                        raw_response={"count": len(products)}
                    )
                elif status_code == 429:
                    return ShopifyFetchResult(
                        success=False,
                        error_code=429,
                        error_message="Rate limit reached on ShopScraper",
                        is_rate_limited=True
                    )
                else:
                    return ShopifyFetchResult(
                        success=False,
                        error_code=status_code,
                        error_message=f"HTTP {status_code} from ShopScraper"
                    )
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return ShopifyFetchResult(
                    success=False,
                    error_code=429,
                    error_message="Rate limit exceeded on ShopScraper",
                    is_rate_limited=True
                )
            return ShopifyFetchResult(
                success=False,
                error_code=e.code,
                error_message=f"HTTP Error {e.code} on ShopScraper: {e.reason}"
            )
        except urllib.error.URLError as e:
            is_timeout = "timed out" in str(e).lower()
            return ShopifyFetchResult(
                success=False,
                error_code=408 if is_timeout else 503,
                error_message=f"Network error on ShopScraper: {str(e.reason)}",
                is_timeout=is_timeout
            )
        except Exception as e:
            return ShopifyFetchResult(
                success=False,
                error_code=500,
                error_message=f"Unexpected error in ShopScraper: {str(e)}"
            )

    def fetch_product(self, store_domain: str, product_id_or_handle: str) -> Optional[ShopifyProduct]:
        domain = clean_domain(store_domain)
        handle = str(product_id_or_handle).strip()
        url = f"https://{domain}/products/{handle}.json"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    p = data.get("product")
                    if p:
                        return parse_shopify_product_json(p, domain, self.name)
        except Exception:
            pass
        return None

    def health_check(self) -> bool:
        return True
