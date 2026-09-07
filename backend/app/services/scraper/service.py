import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from backend.app.models.domain import (
    ScraperCrawlJob, RawScrapedPayload, ScraperMarketplaceHealth,
    MarketplaceProduct, ProductMarketSnapshot
)
from backend.app.repositories.base import (
    ScraperRepository, MarketplaceProductRepository, UnifiedProductRepository,
    DataQualityRepository
)
from backend.app.services.scraper.models import (
    StartScraperJobRequest, ScraperJobProgressResponse, ScraperJobListResponse,
    ScraperProductItem, ScraperProductListResponse, RawScrapedDataResponse,
    ScraperHistoricalSnapshotItem, ScraperProductHistoryResponse
)
from backend.app.services.scraper.bridge import ScraperIntegrationBridge

logger = logging.getLogger("trendpulse.scraper.service")


class ScraperService:
    """
    High-level service managing Scraper job execution, real-time status tracking,
    marketplace health telemetry, and product queries.
    """
    _active_tasks: Dict[str, asyncio.Task] = {}

    def __init__(
        self,
        scraper_repo: ScraperRepository,
        marketplace_repo: MarketplaceProductRepository,
        unified_repo: UnifiedProductRepository,
        bridge: Optional[ScraperIntegrationBridge] = None
    ):
        self.scraper_repo = scraper_repo
        self.marketplace_repo = marketplace_repo
        self.unified_repo = unified_repo
        self.bridge = bridge or ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=marketplace_repo,
            unified_repo=unified_repo
        )

    def _to_progress_response(self, job: ScraperCrawlJob) -> ScraperJobProgressResponse:
        now = datetime.now(timezone.utc)
        duration = 0.0
        if job.started_at:
            end_t = job.completed_at or now
            duration = round((end_t - job.started_at).total_seconds(), 2)

        return ScraperJobProgressResponse(
            job_id=job.id,
            marketplace=job.marketplace,
            provider=job.metadata_json.get("provider", "auto") if job.metadata_json else "auto",
            trigger_type=job.trigger_type,
            status=job.status,
            target_count=job.target_count,
            products_fetched=job.products_fetched,
            products_persisted=job.products_persisted,
            products_rejected=job.products_rejected,
            challenged_count=job.challenged_count,
            failed_count=job.failed_count,
            current_throughput=job.current_throughput,
            duration_seconds=duration,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            metadata_json=job.metadata_json or {},
            created_at=job.created_at
        )

    def _to_product_item(self, p: MarketplaceProduct) -> ScraperProductItem:
        raw = p.raw_source_data or {}
        specs = raw.get("specifications") or raw.get("specs") or {}
        variants = raw.get("variants") or raw.get("variations") or []
        images = raw.get("images") or ([p.image_url] if p.image_url else [])
        reviews = raw.get("reviews") or []
        seller_metrics = raw.get("seller_metrics") or {}

        return ScraperProductItem(
            id=p.id,
            marketplace=p.platform,
            provider=raw.get("source_provider") or ("daraz_specialized" if p.platform == "daraz" else "universal"),
            product_id=p.product_id,
            title=p.product_name,
            brand=raw.get("brand"),
            price=p.price,
            original_price=p.original_price if p.original_price > 0 else None,
            discount=p.discount_percentage if p.discount_percentage > 0 else None,
            discount_label=p.discount_label,
            currency=p.currency or "PKR",
            rating=p.rating if p.rating > 0 else None,
            review_count=p.review_count,
            sold_count=raw.get("sold_count"),
            seller_name=p.seller_name,
            seller_id=p.seller_id,
            seller_rating=raw.get("seller_rating"),
            seller_metrics=seller_metrics,
            category=p.category,
            availability=p.in_stock,
            image_url=p.image_url,
            images=images,
            product_url=p.product_url or "",
            source_url=p.product_url,
            extraction_status=raw.get("extraction_status", "complete"),
            quality_status="valid",
            confidence_score=raw.get("confidence_score", 1.0),
            challenge_status=raw.get("challenge_status"),
            description_text=raw.get("description"),
            specifications=specs,
            variants=variants,
            reviews=reviews,
            first_seen_at=p.first_seen_at,
            last_seen_at=p.last_seen_at,
            raw_payload_available=bool(p.raw_source_data)
        )

    async def start_job(self, req: StartScraperJobRequest) -> ScraperJobProgressResponse:
        """
        Creates a new Scraper job and schedules async execution in the background.
        """
        job_id = f"job_{req.marketplace}_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        keywords = req.keywords or ([req.keyword] if req.keyword else [])
        urls = req.urls or ([req.url] if req.url else [])

        job = ScraperCrawlJob(
            id=job_id,
            marketplace=req.marketplace.lower().strip(),
            trigger_type="manual",
            keywords=keywords,
            urls=urls,
            category_id=req.category,
            target_count=req.max_products,
            max_workers=req.max_workers,
            status="queued",
            metadata_json={
                "provider": req.provider,
                "export_format": req.export_format,
                "dry_run": req.dry_run
            },
            created_at=now,
            updated_at=now
        )
        self.scraper_repo.create_job(job)

        # Launch background task
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.bridge.run_scraper_job(job))
        ScraperService._active_tasks[job_id] = task

        def _on_task_done(t: asyncio.Task):
            try:
                fresh_job = self.scraper_repo.get_job(job_id)
                if not fresh_job:
                    return
                now = datetime.now(timezone.utc)
                if t.cancelled():
                    logger.info(f"Scraper task {job_id} cancelled.")
                    if fresh_job.status in ("queued", "running"):
                        fresh_job.status = "stopped"
                        fresh_job.completed_at = fresh_job.completed_at or now
                        self.scraper_repo.update_job(fresh_job)
                elif t.exception():
                    exc = t.exception()
                    logger.error(f"Scraper task {job_id} failed with unhandled exception: {exc}")
                    if fresh_job.status in ("queued", "running"):
                        fresh_job.status = "failed"
                        fresh_job.error_message = f"Scraper execution error: {str(exc)}"
                        fresh_job.completed_at = fresh_job.completed_at or now
                        self.scraper_repo.update_job(fresh_job)
                else:
                    if fresh_job.status in ("queued", "running"):
                        if fresh_job.products_persisted > 0 or fresh_job.metadata_json.get("dry_run"):
                            fresh_job.status = "completed"
                        else:
                            fresh_job.status = "failed"
                            if not fresh_job.error_message:
                                fresh_job.error_message = "Crawl finished with 0 products extracted."
                        fresh_job.completed_at = fresh_job.completed_at or now
                        self.scraper_repo.update_job(fresh_job)
            except Exception as cb_err:
                logger.error(f"Error in scraper task done callback for {job_id}: {cb_err}")
            finally:
                ScraperService._active_tasks.pop(job_id, None)

        task.add_done_callback(_on_task_done)
        return self._to_progress_response(job)

    def _check_and_recover_stalled_job(self, job: ScraperCrawlJob) -> ScraperCrawlJob:
        """Watchdog detecting stalled, orphaned, or finished background tasks."""
        if job.status not in ("queued", "running"):
            return job

        task = ScraperService._active_tasks.get(job.id)
        now = datetime.now(timezone.utc)

        # 1. Task completed or failed outside of normal flow
        if task and task.done():
            if task.cancelled():
                job.status = "stopped"
                job.completed_at = job.completed_at or now
                self.scraper_repo.update_job(job)
            elif task.exception():
                job.status = "failed"
                job.error_message = f"Worker exception: {str(task.exception())}"
                job.completed_at = job.completed_at or now
                self.scraper_repo.update_job(job)
            elif job.products_persisted > 0 or job.metadata_json.get("dry_run"):
                job.status = "completed"
                job.completed_at = job.completed_at or now
                self.scraper_repo.update_job(job)
            else:
                job.status = "failed"
                if not job.error_message:
                    job.error_message = "Crawl finished with 0 products extracted."
                job.completed_at = job.completed_at or now
                self.scraper_repo.update_job(job)
            ScraperService._active_tasks.pop(job.id, None)
            return job

        # 2. Worker task does NOT exist in memory (e.g. backend restarted, task lost, or worker died)
        if not task:
            last_activity = job.updated_at or job.started_at or job.created_at
            elapsed = (now - last_activity).total_seconds() if last_activity else 999.0
            # Allow a 3.0s grace period for freshly queued jobs before task registration is confirmed
            if elapsed > 3.0:
                if job.products_persisted >= job.target_count and job.target_count > 0:
                    job.status = "completed"
                elif job.products_persisted > 0:
                    job.status = "completed"
                else:
                    job.status = "failed"
                    if not job.error_message:
                        job.error_message = "Scraper worker was interrupted before completion."
                job.completed_at = job.completed_at or now
                self.scraper_repo.update_job(job)
            return job

        # 3. Active task exists, but no heartbeat for > 180s (stall timeout)
        last_activity = job.updated_at or job.started_at or job.created_at
        if last_activity:
            stalled_seconds = (now - last_activity).total_seconds()
            if stalled_seconds > 180.0:
                logger.warning(f"Scraper job {job.id} stalled (no progress for {stalled_seconds:.1f}s). Terminating task.")
                task.cancel()
                job.status = "failed"
                job.error_message = f"Scraper worker stalled (no progress for {int(stalled_seconds)}s)."
                job.completed_at = now
                self.scraper_repo.update_job(job)
                ScraperService._active_tasks.pop(job.id, None)

        return job

    def reconcile_orphaned_jobs(self) -> int:
        """
        Scans repository on startup or initialization for jobs left in 'queued' or 'running' state
        without an active worker task, and marks them failed with an interruption diagnostic.
        """
        jobs = self.scraper_repo.list_jobs(limit=100)
        reconciled = 0
        now = datetime.now(timezone.utc)
        for job in jobs:
            if job.status in ("queued", "running") and job.id not in ScraperService._active_tasks:
                if job.products_persisted >= job.target_count and job.target_count > 0:
                    job.status = "completed"
                elif job.products_persisted > 0:
                    job.status = "completed"
                else:
                    job.status = "failed"
                    if not job.error_message:
                        job.error_message = "Scraper worker was interrupted before completion."
                job.completed_at = job.completed_at or now
                self.scraper_repo.update_job(job)
                reconciled += 1
        if reconciled > 0:
            logger.info(f"Reconciled {reconciled} orphaned scraper jobs.")
        return reconciled

    def get_job_status(self, job_id: str) -> Optional[ScraperJobProgressResponse]:
        job = self.scraper_repo.get_job(job_id)
        if not job:
            return None
        job = self._check_and_recover_stalled_job(job)
        return self._to_progress_response(job)

    def pause_job(self, job_id: str) -> bool:
        job = self.scraper_repo.get_job(job_id)
        if not job or job.status != "running":
            return False
        job.status = "paused"
        self.scraper_repo.update_job(job)
        return True

    def stop_job(self, job_id: str) -> bool:
        job = self.scraper_repo.get_job(job_id)
        if not job:
            return False
        if job_id in ScraperService._active_tasks:
            t = ScraperService._active_tasks[job_id]
            if not t.done():
                t.cancel()
        job.status = "stopped"
        job.completed_at = datetime.now(timezone.utc)
        self.scraper_repo.update_job(job)
        return True

    def list_jobs(
        self,
        marketplace: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> ScraperJobListResponse:
        jobs = self.scraper_repo.list_jobs(marketplace=marketplace, status=status, limit=limit, offset=offset)
        recovered_jobs = [self._check_and_recover_stalled_job(j) for j in jobs]
        total = self.scraper_repo.count_jobs(marketplace=marketplace, status=status)
        return ScraperJobListResponse(
            total=total,
            jobs=[self._to_progress_response(j) for j in recovered_jobs]
        )

    def get_marketplace_health(self) -> List[ScraperMarketplaceHealth]:
        return self.scraper_repo.list_marketplace_health()

    def list_products(
        self,
        marketplace: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = "newest",
        page: int = 1,
        limit: int = 50
    ) -> ScraperProductListResponse:
        offset = (page - 1) * limit
        platform_filter = marketplace if marketplace and marketplace != "all" else None

        products = self.marketplace_repo.list_products(
            platform=platform_filter,
            category=category,
            search=search,
            limit=limit,
            offset=offset
        )

        total = self.marketplace_repo.count_products(
            platform=platform_filter,
            category=category
        )

        items = [self._to_product_item(p) for p in products]
        return ScraperProductListResponse(
            total=total,
            products=items
        )

    def get_product(self, product_id: str, marketplace: Optional[str] = None) -> Optional[ScraperProductItem]:
        platform = marketplace or "daraz"
        p = self.marketplace_repo.get_product(platform=platform, product_id=product_id)
        if not p:
            # Try searching across all platforms
            all_prods = self.marketplace_repo.list_products(limit=100)
            for item in all_prods:
                if item.product_id == product_id or item.id == product_id:
                    p = item
                    break
        if not p:
            return None
        return self._to_product_item(p)

    def get_raw_payload(self, product_id: str, marketplace: Optional[str] = None) -> Optional[RawScrapedDataResponse]:
        platform = marketplace or "daraz"
        raw = self.scraper_repo.get_raw_payload(marketplace=platform, product_id=product_id)
        if not raw:
            # Fallback to checking MarketplaceProduct.raw_source_data
            p = self.marketplace_repo.get_product(platform=platform, product_id=product_id)
            if p and p.raw_source_data:
                now = datetime.now(timezone.utc)
                return RawScrapedDataResponse(
                    id=f"raw_{platform}_{product_id}",
                    marketplace=platform,
                    product_id=product_id,
                    source_url=p.product_url or "",
                    canonical_url=p.product_url,
                    parser_version="2.0.0",
                    extraction_status="complete",
                    quality_status="valid",
                    confidence_score=1.0,
                    scraped_at=p.last_synced_at or now,
                    raw_payload=p.raw_source_data,
                    normalized_payload=p.raw_source_data
                )
            return None

        return RawScrapedDataResponse(
            id=raw.id,
            marketplace=raw.marketplace,
            product_id=raw.product_id,
            crawl_job_id=raw.crawl_job_id,
            source_url=raw.source_url,
            canonical_url=raw.canonical_url,
            parser_version=raw.parser_version,
            extraction_status=raw.extraction_status,
            quality_status=raw.quality_status,
            confidence_score=raw.confidence_score,
            scraped_at=raw.scraped_at,
            raw_payload=raw.raw_payload,
            normalized_payload=raw.normalized_payload
        )

    def get_product_history(self, product_id: str, marketplace: Optional[str] = None) -> ScraperProductHistoryResponse:
        platform = marketplace or "daraz"
        snaps = self.marketplace_repo.get_snapshots(platform=platform, product_id=product_id)
        items = [
            ScraperHistoricalSnapshotItem(
                id=s.id,
                product_id=s.product_id,
                platform=s.platform,
                price=s.price,
                original_price=s.original_price if s.original_price > 0 else None,
                discount=s.discount if s.discount > 0 else None,
                rating=s.rating if s.rating > 0 else None,
                review_count=s.review_count,
                stock_status=s.stock_status,
                observed_at=s.observed_at
            )
            for s in snaps
        ]
        return ScraperProductHistoryResponse(
            product_id=product_id,
            marketplace=platform,
            total_snapshots=len(items),
            snapshots=items
        )
