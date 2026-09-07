from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ClassifyProductRequest(BaseModel):
    product_name: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    original_category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    platform: Optional[str] = None
    source_provider: Optional[str] = None
    allow_llm: bool = True
    force_reclassify: bool = False

# Backward-compat alias
CategorizationClassifyRequest = ClassifyProductRequest

class ProductTaxonomyAssignmentResponse(BaseModel):
    id: str
    unified_product_id: str
    category: str
    subcategory: str
    product_type: str
    taxonomy_path: List[str]
    brand: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    confidence_tier: Optional[str] = "high"
    classification_method: str
    needs_review: bool
    agent_id: str
    agent_run_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ProductTaxonomyCandidateItem(BaseModel):
    id: str
    product_id: str
    unified_product_id: Optional[str] = None
    candidate_category: str
    candidate_subcategory: str
    candidate_product_type: str
    confidence: float
    reason: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

# Backward-compat alias
ProductTaxonomyCandidateResponse = ProductTaxonomyCandidateItem

class ProductTaxonomyHistoryResponse(BaseModel):
    unified_product_id: str
    total: int
    items: List[ProductTaxonomyAssignmentResponse]

# Backward-compat alias
CategorizationHistoryResponse = ProductTaxonomyHistoryResponse

class AgentCategorizationMemoryItem(BaseModel):
    id: str
    agent_id: str
    memory_type: str
    memory_key: str
    memory_value: Dict[str, Any]
    confidence_score: float
    occurrence_count: int
    last_observed_at: datetime
    created_at: datetime
    updated_at: datetime

# Backward-compat alias
CategorizationMemoryItemResponse = AgentCategorizationMemoryItem

class AgentCategorizationMemoryListResponse(BaseModel):
    agent_id: str
    total: int
    items: List[AgentCategorizationMemoryItem]

# Backward-compat alias
CategorizationMemoryListResponse = AgentCategorizationMemoryListResponse

class CategorizationStatsResponse(BaseModel):
    total_classified: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    needs_review_count: int = 0
    deterministic_count: int = 0
    llm_count: int = 0
    memory_hit_count: int = 0
    average_confidence: float = 0.0
