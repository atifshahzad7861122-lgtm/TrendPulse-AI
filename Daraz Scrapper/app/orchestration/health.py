"""Marketplace health monitoring, latency tracking, and challenge rate auditor."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.crawling.models import MarketplaceType


class HealthStatus(str, Enum):
    """Operational status of a marketplace endpoint."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CHALLENGED_PAUSED = "challenged_paused"
    UNAVAILABLE = "unavailable"


class MarketplaceHealthReport(BaseModel):
    """Real-time health report for a specific marketplace."""
    marketplace: MarketplaceType
    status: HealthStatus = HealthStatus.HEALTHY
    total_requests: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    challenges_encountered: int = 0
    success_rate: float = 1.0
    challenge_rate: float = 0.0
    error_rate: float = 0.0
    average_latency_ms: float = 0.0
    last_successful_crawl: Optional[datetime] = None
    last_challenge: Optional[datetime] = None
    last_error: Optional[str] = None


class MarketplaceHealthTracker:
    """
    Tracks runtime availability, error distributions, and challenge frequencies
    to inform orchestrator pacing and operators.
    """

    def __init__(self):
        self._reports: Dict[MarketplaceType, MarketplaceHealthReport] = {
            m: MarketplaceHealthReport(marketplace=m) for m in MarketplaceType
        }
        self._latencies: Dict[MarketplaceType, List[float]] = {
            m: [] for m in MarketplaceType
        }

    def record_success(self, marketplace: MarketplaceType, latency_ms: float = 0.0) -> None:
        report = self._reports[marketplace]
        report.total_requests += 1
        report.successful_extractions += 1
        report.last_successful_crawl = datetime.now(timezone.utc)
        self._update_metrics(marketplace, latency_ms)

    def record_failure(self, marketplace: MarketplaceType, error: str, status_code: int = 0, latency_ms: float = 0.0) -> None:
        report = self._reports[marketplace]
        report.total_requests += 1
        report.failed_extractions += 1
        report.last_error = f"[HTTP {status_code}] {error}" if status_code > 0 else error
        self._update_metrics(marketplace, latency_ms)

    def record_challenge(self, marketplace: MarketplaceType, reason: str, latency_ms: float = 0.0) -> None:
        report = self._reports[marketplace]
        report.total_requests += 1
        report.challenges_encountered += 1
        report.last_challenge = datetime.now(timezone.utc)
        report.last_error = f"Bot challenge: {reason}"
        self._update_metrics(marketplace, latency_ms)

    def _update_metrics(self, marketplace: MarketplaceType, latency_ms: float) -> None:
        report = self._reports[marketplace]
        if latency_ms > 0:
            lat_list = self._latencies[marketplace]
            lat_list.append(latency_ms)
            if len(lat_list) > 50:
                lat_list.pop(0)
            report.average_latency_ms = round(sum(lat_list) / len(lat_list), 1)

        if report.total_requests > 0:
            report.success_rate = round(report.successful_extractions / report.total_requests, 3)
            report.challenge_rate = round(report.challenges_encountered / report.total_requests, 3)
            report.error_rate = round(report.failed_extractions / report.total_requests, 3)

        # Assess health status
        if report.challenges_encountered > 0 and report.challenge_rate > 0.4:
            report.status = HealthStatus.CHALLENGED_PAUSED
        elif report.error_rate > 0.5 and report.total_requests >= 3:
            report.status = HealthStatus.UNAVAILABLE
        elif report.error_rate > 0.2:
            report.status = HealthStatus.DEGRADED
        else:
            report.status = HealthStatus.HEALTHY

    def get_health(self, marketplace: MarketplaceType) -> MarketplaceHealthReport:
        return self._reports[marketplace]

    def get_all_health(self) -> Dict[MarketplaceType, MarketplaceHealthReport]:
        return dict(self._reports)
