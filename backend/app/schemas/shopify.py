from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ShopifyProductItem(BaseModel):
    id: str
    store_domain: str
    product_id: str
    title: str
    handle: Optional[str] = None
    product_url: str
    image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    price: float = 0.0
    price_formatted: str = "$0.00"
    compare_at_price: Optional[float] = None
    compare_at_price_formatted: Optional[str] = None
    discount_percentage: float = 0.0
    discount_label: Optional[str] = None
    currency: str = "USD"
    available: bool = True
    rating: float = 0.0
    review_count: int = 0
    source_provider: str = "shopify_scout"
    variants_count: int = 1
    first_seen_at: datetime
    last_seen_at: datetime
    last_synced_at: datetime
    raw_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ShopifyProductListResponse(BaseModel):
    items: List[ShopifyProductItem]
    total: int
    page: int
    limit: int
    store_domain: Optional[str] = None
    source_platform: str = "Shopify"
    source_provider: str = "database_cache"
    is_live: bool = False
    last_synced_at: Optional[datetime] = None
    data_age_seconds: Optional[int] = None
    message: Optional[str] = None

class ShopifySyncRequest(BaseModel):
    store_domain: str
    limit: int = Field(default=50, ge=1, le=250)
    page: int = Field(default=1, ge=1)
    collection: Optional[str] = None
    force_live: bool = False

class ProviderAttemptLog(BaseModel):
    provider_name: str
    priority: int
    status: str  # "success", "failed", "rate_limited", "skipped_cooldown"
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None

class ShopifySyncResponse(BaseModel):
    success: bool
    store_domain: str
    source_platform: str = "Shopify"
    source_provider: str
    is_live: bool
    status: str  # "success", "cached", "unavailable", "failed"
    products_fetched: int = 0
    products_inserted: int = 0
    products_updated: int = 0
    snapshots_created: int = 0
    last_synced_at: Optional[datetime] = None
    data_age_seconds: Optional[int] = None
    provider_attempts: List[Dict[str, Any]] = Field(default_factory=list)
    products: List[ShopifyProductItem] = Field(default_factory=list)
    message: str

class ShopifyProviderHealthItem(BaseModel):
    provider_name: str
    display_name: str
    priority: int
    enabled: bool
    status: str  # "healthy", "degraded", "rate_limited", "unhealthy"
    consecutive_failures: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    rate_limited_requests: int
    success_rate: float = 100.0
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    is_in_cooldown: bool = False
    cooldown_remaining_seconds: int = 0
    last_error_code: Optional[int] = None
    last_error_message: Optional[str] = None

class ShopifyStatusResponse(BaseModel):
    overall_status: str  # "healthy", "degraded", "all_down", "cached_fallback"
    preferred_provider: str
    active_providers_count: int
    total_products_stored: int
    total_snapshots_stored: int
    last_synced_at: Optional[datetime] = None
    data_age_seconds: Optional[int] = None
    providers: List[ShopifyProviderHealthItem]
    recent_sync_runs: List[Dict[str, Any]] = Field(default_factory=list)
