from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MatchProductRequest(BaseModel):
    product_name: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    product_type: Optional[str] = None
    platform: str = "unknown"
    platform_product_id: Optional[str] = None
    sku: Optional[str] = None
    gtin: Optional[str] = None
    upc: Optional[str] = None
    ean: Optional[str] = None
    asin: Optional[str] = None
    model_number: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    price: Optional[float] = None
    currency: str = "USD"
    url: Optional[str] = None
    image_url: Optional[str] = None
    allow_llm: bool = True
    force_rematch: bool = False

class CompareProductsRequest(BaseModel):
    product_a: Dict[str, Any]
    product_b: Dict[str, Any]
    allow_llm: bool = True

class ProductMatchDecisionResponse(BaseModel):
    id: str
    product_a_id: str
    product_b_id: Optional[str] = None
    unified_product_id: Optional[str] = None
    platform_a: str
    platform_b: Optional[str] = None
    decision: str  # EXACT_MATCH, HIGH_CONFIDENCE_MATCH, PROBABLE_MATCH, VARIANT, RELATED_PRODUCT, NO_MATCH, NEEDS_REVIEW
    confidence: float
    match_method: str
    reasons: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    variant_attributes: Dict[str, Any] = Field(default_factory=dict)
    base_product_id: Optional[str] = None
    llm_used: bool = False
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    agent_id: str = "agent_entity_matching"
    agent_run_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ProductMatchHistoryResponse(BaseModel):
    product_id: str
    total: int
    items: List[ProductMatchDecisionResponse] = Field(default_factory=list)

class ProductMatchCandidateResponse(BaseModel):
    id: str
    unified_product_id: str
    candidate_unified_id: str
    platform: str
    platform_product_id: str
    confidence_score: float
    method: str
    status: str  # "probable", "needs_review", "confirmed_match", "confirmed_variant", "rejected"
    reasons: List[str] = Field(default_factory=list)
    product_a_title: Optional[str] = None
    product_b_title: Optional[str] = None
    conflicts: List[str] = Field(default_factory=list)
    variant_attributes: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

class ResolveCandidateRequest(BaseModel):
    action: str = Field(..., description="'confirm_match', 'confirm_variant', or 'reject_match'")
    notes: Optional[str] = None
    variant_attributes: Optional[Dict[str, Any]] = None

class EntityMatchingMemoryItem(BaseModel):
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

class EntityMatchingMemoryListResponse(BaseModel):
    agent_id: str
    total: int
    items: List[EntityMatchingMemoryItem] = Field(default_factory=list)

class EntityMatchingStatsResponse(BaseModel):
    total_evaluations: int = 0
    exact_matches: int = 0
    high_confidence_matches: int = 0
    probable_matches: int = 0
    variants_detected: int = 0
    related_products: int = 0
    no_matches: int = 0
    review_queue_count: int = 0
    deterministic_match_rate: float = 0.0
    llm_match_rate: float = 0.0
    memory_hit_count: int = 0
    average_confidence: float = 0.0
