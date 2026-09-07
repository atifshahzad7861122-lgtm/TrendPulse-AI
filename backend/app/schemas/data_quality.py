from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.app.models.domain import (
    AIAgent, AIAgentRun, AIAgentMemory, AIAgentMemoryEvent,
    DataQualityRuleViolation, DataQualityValidationResult
)

class DataQualityValidationRequest(BaseModel):
    product_payload: Dict[str, Any]
    platform: Optional[str] = None
    source_provider: Optional[str] = "direct"
    allow_llm: bool = True
    workspace_id: Optional[str] = None

class DataQualityBatchValidationRequest(BaseModel):
    products: List[Dict[str, Any]]
    platform: Optional[str] = None
    source_provider: Optional[str] = "direct"
    allow_llm: bool = True
    workspace_id: Optional[str] = None

class DataQualityValidationResponse(BaseModel):
    id: str
    platform: str
    source_provider: str
    platform_product_id: str
    unified_product_id: Optional[str] = None
    product_title: str
    overall_score: float
    classification: str  # "valid", "valid_with_warnings", "needs_review", "rejected"
    is_trusted: bool
    issues: List[DataQualityRuleViolation] = Field(default_factory=list)
    warnings: List[DataQualityRuleViolation] = Field(default_factory=list)
    field_scores: Dict[str, float] = Field(default_factory=dict)
    used_llm: bool = False
    llm_resolution: Optional[Dict[str, Any]] = None
    validated_at: datetime
    run_id: Optional[str] = None

class DataQualityBatchValidationResponse(BaseModel):
    run_id: str
    total_processed: int
    valid_count: int
    warning_count: int
    needs_review_count: int
    rejected_count: int
    avg_quality_score: float
    gemini_calls_count: int
    execution_time_ms: float
    results: List[DataQualityValidationResponse]

class ProviderReliabilityMetric(BaseModel):
    provider: str
    platform: str
    total_evaluated: int
    valid_rate: float
    warning_rate: float
    rejection_rate: float
    avg_score: float
    top_issues: List[str] = Field(default_factory=list)

class DataQualityStatusResponse(BaseModel):
    agent_id: str
    agent_name: str
    status: str
    version: str
    capabilities: List[str]
    total_runs: int
    total_products_validated: int
    valid_count: int
    warning_count: int
    needs_review_count: int
    rejected_count: int
    overall_average_score: float
    total_memory_items: int
    provider_reliabilities: List[ProviderReliabilityMetric]
    last_run_at: Optional[datetime] = None

class DataQualityMemoryItemResponse(BaseModel):
    id: str
    agent_id: str
    memory_type: str
    memory_key: str
    memory_value: Dict[str, Any]
    confidence_score: float
    occurrence_count: int
    last_observed_at: datetime
    updated_at: datetime

class DataQualityMemoryListResponse(BaseModel):
    items: List[DataQualityMemoryItemResponse]
    total: int

class DataQualityRunHistoryResponse(BaseModel):
    runs: List[AIAgentRun]
    total: int

class DataQualityValidationListResponse(BaseModel):
    items: List[DataQualityValidationResponse]
    total: int
    page: int
    page_size: int

class PublicDataQualityProductItem(BaseModel):
    id: str
    product_id: str = ""
    product_name: str
    platform: str
    provider: str
    data_quality_category: str = ""

    original_category: Optional[str] = None
    normalized_category: str = "Unknown"
    price: Optional[float] = None
    currency: str = "PKR"
    rating: Optional[float] = None
    review_count: int = 0
    availability: bool = True
    image: Optional[str] = None
    product_url: Optional[str] = None
    quality_score: float = 100.0
    classification: str = "valid"
    public_status: str = "Real Data"
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    invalid_fields: List[str] = Field(default_factory=list)
    suspicious_fields: List[str] = Field(default_factory=list)
    llm_used: bool = False
    last_validated_time: datetime

class PublicDataQualityFeedResponse(BaseModel):
    items: List[PublicDataQualityProductItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1

class PublicDataQualityStatsResponse(BaseModel):
    total_inspected: int = 0
    total_rejected: int = 0
    total_warnings: int = 0
    total_valid: int = 0
    rejection_rate: float = 0.0
    clean_rate: float = 0.0
    average_quality_score: float = 100.0
    top_rejection_reasons: List[Dict[str, Any]] = Field(default_factory=list)
    platform_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    category_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime

class PublicDataQualityHistoryResponse(BaseModel):
    platform: str
    product_id: str
    total_evaluations: int
    history: List[PublicDataQualityProductItem] = Field(default_factory=list)

