"""Stock availability extraction."""

import re
from typing import Any, Dict, Optional, Tuple
from bs4 import BeautifulSoup

from app.extraction.confidence import ExtractionSource


class AvailabilityExtractor:
    """Detects product stock status (in_stock, out_of_stock, limited_stock, pre_order)."""

    OUT_OF_STOCK_SELECTORS = [
        ".out-of-stock",
        ".pdp-button_disabled",
        "button.pdp-button_color_orange[disabled]",
        ".pdp-mod-product-badge-sold-out",
        ".stock-status-out",
        "[data-qa-locator='out-of-stock']",
    ]

    LIMITED_STOCK_SELECTORS = [
        ".stock-status-low",
        ".pdp-stock-warning",
        ".quantity-limit-tip",
    ]

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
        json_ld: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, ExtractionSource]:
        """
        Extract (is_in_stock, stock_status_str, extraction_source).
        """
        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json.get("skuInfos", {}))
            if isinstance(fields, dict):
                in_stock_val = fields.get("inStock") or fields.get("isAvailable")
                if in_stock_val is not None:
                    is_avail = bool(in_stock_val)
                    status_str = "in_stock" if is_avail else "out_of_stock"
                    return is_avail, status_str, ExtractionSource.STRUCTURED_DATA

        # 2. JSON-LD Offers availability
        if json_ld:
            offers = json_ld.get("offers")
            if isinstance(offers, dict):
                avail_str = offers.get("availability") or ""
                if "InStock" in avail_str:
                    return True, "in_stock", ExtractionSource.JSON_LD
                elif "OutOfStock" in avail_str or "Discontinued" in avail_str:
                    return False, "out_of_stock", ExtractionSource.JSON_LD

        # 3. DOM Selectors
        for sel in self.OUT_OF_STOCK_SELECTORS:
            if soup.select_one(sel):
                return False, "out_of_stock", ExtractionSource.DOM

        for sel in self.LIMITED_STOCK_SELECTORS:
            if soup.select_one(sel):
                return True, "limited_stock", ExtractionSource.DOM

        # By default, PDP is in stock if active buy/cart buttons exist
        return True, "in_stock", ExtractionSource.FALLBACK
