"""
ScrapeGraphAI Normalizer.

Transforms ScrapeGraphAI structured extraction output into TrendPulse AI's
canonical ProductIntelligence domain models with strict provenance tracking.
"""

import re
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.app.services.scraper.providers.scrapegraphai.schema import (
    ScrapeGraphProductItem, ScrapeGraphVariantItem, ScrapeGraphReviewItem
)

# Optional import of internal Scraper models
try:
    from app.crawling.models import MarketplaceType
    from app.intelligence.models.product import (
        ProductIntelligence, Variant, Specification, ImageRecord
    )
    from app.intelligence.models.review import IntelligenceReview
except ImportError:
    MarketplaceType = None
    ProductIntelligence = Any
    Variant = Any
    Specification = Any
    ImageRecord = Any
    IntelligenceReview = Any


class ScrapeGraphNormalizer:
    """
    Normalizes raw ScrapeGraphAI dictionaries or Pydantic items into canonical
    ProductIntelligence models, preserving source_provider provenance.
    """

    @staticmethod
    def _extract_product_id(url: Optional[str], raw_id: Optional[str]) -> str:
        if raw_id and str(raw_id).strip():
            # Clean non-alphanumeric except hyphen/underscore
            clean_id = re.sub(r"[^\w\-]", "", str(raw_id).strip())
            if clean_id:
                return clean_id

        if url:
            # Check for Daraz /product/-i12345.html
            daraz_match = re.search(r"-i(\d+)", url)
            if daraz_match:
                return f"daraz_{daraz_match.group(1)}"

            # Check for Amazon /dp/B00XYZ
            amz_match = re.search(r"/dp/([A-Z0-9]{10})", url)
            if amz_match:
                return f"amz_{amz_match.group(1)}"

            # Generic hash of url path
            url_slug = re.sub(r"[^\w\-]", "_", url.split("?")[0][-30:])
            if url_slug:
                return f"sg_{url_slug}"

        return f"sg_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _clean_price(val: Any) -> float:
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        # String cleanup
        clean_str = re.sub(r"[^\d.]", "", str(val))
        try:
            return float(clean_str) if clean_str else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _clean_currency(curr: Optional[str], marketplace: str) -> str:
        if curr and len(curr.strip()) == 3:
            return curr.strip().upper()
        m = marketplace.lower()
        if m == "daraz":
            return "PKR"
        return "USD"

    @classmethod
    def to_product_intelligence(
        cls,
        data: Any,
        marketplace: str = "daraz",
        source_url: Optional[str] = None
    ) -> ProductIntelligence:
        """
        Converts a ScrapeGraphProductItem or raw dict into ProductIntelligence.
        """
        d: Dict[str, Any] = data.model_dump() if hasattr(data, "model_dump") else (data if isinstance(data, dict) else {})

        raw_url = d.get("product_url") or source_url or ""
        prod_id = cls._extract_product_id(raw_url, d.get("product_id"))
        m_lower = marketplace.lower().strip()

        # Map MarketplaceType enum
        m_type = m_lower
        if MarketplaceType:
            mapping = {
                "daraz": getattr(MarketplaceType, "DARAZ", "daraz"),
                "amazon": getattr(MarketplaceType, "AMAZON", "amazon"),
                "ebay": getattr(MarketplaceType, "EBAY", "ebay"),
                "aliexpress": getattr(MarketplaceType, "ALIEXPRESS", "aliexpress"),
                "shopify": getattr(MarketplaceType, "SHOPIFY", "shopify")
            }
            m_type = mapping.get(m_lower, getattr(MarketplaceType, "DARAZ", "daraz"))

        title = str(d.get("title") or "Scraped Product").strip()
        price = cls._clean_price(d.get("price"))
        orig_price = cls._clean_price(d.get("original_price"))
        if orig_price <= 0:
            orig_price = price

        discount = cls._clean_price(d.get("discount"))
        if discount <= 0 and orig_price > price > 0:
            discount = round(((orig_price - price) / orig_price) * 100, 1)

        currency = cls._clean_currency(d.get("currency"), m_lower)

        raw_rating = d.get("rating")
        rating = float(raw_rating) if raw_rating is not None and 0.0 <= float(raw_rating) <= 5.0 else None

        review_count = int(d.get("review_count") or 0)
        availability = bool(d.get("availability", True))

        brand = d.get("brand") or "Generic"
        seller_name = d.get("seller_name") or f"{marketplace.capitalize()} Merchant"
        seller_id = f"seller_{re.sub(r'[^a-zA-Z0-9]', '', seller_name).lower()[:12]}"
        raw_seller_rating = d.get("seller_rating")
        seller_rating = float(raw_seller_rating) if raw_seller_rating is not None and 0.0 <= float(raw_seller_rating) <= 5.0 else None

        category = d.get("category") or "General"

        # Images
        image_url = d.get("image_url")
        images_raw = d.get("images") or []
        if isinstance(images_raw, str):
            images_raw = [images_raw]
        images_list = []
        for img in images_raw:
            if img:
                images_list.append(ImageRecord(url=str(img), is_primary=(str(img) == str(image_url))))
        if not images_list and image_url:
            images_list.append(ImageRecord(url=str(image_url), is_primary=True))

        primary_img = image_url or (images_list[0].url if images_list else None)

        # Specifications
        specs_raw = d.get("specifications") or {}
        specs_list = []
        if isinstance(specs_raw, dict):
            for k, v in specs_raw.items():
                specs_list.append(Specification(key=str(k), value=str(v)))
        elif isinstance(specs_raw, list):
            for item in specs_raw:
                if isinstance(item, dict) and "key" in item:
                    specs_list.append(Specification(key=str(item["key"]), value=str(item.get("value", ""))))

        # Variants
        variants_raw = d.get("variants") or []
        variants_list = []
        for v in variants_raw:
            if isinstance(v, dict):
                v_name = v.get("name") or "Standard"
                v_sku = v.get("sku_id") or f"var_{uuid.uuid4().hex[:6]}"
                v_price = cls._clean_price(v.get("price")) or price
                variants_list.append(Variant(sku_id=v_sku, name=v_name, price=v_price))

        # Reviews
        reviews_raw = d.get("reviews") or []
        reviews_list = []
        for r in reviews_raw:
            if isinstance(r, dict):
                r_rating = float(r.get("rating")) if r.get("rating") is not None and 0.0 <= float(r.get("rating")) <= 5.0 else 5.0
                reviews_list.append(IntelligenceReview(
                    review_id=r.get("review_id") or f"rev_{uuid.uuid4().hex[:8]}",
                    product_id=prod_id,
                    marketplace=m_type,
                    reviewer_name=r.get("reviewer_name") or "Customer",
                    rating=r_rating,
                    review_text=r.get("review_text") or "",
                    raw_date_str=r.get("date") or "",
                    review_variants=r.get("variation") or "",
                    verified_purchase=bool(r.get("verified_purchase", False)),
                    review_images=r.get("images") or []
                ))

        source_fields: Dict[str, Any] = {
            "brand": brand,
            "seller_metrics": d.get("seller_metrics") or {},
            "source_provider": "scrapegraphai",
            "challenge_status": "clear",
            "extraction_engine": "SmartScraperGraph"
        }

        field_conf = {
            "title": 1.0 if title and title != "Scraped Product" else 0.0,
            "price": 1.0 if price > 0 else 0.0,
            "seller": 0.9 if d.get("seller_name") else 0.5,
            "image": 1.0 if primary_img else 0.0,
        }
        overall_conf = round(sum(field_conf.values()) / len(field_conf), 2)

        return ProductIntelligence(
            product_id=prod_id,
            marketplace=m_type,
            source_url=raw_url,
            canonical_url=raw_url,
            title=title,
            description_text=d.get("description") or "",
            price=price,
            original_price=orig_price,
            discount=discount,
            currency=currency,
            rating=rating,
            review_count=review_count,
            sold_count=None,
            seller_name=seller_name,
            seller_id=seller_id,
            seller_rating=seller_rating,
            seller_url=None,
            category_name=category,
            category_path=category,
            primary_image=primary_img,
            images=images_list,
            specifications=specs_list,
            variants=variants_list,
            reviews=reviews_list,
            raw_data=json.dumps(d, ensure_ascii=False),
            availability=availability,
            source_fields=source_fields,
            extraction_confidence=field_conf,
            overall_confidence=overall_conf
        )
