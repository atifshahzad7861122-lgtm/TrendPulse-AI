from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class PlatformSignal(BaseModel):
    id: str
    platform: str  # "TikTok", "Daraz", "Instagram", "YouTube", "Facebook"
    product_id: str
    product_name: str
    category: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    volume: int
    engagement_rate: float  # e.g., 0.08 = 8% engagement
    shares_count: int = 0
    views_count: int = 0
    likes_count: int = 0
    comments_count: int = 0
    sentiment_score: float = 0.8  # 0.0 - 1.0
    mode: str = "mock"  # "live" | "mock"
    data_quality_score: float = 100.0  # 0.0 - 100.0
    quality_flags: List[str] = Field(default_factory=list)
    like_rate: float = 0.0
    comment_rate: float = 0.0
    source_url: Optional[str] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

    @property
    def deduplication_key(self) -> str:
        """Deterministic composite key for deduplication."""
        time_str = self.timestamp.strftime("%Y-%m-%d")
        return f"{self.platform.lower()}:{self.product_id}:{time_str}"

class SignalBatch(BaseModel):
    source_slug: str
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    signals: List[PlatformSignal] = Field(default_factory=list)
    total_records: int = 0

class IngestionResult(BaseModel):
    source: str
    is_live: bool = False
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_seconds: float = 0.0
    records_received: int = 0
    records_normalized: int = 0
    records_matched: int = 0
    records_unmatched: int = 0
    records_ambiguous: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    alerts_created: int = 0
    notifications_created: int = 0
    status: str = "Success"  # "Success", "Partial", "RateLimited", "QuotaExceeded", "Failed", "Skipped"
    errors: List[str] = Field(default_factory=list)
