"""Universal Multi-Marketplace Crawling Engine coordinating adapters, strategies, and persistence."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid

from app.crawling.adapters.crawl4ai_adapter import Crawl4AIAdapter
from app.crawling.cache import UniversalCrawlCache
from app.crawling.challenge import ChallengeDetectionResult, UniversalChallengeDetector
from app.crawling.config import UniversalCrawlerConfig
from app.crawling.dispatcher import ConcurrencyDispatcher
from app.crawling.hooks import CrawlHookPipeline
from app.crawling.interfaces import (
    BaseMarketplaceAdapterInterface,
    CrawlStrategyInterface,
    UniversalCrawlerInterface,
)
from app.crawling.marketplaces import (
    AliExpressAdapter,
    AmazonAdapter,
    BaseMarketplaceAdapter,
    DarazAdapter,
    EbayAdapter,
    ShopifyAdapter,
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
from app.crawling.session import UniversalSessionManager
from app.crawling.strategies import (
    CategoryCrawlStrategy,
    DeepCrawlStrategy,
    PaginationCrawlStrategy,
    ProductCrawlStrategy,
    SearchCrawlStrategy,
    StandardCrawlStrategy,
)
from app.storage.repository import InMemoryStorage
from app.core.logging import logger


class UniversalCrawlingEngine:
    """
    High-level, marketplace-agnostic crawling engine powered by Crawl4AI / Playwright.
    Orchestrates adapters, strategies, caching, challenge handling, and recovery.
    """

    def __init__(
        self,
        config: Optional[UniversalCrawlerConfig] = None,
        crawler: Optional[UniversalCrawlerInterface] = None,
        cache: Optional[UniversalCrawlCache] = None,
        recovery: Optional[UniversalCheckpointRecovery] = None,
        session_manager: Optional[UniversalSessionManager] = None,
        storage: Optional[Any] = None,
    ):
        self.config = config or UniversalCrawlerConfig()
        self.cache = cache or UniversalCrawlCache(cache_mode=self.config.cache_mode)
        self.recovery = recovery or UniversalCheckpointRecovery()
        self.session_manager = session_manager or UniversalSessionManager()
        self.storage = storage or InMemoryStorage()
        self.hooks = CrawlHookPipeline()
        self.detector = UniversalChallengeDetector()

        # Pluggable marketplace adapters
        self.adapters: Dict[MarketplaceType, BaseMarketplaceAdapterInterface] = {
            MarketplaceType.DARAZ: DarazAdapter(),
            MarketplaceType.AMAZON: AmazonAdapter(),
            MarketplaceType.EBAY: EbayAdapter(),
            MarketplaceType.ALIEXPRESS: AliExpressAdapter(),
            MarketplaceType.SHOPIFY: ShopifyAdapter(),
        }

        # Strategies
        self.strategies: Dict[str, CrawlStrategyInterface] = {
            "standard": StandardCrawlStrategy(),
            "product": ProductCrawlStrategy(),
            "category": CategoryCrawlStrategy(),
            "search": SearchCrawlStrategy(),
            "pagination": PaginationCrawlStrategy(),
            "deep": DeepCrawlStrategy(
                max_depth=self.config.max_deep_crawl_depth,
                max_pages=self.config.max_deep_crawl_pages,
            ),
        }

        # Default crawler backend
        self.crawler = crawler or Crawl4AIAdapter(
            config=self.config,
            cache=self.cache,
        )

    def register_adapter(self, adapter: BaseMarketplaceAdapterInterface) -> None:
        """Register custom marketplace adapter."""
        self.adapters[adapter.marketplace_type] = adapter

    def resolve_adapter(self, url: str, explicit_marketplace: Optional[MarketplaceType] = None) -> BaseMarketplaceAdapterInterface:
        """Resolve suitable marketplace adapter based on URL or explicit type."""
        if explicit_marketplace and explicit_marketplace in self.adapters:
            return self.adapters[explicit_marketplace]

        for adapter in self.adapters.values():
            if adapter.validate_url(url):
                return adapter

        # Fallback to Shopify if domain looks like an independent ecommerce store or Daraz default
        if "myshopify.com" in url.lower() or "/products/" in url.lower():
            return self.adapters[MarketplaceType.SHOPIFY]

        return self.adapters[MarketplaceType.DARAZ]

    async def execute_crawl(
        self,
        request: CrawlRequest,
        strategy_name: str = "standard",
    ) -> UniversalCrawlResult:
        """
        Main execution workflow with pre/post hooks, challenge interception,
        strategy delegation, and error handling.
        """
        adapter = self.resolve_adapter(request.url, request.marketplace)
        strategy = self.strategies.get(strategy_name, self.strategies["standard"])
        crawl_id = request.crawl_id or f"crawl_{uuid.uuid4().hex[:8]}"
        req = request.model_copy(update={"crawl_id": crawl_id, "marketplace": adapter.marketplace_type})

        # Execute before_request hooks
        req = await self.hooks.execute_before_request(req)

        try:
            result = await strategy.execute(req, adapter, self.crawler)

            # Check challenge detection
            if result.raw_html:
                detection = self.detector.detect(result.status_code, result.raw_html, current_url=req.url)
                if detection.is_challenge or detection.is_blocked:
                    logger.warning(
                        f"Challenge detected on {req.url} ({detection.reason}). Pausing crawl for manual intervention.",
                        extra={"crawl_id": crawl_id, "url": req.url, "waf": detection.waf_provider},
                    )
                    result.challenge_detected = True
                    result.challenge_reason = detection.reason
                    result.status = CrawlStatus.MANUAL_INTERVENTION
                    result.success = False

                    # Save resumable checkpoint
                    snapshot = CrawlJobSnapshot(
                        crawl_id=crawl_id,
                        marketplace=adapter.marketplace_type,
                        strategy_name=strategy_name,
                        status=CrawlStatus.MANUAL_INTERVENTION,
                        discovered_urls=result.discovered_urls,
                        pending_urls=[req.url],
                        error=detection.reason,
                    )
                    self.recovery.save_checkpoint(snapshot)

            # Persist product entities if extracted
            if result.product and hasattr(self.storage, "save_product"):
                await self.storage.save_product(result.product)
            if result.products and hasattr(self.storage, "save_products"):
                await self.storage.save_products(result.products)

            # Execute on_result hooks
            result = await self.hooks.execute_on_result(result)
            return result

        except Exception as e:
            logger.error(f"Error in universal crawl for {req.url}: {e}", exc_info=True)
            await self.hooks.execute_on_error(req, e)
            return UniversalCrawlResult(
                crawl_id=crawl_id,
                url=req.url,
                marketplace=adapter.marketplace_type,
                content_type=req.content_type,
                status=CrawlStatus.FAILED,
                success=False,
                errors=[str(e)],
            )

    # ==========================================
    # High-level convenience operations
    # ==========================================

    async def crawl(self, url: Union[str, CrawlRequest], force_refresh: bool = False) -> UniversalCrawlResult:
        """Crawl a single URL or CrawlRequest."""
        if isinstance(url, CrawlRequest):
            req = url
            if force_refresh:
                req.force_refresh = True
        else:
            req = CrawlRequest(url=url, force_refresh=force_refresh)
        return await self.execute_crawl(req, strategy_name="standard")

    async def crawl_many(self, urls: List[Union[str, CrawlRequest]], force_refresh: bool = False) -> List[UniversalCrawlResult]:
        """Crawl multiple URLs concurrently."""
        tasks = [self.crawl(u, force_refresh=force_refresh) for u in urls]
        return await asyncio.gather(*tasks)

    async def crawl_product(self, url: Union[str, CrawlRequest], force_refresh: bool = False) -> UniversalCrawlResult:
        """Crawl and extract single product."""
        if isinstance(url, CrawlRequest):
            req = url
            req.content_type = CrawlContentType.PRODUCT
            if force_refresh:
                req.force_refresh = True
        else:
            req = CrawlRequest(url=url, content_type=CrawlContentType.PRODUCT, force_refresh=force_refresh)
        return await self.execute_crawl(req, strategy_name="product")

    async def crawl_category(self, url: str, max_pages: int = 1) -> UniversalCrawlResult:
        """Crawl category hierarchy."""
        strategy = "pagination" if max_pages > 1 else "category"
        req = CrawlRequest(url=url, content_type=CrawlContentType.CATEGORY)
        return await self.execute_crawl(req, strategy_name=strategy)

    async def crawl_search(self, keyword: str, marketplace: MarketplaceType = MarketplaceType.DARAZ, max_pages: int = 1) -> UniversalCrawlResult:
        """Search keyword and extract candidate listings."""
        adapter = self.adapters.get(marketplace, self.adapters[MarketplaceType.DARAZ])
        search_url = adapter.build_search_url(keyword, page=1)
        strategy = "pagination" if max_pages > 1 else "search"
        req = CrawlRequest(url=search_url, marketplace=marketplace, content_type=CrawlContentType.SEARCH)
        return await self.execute_crawl(req, strategy_name=strategy)

    async def deep_crawl(self, url: str, max_depth: int = 2, max_pages: int = 20) -> UniversalCrawlResult:
        """Deep crawl starting from seed URL."""
        req = CrawlRequest(url=url, max_depth=max_depth, content_type=CrawlContentType.DEEP)
        deep_strat = DeepCrawlStrategy(max_depth=max_depth, max_pages=max_pages)
        self.strategies["deep"] = deep_strat
        return await self.execute_crawl(req, strategy_name="deep")

    async def resume_crawl(self, crawl_id: str) -> Optional[UniversalCrawlResult]:
        """Resume paused crawl from checkpoint snapshot."""
        snapshot = self.recovery.load_checkpoint(crawl_id)
        if not snapshot:
            logger.warning(f"No checkpoint found for crawl {crawl_id}")
            return None

        if not snapshot.pending_urls and not snapshot.discovered_urls:
            logger.info(f"Crawl {crawl_id} has no pending URLs to resume.")
            return None

        next_url = snapshot.pending_urls[0] if snapshot.pending_urls else snapshot.discovered_urls[0]
        req = CrawlRequest(
            url=next_url,
            crawl_id=crawl_id,
            marketplace=snapshot.marketplace,
        )
        return await self.execute_crawl(req, strategy_name=snapshot.strategy_name)

    async def close(self) -> None:
        """Close crawler backend."""
        if hasattr(self.crawler, "close"):
            await self.crawler.close()
