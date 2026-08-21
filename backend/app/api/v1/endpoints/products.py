from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.models.domain import Product, User
from backend.app.services.intelligence import ProductIntelligenceEngine
from backend.app.services.watchlist_service import WatchlistService
from backend.app.api.deps import (
    get_product_intelligence_engine, get_watchlist_service, get_current_user
)
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[List[Product]])
def list_products(
    category: Optional[str] = "all",
    platform: Optional[str] = "all",
    search: Optional[str] = None,
    sort_by: Optional[str] = "trend_score",
    intelligence: ProductIntelligenceEngine = Depends(get_product_intelligence_engine),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user)
):
    items = intelligence.list_products(category=category, platform=platform, search=search, sort_by=sort_by)
    
    # Sync is_watchlisted flag
    for p in items:
        p.is_watchlisted = watchlist_service.is_watched(current_user.id, p.id)
    
    return ResponseModel(
        success=True,
        message="Products retrieved successfully",
        data=items
    )

@router.get("/compare", response_model=ResponseModel[List[Product]])
def compare_products(
    ids: str = Query(..., description="Comma-separated product IDs e.g. prod_01,prod_02"),
    intelligence: ProductIntelligenceEngine = Depends(get_product_intelligence_engine),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user)
):
    product_ids = [i.strip() for i in ids.split(",") if i.strip()]
    if not product_ids:
        raise HTTPException(status_code=400, detail="Please provide at least one product ID to compare")
    
    results = intelligence.compare_products(product_ids)
    for p in results:
        p.is_watchlisted = watchlist_service.is_watched(current_user.id, p.id)
            
    return ResponseModel(
        success=True,
        message="Product comparison data retrieved",
        data=results
    )

@router.get("/{product_id}", response_model=ResponseModel[Product])
def get_product_detail(
    product_id: str,
    intelligence: ProductIntelligenceEngine = Depends(get_product_intelligence_engine),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user)
):
    p = intelligence.get_product_intelligence(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    
    p.is_watchlisted = watchlist_service.is_watched(current_user.id, p.id)
    return ResponseModel(
        success=True,
        message="Product detail retrieved",
        data=p
    )
