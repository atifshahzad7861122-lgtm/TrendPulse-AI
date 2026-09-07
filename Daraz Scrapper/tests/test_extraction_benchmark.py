"""Performance and throughput benchmark across 100 synthetic fixture product pages."""

import asyncio
from pathlib import Path
import time
from unittest.mock import AsyncMock
import pytest

from app.discovery.models import ProductTarget
from app.extraction.config import DarazExtractionConfig
from app.extraction.engine import DarazProductExtractionEngine
from app.extraction.validator import ValidationStatus
from app.storage.repository import InMemoryStorage

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "daraz"


@pytest.mark.asyncio
async def test_100_products_extraction_benchmark():
    """
    Benchmarks parsing and batch extraction over 100 synthetic/fixture products.
    Measures throughput (products/sec, products/min), average latency, validation pass rate,
    and duplicate prevention.
    """
    html_standard = (FIXTURES_DIR / "product_page_standard.html").read_text(encoding="utf-8")
    html_minimal = (FIXTURES_DIR / "product_page_minimal.html").read_text(encoding="utf-8")
    html_dynamic = (FIXTURES_DIR / "product_page_dynamic_json.html").read_text(encoding="utf-8")

    storage = InMemoryStorage()
    config = DarazExtractionConfig(max_concurrency=10, batch_size=25, auto_browser_fallback=False)
    engine = DarazProductExtractionEngine(config=config, storage=storage)

    # Mock HTTP retrieval with mixed HTML variations
    fixtures = [html_standard, html_minimal, html_dynamic]

    async def mock_http(url: str):
        idx = hash(url) % len(fixtures)
        return 200, fixtures[idx]

    engine._fetch_http = AsyncMock(side_effect=mock_http)

    # Generate 100 synthetic targets (including 5 duplicate entries)
    targets = []
    for i in range(1, 96):
        targets.append(
            ProductTarget(
                product_id=f"SYNTH_{i:04d}",
                url=f"https://www.daraz.pk/products/synthetic-item-{i}-i{i:04d}.html",
            )
        )
    # Add 5 duplicates
    for i in range(1, 6):
        targets.append(
            ProductTarget(
                product_id=f"SYNTH_{i:04d}",
                url=f"https://www.daraz.pk/products/synthetic-item-{i}-i{i:04d}.html",
            )
        )

    assert len(targets) == 100

    start_time = time.perf_counter()
    results = await engine.extract_batch(targets, use_browser=False)
    total_duration_sec = time.perf_counter() - start_time

    # Verification assertions
    assert len(results) == 95  # 5 duplicates filtered before extraction
    assert engine.duplicates_prevented == 5

    # Check metrics
    valid_count = sum(1 for r in results if r.success)
    assert valid_count >= 90

    validation_rate = (valid_count / len(results)) * 100.0
    products_per_sec = len(results) / total_duration_sec
    products_per_min = products_per_sec * 60.0
    avg_latency_ms = (total_duration_sec / len(results)) * 1000.0

    print(f"\n=======================================================")
    print(f"      100 PRODUCT EXTRACTION BENCHMARK RESULTS         ")
    print(f"=======================================================")
    print(f"Total Targets Submitted:   100")
    print(f"Duplicates Filtered:       {engine.duplicates_prevented}")
    print(f"Unique Extracted Products: {len(results)}")
    print(f"Valid Product Rate:        {validation_rate:.1f}%")
    print(f"Total Execution Time:      {total_duration_sec:.3f} s")
    print(f"Throughput (Products/Min): {products_per_min:.1f} prods/min")
    print(f"Average Product Latency:   {avg_latency_ms:.2f} ms")
    print(f"=======================================================")

    assert products_per_min > 300  # High throughput expectation for async engine
    assert avg_latency_ms < 100    # Fast local latency
