"""Title extraction with multi-source fallback and sanitization."""

import html
import re
from typing import Any, Dict, Optional, Tuple
from bs4 import BeautifulSoup

from app.extraction.confidence import ExtractionSource


class TitleExtractor:
    """Extracts and normalizes product title from structured data, JSON-LD, DOM, or OpenGraph."""

    TITLE_SELECTORS = [
        ".pdp-mod-product-badge-title",
        "h1.pdp-title",
        "h1.pdp-mod-product-badge-title",
        "[data-qa-locator='product-title']",
        ".pdp-product-title h1",
        "h1#id-title",
        "h1",
    ]

    OPENGRAPH_SELECTORS = [
        "meta[property='og:title']",
        "meta[name='twitter:title']",
        "meta[name='title']",
    ]

    @staticmethod
    def normalize_title(raw_title: str) -> str:
        """
        Normalize title text: unescape HTML entities, replace NBSP,
        collapse whitespace, strip non-printable characters while preserving meaningful text.
        """
        if not raw_title:
            return ""

        # 1. Unescape HTML entities (e.g. &amp;, &quot;, &#39;)
        text = html.unescape(raw_title)

        # 2. Replace non-breaking spaces and irregular unicode spaces
        text = text.replace("\u00A0", " ").replace("\u200b", "")

        # 3. Collapse multiple whitespace into single space
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
        json_ld: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], ExtractionSource]:
        """
        Extract title and return (normalized_title, extraction_source).
        Fallback order: structured_data -> json_ld -> dom -> opengraph.
        """
        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json.get("product", {}))
            if isinstance(fields, dict):
                title_val = fields.get("title") or fields.get("productTitle")
                if title_val and str(title_val).strip():
                    return self.normalize_title(str(title_val)), ExtractionSource.STRUCTURED_DATA

        # 2. JSON-LD
        if json_ld:
            title_val = json_ld.get("name") or json_ld.get("headline")
            if title_val and str(title_val).strip():
                return self.normalize_title(str(title_val)), ExtractionSource.JSON_LD

        # 3. DOM Selectors
        for sel in self.TITLE_SELECTORS:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                norm = self.normalize_title(el.get_text())
                if norm and len(norm) >= 2:
                    return norm, ExtractionSource.DOM

        # 4. OpenGraph Metadata
        for sel in self.OPENGRAPH_SELECTORS:
            el = soup.select_one(sel)
            if el and el.get("content"):
                norm = self.normalize_title(str(el.get("content")))
                if norm and len(norm) >= 2:
                    return norm, ExtractionSource.OPENGRAPH

        return None, ExtractionSource.FALLBACK
