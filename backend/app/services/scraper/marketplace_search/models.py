"""
Canonical Domain and Contract Models for Marketplace Search.

Defines the search request contract, intermediate search candidate entity,
and final search result schema.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.services.scraper.marketplace_search.constants import (
    DEFAULT_RESULT_LIMIT,
    MAX_RESULT_LIMIT,
    DEFAULT_CANDIDATE_TARGET,
    MIN_CANDIDATES
)
from backend.app.services.scraper.marketplace_search.enums import (
    MarketplaceType,
    MarketplaceSearchStatus
)


class MarketplaceSearchRequest(BaseModel):
    """
    Canonical request contract for multi-marketplace product search.
    Validates keyword, result boundaries, and candidate limits.
    """
    marketplace: MarketplaceType = Field(
        ...,
        description="Target marketplace: daraz, amazon, ebay, or shopify"
    )
    keyword: str = Field(
        ...,
        description="Search keyword to query against the target marketplace"
    )
    desired_results: int = Field(
        default=DEFAULT_RESULT_LIMIT,
        description=f"Desired number of verified output products (1-{MAX_RESULT_LIMIT})"
    )
    candidate_target: int = Field(
        default=DEFAULT_CANDIDATE_TARGET,
        description="Internal target candidate count for extraction pipeline"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User context for multi-tenant isolation"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session context for trace isolation"
    )
    execute_pipeline: bool = Field(
        default=False,
        description="Whether to execute pipeline immediately and return verified results"
    )


    @field_validator("keyword")
    @classmethod
    def validate_and_normalize_keyword(cls, v: str) -> str:
        if v is None:
            raise ValueError("Search keyword cannot be None.")
        normalized = v.strip()
        if not normalized:
            raise ValueError("Search keyword cannot be empty or whitespace-only.")
        return normalized

    @field_validator("desired_results")
    @classmethod
    def validate_desired_results(cls, v: int) -> int:
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError("desired_results must be an integer.")
        if v <= 0:
            raise ValueError("desired_results must be a positive integer greater than 0.")
        if v > MAX_RESULT_LIMIT:
            raise ValueError(
                f"desired_results cannot exceed MAX_RESULT_LIMIT ({MAX_RESULT_LIMIT}). Requested: {v}"
            )
        return v

    @field_validator("candidate_target")
    @classmethod
    def validate_candidate_target(cls, v: int) -> int:
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError("candidate_target must be an integer.")
        if v <= 0:
            raise ValueError("candidate_target must be a positive integer greater than 0.")
        return v

    @model_validator(mode="after")
    def validate_candidate_target_vs_desired_results(self) -> "MarketplaceSearchRequest":
        if self.candidate_target < self.desired_results:
            raise ValueError(
                f"candidate_target ({self.candidate_target}) cannot be smaller than "
                f"desired_results ({self.desired_results})."
            )
        return self


class MarketplaceSearchCandidate(BaseModel):
    """
    Canonical intermediate candidate model produced by any marketplace provider.
    Maintains pure factual data without fabricating missing values.
    """
    external_product_id: Optional[str] = Field(
        default=None,
        description="Marketplace-specific external product/listing identifier"
    )
    marketplace: MarketplaceType = Field(
        ...,
        description="Target marketplace where the candidate was observed"
    )
    title: str = Field(
        ...,
        description="Factual product title as extracted from the marketplace"
    )
    url: str = Field(
        ...,
        description="Direct link to the product listing on the marketplace"
    )
    image_url: Optional[str] = Field(
        default=None,
        description="Primary product image URL"
    )
    price: Optional[float] = Field(
        default=None,
        description="Current listing price. None if unavailable. Never fabricated."
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency ISO code (e.g. PKR, USD). None if unavailable."
    )
    original_price: Optional[float] = Field(
        default=None,
        description="Pre-discount list price if available"
    )
    seller: Optional[str] = Field(
        default=None,
        description="Merchant/Seller name if available. Never fabricated."
    )
    brand: Optional[str] = Field(
        default=None,
        description="Brand name if identified on listing"
    )
    category: Optional[str] = Field(
        default=None,
        description="Category name or hierarchy breadcrumb"
    )
    rating: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Average review score (0-5). None if not displayed. Never fabricated."
    )
    review_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total review count. None if not displayed. Never fabricated."
    )
    availability: Optional[bool] = Field(
        default=None,
        description="Stock availability status"
    )
    description: Optional[str] = Field(
        default=None,
        description="Product summary or description snippet"
    )
    source_provider: str = Field(
        ...,
        description="Name of the provider engine that extracted this candidate"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL of the page from which this item was extracted"
    )
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Exact timestamp when this observation occurred"
    )
    raw_payload_reference: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Raw payload snapshot or pointer for full auditability"
    )


class MarketplaceSearchResult(BaseModel):
    """
    Canonical response contract for marketplace search operations.
    Reports pipeline transition metrics and verified product results.
    """
    search_id: str = Field(
        default_factory=lambda: f"mkt_search_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for the search session"
    )
    marketplace: MarketplaceType = Field(
        ...,
        description="Target marketplace for this search"
    )
    keyword: str = Field(
        ...,
        description="Normalized search keyword"
    )
    status: MarketplaceSearchStatus = Field(
        default=MarketplaceSearchStatus.QUEUED,
        description="Current lifecycle status of the search operation"
    )
    candidate_count: int = Field(
        default=0,
        ge=0,
        description="Raw candidates extracted from provider"
    )
    normalized_count: int = Field(
        default=0,
        ge=0,
        description="Candidates successfully normalized into standard schema"
    )
    quality_passed_count: int = Field(
        default=0,
        ge=0,
        description="Candidates passing Data Quality verification gates"
    )
    deduplicated_count: int = Field(
        default=0,
        ge=0,
        description="Unique candidates remaining after deduplication"
    )
    returned_count: int = Field(
        default=0,
        ge=0,
        description="Final count of verified products returned to dashboard"
    )
    products: List[MarketplaceSearchCandidate] = Field(
        default_factory=list,
        description="Canonical verified products. Strictly no demo or synthetic items."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when search request was created"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when search reached terminal state"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error details if search failed"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable informational message"
    )
