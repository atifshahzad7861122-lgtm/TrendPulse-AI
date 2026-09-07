from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.app.schemas.common import ResponseModel
from backend.app.schemas.intelligence import (
    UnifiedProductListResponse, UnifiedProductDetailResponse,
    UnifiedProductHistoryResponse, UnifiedSearchResponse, PlatformListingItem
)
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
from backend.app.api.deps import get_unified_intelligence_service

router = APIRouter()

@router.get("", response_model=ResponseModel[UnifiedProductListResponse])
@router.get("/", response_model=ResponseModel[UnifiedProductListResponse], include_in_schema=False)
def list_unified_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    platform: Optional[str] = Query(None, description="Filter by platform (e.g. Daraz, Shopify)"),
    search: Optional[str] = Query(None, description="Search product titles, brands, or identifiers"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    available: Optional[bool] = Query(None, description="Filter by availability"),
    min_rating: Optional[float] = Query(None, description="Minimum rating filter"),
    sort_by: Optional[str] = Query("synced", description="Sort by (synced, name_asc, name_desc, oldest)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    service: UnifiedProductIntelligenceService = Depends(get_unified_intelligence_service)
):
    """Lists canonical unified products across Daraz, Shopify, and future platforms with multi-attribute filtering."""
    data = service.list_products(
        category=category,
        brand=brand,
        platform=platform,
        search=search,
        min_price=min_price,
        max_price=max_price,
        available=available,
        min_rating=min_rating,
        sort_by=sort_by,
        page=page,
        limit=limit
    )
    return ResponseModel(
        success=True,
        message=f"Retrieved {len(data.items)} unified products (Total: {data.total}).",
        data=data
    )

@router.get("/search", response_model=ResponseModel[UnifiedSearchResponse])
def search_unified_products(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    service: UnifiedProductIntelligenceService = Depends(get_unified_intelligence_service)
):
    """Searches canonical unified products across all connected marketplace sources."""
    data = service.search(query=q, page=page, limit=limit)
    return ResponseModel(
        success=True,
        message=f"Found {data.total_matches} matches for '{q}'.",
        data=data
    )

@router.get("/{unified_product_id}", response_model=ResponseModel[UnifiedProductDetailResponse])
def get_unified_product_detail(
    unified_product_id: str,
    service: UnifiedProductIntelligenceService = Depends(get_unified_intelligence_service)
):
    """Retrieves full details for a unified product including cross-platform listings and price comparison."""
    detail = service.get_product_detail(unified_product_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unified product '{unified_product_id}' not found."
        )
    return ResponseModel(
        success=True,
        message="Unified product details retrieved successfully.",
        data=detail
    )

@router.get("/{unified_product_id}/platforms", response_model=ResponseModel[List[PlatformListingItem]])
def get_unified_product_platforms(
    unified_product_id: str,
    service: UnifiedProductIntelligenceService = Depends(get_unified_intelligence_service)
):
    """Retrieves all connected platform listings for a unified product."""
    detail = service.get_product_detail(unified_product_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unified product '{unified_product_id}' not found."
        )
    return ResponseModel(
        success=True,
        message=f"Retrieved {len(detail.platform_listings)} platform listings.",
        data=detail.platform_listings
    )

@router.get("/{unified_product_id}/history", response_model=ResponseModel[UnifiedProductHistoryResponse])
def get_unified_product_history(
    unified_product_id: str,
    service: UnifiedProductIntelligenceService = Depends(get_unified_intelligence_service)
):
    """Retrieves real historical observations (price, availability, rating) across linked platforms."""
    history = service.get_product_history(unified_product_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unified product '{unified_product_id}' not found."
        )
    return ResponseModel(
        success=True,
        message=f"Retrieved {history.total_observations} historical observations across {len(history.platforms)} platforms.",
        data=history
    )
