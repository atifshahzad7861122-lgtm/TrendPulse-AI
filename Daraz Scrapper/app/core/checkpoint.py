"""Crawl checkpointing and resume management for failure recovery."""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional

from app.core.constants import CrawlStatus
from app.core.exceptions import CheckpointError
from app.core.logging import logger
from app.models.checkpoint import CrawlCheckpoint
from app.storage.base import BaseStorage


class CheckpointManager:
    """Coordinates periodic snapshot creation and crash recovery for long-running crawls."""

    def __init__(
        self,
        storage: BaseStorage,
        crawl_id: str,
        target: str,
        checkpoint_interval: int = 50,
    ):
        self.storage = storage
        self.crawl_id = crawl_id
        self.target = target
        self.checkpoint_interval = checkpoint_interval

        self._checkpoint: CrawlCheckpoint = CrawlCheckpoint(
            crawl_id=crawl_id,
            target=target,
            status=CrawlStatus.RUNNING,
        )
        self._items_since_save: int = 0
        self._lock = asyncio.Lock()

    @property
    def current_checkpoint(self) -> CrawlCheckpoint:
        return self._checkpoint

    async def record_progress(
        self,
        position: int,
        item_id: Optional[str] = None,
        url: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """Update active progress counter and trigger save when interval is reached."""
        async with self._lock:
            self._checkpoint.current_position = position
            if success:
                self._checkpoint.completed_items += 1
                if item_id:
                    self._checkpoint.last_successful_item = item_id
            else:
                self._checkpoint.failed_items += 1

            if url:
                self._checkpoint.last_processed_url = url

            self._checkpoint.timestamp = datetime.now(timezone.utc)
            self._items_since_save += 1

            if self._items_since_save >= self.checkpoint_interval:
                await self._save_checkpoint_unlocked()

    async def _save_checkpoint_unlocked(self, status: Optional[CrawlStatus] = None) -> CrawlCheckpoint:
        """Internal save routine assuming lock is already held."""
        if status:
            self._checkpoint.status = status
        self._checkpoint.timestamp = datetime.now(timezone.utc)

        try:
            await self.storage.save_checkpoint(self._checkpoint)
            self._items_since_save = 0
            logger.info(
                f"Checkpoint persisted for crawl '{self.crawl_id}' at pos {self._checkpoint.current_position} "
                f"({self._checkpoint.completed_items} completed, {self._checkpoint.failed_items} failed)",
                extra={
                    "event": "checkpoint_saved",
                    "crawl_id": self.crawl_id,
                    "position": self._checkpoint.current_position,
                    "completed": self._checkpoint.completed_items,
                },
            )
            return self._checkpoint
        except Exception as e:
            raise CheckpointError(f"Failed to persist checkpoint for {self.crawl_id}: {e}") from e

    async def save_checkpoint(self, status: Optional[CrawlStatus] = None) -> CrawlCheckpoint:
        """Persist active checkpoint to storage backend."""
        async with self._lock:
            return await self._save_checkpoint_unlocked(status=status)

    async def resume_checkpoint(self) -> Optional[CrawlCheckpoint]:
        """Load and restore previous state from storage for resumption."""
        async with self._lock:
            try:
                cp = await self.storage.get_checkpoint(self.crawl_id)
                if cp:
                    self._checkpoint = cp
                    logger.info(
                        f"Resumed crawl '{self.crawl_id}' from checkpoint at pos {cp.current_position} "
                        f"({cp.completed_items} already completed)",
                        extra={"event": "checkpoint_resumed", "crawl_id": self.crawl_id, "position": cp.current_position},
                    )
                    return cp
                return None
            except Exception as e:
                raise CheckpointError(f"Failed to resume checkpoint for {self.crawl_id}: {e}") from e
