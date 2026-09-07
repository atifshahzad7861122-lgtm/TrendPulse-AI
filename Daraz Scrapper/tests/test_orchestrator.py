"""Unit and integration test suite for Module 6: Production Scraping Orchestrator."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.crawling.models import CrawlResponse, MarketplaceType
from app.history.store import InMemoryHistoricalStore
from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.result import ExtractionStatus, IntelligenceExtractionResult
from app.orchestration.health import HealthStatus, MarketplaceHealthTracker
from app.orchestration.models import CrawlTask, MarketplaceLimitConfig, OrchestratorConfig, TaskState
from app.orchestration.orchestrator import ProductionScrapingOrchestrator
from app.orchestration.queue import DurableTaskQueue
from app.orchestration.rate_limiter import MarketplaceRateLimiter
from app.orchestration.retry import SmartRetryPolicy
from app.orchestration.worker import WorkerPool


# ==========================================
# 1. Durable Queue & Crash Recovery Tests
# ==========================================

@pytest.mark.asyncio
async def test_durable_queue_lifecycle_and_deduplication(tmp_path: Path):
    chk_dir = str(tmp_path / "checkpoints")
    queue = DurableTaskQueue(crawl_id="test_crawl_01", checkpoints_dir=chk_dir)

    task1 = CrawlTask(
        crawl_id="test_crawl_01",
        url="https://www.daraz.pk/products/item1-i1.html",
        marketplace=MarketplaceType.DARAZ,
        product_id="prod_1",
    )
    task2 = CrawlTask(
        crawl_id="test_crawl_01",
        url="https://www.daraz.pk/products/item2-i2.html",
        marketplace=MarketplaceType.DARAZ,
        product_id="prod_2",
    )

    # Test enqueue
    added1 = await queue.enqueue(task1)
    added2 = await queue.enqueue(task2)
    assert added1 is True
    assert added2 is True

    # Test deduplication
    duplicate = await queue.enqueue(task1)
    assert duplicate is False

    # Pop next task
    popped = await queue.pop_next()
    assert popped is not None
    assert popped.task_id == task1.task_id
    assert popped.status == TaskState.PROCESSING

    # Complete task
    await queue.mark_completed(popped.task_id, product_id="prod_1")
    counts = queue.get_counts()
    assert counts[TaskState.COMPLETED] == 1
    assert counts[TaskState.PENDING] == 1


@pytest.mark.asyncio
async def test_durable_queue_crash_recovery(tmp_path: Path):
    chk_dir = str(tmp_path / "checkpoints")
    
    # 1. Create queue and leave one task processing (simulating crash)
    queue1 = DurableTaskQueue(crawl_id="crash_session", checkpoints_dir=chk_dir)
    t = CrawlTask(
        crawl_id="crash_session",
        url="https://www.daraz.pk/products/crash-test.html",
        marketplace=MarketplaceType.DARAZ,
    )
    await queue1.enqueue(t)
    popped = await queue1.pop_next()
    assert popped.status == TaskState.PROCESSING

    # 2. Re-instantiate queue (restarting process)
    queue2 = DurableTaskQueue(crawl_id="crash_session", checkpoints_dir=chk_dir)
    assert queue2.has_pending_or_processing() is True
    recovered = await queue2.pop_next()
    assert recovered is not None
    assert recovered.task_id == t.task_id
    assert recovered.status == TaskState.PROCESSING


# ==========================================
# 2. Smart Retry Policy Tests
# ==========================================

def test_retry_transient_error():
    policy = SmartRetryPolicy(base_backoff_sec=1.0, max_backoff_sec=10.0, max_retries=3)
    task = CrawlTask(
        crawl_id="c1",
        url="https://www.amazon.com/dp/B000",
        marketplace=MarketplaceType.AMAZON,
        attempt_count=1,
    )
    should_retry, next_retry, reason = policy.should_retry(task, status_code=503, error_message="Service Unavailable")
    assert should_retry is True
    assert next_retry is not None
    assert next_retry > datetime.now(timezone.utc)
    assert "Transient failure" in reason


def test_retry_non_retryable_404():
    policy = SmartRetryPolicy(max_retries=3)
    task = CrawlTask(
        crawl_id="c1",
        url="https://www.daraz.pk/products/deleted.html",
        marketplace=MarketplaceType.DARAZ,
        attempt_count=1,
    )
    should_retry, next_retry, reason = policy.should_retry(task, status_code=404, error_message="Listing Not Found")
    assert should_retry is False
    assert next_retry is None
    assert "Non-retryable" in reason


# ==========================================
# 3. Marketplace Rate Limiter Tests
# ==========================================

@pytest.mark.asyncio
async def test_marketplace_rate_limiter_pacing():
    limits = {
        MarketplaceType.SHOPIFY: MarketplaceLimitConfig(
            requests_per_second=10.0,
            max_http_concurrency=2,
            min_delay_ms=10,
            max_delay_ms=30,
        )
    }
    limiter = MarketplaceRateLimiter(limits)
    
    # Fast concurrent acquire
    t0 = asyncio.get_event_loop().time()
    async with limiter.throttle(MarketplaceType.SHOPIFY, is_browser=False):
        pass
    t1 = asyncio.get_event_loop().time()
    assert (t1 - t0) >= 0.01


# ==========================================
# 4. Marketplace Health Tracker Tests
# ==========================================

def test_health_tracker_success_and_degradation():
    tracker = MarketplaceHealthTracker()
    
    # Record successes
    tracker.record_success(MarketplaceType.DARAZ, latency_ms=250.0)
    tracker.record_success(MarketplaceType.DARAZ, latency_ms=300.0)
    
    report = tracker.get_health(MarketplaceType.DARAZ)
    assert report.total_requests == 2
    assert report.success_rate == 1.0
    assert report.status == HealthStatus.HEALTHY
    assert report.average_latency_ms == 275.0

    # Record challenge
    tracker.record_challenge(MarketplaceType.DARAZ, reason="Baxia Security Slider", latency_ms=100.0)
    tracker.record_challenge(MarketplaceType.DARAZ, reason="Baxia Security Slider", latency_ms=100.0)
    report2 = tracker.get_health(MarketplaceType.DARAZ)
    assert report2.challenges_encountered == 2
    assert report2.status == HealthStatus.CHALLENGED_PAUSED


# ==========================================
# 5. Worker Pool Failure Isolation Tests
# ==========================================

@pytest.mark.asyncio
async def test_worker_pool_failure_isolation(tmp_path: Path):
    chk_dir = str(tmp_path / "checkpoints")
    queue = DurableTaskQueue(crawl_id="worker_test", checkpoints_dir=chk_dir)
    
    t1 = CrawlTask(crawl_id="worker_test", url="https://site.com/ok", marketplace=MarketplaceType.SHOPIFY)
    t2 = CrawlTask(crawl_id="worker_test", url="https://site.com/fail", marketplace=MarketplaceType.SHOPIFY)
    await queue.enqueue_many([t1, t2])

    processed_ids = []

    async def mock_processor(task: CrawlTask, worker_id: int):
        processed_ids.append(task.task_id)
        if "fail" in task.url:
            raise RuntimeError("Task execution exploded")
        await queue.mark_completed(task.task_id)

    pool = WorkerPool(queue=queue, process_task_fn=mock_processor, max_workers=2)
    await pool.start()
    await pool.wait_idle()
    await pool.stop()

    assert len(processed_ids) == 2
    counts = queue.get_counts()
    assert counts[TaskState.COMPLETED] == 1
    assert counts[TaskState.FAILED] == 1


# ==========================================
# 6. End-to-End Orchestrator Mock Test
# ==========================================

@pytest.mark.asyncio
async def test_production_orchestrator_mock_crawl(tmp_path: Path):
    chk_dir = str(tmp_path / "checkpoints")
    storage_dir = str(tmp_path / "storage")
    out_file = str(tmp_path / "output.json")

    config = OrchestratorConfig(
        max_workers=2,
        batch_size=2,
        checkpoints_dir=chk_dir,
        storage_dir=storage_dir,
    )

    mock_intel_engine = MagicMock()
    
    mock_product = ProductIntelligence(
        product_id="P123",
        marketplace=MarketplaceType.DARAZ,
        source_url="https://www.daraz.pk/products/test-item.html",
        canonical_url="https://www.daraz.pk/products/test-item.html",
        title="Gaming Headset 7.1 Surround Sound",
        price=3200.0,
        currency="PKR",
        rating=4.7,
        review_count=85,
    )

    mock_res = IntelligenceExtractionResult(
        extraction_id="ext_001",
        product_id="P123",
        marketplace=MarketplaceType.DARAZ,
        url="https://www.daraz.pk/products/test-item.html",
        status=ExtractionStatus.SUCCESS,
        success=True,
        product=mock_product,
    )

    mock_intel_engine.extract_product = AsyncMock(return_value=mock_res)
    hist_store = InMemoryHistoricalStore()

    orchestrator = ProductionScrapingOrchestrator(
        config=config,
        intelligence_engine=mock_intel_engine,
        historical_store=hist_store,
    )

    summary = await orchestrator.execute_crawl(
        crawl_id="test_run_100",
        marketplace=MarketplaceType.DARAZ,
        urls=["https://www.daraz.pk/products/test-item.html"],
        output_file=out_file,
        export_format="json",
    )

    assert summary.status == "completed"
    assert summary.completed_count == 1
    assert summary.products_persisted == 1
    assert Path(out_file).exists()

    # Check factual historical observation recorded
    history = await hist_store.get_all_observations_for_product(MarketplaceType.DARAZ, "P123")
    assert len(history) == 1
    assert history[0].price == 3200.0
    assert history[0].title == "Gaming Headset 7.1 Surround Sound"
