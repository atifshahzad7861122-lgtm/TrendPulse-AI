"""Configuration and settings specific to the Daraz Pakistan marketplace discovery engine."""

from typing import List, Set
from pydantic import BaseModel, Field

from app.discovery.selectors import DarazSelectors


class DarazDiscoveryConfig(BaseModel):
    """Configuration parameters for Daraz marketplace catalog and search discovery."""

    # Base URLs and Paths
    BASE_URL: str = Field(default="https://www.daraz.pk", description="Daraz Pakistan base domain")
    SEARCH_PATH: str = Field(default="/catalog/", description="Catalog/search endpoint")
    CATEGORY_BASE_PATH: str = Field(default="", description="Base path for categories")

    # Default Keywords for Keyword Discovery Strategy
    DEFAULT_KEYWORDS: List[str] = Field(
        default_factory=lambda: [
            "laptop",
            "mobile",
            "headphones",
            "smartwatch",
            "camera",
            "keyboard",
            "shoes",
            "perfume",
            "television",
            "tablet",
            "gaming",
            "printer",
        ],
        description="Default keywords for search-based product discovery",
    )

    # Pagination & Crawl Limits
    PAGE_PARAM: str = Field(default="page", description="Query parameter for page number")
    PAGE_SIZE_PARAM: str = Field(default="pageSize", description="Query parameter for page size")
    DEFAULT_PAGE_SIZE: int = Field(default=40, ge=1, le=100)
    MAX_PAGES_PER_CATEGORY: int = Field(default=50, ge=1, description="Safety limit on category pagination")
    MAX_PAGES_PER_SEARCH: int = Field(default=20, ge=1, description="Safety limit on search query pagination")

    # Worker Concurrency & Batch Limits
    MAX_CONCURRENT_CATEGORIES: int = Field(default=2, ge=1, le=10)
    MAX_CONCURRENT_PAGES: int = Field(default=3, ge=1, le=20)
    QUEUE_BATCH_SIZE: int = Field(default=50, ge=1, le=500, description="Batch size for queue flushing to storage")

    # Tracking & Noise Query Parameters to strip during URL normalization
    STRIP_QUERY_PARAMS: Set[str] = Field(
        default_factory=lambda: {
            "spm",
            "scm",
            "searchId",
            "clicktrack",
            "wh_pid",
            "pos",
            "acm",
            "pvid",
            "trafficFrom",
            "laz_token",
            "dsource",
            "_keyori",
            "from",
            "isFirstRequest",
            "current_key",
            "exptype",
            "search_source",
            "sort",
            "q",  # On PDP pages, q is search context
            "trackInfo",
            "item_id",
        }
    )

    # DOM Selectors for Parsing (Delegated to DarazSelectors class)
    CATEGORY_MENU_SELECTORS: List[str] = Field(default_factory=lambda: DarazSelectors.CATEGORY_MENU_ROOT)
    CATEGORY_ROOT_SELECTORS: List[str] = Field(default_factory=lambda: DarazSelectors.CATEGORY_ROOT_ITEMS)
    CATEGORY_SUB_SELECTORS: List[str] = Field(default_factory=lambda: DarazSelectors.CATEGORY_SUB_ITEMS)
    PRODUCT_CARD_SELECTORS: List[str] = Field(default_factory=lambda: DarazSelectors.PRODUCT_CARDS)
    PRODUCT_LINK_SELECTORS: List[str] = Field(default_factory=lambda: DarazSelectors.PRODUCT_LINKS)
    PAGINATION_SELECTORS: List[str] = Field(default_factory=lambda: DarazSelectors.PAGINATION_CONTAINERS)
    NEXT_PAGE_SELECTORS: List[str] = Field(default_factory=lambda: DarazSelectors.NEXT_PAGE_BUTTONS)

    # Anti-Bot & Challenge Signatures
    CAPTCHA_INDICATORS: List[str] = Field(
        default_factory=lambda: [
            "punish",
            "captcha",
            "sec.daraz.pk",
            "verify you are human",
            "pardon the interruption",
            "please slide to verify",
            "security check",
            "baxia-dialog",
            "nocaptcha",
            "validate.js",
            "nc_wrapper",
        ]
    )

    BLOCKED_INDICATORS: List[str] = Field(
        default_factory=lambda: [
            "access denied",
            "403 forbidden",
            "you don't have permission to access",
            "temporarily blocked",
            "ip is blocked",
            "cf-error-details",
        ]
    )


# Default shared discovery configuration instance
default_discovery_config = DarazDiscoveryConfig()
