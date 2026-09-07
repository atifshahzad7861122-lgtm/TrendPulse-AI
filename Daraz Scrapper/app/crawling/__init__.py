"""Universal Multi-Marketplace Crawling Engine package exports."""

from app.crawling.adapters.crawl4ai_adapter import Crawl4AIAdapter
from app.crawling.cache import UniversalCrawlCache
from app.crawling.challenge import ChallengeDetectionResult, UniversalChallengeDetector
from app.crawling.config import CrawlCacheMode, UniversalCrawlerConfig
from app.crawling.dispatcher import AdaptiveRateLimiter, ConcurrencyDispatcher
from app.crawling.engine import UniversalCrawlingEngine
from app.crawling.hooks import CrawlHookPipeline
from app.crawling.interfaces import (
    BaseMarketplaceAdapterInterface,
    CrawlStrategyInterface,
    UniversalCrawlerInterface,
)
from app.crawling.models import (
    CrawlContentType,
    CrawlRequest,
    CrawlResponse,
    CrawlStatus,
    MarketplaceType,
    UniversalCrawlResult,
)
from app.crawling.recovery import CrawlJobSnapshot, UniversalCheckpointRecovery
from app.crawling.session import MarketplaceSessionState, UniversalSessionManager

__all__ = [
    "UniversalCrawlingEngine",
    "UniversalCrawlerConfig",
    "CrawlCacheMode",
    "UniversalCrawlerInterface",
    "BaseMarketplaceAdapterInterface",
    "CrawlStrategyInterface",
    "CrawlRequest",
    "CrawlResponse",
    "UniversalCrawlResult",
    "CrawlStatus",
    "CrawlContentType",
    "MarketplaceType",
    "Crawl4AIAdapter",
    "UniversalCrawlCache",
    "UniversalSessionManager",
    "MarketplaceSessionState",
    "UniversalCheckpointRecovery",
    "CrawlJobSnapshot",
    "UniversalChallengeDetector",
    "ChallengeDetectionResult",
    "ConcurrencyDispatcher",
    "AdaptiveRateLimiter",
    "CrawlHookPipeline",
]
