"""Shopify product intelligence extractor."""

import json
import re
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
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


class ShopifyIntelligenceExtractor(BaseMarketplaceExtractor):
    """Production-grade Shopify store product intelligence extractor."""

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.SHOPIFY

    def validate_url(self, url: str) -> bool:
        u_low = url.lower()
        return "myshopify.com" in u_low or "/products/" in u_low

    def extract_product_id(self, url: str) -> Optional[str]:
        # Extract product handle / slug from /products/<handle>
        m = re.search(r"/products/([a-zA-Z0-9_\-]+)(?:\.json|\.html)?", url)
        if m:
            return m.group(1)
        return None

    def extract_intelligence(self, response: CrawlResponse) -> IntelligenceExtractionResult:
        canonical_url = self.canonicalize_url(response.url)
        handle = self.extract_product_id(canonical_url) or str(uuid.uuid4())[:10]
        warnings: List[str] = []
        errors: List[str] = []

        if response.status_code == 404:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=handle,
                marketplace=MarketplaceType.SHOPIFY,
                url=canonical_url,
                status=ExtractionStatus.NOT_FOUND,
                success=False,
                status_code=404,
                errors=["Shopify product listing not found (HTTP 404)"],
            )

        # 1. Check if raw JSON response from .json endpoint
        if response.html.strip().startswith("{") and ("product" in response.html or "products" in response.html):
            try:
                data = json.loads(response.html)
                prod_data = data.get("product") or (data.get("products", [{}])[0] if isinstance(data.get("products"), list) else data)
                
                title = prod_data.get("title")
                vendor = prod_data.get("vendor")
                body_html = prod_data.get("body_html", "")
                d_html, d_text = DescriptionExtractor.sanitize_html(body_html)

                # Variants
                variants: List[Variant] = []
                price = 0.0
                orig_price = None

                for v in prod_data.get("variants", []):
                    v_p = float(v.get("price", 0.0))
                    v_comp = float(v.get("compare_at_price")) if v.get("compare_at_price") else None
                    if not price and v_p > 0:
                        price = v_p
                        orig_price = v_comp

                    variants.append(
                        Variant(
                            sku_id=str(v.get("id") or ""),
                            name=str(v.get("title") or "Default"),
                            price=v_p,
                            original_price=v_comp,
                            available=bool(v.get("available", True)),
                        )
                    )

                # Images
                img_records: List[ImageRecord] = []
                primary_img = None
                for idx, img in enumerate(prod_data.get("images", [])):
                    src = img.get("src") if isinstance(img, dict) else img
                    if src:
                        if idx == 0:
                            primary_img = src
                        img_records.append(ImageRecord(url=src, position=idx, is_primary=(idx == 0)))

                product = ProductIntelligence(
                    product_id=str(prod_data.get("id") or handle),
                    marketplace=MarketplaceType.SHOPIFY,
                    source_url=response.url,
                    canonical_url=canonical_url,
                    title=title or "Shopify Product",
                    description_text=d_text,
                    description_html=d_html,
                    price=price,
                    original_price=orig_price,
                    discount=round(((orig_price - price) / orig_price) * 100, 1) if orig_price and orig_price > price else None,
                    currency="USD",
                    seller_name=vendor,
                    primary_image=primary_img,
                    images=img_records,
                    variants=variants,
                    specifications=[],
                    reviews=[],
                    source_fields={"format": "shopify_json_endpoint"},
                )

                snapshot = HistoricalSnapshot(
                    product_id=str(prod_data.get("id") or handle),
                    marketplace=MarketplaceType.SHOPIFY,
                    title=title or "Shopify Product",
                    price=price,
                    original_price=orig_price,
                    discount=product.discount,
                    currency="USD",
                    availability=True,
                    seller_name=vendor,
                    primary_image=primary_img,
                    image_urls=[img.url for img in img_records],
                    source_url=canonical_url,
                )

                return IntelligenceExtractionResult(
                    extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                    product_id=handle,
                    marketplace=MarketplaceType.SHOPIFY,
                    url=canonical_url,
                    status=ExtractionStatus.SUCCESS,
                    success=True,
                    status_code=response.status_code,
                    duration_ms=response.duration_ms,
                    product=product,
                    reviews=[],
                    snapshot=snapshot,
                    fields_extracted=["title", "price", "variants", "images", "vendor"],
                )
            except Exception as e:
                warnings.append(f"Shopify JSON parsing fallback to DOM: {e}")

        # 2. HTML DOM & JSON-LD parsing
        soup = BeautifulSoup(response.html, "html.parser")
        
        # Check JSON-LD
        json_lds = self.extract_json_ld(soup)
        title, price, orig_price, currency = None, 0.0, None, "USD"
        vendor = None

        for jld in json_lds:
            if jld.get("@type") == "Product":
                title = jld.get("name")
                offers = jld.get("offers", {})
                if isinstance(offers, dict):
                    price = float(offers.get("price", 0.0))
                    currency = offers.get("priceCurrency", "USD")
                elif isinstance(offers, list) and offers:
                    price = float(offers[0].get("price", 0.0))
                    currency = offers[0].get("priceCurrency", "USD")
                brand_info = jld.get("brand")
                if isinstance(brand_info, dict):
                    vendor = brand_info.get("name")
                elif isinstance(brand_info, str):
                    vendor = brand_info
                break

        # Check Shopify embedded meta script
        if not title:
            m_meta = re.search(r"var\s+meta\s*=\s*(\{.*?\});", response.html)
            if m_meta:
                try:
                    s_meta = json.loads(m_meta.group(1))
                    p_meta = s_meta.get("product", {})
                    title = p_meta.get("title") or title
                    vendor = p_meta.get("vendor") or vendor
                    v_list = p_meta.get("variants", [])
                    if v_list and price == 0.0:
                        raw_p = float(v_list[0].get("price", 0.0))
                        price = raw_p / 100.0 if raw_p > 1000 else raw_p
                except Exception:
                    pass

        if not title:
            title_el = soup.select_one("h1.product__title, h1.product-single__title, h1.pdp-title, h1")
            if title_el:
                title = title_el.get_text(strip=True)

        if not title:
            og = self.extract_opengraph(soup)
            title = og.get("og:title") or og.get("title")

        if not title:
            return IntelligenceExtractionResult(
                extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                product_id=handle,
                marketplace=MarketplaceType.SHOPIFY,
                url=canonical_url,
                status=ExtractionStatus.FAILED,
                success=False,
                status_code=response.status_code,
                errors=["Mandatory product title missing from Shopify listing"],
            )

        # Price fallback from DOM
        if price == 0.0:
            price_el = soup.select_one(".price-item--regular, .product__price, span.price")
            if price_el:
                clean_p = re.sub(r"[^\d\.]", "", price_el.get_text(strip=True))
                try:
                    price = float(clean_p)
                except ValueError:
                    pass

        # Images & Description
        primary_img, img_records = ImageExtractor.extract_gallery(soup)
        desc_el = soup.select_one(".product__description, .rte, .product-single__description")
        d_html, d_text = DescriptionExtractor.sanitize_html(str(desc_el) if desc_el else None)

        # Category & Breadcrumbs
        cat_name, cat_path, breadcrumbs = CategoryExtractor.extract_from_breadcrumbs(soup)

        # Variants
        variants = VariantExtractor.extract_from_dom(soup)

        product = ProductIntelligence(
            product_id=handle,
            marketplace=MarketplaceType.SHOPIFY,
            source_url=response.url,
            canonical_url=canonical_url,
            title=title,
            description_text=d_text,
            description_html=d_html,
            price=price,
            original_price=orig_price,
            currency=currency,
            seller_name=vendor,
            category_name=cat_name,
            category_path=cat_path,
            breadcrumbs=breadcrumbs,
            primary_image=primary_img,
            images=img_records,
            variants=variants,
            specifications=[],
            reviews=[],
            extraction_warnings=warnings,
        )

        snapshot = HistoricalSnapshot(
            product_id=handle,
            marketplace=MarketplaceType.SHOPIFY,
            title=title,
            price=price,
            original_price=orig_price,
            discount=None,
            currency=currency,
            availability=True,
            seller_name=vendor,
            primary_image=primary_img,
            image_urls=[img.url for img in img_records],
            source_url=canonical_url,
        )

        return IntelligenceExtractionResult(
            extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
            product_id=handle,
            marketplace=MarketplaceType.SHOPIFY,
            url=canonical_url,
            status=ExtractionStatus.SUCCESS,
            success=True,
            status_code=response.status_code,
            duration_ms=response.duration_ms,
            product=product,
            reviews=[],
            snapshot=snapshot,
            fields_extracted=["title", "price", "images"],
            warnings=warnings,
        )
