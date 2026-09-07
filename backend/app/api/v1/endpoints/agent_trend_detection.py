from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from backend.app.api.deps import get_current_user
from backend.app.models.domain import (
    User, ProductTrendSummary, TrendSignal, TrendSignalCandidate,
    TrendObservation, AgentTrendDetectionStats, AIAgentMemory, AIAgentMemoryEvent
)
from backend.app.repositories.in_memory import (
    trend_detection_repo, unified_product_repo, taxonomy_repo
)
from backend.app.services.agents.trend_detection.agent import ProductTrendDetectionAgent

router = APIRouter(prefix="/agents/trend-detection", tags=["Agent 4: Trend Detection"])

# Shared Agent 4 instance
trend_agent = ProductTrendDetectionAgent(
    trend_repo=trend_detection_repo,
    unified_repo=unified_product_repo,
    taxonomy_repo=taxonomy_repo
)

class AnalyzeProductTrendRequest(BaseModel):
    new_listing: Optional[Dict[str, Any]] = None
    allow_llm: bool = True

class ResolveCandidateRequest(BaseModel):
    status: str = Field(..., description="'confirmed', 'rejected', or 'auto_promoted'")
    notes: Optional[str] = None

class TrendSignalListResponse(BaseModel):
    items: List[TrendSignal] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50

class TrendCandidateListResponse(BaseModel):
    items: List[TrendSignalCandidate] = Field(default_factory=list)
    total: int = 0

class TrendObservationListResponse(BaseModel):
    unified_product_id: str
    items: List[TrendObservation] = Field(default_factory=list)
    total: int = 0

class TrendMemoryListResponse(BaseModel):
    memories: List[AIAgentMemory] = Field(default_factory=list)
    events: List[AIAgentMemoryEvent] = Field(default_factory=list)


@router.post("/analyze/{unified_product_id}", response_model=ProductTrendSummary)
def analyze_product_trends(
    unified_product_id: str = Path(..., description="Unified Product ID to analyze"),
    payload: Optional[AnalyzeProductTrendRequest] = None,
    current_user: User = Depends(get_current_user)
):
    """Analyzes historical and incoming marketplace metrics for a product to detect trend signals."""
    new_listing = payload.new_listing if payload else None
    allow_llm = payload.allow_llm if payload else True
    summary = trend_agent.analyze_product_trends(
        unified_product_id=unified_product_id,
        new_listing=new_listing,
        allow_llm=allow_llm
    )
    return summary


@router.get("/signals", response_model=TrendSignalListResponse)
def list_trend_signals(
    unified_product_id: Optional[str] = Query(None, description="Filter by product ID"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type"),
    direction: Optional[str] = Query(None, description="Filter by direction (up, down, stable, volatile)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    status: Optional[str] = Query(None, description="Filter by status (active, resolved)"),
    min_strength: Optional[float] = Query(None, description="Filter by minimum signal strength"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user)
):
    """Lists detected market and product trend signals with pagination and filters."""
    offset = (page - 1) * page_size
    signals = trend_agent.list_signals(
        unified_product_id=unified_product_id,
        signal_type=signal_type,
        direction=direction,
        severity=severity,
        status=status,
        min_strength=min_strength,
        limit=page_size,
        offset=offset
    )
    total = trend_detection_repo.count_signals(
        unified_product_id=unified_product_id,
        signal_type=signal_type,
        direction=direction,
        severity=severity,
        status=status
    )
    return TrendSignalListResponse(
        items=signals,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/candidates", response_model=TrendCandidateListResponse)
def list_trend_candidates(
    status: Optional[str] = Query(None, description="Filter by candidate status (e.g. pending_review)"),
    candidate_type: Optional[str] = Query(None, description="Filter by candidate type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Lists breakout and emerging product candidates for review."""
    candidates = trend_agent.list_candidates(
        status=status,
        candidate_type=candidate_type,
        limit=limit,
        offset=offset
    )
    return TrendCandidateListResponse(
        items=candidates,
        total=len(candidates)
    )


@router.post("/candidates/{id}/resolve", response_model=TrendSignalCandidate)
def resolve_trend_candidate(
    id: str = Path(..., description="Candidate ID"),
    payload: ResolveCandidateRequest = ...,
    current_user: User = Depends(get_current_user)
):
    """Resolves a breakout or trend signal candidate with human-in-the-loop audit recording."""
    resolved = trend_agent.resolve_candidate(
        candidate_id=id,
        status=payload.status,
        notes=payload.notes
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return resolved


@router.get("/memory", response_model=TrendMemoryListResponse)
def get_agent_memory(
    memory_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Retrieves Agent 4 persistent learned memory patterns and reinforcement events."""
    memories = trend_agent.memory_manager.list_memories(memory_type=memory_type)
    events = trend_agent.memory_manager.get_events(limit=50)
    return TrendMemoryListResponse(
        memories=memories,
        events=events
    )


@router.get("/stats", response_model=AgentTrendDetectionStats)
def get_agent_stats(
    current_user: User = Depends(get_current_user)
):
    """Returns Agent 4 operational telemetry and signal breakdowns."""
    return trend_agent.get_stats()


@router.get("/{unified_product_id}", response_model=ProductTrendSummary)
def get_product_trend_summary(
    unified_product_id: str = Path(..., description="Unified Product ID"),
    current_user: User = Depends(get_current_user)
):
    """Retrieves the latest trend summary and deterministic score for a product."""
    summary = trend_agent.get_product_trend_summary(unified_product_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Product trend summary not found")
    return summary


@router.get("/{unified_product_id}/history", response_model=TrendObservationListResponse)
def get_product_observations_history(
    unified_product_id: str = Path(..., description="Unified Product ID"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type (price, rating, review_count, availability)"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user)
):
    """Returns raw historical observations recorded for a product across platforms."""
    obs = trend_detection_repo.list_observations(
        unified_product_id=unified_product_id,
        metric_type=metric_type,
        platform=platform,
        limit=limit
    )
    return TrendObservationListResponse(
        unified_product_id=unified_product_id,
        items=obs,
        total=len(obs)
    )
