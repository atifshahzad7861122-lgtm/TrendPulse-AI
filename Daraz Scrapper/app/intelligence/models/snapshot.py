"""Historical snapshot model for TrendPulse 30-day and 365-day trend intelligence."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.crawling.models import MarketplaceType


class HistoricalSnapshot(BaseModel):
    """
    Point-in-time observation of a product's price, rating, reviews, sales, and availability.
    Accumulated over time to enable 30-day velocity and 365-day longevity analysis.
    """

    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique snapshot record identifier")
    product_id: str = Field(..., description="Target product identifier")
    marketplace: MarketplaceType = Field(..., description="Origin marketplace platform")
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the observation"
    )

    # Core Metrics at Observation Time
    title: str = Field(..., description="Product title at observation time")
    price: float = Field(..., ge=0.0, description="Observed current selling price")
    original_price: Optional[float] = Field(default=None, ge=0.0, description="Observed list price before discount")
    discount: Optional[float] = Field(default=None, description="Observed discount percentage/value")
    currency: str = Field(default="USD", description="Currency code")

    # Engagement Metrics
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0, description="Observed average rating")
    review_count: int = Field(default=0, ge=0, description="Observed total review count")
    rating_count: Optional[int] = Field(default=None, ge=0, description="Observed star rating count")
    sold_count: Optional[int] = Field(default=None, ge=0, description="Observed estimated units sold")
    raw_sold_text: Optional[str] = Field(default=None, description="Original unparsed sales string")

    # Status & Seller
    availability: bool = Field(default=True, description="Observed in-stock availability status")
    seller_name: Optional[str] = Field(default=None, description="Observed seller name")
    primary_image: Optional[str] = Field(default=None, description="Hero image URL")
    image_urls: List[str] = Field(default_factory=list, description="List of all gallery image URLs")

    # Metadata
    source_url: str = Field(..., description="Product listing URL")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional arbitrary point-in-time metrics")
