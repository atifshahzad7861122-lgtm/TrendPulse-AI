"""Data models and contracts for the Daraz discovery engine."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.core.constants import CrawlStatus


class CategoryTarget(BaseModel):
    """Discovered category or subcategory node in the marketplace catalog tree."""

    category_id: str = Field(..., description="Unique slug or ID of the category")
    name: str = Field(..., min_length=1, description="Display title of the category")
    parent_id: Optional[str] = Field(default=None, description="Parent category ID if subcategory")
    url: str = Field(..., description="Canonical category URL")
    level: int = Field(default=1, ge=1, description="Hierarchy depth (1=Top-level, 2=Subcategory, 3=Leaf)")
    is_leaf: bool = Field(default=False, description="True if no subcategories exist below this node")
    source: str = Field(default="catalog_tree", description="Discovery source (e.g. catalog_tree, breadcrumb)")
    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when target was discovered",
    )

    @property
    def parent_category_id(self) -> Optional[str]:
        """Backward-compatible property for parent_category_id."""
        return self.parent_id


class ProductTarget(BaseModel):
    """Discovered product target reference queued for downstream extraction."""

    product_id: str = Field(..., description="Unique item ID extracted from URL/page")
    url: str = Field(..., description="Original discovered product URL")
    marketplace: Optional[Any] = Field(default=None, description="Origin marketplace if known")
    canonical_url: Optional[str] = Field(default=None, description="Canonical clean product URL without tracking noise")
    source: str = Field(default="category", description="Discovery channel (e.g., category, keyword, recommendation)")
    keyword: Optional[str] = Field(default=None, description="Search keyword if found via search query")
    source_query: Optional[str] = Field(default=None, description="Alias for keyword query")
    category_id: Optional[str] = Field(default=None, description="Category ID where discovered")
    category_name: Optional[str] = Field(default=None, description="Category name where discovered")
    source_category: Optional[str] = Field(default=None, description="Alias for source category name/ID")
    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when target was discovered",
    )

    def model_post_init(self, __context: Any) -> None:
        """Ensure canonical_url and source aliases are populated."""
        if not self.canonical_url:
            self.canonical_url = self.url
        if self.keyword and not self.source_query:
            self.source_query = self.keyword
        elif self.source_query and not self.keyword:
            self.keyword = self.source_query
        if self.category_name and not self.source_category:
            self.source_category = self.category_name
        elif self.source_category and not self.category_name:
            self.category_name = self.source_category


class DiscoveryCheckpointState(BaseModel):
    """Serializable state representing a resumable discovery checkpoint."""

    crawl_id: str = Field(..., description="Discovery crawl session ID")
    strategy: str = Field(default="all", description="Active discovery strategy (category, keyword, all)")
    current_category: Optional[str] = Field(default=None, description="Category being actively processed")
    current_keyword: Optional[str] = Field(default=None, description="Keyword being actively processed")
    current_page: int = Field(default=1, ge=1, description="Last successfully processed page number")
    discovered_categories: List[str] = Field(default_factory=list, description="IDs of discovered categories")
    processed_product_ids: List[str] = Field(default_factory=list, description="IDs of discovered products")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Running discovery statistics")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Checkpoint creation timestamp",
    )


class DiscoveryRun(BaseModel):
    """Execution state and statistics for a marketplace discovery crawl."""

    crawl_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique discovery crawl session ID")
    strategy: str = Field(default="all", description="Discovery strategy: 'category', 'keyword', 'all'")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Discovery session start timestamp",
    )
    finished_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    status: CrawlStatus = Field(default=CrawlStatus.PENDING, description="Current lifecycle state")

    categories_discovered: int = Field(default=0, ge=0, description="Top-level categories discovered")
    subcategories_discovered: int = Field(default=0, ge=0, description="Subcategories discovered")
    product_urls_discovered: int = Field(default=0, ge=0, description="Total raw product links extracted")
    unique_products_discovered: int = Field(default=0, ge=0, description="Unique products queued after deduplication")
    duplicates_removed: int = Field(default=0, ge=0, description="Duplicate product links discarded")

    pages_processed: int = Field(default=0, ge=0, description="Listing pages successfully parsed")
    pages_failed: int = Field(default=0, ge=0, description="Pages that failed due to errors")
    captcha_events: int = Field(default=0, ge=0, description="CAPTCHA/challenge trigger count")
    parser_errors: int = Field(default=0, ge=0, description="Parsing or schema extraction errors")
