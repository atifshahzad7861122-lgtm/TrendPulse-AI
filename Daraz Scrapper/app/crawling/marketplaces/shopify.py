"""Shopify Marketplace Adapter supporting independent Shopify storefronts and JSON endpoints."""

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from app.crawling.marketplaces.base import BaseMarketplaceAdapter
from app.crawling.models import (
    CrawlContentType,
    CrawlResponse,
    CrawlStatus,
    MarketplaceType,
    UniversalCrawlResult,
)
from app.models.image import Image
from app.models.product import Product, ProductVariant


class ShopifyAdapter(BaseMarketplaceAdapter):
    """
    Marketplace adapter for independent Shopify-powered ecommerce stores.
    """

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.SHOPIFY

    @property
    def supported_domains(self) -> List[str]:
        return ["myshopify.com", "shopify"]

    def validate_url(self, url: str) -> bool:
        if not url:
            return False
        # Detect if domain is a Shopify store or contains Shopify URL structures
        return "myshopify.com" in url.lower() or "/products/" in url.lower() or "/collections/" in url.lower()

    @staticmethod
    def is_shopify_page(html: str) -> bool:
        """Heuristic detecting whether an arbitrary website runs on Shopify."""
        if not html:
            return False
        signals = [
            "cdn.shopify.com",
            "Shopify.theme",
            "Shopify.shop",
            "window.Shopify",
            "shopify-features",
            "/collections/all",
        ]
        return any(sig in html for sig in signals)

    def detect_content_type(self, url: str) -> CrawlContentType:
        canonical = self.canonicalize_url(url).lower()
        if "/products/" in canonical:
            return CrawlContentType.PRODUCT
        elif "/collections/" in canonical or "/collections/all" in canonical:
            return CrawlContentType.CATEGORY
        elif "/search" in canonical or "q=" in canonical:
            return CrawlContentType.SEARCH
        return CrawlContentType.GENERIC

    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract product handle / slug."""
        match = re.search(r"/products/([a-zA-Z0-9_-]+)", url)
        return match.group(1) if match else None

    def build_search_url(self, keyword: str, page: int = 1) -> str:
        # Base implementation requires domain or returns generic search query
        safe_kw = keyword.strip().replace(" ", "+")
        return f"/search?q={safe_kw}&page={page}"

    def build_json_endpoint(self, url: str) -> str:
        """Construct the direct public Shopify .json product endpoint."""
        clean = self.canonicalize_url(url)
        if clean.endswith(".json"):
            return clean
        parsed = urlparse(clean)
        path = parsed.path.rstrip("/") + ".json"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def parse_response(self, response: CrawlResponse, content_type: CrawlContentType) -> UniversalCrawlResult:
        canonical_url = self.canonicalize_url(response.url)
        handle = self.extract_product_id(canonical_url) or "unknown_handle"

        # 1. Check if response is raw JSON from .json endpoint
        if response.html.strip().startswith("{") and "product" in response.html:
            try:
                data = json.loads(response.html)
                prod_data = data.get("product", data)
                
                title = prod_data.get("title")
                vendor = prod_data.get("vendor")
                body_html = prod_data.get("body_html", "")
                
                # Variants
                variants = []
                primary_price = 0.0
                primary_orig_price = None
                
                raw_variants = prod_data.get("variants", [])
                for v in raw_variants:
                    v_price = float(v.get("price", 0.0))
                    v_compare = float(v.get("compare_at_price")) if v.get("compare_at_price") else None
                    if not primary_price and v_price > 0:
                        primary_price = v_price
                        primary_orig_price = v_compare
                    
                    variants.append({
                        "sku_id": str(v.get("id")),
                        "name": v.get("title") or "Default",
                        "price": v_price,
                        "available": v.get("available", True),
                    })

                # Images
                images = []
                for idx, img in enumerate(prod_data.get("images", [])):
                    src = img.get("src") if isinstance(img, dict) else img
                    if src:
                        images.append(Image(
                            product_id=str(prod_data.get("id", handle)),
                            url=src,
                            position=idx,
                            is_primary=(idx == 0),
                        ))

                product = Product(
                    product_id=str(prod_data.get("id", handle)),
                    title=title,
                    url=canonical_url,
                    price=primary_price,
                    original_price=primary_orig_price,
                    currency="USD",
                    seller_name=vendor,
                    description=body_html,
                    variants=variants,
                    images=images,
                )

                return UniversalCrawlResult(
                    crawl_id=f"shopify_{handle}",
                    url=canonical_url,
                    marketplace=MarketplaceType.SHOPIFY,
                    content_type=content_type,
                    status=CrawlStatus.COMPLETED,
                    success=True,
                    status_code=response.status_code,
                    source_engine=response.source_engine,
                    duration_ms=response.duration_ms,
                    product=product,
                    raw_html=response.html,
                )
            except Exception as e:
                pass

        # 2. HTML DOM / JSON-LD parsing
        soup = BeautifulSoup(response.html, "html.parser")
        title, price, orig_price, currency = None, None, None, "USD"
        images: List[Image] = []
        vendor = None

        # Check JSON-LD
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string)
                if isinstance(data, list):
                    data = data[0]
                if data.get("@type") == "Product":
                    title = data.get("name")
                    vendor = data.get("brand", {}).get("name") if isinstance(data.get("brand"), dict) else data.get("brand")
                    offers = data.get("offers", {})
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    if isinstance(offers, dict):
                        price = float(offers.get("price", 0.0))
                        currency = offers.get("priceCurrency", "USD")
                    img = data.get("image")
                    if isinstance(img, str):
                        images.append(Image(product_id=handle, url=img, is_primary=True))
                    elif isinstance(img, list):
                        for i, u in enumerate(img):
                            images.append(Image(product_id=handle, url=u, position=i, is_primary=(i == 0)))
                    break
            except Exception:
                pass

        # Fallback DOM selectors
        if not title:
            h1 = soup.select_one("h1.product-title, h1.product__title, h1")
            if h1:
                title = self.clean_text(h1.get_text())

        if price is None:
            p_el = soup.select_one(".price, .product__price, .price-item--regular, span[data-product-price]")
            if p_el:
                price, currency = self.clean_price(p_el.get_text())

        product = None
        if title and price is not None:
            product = Product(
                product_id=handle,
                title=title,
                url=canonical_url,
                price=price,
                original_price=orig_price,
                currency=currency,
                seller_name=vendor,
                images=images,
            )

        # Discovered URLs for collections / search
        discovered_urls: List[str] = []
        for a in soup.select("a[href*='/products/']"):
            href = a.get("href", "")
            if href.startswith("/"):
                parsed_root = urlparse(canonical_url)
                href = f"{parsed_root.scheme}://{parsed_root.netloc}{href}"
            clean = self.canonicalize_url(href)
            if clean not in discovered_urls:
                discovered_urls.append(clean)

        return UniversalCrawlResult(
            crawl_id=f"shopify_{handle}",
            url=canonical_url,
            marketplace=MarketplaceType.SHOPIFY,
            content_type=content_type,
            status=CrawlStatus.COMPLETED if product else CrawlStatus.FAILED,
            success=product is not None or len(discovered_urls) > 0,
            status_code=response.status_code,
            source_engine=response.source_engine,
            duration_ms=response.duration_ms,
            product=product,
            discovered_urls=discovered_urls,
            raw_html=response.html,
        )
