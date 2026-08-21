from typing import List
from fastapi import APIRouter, Depends, HTTPException
from backend.app.models.domain import Product, User
from backend.app.services.watchlist_service import WatchlistService
from backend.app.api.deps import get_watchlist_service, get_current_user
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[List[Product]])
def get_watchlist(
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user)
):
    results = watchlist_service.get_watchlist(current_user.id)
    return ResponseModel(
        success=True,
        message="Watchlist retrieved successfully",
        data=results
    )

@router.post("/{product_id}", response_model=ResponseModel[dict])
def add_to_watchlist(
    product_id: str,
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user)
):
    success = watchlist_service.add_to_watchlist(current_user.id, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found or already added")
    
    return ResponseModel(
        success=True,
        message="Product added to watchlist",
        data={"product_id": product_id, "is_watchlisted": True}
    )

@router.delete("/{product_id}", response_model=ResponseModel[dict])
def remove_from_watchlist(
    product_id: str,
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user)
):
    watchlist_service.remove_from_watchlist(current_user.id, product_id)
    return ResponseModel(
        success=True,
        message="Product removed from watchlist",
        data={"product_id": product_id, "is_watchlisted": False}
    )
