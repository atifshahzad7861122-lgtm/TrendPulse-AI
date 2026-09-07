"""
Marketplace Search Providers Package.
Exposes concrete implementations of MarketplaceSearchProvider for each supported platform.
"""

from backend.app.services.scraper.marketplace_search.providers.daraz_provider import (
    DarazMarketplaceSearchProvider
)
from backend.app.services.scraper.marketplace_search.providers.scrapegraphai_provider import (
    ScrapeGraphAIMarketplaceSearchProvider
)
from backend.app.services.scraper.marketplace_search.providers.shopify_provider import (
    ShopifyMarketplaceSearchProvider
)

__all__ = [
    "DarazMarketplaceSearchProvider",
    "ScrapeGraphAIMarketplaceSearchProvider",
    "ShopifyMarketplaceSearchProvider",
]
