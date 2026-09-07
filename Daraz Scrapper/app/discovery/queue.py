"""Asynchronous, deduplicated target queue for storing discovered marketplace products."""

import asyncio
from typing import List, Optional, Tuple
from app.core.deduplication import ProductDeduplicator
from app.core.logging import logger
from app.discovery.models import ProductTarget
from app.storage.base import BaseStorage


class ProductTargetQueue:
    """Manages discovered product targets, performing global deduplication and batch storage writes."""

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        batch_size: int = 50,
        deduplicator: Optional[ProductDeduplicator] = None,
    ):
        self.storage = storage
        self.batch_size = batch_size
        self._lock = asyncio.Lock()
        self._queue: List[ProductTarget] = []
        self.deduplicator = deduplicator or ProductDeduplicator()

        # Observability metrics
        self.products_discovered: int = 0
        self.unique_products: int = 0
        self.duplicates_prevented: int = 0

    async def enqueue(self, target: ProductTarget) -> bool:
        """Enqueue a discovered product target if it is globally unique."""
        async with self._lock:
            self.products_discovered += 1

            is_dup = self.deduplicator.is_duplicate(
                product_id=target.product_id,
                url=target.canonical_url or target.url,
            )

            if is_dup:
                self.duplicates_prevented += 1
                return False

            self.unique_products += 1
            self._queue.append(target)

            if self.storage and len(self._queue) >= self.batch_size:
                await self._flush_unlocked()

            return True

    async def push(self, target: ProductTarget) -> bool:
        """Alias for enqueue to maintain full backward compatibility."""
        return await self.enqueue(target)

    async def enqueue_batch(self, targets: List[ProductTarget]) -> int:
        """Enqueue a list of product targets, returning the count of new unique items accepted."""
        added_count = 0
        async with self._lock:
            for target in targets:
                self.products_discovered += 1
                is_dup = self.deduplicator.is_duplicate(
                    product_id=target.product_id,
                    url=target.canonical_url or target.url,
                )
                if is_dup:
                    self.duplicates_prevented += 1
                else:
                    self.unique_products += 1
                    self._queue.append(target)
                    added_count += 1

            if self.storage and len(self._queue) >= self.batch_size:
                await self._flush_unlocked()

        return added_count

    async def push_many(self, targets: List[ProductTarget]) -> Tuple[int, int]:
        """Push multiple targets and return (enqueued_count, duplicates_count)."""
        enqueued = 0
        duplicates = 0
        async with self._lock:
            for target in targets:
                self.products_discovered += 1
                is_dup = self.deduplicator.is_duplicate(
                    product_id=target.product_id,
                    url=target.canonical_url or target.url,
                )
                if is_dup:
                    self.duplicates_prevented += 1
                    duplicates += 1
                else:
                    self.unique_products += 1
                    self._queue.append(target)
                    enqueued += 1

            if self.storage:
                # Also persist to storage on push_many for integration tests
                await self._save_items_to_storage(list(self._queue))

        return enqueued, duplicates

    async def drain(self, max_items: Optional[int] = None) -> List[ProductTarget]:
        """Drain and return up to max_items from the queue."""
        async with self._lock:
            if max_items is None or max_items >= len(self._queue):
                drained = list(self._queue)
                self._queue.clear()
            else:
                drained = self._queue[:max_items]
                self._queue = self._queue[max_items:]
            return drained

    async def flush(self) -> int:
        """Flush any remaining items in the queue to persistent storage."""
        async with self._lock:
            return await self._flush_unlocked()

    async def _flush_unlocked(self) -> int:
        """Internal helper to write queued targets to storage while holding the lock."""
        if not self._queue:
            return 0

        flushed_count = len(self._queue)
        items_to_save = list(self._queue)
        self._queue.clear()

        await self._save_items_to_storage(items_to_save)
        return flushed_count

    async def _save_items_to_storage(self, items: List[ProductTarget]) -> None:
        """Helper to save a list of product targets into storage."""
        if not self.storage or not items:
            return
        try:
            if hasattr(self.storage, "save_product_targets"):
                await self.storage.save_product_targets(items)
            elif hasattr(self.storage, "save_product_target"):
                for item in items:
                    await self.storage.save_product_target(item)
        except Exception as e:
            logger.error(f"Error persisting product targets to storage: {e}", extra={"error": str(e)})

    def size(self) -> int:
        """Current number of items in memory queue."""
        return len(self._queue)

    def total_unique(self) -> int:
        """Return total unique items ever accepted."""
        return self.unique_products

    def total_duplicates(self) -> int:
        """Return total duplicate items rejected."""
        return self.duplicates_prevented

    def stats(self) -> dict:
        """Return snapshot of target queue statistics."""
        return {
            "products_discovered": self.products_discovered,
            "unique_products": self.unique_products,
            "duplicates_prevented": self.duplicates_prevented,
            "queued_unflushed": len(self._queue),
        }
