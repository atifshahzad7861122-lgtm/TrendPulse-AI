from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Path

from backend.app.schemas.common import ResponseModel
from backend.app.models.domain import ScraperMarketplaceHealth
from backend.app.services.scraper.models import (
    StartScraperJobRequest, ScraperJobProgressResponse, ScraperJobListResponse,
    ScraperProductItem, ScraperProductListResponse, RawScrapedDataResponse,
    ScraperProductHistoryResponse
)
from backend.app.services.scraper.service import ScraperService
from backend.app.api.deps import get_scraper_service

router = APIRouter()


@router.post("/jobs/start", response_model=ResponseModel[ScraperJobProgressResponse])
async def start_scraper_job(
    request: StartScraperJobRequest,
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """
    Starts a real-world asynchronous scraping job across Daraz, Amazon, eBay, AliExpress, or Shopify.
    """
    try:
        progress = await scraper_service.start_job(request)
        return ResponseModel(
            success=True,
            message=f"Scraper job {progress.job_id} scheduled for {progress.marketplace}",
            data=progress
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scraper job: {str(e)}")


@router.get("/jobs/{job_id}/status", response_model=ResponseModel[ScraperJobProgressResponse])
def get_scraper_job_status(
    job_id: str = Path(..., description="Crawl Job ID"),
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Returns real-time execution progress, throughput, and error diagnostics for a scraper job."""
    progress = scraper_service.get_job_status(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Scraper job '{job_id}' not found.")
    return ResponseModel(
        success=True,
        message=f"Status for job {job_id}: {progress.status}",
        data=progress
    )


@router.post("/jobs/{job_id}/pause", response_model=ResponseModel[Dict[str, Any]])
def pause_scraper_job(
    job_id: str = Path(..., description="Crawl Job ID"),
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Pauses an active scraper crawl job safely."""
    paused = scraper_service.pause_job(job_id)
    return ResponseModel(
        success=paused,
        message="Pause request sent." if paused else "Job not found or not in running state.",
        data={"job_id": job_id, "paused": paused}
    )


@router.post("/jobs/{job_id}/stop", response_model=ResponseModel[Dict[str, Any]])
def stop_scraper_job(
    job_id: str = Path(..., description="Crawl Job ID"),
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Stops and cancels a running scraper crawl job."""
    stopped = scraper_service.stop_job(job_id)
    return ResponseModel(
        success=stopped,
        message="Stop request processed." if stopped else "Job not found.",
        data={"job_id": job_id, "stopped": stopped}
    )


@router.get("/jobs", response_model=ResponseModel[ScraperJobListResponse])
def list_scraper_jobs(
    marketplace: Optional[str] = Query(None, description="Filter by marketplace"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Returns historical and active scraper crawl jobs."""
    jobs_res = scraper_service.list_jobs(marketplace=marketplace, status=status, limit=limit, offset=offset)
    return ResponseModel(
        success=True,
        message=f"Retrieved {len(jobs_res.jobs)} scraper jobs.",
        data=jobs_res
    )


@router.get("/jobs/{job_id}", response_model=ResponseModel[ScraperJobProgressResponse])
def get_scraper_job_detail(
    job_id: str = Path(..., description="Crawl Job ID"),
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Returns full details and telemetry for a specific crawl job."""
    progress = scraper_service.get_job_status(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Scraper job '{job_id}' not found.")
    return ResponseModel(
        success=True,
        message=f"Retrieved scraper job {job_id}",
        data=progress
    )


@router.get("/marketplaces/health", response_model=ResponseModel[List[ScraperMarketplaceHealth]])
def get_marketplaces_health(
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Returns health, latency, availability, and challenge rates across all supported marketplaces."""
    health_list = scraper_service.get_marketplace_health()
    return ResponseModel(
        success=True,
        message=f"Retrieved health status for {len(health_list)} marketplaces.",
        data=health_list
    )


@router.get("/products", response_model=ResponseModel[ScraperProductListResponse])
def list_scraped_products(
    marketplace: Optional[str] = Query(None, description="Filter by marketplace: daraz, amazon, ebay, aliexpress, shopify"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search keyword in titles"),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    sort_by: str = Query("newest", description="Sort order: newest, price_asc, price_desc, rating"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Returns scraped products with full marketplace provenance, specs, and variants."""
    products_res = scraper_service.list_products(
        marketplace=marketplace,
        category=category,
        search=search,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        page=page,
        limit=limit
    )
    return ResponseModel(
        success=True,
        message=f"Retrieved {len(products_res.products)} scraped products.",
        data=products_res
    )


@router.get("/products/{product_id}", response_model=ResponseModel[ScraperProductItem])
def get_scraped_product(
    product_id: str = Path(..., description="Platform Product ID or Unique ID"),
    marketplace: Optional[str] = Query(None, description="Marketplace identifier"),
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Returns detailed scraped product specifications, variants, and seller data."""
    product = scraper_service.get_product(product_id=product_id, marketplace=marketplace)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found.")
    return ResponseModel(
        success=True,
        message="Product details retrieved successfully.",
        data=product
    )


@router.get("/products/{product_id}/raw", response_model=ResponseModel[RawScrapedDataResponse])
def get_product_raw_payload(
    product_id: str = Path(..., description="Platform Product ID"),
    marketplace: Optional[str] = Query(None, description="Marketplace identifier"),
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Returns the factual raw scraped payload and parser diagnostics without exposing credentials."""
    raw = scraper_service.get_raw_payload(product_id=product_id, marketplace=marketplace)
    if not raw:
        raise HTTPException(status_code=404, detail=f"Raw scraped data for product '{product_id}' not found.")
    return ResponseModel(
        success=True,
        message="Raw scraped data retrieved successfully.",
        data=raw
    )


@router.get("/products/{product_id}/history", response_model=ResponseModel[ScraperProductHistoryResponse])
def get_product_historical_snapshots(
    product_id: str = Path(..., description="Platform Product ID"),
    marketplace: Optional[str] = Query(None, description="Marketplace identifier"),
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """Returns immutable price and stock observation history for a product."""
    history = scraper_service.get_product_history(product_id=product_id, marketplace=marketplace)
    return ResponseModel(
        success=True,
        message=f"Retrieved {history.total_snapshots} historical snapshots.",
        data=history
    )
