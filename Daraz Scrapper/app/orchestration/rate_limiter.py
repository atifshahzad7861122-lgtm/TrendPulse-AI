"""Marketplace-specific rate limiting, concurrency gates, and jitter delays."""

import asyncio
from contextlib import asynccontextmanager
import random
import time
from typing import Dict

from app.crawling.models import MarketplaceType
from app.orchestration.models import MarketplaceLimitConfig


class MarketplaceRateLimiter:
    """
    Manages per-marketplace request rates, HTTP & Browser concurrency semaphores,
    and anti-bot jitter delays to maintain respectful crawl pacing.
    """

    def __init__(self, limits: Dict[MarketplaceType, MarketplaceLimitConfig]):
        self.limits = limits
        self._http_semaphores: Dict[MarketplaceType, asyncio.Semaphore] = {}
        self._browser_semaphores: Dict[MarketplaceType, asyncio.Semaphore] = {}
        self._last_request_times: Dict[MarketplaceType, float] = {}
        self._lock = asyncio.Lock()

        for m_type, conf in limits.items():
            self._http_semaphores[m_type] = asyncio.Semaphore(conf.max_http_concurrency)
            self._browser_semaphores[m_type] = asyncio.Semaphore(conf.max_browser_concurrency)
            self._last_request_times[m_type] = 0.0

    @asynccontextmanager
    async def throttle(self, marketplace: MarketplaceType, is_browser: bool = False):
        """
        Async context manager acquiring the appropriate concurrency slot,
        enforcing inter-request pacing and random jitter.
        """
        conf = self.limits.get(marketplace, MarketplaceLimitConfig())
        semaphore = (
            self._browser_semaphores.get(marketplace)
            if is_browser and marketplace in self._browser_semaphores
            else self._http_semaphores.get(marketplace, asyncio.Semaphore(conf.max_http_concurrency))
        )

        async with semaphore:
            # 1. Enforce minimum request spacing based on requests_per_second
            min_interval = 1.0 / conf.requests_per_second if conf.requests_per_second > 0 else 0.5
            async with self._lock:
                now = time.time()
                elapsed = now - self._last_request_times.get(marketplace, 0.0)
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                self._last_request_times[marketplace] = time.time()

            # 2. Add randomized human jitter delay
            if conf.max_delay_ms > conf.min_delay_ms >= 0:
                jitter_ms = random.randint(conf.min_delay_ms, conf.max_delay_ms)
                await asyncio.sleep(jitter_ms / 1000.0)

            yield
