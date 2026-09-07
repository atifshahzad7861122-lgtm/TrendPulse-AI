"""Bounded asynchronous worker pool for resilient task processing."""

import asyncio
from typing import Any, Callable, List, Optional
from app.core.logging import logger
from app.orchestration.models import CrawlTask, TaskState
from app.orchestration.queue import DurableTaskQueue


class WorkerPool:
    """
    Manages a pool of bounded asynchronous worker coroutines.
    Ensures failure isolation, graceful shutdown, and task progress accounting.
    """

    def __init__(
        self,
        queue: DurableTaskQueue,
        process_task_fn: Callable[[CrawlTask, int], Any],
        max_workers: int = 4,
    ):
        self.queue = queue
        self.process_task_fn = process_task_fn
        self.max_workers = max_workers
        self._workers: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._active_workers = 0

    async def start(self) -> None:
        """Start the worker pool."""
        self._shutdown_event.clear()
        self._workers = [
            asyncio.create_task(self._worker_loop(worker_id=i + 1))
            for i in range(self.max_workers)
        ]
        logger.info(f"WorkerPool started with {self.max_workers} active workers.")

    async def _worker_loop(self, worker_id: int) -> None:
        """Continuous execution loop for a single worker."""
        while not self._shutdown_event.is_set():
            task: Optional[CrawlTask] = await self.queue.pop_next()
            if not task:
                # If no task ready, check if any pending or retrying
                if not self.queue.has_pending_or_processing():
                    break
                await asyncio.sleep(0.2)
                continue

            self._active_workers += 1
            try:
                await self.process_task_fn(task, worker_id)
            except asyncio.CancelledError:
                logger.warning(f"Worker {worker_id} cancelled during task {task.task_id}")
                await self.queue.mark_failed(task.task_id, "Worker task cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} encountered uncaught error on {task.url}: {e}", exc_info=True)
                await self.queue.mark_failed(task.task_id, f"Uncaught worker exception: {e}")
            finally:
                self._active_workers -= 1

        logger.debug(f"Worker {worker_id} finished execution loop.")

    async def wait_idle(self) -> None:
        """Wait until all tasks in the queue are completed, failed, or challenged."""
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

    async def stop(self) -> None:
        """Signal graceful shutdown and cancel remaining tasks."""
        self._shutdown_event.set()
        for w in self._workers:
            if not w.done():
                w.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("WorkerPool stopped.")

    @property
    def active_worker_count(self) -> int:
        return self._active_workers
