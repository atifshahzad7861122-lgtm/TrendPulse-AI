"""Review and customer feedback data model."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field

from app.core.constants import PARSER_VERSION, SCHEMA_VERSION, SentimentType


class Review(BaseModel):
    """Customer review schema adhering to data contract."""
    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique review identifier")
    product_id: str = Field(..., description="Target product ID")
    reviewer: Optional[str] = Field(default=None, description="Display name or alias of the reviewer")
    rating: float = Field(..., ge=1.0, le=5.0, description="Star rating from 1 to 5")
    text: Optional[str] = Field(default=None, description="Review feedback body")
    date: Optional[str] = Field(default=None, description="String representation of review date")
    review_date: Optional[datetime] = Field(default=None, description="Parsed timestamp when review was posted")
    variation: Optional[str] = Field(default=None, description="Purchased SKU variation or specification")
    images: List[str] = Field(default_factory=list, description="Customer-uploaded image URLs")
    verified: bool = Field(default=True, description="Whether the purchase was verified by marketplace")
    source: str = Field(default="daraz", description="Origin marketplace platform")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Scrape ingestion timestamp"
    )
    schema_version: str = Field(default=SCHEMA_VERSION, description="Data contract schema version")
    parser_version: str = Field(default=PARSER_VERSION, description="Parser implementation version")

    # Downstream Intelligence & Sentiment Analysis
    sentiment: Optional[SentimentType] = Field(default=None, description="Sentiment classification")
    sentiment_score: Optional[float] = Field(
        default=None, ge=-1.0, le=1.0, description="Normalized sentiment polarity (-1.0 to 1.0)"
    )
    is_negative: bool = Field(default=False, description="Flag for negative/critical review")
    complaint_category: Optional[str] = Field(
        default=None, description="Categorized complaint issue (e.g. delivery, quality, damaged)"
    )
