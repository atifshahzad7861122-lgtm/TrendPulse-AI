"""Crawl job execution manager, lifecycle coordinator, and checkpoint recovery handler."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from app.core.checkpoint import CheckpointManager, CrawlCheckpoint
from app.core.constants import CrawlStatus, CrawlType
from app.core.exceptions import CrawlError
from app.core.logging import logger
from app.core.runtime import get_current_crawl_id, runtime_metrics, set_current_crawl_id
from app.models.crawl import CrawlRun, CrawlStats
from app.storage.base import BaseStorage


class CrawlJob:
    """Manages the end-to-end execution lifecycle, metrics, and checkpointing of a crawl session."""

    def __init__(
        self,
        storage: BaseStorage,
        crawl_type: CrawlType = CrawlType.FULL,
        crawl_id: Optional[str] = None,
        target: str = "all",
        checkpoint_interval: int = 50,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.storage = storage
        self.crawl_id = crawl_id or str(uuid.uuid4())
        self.crawl_type = crawl_type
        self.target = target
        self.checkpoint_interval = checkpoint_interval
        self.metadata = metadata or {}

        self.crawl_run: Optional[CrawlRun] = None
        self.checkpoint_manager = CheckpointManager(
            storage=self.storage,
            crawl_id=self.crawl_id,
            target=self.target,
            checkpoint_interval=self.checkpoint_interval,
        )

    async def start(self) -> CrawlRun:
        """Create and initialize the crawl run in storage."""
        set_current_crawl_id(self.crawl_id)
        self.crawl_run = CrawlRun(
            crawl_id=self.crawl_id,
            crawl_type=self.crawl_type,
            status=CrawlStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            metadata=self.metadata,
        )
        self.crawl_run = await self.storage.create_crawl_run(self.crawl_run)
        logger.info(
            f"Crawl job started: {self.crawl_id} (Type: {self.crawl_type}, Target: {self.target})",
            extra={
                "crawl_id": self.crawl_id,
                "status": self.crawl_run.status,
                "target": self.target,
                "event": "crawl_started",
            },
        )
        return self.crawl_run

    async def resume(self) -> Optional[CrawlCheckpoint]:
        """Attempt to restore existing checkpoint state for resumed crawling."""
        set_current_crawl_id(self.crawl_id)
        cp = await self.checkpoint_manager.resume_checkpoint()
        if cp:
            existing_run = await self.storage.get_crawl_run(self.crawl_id)
            if existing_run:
                self.crawl_run = existing_run
                self.crawl_run.status = CrawlStatus.RUNNING
                await self.storage.update_crawl_run(self.crawl_id, status=CrawlStatus.RUNNING)
            else:
                self.crawl_run = CrawlRun(
                    crawl_id=self.crawl_id,
                    crawl_type=self.crawl_type,
                    status=CrawlStatus.RUNNING,
                    started_at=cp.timestamp,
                    items_processed=cp.completed_items,
                    items_failed=cp.failed_items,
                    metadata=self.metadata,
                )
                await self.storage.create_crawl_run(self.crawl_run)
        return cp

    async def record_discovery(self, count: int = 1) -> None:
        """Increment count of discovered items."""
        if not self.crawl_run:
            raise CrawlError("Crawl run not initialized. Call start() or resume() first.")
        self.crawl_run.items_discovered += count
        await runtime_metrics.record_discovery(count)

    async def record_processed(
        self,
        position: int,
        item_id: Optional[str] = None,
        url: Optional[str] = None,
        count: int = 1,
    ) -> None:
        """Record successful item processing and update checkpoint tracker."""
        if not self.crawl_run:
            raise CrawlError("Crawl run not initialized. Call start() or resume() first.")

        self.crawl_run.items_processed += count
        await runtime_metrics.record_product_extracted(count)
        await self.checkpoint_manager.record_progress(
            position=position,
            item_id=item_id,
            url=url,
            success=True,
        )

    async def record_failure(
        self,
        position: int,
        url: Optional[str] = None,
        count: int = 1,
        is_error: bool = True,
    ) -> None:
        """Record failed item processing and/or error count."""
        if not self.crawl_run:
            raise CrawlError("Crawl run not initialized. Call start() or resume() first.")

        self.crawl_run.items_failed += count
        if is_error:
            self.crawl_run.error_count += count

        await self.checkpoint_manager.record_progress(
            position=position,
            url=url,
            success=False,
        )

    async def request_manual_intervention(self, reason: str, url: Optional[str] = None) -> None:
        """Pause crawl session and mark status as MANUAL_INTERVENTION."""
        if not self.crawl_run:
            raise CrawlError("Crawl run not initialized.")

        self.crawl_run.status = CrawlStatus.MANUAL_INTERVENTION
        await self.storage.update_crawl_run(
            crawl_id=self.crawl_id,
            status=CrawlStatus.MANUAL_INTERVENTION,
        )
        await self.checkpoint_manager.save_checkpoint(status=CrawlStatus.MANUAL_INTERVENTION)
        await runtime_metrics.record_manual_intervention()

        logger.warning(
            f"Crawl {self.crawl_id} paused for MANUAL_INTERVENTION: {reason}",
            extra={
                "crawl_id": self.crawl_id,
                "event": "manual_intervention_requested",
                "reason": reason,
                "url": url,
            },
        )

    async def checkpoint(self) -> CrawlCheckpoint:
        """Manually trigger checkpoint persistence."""
        if self.crawl_run:
            await self.storage.update_crawl_run(
                crawl_id=self.crawl_id,
                items_discovered=self.crawl_run.items_discovered,
                items_processed=self.crawl_run.items_processed,
                items_failed=self.crawl_run.items_failed,
                error_count=self.crawl_run.error_count,
            )
        return await self.checkpoint_manager.save_checkpoint()

    async def finish(self, status: CrawlStatus = CrawlStatus.COMPLETED) -> CrawlRun:
        """Complete the crawl job and update terminal status."""
        if not self.crawl_run:
            raise CrawlError("Crawl run not initialized.")

        self.crawl_run.status = status
        self.crawl_run.finished_at = datetime.now(timezone.utc)

        await self.checkpoint_manager.save_checkpoint(status=status)
        await self.storage.update_crawl_run(
            crawl_id=self.crawl_id,
            status=self.crawl_run.status,
            finished_at=self.crawl_run.finished_at,
            items_discovered=self.crawl_run.items_discovered,
            items_processed=self.crawl_run.items_processed,
            items_failed=self.crawl_run.items_failed,
            error_count=self.crawl_run.error_count,
        )

        logger.info(
            f"Crawl job finished: {self.crawl_id} (Status: {status})",
            extra={
                "crawl_id": self.crawl_id,
                "status": status,
                "items_processed": self.crawl_run.items_processed,
                "items_failed": self.crawl_run.items_failed,
                "event": "crawl_finished",
            },
        )
        set_current_crawl_id(None)
        return self.crawl_run

    def get_stats(self) -> CrawlStats:
        """Compute active stats for the crawl job."""
        if not self.crawl_run:
            return CrawlStats(crawl_id=self.crawl_id)

        now = self.crawl_run.finished_at or datetime.now(timezone.utc)
        duration = max(0.001, (now - self.crawl_run.started_at).total_seconds())
        items_per_min = (self.crawl_run.items_processed / duration) * 60.0
        total_attempted = self.crawl_run.items_processed + self.crawl_run.items_failed
        success_rate = (
            (self.crawl_run.items_processed / total_attempted * 100.0)
            if total_attempted > 0
            else 100.0
        )

        return CrawlStats(
            crawl_id=self.crawl_id,
            duration_seconds=duration,
            items_per_minute=round(items_per_min, 2),
            success_rate_percentage=round(success_rate, 2),
        )
