"""Normalized review and customer sentiment models."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.core.constants import SentimentType
from app.crawling.models import MarketplaceType


class IntelligenceReview(BaseModel):
    """Normalized customer review schema across all marketplaces."""

    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique review identifier")
    product_id: str = Field(..., description="Target platform product identifier")
    marketplace: MarketplaceType = Field(..., description="Origin marketplace platform")

    # Core Rating & Feedback
    rating: float = Field(..., ge=1.0, le=5.0, description="Star rating score from 1.0 to 5.0")
    review_title: Optional[str] = Field(default=None, description="Review headline or summary")
    review_text: Optional[str] = Field(default=None, description="Detailed customer review body")

    # Date Information (Mandatory when exposed)
    review_date: Optional[datetime] = Field(default=None, description="Parsed UTC datetime when review was posted")
    raw_date_str: Optional[str] = Field(default=None, description="Original unparsed date string")

    # Reviewer Metadata
    reviewer_name: Optional[str] = Field(default=None, description="Customer display name or alias")
    reviewer_location: Optional[str] = Field(default=None, description="Reviewer country or city")
    verified_purchase: bool = Field(default=True, description="Verified buyer status")
    helpful_count: int = Field(default=0, ge=0, description="Count of customers finding review helpful")

    # Media & Variation Attachments
    review_images: List[str] = Field(default_factory=list, description="Customer attached image URLs")
    review_variants: Optional[str] = Field(default=None, description="Purchased SKU variant descriptor")
    raw_review: Dict[str, Any] = Field(default_factory=dict, description="Raw marketplace review payload")

    # Sentiment Intelligence
    sentiment: Optional[SentimentType] = Field(default=None, description="Calculated sentiment classification")
    sentiment_score: Optional[float] = Field(default=None, ge=-1.0, le=1.0, description="Sentiment polarity (-1.0 to 1.0)")
    is_negative: bool = Field(default=False, description="Flag for negative rating / review")
    extraction_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Extraction ingestion timestamp"
    )

    def compute_fingerprint(self) -> str:
        """Compute deterministic review fingerprint hash for cross-crawl deduplication."""
        import hashlib
        text_snip = (self.review_text or "").strip()[:100]
        name_snip = (self.reviewer_name or "").strip().lower()
        payload = f"{self.marketplace.value}|{self.product_id}|{self.rating}|{name_snip}|{text_snip}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
