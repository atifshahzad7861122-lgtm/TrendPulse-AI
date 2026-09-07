from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from backend.app.api.deps import get_current_user
from backend.app.models.domain import (
    User, ProductRecommendation, RecommendationCandidate, RecommendationInteraction,
    ProductRecommendationSummary, AgentRecommendationStats, AIAgentMemory, AIAgentMemoryEvent
)
from backend.app.repositories.in_memory import (
    recommendation_repo, unified_product_repo, data_quality_repo,
    trend_detection_repo, anomaly_detection_repo
)
from backend.app.services.agents.recommendation.agent import ProductRecommendationAgent

router = APIRouter(prefix="/agents/recommendations", tags=["Agent 6: Recommendation & Product Intelligence"])

# Shared Agent 6 instance
recommendation_agent = ProductRecommendationAgent(
    recommendation_repo=recommendation_repo,
    unified_product_repo=unified_product_repo,
    data_quality_repo=data_quality_repo,
    trend_repo=trend_detection_repo,
    anomaly_repo=anomaly_detection_repo
)


class GenerateCatalogRecommendationsRequest(BaseModel):
    recommendation_type: Optional[str] = None
    category: Optional[str] = None
    min_score: float = Field(default=50.0, ge=0.0, le=100.0)
    limit: int = Field(default=20, ge=1, le=100)


class GenerateProductRecommendationsRequest(BaseModel):
    include_similar: bool = True
    include_alternatives: bool = True
    include_better_price: bool = True
    include_cross_platform: bool = True
    include_best_value: bool = True
    limit_per_type: int = Field(default=5, ge=1, le=20)


class LogRecommendationInteractionRequest(BaseModel):
    recommendation_id: Optional[str] = None
    product_id: str
    interaction_type: str = Field(..., description="'view', 'click', 'save', 'dismiss', 'compare', 'external_link_click'")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResolveRecommendationCandidateRequest(BaseModel):
    status: str = Field(..., description="'approved', 'dismissed', 'rejected'")
    notes: Optional[str] = None


class RecommendationListResponse(BaseModel):
    items: List[ProductRecommendation] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class RecommendationCandidateListResponse(BaseModel):
    items: List[RecommendationCandidate] = Field(default_factory=list)
    total: int = 0


class RecommendationMemoryListResponse(BaseModel):
    memories: List[AIAgentMemory] = Field(default_factory=list)
    events: List[AIAgentMemoryEvent] = Field(default_factory=list)


@router.post("/generate", response_model=List[ProductRecommendation])
async def generate_catalog_recommendations(
    payload: Optional[GenerateCatalogRecommendationsRequest] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Generates evidence-grounded recommendations for the catalog or personalized for the current user.
    """
    req = payload or GenerateCatalogRecommendationsRequest()
    return await recommendation_agent.generate_catalog_recommendations(
        recommendation_type=req.recommendation_type,
        category=req.category,
        user_id=current_user.id,
        min_score=req.min_score,
        limit=req.limit
    )


@router.post("/product/{unified_product_id}", response_model=ProductRecommendationSummary)
async def generate_product_recommendations(
    unified_product_id: str = Path(..., description="Unified product ID"),
    payload: Optional[GenerateProductRecommendationsRequest] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Generates multi-type recommendations (similar, alternatives, better price, cross platform, best value) for a specific product.
    """
    req = payload or GenerateProductRecommendationsRequest()
    return await recommendation_agent.analyze_product_recommendations(
        unified_product_id=unified_product_id,
        user_id=current_user.id,
        include_similar=req.include_similar,
        include_alternatives=req.include_alternatives,
        include_better_price=req.include_better_price,
        include_cross_platform=req.include_cross_platform,
        include_best_value=req.include_best_value,
        limit_per_type=req.limit_per_type
    )


@router.get("", response_model=RecommendationListResponse)
@router.get("/", response_model=RecommendationListResponse)
def list_recommendations(
    unified_product_id: Optional[str] = Query(None),
    recommendation_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query("active"),
    min_score: Optional[float] = Query(None),
    min_confidence: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("score_desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves filterable list of active recommendations.
    """
    offset = (page - 1) * limit
    items = recommendation_repo.list_recommendations(
        unified_product_id=unified_product_id,
        recommendation_type=recommendation_type,
        category=category,
        brand=brand,
        platform=platform,
        status=status,
        min_score=min_score,
        min_confidence=min_confidence,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )
    total = recommendation_repo.count_recommendations(
        unified_product_id=unified_product_id,
        recommendation_type=recommendation_type,
        category=category,
        brand=brand,
        platform=platform,
        status=status,
        min_score=min_score,
        min_confidence=min_confidence,
        search=search
    )
    return RecommendationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=limit
    )


@router.get("/candidates", response_model=RecommendationCandidateListResponse)
def list_recommendation_candidates(
    status: Optional[str] = Query("pending"),
    candidate_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves low-confidence or ambiguous recommendations in the review queue.
    """
    items = recommendation_repo.list_candidates(
        status=status,
        candidate_type=candidate_type,
        limit=limit
    )
    return RecommendationCandidateListResponse(items=items, total=len(items))


@router.post("/candidates/{id}/resolve", response_model=RecommendationCandidate)
def resolve_recommendation_candidate(
    id: str = Path(..., description="Candidate ID"),
    payload: ResolveRecommendationCandidateRequest = ...,
    current_user: User = Depends(get_current_user)
):
    """
    Resolves a recommendation candidate (approve, dismiss, reject).
    """
    resolved = recommendation_repo.resolve_candidate(
        candidate_id=id,
        status=payload.status,
        reviewed_by=current_user.id
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return resolved


@router.post("/interactions", response_model=RecommendationInteraction)
def log_user_interaction(
    payload: LogRecommendationInteractionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Logs real user interaction events (view, click, save, compare).
    """
    interaction = RecommendationInteraction(
        id=f"rint_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{payload.product_id[:8]}",
        user_id=current_user.id,
        workspace_id=current_user.workspace_id,
        recommendation_id=payload.recommendation_id,
        product_id=payload.product_id,
        interaction_type=payload.interaction_type,
        metadata=payload.metadata,
        occurred_at=datetime.now(timezone.utc)
    )
    return recommendation_agent.record_user_interaction(interaction)


@router.get("/product/{unified_product_id}", response_model=List[ProductRecommendation])
def get_recommendations_for_product(
    unified_product_id: str = Path(..., description="Unified product ID"),
    recommendation_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves stored active recommendations for a given product.
    """
    return recommendation_repo.list_recommendations_for_product(
        unified_product_id=unified_product_id,
        recommendation_type=recommendation_type,
        limit=limit
    )


@router.get("/memory", response_model=RecommendationMemoryListResponse)
def get_recommendation_memories(
    current_user: User = Depends(get_current_user)
):
    """
    Returns Agent 6 persistent learned recommendation patterns and audit events.
    """
    mems = recommendation_repo.list_memories("agent_recommendation_engine")
    events = recommendation_repo.list_memory_events("agent_recommendation_engine")
    return RecommendationMemoryListResponse(memories=mems, events=events)


@router.get("/stats", response_model=AgentRecommendationStats)
def get_recommendation_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Returns operational metrics and counts for Agent 6.
    """
    return recommendation_repo.get_recommendation_stats()


@router.get("/{id}", response_model=ProductRecommendation)
def get_recommendation_by_id(
    id: str = Path(..., description="Recommendation ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a single recommendation by its ID.
    """
    rec = recommendation_repo.get_recommendation(id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec
