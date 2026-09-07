"""Product data model and associated schema specifications."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.constants import PARSER_VERSION, SCHEMA_VERSION, SCRAPER_VERSION
from app.models.image import Image


class ProductVariant(BaseModel):
    """Product SKU variant (color, size, storage)."""
    sku_id: Optional[str] = Field(default=None, description="SKU identifier")
    name: str = Field(..., description="Variant name")
    color: Optional[str] = Field(default=None, description="Color attribute")
    size: Optional[str] = Field(default=None, description="Size attribute")
    price: Optional[float] = Field(default=None, description="Variant price")
    available: bool = Field(default=True, description="Availability flag")


class SellerInfo(BaseModel):
    """Seller and merchant attributes."""
    seller_id: Optional[str] = Field(default=None, description="Seller identifier")
    name: str = Field(..., description="Seller display name")
    url: Optional[str] = Field(default=None, description="Seller shop URL")
    rating_score: Optional[float] = Field(default=None, description="Seller rating")
    positive_rating_percentage: Optional[float] = Field(default=None, description="Positive feedback percentage")
    is_mall: bool = Field(default=False, description="Whether seller is Daraz Mall")
    is_verified: bool = Field(default=False, description="Verified merchant flag")


class CategoryHierarchy(BaseModel):
    """Category navigation hierarchy."""
    category_id: Optional[str] = Field(default=None, description="Leaf category ID")
    category_name: str = Field(..., description="Leaf category name")
    level_1: Optional[str] = Field(default=None, description="Top-level category")
    level_2: Optional[str] = Field(default=None, description="Secondary category")
    level_3: Optional[str] = Field(default=None, description="Tertiary category")
    breadcrumb_path: Optional[str] = Field(default=None, description="Full breadcrumb path")


class Product(BaseModel):
    """Core standard data contract for scraped product information."""

    product_id: str = Field(..., description="Unique platform product identifier")
    title: str = Field(..., min_length=1, description="Product listing title")
    description: Optional[str] = Field(default=None, description="Detailed product description text")
    url: str = Field(..., description="Full canonical product URL")

    # Pricing & Currency
    price: float = Field(..., ge=0.0, description="Current selling price")
    original_price: Optional[float] = Field(default=None, ge=0.0, description="Original list price before discount")
    discount: Optional[float] = Field(default=None, description="Discount amount or percentage numeric representation")
    currency: str = Field(default="PKR", description="ISO currency code")

    # Metrics & Engagement
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0, description="Average rating score out of 5")
    review_count: int = Field(default=0, ge=0, description="Total count of customer reviews")
    sold_count: Optional[int] = Field(default=None, ge=0, description="Estimated total units sold")

    # Brand & Seller Information
    brand: Optional[str] = Field(default=None, description="Brand name or 'No Brand'")
    seller_id: Optional[str] = Field(default=None, description="Identifier of the selling merchant")
    seller_name: Optional[str] = Field(default=None, description="Display name of the merchant")

    # Category Classification
    category_id: Optional[str] = Field(default=None, description="Leaf category ID")
    category_name: Optional[str] = Field(default=None, description="Category name hierarchy")

    # Stock & Variations
    availability: bool = Field(default=True, description="Whether the item is currently in stock")
    images: List[Image] = Field(default_factory=list, description="Associated image gallery records")
    variants: List[Dict[str, Any]] = Field(default_factory=list, description="SKU variations (size, color, etc.)")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Key-value product specifications")

    # Provenance & Versioning
    source: str = Field(default="daraz", description="Origin marketplace platform")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Initial discovery / scrape timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Most recent update timestamp"
    )
    first_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Initial discovery timestamp (alias for created_at)"
    )
    last_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Most recent scrape timestamp (alias for updated_at)"
    )
    schema_version: str = Field(default=SCHEMA_VERSION, description="Data contract schema version")
    parser_version: str = Field(default=PARSER_VERSION, description="Parser implementation version")
    scraper_version: str = Field(default=SCRAPER_VERSION, description="Scraper runtime version")
