"""Crawl checkpoint data model for recovery and state persistence."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.core.constants import CrawlStatus


class CrawlCheckpoint(BaseModel):
    """Snapshot representation of an in-progress crawl session for resume capabilities."""

    crawl_id: str = Field(..., description="Active crawl session ID")
    target: str = Field(..., description="Target query, category, or starting URL")
    current_position: int = Field(default=0, ge=0, description="Current index/page offset in target sequence")
    completed_items: int = Field(default=0, ge=0, description="Number of items successfully scraped")
    failed_items: int = Field(default=0, ge=0, description="Number of failed item attempts")
    retry_count: int = Field(default=0, ge=0, description="Total retry attempts accumulated")
    status: CrawlStatus = Field(default=CrawlStatus.RUNNING, description="Crawl lifecycle status at checkpoint")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Checkpoint creation time")
    last_successful_item: Optional[str] = Field(default=None, description="Identifier of last scraped item")
    last_processed_url: Optional[str] = Field(default=None, description="Last processed request URL")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary checkpoint contextual payload")
