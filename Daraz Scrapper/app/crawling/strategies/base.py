"""Base abstract crawl strategy implementation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.crawling.interfaces import (
    BaseMarketplaceAdapterInterface,
    CrawlStrategyInterface,
    UniversalCrawlerInterface,
)
from app.crawling.models import CrawlRequest, UniversalCrawlResult


class BaseCrawlStrategy(CrawlStrategyInterface, ABC):
    """
    Base class providing common validation and helper routines for crawl strategies.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy name."""
        pass
