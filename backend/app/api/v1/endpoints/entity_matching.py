from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import (
    get_entity_matching_agent,
    get_unified_repository,
    get_taxonomy_repository,
    get_current_user_optional
)
from backend.app.repositories.base import UnifiedProductRepository, TaxonomyRepository
from backend.app.services.agents.entity_matching.agent import ProductEntityMatchingAgent
from backend.app.schemas.entity_matching import (
    MatchProductRequest,
    CompareProductsRequest,
    ProductMatchDecisionResponse,
    ProductMatchHistoryResponse,
    ProductMatchCandidateResponse,
    ResolveCandidateRequest,
    EntityMatchingMemoryItem,
    EntityMatchingMemoryListResponse,
    EntityMatchingStatsResponse
)
from backend.app.models.domain import User

router = APIRouter()

@router.post(
    "/match",
    response_model=ProductMatchDecisionResponse,
    summary="Match and resolve product entity across multi-platform catalog"
)
def match_product_entity(
    body: MatchProductRequest,
    agent: ProductEntityMatchingAgent = Depends(get_entity_matching_agent),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Executes Agent 3 (Product Entity Matching & Deduplication) on an incoming product payload.
    Evaluates 7 matching tiers, candidate blocking, variant detection, and selective Gemini reasoning.
    """
    payload = body.model_dump(exclude_none=True)
    decision, unified_prod = agent.match_listing(
        payload=payload,
        allow_llm=body.allow_llm,
        force_rematch=body.force_rematch,
        user_id=current_user.id if current_user else None
    )

    return ProductMatchDecisionResponse(
        id=decision.id,
        product_a_id=decision.product_a_id,
        product_b_id=decision.product_b_id,
        unified_product_id=decision.unified_product_id,
        platform_a=decision.platform_a,
        platform_b=decision.platform_b,
        decision=decision.decision,
        confidence=decision.confidence,
        match_method=decision.match_method,
        reasons=decision.reasons,
        conflicts=decision.conflicts,
        variant_attributes=decision.variant_attributes,
        base_product_id=decision.base_product_id,
        llm_used=decision.llm_used,
        llm_provider=decision.llm_provider,
        llm_model=decision.llm_model,
        agent_id=decision.agent_id,
        agent_run_id=decision.agent_run_id,
        created_at=decision.created_at,
        updated_at=decision.updated_at
    )

@router.post(
    "/compare",
    response_model=ProductMatchDecisionResponse,
    summary="Directly compare two products for entity match or variant"
)
def compare_products(
    body: CompareProductsRequest,
    agent: ProductEntityMatchingAgent = Depends(get_entity_matching_agent)
):
    """
    Direct pairwise comparison between Product A and Product B.
    """
    decision = agent.compare_products(
        product_a=body.product_a,
        product_b=body.product_b,
        allow_llm=body.allow_llm
    )
    return ProductMatchDecisionResponse(
        id=decision.id,
        product_a_id=decision.product_a_id,
        product_b_id=decision.product_b_id,
        unified_product_id=decision.unified_product_id,
        platform_a=decision.platform_a,
        platform_b=decision.platform_b,
        decision=decision.decision,
        confidence=decision.confidence,
        match_method=decision.match_method,
        reasons=decision.reasons,
        conflicts=decision.conflicts,
        variant_attributes=decision.variant_attributes,
        base_product_id=decision.base_product_id,
        llm_used=decision.llm_used,
        llm_provider=decision.llm_provider,
        llm_model=decision.llm_model,
        agent_id=decision.agent_id,
        agent_run_id=decision.agent_run_id,
        created_at=decision.created_at,
        updated_at=decision.updated_at
    )

@router.get(
    "/candidates",
    response_model=List[ProductMatchCandidateResponse],
    summary="List ambiguous match candidates in Review Queue (confidence 0.75-0.84)"
)
def list_review_candidates(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status ('needs_review', 'probable', 'confirmed_match', 'rejected')"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: UnifiedProductRepository = Depends(get_unified_repository)
):
    candidates = repo.list_match_candidates(status=status_filter, limit=limit, offset=offset)
    return [
        ProductMatchCandidateResponse(
            id=c.id,
            unified_product_id=c.unified_product_id,
            candidate_unified_id=c.candidate_unified_id,
            platform=c.platform,
            platform_product_id=c.platform_product_id,
            confidence_score=c.confidence_score,
            method=c.method,
            status=c.status,
            reasons=c.reasons,
            product_a_title=getattr(c, "product_a_title", None),
            product_b_title=getattr(c, "product_b_title", None),
            conflicts=getattr(c, "conflicts", []),
            variant_attributes=getattr(c, "variant_attributes", {}),
            created_at=c.created_at
        )
        for c in candidates
    ]

@router.post(
    "/candidates/{candidate_id}/resolve",
    response_model=ProductMatchCandidateResponse,
    summary="Resolve a review candidate and record confirmed pattern into Agent 3 memory"
)
def resolve_candidate(
    candidate_id: str,
    body: ResolveCandidateRequest,
    agent: ProductEntityMatchingAgent = Depends(get_entity_matching_agent),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    resolved = agent.resolve_review_candidate(
        candidate_id=candidate_id,
        action=body.action,
        variant_attributes=body.variant_attributes,
        notes=body.notes or "",
        user_id=current_user.id if current_user else None
    )
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match candidate '{candidate_id}' not found"
        )
    return ProductMatchCandidateResponse(
        id=resolved.id,
        unified_product_id=resolved.unified_product_id,
        candidate_unified_id=resolved.candidate_unified_id,
        platform=resolved.platform,
        platform_product_id=resolved.platform_product_id,
        confidence_score=resolved.confidence_score,
        method=resolved.method,
        status=resolved.status,
        reasons=resolved.reasons,
        product_a_title=getattr(resolved, "product_a_title", None),
        product_b_title=getattr(resolved, "product_b_title", None),
        conflicts=getattr(resolved, "conflicts", []),
        variant_attributes=getattr(resolved, "variant_attributes", {}),
        created_at=resolved.created_at
    )

@router.get(
    "/memory",
    response_model=EntityMatchingMemoryListResponse,
    summary="List learned matching patterns and verified memory items for Agent 3"
)
def list_matching_memory(
    memory_type: Optional[str] = Query(None, description="Optional memory type filter"),
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    memories = repo.list_memory("agent_entity_matching", memory_type=memory_type)
    items = [
        EntityMatchingMemoryItem(
            id=m.id,
            agent_id=m.agent_id,
            memory_type=m.memory_type,
            memory_key=m.memory_key,
            memory_value=m.memory_value,
            confidence_score=m.confidence_score,
            occurrence_count=m.occurrence_count,
            last_observed_at=m.last_observed_at,
            created_at=m.created_at,
            updated_at=m.updated_at
        )
        for m in memories
    ]
    return EntityMatchingMemoryListResponse(
        agent_id="agent_entity_matching",
        total=len(items),
        items=items
    )

@router.get(
    "/stats",
    response_model=EntityMatchingStatsResponse,
    summary="Summary telemetry & matching performance metrics"
)
def get_matching_stats(
    agent: ProductEntityMatchingAgent = Depends(get_entity_matching_agent)
):
    stats = agent.get_stats()
    return EntityMatchingStatsResponse(**stats)

@router.get(
    "/{product_id}",
    response_model=List[ProductMatchDecisionResponse],
    summary="Get active match decisions for a product"
)
def get_product_matches(
    product_id: str,
    repo: UnifiedProductRepository = Depends(get_unified_repository)
):
    decisions = repo.list_match_decisions(product_id=product_id, limit=20)
    return [
        ProductMatchDecisionResponse(
            id=d.id,
            product_a_id=d.product_a_id,
            product_b_id=d.product_b_id,
            unified_product_id=d.unified_product_id,
            platform_a=d.platform_a,
            platform_b=d.platform_b,
            decision=d.decision,
            confidence=d.confidence,
            match_method=d.match_method,
            reasons=d.reasons,
            conflicts=d.conflicts,
            variant_attributes=d.variant_attributes,
            base_product_id=d.base_product_id,
            llm_used=d.llm_used,
            llm_provider=d.llm_provider,
            llm_model=d.llm_model,
            agent_id=d.agent_id,
            agent_run_id=d.agent_run_id,
            created_at=d.created_at,
            updated_at=d.updated_at
        )
        for d in decisions
    ]

@router.get(
    "/{product_id}/history",
    response_model=ProductMatchHistoryResponse,
    summary="Get match decision audit history for a product"
)
def get_product_match_history(
    product_id: str,
    limit: int = Query(50, ge=1, le=100),
    repo: UnifiedProductRepository = Depends(get_unified_repository)
):
    decisions = repo.list_match_decisions(product_id=product_id, limit=limit)
    items = [
        ProductMatchDecisionResponse(
            id=d.id,
            product_a_id=d.product_a_id,
            product_b_id=d.product_b_id,
            unified_product_id=d.unified_product_id,
            platform_a=d.platform_a,
            platform_b=d.platform_b,
            decision=d.decision,
            confidence=d.confidence,
            match_method=d.match_method,
            reasons=d.reasons,
            conflicts=d.conflicts,
            variant_attributes=d.variant_attributes,
            base_product_id=d.base_product_id,
            llm_used=d.llm_used,
            llm_provider=d.llm_provider,
            llm_model=d.llm_model,
            agent_id=d.agent_id,
            agent_run_id=d.agent_run_id,
            created_at=d.created_at,
            updated_at=d.updated_at
        )
        for d in decisions
    ]
    return ProductMatchHistoryResponse(
        product_id=product_id,
        total=len(items),
        items=items
    )
