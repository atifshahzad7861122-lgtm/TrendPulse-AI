"""Central product parser orchestrating all domain extractors and evaluating extraction quality."""

import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from app.core.exceptions import ParserError
from app.discovery.normalizer import extract_product_id, normalize_url
from app.extraction.confidence import ConfidenceCalculator, ExtractionSource, FieldConfidenceScore
from app.extraction.config import DarazExtractionConfig, default_extraction_config
from app.extraction.extractors import (
    AvailabilityExtractor,
    CategoryExtractor,
    DescriptionExtractor,
    ImageExtractor,
    PriceExtractor,
    RatingExtractor,
    SalesExtractor,
    SellerExtractor,
    SpecificationExtractor,
    TitleExtractor,
    VariantExtractor,
)
from app.extraction.models import ExtractionResult
from app.extraction.raw_data import RawDataRecord
from app.extraction.validator import ProductExtractionValidator
from app.models.image import Image
from app.models.product import Product


class ProductParser:
    """Combines DOM parsing, JSON-LD, and embedded page state to produce validated Product models."""

    BRAND_SELECTORS = [
        ".pdp-product-brand__brand-link",
        ".pdp-link_color_blue",
        ".pdp-product-brand a",
        "a[data-qa-locator='product-brand']",
        ".pdp-product-brand",
    ]

    def __init__(self, config: Optional[DarazExtractionConfig] = None):
        self.config = config or default_extraction_config
        self.title_extractor = TitleExtractor()
        self.price_extractor = PriceExtractor()
        self.image_extractor = ImageExtractor()
        self.rating_extractor = RatingExtractor()
        self.sales_extractor = SalesExtractor()
        self.seller_extractor = SellerExtractor()
        self.category_extractor = CategoryExtractor()
        self.variant_extractor = VariantExtractor()
        self.specification_extractor = SpecificationExtractor()
        self.description_extractor = DescriptionExtractor()
        self.availability_extractor = AvailabilityExtractor()

    def _extract_embedded_json(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract JavaScript state dictionaries like pageData, appData, or __INITIAL_STATE__."""
        scripts = soup.find_all("script")
        for script in scripts:
            content = script.string or script.text or ""
            if not content:
                continue

            match = re.search(
                r"(?:window\.)?(?:pageData|appData|__INITIAL_STATE__|__app_data__)\s*=\s*(\{.*?\});",
                content,
                re.DOTALL,
            )
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass

            if "__ICE_APP_CONTEXT__" in content:
                m_ice = re.search(r"__ICE_APP_CONTEXT__\s*=\s*(\{.*?\});", content, re.DOTALL)
                if m_ice:
                    try:
                        data = json.loads(m_ice.group(1))
                        if isinstance(data, dict):
                            app_data = data.get("appData")
                            if isinstance(app_data, dict):
                                return app_data
                    except Exception:
                        pass

        return None

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract Schema.org Product JSON-LD block."""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or script.text or "")
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") in ("Product", "http://schema.org/Product"):
                            return item
                elif isinstance(data, dict):
                    if data.get("@type") in ("Product", "http://schema.org/Product"):
                        return data
                    if "@graph" in data and isinstance(data["@graph"], list):
                        for item in data["@graph"]:
                            if isinstance(item, dict) and item.get("@type") in ("Product", "http://schema.org/Product"):
                                return item
            except Exception:
                continue
        return None

    def _extract_brand(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
        json_ld: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Extract product brand name."""
        if raw_json:
            fields = raw_json.get("fields", raw_json)
            if isinstance(fields, dict):
                prod = fields.get("product") if isinstance(fields.get("product"), dict) else {}
                brand_obj = prod.get("brand") or fields.get("brand")
                if isinstance(brand_obj, dict):
                    brand_val = brand_obj.get("name")
                else:
                    brand_val = brand_obj

                if brand_val and str(brand_val).strip() and str(brand_val).lower() != "no brand":
                    return str(brand_val).strip()

        if json_ld:
            brand_val = json_ld.get("brand", {}).get("name") if isinstance(json_ld.get("brand"), dict) else json_ld.get("brand")
            if brand_val and str(brand_val).strip() and str(brand_val).lower() != "no brand":
                return str(brand_val).strip()

        for sel in self.BRAND_SELECTORS:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                txt = el.get_text(strip=True)
                if txt and txt.lower() != "no brand":
                    return txt

        return None

    def parse(
        self,
        html_content: str,
        url: str,
        product_id: Optional[str] = None,
        source_engine: str = "http",
    ) -> ExtractionResult:
        """
        Parse raw HTML content into a validated Product instance wrapped in ExtractionResult.
        """
        start_time = time.perf_counter()

        if not html_content or not html_content.strip():
            raise ParserError("Empty HTML content provided for product parsing", details={"url": url})

        soup = BeautifulSoup(html_content, "html.parser")
        raw_json = self._extract_embedded_json(soup)
        json_ld = self._extract_json_ld(soup)

        canonical_url = normalize_url(url)
        extracted_id = product_id or extract_product_id(canonical_url)

        if not extracted_id and raw_json:
            extracted_id = str(
                raw_json.get("fields", {}).get("skuInfos", {}).get("itemId")
                or raw_json.get("itemId")
                or ""
            ) or None

        if not extracted_id and json_ld:
            extracted_id = str(json_ld.get("sku") or json_ld.get("productID") or "") or None

        if not extracted_id:
            raise ParserError(f"Unable to extract product ID from URL or page data: {url}", details={"url": url})

        field_confidence: Dict[str, FieldConfidenceScore] = {}
        fields_extracted: List[str] = []
        fields_missing: List[str] = []

        # 1. Product ID
        fields_extracted.append("product_id")

        # 2. Title
        title, t_source = self.title_extractor.extract(soup, raw_json=raw_json, json_ld=json_ld)
        field_confidence["title"] = ConfidenceCalculator.score_field("title", t_source, bool(title))
        if title:
            fields_extracted.append("title")
        else:
            fields_missing.append("title")

        if not title:
            raise ParserError(f"Missing required title on page: {url}", details={"url": url})

        # 3. Price
        price, orig_price, discount, currency = self.price_extractor.extract(
            soup, raw_json=raw_json, json_ld=json_ld
        )
        p_source = ExtractionSource.STRUCTURED_DATA if raw_json else (ExtractionSource.JSON_LD if json_ld else ExtractionSource.DOM)
        field_confidence["price"] = ConfidenceCalculator.score_field("price", p_source, price is not None)
        if price is not None:
            fields_extracted.append("price")
        else:
            fields_missing.append("price")

        # 4. Images
        image_objects = self.image_extractor.extract(
            soup,
            raw_json=raw_json,
            json_ld=json_ld,
            product_id=extracted_id,
            prefer_high_res=self.config.prefer_high_res_images,
            max_images=self.config.max_gallery_images,
        )
        img_source = ExtractionSource.STRUCTURED_DATA if raw_json else (ExtractionSource.JSON_LD if json_ld else ExtractionSource.DOM)
        field_confidence["images"] = ConfidenceCalculator.score_field("images", img_source, len(image_objects) > 0)
        if image_objects:
            fields_extracted.append("images")
        else:
            fields_missing.append("images")

        # 5. Rating & Reviews
        rating, review_count = self.rating_extractor.extract(soup, raw_json=raw_json, json_ld=json_ld)
        r_source = ExtractionSource.STRUCTURED_DATA if raw_json else (ExtractionSource.JSON_LD if json_ld else ExtractionSource.DOM)
        field_confidence["rating"] = ConfidenceCalculator.score_field("rating", r_source, rating is not None)
        if rating is not None:
            fields_extracted.append("rating")
        else:
            fields_missing.append("rating")

        if review_count is not None:
            fields_extracted.append("review_count")
        else:
            fields_missing.append("review_count")

        # 6. Sales Count
        sold_count = self.sales_extractor.extract(soup, raw_json=raw_json)
        s_source = ExtractionSource.STRUCTURED_DATA if raw_json else ExtractionSource.DOM
        field_confidence["sold_count"] = ConfidenceCalculator.score_field("sold_count", s_source, sold_count is not None)
        if sold_count is not None:
            fields_extracted.append("sold_count")
        else:
            fields_missing.append("sold_count")

        # 7. Brand
        brand = self._extract_brand(soup, raw_json=raw_json, json_ld=json_ld)
        if brand:
            fields_extracted.append("brand")
        else:
            fields_missing.append("brand")

        # 8. Seller
        seller_id, seller_name, seller_rating = self.seller_extractor.extract(soup, raw_json=raw_json)
        sel_source = ExtractionSource.STRUCTURED_DATA if raw_json else ExtractionSource.DOM
        field_confidence["seller"] = ConfidenceCalculator.score_field("seller", sel_source, bool(seller_name))
        if seller_name:
            fields_extracted.append("seller")
        else:
            fields_missing.append("seller")

        # 9. Category
        category_id, category_name = self.category_extractor.extract(soup, raw_json=raw_json)
        cat_source = ExtractionSource.STRUCTURED_DATA if raw_json else ExtractionSource.DOM
        field_confidence["category"] = ConfidenceCalculator.score_field("category", cat_source, bool(category_name))
        if category_name:
            fields_extracted.append("category")
        else:
            fields_missing.append("category")

        # 10. Description
        desc_text = self.description_extractor.extract(soup, raw_json=raw_json, json_ld=json_ld)
        d_source = ExtractionSource.STRUCTURED_DATA if raw_json else (ExtractionSource.JSON_LD if json_ld else ExtractionSource.DOM)
        field_confidence["description"] = ConfidenceCalculator.score_field(
            "description", d_source, bool(desc_text)
        )
        if desc_text:
            fields_extracted.append("description")
        else:
            fields_missing.append("description")

        # 11. Variants
        variants_raw, _ = self.variant_extractor.extract(soup, raw_json=raw_json)
        variants_dicts = [v.model_dump() if hasattr(v, "model_dump") else dict(v) for v in variants_raw]
        if variants_dicts:
            fields_extracted.append("variants")
        else:
            fields_missing.append("variants")

        # 12. Specifications
        specifications = self.specification_extractor.extract(soup, raw_json=raw_json)
        field_confidence["specifications"] = ConfidenceCalculator.score_field(
            "specifications", ExtractionSource.DOM, len(specifications) > 0
        )
        if specifications:
            fields_extracted.append("specifications")
        else:
            fields_missing.append("specifications")

        # 13. Availability
        in_stock, stock_status, _ = self.availability_extractor.extract(soup, raw_json=raw_json, json_ld=json_ld)
        fields_extracted.append("availability")

        # Calculate Overall Weighted Confidence
        overall_confidence = ConfidenceCalculator.calculate_overall_confidence(
            field_confidence,
            field_weights=self.config.field_weights,
        )

        now = datetime.now(timezone.utc)
        product = Product(
            product_id=extracted_id,
            title=title,
            description=desc_text,
            url=canonical_url,
            price=price or 0.0,
            original_price=orig_price,
            discount=discount,
            currency=currency,
            rating=rating,
            review_count=review_count or 0,
            sold_count=sold_count,
            brand=brand,
            seller_id=seller_id,
            seller_name=seller_name,
            category_id=category_id,
            category_name=category_name,
            availability=in_stock,
            images=image_objects,
            variants=variants_dicts,
            specifications=specifications,
            created_at=now,
            updated_at=now,
            first_seen_at=now,
            last_seen_at=now,
        )

        # Quality Validation Gate
        validation_report = ProductExtractionValidator.validate_product(
            product=product,
            overall_confidence=overall_confidence,
            min_confidence_threshold=self.config.min_overall_confidence,
        )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Raw Data Record
        raw_data = RawDataRecord(
            product_id=extracted_id,
            url=canonical_url,
            structured_json=raw_json,
            json_ld=json_ld,
            html_snapshot_length=len(html_content),
            extraction_source=source_engine,
        )

        return ExtractionResult(
            product=product,
            success=validation_report.is_valid,
            validation_status=validation_report.status,
            validation_report=validation_report,
            overall_confidence=overall_confidence,
            field_confidence=field_confidence,
            raw_data=raw_data,
            warnings=validation_report.warnings,
            errors=validation_report.errors,
            fields_extracted=fields_extracted,
            fields_missing=fields_missing,
            extraction_duration_ms=duration_ms,
            source_engine=source_engine,
        )
