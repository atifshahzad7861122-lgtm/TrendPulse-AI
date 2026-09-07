"""Price, discount, and currency extraction."""

import re
from typing import Any, Dict, Optional, Tuple
from bs4 import BeautifulSoup


class PriceExtractor:
    """Extracts and normalizes selling price, original price, discount, and currency."""

    CURRENT_PRICE_SELECTORS = [
        ".pdp-price_type_normal",
        ".pdp-price",
        ".pdp-product-price .pdp-price_color_orange",
        "span.notranslate.pdp-price",
        "[data-qa-locator='product-price']",
        ".price-current",
        ".pdp-mod-product-price .pdp-price",
        "div.pdp-mod-product-price span",
    ]

    ORIGINAL_PRICE_SELECTORS = [
        ".pdp-price_type_deleted",
        ".pdp-price_color_lightgray",
        "span.pdp-price_type_deleted",
        ".origin-price-value",
        ".price-original",
        "del.pdp-price_type_deleted",
        ".pdp-mod-product-price del",
        "div.orign-block span.pdp-price_type_deleted",
    ]

    DISCOUNT_SELECTORS = [
        ".pdp-product-price__discount",
        ".pdp-discount",
        ".discount-percentage",
        "span[data-qa-locator='discount-tag']",
        ".pdp-price-discount",
    ]

    @staticmethod
    def clean_number(text: str) -> Optional[float]:
        """Convert formatted currency string like 'Rs. 45,999', 'PKR 1,250.50', '-25%', or '45,999' into float."""
        if not text:
            return None
        cleaned = str(text).replace(",", "").replace("\u00a0", " ").strip()
        match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
        json_ld: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
        """
        Extract (price, original_price, discount, currency).
        """
        price: Optional[float] = None
        original_price: Optional[float] = None
        discount: Optional[float] = None
        currency = "PKR"

        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json.get("skuInfos", {}))
            if isinstance(fields, dict):
                p_val = fields.get("price", {}).get("value") or fields.get("salePrice", {}).get("value")
                if p_val:
                    price = self.clean_number(str(p_val))

                orig_val = fields.get("originalPrice", {}).get("value")
                if orig_val:
                    original_price = self.clean_number(str(orig_val))

                disc_val = fields.get("discount")
                if disc_val:
                    discount = self.clean_number(str(disc_val))

        # 2. JSON-LD Offers
        if price is None and json_ld:
            offers = json_ld.get("offers")
            if isinstance(offers, dict):
                p_val = offers.get("price")
                if p_val is not None:
                    price = self.clean_number(str(p_val))
                curr_val = offers.get("priceCurrency")
                if curr_val and str(curr_val).strip():
                    currency = str(curr_val).strip()
            elif isinstance(offers, list) and len(offers) > 0:
                p_val = offers[0].get("price")
                if p_val is not None:
                    price = self.clean_number(str(p_val))

        # 3. DOM Selectors
        if price is None:
            for sel in self.CURRENT_PRICE_SELECTORS:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    txt = el.get_text(strip=True)
                    if "rs" in txt.lower() or "pkr" in txt.lower():
                        currency = "PKR"
                    val = self.clean_number(txt)
                    if val is not None:
                        price = val
                        break

        if original_price is None:
            for sel in self.ORIGINAL_PRICE_SELECTORS:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    val = self.clean_number(el.get_text(strip=True))
                    if val is not None:
                        original_price = val
                        break

        if discount is None:
            for sel in self.DISCOUNT_SELECTORS:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    val = self.clean_number(el.get_text(strip=True))
                    if val is not None:
                        discount = val
                        break

        # Calculate discount percentage if original price and price are available but discount tag is missing
        if discount is None and original_price and price and original_price > price:
            discount = round(((original_price - price) / original_price) * 100.0, 1)

        return price, original_price, discount, currency
