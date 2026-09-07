"""Abstract base crawler architecture."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.core.rate_limiter import AsyncRateLimiter
from app.models.crawl import CrawlRun
from app.storage.base import BaseStorage


class BaseCrawler(ABC):
    """Abstract base class defining standardized crawler lifecycle and execution interfaces."""

    def __init__(
        self,
        storage: BaseStorage,
        settings: Optional[Settings] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
    ):
        self.storage = storage
        self.settings = settings or get_settings()
        self.rate_limiter = rate_limiter or AsyncRateLimiter(settings=self.settings)
        self.is_running = False

    @abstractmethod
    async def run(self, crawl_run: CrawlRun, **kwargs: Any) -> CrawlRun:
        """Main crawl execution entry point."""
        pass

    @abstractmethod
    async def extract(self, source: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """Extract raw records from input source."""
        pass

    async def stop(self) -> None:
        """Signal crawler to gracefully halt execution."""
        self.is_running = False
        logger.info("Crawler stop requested", extra={"event": "crawler_stop_requested"})
