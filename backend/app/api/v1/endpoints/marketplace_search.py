"""
Marketplace Search Endpoint.

Exposes endpoint: POST /api/v1/marketplace-search
Validates incoming search requests and executes the canonical candidate acquisition pipeline
via MarketplaceSearchOrchestrator.
Supports both synchronous immediate execution (?execute=true or execute_pipeline=True)
and canonical queued job intake.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status

from backend.app.schemas.common import ResponseModel
from backend.app.models.domain import User
from backend.app.api.deps import (
    get_current_user_optional,
    get_marketplace_search_orchestrator
)
from backend.app.services.scraper.marketplace_search import (
    MarketplaceSearchRequest,
    MarketplaceSearchResult,
    MarketplaceSearchStatus,
    MarketplaceSearchOrchestrator
)

logger = logging.getLogger("trendpulse.api.marketplace_search")
router = APIRouter()


@router.post(
    "",
    response_model=ResponseModel[MarketplaceSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Submit and execute a canonical marketplace search request"
)
async def submit_marketplace_search(
    request: MarketplaceSearchRequest,
    execute: bool = Query(False, description="Whether to synchronously execute candidate acquisition and verification"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    orchestrator: MarketplaceSearchOrchestrator = Depends(get_marketplace_search_orchestrator)
) -> ResponseModel[MarketplaceSearchResult]:
    """
    Submits and processes a canonical marketplace search request.

    If execute is True (via query param or execute_pipeline in body),
    executes end-to-end candidate acquisition (200-250+ candidates),
    normalization, Data Quality evaluation, deduplication, ranking, and persistence,
    returning up to 30 verified products.
    Otherwise returns canonical queued job intake response.
    """
    # Enforce user context if authenticated
    user_id = current_user.id if current_user else request.user_id

    should_execute = execute or request.execute_pipeline

    if should_execute:
        try:
            result = await orchestrator.execute_search(request=request, user_id=user_id)
            return ResponseModel(
                success=result.status != MarketplaceSearchStatus.FAILED,
                message=result.message or f"Marketplace search {result.status.value}",
                data=result
            )
        except Exception as err:
            logger.exception(f"Unhandled error in marketplace search: {err}")
            fail_res = MarketplaceSearchResult(
                search_id=f"mkt_search_{uuid.uuid4().hex[:12]}",
                marketplace=request.marketplace,
                keyword=request.keyword,
                status=MarketplaceSearchStatus.FAILED,
                error="Internal error occurred while executing marketplace search",
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
            return ResponseModel(
                success=False,
                message="Marketplace search execution failed",
                data=fail_res
            )

    # Canonical queued result
    search_id = f"mkt_search_{uuid.uuid4().hex[:12]}"
    result = MarketplaceSearchResult(
        search_id=search_id,
        marketplace=request.marketplace,
        keyword=request.keyword,
        status=MarketplaceSearchStatus.QUEUED,
        candidate_count=0,
        normalized_count=0,
        quality_passed_count=0,
        deduplicated_count=0,
        returned_count=0,
        products=[],
        created_at=datetime.now(timezone.utc),
        completed_at=None,
        error=None,
        message=f"Search request accepted for {request.marketplace.value}. Candidate target: {request.candidate_target}, desired results: {request.desired_results}."
    )

    return ResponseModel(
        success=True,
        message="Marketplace search request accepted",
        data=result
    )
