"""Seller data model."""

from typing import Optional
from pydantic import BaseModel, Field


class Seller(BaseModel):
    """Seller information schema."""
    seller_id: str = Field(..., description="Unique merchant/store ID")
    seller_name: str = Field(..., description="Store or seller display name")
    seller_url: Optional[str] = Field(default=None, description="Direct URL to the seller store page")
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0, description="Overall seller score out of 5")
    positive_seller_ratings: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Positive seller rating percentage"
    )
    ship_on_time_rate: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="On-time shipping rate percentage"
    )
    response_rate: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Chat/inquiry response rate percentage"
    )
