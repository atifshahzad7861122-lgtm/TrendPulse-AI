"""
Extraction Schemas for ScrapeGraphAI.

Defines the structured output contract passed to SmartScraperGraph/SearchGraph.
Strictly extracts factual fields without permitting hallucination of intelligence scores.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ScrapeGraphReviewItem(BaseModel):
    reviewer_name: Optional[str] = Field(default=None, description="Name or nickname of reviewer")
    rating: Optional[float] = Field(default=None, ge=1.0, le=5.0, description="Star rating given by customer")
    review_text: Optional[str] = Field(default="", description="Text content of the customer review")
    date: Optional[str] = Field(default=None, description="Date review was posted")
    variation: Optional[str] = Field(default=None, description="Purchased variation/color/size")
    verified_purchase: bool = Field(default=False, description="Whether this review is marked as a verified purchase")
    images: List[str] = Field(default_factory=list, description="URLs of user-uploaded review photos")


class ScrapeGraphVariantItem(BaseModel):
    sku_id: Optional[str] = Field(default=None, description="Unique SKU or variation identifier")
    name: str = Field(..., description="Variant name, e.g. 'Color: Midnight Blue, Size: XL'")
    price: Optional[float] = Field(default=None, description="Price specific to this variant if different")
    availability: bool = Field(default=True, description="Whether this variant is in stock")


class ScrapeGraphProductItem(BaseModel):
    product_id: Optional[str] = Field(default=None, description="Marketplace product ID or SKU if visible")
    title: str = Field(..., description="Full factual product title/name exactly as displayed on the page")
    price: float = Field(default=0.0, description="Current selling price as a numeric float")
    original_price: Optional[float] = Field(default=None, description="Original list price before discount")
    discount: Optional[float] = Field(default=None, description="Discount percentage or value if displayed")
    currency: Optional[str] = Field(default="PKR", description="Currency symbol or 3-letter code (e.g. PKR, USD)")
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0, description="Product average rating if displayed")
    review_count: int = Field(default=0, ge=0, description="Total number of customer reviews")
    availability: bool = Field(default=True, description="True if in stock, False if out of stock")
    brand: Optional[str] = Field(default=None, description="Product brand name")
    category: Optional[str] = Field(default=None, description="Product breadcrumb or category name")
    seller_name: Optional[str] = Field(default=None, description="Store or merchant seller name")
    seller_rating: Optional[float] = Field(default=None, description="Seller rating score or percentage")
    product_url: Optional[str] = Field(default=None, description="Direct URL to product page")
    image_url: Optional[str] = Field(default=None, description="Primary high-res product image URL")
    images: List[str] = Field(default_factory=list, description="All gallery product image URLs")
    description: Optional[str] = Field(default=None, description="Factual product description text")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Key-value product specifications")
    variants: List[ScrapeGraphVariantItem] = Field(default_factory=list, description="Product variations")
    reviews: List[ScrapeGraphReviewItem] = Field(default_factory=list, description="Extracted customer reviews")


class ScrapeGraphProductList(BaseModel):
    products: List[ScrapeGraphProductItem] = Field(default_factory=list, description="List of extracted products")
