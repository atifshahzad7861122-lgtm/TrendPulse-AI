"""Unit tests for ConcurrencyDispatcher and AdaptiveRateLimiter."""

import asyncio
import time
import pytest

from app.crawling.dispatcher import AdaptiveRateLimiter, ConcurrencyDispatcher
from app.crawling.models import CrawlRequest


@pytest.mark.asyncio
async def test_adaptive_rate_limiter_pacing():
    limiter = AdaptiveRateLimiter(default_rps=10.0)  # 100ms per request
    url = "https://www.amazon.com/dp/B001"

    start = time.monotonic()
    await limiter.acquire(url)
    await limiter.acquire(url)
    duration = time.monotonic() - start

    assert duration >= 0.08  # Enforced minimum delay


@pytest.mark.asyncio
async def test_concurrency_dispatcher_bounded():
    dispatcher = ConcurrencyDispatcher(max_concurrency=3)
    active_count = 0
    max_active_observed = 0

    async def mock_task(req: CrawlRequest):
        nonlocal active_count, max_active_observed
        active_count += 1
        max_active_observed = max(max_active_observed, active_count)
        await asyncio.sleep(0.05)
        active_count -= 1
        return req.url

    tasks = [lambda i=i: mock_task(CrawlRequest(url=f"https://store.myshopify.com/{i}")) for i in range(10)]
    results = await dispatcher.dispatch_all(tasks)

    assert len(results) == 10
    assert max_active_observed <= 3
