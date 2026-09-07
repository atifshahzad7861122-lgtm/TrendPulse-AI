"""Abstract base interface for marketplace intelligence extractors."""

from abc import ABC, abstractmethod
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from app.crawling.models import CrawlResponse, MarketplaceType
from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.result import ExtractionStatus, IntelligenceExtractionResult
from app.intelligence.models.review import IntelligenceReview


class BaseMarketplaceExtractor(ABC):
    """
    Abstract base extractor enforcing layered extraction and standardized intelligence mapping.
    Extraction Sequence:
    1. Structured JSON-LD / schema.org
    2. Embedded Page State / JSON scripts
    3. Dedicated DOM Selectors
    4. Safe Fallback extraction
    """

    @property
    @abstractmethod
    def marketplace_type(self) -> MarketplaceType:
        """Supported marketplace type identifier."""
        pass

    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """Validate if URL belongs to this marketplace."""
        pass

    @abstractmethod
    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract native product or item ID from URL."""
        pass

    @abstractmethod
    def extract_intelligence(self, response: CrawlResponse) -> IntelligenceExtractionResult:
        """Extract full product intelligence from crawl response."""
        pass

    # ==========================================
    # Common Utilities & Layered Extraction Helpers
    # ==========================================

    def extract_json_ld(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract all valid JSON-LD objects from script tags."""
        json_ld_list: List[Dict[str, Any]] = []
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string:
                try:
                    data = json.loads(script.string.strip())
                    if isinstance(data, dict):
                        json_ld_list.append(data)
                    elif isinstance(data, list):
                        json_ld_list.extend([item for item in data if isinstance(item, dict)])
                except (json.JSONDecodeError, TypeError):
                    continue
        return json_ld_list

    def extract_jsonld(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract primary JSON-LD product dictionary or first JSON-LD object."""
        items = self.extract_json_ld(soup)
        for item in items:
            t = item.get("@type")
            if t == "Product" or (isinstance(t, list) and "Product" in t):
                return item
        return items[0] if items else None

    def extract_opengraph(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract OpenGraph metadata tags."""
        og_data: Dict[str, str] = {}
        for meta in soup.find_all("meta"):
            prop = meta.get("property") or meta.get("name")
            content = meta.get("content")
            if prop and content and isinstance(prop, str) and isinstance(content, str):
                if prop.startswith("og:") or prop.startswith("twitter:"):
                    og_data[prop.lower()] = content.strip()
        return og_data

    def canonicalize_url(self, url: str) -> str:
        """Remove tracking parameters while preserving identity."""
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        return clean_url
