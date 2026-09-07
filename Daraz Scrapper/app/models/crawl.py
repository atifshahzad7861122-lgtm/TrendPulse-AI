"""Crawl job and execution run models."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.core.constants import CrawlStatus, CrawlType


class CrawlRun(BaseModel):
    """Execution state and metrics for a crawling session."""
    crawl_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique crawl session ID")
    crawl_type: CrawlType = Field(default=CrawlType.FULL, description="Type or scope of the crawl")
    status: CrawlStatus = Field(default=CrawlStatus.PENDING, description="Current lifecycle state")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Crawl start timestamp")
    finished_at: Optional[datetime] = Field(default=None, description="Crawl termination timestamp")
    items_discovered: int = Field(default=0, ge=0, description="Total item links identified")
    items_processed: int = Field(default=0, ge=0, description="Total items successfully parsed & processed")
    items_failed: int = Field(default=0, ge=0, description="Total items that failed processing")
    error_count: int = Field(default=0, ge=0, description="Total error occurrences encountered")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional contextual crawl metadata")


class CrawlStats(BaseModel):
    """Aggregated real-time metrics for crawl job tracking."""
    crawl_id: str
    duration_seconds: float = 0.0
    items_per_minute: float = 0.0
    success_rate_percentage: float = 100.0
