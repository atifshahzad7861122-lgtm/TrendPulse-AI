from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from backend.app.schemas.common import ResponseModel
from backend.app.schemas.daraz import (
    DarazSearchResponse, DarazProductDetails, DarazCategoryItem, DarazSellerProductsResponse,
    DarazCallbackResponse, DarazStatusResponse
)
from backend.app.services.daraz_service import DarazService, DarazException, DarazAuthError, DarazRateLimitError
from backend.app.api.deps import get_daraz_service

router = APIRouter()

@router.get("/products/search", response_model=ResponseModel[DarazSearchResponse])
def search_daraz_products(
    query: Optional[str] = Query(None, description="Search keyword for Daraz products"),
    q: Optional[str] = Query(None, description="Alternative alias for search query"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    category: Optional[str] = Query(None, description="Category filter"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0, description="Minimum customer rating (0-5)"),
    min_price: Optional[float] = Query(None, ge=0.0, description="Minimum price in PKR"),
    max_price: Optional[float] = Query(None, ge=0.0, description="Maximum price in PKR"),
    sort_by: Optional[str] = Query(None, description="Sort order: price_asc, price_desc, rating, etc."),
    daraz_service: DarazService = Depends(get_daraz_service)
):
    search_term = query or q or ""
    try:
        results = daraz_service.search_products(
            query=search_term,
            page=page,
            category=category,
            min_rating=min_rating,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by
        )
        return ResponseModel(
            success=True,
            message=f"Retrieved {len(results.products)} products from Daraz Pakistan for '{search_term}'",
            data=results
        )
    except DarazAuthError as auth_err:
        raise HTTPException(status_code=401, detail=auth_err.message)
    except DarazRateLimitError as rate_err:
        raise HTTPException(status_code=429, detail=rate_err.message)
    except DarazException as d_err:
        raise HTTPException(status_code=d_err.status_code, detail=d_err.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error communicating with Daraz API: {str(e)}")

@router.get("/products/{item_id}", response_model=ResponseModel[DarazProductDetails])
def get_daraz_product_details(
    item_id: str = Path(..., description="Daraz Item/Product ID"),
    url: Optional[str] = Query(None, description="Optional canonical Daraz product URL"),
    daraz_service: DarazService = Depends(get_daraz_service)
):
    try:
        details = daraz_service.get_product_details(item_id=item_id, url=url)
        return ResponseModel(
            success=True,
            message="Daraz product details retrieved successfully",
            data=details
        )
    except DarazAuthError as auth_err:
        raise HTTPException(status_code=401, detail=auth_err.message)
    except DarazRateLimitError as rate_err:
        raise HTTPException(status_code=429, detail=rate_err.message)
    except DarazException as d_err:
        raise HTTPException(status_code=d_err.status_code, detail=d_err.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching product details: {str(e)}")

@router.get("/categories", response_model=ResponseModel[List[DarazCategoryItem]])
def get_daraz_categories(
    daraz_service: DarazService = Depends(get_daraz_service)
):
    try:
        categories = daraz_service.get_categories()
        return ResponseModel(
            success=True,
            message=f"Retrieved {len(categories)} Daraz category hierarchies",
            data=categories
        )
    except DarazAuthError as auth_err:
        raise HTTPException(status_code=401, detail=auth_err.message)
    except DarazRateLimitError as rate_err:
        raise HTTPException(status_code=429, detail=rate_err.message)
    except DarazException as d_err:
        raise HTTPException(status_code=d_err.status_code, detail=d_err.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching categories: {str(e)}")

@router.get("/sellers/{seller_id}/products", response_model=ResponseModel[DarazSellerProductsResponse])
def get_daraz_seller_products(
    seller_id: str = Path(..., description="Daraz seller ID or shop slug (e.g. 'rluo1j71')"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    daraz_service: DarazService = Depends(get_daraz_service)
):
    try:
        seller_res = daraz_service.get_seller_products(seller_id=seller_id, page=page)
        return ResponseModel(
            success=True,
            message=f"Retrieved {len(seller_res.products)} products for seller '{seller_id}'",
            data=seller_res
        )
    except DarazAuthError as auth_err:
        raise HTTPException(status_code=401, detail=auth_err.message)
    except DarazRateLimitError as rate_err:
        raise HTTPException(status_code=429, detail=rate_err.message)
    except DarazException as d_err:
        raise HTTPException(status_code=d_err.status_code, detail=d_err.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching seller products: {str(e)}")

# ----------------------------------------------------------------------
# Daraz Official Open Platform Callback & Connection Status
# ----------------------------------------------------------------------

from pydantic import BaseModel

class DarazCallbackPayload(BaseModel):
    code: Optional[str] = None
    state: Optional[str] = None
    account: Optional[str] = None
    seller_id: Optional[str] = None

@router.get("/callback", response_model=ResponseModel[DarazCallbackResponse])
def daraz_oauth_callback_get(
    code: Optional[str] = Query(None, description="Daraz authorization code"),
    state: Optional[str] = Query(None, description="Optional CSRF state parameter"),
    account: Optional[str] = Query(None, description="Optional Daraz account or seller identifier"),
    daraz_service: DarazService = Depends(get_daraz_service)
):
    """
    Handles Daraz Open Platform OAuth authorization callback via HTTP GET.
    Validates the authorization code, completes secure server-side token exchange,
    and returns a clean, sanitized response without exposing secrets or tokens.
    """
    if not code:
        raise HTTPException(
            status_code=400,
            detail="Missing required authorization parameter 'code' in Daraz callback."
        )

    result = daraz_service.exchange_oauth_code(code=code, state=state, account=account)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or result.message)

    return ResponseModel(
        success=True,
        message=result.message,
        data=result
    )

@router.post("/callback", response_model=ResponseModel[DarazCallbackResponse])
def daraz_oauth_callback_post(
    payload: Optional[DarazCallbackPayload] = None,
    code: Optional[str] = Query(None, description="Daraz authorization code in query"),
    state: Optional[str] = Query(None, description="Optional CSRF state in query"),
    account: Optional[str] = Query(None, description="Optional account in query"),
    daraz_service: DarazService = Depends(get_daraz_service)
):
    """
    Handles Daraz Open Platform OAuth authorization callback via HTTP POST.
    Supports either JSON body payload or query parameters.
    """
    auth_code = (payload.code if payload and payload.code else None) or code
    auth_state = (payload.state if payload and payload.state else None) or state
    auth_account = (payload.account if payload and payload.account else None) or (payload.seller_id if payload and payload.seller_id else None) or account

    if not auth_code:
        raise HTTPException(
            status_code=400,
            detail="Missing required authorization parameter 'code' in Daraz callback payload."
        )

    result = daraz_service.exchange_oauth_code(code=auth_code, state=auth_state, account=auth_account)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or result.message)

    return ResponseModel(
        success=True,
        message=result.message,
        data=result
    )

@router.get("/status", response_model=ResponseModel[DarazStatusResponse])
def get_daraz_integration_status(
    daraz_service: DarazService = Depends(get_daraz_service)
):
    """
    Returns high-level health and connection status of the Daraz integration.
    Never exposes App Secret, Access Tokens, or private keys.
    """
    status_data = daraz_service.get_connection_status()
    return ResponseModel(
        success=True,
        message=f"Daraz integration status: {status_data.status}",
        data=status_data
    )

# ----------------------------------------------------------------------
# Large-Scale Ingestion Engine API
# ----------------------------------------------------------------------

from backend.app.services.daraz.ingestion_engine import (
    DarazIngestionEngine, DarazIngestionConfig, IngestionProgressSummary
)
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.models.domain import DarazIngestionRun
from backend.app.api.deps import (
    get_marketplace_product_repository, get_data_quality_repository
)
from backend.app.repositories.base import MarketplaceProductRepository, DataQualityRepository

_engine_instance: Optional[DarazIngestionEngine] = None

def get_ingestion_engine(
    daraz_service: DarazService = Depends(get_daraz_service),
    repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    dq_repo: DataQualityRepository = Depends(get_data_quality_repository)
) -> DarazIngestionEngine:
    global _engine_instance
    if _engine_instance is None:
        official_prov = None
        for p in daraz_service.failover_pool.providers:
            if isinstance(p, DarazOfficialProvider):
                official_prov = p
                break
        if not official_prov:
            official_prov = DarazOfficialProvider(repository=repo)
        _engine_instance = DarazIngestionEngine(
            provider=official_prov,
            repository=repo,
            dq_repository=dq_repo
        )
    return _engine_instance


class StartIngestionPayload(BaseModel):
    target_count: int = 1000
    batch_size: int = 50
    category_id: Optional[str] = None
    search_query: Optional[str] = None
    search_filter: str = "all"
    resume_from_checkpoint: bool = True
    run_id: Optional[str] = None


@router.post("/ingestion/start", response_model=ResponseModel[IngestionProgressSummary])
def start_daraz_ingestion(
    payload: Optional[StartIngestionPayload] = None,
    engine: DarazIngestionEngine = Depends(get_ingestion_engine)
):
    """
    Starts or queues a controlled, resumable Daraz ingestion run.
    """
    params = payload or StartIngestionPayload()
    config = DarazIngestionConfig(
        target_count=params.target_count,
        batch_size=params.batch_size,
        category_id=params.category_id,
        search_query=params.search_query,
        search_filter=params.search_filter
    )
    engine.config = config

    try:
        progress = engine.execute_batch_ingestion(
            run_id=params.run_id,
            target_count=params.target_count,
            resume_from_checkpoint=params.resume_from_checkpoint
        )
        return ResponseModel(
            success=True,
            message=f"Daraz ingestion run {progress.run_id} executed with status: {progress.status}",
            data=progress
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute ingestion run: {str(e)}")


@router.post("/ingestion/pause", response_model=ResponseModel[Dict[str, Any]])
def pause_daraz_ingestion(
    engine: DarazIngestionEngine = Depends(get_ingestion_engine)
):
    """Pauses the active Daraz ingestion run at the next checkpoint."""
    paused = engine.pause()
    return ResponseModel(
        success=paused,
        message="Pause request sent to active ingestion run." if paused else "No active ingestion run to pause.",
        data={"paused": paused}
    )


@router.post("/ingestion/stop", response_model=ResponseModel[Dict[str, Any]])
def stop_daraz_ingestion(
    engine: DarazIngestionEngine = Depends(get_ingestion_engine)
):
    """Stops the active Daraz ingestion run safely at the next checkpoint."""
    stopped = engine.stop()
    return ResponseModel(
        success=stopped,
        message="Stop request sent to active ingestion run." if stopped else "No active ingestion run to stop.",
        data={"stopped": stopped}
    )


@router.get("/ingestion/status", response_model=ResponseModel[Optional[IngestionProgressSummary]])
def get_ingestion_status(
    run_id: Optional[str] = Query(None, description="Optional Ingestion Run ID to look up"),
    engine: DarazIngestionEngine = Depends(get_ingestion_engine)
):
    """Returns real-time progress, checkpoint, throughput, and error diagnostics."""
    status = engine.get_status(run_id=run_id)
    return ResponseModel(
        success=True,
        message="Ingestion status retrieved successfully." if status else "No active or recorded ingestion status found.",
        data=status
    )


@router.get("/ingestion/history", response_model=ResponseModel[List[DarazIngestionRun]])
def get_ingestion_history(
    limit: int = Query(20, ge=1, le=100),
    engine: DarazIngestionEngine = Depends(get_ingestion_engine)
):
    """Returns past ingestion run records with historical progress and metrics."""
    history = engine.list_history(limit=limit)
    return ResponseModel(
        success=True,
        message=f"Retrieved {len(history)} past ingestion runs.",
        data=history
    )


