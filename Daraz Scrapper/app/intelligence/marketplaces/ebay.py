"""eBay product intelligence extractor."""

import re
import uuid
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from app.core.constants import SentimentType
from app.crawling.models import CrawlResponse, MarketplaceType
from app.intelligence.extractors.category import CategoryExtractor
from app.intelligence.extractors.description import DescriptionExtractor
from app.intelligence.extractors.images import ImageExtractor
from app.intelligence.extractors.rating import RatingReviewExtractor
from app.intelligence.extractors.sales import SalesExtractor
from app.intelligence.extractors.seller import SellerExtractor
from app.intelligence.extractors.specifications import SpecificationExtractor
from app.intelligence.extractors.variants import VariantExtractor
from app.intelligence.marketplaces.base import BaseMarketplaceExtractor
from app.intelligence.models.product import ImageRecord, ProductIntelligence, Specification, Variant
from app.intelligence.models.result import ExtractionStatus, IntelligenceExtractionResult
from app.intelligence.models.review import IntelligenceReview
from app.intelligence.models.snapshot import HistoricalSnapshot


class EbayIntelligenceExtractor(BaseMarketplaceExtractor):
    """Production-grade eBay product intelligence extractor."""

    _EBAY_DOMAINS = ["ebay.com", "ebay.co.uk", "ebay.de", "ebay.ca", "ebay.com.au"]

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.EBAY

    def validate_url(self, url: str) -> bool:
        return any(d in url.lower() for d in self._EBAY_DOMAINS)

    def extract_product_id(self, url: str) -> Optional[str]:
        # Extract numeric eBay Item ID
        m = re.search(r"/itm/(?:[a-zA-Z0-9\-]+/)?(\d{9,14})", url)
        if m:
            return m.group(1)
        return None

    def extract_intelligence(self, response: CrawlResponse) -> IntelligenceExtractionResult:
        canonical_url = self.canonicalize_url(response.url)
        item_id = self.extract_product_id(canonical_url) or str(uuid.uuid4())[:12]
        warnings: List[str] = []
        errors: List[str] = []

        if response.status_code == 404:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=item_id,
                marketplace=MarketplaceType.EBAY,
                url=canonical_url,
                status=ExtractionStatus.NOT_FOUND,
                success=False,
                status_code=404,
                errors=["eBay item listing not found (HTTP 404)"],
            )

        if response.status_code in (403, 429) or "Reference #" in response.html or "Pardon Our Interruption" in response.html:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=item_id,
                marketplace=MarketplaceType.EBAY,
                url=canonical_url,
                status=ExtractionStatus.CHALLENGE,
                success=False,
                status_code=response.status_code,
                errors=["eBay Bot Challenge / Akamai 403 encountered."],
                raw_payload=response.html,
            )

        soup = BeautifulSoup(response.html, "html.parser")
        jsonld = self.extract_jsonld(soup)

        # 1. Extract Title (JSON-LD -> DOM -> OpenGraph)
        title = None
        if jsonld:
            title = jsonld.get("name") or jsonld.get("title")

        if not title:
            title_el = soup.select_one(".x-item-title__mainTitle .ux-textspans, h1.x-item-title, h1#itemTitle, h1")
            if title_el:
                title = title_el.get_text(strip=True)

        if not title:
            og = self.extract_opengraph(soup)
            title = og.get("og:title") or og.get("title")

        if not title:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=item_id,
                marketplace=MarketplaceType.EBAY,
                url=canonical_url,
                status=ExtractionStatus.FAILED,
                success=False,
                status_code=response.status_code,
                errors=["Mandatory title missing from eBay listing"],
            )

        # 2. Extract Price & Currency (JSON-LD -> DOM -> OpenGraph)
        price = 0.0
        orig_price = None
        currency = "USD"

        if jsonld and "offers" in jsonld:
            offers = jsonld["offers"]
            if isinstance(offers, dict):
                p_val = offers.get("price") or offers.get("lowPrice")
                if p_val:
                    try:
                        price = float(p_val)
                    except ValueError:
                        pass
                if "priceCurrency" in offers:
                    currency = str(offers["priceCurrency"])

        if price == 0.0:
            price_el = soup.select_one(".x-price-primary .ux-textspans, .x-bin-price .ux-textspans, #prcIsum, .vim.d-vi-price")
            if price_el:
                p_text = price_el.get_text(strip=True)
                if "£" in p_text:
                    currency = "GBP"
                elif "EUR" in p_text or "€" in p_text:
                    currency = "EUR"
                elif "AU" in p_text or "C $" in p_text:
                    currency = "CAD"

                clean_p = re.sub(r"[^\d\.]", "", p_text)
                try:
                    price = float(clean_p)
                except ValueError:
                    pass

        # 3. Rating & Review Count
        rating = None
        if jsonld and "aggregateRating" in jsonld:
            agg = jsonld["aggregateRating"]
            if isinstance(agg, dict):
                r_val = agg.get("ratingValue")
                if r_val:
                    try:
                        rating = float(r_val)
                    except ValueError:
                        pass

        if rating is None:
            rating_el = soup.select_one(".ux-summary__count .ux-textspans, .reviews-star-rating, .star-rating")
            if rating_el:
                rating = RatingReviewExtractor.extract_rating(rating_el.get_text(strip=True))

        review_count = 0
        if jsonld and "aggregateRating" in jsonld:
            agg = jsonld["aggregateRating"]
            if isinstance(agg, dict):
                rc_val = agg.get("reviewCount") or agg.get("ratingCount")
                if rc_val:
                    try:
                        review_count = int(rc_val)
                    except ValueError:
                        pass

        if review_count == 0:
            review_el = soup.select_one(".reviews-count, .ux-summary__count, .ebay-review-count")
            if review_el:
                review_count = RatingReviewExtractor.extract_count(review_el.get_text(strip=True))

        # 4. Sales Count ("1,234 sold", "12 sold in last 24 hours")
        sold_count = None
        raw_sold_text = None
        sold_el = soup.select_one(".x-quantity__availability .ux-textspans--BOLD, .d-quantity__availability, .vi-qtyS-hot-item")
        if sold_el:
            sold_count, raw_sold_text = SalesExtractor.extract_sales(sold_el.get_text(strip=True))

        # 5. Seller & Store Info
        seller_id, seller_name, seller_rating, seller_url = SellerExtractor.extract_seller_from_dom(soup, item_id)

        # 6. Description
        desc_el = soup.select_one("#viTabs_0_is, .d-item-description, iframe#desc_ifr")
        raw_desc = str(desc_el) if desc_el else None
        d_html, d_text = DescriptionExtractor.sanitize_html(raw_desc)

        # 7. Images
        primary_img, img_records = ImageExtractor.extract_gallery(soup)

        # 8. Category & Breadcrumbs
        cat_name, cat_path, breadcrumbs = CategoryExtractor.extract_from_breadcrumbs(soup)

        # 9. Specifications / Item Specifics
        specs: List[Specification] = []
        for item_spec in soup.select(".ux-layout-section-evo__item"):
            labels = item_spec.select(".ux-labels-values__labels .ux-textspans")
            values = item_spec.select(".ux-labels-values__values .ux-textspans")
            if labels and values:
                k = labels[0].get_text(strip=True).rstrip(":")
                v = values[0].get_text(strip=True)
                if k and v:
                    specs.append(Specification(key=k, value=v))

        # 10. Variants
        variants = VariantExtractor.extract_from_dom(soup)

        product = ProductIntelligence(
            product_id=item_id,
            marketplace=MarketplaceType.EBAY,
            source_url=response.url,
            canonical_url=canonical_url,
            title=title,
            description_text=d_text,
            description_html=d_html,
            price=price,
            original_price=orig_price,
            currency=currency,
            rating=rating,
            review_count=review_count,
            sold_count=sold_count,
            raw_sold_text=raw_sold_text,
            seller_id=seller_id,
            seller_name=seller_name,
            seller_rating=seller_rating,
            seller_url=seller_url,
            category_name=cat_name,
            category_path=cat_path,
            breadcrumbs=breadcrumbs,
            primary_image=primary_img,
            images=img_records,
            variants=variants,
            specifications=specs,
            reviews=[],
            extraction_warnings=warnings,
        )

        snapshot = HistoricalSnapshot(
            product_id=item_id,
            marketplace=MarketplaceType.EBAY,
            title=title,
            price=price,
            original_price=orig_price,
            discount=None,
            currency=currency,
            rating=rating,
            review_count=review_count,
            sold_count=sold_count,
            raw_sold_text=raw_sold_text,
            availability=True,
            seller_name=seller_name,
            primary_image=primary_img,
            image_urls=[img.url for img in img_records],
            source_url=canonical_url,
        )

        return IntelligenceExtractionResult(
            extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
            product_id=item_id,
            marketplace=MarketplaceType.EBAY,
            url=canonical_url,
            status=ExtractionStatus.SUCCESS,
            success=True,
            status_code=response.status_code,
            duration_ms=response.duration_ms,
            product=product,
            reviews=[],
            snapshot=snapshot,
            fields_extracted=["title", "price", "images", "seller", "specifications"],
            warnings=warnings,
        )
