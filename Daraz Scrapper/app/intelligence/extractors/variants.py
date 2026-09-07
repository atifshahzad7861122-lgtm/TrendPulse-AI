"""Structured SKU variation extraction."""

from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup, Tag

from app.intelligence.models.product import Variant


class VariantExtractor:
    """
    Extracts structured product variants (Color, Size, Storage, Style) from JSON state or DOM swatches.
    Never flattens structured variants into meaningless unstructured text.
    """

    @classmethod
    def extract_from_dict_list(cls, raw_variants: List[Dict[str, Any]]) -> List[Variant]:
        """Convert list of raw variation dictionaries into structured Variant models."""
        variants: List[Variant] = []
        for v in raw_variants:
            if not isinstance(v, dict):
                continue

            name = str(v.get("title") or v.get("name") or v.get("sku_name") or "Default Variant")
            sku_id = str(v.get("id") or v.get("sku_id") or v.get("sku") or "")
            price = None
            orig_price = None

            if "price" in v:
                try:
                    price = float(v["price"])
                except (ValueError, TypeError):
                    pass

            if "compare_at_price" in v or "original_price" in v:
                raw_orig = v.get("compare_at_price") or v.get("original_price")
                try:
                    orig_price = float(raw_orig)
                except (ValueError, TypeError):
                    pass

            available = bool(v.get("available", True) and v.get("in_stock", True))
            stock = None
            if "inventory_quantity" in v or "stock" in v:
                try:
                    stock = int(v.get("inventory_quantity") or v.get("stock"))
                except (ValueError, TypeError):
                    pass

            img = v.get("featured_image", {}).get("src") if isinstance(v.get("featured_image"), dict) else v.get("image") or v.get("variant_image")

            variants.append(
                Variant(
                    sku_id=sku_id or None,
                    name=name,
                    group=v.get("option1_name") or v.get("group"),
                    value=v.get("option1") or v.get("value"),
                    price=price,
                    original_price=orig_price,
                    stock=stock,
                    available=available,
                    variant_image=img if isinstance(img, str) else None,
                    attributes={k: v_val for k, v_val in v.items() if k not in ("price", "name", "id", "title")},
                )
            )

        return variants

    @classmethod
    def extract_from_dom(cls, soup: BeautifulSoup) -> List[Variant]:
        """Extract variants from DOM option selectors or swatch elements."""
        variants: List[Variant] = []

        # Look for option swatches (e.g. Amazon / eBay / Daraz swatches)
        swatch_elements = soup.select(".sku-prop-content .sku-variable-size, .swatches li, .dimension-values li")
        for el in swatch_elements:
            name = el.get_text(strip=True)
            if name:
                variants.append(Variant(
                    name=name,
                    available=not ("disabled" in el.get("class", []) or "out-of-stock" in el.get("class", [])),
                ))

        return variants
