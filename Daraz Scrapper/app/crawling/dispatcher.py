"""Concurrency dispatching and adaptive token-bucket rate limiting."""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional
from urllib.parse import urlparse

from app.core.logging import logger


class AdaptiveRateLimiter:
    """
    Per-domain token-bucket rate limiter.
    Ensures safe request pacing across diverse marketplace domains.
    """

    def __init__(self, default_rps: float = 2.0, domain_rps: Optional[Dict[str, float]] = None):
        self.default_rps = max(0.1, default_rps)
        self.domain_rps = domain_rps or {}
        self._last_hit: Dict[str, float] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower() or "default"
        except Exception:
            return "default"

    async def acquire(self, url: str) -> None:
        """Wait until enough time has elapsed to safely hit the domain."""
        domain = self._get_domain(url)
        rps = self.domain_rps.get(domain, self.default_rps)
        delay = 1.0 / rps

        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()

        async with self._locks[domain]:
            now = time.monotonic()
            last = self._last_hit.get(domain, 0.0)
            elapsed = now - last
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
            self._last_hit[domain] = time.monotonic()


class ConcurrencyDispatcher:
    """
    Bounded concurrency dispatcher inspired by Crawl4AI's memory-adaptive dispatcher.
    Prevents overwhelming target sites and system resources.
    """

    def __init__(self, max_concurrency: int = 5, rate_limiter: Optional[AdaptiveRateLimiter] = None):
        self.max_concurrency = max(1, max_concurrency)
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        self.rate_limiter = rate_limiter or AdaptiveRateLimiter()

    async def dispatch(self, coro_func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any) -> Any:
        """Execute a coroutine within bounded semaphore and domain rate limits."""
        url = kwargs.get("url") or (args[0].url if args and hasattr(args[0], "url") else None)
        if url:
            await self.rate_limiter.acquire(url)

        async with self.semaphore:
            return await coro_func(*args, **kwargs)

    async def dispatch_all(
        self,
        tasks: List[Callable[..., Coroutine[Any, Any, Any]]],
    ) -> List[Any]:
        """Dispatch list of asynchronous tasks concurrently with bounded limits."""
        return await asyncio.gather(*(self.dispatch(t) for t in tasks), return_exceptions=True)
