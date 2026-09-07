"""Amazon product intelligence extractor."""

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


class AmazonIntelligenceExtractor(BaseMarketplaceExtractor):
    """Production-grade Amazon product intelligence extractor."""

    _AMAZON_DOMAINS = ["amazon.com", "amazon.co.uk", "amazon.de", "amazon.ca", "amazon.in", "amazon.co.jp"]

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.AMAZON

    def validate_url(self, url: str) -> bool:
        return any(d in url.lower() for d in self._AMAZON_DOMAINS)

    def extract_product_id(self, url: str) -> Optional[str]:
        # Extract 10-character alphanumeric ASIN
        m = re.search(r"/(?:dp|gp/product|d)/([A-Z0-9]{10})", url, re.IGNORECASE)
        if m:
            return m.group(1).upper()
        return None

    def extract_intelligence(self, response: CrawlResponse) -> IntelligenceExtractionResult:
        canonical_url = self.canonicalize_url(response.url)
        asin = self.extract_product_id(canonical_url) or str(uuid.uuid4())[:10].upper()
        warnings: List[str] = []
        errors: List[str] = []

        if response.status_code == 404:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=asin,
                marketplace=MarketplaceType.AMAZON,
                url=canonical_url,
                status=ExtractionStatus.NOT_FOUND,
                success=False,
                status_code=404,
                errors=["Amazon product listing not found (HTTP 404)"],
            )

        # Detect Amazon Robot Check / Captcha early
        if "Robot Check" in response.html or "images-amazon.com/captcha/" in response.html or "/errors/validateCaptcha" in response.html:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=asin,
                marketplace=MarketplaceType.AMAZON,
                url=canonical_url,
                status=ExtractionStatus.CHALLENGE,
                success=False,
                status_code=response.status_code,
                errors=["Amazon Bot Detection (Robot Check / CAPTCHA) encountered."],
                raw_payload=response.html,
            )

        soup = BeautifulSoup(response.html, "html.parser")
        jsonld = self.extract_jsonld(soup)

        # 1. Extract Title (JSON-LD -> DOM -> OpenGraph)
        title = None
        if jsonld:
            title = jsonld.get("name") or jsonld.get("title")

        if not title:
            title_el = soup.select_one("#productTitle, #title, h1.a-size-large, h1")
            if title_el:
                title = title_el.get_text(strip=True)

        if not title:
            og = self.extract_opengraph(soup)
            title = og.get("og:title") or og.get("title")

        if not title:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=asin,
                marketplace=MarketplaceType.AMAZON,
                url=canonical_url,
                status=ExtractionStatus.FAILED,
                success=False,
                status_code=response.status_code,
                errors=["Mandatory product title missing from Amazon listing"],
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
            price_el = soup.select_one(
                ".a-price .a-offscreen, #priceblock_ourprice, #priceblock_dealprice, #corePriceDisplay_desktop_feature_div .a-price-whole, #corePrice_desktop .a-offscreen, span[data-a-color='price']"
            )
            if price_el:
                p_text = price_el.get_text(strip=True)
                if "£" in p_text:
                    currency = "GBP"
                elif "€" in p_text:
                    currency = "EUR"
                elif "₹" in p_text:
                    currency = "INR"
                elif "¥" in p_text:
                    currency = "JPY"

                clean_p = re.sub(r"[^\d\.]", "", p_text)
                try:
                    price = float(clean_p)
                except ValueError:
                    pass

        # Strike-through list price
        strike_el = soup.select_one(".a-text-price .a-offscreen, #listPrice, #priceblock_listprice")
        if strike_el:
            clean_orig = re.sub(r"[^\d\.]", "", strike_el.get_text(strip=True))
            try:
                orig_price = float(clean_orig)
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
            rating_el = soup.select_one("#acrPopover .a-icon-alt, #averageCustomerReviews .a-icon-alt, .a-star-rating-5, span[data-hook='rating-out-of-text']")
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
            review_el = soup.select_one("#acrCustomerReviewText, #acrCustomerReviewLink, #reviews-medley-footer, span[data-hook='total-review-count']")
            if review_el:
                review_count = RatingReviewExtractor.extract_count(review_el.get_text(strip=True))

        # 4. Sales / Bought in past month
        sold_count = None
        raw_sold_text = None
        sales_el = soup.select_one("#social-proofing-faceout-title-tk_bought .a-text-bold, #social-proofing-faceout-title-tk_bought, .social-proofing-faceout-title")
        if sales_el:
            sold_count, raw_sold_text = SalesExtractor.extract_sales(sales_el.get_text(strip=True))

        # 4. Sales Volume (e.g. "50+ bought in past month")
        sold_count = None
        raw_sold_text = None
        bought_el = soup.select_one("#social-proofing-faceout-title-tk_bought, .social-proofing-faceout, .sales-volume")
        if bought_el:
            sold_count, raw_sold_text = SalesExtractor.extract_sales(bought_el.get_text(strip=True))

        # 5. Brand & Seller
        brand = None
        brand_el = soup.select_one("#bylineInfo, .po-brand .a-span9, #brand")
        if brand_el:
            brand_text = brand_el.get_text(strip=True)
            brand = re.sub(r"(?:Visit the|Brand:)\s*", "", brand_text, flags=re.IGNORECASE).strip()

        seller_id, seller_name, seller_rating, seller_url = SellerExtractor.extract_seller_from_dom(soup, asin)
        if not seller_name and brand:
            seller_name = brand

        # 6. Description & Bullets
        desc_parts = []
        bullets = soup.select("#feature-bullets li span.a-list-item")
        for b in bullets:
            b_text = b.get_text(strip=True)
            if b_text and not b_text.startswith("›"):
                desc_parts.append(b_text)

        desc_el = soup.select_one("#productDescription, #aplus")
        raw_html_desc = str(desc_el) if desc_el else None
        d_html, d_text = DescriptionExtractor.sanitize_html(raw_html_desc)

        if desc_parts:
            bullet_summary = "\n".join([f"• {p}" for p in desc_parts])
            description_text = f"{bullet_summary}\n\n{d_text}" if d_text else bullet_summary
        else:
            description_text = d_text

        # 7. Images
        primary_img, img_records = ImageExtractor.extract_gallery(soup)

        # 8. Category & Breadcrumbs
        cat_name, cat_path, breadcrumbs = CategoryExtractor.extract_from_breadcrumbs(soup)

        # 9. Specifications
        specs = SpecificationExtractor.extract_from_dom(soup)

        # 10. Variants
        variants = VariantExtractor.extract_from_dom(soup)

        # 11. Customer Reviews
        reviews: List[IntelligenceReview] = []
        for r_el in soup.select("#cm-cr-dp-review-list .review, .review[data-hook='review']"):
            r_title_el = r_el.select_one("[data-hook='review-title'], .review-title")
            r_title = r_title_el.get_text(strip=True) if r_title_el else None

            r_text_el = r_el.select_one("[data-hook='review-body'], .review-text")
            r_text = r_text_el.get_text(strip=True) if r_text_el else None

            r_date_el = r_el.select_one("[data-hook='review-date'], .review-date")
            r_date = r_date_el.get_text(strip=True) if r_date_el else None

            r_author_el = r_el.select_one(".a-profile-name")
            r_author = r_author_el.get_text(strip=True) if r_author_el else "Amazon Customer"

            r_rating = 5.0
            r_star_el = r_el.select_one("[data-hook='review-star-rating'] .a-icon-alt, .review-rating")
            if r_star_el:
                parsed_r = RatingReviewExtractor.extract_rating(r_star_el.get_text(strip=True))
                if parsed_r:
                    r_rating = parsed_r

            sentiment = SentimentType.POSITIVE if r_rating >= 4.0 else (SentimentType.NEGATIVE if r_rating <= 2.0 else SentimentType.NEUTRAL)
            sentiment_score = (r_rating - 3.0) / 2.0

            reviews.append(
                IntelligenceReview(
                    product_id=asin,
                    marketplace=MarketplaceType.AMAZON,
                    rating=r_rating,
                    review_title=r_title,
                    review_text=r_text,
                    reviewer_name=r_author,
                    raw_date_str=r_date,
                    sentiment=sentiment,
                    sentiment_score=sentiment_score,
                    is_negative=(r_rating <= 2.0),
                )
            )

        product = ProductIntelligence(
            product_id=asin,
            marketplace=MarketplaceType.AMAZON,
            source_url=response.url,
            canonical_url=canonical_url,
            title=title,
            description_text=description_text,
            description_html=d_html,
            price=price,
            original_price=orig_price,
            discount=round(((orig_price - price) / orig_price) * 100, 1) if orig_price and orig_price > price else None,
            currency=currency,
            rating=rating,
            review_count=review_count,
            sold_count=sold_count,
            raw_sold_text=raw_sold_text,
            brand=brand,
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
            extraction_warnings=warnings,
        )

        snapshot = HistoricalSnapshot(
            product_id=asin,
            marketplace=MarketplaceType.AMAZON,
            title=title,
            price=price,
            original_price=orig_price,
            discount=product.discount,
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
            product_id=asin,
            marketplace=MarketplaceType.AMAZON,
            url=canonical_url,
            status=ExtractionStatus.SUCCESS,
            success=True,
            status_code=response.status_code,
            duration_ms=response.duration_ms,
            product=product,
            reviews=reviews,
            snapshot=snapshot,
            fields_extracted=["title", "price", "rating", "review_count", "images", "brand", "seller"],
            warnings=warnings,
        )
