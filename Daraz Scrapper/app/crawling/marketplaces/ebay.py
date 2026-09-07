"""eBay Marketplace Adapter supporting ebay.com, ebay.co.uk, ebay.de, etc."""

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


class EbayAdapter(BaseMarketplaceAdapter):
    """
    Marketplace adapter for eBay catalogs and item pages.
    """

    DOMAINS = ["ebay.com", "ebay.co.uk", "ebay.de", "ebay.com.au", "ebay.ca"]

    TITLE_SELECTORS = [
        "h1.x-item-title__mainTitle",
        ".x-item-title span",
        "#itemTitle",
        "h1.it-ttl",
    ]
    PRICE_SELECTORS = [
        ".x-price-primary span",
        ".x-bin-price__content .x-price-primary",
        "#prcIsum",
        "#mm-saleDscPrc",
        ".mainPrice span",
    ]
    IMAGE_SELECTORS = [
        ".ux-image-filmstrip-carousel-item img",
        ".x-photos-min-view img",
        "#mainImgHldr img",
        ".ux-image-carousel-item img",
    ]
    SELLER_SELECTORS = [
        ".x-sellercard-atf__info__about-seller a",
        ".mbg-nw",
        ".seller-persona a",
    ]

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.EBAY

    @property
    def supported_domains(self) -> List[str]:
        return self.DOMAINS

    def validate_url(self, url: str) -> bool:
        if not url:
            return False
        return any(d in url.lower() for d in self.DOMAINS)

    def detect_content_type(self, url: str) -> CrawlContentType:
        canonical = self.canonicalize_url(url).lower()
        if "/itm/" in canonical or re.search(r"/\d{9,14}(?:\?|$)", canonical):
            return CrawlContentType.PRODUCT
        elif "/sch/" in canonical or "_nkw=" in canonical:
            return CrawlContentType.SEARCH
        elif "/b/" in canonical:
            return CrawlContentType.CATEGORY
        return CrawlContentType.GENERIC

    def extract_product_id(self, url: str) -> Optional[str]:
        match = re.search(r"/itm/(?:[^/]+/)?(\d+)", url)
        if match:
            return match.group(1)
        match_alt = re.search(r"/(\d{9,14})(?:[/?]|$)", url)
        return match_alt.group(1) if match_alt else None

    def build_search_url(self, keyword: str, page: int = 1) -> str:
        safe_kw = keyword.strip().replace(" ", "+")
        if page > 1:
            return f"https://www.ebay.com/sch/i.html?_nkw={safe_kw}&_pgn={page}"
        return f"https://www.ebay.com/sch/i.html?_nkw={safe_kw}"

    def parse_response(self, response: CrawlResponse, content_type: CrawlContentType) -> UniversalCrawlResult:
        canonical_url = self.canonicalize_url(response.url)
        soup = BeautifulSoup(response.html, "html.parser")

        if content_type == CrawlContentType.PRODUCT:
            item_id = self.extract_product_id(canonical_url) or "UNKNOWN_EBAY_ID"

            # Title
            title = None
            for sel in self.TITLE_SELECTORS:
                el = soup.select_one(sel)
                if el:
                    title = self.clean_text(el.get_text())
                    if title:
                        break

            # Price
            price, currency = None, "USD"
            for sel in self.PRICE_SELECTORS:
                el = soup.select_one(sel)
                if el:
                    price, currency = self.clean_price(el.get_text())
                    if price is not None:
                        break

            # Images
            images: List[Image] = []
            seen_imgs = set()
            for sel in self.IMAGE_SELECTORS:
                for el in soup.select(sel):
                    src = el.get("data-src") or el.get("src")
                    if src and src not in seen_imgs and "s-l" in src:
                        # Convert to high-res s-l1600.jpg if thumbnail
                        hires = re.sub(r"s-l\d+\.", "s-l1600.", src)
                        seen_imgs.add(hires)
                        images.append(Image(
                            product_id=item_id,
                            url=hires,
                            position=len(images),
                            is_primary=(len(images) == 0),
                        ))

            # Seller
            seller_name = None
            for sel in self.SELLER_SELECTORS:
                el = soup.select_one(sel)
                if el:
                    seller_name = self.clean_text(el.get_text())
                    if seller_name:
                        break

            product = None
            if title and price is not None:
                product = Product(
                    product_id=item_id,
                    title=title,
                    url=canonical_url,
                    price=price,
                    currency=currency,
                    seller_name=seller_name,
                    images=images,
                )

            return UniversalCrawlResult(
                crawl_id=f"ebay_{item_id}",
                url=canonical_url,
                marketplace=MarketplaceType.EBAY,
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
        for a in soup.select("a[href*='/itm/']"):
            href = a.get("href", "")
            if self.validate_url(href):
                clean = self.canonicalize_url(href)
                if clean not in discovered_urls:
                    discovered_urls.append(clean)

        return UniversalCrawlResult(
            crawl_id="ebay_discovery",
            url=canonical_url,
            marketplace=MarketplaceType.EBAY,
            content_type=content_type,
            status=CrawlStatus.COMPLETED,
            success=True,
            status_code=response.status_code,
            discovered_urls=discovered_urls,
            raw_html=response.html,
        )
