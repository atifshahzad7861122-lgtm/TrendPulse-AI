"""
Pydantic Schemas for Marketplace Search API endpoints.

Phase 1 Canonical Architecture:
Prepares request/response validation schemas for POST /api/v1/marketplace-search.
"""

from backend.app.services.scraper.marketplace_search.enums import (
    MarketplaceType,
    MarketplaceSearchStatus,
    SearchProviderName
)
from backend.app.services.scraper.marketplace_search.constants import (
    MIN_CANDIDATES,
    DEFAULT_CANDIDATE_TARGET,
    DEFAULT_RESULT_LIMIT,
    MAX_RESULT_LIMIT
)
from backend.app.services.scraper.marketplace_search.models import (
    MarketplaceSearchRequest,
    MarketplaceSearchCandidate,
    MarketplaceSearchResult
)

__all__ = [
    "MarketplaceType",
    "MarketplaceSearchStatus",
    "SearchProviderName",
    "MIN_CANDIDATES",
    "DEFAULT_CANDIDATE_TARGET",
    "DEFAULT_RESULT_LIMIT",
    "MAX_RESULT_LIMIT",
    "MarketplaceSearchRequest",
    "MarketplaceSearchCandidate",
    "MarketplaceSearchResult",
]
