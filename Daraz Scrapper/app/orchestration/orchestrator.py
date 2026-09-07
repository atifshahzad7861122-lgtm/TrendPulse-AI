"""Central Production Scraping Orchestrator coordinating discovery, crawling, extraction, rate limiting, retries, and persistence."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union
import uuid

from app.core.logging import logger
from app.crawling.models import MarketplaceType
from app.discovery.engine import DarazDiscoveryEngine
from app.discovery.models import CategoryTarget, ProductTarget
from app.history.models import HistoricalObservation
from app.history.collector import HistoricalCollectionEngine
from app.history.store import BaseHistoricalStore, DiskJsonlHistoricalStore
from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.result import ExtractionStatus, IntelligenceExtractionResult
from app.intelligence.models.review import IntelligenceReview
from app.intelligence.pipeline.engine import ProductIntelligenceEngine
from app.orchestration.health import MarketplaceHealthTracker
from app.orchestration.models import CrawlJobSummary, CrawlTask, OrchestratorConfig, TaskState
from app.orchestration.queue import DurableTaskQueue
from app.orchestration.rate_limiter import MarketplaceRateLimiter
from app.orchestration.retry import SmartRetryPolicy
from app.orchestration.worker import WorkerPool
from app.storage.export import DataExporter


class ProductionScrapingOrchestrator:
    """
    Master Production Scraping Orchestrator.
    Executes discovery, priority queuing, bounded worker extraction,
    layered retry logic, rate-limited pacing, challenge interception,
    factual historical recording, and incremental batch persistence.
    """

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        intelligence_engine: Optional[ProductIntelligenceEngine] = None,
        historical_store: Optional[BaseHistoricalStore] = None,
        health_tracker: Optional[MarketplaceHealthTracker] = None,
    ):
        self.config = config or OrchestratorConfig()
        self.intelligence_engine = intelligence_engine or ProductIntelligenceEngine()
        self.historical_store = historical_store or DiskJsonlHistoricalStore(
            base_dir=str(Path(self.config.storage_dir) / "history")
        )
        self.historical_collector = HistoricalCollectionEngine(store=self.historical_store)
        self.health_tracker = health_tracker or MarketplaceHealthTracker()
        self.rate_limiter = MarketplaceRateLimiter(self.config.marketplace_limits)
        self.retry_policy = SmartRetryPolicy(
            base_backoff_sec=self.config.base_backoff_sec,
            max_backoff_sec=self.config.max_backoff_sec,
            max_retries=self.config.max_retries,
        )

        self._extracted_products: List[ProductIntelligence] = []
        self._extracted_reviews: List[IntelligenceReview] = []
        self._batch_lock = asyncio.Lock()

    async def execute_crawl(
        self,
        crawl_id: Optional[str] = None,
        marketplace: Optional[MarketplaceType] = None,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        urls: Optional[List[str]] = None,
        max_products: int = 10,
        resume: bool = False,
        dry_run: bool = False,
        output_file: Optional[str] = None,
        export_format: str = "json",
    ) -> CrawlJobSummary:
        """
        Execute an end-to-end production crawl job.
        """
        cid = crawl_id or f"crawl_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now(timezone.utc)
        t0 = time.time()

        logger.info(f"Starting Production Crawl [{cid}] - Marketplace: {marketplace or 'MULTI'}")

        # 1. Initialize Durable Queue
        queue = DurableTaskQueue(crawl_id=cid, checkpoints_dir=self.config.checkpoints_dir)

        # 2. Ingest Targets if not resuming existing queue
        if not resume or not queue.has_pending_or_processing():
            await self._populate_queue(
                queue=queue,
                crawl_id=cid,
                marketplace=marketplace,
                keyword=keyword,
                category=category,
                urls=urls,
                max_products=max_products,
            )

        task_count = len(queue.get_all_tasks())
        logger.info(f"Queue populated with {task_count} total tasks for crawl {cid}")

        if dry_run:
            logger.info(f"DRY RUN enabled: {task_count} tasks planned without making network requests.")
            return CrawlJobSummary(
                crawl_id=cid,
                marketplace=marketplace,
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
                duration_seconds=round(time.time() - t0, 2),
                total_tasks=task_count,
                status="dry_run_completed",
            )

        # 3. Define Task Processor
        async def process_task(task: CrawlTask, worker_id: int) -> None:
            await self._process_single_task(task, worker_id, queue)

        # 4. Start Bounded Worker Pool
        worker_pool = WorkerPool(
            queue=queue,
            process_task_fn=process_task,
            max_workers=self.config.max_workers,
        )

        await worker_pool.start()
        await worker_pool.wait_idle()
        await worker_pool.stop()

        # 5. Final Export
        if output_file and self._extracted_products:
            out_path = DataExporter.export_products(
                self._extracted_products,
                output_file,
                export_format=export_format,
            )
            logger.info(f"Exported {len(self._extracted_products)} products to {out_path}")

        # 6. Build Summary
        duration = round(time.time() - t0, 2)
        counts = queue.get_counts()

        summary = CrawlJobSummary(
            crawl_id=cid,
            marketplace=marketplace,
            started_at=start_time,
            completed_at=datetime.now(timezone.utc),
            duration_seconds=duration,
            total_tasks=task_count,
            completed_count=counts.get(TaskState.COMPLETED, 0),
            failed_count=counts.get(TaskState.FAILED, 0),
            challenged_count=counts.get(TaskState.CHALLENGED, 0),
            retried_count=counts.get(TaskState.RETRY_PENDING, 0),
            cancelled_count=counts.get(TaskState.CANCELLED, 0),
            products_persisted=len(self._extracted_products),
            observations_recorded=len(self._extracted_products),
            average_latency_ms=self.health_tracker.get_health(marketplace).average_latency_ms if marketplace else 0.0,
            status="completed" if counts.get(TaskState.CHALLENGED, 0) == 0 else "completed_with_challenges",
        )

        logger.info(f"Production Crawl [{cid}] finished in {duration}s. Completed: {summary.completed_count}, Challenged: {summary.challenged_count}, Failed: {summary.failed_count}")
        return summary

    async def _populate_queue(
        self,
        queue: DurableTaskQueue,
        crawl_id: str,
        marketplace: Optional[MarketplaceType],
        keyword: Optional[str],
        category: Optional[str],
        urls: Optional[List[str]],
        max_products: int,
    ) -> None:
        """Discover or ingest target listing URLs and enqueue them."""
        tasks_to_add: List[CrawlTask] = []

        # A. Direct URLs
        if urls:
            for url in urls:
                m_type = marketplace or self._infer_marketplace(url)
                tasks_to_add.append(
                    CrawlTask(
                        crawl_id=crawl_id,
                        url=url,
                        marketplace=m_type,
                        priority=5,
                    )
                )

        # B. Keyword / Category Discovery (Daraz Engine)
        elif marketplace == MarketplaceType.DARAZ and (keyword or category):
            disc_engine = DarazDiscoveryEngine()
            discovered: List[ProductTarget] = []
            if keyword:
                discovered = await disc_engine.discover_keyword_products(keyword=keyword, max_pages=2)
            elif category:
                cat = CategoryTarget(category_id="cat_01", name="Custom Category", url=category)
                discovered = await disc_engine.discover_category_products(category_target=cat, max_pages=2)

            for target in discovered[:max_products]:
                tasks_to_add.append(
                    CrawlTask(
                        crawl_id=crawl_id,
                        url=target.url,
                        marketplace=MarketplaceType.DARAZ,
                        product_id=target.product_id,
                        priority=10,
                    )
                )
        elif keyword:
            # Multi-marketplace keyword targets
            m_type = marketplace or MarketplaceType.DARAZ
            kw_slug = keyword.replace(' ', '+')
            if m_type == MarketplaceType.AMAZON:
                u = f"https://www.amazon.com/s?k={kw_slug}"
            elif m_type == MarketplaceType.EBAY:
                u = f"https://www.ebay.com/sch/i.html?_nkw={kw_slug}"
            elif m_type == MarketplaceType.ALIEXPRESS:
                u = f"https://www.aliexpress.com/w/wholesale-{kw_slug}.html"
            elif m_type == MarketplaceType.SHOPIFY:
                u = f"https://kith.com/collections/all"
            else:
                u = f"https://www.daraz.pk/catalog/?q={kw_slug}"
            tasks_to_add.append(CrawlTask(crawl_id=crawl_id, url=u, marketplace=m_type, priority=10))

        await queue.enqueue_many(tasks_to_add)

    async def _process_single_task(
        self,
        task: CrawlTask,
        worker_id: int,
        queue: DurableTaskQueue,
    ) -> None:
        """Process a single extraction task with rate-limiting, challenge checking, retries, and persistence."""
        m_type = task.marketplace
        logger.info(f"[Worker {worker_id}] Processing {m_type.value.upper()} task {task.task_id}: {task.url}")

        t_start = time.time()
        
        # 1. Pacing & Concurrency Gate
        async with self.rate_limiter.throttle(m_type, is_browser=self.config.enable_browser):
            try:
                res: IntelligenceExtractionResult = await self.intelligence_engine.extract_product(task.url)
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Unhandled error on {task.url}: {e}", exc_info=True)
                res = IntelligenceExtractionResult(
                    extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                    product_id=task.product_id or "error",
                    marketplace=m_type,
                    url=task.url,
                    status=ExtractionStatus.FAILED,
                    success=False,
                    errors=[str(e)],
                )

        latency_ms = round((time.time() - t_start) * 1000, 1)

        # 2. Challenge Interception
        if res.status == ExtractionStatus.CHALLENGE:
            reason = res.errors[0] if res.errors else "Bot challenge detected"
            logger.warning(f"⚠️ [Worker {worker_id}] Challenge wall encountered on {task.url}: {reason}")
            self.health_tracker.record_challenge(m_type, reason=reason, latency_ms=latency_ms)
            await queue.mark_challenged(task.task_id, reason=reason)
            return

        # 3. Successful Extraction
        if res.success and res.product:
            p = res.product
            logger.info(f"✅ [Worker {worker_id}] Extracted: {p.title[:40]} | Price: {p.price} {p.currency} | Latency: {latency_ms}ms")
            
            self.health_tracker.record_success(m_type, latency_ms=latency_ms)
            await queue.mark_completed(task.task_id, product_id=p.product_id)

            # Record Factual Historical Observation
            try:
                obs = HistoricalObservation(
                    product_id=p.product_id,
                    marketplace=p.marketplace,
                    product_url=p.canonical_url or task.url,
                    observed_at=datetime.now(timezone.utc),
                    crawl_id=task.crawl_id,
                    title=p.title,
                    price=p.price,
                    original_price=p.original_price,
                    discount=p.discount,
                    currency=p.currency,
                    rating=p.rating,
                    review_count=p.review_count or 0,
                    rating_count=p.rating_count,
                    sold_count=p.sold_count,
                    raw_sold_text=p.raw_sold_text,
                    availability=p.availability,
                    seller_id=p.seller_id,
                    seller_name=p.seller_name,
                    category_id=p.category_id,
                    category_path=p.category_path,
                    variants_count=len(p.variants) if p.variants else 0,
                    specifications_count=len(p.specifications) if p.specifications else 0,
                    source="production_orchestrator",
                )
                await self.historical_store.save_observation(obs)
            except Exception as e:
                logger.error(f"Failed to record historical observation for {p.product_id}: {e}")

            # Incremental Batch Append
            async with self._batch_lock:
                self._extracted_products.append(p)
                if res.reviews:
                    self._extracted_reviews.extend(res.reviews)

                if len(self._extracted_products) % self.config.batch_size == 0:
                    logger.info(f"Incremental batch checkpoint: {len(self._extracted_products)} products in memory/store.")
            return

        # 4. Extraction Failure & Retry Evaluation
        err_msg = res.errors[0] if res.errors else f"HTTP {res.status_code} extraction failed"
        logger.warning(f"❌ [Worker {worker_id}] Task {task.task_id} failed: {err_msg}")
        self.health_tracker.record_failure(m_type, error=err_msg, status_code=res.status_code, latency_ms=latency_ms)

        should_retry, next_retry, reason = self.retry_policy.should_retry(
            task=task,
            status_code=res.status_code,
            error_message=err_msg,
        )

        if should_retry and next_retry:
            logger.info(f"🔄 Scheduling retry for {task.task_id} (Attempt {task.attempt_count}/{task.max_retries}) at {next_retry.isoformat()}")
            await queue.mark_retry_pending(task.task_id, next_retry_at=next_retry, error=reason or err_msg)
        else:
            logger.info(f"🛑 Marking task {task.task_id} as permanently failed: {reason or err_msg}")
            await queue.mark_failed(task.task_id, error=reason or err_msg)

    def _infer_marketplace(self, url: str) -> MarketplaceType:
        """Infer marketplace type from URL domain."""
        u_lower = url.lower()
        if "daraz" in u_lower:
            return MarketplaceType.DARAZ
        elif "amazon" in u_lower:
            return MarketplaceType.AMAZON
        elif "ebay" in u_lower:
            return MarketplaceType.EBAY
        elif "aliexpress" in u_lower:
            return MarketplaceType.ALIEXPRESS
        else:
            return MarketplaceType.SHOPIFY
