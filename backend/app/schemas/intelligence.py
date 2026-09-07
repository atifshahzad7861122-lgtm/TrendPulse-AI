from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PlatformListingItem(BaseModel):
    id: str
    unified_product_id: str
    platform: str  # "Daraz", "Shopify", etc.
    platform_product_id: str
    store_domain: Optional[str] = None
    product_url: str
    title: str
    normalized_title: str
    price: float
    price_formatted: str
    original_price: Optional[float] = None
    original_price_formatted: Optional[str] = None
    currency: str = "USD"
    discount_percentage: float = 0.0
    discount_label: Optional[str] = None
    seller_name: Optional[str] = None
    vendor: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    available: bool = True
    image_url: Optional[str] = None
    source_provider: str = "direct"
    last_synced_at: datetime
    completeness_score: float = 1.0
    raw_data: Dict[str, Any] = Field(default_factory=dict)

class PriceComparisonItem(BaseModel):
    platform: str
    store_domain: Optional[str] = None
    price: float
    price_formatted: str
    original_price: Optional[float] = None
    original_price_formatted: Optional[str] = None
    currency: str
    discount_percentage: float = 0.0
    discount_label: Optional[str] = None
    available: bool = True
    seller_or_vendor: Optional[str] = None
    product_url: str
    last_updated: datetime

class PlatformComparisonItem(BaseModel):
    platform: str
    store_domain: Optional[str] = None
    title: str
    price: float
    price_formatted: str
    currency: str
    discount_percentage: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    available: bool = True
    seller_name: Optional[str] = None
    vendor: Optional[str] = None
    product_url: str
    image_url: Optional[str] = None
    source_provider: str

class UnifiedProductItem(BaseModel):
    id: str
    unified_product_id: str
    canonical_name: str
    normalized_name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    product_type: Optional[str] = None
    taxonomy_path: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    category_confidence: float = 1.0
    classification_method: str = "deterministic"
    needs_review: bool = False
    description: Optional[str] = None
    primary_image: Optional[str] = None
    identifiers: Dict[str, Any] = Field(default_factory=dict)
    platforms: List[str] = Field(default_factory=list)
    platform_count: int = 1
    listings_count: int = 1
    lowest_price: float = 0.0
    highest_price: float = 0.0
    average_price: float = 0.0
    primary_currency: str = "USD"
    price_range_formatted: str = ""
    avg_rating: float = 0.0
    total_reviews: int = 0
    completeness_score: float = 1.0
    first_seen_at: datetime
    last_seen_at: datetime
    last_synced_at: datetime


class UnifiedProductDetailResponse(BaseModel):
    unified_product: UnifiedProductItem
    platform_listings: List[PlatformListingItem]
    price_comparison: List[PriceComparisonItem]
    platform_comparison: List[PlatformComparisonItem]
    match_audit: Optional[Dict[str, Any]] = None

class UnifiedProductListResponse(BaseModel):
    items: List[UnifiedProductItem]
    total: number if False else int
    page: int = 1
    limit: int = 50
    total_pages: int = 1
    filters_applied: Dict[str, Any] = Field(default_factory=dict)

class UnifiedHistoricalPoint(BaseModel):
    timestamp: datetime
    platform: str
    store_domain: Optional[str] = None
    price: float
    currency: str
    available: bool
    rating: float
    review_count: int
    source_provider: str

class UnifiedProductHistoryResponse(BaseModel):
    unified_product_id: str
    canonical_name: str
    timeline: List[UnifiedHistoricalPoint]
    total_observations: int
    platforms: List[str]

class UnifiedSearchResponse(BaseModel):
    query: str
    total_matches: int
    items: List[UnifiedProductItem]
    page: int = 1
    limit: int = 50
