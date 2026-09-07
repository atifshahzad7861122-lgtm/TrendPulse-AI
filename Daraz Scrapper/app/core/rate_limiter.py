"""Centralized async rate limiting, host isolation, and concurrency management."""

import asyncio
import random
import time
from typing import Dict, Optional
from urllib.parse import urlparse

from app.core.config import Settings, get_settings
from app.core.logging import logger


class AsyncRateLimiter:
    """Controls request pacing and maximum concurrency to ensure polite, non-disruptive scraping."""

    def __init__(
        self,
        min_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        max_concurrency: Optional[int] = None,
        settings: Optional[Settings] = None,
    ):
        cfg = settings or get_settings()
        self.min_delay = min_delay if min_delay is not None else cfg.REQUEST_DELAY_MIN
        self.max_delay = max_delay if max_delay is not None else cfg.REQUEST_DELAY_MAX
        self.max_concurrency = max_concurrency if max_concurrency is not None else cfg.MAX_CONCURRENCY

        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._last_request_time: float = 0.0
        self._host_last_request_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, url: Optional[str] = None, retry_after: Optional[float] = None) -> float:
        """Wait for the rate limiter interval with randomized jitter and return sleep duration."""
        async with self._lock:
            now = time.monotonic()
            host = urlparse(url).netloc.lower() if url else "global"
            last_time = max(self._last_request_time, self._host_last_request_times.get(host, 0.0))
            elapsed = now - last_time

            # Check if an explicit Retry-After was provided
            if retry_after is not None and retry_after > 0:
                target_delay = retry_after
            else:
                # Compute random delay with jitter within configured range
                if self.min_delay < self.max_delay:
                    target_delay = random.uniform(self.min_delay, self.max_delay)
                else:
                    target_delay = self.min_delay

            delay_needed = max(0.0, target_delay - elapsed)
            if delay_needed > 0:
                logger.debug(
                    f"Rate limit delay active for '{host}': sleeping {delay_needed:.3f}s",
                    extra={"event": "rate_limit_sleep", "host": host, "duration_ms": delay_needed * 1000},
                )
                await asyncio.sleep(delay_needed)

            current_time = time.monotonic()
            self._last_request_time = current_time
            self._host_last_request_times[host] = current_time
            return delay_needed

    async def __aenter__(self):
        await self._semaphore.acquire()
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._semaphore.release()
