"""AliExpress Marketplace Adapter supporting aliexpress.com item URLs and runParams payloads."""

import json
import re
from typing import Any, Dict, List, Optional
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
from app.models.product import Product


class AliExpressAdapter(BaseMarketplaceAdapter):
    """
    Marketplace adapter for AliExpress catalogs and item pages.
    """

    DOMAINS = ["aliexpress.com", "aliexpress.us", "aliexpress.ru"]

    TITLE_SELECTORS = [
        "h1[data-pl='product-title']",
        ".product-title-text",
        "h1.title--wrap--MsrSsir",
        "h1",
    ]
    PRICE_SELECTORS = [
        ".product-price-value",
        ".price--current--I3msQc",
        ".uniform-banner-box-price",
        ".product-price-current",
    ]

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.ALIEXPRESS

    @property
    def supported_domains(self) -> List[str]:
        return self.DOMAINS

    def validate_url(self, url: str) -> bool:
        if not url:
            return False
        return any(d in url.lower() for d in self.DOMAINS)

    def detect_content_type(self, url: str) -> CrawlContentType:
        canonical = self.canonicalize_url(url).lower()
        if "/item/" in canonical or re.search(r"/\d{11,18}\.html", canonical):
            return CrawlContentType.PRODUCT
        elif "/w/wholesale" in canonical or "/wholesale" in canonical or "SearchText=" in canonical:
            return CrawlContentType.SEARCH
        elif "/category/" in canonical:
            return CrawlContentType.CATEGORY
        return CrawlContentType.GENERIC

    def extract_product_id(self, url: str) -> Optional[str]:
        match = re.search(r"/item/(\d+)\.html", url)
        if match:
            return match.group(1)
        match_alt = re.search(r"/(\d{11,18})\.html", url)
        return match_alt.group(1) if match_alt else None

    def build_search_url(self, keyword: str, page: int = 1) -> str:
        safe_kw = keyword.strip().replace(" ", "-")
        if page > 1:
            return f"https://www.aliexpress.com/w/wholesale-{safe_kw}.html?page={page}"
        return f"https://www.aliexpress.com/w/wholesale-{safe_kw}.html"

    def parse_response(self, response: CrawlResponse, content_type: CrawlContentType) -> UniversalCrawlResult:
        canonical_url = self.canonicalize_url(response.url)
        soup = BeautifulSoup(response.html, "html.parser")

        if content_type == CrawlContentType.PRODUCT:
            item_id = self.extract_product_id(canonical_url) or "UNKNOWN_ALIEXPRESS_ID"

            title, price, orig_price, currency = None, None, None, "USD"
            images: List[Image] = []
            rating, review_count, seller_name = None, 0, None

            # 1. Try parsing dynamic runParams JSON
            run_params_match = re.search(r"window\.runParams\s*=\s*({.*?});", response.html, re.DOTALL)
            if run_params_match:
                try:
                    data = json.loads(run_params_match.group(1))
                    data_obj = data.get("data", data)
                    title = data_obj.get("productInfoComponent", {}).get("subject")
                    price_info = data_obj.get("priceComponent", {})
                    if price_info:
                        price_str = price_info.get("discountPrice") or price_info.get("origPrice")
                        price, currency = self.clean_price(price_str)
                    
                    img_list = data_obj.get("imageComponent", {}).get("imagePathList", [])
                    for idx, img_url in enumerate(img_list):
                        images.append(Image(
                            product_id=item_id,
                            url=img_url,
                            position=idx,
                            is_primary=(idx == 0),
                        ))
                    
                    feedback = data_obj.get("feedbackComponent", {})
                    rating = feedback.get("evarageStar")
                    review_count = feedback.get("totalValidNum", 0)
                    seller_name = data_obj.get("sellerComponent", {}).get("storeName")
                except Exception:
                    pass

            # 2. DOM fallback
            if not title:
                for sel in self.TITLE_SELECTORS:
                    el = soup.select_one(sel)
                    if el:
                        title = self.clean_text(el.get_text())
                        if title:
                            break

            if price is None:
                for sel in self.PRICE_SELECTORS:
                    el = soup.select_one(sel)
                    if el:
                        price, currency = self.clean_price(el.get_text())
                        if price is not None:
                            break

            product = None
            if title and price is not None:
                product = Product(
                    product_id=item_id,
                    title=title,
                    url=canonical_url,
                    price=price,
                    currency=currency,
                    rating=rating,
                    review_count=review_count,
                    seller_name=seller_name,
                    images=images,
                )

            return UniversalCrawlResult(
                crawl_id=f"aliexpress_{item_id}",
                url=canonical_url,
                marketplace=MarketplaceType.ALIEXPRESS,
                content_type=content_type,
                status=CrawlStatus.COMPLETED if product else CrawlStatus.FAILED,
                success=product is not None,
                status_code=response.status_code,
                source_engine=response.source_engine,
                duration_ms=response.duration_ms,
                product=product,
                raw_html=response.html,
            )

        # Search / Category parsing
        discovered_urls: List[str] = []
        for a in soup.select("a[href*='/item/']"):
            href = a.get("href", "")
            if href.startswith("//"):
                href = f"https:{href}"
            if self.validate_url(href):
                clean = self.canonicalize_url(href)
                if clean not in discovered_urls:
                    discovered_urls.append(clean)

        return UniversalCrawlResult(
            crawl_id="aliexpress_discovery",
            url=canonical_url,
            marketplace=MarketplaceType.ALIEXPRESS,
            content_type=content_type,
            status=CrawlStatus.COMPLETED,
            success=True,
            status_code=response.status_code,
            discovered_urls=discovered_urls,
            raw_html=response.html,
        )
