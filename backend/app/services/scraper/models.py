from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StartScraperJobRequest(BaseModel):
    marketplace: str = Field(default="daraz", description="Target marketplace: daraz, amazon, ebay, aliexpress, shopify")
    provider: str = Field(default="auto", description="Scraper provider: daraz_specialized, universal, scrapegraphai, auto")
    keywords: Optional[List[str]] = Field(default=None, description="Keywords for marketplace search")
    keyword: Optional[str] = Field(default=None, description="Single keyword alias")
    urls: Optional[List[str]] = Field(default=None, description="Direct listing URLs to crawl")
    url: Optional[str] = Field(default=None, description="Single URL alias")
    category: Optional[str] = Field(default=None, description="Category name or URL")
    max_products: int = Field(default=10, ge=1, le=500, description="Target product limit")
    max_workers: int = Field(default=2, ge=1, le=8, description="Worker pool concurrency")
    export_format: str = Field(default="json", description="Export format: json, jsonl, csv")
    dry_run: bool = Field(default=False, description="Dry run mode without network calls")


class ScraperJobProgressResponse(BaseModel):
    job_id: str
    marketplace: str
    provider: str = "auto"
    trigger_type: str = "manual"
    status: str
    target_count: int
    products_fetched: int = 0
    products_persisted: int = 0
    products_rejected: int = 0
    challenged_count: int = 0
    failed_count: int = 0
    current_throughput: float = 0.0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScraperJobListResponse(BaseModel):
    total: int
    jobs: List[ScraperJobProgressResponse]


class ScraperProductItem(BaseModel):
    id: str
    marketplace: str
    provider: str = "daraz_specialized"
    product_id: str
    title: str
    brand: Optional[str] = None
    price: float = 0.0
    original_price: Optional[float] = None
    discount: Optional[float] = None
    discount_label: Optional[str] = None
    currency: str = "PKR"
    rating: Optional[float] = None
    review_count: int = 0
    sold_count: Optional[int] = None
    seller_name: Optional[str] = None
    seller_id: Optional[str] = None
    seller_rating: Optional[float] = None
    seller_metrics: Dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = None
    availability: bool = True
    image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    product_url: str
    source_url: Optional[str] = None
    extraction_status: str = "complete"
    quality_status: str = "valid"
    confidence_score: float = 1.0
    challenge_status: Optional[str] = None
    description_text: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    variants: List[Dict[str, Any]] = Field(default_factory=list)
    reviews: List[Dict[str, Any]] = Field(default_factory=list)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload_available: bool = True


class ScraperProductListResponse(BaseModel):
    total: int
    products: List[ScraperProductItem]


class RawScrapedDataResponse(BaseModel):
    id: str
    marketplace: str
    product_id: str
    crawl_job_id: Optional[str] = None
    source_url: str
    canonical_url: Optional[str] = None
    parser_version: str = "1.0.0"
    extraction_status: str = "complete"
    quality_status: str = "valid"
    confidence_score: float = 1.0
    scraped_at: datetime
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    normalized_payload: Dict[str, Any] = Field(default_factory=dict)


class ScraperHistoricalSnapshotItem(BaseModel):
    id: str
    product_id: str
    platform: str
    price: float
    original_price: Optional[float] = None
    discount: Optional[float] = None
    rating: Optional[float] = None
    review_count: int = 0
    stock_status: str = "in_stock"
    observed_at: datetime


class ScraperProductHistoryResponse(BaseModel):
    product_id: str
    marketplace: str
    total_snapshots: int
    snapshots: List[ScraperHistoricalSnapshotItem]
