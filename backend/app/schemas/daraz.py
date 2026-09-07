from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class DarazProductItem(BaseModel):
    """
    Standardized TrendPulse product representation for Daraz marketplace items.
    """
    platform: str = "daraz"
    product_id: str
    name: str
    price: float = 0.0
    original_price: float = 0.0
    discount: float = 0.0
    discount_label: Optional[str] = None
    currency: str = "PKR"
    rating: float = 0.0
    review_count: int = 0
    seller_name: Optional[str] = None
    seller_id: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    sku: Optional[str] = None
    in_stock: bool = True
    location: Optional[str] = None
    sold_count: int = 0
    source: str = "daraz.pk"
    raw_data: Optional[Dict[str, Any]] = None

class DarazSellerInfo(BaseModel):
    seller_id: Optional[str] = None
    name: Optional[str] = None
    shop_id: Optional[int] = None
    seller_url: Optional[str] = None
    positive_seller_rating: Optional[str] = None
    ship_on_time: Optional[str] = None
    chat_response_rate: Optional[str] = None
    chat_url: Optional[str] = None
    raw_seller: Optional[Dict[str, Any]] = None

class DarazSkuVariant(BaseModel):
    sku_id: Optional[str] = None
    sku_name: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    in_stock: bool = True
    image: Optional[str] = None

class DarazProductDetails(BaseModel):
    """
    Comprehensive product detail entity including specs, warranty, seller metrics, and variants.
    """
    platform: str = "daraz"
    product_id: str
    name: str
    price: float = 0.0
    original_price: float = 0.0
    discount: float = 0.0
    discount_label: Optional[str] = None
    currency: str = "PKR"
    rating: float = 0.0
    review_count: int = 0
    in_stock: bool = True
    brand: Optional[str] = None
    category: Optional[str] = None
    category_breadcrumbs: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    warranty: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    main_image: Optional[str] = None
    product_url: Optional[str] = None
    seller: Optional[DarazSellerInfo] = None
    sku_variants: List[DarazSkuVariant] = Field(default_factory=list)
    ratings_breakdown: Dict[str, Any] = Field(default_factory=dict)
    qa_list: List[Dict[str, Any]] = Field(default_factory=list)
    reviews_sample: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = "daraz.pk"
    raw_module: Optional[Dict[str, Any]] = None

class DarazCategoryItem(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    url: Optional[str] = None
    level: int = 1
    subcategories: List[Dict[str, Any]] = Field(default_factory=list)

class DarazSearchResponse(BaseModel):
    query: str
    page: int = 1
    total_products: int = 0
    has_next: bool = False
    source: str = "daraz.pk"
    products: List[DarazProductItem] = Field(default_factory=list)

class DarazSellerProductsResponse(BaseModel):
    seller_id: str
    page: int = 1
    total_products: int = 0
    has_next: bool = False
    source: str = "daraz.pk"
    products: List[DarazProductItem] = Field(default_factory=list)

class DarazCallbackResponse(BaseModel):
    success: bool
    message: str
    account: Optional[str] = None
    seller_id: Optional[str] = None
    status: str = "authorized"
    error: Optional[str] = None

class DarazProviderHealthItem(BaseModel):
    provider_name: str
    priority: int
    status: str
    enabled: bool = True
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_success_at: Optional[str] = None
    last_failure_at: Optional[str] = None
    cooldown_until: Optional[str] = None

class DarazStatusResponse(BaseModel):
    connected: bool
    status: str  # "connected", "pending_authorization", "not_configured", "degraded"
    app_key_configured: bool
    app_secret_configured: bool
    callback_url: Optional[str] = None
    active_provider: str
    providers: List[DarazProviderHealthItem] = Field(default_factory=list)

