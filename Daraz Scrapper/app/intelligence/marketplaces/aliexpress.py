"""AliExpress product intelligence extractor."""

import json
import re
import uuid
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

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


class AliExpressIntelligenceExtractor(BaseMarketplaceExtractor):
    """Production-grade AliExpress product intelligence extractor."""

    _ALI_DOMAINS = ["aliexpress.com", "aliexpress.ru", "aliexpress.us"]

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.ALIEXPRESS

    def validate_url(self, url: str) -> bool:
        return any(d in url.lower() for d in self._ALI_DOMAINS)

    def extract_product_id(self, url: str) -> Optional[str]:
        # Extract numeric AliExpress Item ID
        m = re.search(r"/item/(\d+)\.html", url)
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
                marketplace=MarketplaceType.ALIEXPRESS,
                url=canonical_url,
                status=ExtractionStatus.NOT_FOUND,
                success=False,
                status_code=404,
                errors=["AliExpress product listing not found (HTTP 404)"],
            )

        soup = BeautifulSoup(response.html, "html.parser")

        # 1. Check for JSON-LD Structured Data
        jsonld = self.extract_jsonld(soup)

        # 2. Parse window.runParams embedded state
        run_params: Dict[str, Any] = {}
        m_run = re.search(r"window\.runParams\s*=\s*(\{.*?\});\s*(?:</script>|\n|var )", response.html, re.DOTALL)
        if m_run:
            try:
                run_params = json.loads(m_run.group(1))
            except Exception as e:
                warnings.append(f"Failed to parse window.runParams: {e}")

        # 3. Extract Title (JSON-LD -> runParams -> DOM -> OpenGraph)
        title = None
        if jsonld:
            title = jsonld.get("name") or jsonld.get("title")

        if not title and run_params:
            title = (
                run_params.get("data", {}).get("productInfoComponent", {}).get("subject")
                or run_params.get("productInfo", {}).get("subject")
                or run_params.get("data", {}).get("metaDataComponent", {}).get("title")
            )

        if not title:
            title_el = soup.select_one("h1[data-pl='product-title'], .product-title-text, h1.pdp-title, h1")
            if title_el:
                title = title_el.get_text(strip=True)

        if not title:
            og = self.extract_opengraph(soup)
            title = og.get("og:title") or og.get("title")

        # Reject generic non-product placeholder titles
        if title and title.strip().lower() in ("aliexpress", "aliexpress.com", "aliexpress.ru", "aliexpress.us", "welcome to aliexpress"):
            title = None

        if not title:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=item_id,
                marketplace=MarketplaceType.ALIEXPRESS,
                url=canonical_url,
                status=ExtractionStatus.FAILED,
                success=False,
                status_code=response.status_code,
                errors=["Mandatory product title missing from AliExpress listing or page is an empty stub"],
            )

        # 4. Extract Price & Currency (JSON-LD -> runParams -> DOM -> OpenGraph)
        price = 0.0
        orig_price = None
        currency = "USD"

        # JSON-LD offer
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

        # runParams priceComponent / skuModule
        if price == 0.0 and run_params:
            price_comp = run_params.get("data", {}).get("priceComponent", {}) or run_params.get("priceComponent", {})
            disc_p = (
                price_comp.get("discountPrice", {}).get("minAmount", {}).get("value")
                or price_comp.get("origPrice", {}).get("minAmount", {}).get("value")
            )
            if disc_p:
                try:
                    price = float(disc_p)
                except ValueError:
                    pass
            
            orig_p = price_comp.get("origPrice", {}).get("minAmount", {}).get("value")
            if orig_p:
                try:
                    orig_price = float(orig_p)
                except ValueError:
                    pass

            if price == 0.0:
                sku_module = run_params.get("data", {}).get("skuModule", {}) or run_params.get("skuModule", {})
                price_list = sku_module.get("priceList", [])
                if price_list and isinstance(price_list, list):
                    sku0 = price_list[0]
                    p_sku = (
                        sku0.get("skuVal", {}).get("actSkuCalPrice")
                        or sku0.get("skuVal", {}).get("skuCalPrice")
                        or sku0.get("skuVal", {}).get("skuAmount", {}).get("value")
                    )
                    if p_sku:
                        try:
                            price = float(p_sku)
                        except ValueError:
                            pass

        # DOM Price
        if price == 0.0:
            price_el = soup.select_one(".product-price-current, .pdp-comp-price, .uniform-banner-box-price, .product-price-value, span[class*='price']")
            if price_el:
                clean_p = re.sub(r"[^\d\.]", "", price_el.get_text(strip=True))
                try:
                    price = float(clean_p)
                except ValueError:
                    pass

        # 5. Rating & Reviews
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

        if rating is None and run_params:
            feed_comp = run_params.get("data", {}).get("feedbackComponent", {}) or run_params.get("feedbackComponent", {})
            r_avg = feed_comp.get("evarageStar") or feed_comp.get("averageStar")
            if r_avg:
                try:
                    rating = float(r_avg)
                except ValueError:
                    pass

        if rating is None:
            rating_el = soup.select_one(".overview-rating-average, .reviewer-info-average, .feedback-rating-score")
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

        if review_count == 0 and run_params:
            feed_comp = run_params.get("data", {}).get("feedbackComponent", {}) or run_params.get("feedbackComponent", {})
            rc_val = feed_comp.get("totalValidNum")
            if rc_val:
                try:
                    review_count = int(rc_val)
                except ValueError:
                    pass

        if review_count == 0:
            rev_el = soup.select_one(".reviewer-info-reviews, .product-reviewer-reviews, .feedback-rating-count")
            if rev_el:
                review_count = RatingReviewExtractor.extract_count(rev_el.get_text(strip=True))

        # 6. Sales / Orders volume
        sold_count = None
        raw_sold_text = None
        if run_params:
            trade_comp = run_params.get("data", {}).get("tradeComponent", {}) or run_params.get("tradeComponent", {})
            t_count = trade_comp.get("formatTradeCount")
            if t_count:
                sold_count, raw_sold_text = SalesExtractor.extract_sales(str(t_count))

        if sold_count is None:
            orders_el = soup.select_one(".reviewer-info-sold, .product-reviewer-sold, .order-num, .trade-num")
            if orders_el:
                sold_count, raw_sold_text = SalesExtractor.extract_sales(orders_el.get_text(strip=True))

        # 6. Seller & Store Info
        seller_id, seller_name, seller_rating, seller_url = SellerExtractor.extract_seller_from_dom(soup, item_id)

        # 7. Images
        primary_img, img_records = ImageExtractor.extract_gallery(soup)

        # 8. Category & Breadcrumbs
        cat_name, cat_path, breadcrumbs = CategoryExtractor.extract_from_breadcrumbs(soup)

        # 9. Specifications
        specs = SpecificationExtractor.extract_from_dom(soup)

        # 10. Variants
        variants = VariantExtractor.extract_from_dom(soup)

        product = ProductIntelligence(
            product_id=item_id,
            marketplace=MarketplaceType.ALIEXPRESS,
            source_url=response.url,
            canonical_url=canonical_url,
            title=title,
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
            source_fields={"has_runParams": bool(run_params)},
            extraction_warnings=warnings,
        )

        snapshot = HistoricalSnapshot(
            product_id=item_id,
            marketplace=MarketplaceType.ALIEXPRESS,
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
            marketplace=MarketplaceType.ALIEXPRESS,
            url=canonical_url,
            status=ExtractionStatus.SUCCESS,
            success=True,
            status_code=response.status_code,
            duration_ms=response.duration_ms,
            product=product,
            reviews=[],
            snapshot=snapshot,
            fields_extracted=["title", "price", "images", "seller", "orders"],
            warnings=warnings,
        )
