"""Universal data models and schemas for multi-marketplace crawling."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl

from app.models.category import Category
from app.models.image import Image
from app.models.product import Product
from app.models.review import Review
from app.models.seller import Seller


class MarketplaceType(str, Enum):
    """Supported ecommerce marketplace types."""
    DARAZ = "daraz"
    AMAZON = "amazon"
    EBAY = "ebay"
    ALIEXPRESS = "aliexpress"
    SHOPIFY = "shopify"
    GENERIC = "generic"


class CrawlStatus(str, Enum):
    """Execution status for a crawl request or job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    MANUAL_INTERVENTION = "manual_intervention"
    CACHED = "cached"


class CrawlContentType(str, Enum):
    """Type of page/content being targeted."""
    PRODUCT = "product"
    CATEGORY = "category"
    SEARCH = "search"
    DEEP = "deep"
    GENERIC = "generic"


class CrawlRequest(BaseModel):
    """Input specification for a crawling operation."""
    url: str
    marketplace: Optional[MarketplaceType] = None
    content_type: CrawlContentType = CrawlContentType.GENERIC
    crawl_id: Optional[str] = None
    session_id: Optional[str] = None
    depth: int = 0
    max_depth: int = 1
    force_refresh: bool = False
    use_browser: bool = False
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    custom_cookies: Dict[str, str] = Field(default_factory=dict)
    js_code: Optional[str] = None
    wait_selector: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CrawlResponse(BaseModel):
    """Low-level fetch response from HTTP or browser client."""
    url: str
    status_code: int
    html: str
    markdown: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    source_engine: str = "http"  # 'http', 'browser', 'crawl4ai', 'cache'
    duration_ms: float = 0.0
    is_cached: bool = False
    screenshot_bytes: Optional[bytes] = None
    extracted_links: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UniversalCrawlResult(BaseModel):
    """Standardized high-level result containing extracted marketplace entities."""
    crawl_id: str
    url: str
    marketplace: MarketplaceType
    content_type: CrawlContentType
    status: CrawlStatus
    success: bool
    status_code: int = 200
    source_engine: str = "http"
    duration_ms: float = 0.0
    
    # Standardized domain entities
    product: Optional[Product] = None
    products: List[Product] = Field(default_factory=list)
    categories: List[Category] = Field(default_factory=list)
    reviews: List[Review] = Field(default_factory=list)
    sellers: List[Seller] = Field(default_factory=list)
    
    # Discovery navigation
    discovered_urls: List[str] = Field(default_factory=list)
    pagination_next_url: Optional[str] = None
    
    # Challenge detection
    challenge_detected: bool = False
    challenge_reason: Optional[str] = None
    
    # Raw preservation
    raw_html: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeepCrawlNode(BaseModel):
    """Node in a recursive deep crawling graph."""
    url: str
    depth: int
    parent_url: Optional[str] = None
    status: CrawlStatus = CrawlStatus.PENDING
    score: float = 0.0
    retry_count: int = 0
