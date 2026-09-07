"""Product variant extraction (color, size, SKU, price, availability)."""

from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from app.extraction.confidence import ExtractionSource
from app.models.product import ProductVariant


class VariantExtractor:
    """Extracts selectable SKU variants (color, storage, size) from structured data or DOM."""

    VARIANT_DOM_SELECTORS = [
        ".sku-prop-content",
        ".pdp-mod-product-info-section",
        "#module_sku-select",
    ]

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ProductVariant], ExtractionSource]:
        """
        Extract list of ProductVariant instances and extraction source.
        """
        variants: List[ProductVariant] = []
        source = ExtractionSource.FALLBACK

        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json.get("skuInfos", {}))
            if isinstance(fields, dict):
                sku_data = fields.get("skuInfos") or fields.get("skus") or {}
                if isinstance(sku_data, dict):
                    sku_data = list(sku_data.values())

                if isinstance(sku_data, list):
                    for idx, sku in enumerate(sku_data):
                        if isinstance(sku, dict):
                            sku_id = str(sku.get("skuId") or sku.get("id") or f"sku_{idx}")
                            price_val = None
                            if "price" in sku and isinstance(sku["price"], dict):
                                price_val = sku["price"].get("value")
                            elif "salePrice" in sku and isinstance(sku["salePrice"], dict):
                                price_val = sku["salePrice"].get("value")

                            # Parse attributes
                            props = sku.get("properties") or sku.get("propValues") or {}
                            color_val = props.get("color") if isinstance(props, dict) else None
                            size_val = props.get("size") if isinstance(props, dict) else None

                            var_obj = ProductVariant(
                                sku_id=sku_id,
                                name=str(sku.get("name") or color_val or size_val or f"Variant {idx+1}"),
                                color=color_val,
                                size=size_val,
                                price=float(price_val) if price_val is not None else None,
                                available=bool(sku.get("avail", True)),
                            )
                            variants.append(var_obj)

                    if variants:
                        source = ExtractionSource.STRUCTURED_DATA

        # 2. DOM Selectors (fallback)
        if not variants:
            for sel in self.VARIANT_DOM_SELECTORS:
                container = soup.select_one(sel)
                if container:
                    items = container.select(".sku-name, .sku-variable-name, .sku-prop-content-header")
                    for idx, it in enumerate(items):
                        txt = it.get_text(strip=True)
                        if txt:
                            variants.append(
                                ProductVariant(
                                    sku_id=f"dom_sku_{idx+1}",
                                    name=txt,
                                    available=True,
                                )
                            )
                    if variants:
                        source = ExtractionSource.DOM
                        break

        return variants, source
