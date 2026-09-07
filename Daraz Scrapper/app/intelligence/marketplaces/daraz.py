"""Daraz product intelligence extractor."""

import json
import re
import uuid
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from app.core.constants import SentimentType
from app.crawling.models import CrawlResponse, MarketplaceType
from app.discovery.normalizer import extract_product_id, normalize_url
from app.extraction.parser import ProductParser
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
from app.intelligence.models.result import ExtractionStatus, FieldConfidence, IntelligenceExtractionResult
from app.intelligence.models.review import IntelligenceReview
from app.intelligence.models.snapshot import HistoricalSnapshot


class DarazIntelligenceExtractor(BaseMarketplaceExtractor):
    """Production-grade Daraz product intelligence extractor."""

    _DARAZ_DOMAINS = ["daraz.pk", "daraz.com.bd", "daraz.lk", "daraz.com.np", "daraz.com.mm"]

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.DARAZ

    def validate_url(self, url: str) -> bool:
        return any(d in url.lower() for d in self._DARAZ_DOMAINS)

    def extract_product_id(self, url: str) -> Optional[str]:
        return extract_product_id(url)

    def extract_intelligence(self, response: CrawlResponse) -> IntelligenceExtractionResult:
        canonical_url = normalize_url(response.url)
        prod_id = self.extract_product_id(canonical_url) or str(uuid.uuid4())[:8]
        warnings: List[str] = []
        errors: List[str] = []

        if response.status_code == 404:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=prod_id,
                marketplace=MarketplaceType.DARAZ,
                url=canonical_url,
                status=ExtractionStatus.NOT_FOUND,
                success=False,
                status_code=404,
                errors=["Product not found (HTTP 404)"],
            )

        soup = BeautifulSoup(response.html, "html.parser")
        
        # 1. Check for JSON-LD Structured Data
        jsonld = self.extract_jsonld(soup)
        
        # 2. Check for window.pageData embedded JSON state
        page_data: Dict[str, Any] = {}
        m = re.search(r"window\.pageData\s*=\s*(\{.*?\});\s*(?:</script>|\n|var )", response.html, re.DOTALL)
        if m:
            try:
                page_data = json.loads(m.group(1))
            except Exception as e:
                warnings.append(f"Failed to parse window.pageData: {e}")

        # 3. Extract Title (JSON-LD -> pageData -> DOM -> OpenGraph)
        title = None
        if jsonld:
            title = jsonld.get("name") or jsonld.get("title")

        if not title and page_data:
            fields = page_data.get("mods", {}).get("fields", {})
            title = fields.get("title") or page_data.get("product", {}).get("title")

        if not title:
            title_tag = soup.select_one(".pdp-mod-product-badge-title, h1.pdp-product-title, h1")
            if title_tag:
                title = title_tag.get_text(strip=True)

        if not title:
            og = self.extract_opengraph(soup)
            title = og.get("og:title") or og.get("title")

        if not title:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=prod_id,
                marketplace=MarketplaceType.DARAZ,
                url=canonical_url,
                status=ExtractionStatus.FAILED,
                success=False,
                status_code=response.status_code,
                errors=["Mandatory product title missing from Daraz page"],
            )

        # 4. Extract Pricing & Currency (JSON-LD -> pageData -> DOM)
        price = 0.0
        original_price = None
        currency = "PKR"
        
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

        if price == 0.0 and page_data:
            fields = page_data.get("mods", {}).get("fields", {})
            sku_infos = fields.get("skuInfos", [])
            if sku_infos and isinstance(sku_infos, list):
                s0 = sku_infos[0]
                sale_p = s0.get("price", {}).get("salePrice", {}).get("value")
                orig_p = s0.get("price", {}).get("originalPrice", {}).get("value")
                if sale_p:
                    try:
                        price = float(sale_p)
                    except ValueError:
                        pass
                if orig_p:
                    try:
                        original_price = float(orig_p)
                    except ValueError:
                        pass

        if price == 0.0:
            price_tag = soup.select_one(".pdp-price, .pdp-product-price, .notranslate.pdp-price")
            if price_tag:
                price_text = price_tag.get_text(strip=True)
                # detect currency
                if "Rs." in price_text or "PKR" in price_text:
                    currency = "PKR"
                elif "৳" in price_text or "BDT" in price_text:
                    currency = "BDT"
                elif "Rs" in price_text or "LKR" in price_text:
                    currency = "LKR"

                m_price = re.search(r"(\d[\d,]*(?:\.\d+)?)", price_text.replace("Rs.", "").replace("Rs", "").replace("PKR", "").strip())
                if m_price:
                    try:
                        price = float(m_price.group(1).replace(",", ""))
                    except ValueError:
                        pass

        if original_price is None:
            orig_tag = soup.select_one(".pdp-price_type_deleted, .pdp-price_type_original")
            if orig_tag:
                orig_text = orig_tag.get_text(strip=True)
                m_orig = re.search(r"(\d[\d,]*(?:\.\d+)?)", orig_text.replace("Rs.", "").replace("Rs", "").replace("PKR", "").strip())
                if m_orig:
                    try:
                        original_price = float(m_orig.group(1).replace(",", ""))
                    except ValueError:
                        pass

        # 5. Extract Engagement, Rating, Review Count, Sales
        rating_score = None
        if jsonld and "aggregateRating" in jsonld:
            agg = jsonld["aggregateRating"]
            if isinstance(agg, dict):
                r_val = agg.get("ratingValue")
                if r_val:
                    try:
                        rating_score = float(r_val)
                    except ValueError:
                        pass

        if rating_score is None:
            rating_tag = soup.select_one(".score .score-average, .pdp-review-summary__score")
            if rating_tag:
                rating_score = RatingReviewExtractor.extract_rating(rating_tag.get_text(strip=True))

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
            review_count_tag = soup.select_one(".pdp-review-summary__link, .count, .rate-num")
            if review_count_tag:
                review_count = RatingReviewExtractor.extract_count(review_count_tag.get_text(strip=True))

        # Sales Extraction
        sold_count = None
        raw_sold_text = None
        sold_tag = soup.select_one(".pdp-mod-product-badge-sub .sold-count, .pdp-seller-badge-sold, .sold-info, .sold-count")
        if sold_tag:
            sold_count, raw_sold_text = SalesExtractor.extract_sales(sold_tag.get_text(strip=True))

        # 5. Extract Images
        primary_img, img_records = ImageExtractor.extract_gallery(soup)

        # 6. Extract Descriptions
        desc_tag = soup.select_one(".pdp-product-desc, .detail-desc-module, .pdp-description")
        desc_html, desc_text = DescriptionExtractor.sanitize_html(str(desc_tag) if desc_tag else None)

        # 7. Extract Seller Information
        seller_id, seller_name, seller_rating, seller_url = SellerExtractor.extract_seller_from_dom(soup, prod_id)

        # 8. Extract Category Breadcrumbs
        cat_name, cat_path, breadcrumbs = CategoryExtractor.extract_from_breadcrumbs(soup)

        # 9. Extract Specifications
        specs = SpecificationExtractor.extract_from_dom(soup)

        # 10. Extract Variants
        variants = VariantExtractor.extract_from_dom(soup)

        # 11. Extract Customer Reviews
        reviews: List[IntelligenceReview] = []
        for item in soup.select(".item, .review-item, .pdp-review-item"):
            r_text_el = item.select_one(".item-content, .content, .review-content")
            r_text = r_text_el.get_text(strip=True) if r_text_el else None
            
            r_author_el = item.select_one(".user-name, .author, .reviewer-name")
            r_author = r_author_el.get_text(strip=True) if r_author_el else "Daraz Customer"
            
            r_date_el = item.select_one(".date, .review-date, .time")
            r_date_raw = r_date_el.get_text(strip=True) if r_date_el else None
            
            # Star rating
            r_stars = 5.0
            stars_el = item.select(".star-icon, .icon-star, .star")
            if stars_el:
                r_stars = float(len(stars_el))

            # Review images
            r_images = [
                img.get("src") for img in item.select("img")
                if img.get("src") and not img.get("src", "").endswith(".svg")
            ]

            sentiment = SentimentType.POSITIVE if r_stars >= 4.0 else (SentimentType.NEGATIVE if r_stars <= 2.0 else SentimentType.NEUTRAL)
            sentiment_score = (r_stars - 3.0) / 2.0

            reviews.append(
                IntelligenceReview(
                    product_id=prod_id,
                    marketplace=MarketplaceType.DARAZ,
                    rating=r_stars,
                    review_text=r_text,
                    reviewer_name=r_author,
                    raw_date_str=r_date_raw,
                    review_images=[img for img in r_images if img],
                    sentiment=sentiment,
                    sentiment_score=sentiment_score,
                    is_negative=(r_stars <= 2.0),
                )
            )

        product = ProductIntelligence(
            product_id=prod_id,
            marketplace=MarketplaceType.DARAZ,
            source_url=response.url,
            canonical_url=canonical_url,
            title=title,
            description_text=desc_text,
            description_html=desc_html,
            price=price,
            original_price=original_price,
            discount=round(((original_price - price) / original_price) * 100, 1) if original_price and original_price > price else None,
            currency=currency,
            rating=rating_score,
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
            reviews=reviews,
            source_fields={"has_window_pageData": bool(page_data)},
            extraction_warnings=warnings,
        )

        snapshot = HistoricalSnapshot(
            product_id=prod_id,
            marketplace=MarketplaceType.DARAZ,
            title=title,
            price=price,
            original_price=original_price,
            discount=product.discount,
            currency=currency,
            rating=rating_score,
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
            product_id=prod_id,
            marketplace=MarketplaceType.DARAZ,
            url=canonical_url,
            status=ExtractionStatus.SUCCESS,
            success=True,
            status_code=response.status_code,
            duration_ms=response.duration_ms,
            product=product,
            reviews=reviews,
            snapshot=snapshot,
            fields_extracted=["title", "price", "images", "rating", "review_count", "seller"],
            warnings=warnings,
        )
