"""Durable, persistent task queue for production crawl orchestration."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.core.logging import logger
from app.orchestration.models import CrawlTask, TaskState


class DurableTaskQueue:
    """
    Disk-backed persistent task queue supporting priority scheduling,
    state persistence, crash recovery, and URL/product deduplication.
    """

    def __init__(self, crawl_id: str, checkpoints_dir: str = "data/checkpoints/orchestrator"):
        self.crawl_id = crawl_id
        self.checkpoints_dir = Path(checkpoints_dir)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.checkpoints_dir / f"queue_{crawl_id}.json"

        self._tasks: Dict[str, CrawlTask] = {}
        self._seen_urls: Set[str] = set()
        self._seen_product_ids: Set[str] = set()
        self._lock = asyncio.Lock()

        # Load existing state if resuming
        if self.checkpoint_file.exists():
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load queue checkpoint from disk on restart."""
        try:
            raw_text = self.checkpoint_file.read_text(encoding="utf-8")
            data = json.loads(raw_text)
            for item in data.get("tasks", []):
                task = CrawlTask(**item)
                # If was processing when process crashed, reset to PENDING for recovery
                if task.status == TaskState.PROCESSING:
                    task.status = TaskState.PENDING
                self._tasks[task.task_id] = task
                self._seen_urls.add(task.url)
                if task.product_id:
                    self._seen_product_ids.add(task.product_id)
            logger.info(f"Loaded {len(self._tasks)} tasks from queue checkpoint {self.checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to load queue checkpoint {self.checkpoint_file}: {e}")

    def save_checkpoint(self) -> None:
        """Atomically persist current queue state to disk."""
        try:
            data = {
                "crawl_id": self.crawl_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "tasks": [t.model_dump(mode="json") for t in self._tasks.values()],
            }
            tmp_path = self.checkpoint_file.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            tmp_path.replace(self.checkpoint_file)
        except Exception as e:
            logger.error(f"Failed to save queue checkpoint: {e}")

    async def enqueue(self, task: CrawlTask) -> bool:
        """Add a single task to the queue if not already seen."""
        async with self._lock:
            if task.url in self._seen_urls:
                return False
            if task.product_id and task.product_id in self._seen_product_ids:
                return False

            self._tasks[task.task_id] = task
            self._seen_urls.add(task.url)
            if task.product_id:
                self._seen_product_ids.add(task.product_id)
            self.save_checkpoint()
            return True

    async def enqueue_many(self, tasks: List[CrawlTask]) -> int:
        """Batch enqueue unique tasks."""
        added_count = 0
        async with self._lock:
            for task in tasks:
                if task.url not in self._seen_urls and (not task.product_id or task.product_id not in self._seen_product_ids):
                    self._tasks[task.task_id] = task
                    self._seen_urls.add(task.url)
                    if task.product_id:
                        self._seen_product_ids.add(task.product_id)
                    added_count += 1
            if added_count > 0:
                self.save_checkpoint()
        return added_count

    async def pop_next(self) -> Optional[CrawlTask]:
        """
        Retrieve highest priority ready task (PENDING or ready RETRY_PENDING).
        """
        now = datetime.now(timezone.utc)
        async with self._lock:
            ready_tasks: List[CrawlTask] = []
            for t in self._tasks.values():
                if t.status == TaskState.PENDING:
                    ready_tasks.append(t)
                elif t.status == TaskState.RETRY_PENDING:
                    if not t.next_retry_at or t.next_retry_at <= now:
                        ready_tasks.append(t)

            if not ready_tasks:
                return None

            # Sort by priority (asc) then created_at (asc)
            ready_tasks.sort(key=lambda x: (x.priority, x.created_at))
            chosen = ready_tasks[0]
            chosen.status = TaskState.PROCESSING
            chosen.started_at = now
            chosen.attempt_count += 1
            self.save_checkpoint()
            return chosen

    async def mark_completed(self, task_id: str, product_id: Optional[str] = None) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskState.COMPLETED
                task.completed_at = datetime.now(timezone.utc)
                if product_id:
                    task.product_id = product_id
                    self._seen_product_ids.add(product_id)
                self.save_checkpoint()

    async def mark_failed(self, task_id: str, error: str) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskState.FAILED
                task.last_error = error
                task.completed_at = datetime.now(timezone.utc)
                self.save_checkpoint()

    async def mark_challenged(self, task_id: str, reason: str) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskState.CHALLENGED
                task.last_error = f"Bot challenge: {reason}"
                self.save_checkpoint()

    async def mark_retry_pending(self, task_id: str, next_retry_at: datetime, error: str) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskState.RETRY_PENDING
                task.next_retry_at = next_retry_at
                task.last_error = error
                self.save_checkpoint()

    async def mark_cancelled(self, task_id: str) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskState.CANCELLED
                task.completed_at = datetime.now(timezone.utc)
                self.save_checkpoint()

    def get_counts(self) -> Dict[TaskState, int]:
        counts = {state: 0 for state in TaskState}
        for task in self._tasks.values():
            counts[task.status] += 1
        return counts

    def has_pending_or_processing(self) -> bool:
        for t in self._tasks.values():
            if t.status in (TaskState.PENDING, TaskState.PROCESSING, TaskState.RETRY_PENDING):
                return True
        return False

    def get_all_tasks(self) -> List[CrawlTask]:
        return list(self._tasks.values())
