"""Runtime context, request metrics, and global crawl execution statistics tracker."""

import asyncio
import contextvars
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid

# Context variables to hold active crawl / request context
_crawl_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("crawl_id", default=None)
_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


def get_current_crawl_id() -> Optional[str]:
    return _crawl_id_var.get()


def set_current_crawl_id(crawl_id: Optional[str]):
    _crawl_id_var.set(crawl_id)


def get_current_request_id() -> Optional[str]:
    return _request_id_var.get()


def set_current_request_id(request_id: Optional[str]):
    _request_id_var.set(request_id)


@dataclass
class RequestMetrics:
    """Collects timing and status metrics for individual HTTP and Browser requests."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    method: str = "GET"
    status_code: Optional[int] = None
    start_time: float = field(default_factory=time.monotonic)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    retry_count: int = 0

    def finish(self, status_code: Optional[int] = None, error: Optional[str] = None):
        self.end_time = time.monotonic()
        self.duration_ms = (self.end_time - self.start_time) * 1000.0
        if status_code is not None:
            self.status_code = status_code
        if error is not None:
            self.error = error


class RuntimeMetricsTracker:
    """Aggregates and tracks real-time execution metrics across all scraper operations."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self.start_time: float = time.monotonic()

        # Request metrics
        self.requests_total: int = 0
        self.requests_successful: int = 0
        self.requests_failed: int = 0
        self.responses_429: int = 0
        self.responses_403: int = 0

        # Challenge & Retry metrics
        self.captcha_events: int = 0
        self.manual_interventions: int = 0
        self.retries_total: int = 0

        # Data discovery & extraction metrics
        self.products_discovered: int = 0
        self.products_extracted: int = 0
        self.reviews_extracted: int = 0
        self.duplicates_prevented: int = 0

        # Latency tracking
        self._latencies_ms: List[float] = []

    async def record_request(
        self,
        status_code: Optional[int],
        duration_ms: float,
        is_error: bool = False,
    ) -> None:
        """Record an executed HTTP or browser request."""
        async with self._lock:
            self.requests_total += 1
            if is_error or (status_code and status_code >= 400):
                self.requests_failed += 1
            else:
                self.requests_successful += 1

            if status_code == 429:
                self.responses_429 += 1
            elif status_code == 403:
                self.responses_403 += 1

            self._latencies_ms.append(duration_ms)
            if len(self._latencies_ms) > 1000:
                self._latencies_ms = self._latencies_ms[-1000:]

    async def record_retry(self) -> None:
        async with self._lock:
            self.retries_total += 1

    async def record_challenge(self, challenge_type: str) -> None:
        async with self._lock:
            self.captcha_events += 1

    async def record_manual_intervention(self) -> None:
        async with self._lock:
            self.manual_interventions += 1

    async def record_discovery(self, count: int = 1) -> None:
        async with self._lock:
            self.products_discovered += count

    async def record_product_extracted(self, count: int = 1) -> None:
        async with self._lock:
            self.products_extracted += count

    async def record_review_extracted(self, count: int = 1) -> None:
        async with self._lock:
            self.reviews_extracted += count

    async def record_duplicate_prevented(self, count: int = 1) -> None:
        async with self._lock:
            self.duplicates_prevented += count

    def get_summary(self) -> Dict[str, Any]:
        """Compute an instantaneous snapshot dictionary of all metrics."""
        duration_s = max(0.001, time.monotonic() - self.start_time)
        avg_latency = (
            sum(self._latencies_ms) / len(self._latencies_ms)
            if self._latencies_ms
            else 0.0
        )
        req_per_sec = self.requests_total / duration_s

        return {
            "duration_seconds": round(duration_s, 2),
            "requests_total": self.requests_total,
            "requests_successful": self.requests_successful,
            "requests_failed": self.requests_failed,
            "responses_429": self.responses_429,
            "responses_403": self.responses_403,
            "captcha_events": self.captcha_events,
            "manual_interventions": self.manual_interventions,
            "retries_total": self.retries_total,
            "products_discovered": self.products_discovered,
            "products_extracted": self.products_extracted,
            "reviews_extracted": self.reviews_extracted,
            "duplicates_prevented": self.duplicates_prevented,
            "average_latency_ms": round(avg_latency, 2),
            "requests_per_second": round(req_per_sec, 2),
        }

    def reset(self) -> None:
        self.start_time = time.monotonic()
        self.requests_total = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.responses_429 = 0
        self.responses_403 = 0
        self.captcha_events = 0
        self.manual_interventions = 0
        self.retries_total = 0
        self.products_discovered = 0
        self.products_extracted = 0
        self.reviews_extracted = 0
        self.duplicates_prevented = 0
        self._latencies_ms.clear()


# Global runtime metrics tracker
runtime_metrics = RuntimeMetricsTracker()
