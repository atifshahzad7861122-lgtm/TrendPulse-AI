"""
Canonical Marketplace Search Package.

Phase 1 production-ready foundation establishing contracts, enums, limits,
models, and provider abstractions across Daraz, Amazon, eBay, and Shopify.
"""

from backend.app.services.scraper.marketplace_search.constants import (
    MIN_CANDIDATES,
    DEFAULT_CANDIDATE_TARGET,
    DEFAULT_RESULT_LIMIT,
    MAX_RESULT_LIMIT
)
from backend.app.services.scraper.marketplace_search.enums import (
    MarketplaceType,
    MarketplaceSearchStatus,
    SearchProviderName
)
from backend.app.services.scraper.marketplace_search.models import (
    MarketplaceSearchRequest,
    MarketplaceSearchCandidate,
    MarketplaceSearchResult
)
from backend.app.services.scraper.marketplace_search.provider import (
    MarketplaceSearchProvider
)
from backend.app.services.scraper.marketplace_search.orchestrator import (
    MarketplaceSearchOrchestrator
)
from backend.app.services.scraper.marketplace_search.providers import (
    DarazMarketplaceSearchProvider,
    ScrapeGraphAIMarketplaceSearchProvider,
    ShopifyMarketplaceSearchProvider
)

__all__ = [
    # Constants
    "MIN_CANDIDATES",
    "DEFAULT_CANDIDATE_TARGET",
    "DEFAULT_RESULT_LIMIT",
    "MAX_RESULT_LIMIT",
    # Enums
    "MarketplaceType",
    "MarketplaceSearchStatus",
    "SearchProviderName",
    # Models
    "MarketplaceSearchRequest",
    "MarketplaceSearchCandidate",
    "MarketplaceSearchResult",
    # Provider Abstraction & Orchestrator
    "MarketplaceSearchProvider",
    "MarketplaceSearchOrchestrator",
    # Providers
    "DarazMarketplaceSearchProvider",
    "ScrapeGraphAIMarketplaceSearchProvider",
    "ShopifyMarketplaceSearchProvider",
]

