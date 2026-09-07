"""Core abstract interfaces for universal crawler, marketplace adapters, and strategies."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from app.crawling.models import (
    CrawlContentType,
    CrawlRequest,
    CrawlResponse,
    MarketplaceType,
    UniversalCrawlResult,
)


class UniversalCrawlerInterface(ABC):
    """
    Contract for generic crawling backend.
    Our application interacts strictly with this interface, isolating Crawl4AI.
    """

    @abstractmethod
    async def crawl(self, request: CrawlRequest) -> CrawlResponse:
        """Fetch a single page (via HTTP or browser)."""
        pass

    @abstractmethod
    async def crawl_many(self, requests: List[CrawlRequest]) -> List[CrawlResponse]:
        """Fetch multiple pages concurrently with rate limiting and concurrency control."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Release browser/client resources."""
        pass


class BaseMarketplaceAdapterInterface(ABC):
    """
    Contract for marketplace-specific rules, URL recognizers, and extraction logic.
    """

    @property
    @abstractmethod
    def marketplace_type(self) -> MarketplaceType:
        """Marketplace enum identifier."""
        pass

    @property
    @abstractmethod
    def supported_domains(self) -> List[str]:
        """List of supported domains/TLDs (e.g. ['daraz.pk', 'amazon.com'])."""
        pass

    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """Check if URL belongs to this marketplace."""
        pass

    @abstractmethod
    def detect_content_type(self, url: str) -> CrawlContentType:
        """Classify URL as PRODUCT, CATEGORY, SEARCH, etc."""
        pass

    @abstractmethod
    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract canonical product ID (e.g. ASIN for Amazon, item_id for Daraz)."""
        pass

    @abstractmethod
    def build_search_url(self, keyword: str, page: int = 1) -> str:
        """Construct standard search URL for keyword and page number."""
        pass

    @abstractmethod
    def parse_response(self, response: CrawlResponse, content_type: CrawlContentType) -> UniversalCrawlResult:
        """Parse HTML/JSON into standardized UniversalCrawlResult."""
        pass


class CrawlStrategyInterface(ABC):
    """
    Contract for execution strategies (Standard, Deep, Pagination, Product, Category, Search).
    """

    @abstractmethod
    async def execute(
        self,
        request: CrawlRequest,
        adapter: BaseMarketplaceAdapterInterface,
        crawler: UniversalCrawlerInterface,
    ) -> UniversalCrawlResult:
        """Execute crawling workflow for the given request and marketplace adapter."""
        pass
