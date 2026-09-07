"""
Canonical Provider Abstraction for Marketplace Search.

Defines the interface that all candidate-extracting marketplace search engines
(Daraz Specialized, ScrapeGraphAI, Amazon, eBay, Shopify) must implement.

Provider responsibility is strictly bounded to candidate acquisition and extraction.
Providers MUST NOT own Data Quality scoring, deduplication, ranking, persistence,
or frontend presentation logic.
"""

from abc import ABC, abstractmethod
from typing import List

from backend.app.services.scraper.marketplace_search.enums import MarketplaceType
from backend.app.services.scraper.marketplace_search.models import (
    MarketplaceSearchRequest,
    MarketplaceSearchCandidate
)


class MarketplaceSearchProvider(ABC):
    """
    Abstract interface for marketplace search data acquisition.
    Every marketplace search provider implementation must conform to this contract.
    """

    @abstractmethod
    async def search(
        self,
        request: MarketplaceSearchRequest
    ) -> List[MarketplaceSearchCandidate]:
        """
        Execute candidate search and acquisition on the target marketplace.

        Args:
            request: Canonical search request specification.

        Returns:
            List of raw intermediate MarketplaceSearchCandidate entities.
            Returns empty list if no results or insufficient data found.
        """
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Returns the unique identifier of this provider engine.
        (e.g. 'daraz_specialized', 'scrapegraphai', 'universal')
        """
        ...

    @abstractmethod
    def get_supported_marketplaces(self) -> List[MarketplaceType]:
        """
        Returns the list of marketplaces this provider is capable of searching.
        """
        ...
