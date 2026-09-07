from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from backend.app.models.domain import (
    User, MarketOpportunity, MarketOpportunityCandidate,
    MarketOpportunityAudit, MarketOpportunitySummary, AgentMarketOpportunityStats,
    AIAgentMemory, AIAgentMemoryEvent
)
from backend.app.api.deps import get_current_user
from backend.app.repositories.in_memory import (
    market_opportunity_repo, unified_product_repo, data_quality_repo,
    taxonomy_repo, trend_detection_repo, anomaly_detection_repo, recommendation_repo
)
from backend.app.services.agents.market_opportunity.agent import MarketOpportunityIntelligenceAgent

router = APIRouter(prefix="/agents/market-opportunities", tags=["market-opportunity-agent"])


def get_market_opportunity_agent() -> MarketOpportunityIntelligenceAgent:
    return MarketOpportunityIntelligenceAgent(
        opp_repo=market_opportunity_repo,
        unified_product_repo=unified_product_repo,
        data_quality_repo=data_quality_repo,
        taxonomy_repo=taxonomy_repo,
        trend_repo=trend_detection_repo,
        anomaly_repo=anomaly_detection_repo,
        recommendation_repo=recommendation_repo
    )


# Request/Response Schemas
class AnalyzeOpportunitiesRequest(BaseModel):
    category: Optional[str] = None
    min_score: float = 50.0
    limit: int = 50


class ResolveOpportunityCandidateRequest(BaseModel):
    status: str = Field(..., description="approved, dismissed, rejected")
    notes: Optional[str] = None


class OpportunityListResponse(BaseModel):
    items: List[MarketOpportunity] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class OpportunityCandidateListResponse(BaseModel):
    items: List[MarketOpportunityCandidate] = Field(default_factory=list)
    total: int = 0


class OpportunityMemoryListResponse(BaseModel):
    memories: List[AIAgentMemory] = Field(default_factory=list)
    events: List[AIAgentMemoryEvent] = Field(default_factory=list)


# 1. Pipeline Run / Discovery Endpoint
@router.post("/analyze", response_model=List[MarketOpportunity])
async def analyze_catalog_opportunities(
    payload: Optional[AnalyzeOpportunitiesRequest] = None,
    current_user: User = Depends(get_current_user),
    agent: MarketOpportunityIntelligenceAgent = Depends(get_market_opportunity_agent)
):
    """
    Triggers catalog-wide market opportunity discovery across unified products.
    """
    req = payload or AnalyzeOpportunitiesRequest()
    return await agent.run_market_opportunity_pipeline(
        category=req.category,
        min_score=req.min_score,
        limit=req.limit
    )


# 2. Product-Specific Opportunity Analysis
@router.post("/product/{unified_product_id}", response_model=MarketOpportunitySummary)
async def analyze_product_opportunities(
    unified_product_id: str = Path(..., description="Unified Product ID"),
    is_complex_strategy: bool = Query(False, description="Whether to trigger selective LLM synthesis"),
    current_user: User = Depends(get_current_user),
    agent: MarketOpportunityIntelligenceAgent = Depends(get_market_opportunity_agent)
):
    """
    Generates and returns comprehensive market opportunity intelligence for a product.
    """
    return await agent.analyze_product_opportunities(
        unified_product_id=unified_product_id,
        is_complex_strategy=is_complex_strategy
    )


# 3. List Opportunities
@router.get("", response_model=OpportunityListResponse)
def list_market_opportunities(
    unified_product_id: Optional[str] = Query(None, description="Filter by unified product ID"),
    opportunity_type: Optional[str] = Query(None, description="Filter by opportunity type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status: Optional[str] = Query("active", description="active, archived, dismissed, all"),
    min_score: Optional[float] = Query(None, description="Minimum opportunity score"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query("score_desc", description="score_desc, score_asc, confidence_desc, oldest"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user)
):
    """
    Lists generated market opportunities with multi-faceted filtering.
    """
    offset = (page - 1) * limit
    items = market_opportunity_repo.list_opportunities(
        unified_product_id=unified_product_id,
        opportunity_type=opportunity_type,
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
    total = market_opportunity_repo.count_opportunities(
        unified_product_id=unified_product_id,
        opportunity_type=opportunity_type,
        category=category,
        brand=brand,
        platform=platform,
        status=status,
        min_score=min_score,
        min_confidence=min_confidence,
        search=search
    )
    return OpportunityListResponse(items=items, total=total, page=page, page_size=limit)


# 4. Candidates Review Queue
@router.get("/candidates", response_model=OpportunityCandidateListResponse)
def list_opportunity_candidates(
    status: Optional[str] = Query("pending", description="pending, approved, dismissed, rejected, all"),
    candidate_type: Optional[str] = Query(None, description="Filter by opportunity type"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user)
):
    """
    Lists opportunity candidates pending operator review.
    """
    items = market_opportunity_repo.list_candidates(
        status=status,
        candidate_type=candidate_type,
        limit=limit
    )
    return OpportunityCandidateListResponse(items=items, total=len(items))


# 5. Resolve Candidate
@router.post("/candidates/{id}/resolve", response_model=MarketOpportunityCandidate)
def resolve_opportunity_candidate(
    id: str = Path(..., description="Candidate ID"),
    payload: ResolveOpportunityCandidateRequest = ...,
    current_user: User = Depends(get_current_user)
):
    """
    Resolves an opportunity candidate (approved, dismissed, rejected).
    """
    resolved = market_opportunity_repo.resolve_candidate(
        candidate_id=id,
        status=payload.status,
        reviewed_by=current_user.id
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return resolved


# 6. Get Opportunity Stats
@router.get("/stats", response_model=AgentMarketOpportunityStats)
def get_market_opportunity_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Returns aggregated KPI statistics for Agent 07.
    """
    return market_opportunity_repo.get_opportunity_stats()


# 7. Get Memory
@router.get("/memory", response_model=OpportunityMemoryListResponse)
def get_opportunity_memories(
    current_user: User = Depends(get_current_user)
):
    """
    Returns Agent 7 persistent learned opportunity rules and audit events.
    """
    mems = market_opportunity_repo.list_memories("agent_market_opportunity_intelligence")
    events = market_opportunity_repo.list_memory_events("agent_market_opportunity_intelligence")
    return OpportunityMemoryListResponse(memories=mems, events=events)


# 8. Get Product Opportunities
@router.get("/product/{unified_product_id}", response_model=List[MarketOpportunity])
def get_opportunities_for_product(
    unified_product_id: str = Path(..., description="Unified Product ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all active market opportunities associated with a specific product.
    """
    return market_opportunity_repo.list_opportunities_for_product(unified_product_id)


# 9. Get Single Opportunity By ID
@router.get("/{id}", response_model=MarketOpportunity)
def get_market_opportunity_by_id(
    id: str = Path(..., description="Opportunity ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a single market opportunity by its ID.
    """
    opp = market_opportunity_repo.get_opportunity(id)
    if not opp:
        raise HTTPException(status_code=404, detail="Market opportunity not found")
    return opp
