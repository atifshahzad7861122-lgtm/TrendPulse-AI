"""Structured data models for product intelligence, variations, and images."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.crawling.models import MarketplaceType
from app.models.image import Image


class Variant(BaseModel):
    """Structured product SKU variation (size, color, storage, style)."""
    sku_id: Optional[str] = Field(default=None, description="SKU variation identifier")
    name: str = Field(..., description="Variant display title / attribute descriptor")
    group: Optional[str] = Field(default=None, description="Variant grouping attribute (e.g. Color, Size, Storage)")
    value: Optional[str] = Field(default=None, description="Specific variant value (e.g. Red, XL, 256GB)")
    price: Optional[float] = Field(default=None, ge=0.0, description="Variant price")
    original_price: Optional[float] = Field(default=None, ge=0.0, description="Variant original price before discount")
    stock: Optional[int] = Field(default=None, ge=0, description="Available stock quantity")
    available: bool = Field(default=True, description="Availability flag")
    variant_image: Optional[str] = Field(default=None, description="Variant specific thumbnail or image URL")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary variation metadata")


class Specification(BaseModel):
    """Technical or catalog specification key-value pair."""
    key: str = Field(..., description="Specification name / label")
    value: str = Field(..., description="Specification value")
    group: Optional[str] = Field(default="General", description="Grouping category for specification")


class ImageRecord(BaseModel):
    """Normalized image record with deduplication and lazy-load resolution."""
    url: str = Field(..., description="Clean canonical image URL")
    position: int = Field(default=0, description="Display order index")
    is_primary: bool = Field(default=False, description="Primary hero image flag")
    variant_id: Optional[str] = Field(default=None, description="Linked SKU variant ID")
    alt_text: Optional[str] = Field(default=None, description="Alternative text description")


class ProductIntelligence(BaseModel):
    """Core normalized product intelligence model across all marketplaces."""

    # Identifiers & Origins
    product_id: str = Field(..., description="Unique platform product identifier")
    marketplace: MarketplaceType = Field(..., description="Origin marketplace platform")
    source_url: str = Field(..., description="Original crawled listing URL")
    canonical_url: str = Field(..., description="Normalized clean canonical product URL")

    # Title & Descriptions
    title: str = Field(..., min_length=1, description="Normalized listing title")
    description_text: Optional[str] = Field(default=None, description="Plain text sanitized description")
    description_html: Optional[str] = Field(default=None, description="Sanitized safe HTML description")

    # Pricing & Currency
    price: float = Field(..., ge=0.0, description="Current selling price")
    original_price: Optional[float] = Field(default=None, ge=0.0, description="Original list price before discount")
    discount: Optional[float] = Field(default=None, description="Calculated or reported discount percentage/value")
    currency: str = Field(default="USD", description="3-letter ISO currency code")

    # Engagement & Trend Signals (High Priority)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0, description="Average rating score out of 5")
    review_count: int = Field(default=0, ge=0, description="Total number of customer reviews")
    rating_count: Optional[int] = Field(default=None, ge=0, description="Total number of star ratings submitted")
    sold_count: Optional[int] = Field(default=None, ge=0, description="Normalized numeric estimated units sold")
    raw_sold_text: Optional[str] = Field(default=None, description="Original unparsed sales text string")

    # Brand & Seller Information
    brand: Optional[str] = Field(default=None, description="Brand name or 'No Brand'")
    seller_id: Optional[str] = Field(default=None, description="Unique merchant/seller identifier")
    seller_name: Optional[str] = Field(default=None, description="Display name of the selling merchant")
    seller_rating: Optional[float] = Field(default=None, ge=0.0, description="Merchant feedback or rating score")
    seller_review_count: Optional[int] = Field(default=None, ge=0, description="Total seller ratings/reviews")
    seller_url: Optional[str] = Field(default=None, description="Seller store URL")

    # Category Classification
    category_id: Optional[str] = Field(default=None, description="Leaf category ID")
    category_name: Optional[str] = Field(default=None, description="Primary category name")
    category_path: Optional[str] = Field(default=None, description="Full breadcrumb path (e.g. Electronics > Audio > Headphones)")
    breadcrumbs: List[str] = Field(default_factory=list, description="Ordered hierarchy of category nodes")

    # Stock & Sub-Entities
    availability: bool = Field(default=True, description="In-stock availability status")
    primary_image: Optional[str] = Field(default=None, description="Hero image canonical URL")
    images: List[ImageRecord] = Field(default_factory=list, description="Deduplicated ordered gallery images")
    variants: List[Variant] = Field(default_factory=list, description="Structured SKU variations")
    specifications: List[Specification] = Field(default_factory=list, description="Key-value specifications list")
    reviews: List[Any] = Field(default_factory=list, description="Normalized extracted customer reviews")

    # Observability, Confidence & Provenance
    raw_data: Optional[str] = Field(default=None, description="Raw source payload (HTML, JSON, or JSON-LD snippet)")
    source_fields: Dict[str, Any] = Field(default_factory=dict, description="Raw unnormalized marketplace fields")
    extraction_warnings: List[str] = Field(default_factory=list, description="Diagnostics and non-fatal warnings")
    extraction_confidence: Dict[str, float] = Field(default_factory=dict, description="Field-level confidence diagnostics")
    overall_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Aggregate confidence score")

    # Timestamps
    extraction_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when extraction completed"
    )
    first_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Initial discovery timestamp"
    )
    last_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Most recent scrape timestamp"
    )
