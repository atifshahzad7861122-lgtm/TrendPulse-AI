"""Sales count and sold quantity extraction."""

import re
from typing import Any, Dict, Optional
from bs4 import BeautifulSoup


class SalesExtractor:
    """Extracts normalized integer sold count and original raw sold text."""

    SALES_SELECTORS = [
        ".pdp-mod-sold",
        ".pdp-mod-review .sold-info",
        ".sold-count",
        ".product-sold-count",
        "span.sold_quantity",
        "[data-qa-locator='sold-count']",
        ".pdp-seller-info .item-sold",
    ]

    @staticmethod
    def parse_sold_string(text: str) -> Optional[int]:
        """
        Parse strings like '1.2K sold', '1.5K sold', '500+ sold', '1,000 sold', '2.5M sold' into an integer count.
        """
        if not text or not text.strip():
            return None

        cleaned = str(text).replace(",", "").strip()

        # Check for '2.5M' pattern
        m_match = re.search(r"(\d+(?:\.\d+)?)\s*[mM]", cleaned)
        if m_match:
            try:
                return int(float(m_match.group(1)) * 1_000_000)
            except ValueError:
                pass

        # Check for '1.2K' or '1.5K' multiplier pattern
        k_match = re.search(r"(\d+(?:\.\d+)?)\s*[kK]", cleaned)
        if k_match:
            try:
                return int(float(k_match.group(1)) * 1000)
            except ValueError:
                pass

        # Check for plain digits e.g. '500+' or '42 sold'
        num_match = re.search(r"(\d+)", cleaned)
        if num_match:
            try:
                return int(num_match.group(1))
            except ValueError:
                pass

        return None

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Extract integer sold count.
        """
        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json.get("product", {}))
            if isinstance(fields, dict):
                sold_val = fields.get("soldCount") or fields.get("itemSold") or fields.get("saleCount")
                if sold_val is not None:
                    count = self.parse_sold_string(str(sold_val))
                    if count is not None:
                        return count

        # 2. DOM Selectors
        for sel in self.SALES_SELECTORS:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                count = self.parse_sold_string(el.get_text(strip=True))
                if count is not None:
                    return count

        return None
