"""
Market Intelligence Endpoints (Phase 3).

Exposes unified Market Intelligence API under /api/v1/intelligence/*
Coordinating real marketplace products, historical snapshots, social demand signals,
deterministic scoring engines, and AI analyst reasoning.
Strictly zero synthetic or mocked metrics.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.schemas.common import ResponseModel
from backend.app.models.domain import User
from backend.app.api.deps import (
    get_market_intelligence_service,
    get_current_user_optional
)
from backend.app.services.market_intelligence_service import MarketIntelligenceService
from backend.app.schemas.market_intelligence import (
    MarketOverviewResponse,
    ProductMarketIntelligenceDetail,
    CategoryIntelligenceResponse,
    MarketplacesIntelligenceResponse,
    SocialIntelligenceResponse,
    MarketIntelligenceReportResponse,
    AnalyzeIntelligenceRequest
)

logger = logging.getLogger("trendpulse.api.market_intelligence")
router = APIRouter()


@router.get(
    "/overview",
    response_model=ResponseModel[MarketOverviewResponse],
    summary="Get aggregated market intelligence overview across verified products"
)
def get_market_overview(
    category: Optional[str] = Query(None, description="Filter overview by category"),
    marketplace: Optional[str] = Query(None, description="Filter overview by marketplace (amazon, daraz, ebay, shopify)"),
    keyword: Optional[str] = Query(None, description="Filter overview by search keyword"),
    limit: int = Query(30, ge=1, le=30, description="Max products to analyze (maximum 30)"),
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ResponseModel[MarketOverviewResponse]:
    """
    Computes an executive market overview strictly using real observed products and historical metrics.
    """
    try:
        overview = service.get_market_overview(
            category=category,
            marketplace=marketplace,
            keyword=keyword,
            limit=limit
        )
        return ResponseModel(
            success=True,
            message=f"Market overview generated for {overview.total_products_analyzed} verified products.",
            data=overview
        )
    except Exception as e:
        logger.exception(f"Error generating market overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute market overview: {str(e)}"
        )


@router.get(
    "/products",
    response_model=ResponseModel[List[ProductMarketIntelligenceDetail]],
    summary="List detailed market intelligence across products"
)
def list_products_intelligence(
    category: Optional[str] = Query(None, description="Filter products by category"),
    marketplace: Optional[str] = Query(None, description="Filter products by marketplace"),
    keyword: Optional[str] = Query(None, description="Keyword search in product title"),
    min_market_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum market score filter"),
    min_demand_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum demand score filter"),
    limit: int = Query(30, ge=1, le=30, description="Pagination limit (max 30)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ResponseModel[List[ProductMarketIntelligenceDetail]]:
    """
    Retrieves a list of real marketplace products with full intelligence breakdowns.
    """
    try:
        products = service.list_products_intelligence(
            category=category,
            marketplace=marketplace,
            keyword=keyword,
            min_market_score=min_market_score,
            min_demand_score=min_demand_score,
            limit=limit,
            offset=offset
        )
        return ResponseModel(
            success=True,
            message=f"Retrieved {len(products)} products with market intelligence.",
            data=products
        )
    except Exception as e:
        logger.exception(f"Error listing product intelligence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list product intelligence: {str(e)}"
        )


@router.get(
    "/products/{product_id}",
    response_model=ResponseModel[ProductMarketIntelligenceDetail],
    summary="Get full market intelligence detail for a single product"
)
def get_product_intelligence(
    product_id: str,
    platform: Optional[str] = Query(None, description="Optional platform hint (amazon, daraz, ebay, shopify)"),
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ResponseModel[ProductMarketIntelligenceDetail]:
    """
    Computes complete factual market intelligence for a specific product including
    Market Score (0-100), Demand Intelligence, Trend Velocity, Growth, Viral Potential,
    Opportunity analysis, cross-platform spread, and AI Analyst interpretation.
    """
    detail = service.get_product_intelligence(product_id=product_id, platform=platform)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found in verified marketplace records."
        )
    return ResponseModel(
        success=True,
        message=f"Market intelligence loaded for '{detail.title}'.",
        data=detail
    )


@router.get(
    "/categories",
    response_model=ResponseModel[CategoryIntelligenceResponse],
    summary="Get aggregated category intelligence"
)
def get_category_intelligence(
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ResponseModel[CategoryIntelligenceResponse]:
    """
    Returns aggregated category-level intelligence strictly based on observed products.
    """
    cat_intel = service.get_category_intelligence()
    return ResponseModel(
        success=True,
        message=f"Retrieved intelligence for {cat_intel.total_categories} categories.",
        data=cat_intel
    )


@router.get(
    "/marketplaces",
    response_model=ResponseModel[MarketplacesIntelligenceResponse],
    summary="Get cross-marketplace comparison intelligence"
)
def get_marketplaces_intelligence(
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ResponseModel[MarketplacesIntelligenceResponse]:
    """
    Returns comparative intelligence across Daraz, Amazon, eBay, and Shopify.
    """
    mp_intel = service.get_marketplaces_intelligence()
    return ResponseModel(
        success=True,
        message="Cross-marketplace intelligence retrieved.",
        data=mp_intel
    )


@router.get(
    "/social",
    response_model=ResponseModel[SocialIntelligenceResponse],
    summary="Get real social demand signals and engagement metrics"
)
def get_social_intelligence(
    platform: Optional[str] = Query(None, description="Filter social signals by platform (e.g. YouTube)"),
    product_id: Optional[str] = Query(None, description="Filter social signals matched to a specific product"),
    limit: int = Query(50, ge=1, le=100, description="Max signals to return"),
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ResponseModel[SocialIntelligenceResponse]:
    """
    Returns real social signals and engagement metrics extracted from connected platforms.
    """
    social_intel = service.get_social_intelligence(
        platform=platform,
        product_id=product_id,
        limit=limit
    )
    return ResponseModel(
        success=True,
        message=f"Retrieved {social_intel.total_signals} verified social signals.",
        data=social_intel
    )


@router.get(
    "/reports",
    response_model=ResponseModel[MarketIntelligenceReportResponse],
    summary="Generate or fetch a comprehensive market intelligence report"
)
def get_market_intelligence_report(
    marketplace: Optional[str] = Query("amazon", description="Target marketplace"),
    category: Optional[str] = Query(None, description="Target category"),
    keyword: Optional[str] = Query(None, description="Target keyword query"),
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ResponseModel[MarketIntelligenceReportResponse]:
    """
    Compiles an auditable Market Intelligence Report combining quantitative metrics
    and AI Market Analyst narrative reasoning.
    """
    user_id = current_user.id if current_user else None
    report = service.generate_market_report(
        marketplace=marketplace,
        category=category,
        keyword=keyword,
        user_id=user_id
    )
    return ResponseModel(
        success=True,
        message=f"Market Intelligence Report generated: {report.title}",
        data=report
    )


@router.post(
    "/analyze",
    response_model=ResponseModel[MarketIntelligenceReportResponse],
    summary="Run custom on-demand market intelligence analysis"
)
def analyze_custom_market_intelligence(
    request: AnalyzeIntelligenceRequest,
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ResponseModel[MarketIntelligenceReportResponse]:
    """
    Analyzes specific market slices on demand with full provenance tracking.
    """
    report = service.analyze_custom_intelligence(request)
    return ResponseModel(
        success=True,
        message=f"Analysis report compiled for '{request.keyword or request.category or request.marketplace}'.",
        data=report
    )
