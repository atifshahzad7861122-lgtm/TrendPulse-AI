"""Tests for RuntimeMetricsTracker and aggregate performance stats."""

import pytest
from app.core.runtime import RuntimeMetricsTracker


@pytest.mark.asyncio
async def test_runtime_metrics_tracker_accumulation():
    tracker = RuntimeMetricsTracker()

    await tracker.record_request(status_code=200, duration_ms=120.0)
    await tracker.record_request(status_code=429, duration_ms=80.0, is_error=True)
    await tracker.record_request(status_code=403, duration_ms=90.0, is_error=True)

    await tracker.record_retry()
    await tracker.record_challenge("CLOUDFLARE_BLOCK")
    await tracker.record_manual_intervention()

    await tracker.record_discovery(count=15)
    await tracker.record_product_extracted(count=10)
    await tracker.record_review_extracted(count=25)
    await tracker.record_duplicate_prevented(count=3)

    summary = tracker.get_summary()

    assert summary["requests_total"] == 3
    assert summary["requests_successful"] == 1
    assert summary["requests_failed"] == 2
    assert summary["responses_429"] == 1
    assert summary["responses_403"] == 1
    assert summary["retries_total"] == 1
    assert summary["captcha_events"] == 1
    assert summary["manual_interventions"] == 1
    assert summary["products_discovered"] == 15
    assert summary["products_extracted"] == 10
    assert summary["reviews_extracted"] == 25
    assert summary["duplicates_prevented"] == 3
    assert summary["average_latency_ms"] > 0
