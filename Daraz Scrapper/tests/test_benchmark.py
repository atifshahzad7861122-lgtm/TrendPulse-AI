"""Automated pytest test ensuring benchmarks execute within expected performance bounds."""

import pytest
from scripts.benchmark_module1 import (
    benchmark_batch_storage,
    benchmark_checkpoint_operations,
    benchmark_concurrent_http,
    benchmark_deduplication,
)


@pytest.mark.asyncio
async def test_benchmark_http_concurrency():
    duration = await benchmark_concurrent_http(n_requests=30, concurrency=5)
    assert duration < 5.0  # Must complete 30 mocked requests well under 5 seconds


@pytest.mark.asyncio
async def test_benchmark_batch_storage_performance():
    duration = await benchmark_batch_storage(n_products=200, n_reviews=1000)
    assert duration < 2.0  # Must persist 1,200 records in < 2 seconds


def test_benchmark_deduplication_speed():
    duration = benchmark_deduplication(n_items=2000)
    assert duration < 1.0  # Must perform 4,000 dedup checks in < 1 second


@pytest.mark.asyncio
async def test_benchmark_checkpoint_latency():
    duration = await benchmark_checkpoint_operations(n_checkpoints=50)
    assert duration < 1.0  # Must perform 50 checkpoint writes in < 1 second
