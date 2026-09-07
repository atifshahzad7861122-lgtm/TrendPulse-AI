"""Module 1 Performance and Scalability Benchmark Script."""

import asyncio
import os
from pathlib import Path
import sys
import time
from typing import List
import httpx

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients.http_client import AsyncHttpClient
from app.core.checkpoint import CheckpointManager
from app.core.config import Settings
from app.core.deduplication import ProductDeduplicator, ReviewDeduplicator
from app.models.image import Image
from app.models.product import Product
from app.models.review import Review
from app.storage.repository import InMemoryStorage


async def benchmark_concurrent_http(n_requests: int = 50, concurrency: int = 10) -> float:
    """Benchmark async HTTP client throughput under bounded concurrency."""
    settings = Settings(MAX_CONCURRENCY=concurrency, REQUEST_DELAY_MIN=0.0, REQUEST_DELAY_MAX=0.0, ENVIRONMENT="testing")
    client = AsyncHttpClient(settings=settings)

    def mock_handler(request: httpx.Request):
        return httpx.Response(200, text="<html><body>OK</body></html>", request=request)

    client._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

    start = time.perf_counter()
    tasks = [client.get(f"https://www.daraz.pk/mock-item-{i}") for i in range(n_requests)]
    await asyncio.gather(*tasks)
    duration = time.perf_counter() - start

    await client.aclose()
    rps = n_requests / duration
    print(f"[BENCHMARK] HTTP Concurrent ({n_requests} requests, concurrency={concurrency}): {duration:.3f}s ({rps:.1f} req/s)")
    return duration


async def benchmark_batch_storage(n_products: int = 1000, n_reviews: int = 5000) -> float:
    """Benchmark batch storage persistence speed."""
    storage = InMemoryStorage()

    products = [
        Product(
            product_id=f"PK-{i}",
            title=f"Benchmark Product {i}",
            url=f"https://daraz.pk/p-{i}",
            price=float(100 + (i % 500)),
        )
        for i in range(n_products)
    ]

    reviews = [
        Review(
            review_id=f"R-{i}",
            product_id=f"PK-{i % n_products}",
            rating=4.5,
            text=f"Sample review content number {i}",
        )
        for i in range(n_reviews)
    ]

    start = time.perf_counter()
    await storage.save_products(products)
    await storage.save_reviews(reviews)
    duration = time.perf_counter() - start

    total_records = n_products + n_reviews
    ops = total_records / duration
    print(f"[BENCHMARK] Batch Storage ({total_records} records): {duration:.3f}s ({ops:.1f} records/s)")
    return duration


def benchmark_deduplication(n_items: int = 10000) -> float:
    """Benchmark deduplication throughput."""
    p_dedup = ProductDeduplicator()
    r_dedup = ReviewDeduplicator()

    start = time.perf_counter()
    for i in range(n_items):
        p_dedup.is_duplicate(f"P-{i}", f"https://daraz.pk/item-{i}?spm=abc")
        r_dedup.is_duplicate(
            product_id=f"P-{i}",
            reviewer=f"User {i}",
            rating=5.0,
            text=f"Review text for item {i}",
        )
    duration = time.perf_counter() - start
    ops = (n_items * 2) / duration
    print(f"[BENCHMARK] Deduplication ({n_items * 2} checks): {duration:.3f}s ({ops:.1f} checks/s)")
    return duration


async def benchmark_checkpoint_operations(n_checkpoints: int = 100) -> float:
    """Benchmark checkpoint update latency."""
    storage = InMemoryStorage()
    manager = CheckpointManager(storage=storage, crawl_id="bench-crawl", target="bench", checkpoint_interval=1)

    start = time.perf_counter()
    for i in range(n_checkpoints):
        await manager.record_progress(position=i, item_id=f"item-{i}", url=f"https://daraz.pk/{i}")
    duration = time.perf_counter() - start

    ops = n_checkpoints / duration
    print(f"[BENCHMARK] Checkpoint Operations ({n_checkpoints} writes): {duration:.3f}s ({ops:.1f} checkpoints/s)")
    return duration


async def run_all_benchmarks():
    print("\n========== STARTING MODULE 1 PERFORMANCE BENCHMARK ==========")
    await benchmark_concurrent_http(50, 10)
    await benchmark_batch_storage(1000, 5000)
    benchmark_deduplication(10000)
    await benchmark_checkpoint_operations(100)
    print("================ BENCHMARK COMPLETED SUCCESSFULLY ================\n")


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())
