"""Core asynchronous discovery engine coordinating category trees, search queries, pagination, and deduplication."""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.core.checkpoint import CheckpointManager
from app.core.config import Settings, get_settings
from app.core.constants import CrawlStatus
from app.core.logging import logger
from app.core.rate_limiter import AsyncRateLimiter
from app.discovery.client import DarazDiscoveryClient
from app.discovery.config import DarazDiscoveryConfig, default_discovery_config
from app.discovery.manual_intervention import ManualInterventionManager, manual_intervention_manager
from app.discovery.models import CategoryTarget, DiscoveryCheckpointState, DiscoveryRun, ProductTarget
from app.discovery.parser import DarazHTMLParser, daraz_parser
from app.discovery.queue import ProductTargetQueue
from app.discovery.strategies.category import CategoryDiscoveryStrategy
from app.discovery.strategies.keyword import KeywordDiscoveryStrategy
from app.storage.base import BaseStorage
from app.storage.repository import InMemoryStorage


class DarazDiscoveryEngine:
    """Production discovery orchestrator for the Daraz Pakistan marketplace."""

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        settings: Optional[Settings] = None,
        discovery_config: Optional[DarazDiscoveryConfig] = None,
        discovery_client: Optional[DarazDiscoveryClient] = None,
        parser: Optional[DarazHTMLParser] = None,
        queue: Optional[ProductTargetQueue] = None,
        intervention_manager: Optional[ManualInterventionManager] = None,
    ):
        self.storage = storage or InMemoryStorage()
        self.settings = settings or get_settings()
        self.config = discovery_config or default_discovery_config
        self.client = discovery_client or DarazDiscoveryClient(
            settings=self.settings, discovery_config=self.config
        )
        self.parser = parser or daraz_parser
        self.queue = queue or ProductTargetQueue(storage=self.storage, batch_size=self.config.QUEUE_BATCH_SIZE)
        self.intervention_manager = intervention_manager or manual_intervention_manager
        self.rate_limiter = AsyncRateLimiter(settings=self.settings)

        # Initialize strategies
        self.category_strategy = CategoryDiscoveryStrategy(
            client=self.client,
            parser=self.parser,
            queue=self.queue,
            storage=self.storage,
            config=self.config,
        )
        self.keyword_strategy = KeywordDiscoveryStrategy(
            client=self.client,
            parser=self.parser,
            queue=self.queue,
            config=self.config,
        )

    async def discover_categories(
        self,
        start_url: Optional[str] = None,
        crawl_id: Optional[str] = None,
        run_record: Optional[DiscoveryRun] = None,
    ) -> List[CategoryTarget]:
        """Fetch marketplace root/menu and parse complete category and subcategory trees."""
        url = start_url or self.config.BASE_URL
        status_code, html, final_url, detection = await self.client.fetch_page(url, crawl_id=crawl_id)

        if detection.is_captcha or detection.is_blocked:
            if run_record:
                run_record.captcha_events += 1
                run_record.status = CrawlStatus.MANUAL_INTERVENTION
            return []

        categories = self.parser.parse_categories(html, base_url=self.config.BASE_URL)

        if self.storage and categories:
            for cat in categories:
                if hasattr(self.storage, "save_category_target"):
                    await self.storage.save_category_target(cat)

        top_level = [c for c in categories if c.level == 1]
        subs = [c for c in categories if c.level > 1]

        if run_record:
            run_record.categories_discovered += len(top_level)
            run_record.subcategories_discovered += len(subs)
            run_record.pages_processed += 1

        return categories

    async def discover_category_products(
        self,
        category_target: CategoryTarget,
        max_pages: Optional[int] = None,
        crawl_id: Optional[str] = None,
        run_record: Optional[DiscoveryRun] = None,
    ) -> List[ProductTarget]:
        """Harvest product targets across paginated catalog pages for a specific category."""
        stats = await self.category_strategy.crawl_category_products(
            category=category_target,
            max_pages=max_pages,
            crawl_id=crawl_id,
        )

        await self.queue.flush()

        if run_record:
            run_record.pages_processed += stats.pages_processed
            run_record.pages_failed += stats.pages_failed
            run_record.product_urls_discovered += stats.total_targets_found
            run_record.unique_products_discovered = self.queue.unique_products
            run_record.duplicates_removed = self.queue.duplicates_prevented

            if "challenge_detected" in stats.stopped_reason:
                run_record.captcha_events += 1
                run_record.status = CrawlStatus.MANUAL_INTERVENTION

        return stats.collected_targets

    async def discover_keyword_products(
        self,
        keyword: str,
        max_pages: Optional[int] = None,
        crawl_id: Optional[str] = None,
        run_record: Optional[DiscoveryRun] = None,
    ) -> List[ProductTarget]:
        """Harvest product targets for a search keyword query."""
        stats = await self.keyword_strategy.crawl_keyword(
            keyword=keyword,
            max_pages=max_pages,
            crawl_id=crawl_id,
        )

        await self.queue.flush()

        if run_record:
            run_record.pages_processed += stats.pages_processed
            run_record.pages_failed += stats.pages_failed
            run_record.product_urls_discovered += stats.total_targets_found
            run_record.unique_products_discovered = self.queue.unique_products
            run_record.duplicates_removed = self.queue.duplicates_prevented

            if "challenge_detected" in stats.stopped_reason:
                run_record.captcha_events += 1
                run_record.status = CrawlStatus.MANUAL_INTERVENTION

        return stats.collected_targets

    async def run_discovery(
        self,
        seed_categories: bool = True,
        search_queries: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        categories: Optional[List[CategoryTarget]] = None,
        max_category_pages: int = 5,
        max_search_pages: int = 5,
        max_pages_per_target: Optional[int] = None,
        crawl_id: Optional[str] = None,
    ) -> DiscoveryRun:
        """Run full discovery workflow across configured keywords and categories with checkpoints."""
        active_crawl_id = crawl_id or str(uuid.uuid4())
        run = DiscoveryRun(crawl_id=active_crawl_id, status=CrawlStatus.RUNNING)

        checkpoint_mgr = CheckpointManager(
            storage=self.storage,
            crawl_id=active_crawl_id,
            target="discovery",
            checkpoint_interval=1,
        )

        logger.info(
            f"Starting full marketplace discovery session {active_crawl_id}",
            extra={"crawl_id": active_crawl_id, "event": "discovery_started"},
        )

        try:
            # 1. Discover categories if seed_categories is True or explicit categories given
            target_cats: List[CategoryTarget] = []
            if categories is not None:
                target_cats = categories
            elif seed_categories:
                all_cats = await self.discover_categories(crawl_id=active_crawl_id, run_record=run)
                target_cats = [c for c in all_cats if c.is_leaf or c.level >= 2][: self.config.MAX_CONCURRENT_CATEGORIES * 2]

            # 2. Process Categories with concurrency semaphore
            cat_limit = max_pages_per_target or max_category_pages
            cat_semaphore = asyncio.Semaphore(self.config.MAX_CONCURRENT_CATEGORIES)

            async def process_category(cat: CategoryTarget):
                async with cat_semaphore:
                    await self.discover_category_products(
                        category_target=cat,
                        max_pages=cat_limit,
                        crawl_id=active_crawl_id,
                        run_record=run,
                    )
                    await checkpoint_mgr.record_progress(
                        position=run.pages_processed,
                        item_id=cat.category_id,
                        url=cat.url,
                    )

            if target_cats and run.status != CrawlStatus.MANUAL_INTERVENTION:
                await asyncio.gather(*(process_category(c) for c in target_cats), return_exceptions=True)

            # 3. Process Keywords / Search queries
            kw_list = search_queries or keywords or self.config.DEFAULT_KEYWORDS[:5]
            kw_limit = max_pages_per_target or max_search_pages
            kw_semaphore = asyncio.Semaphore(self.config.MAX_CONCURRENT_CATEGORIES)

            async def process_keyword(kw: str):
                async with kw_semaphore:
                    await self.discover_keyword_products(
                        keyword=kw,
                        max_pages=kw_limit,
                        crawl_id=active_crawl_id,
                        run_record=run,
                    )
                    await checkpoint_mgr.record_progress(
                        position=run.pages_processed,
                        item_id=kw,
                    )

            if kw_list and run.status != CrawlStatus.MANUAL_INTERVENTION:
                await asyncio.gather(*(process_keyword(k) for k in kw_list), return_exceptions=True)

            # 4. Final flush and checkpoint save
            await self.queue.flush()
            await checkpoint_mgr.save_checkpoint()

            run.finished_at = datetime.now(timezone.utc)
            if run.status != CrawlStatus.MANUAL_INTERVENTION:
                run.status = CrawlStatus.COMPLETED

        except Exception as e:
            logger.error(f"Discovery crawl {active_crawl_id} failed: {e}", extra={"error": str(e)})
            run.status = CrawlStatus.FAILED
            run.finished_at = datetime.now(timezone.utc)
            await checkpoint_mgr.save_checkpoint()

        # Save run record to storage
        if self.storage and hasattr(self.storage, "save_discovery_run"):
            await self.storage.save_discovery_run(run)

        logger.info(
            f"Discovery crawl {active_crawl_id} finished ({run.status.value}). Found {run.unique_products_discovered} unique products ({run.duplicates_removed} duplicates prevented).",
            extra={
                "crawl_id": active_crawl_id,
                "status": run.status.value,
                "unique_products": run.unique_products_discovered,
                "duplicates_prevented": run.duplicates_removed,
                "pages": run.pages_processed,
            },
        )
        return run

    async def close(self):
        """Cleanly close underlying discovery clients."""
        await self.client.close()
