"""Base marketplace adapter defining shared structure, URL cleaning, and regex extractors."""

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from bs4 import BeautifulSoup

from app.crawling.interfaces import BaseMarketplaceAdapterInterface
from app.crawling.models import (
    CrawlContentType,
    CrawlResponse,
    CrawlStatus,
    MarketplaceType,
    UniversalCrawlResult,
)
from app.models.image import Image
from app.models.product import Product


class BaseMarketplaceAdapter(BaseMarketplaceAdapterInterface):
    """
    Abstract base adapter for specific ecommerce marketplace implementations.
    """

    TRACKING_PARAMS = {
        "spm", "scm", "clickTrackInfo", "pvid", "algo_pvid",
        "tag", "ref", "ref_", "pf_rd_r", "pf_rd_p", "qid",
        "sr", "keywords", "linkCode", "camp", "creative",
    }

    def canonicalize_url(self, url: str) -> str:
        """Strip tracking query parameters and fragments."""
        if not url:
            return ""
        parsed = urlparse(url.strip())
        query_dict = parse_qs(parsed.query, keep_blank_values=False)
        cleaned_query = {k: v for k, v in query_dict.items() if k.lower() not in self.TRACKING_PARAMS}
        new_query = urlencode(cleaned_query, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))

    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """Normalize whitespace and strip HTML entities."""
        if not text:
            return None
        import html
        clean = html.unescape(text)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean or None

    def clean_price(self, text: Optional[str]) -> Tuple[Optional[float], str]:
        """Extract numeric price value and currency token."""
        if not text:
            return None, "USD"
        raw = self.clean_text(text) or ""
        
        # Detect currency
        currency = "USD"
        if "Rs" in raw or "PKR" in raw:
            currency = "PKR"
        elif "৳" in raw or "BDT" in raw:
            currency = "BDT"
        elif "£" in raw or "GBP" in raw:
            currency = "GBP"
        elif "€" in raw or "EUR" in raw:
            currency = "EUR"
        elif "R$" in raw or "BRL" in raw:
            currency = "BRL"
        elif "$" in raw:
            currency = "USD"

        # Extract number
        num_match = re.search(r"[\d,]+(?:\.\d+)?", raw)
        if num_match:
            try:
                val = float(num_match.group(0).replace(",", ""))
                return val, currency
            except ValueError:
                pass
        return None, currency
