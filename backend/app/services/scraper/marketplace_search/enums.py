"""
Canonical Enums for Marketplace Search Pipeline.

Defines strictly validated marketplace identifiers, lifecycle search states,
and provider provenance values.
"""

from enum import Enum
from typing import Set


class MarketplaceType(str, Enum):
    """
    Canonical supported ecommerce marketplace types for search.
    Strictly restricted to Daraz, Amazon, eBay, and Shopify.
    """
    DARAZ = "daraz"
    AMAZON = "amazon"
    EBAY = "ebay"
    SHOPIFY = "shopify"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if member.value == normalized:
                    return member
        return None

    @classmethod
    def values(cls) -> Set[str]:
        return {m.value for m in cls}


class MarketplaceSearchStatus(str, Enum):
    """
    Controlled lifecycle states for marketplace search jobs.
    Distinguishes active processing states from terminal states.
    """
    QUEUED = "queued"
    RUNNING = "running"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT_DATA = "insufficient_data"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if member.value == normalized:
                    return member
        return None

    @classmethod
    def terminal_states(cls) -> Set["MarketplaceSearchStatus"]:
        return {cls.COMPLETED, cls.FAILED, cls.INSUFFICIENT_DATA}

    @classmethod
    def active_states(cls) -> Set["MarketplaceSearchStatus"]:
        return {cls.QUEUED, cls.RUNNING, cls.PROCESSING}

    def is_terminal(self) -> bool:
        return self in self.terminal_states()

    def is_active(self) -> bool:
        return self in self.active_states()


class SearchProviderName(str, Enum):
    """
    Canonical provider provenance values for data acquisition.
    """
    DARAZ_SPECIALIZED = "daraz_specialized"
    SCRAPEGRAPHAI = "scrapegraphai"
    UNIVERSAL = "universal"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if member.value == normalized:
                    return member
        return None
