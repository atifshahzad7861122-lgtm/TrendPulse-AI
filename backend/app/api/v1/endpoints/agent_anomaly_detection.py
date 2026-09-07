from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from backend.app.api.deps import get_current_user
from backend.app.models.domain import (
    User, ProductAnomalySummary, AnomalyDetection, AnomalyCandidate,
    AnomalyObservation, AgentAnomalyDetectionStats, AIAgentMemory, AIAgentMemoryEvent
)
from backend.app.repositories.in_memory import (
    anomaly_detection_repo, unified_product_repo, data_quality_repo
)
from backend.app.services.agents.anomaly_detection.agent import ProductAnomalyDetectionAgent

router = APIRouter(prefix="/agents/anomaly-detection", tags=["Agent 5: Anomaly Detection"])

# Shared Agent 5 instance
anomaly_agent = ProductAnomalyDetectionAgent(
    anomaly_repo=anomaly_detection_repo,
    unified_product_repo=unified_product_repo,
    data_quality_repo=data_quality_repo
)

class AnalyzeProductAnomalyRequest(BaseModel):
    new_listing: Optional[Dict[str, Any]] = None
    provider_data: Optional[Dict[str, Any]] = None

class ResolveAnomalyCandidateRequest(BaseModel):
    status: str = Field(..., description="'confirmed', 'dismissed', 'false_positive', or 'resolved'")
    notes: Optional[str] = None

class AnomalyListResponse(BaseModel):
    items: List[AnomalyDetection] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50

class AnomalyCandidateListResponse(BaseModel):
    items: List[AnomalyCandidate] = Field(default_factory=list)
    total: int = 0

class AnomalyObservationListResponse(BaseModel):
    unified_product_id: str
    items: List[AnomalyObservation] = Field(default_factory=list)
    total: int = 0

class AnomalyMemoryListResponse(BaseModel):
    memories: List[AIAgentMemory] = Field(default_factory=list)
    events: List[AIAgentMemoryEvent] = Field(default_factory=list)


@router.post("/analyze/{unified_product_id}", response_model=ProductAnomalySummary)
async def analyze_product_anomaly(
    unified_product_id: str = Path(..., description="Canonical unified product ID"),
    payload: Optional[AnalyzeProductAnomalyRequest] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Analyzes historical and current observations for a product to detect statistical anomalies.
    """
    try:
        listings = [payload.new_listing] if payload and payload.new_listing else None
        prov_data = payload.provider_data if payload else None
        summary = await anomaly_agent.analyze_product_anomalies(
            unified_product_id=unified_product_id,
            incoming_listings=listings,
            provider_data=prov_data
        )
        return summary
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Anomaly detection analysis failed: {str(err)}")


@router.get("/signals", response_model=AnomalyListResponse)
def list_anomaly_signals(
    unified_product_id: Optional[str] = Query(None, description="Filter by product ID"),
    anomaly_type: Optional[str] = Query(None, description="Filter by anomaly type"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    status: Optional[str] = Query("active", description="Filter by status: active, resolved, false_positive, all"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    min_score: Optional[float] = Query(None, description="Minimum anomaly score"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user)
):
    """
    Returns filterable, paginated anomaly detections across the catalog.
    """
    offset = (page - 1) * page_size
    items = anomaly_detection_repo.list_anomalies(
        unified_product_id=unified_product_id,
        anomaly_type=anomaly_type,
        severity=severity,
        status=status,
        platform=platform,
        min_score=min_score,
        limit=page_size,
        offset=offset
    )
    total = anomaly_detection_repo.count_anomalies(
        unified_product_id=unified_product_id,
        anomaly_type=anomaly_type,
        severity=severity,
        status=status,
        platform=platform
    )
    return AnomalyListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/candidates", response_model=AnomalyCandidateListResponse)
def list_anomaly_candidates(
    status: Optional[str] = Query("pending_review", description="pending_review, confirmed, dismissed, false_positive, all"),
    candidate_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Lists anomaly candidates in human-in-the-loop review queue.
    """
    items = anomaly_detection_repo.list_candidates(status=status, candidate_type=candidate_type)
    return AnomalyCandidateListResponse(items=items, total=len(items))


@router.post("/candidates/{candidate_id}/resolve", response_model=AnomalyCandidate)
def resolve_anomaly_candidate(
    candidate_id: str = Path(...),
    payload: ResolveAnomalyCandidateRequest = ...,
    current_user: User = Depends(get_current_user)
):
    """
    Resolves an anomaly candidate (confirm, dismiss, mark false positive).
    """
    resolved = anomaly_agent.resolve_candidate_review(
        candidate_id=candidate_id,
        status=payload.status,
        notes=payload.notes
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return resolved


@router.get("/stats", response_model=AgentAnomalyDetectionStats)
def get_anomaly_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Returns telemetry stats for Agent 5: Anomaly Detection.
    """
    return anomaly_detection_repo.get_anomaly_stats()


@router.get("/memory", response_model=AnomalyMemoryListResponse)
def get_anomaly_agent_memory(
    current_user: User = Depends(get_current_user)
):
    """
    Inspects learned patterns and memory events for Agent 5.
    """
    memories = []
    events = []
    if data_quality_repo:
        all_mems = data_quality_repo.list_memories(agent_id=ProductAnomalyDetectionAgent.AGENT_ID)
        memories = all_mems
        for m in all_mems:
            evts = data_quality_repo.list_memory_events(agent_id=ProductAnomalyDetectionAgent.AGENT_ID, memory_id=m.id)
            events.extend(evts)
    return AnomalyMemoryListResponse(memories=memories, events=events)


@router.get("/{unified_product_id}/history", response_model=AnomalyObservationListResponse)
def get_product_anomaly_history(
    unified_product_id: str = Path(..., description="Unified product ID"),
    metric_type: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user)
):
    """
    Returns chronological raw metric observation history for a product.
    """
    items = anomaly_detection_repo.list_observations(
        unified_product_id=unified_product_id,
        metric_type=metric_type,
        platform=platform,
        limit=limit
    )
    return AnomalyObservationListResponse(
        unified_product_id=unified_product_id,
        items=items,
        total=len(items)
    )


@router.get("/{unified_product_id}", response_model=ProductAnomalySummary)
async def get_product_anomaly_summary(
    unified_product_id: str = Path(..., description="Unified product ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the latest grounded anomaly summary for a product without injecting new observations.
    """
    return await anomaly_agent.analyze_product_anomalies(unified_product_id=unified_product_id)
