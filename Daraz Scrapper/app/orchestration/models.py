"""Data contracts and configuration models for the Production Scraping Orchestrator."""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.crawling.models import MarketplaceType


class TaskState(str, Enum):
    """Lifecycle states for durable crawling tasks."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CHALLENGED = "challenged"
    RETRY_PENDING = "retry_pending"
    CANCELLED = "cancelled"


class CrawlTask(BaseModel):
    """Durable task unit queued for discovery or extraction."""
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:10]}")
    crawl_id: str = Field(..., description="Parent crawl job session identifier")
    url: str = Field(..., description="Target listing or catalog URL")
    marketplace: MarketplaceType = Field(..., description="Target marketplace")
    product_id: Optional[str] = Field(default=None, description="Extracted product identifier if known")
    priority: int = Field(default=10, description="Execution priority (lower executes first)")
    status: TaskState = Field(default=TaskState.PENDING, description="Current task state")
    attempt_count: int = Field(default=0, description="Number of execution attempts")
    max_retries: int = Field(default=3, description="Maximum permitted retry attempts")
    last_error: Optional[str] = Field(default=None, description="Diagnostic message from last failure")
    next_retry_at: Optional[datetime] = Field(default=None, description="Scheduled time for next retry")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom contextual metadata")


class MarketplaceLimitConfig(BaseModel):
    """Rate limit and concurrency limits per marketplace."""
    requests_per_second: float = Field(default=2.0, gt=0.0)
    max_http_concurrency: int = Field(default=5, ge=1)
    max_browser_concurrency: int = Field(default=2, ge=1)
    min_delay_ms: int = Field(default=800, ge=0)
    max_delay_ms: int = Field(default=2500, ge=0)


class OrchestratorConfig(BaseModel):
    """Production orchestrator execution configuration."""
    max_workers: int = Field(default=4, ge=1, le=32)
    batch_size: int = Field(default=10, ge=1, description="Number of items to process and persist per batch")
    max_retries: int = Field(default=3, ge=0)
    base_backoff_sec: float = Field(default=1.5, gt=0.0)
    max_backoff_sec: float = Field(default=30.0, gt=0.0)
    enable_browser: bool = Field(default=True, description="Allow dynamic browser fallback")
    checkpoints_dir: str = Field(default="data/checkpoints/orchestrator")
    storage_dir: str = Field(default="data/production")
    
    # Per-marketplace limit defaults
    marketplace_limits: Dict[MarketplaceType, MarketplaceLimitConfig] = Field(
        default_factory=lambda: {
            MarketplaceType.DARAZ: MarketplaceLimitConfig(requests_per_second=2.0, max_http_concurrency=4, max_browser_concurrency=2, min_delay_ms=600, max_delay_ms=2000),
            MarketplaceType.AMAZON: MarketplaceLimitConfig(requests_per_second=1.0, max_http_concurrency=2, max_browser_concurrency=1, min_delay_ms=1500, max_delay_ms=4000),
            MarketplaceType.EBAY: MarketplaceLimitConfig(requests_per_second=1.5, max_http_concurrency=3, max_browser_concurrency=1, min_delay_ms=1000, max_delay_ms=3000),
            MarketplaceType.ALIEXPRESS: MarketplaceLimitConfig(requests_per_second=1.5, max_http_concurrency=3, max_browser_concurrency=1, min_delay_ms=1000, max_delay_ms=3000),
            MarketplaceType.SHOPIFY: MarketplaceLimitConfig(requests_per_second=3.0, max_http_concurrency=6, max_browser_concurrency=2, min_delay_ms=400, max_delay_ms=1500),
        }
    )


class CrawlJobSummary(BaseModel):
    """Aggregated execution summary for a production crawl session."""
    crawl_id: str
    marketplace: Optional[MarketplaceType] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    total_tasks: int = 0
    completed_count: int = 0
    failed_count: int = 0
    challenged_count: int = 0
    retried_count: int = 0
    cancelled_count: int = 0
    products_persisted: int = 0
    observations_recorded: int = 0
    average_latency_ms: float = 0.0
    status: str = "completed"
    error_summary: Dict[str, int] = Field(default_factory=dict)
