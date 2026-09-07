"""Historical data models for TrendPulse 30-day collection and 365-day retention engine."""

from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.crawling.models import MarketplaceType


class TrendSignal(str, Enum):
    """Normalized trend signal classifications."""
    RISING = "RISING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ObservationDeltas(BaseModel):
    """Mathematical differences calculated between two consecutive observations."""
    model_config = ConfigDict(frozen=True)

    time_delta_seconds: float = Field(default=0.0, description="Elapsed seconds between observations")
    time_delta_days: float = Field(default=0.0, description="Elapsed days between observations")

    # Absolute metric deltas
    sales_delta: Optional[int] = Field(default=None, description="Change in units sold")
    review_delta: Optional[int] = Field(default=None, description="Change in total review count")
    rating_delta: Optional[float] = Field(default=None, description="Change in average rating")
    price_delta: Optional[float] = Field(default=None, description="Change in selling price")

    # Percentage changes
    sales_pct_change: Optional[float] = Field(default=None, description="Sales percentage change")
    review_pct_change: Optional[float] = Field(default=None, description="Review count percentage change")
    price_pct_change: Optional[float] = Field(default=None, description="Price percentage change")


class VelocityMetrics(BaseModel):
    """Calculated sales and engagement velocity metrics based on real observation timestamps."""
    model_config = ConfigDict(frozen=True)

    sales_per_day: Optional[float] = Field(default=None, description="Estimated daily sales velocity")
    sales_per_7_days: Optional[float] = Field(default=None, description="Extrapolated 7-day sales velocity")
    sales_per_30_days: Optional[float] = Field(default=None, description="Extrapolated 30-day sales velocity")
    review_growth_rate_per_day: Optional[float] = Field(default=None, description="Reviews gained per day")
    price_change_rate: Optional[float] = Field(default=None, description="Rate of price change per day")

    window_days: float = Field(default=0.0, description="Observation span in days")
    observation_count: int = Field(default=1, description="Number of observations analyzed")


class TrendScore(BaseModel):
    """Normalized trend scoring and classification."""
    model_config = ConfigDict(frozen=True)

    score: float = Field(..., ge=0.0, le=100.0, description="Normalized trend composite score (0-100)")
    signal: TrendSignal = Field(..., description="High-level trend direction signal")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Trend calculation confidence")
    velocity: Optional[VelocityMetrics] = Field(default=None, description="Underlying velocity metrics")
    observation_count: int = Field(default=1, description="Number of observations contributing to score")
    summary: str = Field(default="", description="Human-readable trend reasoning")


class HistoricalObservation(BaseModel):
    """
    Immutable point-in-time snapshot observation of an ecommerce product.
    Retained up to 365 days for historical sales velocity, price elasticity, and trend intelligence.
    """
    model_config = ConfigDict(frozen=True)

    observation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Deterministic or unique observation identifier"
    )
    product_id: str = Field(..., description="Unique product identifier")
    marketplace: MarketplaceType = Field(..., description="Origin marketplace")
    product_url: str = Field(..., description="Product canonical listing URL")
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the observation"
    )
    crawl_id: Optional[str] = Field(default=None, description="Crawl run identifier")

    # Core Price & Catalog Metrics
    title: str = Field(..., description="Product title at observation time")
    price: float = Field(..., ge=0.0, description="Current selling price")
    original_price: Optional[float] = Field(default=None, ge=0.0, description="Original list price")
    discount: Optional[float] = Field(default=None, description="Discount amount or percentage")
    currency: str = Field(default="USD", description="Currency symbol/code")

    # Engagement & Volume
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0, description="Average customer rating")
    review_count: int = Field(default=0, ge=0, description="Total customer review count")
    rating_count: Optional[int] = Field(default=None, ge=0, description="Total rating submissions")
    sold_count: Optional[int] = Field(default=None, ge=0, description="Cumulative units sold")
    raw_sold_text: Optional[str] = Field(default=None, description="Raw unparsed sales string from DOM")

    # Deltas against immediately prior observation
    deltas: Optional[ObservationDeltas] = Field(default=None, description="Calculated deltas vs previous observation")

    # Integrity & Content Hashing
    images_hash: Optional[str] = Field(default=None, description="SHA-256 hash of product image URLs")
    content_hash: Optional[str] = Field(default=None, description="SHA-256 hash of core product details")

    # Merchant & Taxonomy
    availability: bool = Field(default=True, description="Stock availability status")
    seller_id: Optional[str] = Field(default=None, description="Sanitized merchant ID")
    seller_name: Optional[str] = Field(default=None, description="Sanitized merchant name")
    category_id: Optional[str] = Field(default=None, description="Category identifier")
    category_path: Optional[str] = Field(default=None, description="Breadcrumb category hierarchy")

    # Structure counts
    variants_count: int = Field(default=0, ge=0, description="Number of available variants/SKUs")
    specifications_count: int = Field(default=0, ge=0, description="Number of technical specifications")

    # Diagnostic & Quality
    source: str = Field(default="universal_extractor", description="Extraction component identifier")
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    raw_data_reference: Optional[str] = Field(
        default=None, description="Reference ID to sanitized raw payload (secrets stripped)"
    )
    quality_status: str = Field(default="accepted", description="Quality gate outcome: accepted, warning, rejected")
    validation_messages: List[str] = Field(default_factory=list, description="Quality gate warning/error messages")

    @classmethod
    def generate_deterministic_id(cls, marketplace: MarketplaceType, product_id: str, observed_at: datetime, bucket_hours: int = 1) -> str:
        """
        Generate a deterministic observation ID based on marketplace, product_id, and time bucket.
        Prevents duplicate observations during retries or multiple extractions within the same bucket.
        """
        bucket_ts = int(observed_at.timestamp() // (bucket_hours * 3600))
        key = f"{marketplace.value}:{product_id}:{bucket_ts}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


class RetentionResult(BaseModel):
    """Statistics returned after executing rolling retention pruning."""
    total_inspected: int = Field(default=0, description="Total historical observation records evaluated")
    expired_count: int = Field(default=0, description="Number of records older than retention threshold")
    deleted_count: int = Field(default=0, description="Number of records permanently removed")
    preserved_count: int = Field(default=0, description="Number of records retained in active window")
    oldest_preserved_date: Optional[datetime] = Field(default=None, description="Timestamp of oldest active record")
    is_dry_run: bool = Field(default=False, description="Whether retention was executed in preview mode")
    execution_time_ms: float = Field(default=0.0, description="Execution duration in milliseconds")


class HistoricalCollectionStats(BaseModel):
    """Summary metrics of a historical collection run."""
    crawl_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
    marketplace: Optional[MarketplaceType] = Field(default=None)
    window_days: int = Field(default=30)
    products_discovered: int = Field(default=0)
    products_extracted: int = Field(default=0)
    successful: int = Field(default=0)
    failed: int = Field(default=0)
    challenges: int = Field(default=0)
    observations_created: int = Field(default=0)
    duplicates_prevented: int = Field(default=0)
    rejected: int = Field(default=0)
    avg_latency_ms: float = Field(default=0.0)
