"""Product description extraction and HTML sanitization."""

import re
from typing import Any, Dict, Optional
from bs4 import BeautifulSoup


class DescriptionExtractor:
    """Extracts raw/sanitized HTML and normalized plain-text descriptions."""

    DESCRIPTION_SELECTORS = [
        ".pdp-product-desc",
        ".pdp-product-detail",
        ".detail-content",
        "#module_product_detail",
        "[data-qa-locator='product-description']",
        ".html-content",
    ]

    HIGHLIGHT_SELECTORS = [
        ".pdp-product-highlights",
        ".pdp-mod-specification ul",
        "#module_product_highlights",
    ]

    def _sanitize_html(self, raw_html: str) -> str:
        """Strip script, style, ads and clean up HTML structure."""
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "iframe", "noscript", "meta", "link", ".ads", "div.ads"]):
            tag.decompose()
        # Also strip tags by class
        for ad_el in soup.find_all(class_="ads"):
            ad_el.decompose()
        return str(soup).strip()

    def _normalize_text(self, text: str) -> str:
        """Normalize whitespace in description text."""
        if not text:
            return ""
        text = text.replace("\u00A0", " ")
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
        json_ld: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Extract sanitized plain text / HTML description.
        """
        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json.get("product", {}))
            if isinstance(fields, dict):
                desc_html = fields.get("description") or fields.get("productDesc")
                if desc_html and str(desc_html).strip():
                    sanitized = self._sanitize_html(str(desc_html))
                    return self._normalize_text(BeautifulSoup(sanitized, "html.parser").get_text(separator="\n"))

        # 2. JSON-LD
        if json_ld:
            desc_val = json_ld.get("description")
            if desc_val and str(desc_val).strip():
                return self._normalize_text(str(desc_val))

        # 3. DOM Selectors
        for sel in self.DESCRIPTION_SELECTORS:
            el = soup.select_one(sel)
            if el:
                sanitized = self._sanitize_html(str(el))
                plain = self._normalize_text(BeautifulSoup(sanitized, "html.parser").get_text(separator="\n"))
                if plain and len(plain) > 5:
                    return plain

        # Fallback to highlights if full description is absent
        for sel in self.HIGHLIGHT_SELECTORS:
            el = soup.select_one(sel)
            if el:
                sanitized = self._sanitize_html(str(el))
                plain = self._normalize_text(BeautifulSoup(sanitized, "html.parser").get_text(separator="\n"))
                if plain:
                    return plain

        return None
