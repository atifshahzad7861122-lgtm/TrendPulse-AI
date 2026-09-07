from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from backend.app.schemas.common import ResponseModel
from backend.app.schemas.shopify import (
    ShopifyProductItem,
    ShopifyProductListResponse,
    ShopifySyncRequest,
    ShopifySyncResponse,
    ShopifyStatusResponse
)
from backend.app.services.shopify.service import ShopifyService
from backend.app.api.deps import get_shopify_service, get_current_user
from backend.app.models.domain import User

router = APIRouter()

@router.get("/products", response_model=ResponseModel[ShopifyProductListResponse])
def list_shopify_products(
    store_domain: Optional[str] = Query(None, description="Shopify store domain filter (e.g. gymshark.com)"),
    category: Optional[str] = Query(None, description="Category / product_type filter"),
    search: Optional[str] = Query(None, description="Search keyword in title, vendor, tags"),
    sort_by: Optional[str] = Query("synced", description="Sort order: synced, price_asc, price_desc, rating"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=250, description="Items per page"),
    shopify_service: ShopifyService = Depends(get_shopify_service),
    current_user: User = Depends(get_current_user)
):
    try:
        response = shopify_service.list_products(
            store_domain=store_domain,
            category=category,
            search=search,
            sort_by=sort_by,
            page=page,
            limit=limit
        )
        return ResponseModel(
            success=True,
            message="Shopify products retrieved successfully",
            data=response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Shopify products: {str(e)}")

@router.get("/products/{product_id}", response_model=ResponseModel[ShopifyProductItem])
def get_shopify_product_detail(
    product_id: str = Path(..., description="Shopify product ID or internal ID"),
    shopify_service: ShopifyService = Depends(get_shopify_service),
    current_user: User = Depends(get_current_user)
):
    prod = shopify_service.get_product(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Shopify product not found")
    return ResponseModel(
        success=True,
        message="Shopify product details retrieved successfully",
        data=prod
    )

@router.post("/sync", response_model=ResponseModel[ShopifySyncResponse])
def sync_shopify_store(
    payload: ShopifySyncRequest,
    shopify_service: ShopifyService = Depends(get_shopify_service),
    current_user: User = Depends(get_current_user)
):
    if not payload.store_domain or not payload.store_domain.strip():
        raise HTTPException(status_code=400, detail="Store domain is required")

    try:
        sync_result = shopify_service.sync_store(
            store_domain=payload.store_domain,
            limit=payload.limit,
            page=payload.page,
            collection=payload.collection,
            force_live=payload.force_live
        )
        return ResponseModel(
            success=sync_result.success,
            message=sync_result.message,
            data=sync_result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shopify synchronization failed: {str(e)}")

@router.get("/status", response_model=ResponseModel[ShopifyStatusResponse])
def get_shopify_platform_status(
    shopify_service: ShopifyService = Depends(get_shopify_service),
    current_user: User = Depends(get_current_user)
):
    try:
        status_data = shopify_service.get_status()
        return ResponseModel(
            success=True,
            message="Shopify platform status retrieved successfully",
            data=status_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Shopify platform status: {str(e)}")
