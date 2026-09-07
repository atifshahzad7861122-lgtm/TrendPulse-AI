"""Amazon Marketplace Adapter supporting international domains (.com, .co.uk, .de, .com.br, etc.)."""

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


class AmazonAdapter(BaseMarketplaceAdapter):
    """
    Marketplace adapter for Amazon ecommerce catalogs.
    """

    DOMAINS = [
        "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
        "amazon.ca", "amazon.com.br", "amazon.in", "amazon.co.jp",
    ]

    TITLE_SELECTORS = ["#productTitle", "#title", "h1.a-size-large"]
    PRICE_SELECTORS = [
        ".a-price .a-offscreen", "#priceblock_ourprice",
        "#priceblock_dealprice", ".a-price-whole",
    ]
    ORIGINAL_PRICE_SELECTORS = [
        ".a-price.a-text-price .a-offscreen",
        ".basisPrice .a-offscreen",
    ]
    IMAGE_SELECTORS = [
        "#landingImage", "#imgBlkFront", "#main-image",
        "#imgTagWrapperId img", ".imageThumb img",
    ]
    RATING_SELECTORS = [
        "span[data-hook='rating-out-of-text']",
        "#acrPopover span.a-icon-alt",
        "i.a-icon-star span",
    ]
    REVIEW_COUNT_SELECTORS = [
        "#acrCustomerReviewText",
        "span[data-hook='total-review-count']",
    ]
    SELLER_SELECTORS = [
        "#sellerProfileTriggerId", "#merchant-info a", "#tabular-buybox .tabular-buybox-text",
    ]

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.AMAZON

    @property
    def supported_domains(self) -> List[str]:
        return self.DOMAINS

    def validate_url(self, url: str) -> bool:
        if not url:
            return False
        return any(d in url.lower() for d in self.DOMAINS)

    def detect_content_type(self, url: str) -> CrawlContentType:
        canonical = self.canonicalize_url(url).lower()
        if "/dp/" in canonical or "/gp/product/" in canonical or re.search(r"/([A-Z0-9]{10})(?:/|\?|$)", canonical):
            return CrawlContentType.PRODUCT
        elif "/s?" in canonical or "keywords=" in canonical or "/s/" in canonical:
            return CrawlContentType.SEARCH
        elif any(k in canonical for k in ["/b/", "/browse/", "/stores/"]):
            return CrawlContentType.CATEGORY
        return CrawlContentType.GENERIC

    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract standard 10-character Amazon ASIN."""
        match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        match_alt = re.search(r"/([A-Z0-9]{10})(?:[/?]|$)", url, re.IGNORECASE)
        if match_alt:
            return match_alt.group(1).upper()
        return None

    def build_search_url(self, keyword: str, page: int = 1) -> str:
        safe_kw = keyword.strip().replace(" ", "+")
        if page > 1:
            return f"https://www.amazon.com/s?k={safe_kw}&page={page}"
        return f"https://www.amazon.com/s?k={safe_kw}"

    def parse_response(self, response: CrawlResponse, content_type: CrawlContentType) -> UniversalCrawlResult:
        canonical_url = self.canonicalize_url(response.url)
        soup = BeautifulSoup(response.html, "html.parser")

        if content_type == CrawlContentType.PRODUCT:
            asin = self.extract_product_id(canonical_url) or "UNKNOWN_ASIN"
            
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

            # Original Price
            orig_price = None
            for sel in self.ORIGINAL_PRICE_SELECTORS:
                el = soup.select_one(sel)
                if el:
                    orig_price, _ = self.clean_price(el.get_text())
                    if orig_price is not None:
                        break

            # Images
            images: List[Image] = []
            seen_imgs = set()
            for sel in self.IMAGE_SELECTORS:
                for el in soup.select(sel):
                    src = el.get("data-old-hires") or el.get("src")
                    if src and src not in seen_imgs:
                        seen_imgs.add(src)
                        images.append(Image(
                            product_id=asin,
                            url=src,
                            position=len(images),
                            is_primary=(len(images) == 0),
                        ))

            # Rating & Reviews
            rating = None
            for sel in self.RATING_SELECTORS:
                el = soup.select_one(sel)
                if el:
                    m = re.search(r"([\d.]+)\s+out\s+of", el.get_text())
                    if m:
                        try:
                            rating = float(m.group(1))
                            break
                        except ValueError:
                            pass

            review_count = 0
            for sel in self.REVIEW_COUNT_SELECTORS:
                el = soup.select_one(sel)
                if el:
                    m = re.search(r"([\d,]+)", el.get_text())
                    if m:
                        try:
                            review_count = int(m.group(1).replace(",", ""))
                            break
                        except ValueError:
                            pass

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
                    product_id=asin,
                    title=title,
                    url=canonical_url,
                    price=price,
                    original_price=orig_price,
                    currency=currency,
                    rating=rating,
                    review_count=review_count,
                    seller_name=seller_name,
                    images=images,
                )

            return UniversalCrawlResult(
                crawl_id=f"amazon_{asin}",
                url=canonical_url,
                marketplace=MarketplaceType.AMAZON,
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
        for a in soup.select("a[href*='/dp/']"):
            href = a.get("href", "")
            if href.startswith("/"):
                href = f"https://www.amazon.com{href}"
            if self.validate_url(href):
                clean = self.canonicalize_url(href)
                if clean not in discovered_urls:
                    discovered_urls.append(clean)

        return UniversalCrawlResult(
            crawl_id="amazon_discovery",
            url=canonical_url,
            marketplace=MarketplaceType.AMAZON,
            content_type=content_type,
            status=CrawlStatus.COMPLETED,
            success=True,
            status_code=response.status_code,
            discovered_urls=discovered_urls,
            raw_html=response.html,
        )
