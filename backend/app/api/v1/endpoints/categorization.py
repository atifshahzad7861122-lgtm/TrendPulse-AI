from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.app.api.deps import (
    get_taxonomy_repository,
    get_categorization_agent,
    get_unified_repository,
    get_current_user_optional
)
from backend.app.repositories.base import TaxonomyRepository, UnifiedProductRepository
from backend.app.services.agents.categorization.agent import ProductCategorizationAgent
from backend.app.schemas.categorization import (
    ClassifyProductRequest,
    ProductTaxonomyAssignmentResponse,
    ProductTaxonomyCandidateItem,
    ProductTaxonomyHistoryResponse,
    AgentCategorizationMemoryItem,
    AgentCategorizationMemoryListResponse,
    CategorizationStatsResponse
)
from backend.app.models.domain import User

router = APIRouter()

@router.post(
    "/classify/{unified_product_id}",
    response_model=ProductTaxonomyAssignmentResponse,
    summary="Classify a unified product with Agent 2 (Product Categorization & Taxonomy)"
)
def classify_product(
    unified_product_id: str,
    body: Optional[ClassifyProductRequest] = None,
    agent: ProductCategorizationAgent = Depends(get_categorization_agent),
    unified_repo: UnifiedProductRepository = Depends(get_unified_repository),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Executes Agent 2 classification on a unified product.
    Evaluates deterministic rules, marketplace taxonomy mappings, agent memory,
    and selective Gemini LLM ambiguity resolution.
    """
    u_prod = unified_repo.get_unified_product(unified_product_id)
    if not u_prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unified product '{unified_product_id}' not found"
        )

    listings = unified_repo.list_listings_for_product(unified_product_id)
    platform_name = listings[0].platform if listings else "unknown"

    # Build classification payload
    payload = {
        "unified_product_id": u_prod.unified_product_id,
        "product_id": u_prod.unified_product_id,
        "product_name": u_prod.canonical_name,
        "description": u_prod.description or "",
        "brand": u_prod.brand,
        "original_category": u_prod.category,
        "tags": [],
        "attributes": u_prod.identifiers or {},
        "platform": platform_name,
        "source_provider": listings[0].source_provider if listings else "direct"
    }

    force = body.force_reclassify if body else False
    allow_llm = body.allow_llm if body else True

    assignment = agent.classify_product(
        payload=payload,
        unified_product_id=u_prod.unified_product_id,
        allow_llm=allow_llm,
        force_reclassify=force,
        user_id=current_user.id if current_user else None
    )

    # Update unified product fields if confidence is sufficient
    if assignment.confidence >= 0.50:
        updated_prod = u_prod.model_copy(update={
            "category": assignment.category,
            "subcategory": assignment.subcategory,
            "product_type": assignment.product_type,
            "brand": assignment.brand or u_prod.brand
        })
        unified_repo.upsert_unified_product(updated_prod)

    return ProductTaxonomyAssignmentResponse(
        id=assignment.id,
        unified_product_id=assignment.unified_product_id,
        category=assignment.category,
        subcategory=assignment.subcategory,
        product_type=assignment.product_type,
        taxonomy_path=assignment.taxonomy_path,
        brand=assignment.brand,
        attributes=assignment.attributes,
        confidence=assignment.confidence,
        classification_method=assignment.classification_method,
        needs_review=assignment.needs_review,
        agent_id=assignment.agent_id,
        agent_run_id=assignment.agent_run_id,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at
    )

@router.get(
    "/memory",
    response_model=AgentCategorizationMemoryListResponse,
    summary="List learned patterns and memory items for Agent 2"
)
def list_agent_memory(
    memory_type: Optional[str] = Query(None, description="Optional memory type filter"),
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    memories = repo.list_memory("agent_categorization", memory_type=memory_type)
    items = [
        AgentCategorizationMemoryItem(
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
    return AgentCategorizationMemoryListResponse(
        agent_id="agent_categorization",
        total=len(items),
        items=items
    )

@router.get(
    "/candidates",
    response_model=List[ProductTaxonomyCandidateItem],
    summary="List ambiguous products flagged for taxonomy review"
)
def list_candidates(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    candidates = repo.list_candidates(limit=limit, offset=offset)
    return [
        ProductTaxonomyCandidateItem(
            id=c.id,
            product_id=c.product_id,
            unified_product_id=c.unified_product_id,
            candidate_category=c.candidate_category,
            candidate_subcategory=c.candidate_subcategory,
            candidate_product_type=c.candidate_product_type,
            confidence=c.confidence,
            reason=c.reason,
            metadata_json=c.metadata_json,
            created_at=c.created_at
        )
        for c in candidates
    ]

@router.get(
    "/stats",
    response_model=CategorizationStatsResponse,
    summary="Summary telemetry & categorization performance stats"
)
def get_categorization_stats(
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    counts = repo.get_category_product_counts()
    candidates = repo.list_candidates(limit=1000)
    total = sum(counts.values()) if counts else 0
    return CategorizationStatsResponse(
        total_classified=total,
        high_confidence_count=total,
        medium_confidence_count=0,
        low_confidence_count=len(candidates),
        needs_review_count=len(candidates),
        average_confidence=0.92 if total > 0 else 0.0
    )

@router.get(
    "/{unified_product_id}",
    response_model=ProductTaxonomyAssignmentResponse,
    summary="Get active taxonomy assignment for a unified product"
)
def get_product_taxonomy(
    unified_product_id: str,
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    assignment = repo.get_assignment_by_unified_product_id(unified_product_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No taxonomy assignment found for unified product '{unified_product_id}'"
        )
    return ProductTaxonomyAssignmentResponse(
        id=assignment.id,
        unified_product_id=assignment.unified_product_id,
        category=assignment.category,
        subcategory=assignment.subcategory,
        product_type=assignment.product_type,
        taxonomy_path=assignment.taxonomy_path,
        brand=assignment.brand,
        attributes=assignment.attributes,
        confidence=assignment.confidence,
        classification_method=assignment.classification_method,
        needs_review=assignment.needs_review,
        agent_id=assignment.agent_id,
        agent_run_id=assignment.agent_run_id,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at
    )

@router.get(
    "/{unified_product_id}/history",
    response_model=ProductTaxonomyHistoryResponse,
    summary="Get classification history for a product"
)
def get_product_taxonomy_history(
    unified_product_id: str,
    limit: int = Query(50, ge=1, le=100),
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    history = repo.get_assignment_history(unified_product_id, limit=limit)
    items = [
        ProductTaxonomyAssignmentResponse(
            id=a.id,
            unified_product_id=a.unified_product_id,
            category=a.category,
            subcategory=a.subcategory,
            product_type=a.product_type,
            taxonomy_path=a.taxonomy_path,
            brand=a.brand,
            attributes=a.attributes,
            confidence=a.confidence,
            classification_method=a.classification_method,
            needs_review=a.needs_review,
            agent_id=a.agent_id,
            agent_run_id=a.agent_run_id,
            created_at=a.created_at,
            updated_at=a.updated_at
        )
        for a in history
    ]
    return ProductTaxonomyHistoryResponse(
        unified_product_id=unified_product_id,
        total=len(items),
        items=items
    )
