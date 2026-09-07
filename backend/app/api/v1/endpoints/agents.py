from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import (
    get_current_user_optional, get_current_user, get_data_quality_agent, get_data_quality_repository
)
from backend.app.models.domain import User, AIAgentRun, AIAgentMemory, AIAgentMemoryEvent
from backend.app.repositories.base import DataQualityRepository
from backend.app.services.agents.data_quality import DataQualityAgent
from backend.app.schemas.data_quality import (
    DataQualityValidationRequest, DataQualityValidationResponse,
    DataQualityBatchValidationRequest, DataQualityBatchValidationResponse,
    DataQualityStatusResponse, DataQualityMemoryItemResponse,
    DataQualityMemoryListResponse, DataQualityRunHistoryResponse,
    DataQualityValidationListResponse
)

router = APIRouter()

@router.post(
    "/data-quality/validate",
    response_model=DataQualityValidationResponse,
    summary="Validate Single Product Record",
    description="Deterministically validates a single incoming product payload with optional selective Gemini ambiguity resolution."
)
def validate_product(
    req: DataQualityValidationRequest,
    agent: DataQualityAgent = Depends(get_data_quality_agent),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    workspace_id = req.workspace_id or (current_user.workspace_id if current_user else None)
    res = agent.validate_product(
        payload=req.product_payload,
        platform=req.platform,
        source_provider=req.source_provider,
        allow_llm=req.allow_llm,
        workspace_id=workspace_id,
        save_result=True
    )
    return DataQualityValidationResponse(
        id=res.id,
        platform=res.platform,
        source_provider=res.source_provider,
        platform_product_id=res.platform_product_id,
        unified_product_id=res.unified_product_id,
        product_title=res.product_title,
        overall_score=res.overall_score,
        classification=res.classification,
        is_trusted=res.is_trusted,
        issues=res.issues,
        warnings=res.warnings,
        field_scores=res.field_scores,
        used_llm=res.used_llm,
        llm_resolution=res.llm_resolution,
        validated_at=res.validated_at,
        run_id=res.run_id
    )

@router.post(
    "/data-quality/validate-batch",
    response_model=DataQualityBatchValidationResponse,
    summary="Validate Batch of Products",
    description="Validates a list of products within an audited AIAgentRun, updating memory and returning aggregate stats."
)
def validate_batch(
    req: DataQualityBatchValidationRequest,
    agent: DataQualityAgent = Depends(get_data_quality_agent),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    workspace_id = req.workspace_id or (current_user.workspace_id if current_user else None)
    run, results = agent.validate_batch(
        products=req.products,
        platform=req.platform,
        source_provider=req.source_provider,
        allow_llm=req.allow_llm,
        workspace_id=workspace_id,
        trigger_source="api_batch"
    )

    formatted_results = [
        DataQualityValidationResponse(
            id=res.id,
            platform=res.platform,
            source_provider=res.source_provider,
            platform_product_id=res.platform_product_id,
            unified_product_id=res.unified_product_id,
            product_title=res.product_title,
            overall_score=res.overall_score,
            classification=res.classification,
            is_trusted=res.is_trusted,
            issues=res.issues,
            warnings=res.warnings,
            field_scores=res.field_scores,
            used_llm=res.used_llm,
            llm_resolution=res.llm_resolution,
            validated_at=res.validated_at,
            run_id=res.run_id
        )
        for res in results
    ]

    return DataQualityBatchValidationResponse(
        run_id=run.id,
        total_processed=run.items_processed,
        valid_count=run.items_valid,
        warning_count=run.items_warning,
        needs_review_count=run.items_needs_review,
        rejected_count=run.items_rejected,
        avg_quality_score=run.avg_quality_score,
        gemini_calls_count=run.gemini_calls_count,
        execution_time_ms=run.execution_time_ms,
        results=formatted_results
    )

@router.get(
    "/data-quality/status",
    response_model=DataQualityStatusResponse,
    summary="Agent Health & Status",
    description="Returns agent status, capabilities, aggregate quality metrics, and provider reliability profiles."
)
def get_status(
    workspace_id: Optional[str] = Query(None, description="Workspace ID filter"),
    agent: DataQualityAgent = Depends(get_data_quality_agent),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    ws_id = workspace_id or (current_user.workspace_id if current_user else None)
    status_data = agent.get_status(workspace_id=ws_id)
    return DataQualityStatusResponse(**status_data)

@router.get(
    "/data-quality/results",
    response_model=DataQualityValidationListResponse,
    summary="List Validation Results",
    description="Retrieves historical product validation records with filtering."
)
def list_validation_results(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    classification: Optional[str] = Query(None, description="Filter by classification"),
    source_provider: Optional[str] = Query(None, description="Filter by provider"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    max_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    workspace_id: Optional[str] = Query(None),
    repo: DataQualityRepository = Depends(get_data_quality_repository),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    ws_id = workspace_id or (current_user.workspace_id if current_user else None)
    offset = (page - 1) * page_size
    items = repo.list_validation_results(
        workspace_id=ws_id,
        platform=platform,
        classification=classification,
        source_provider=source_provider,
        min_score=min_score,
        max_score=max_score,
        limit=page_size,
        offset=offset
    )
    total = repo.count_validation_results(
        workspace_id=ws_id,
        platform=platform,
        classification=classification,
        source_provider=source_provider,
        min_score=min_score,
        max_score=max_score
    )

    formatted = [
        DataQualityValidationResponse(
            id=res.id,
            platform=res.platform,
            source_provider=res.source_provider,
            platform_product_id=res.platform_product_id,
            unified_product_id=res.unified_product_id,
            product_title=res.product_title,
            overall_score=res.overall_score,
            classification=res.classification,
            is_trusted=res.is_trusted,
            issues=res.issues,
            warnings=res.warnings,
            field_scores=res.field_scores,
            used_llm=res.used_llm,
            llm_resolution=res.llm_resolution,
            validated_at=res.validated_at,
            run_id=res.run_id
        )
        for res in items
    ]

    return DataQualityValidationListResponse(
        items=formatted,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get(
    "/data-quality/results/{result_id}",
    response_model=DataQualityValidationResponse,
    summary="Get Validation Result Details"
)
def get_validation_result_detail(
    result_id: str,
    repo: DataQualityRepository = Depends(get_data_quality_repository)
):
    res = repo.get_validation_result(result_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation result not found")
    return DataQualityValidationResponse(
        id=res.id,
        platform=res.platform,
        source_provider=res.source_provider,
        platform_product_id=res.platform_product_id,
        unified_product_id=res.unified_product_id,
        product_title=res.product_title,
        overall_score=res.overall_score,
        classification=res.classification,
        is_trusted=res.is_trusted,
        issues=res.issues,
        warnings=res.warnings,
        field_scores=res.field_scores,
        used_llm=res.used_llm,
        llm_resolution=res.llm_resolution,
        validated_at=res.validated_at,
        run_id=res.run_id
    )

@router.get(
    "/data-quality/history",
    response_model=DataQualityRunHistoryResponse,
    summary="List Agent Execution Runs"
)
def list_agent_runs(
    workspace_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: DataQualityRepository = Depends(get_data_quality_repository),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    ws_id = workspace_id or (current_user.workspace_id if current_user else None)
    runs = repo.list_agent_runs(agent_id="agent_data_quality", workspace_id=ws_id, limit=limit, offset=offset)
    return DataQualityRunHistoryResponse(runs=runs, total=len(runs))

@router.get(
    "/data-quality/memory",
    response_model=DataQualityMemoryListResponse,
    summary="List Learned Agent Memories"
)
def list_agent_memories(
    memory_type: Optional[str] = Query(None, description="Filter by memory_type"),
    repo: DataQualityRepository = Depends(get_data_quality_repository)
):
    memories = repo.list_memories(agent_id="agent_data_quality", memory_type=memory_type)
    items = [
        DataQualityMemoryItemResponse(
            id=m.id,
            agent_id=m.agent_id,
            memory_type=m.memory_type,
            memory_key=m.memory_key,
            memory_value=m.memory_value,
            confidence_score=m.confidence_score,
            occurrence_count=m.occurrence_count,
            last_observed_at=m.last_observed_at,
            updated_at=m.updated_at
        )
        for m in memories
    ]
    return DataQualityMemoryListResponse(items=items, total=len(items))

@router.get(
    "/data-quality/memory/events",
    response_model=List[AIAgentMemoryEvent],
    summary="List Agent Memory Audit Events"
)
def list_memory_events(
    memory_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    repo: DataQualityRepository = Depends(get_data_quality_repository)
):
    return repo.list_memory_events(agent_id="agent_data_quality", memory_id=memory_id, limit=limit)
