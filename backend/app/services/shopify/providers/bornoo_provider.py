import urllib.request
import urllib.error
import json
from typing import Optional
from backend.app.models.domain import ShopifyProduct
from backend.app.services.shopify.base import ShopifyProvider, ShopifyFetchResult
from backend.app.services.shopify.providers.scout_provider import clean_domain, parse_shopify_product_json

class BornooShopifyProvider(ShopifyProvider):
    name = "bornoo"
    priority = 5
    display_name = "Bornoo Shopify Scraper"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

    def validate_store(self, store_domain: str) -> bool:
        domain = clean_domain(store_domain)
        url = f"https://{domain}/products.json?limit=1"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def fetch_products(
        self,
        store_domain: str,
        limit: int = 50,
        page: int = 1,
        collection: Optional[str] = None
    ) -> ShopifyFetchResult:
        domain = clean_domain(store_domain)
        url = f"https://{domain}/products.json?limit={limit}&page={page}"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw_prods = data.get("products", [])
                    products = [parse_shopify_product_json(p, domain, self.name) for p in raw_prods]
                    return ShopifyFetchResult(
                        success=True,
                        products=products,
                        total_count=len(products),
                        has_next=len(products) >= limit,
                        is_empty_valid=len(products) == 0,
                        raw_response={"count": len(products)}
                    )
                elif resp.status == 429:
                    return ShopifyFetchResult(
                        success=False,
                        error_code=429,
                        error_message="Rate limit reached on Bornoo Scraper",
                        is_rate_limited=True
                    )
                else:
                    return ShopifyFetchResult(
                        success=False,
                        error_code=resp.status,
                        error_message=f"HTTP {resp.status} on Bornoo Scraper"
                    )
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return ShopifyFetchResult(
                    success=False,
                    error_code=429,
                    error_message="Rate limit exceeded on Bornoo Scraper",
                    is_rate_limited=True
                )
            return ShopifyFetchResult(
                success=False,
                error_code=e.code,
                error_message=f"HTTP Error {e.code} on Bornoo: {e.reason}"
            )
        except urllib.error.URLError as e:
            is_timeout = "timed out" in str(e).lower()
            return ShopifyFetchResult(
                success=False,
                error_code=408 if is_timeout else 503,
                error_message=f"Network error on Bornoo: {str(e.reason)}",
                is_timeout=is_timeout
            )
        except Exception as e:
            return ShopifyFetchResult(
                success=False,
                error_code=500,
                error_message=f"Unexpected error in Bornoo: {str(e)}"
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
