"""Configuration specifications for Universal Multi-Marketplace Crawling Engine."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CrawlCacheMode(str, Enum):
    """Caching behavior modes (compatible with Crawl4AI CacheMode)."""
    ENABLED = "enabled"
    BYPASS = "bypass"
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    DISABLED = "disabled"


class UniversalCrawlerConfig(BaseModel):
    """Central configuration for universal multi-marketplace crawling."""
    # Concurrency & Dispatching
    max_concurrent_requests: int = Field(default=5, ge=1, le=50)
    requests_per_second: float = Field(default=2.0, gt=0.0)
    domain_rate_limits: Dict[str, float] = Field(default_factory=dict)
    
    # Timeouts & Retries
    http_timeout_seconds: float = Field(default=15.0, gt=1.0)
    browser_timeout_seconds: float = Field(default=30.0, gt=5.0)
    max_retries: int = Field(default=3, ge=0)
    retry_backoff_factor: float = Field(default=2.0, ge=1.0)
    
    # HTTP vs Browser Fallback
    enable_http_first: bool = True
    auto_browser_fallback: bool = True
    scroll_page_on_browser: bool = True
    headless_browser: bool = True
    
    # Caching
    cache_mode: CrawlCacheMode = CrawlCacheMode.ENABLED
    cache_ttl_seconds: int = Field(default=86400, ge=60)  # 24 hours
    cache_directory: str = "data/crawl_cache"
    
    # Deep Crawl Constraints
    max_deep_crawl_depth: int = Field(default=2, ge=1, le=10)
    max_deep_crawl_pages: int = Field(default=100, ge=1, le=1000)
    
    # Quality & Raw Preservation
    preserve_raw_payloads: bool = True
    min_confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    
    # User-Agent & Headers
    default_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
