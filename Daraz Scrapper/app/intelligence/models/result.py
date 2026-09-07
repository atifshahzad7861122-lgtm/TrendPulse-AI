"""Extraction result and status models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.crawling.models import MarketplaceType
from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.review import IntelligenceReview
from app.intelligence.models.snapshot import HistoricalSnapshot


class ExtractionStatus(str, Enum):
    """Status of an intelligence extraction execution."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CHALLENGE = "challenge"
    NOT_FOUND = "not_found"


class FieldConfidence(str, Enum):
    """Qualitative confidence classification."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class IntelligenceExtractionResult(BaseModel):
    """Complete product intelligence extraction output contract."""

    extraction_id: str = Field(..., description="Unique extraction run identifier")
    product_id: str = Field(..., description="Platform product ID")
    marketplace: MarketplaceType = Field(..., description="Target marketplace")
    url: str = Field(..., description="Target listing URL")
    status: ExtractionStatus = Field(..., description="Overall extraction status")
    success: bool = Field(default=False, description="True if core intelligence was successfully extracted")
    status_code: int = Field(default=200, description="HTTP response status code")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")

    # Extracted Intelligence Entities
    product: Optional[ProductIntelligence] = Field(default=None, description="Normalized product intelligence")
    reviews: List[IntelligenceReview] = Field(default_factory=list, description="Extracted customer feedback reviews")
    snapshot: Optional[HistoricalSnapshot] = Field(default=None, description="Generated point-in-time snapshot")

    # Diagnostics & Confidence
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Field-level confidence mapping (0.0-1.0)")
    confidence_levels: Dict[str, FieldConfidence] = Field(default_factory=dict, description="Qualitative confidence labels")
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall aggregate confidence score")
    
    # Audit & Diagnostics
    fields_extracted: List[str] = Field(default_factory=list, description="List of fields successfully populated")
    fields_missing: List[str] = Field(default_factory=list, description="List of expected fields that were missing")
    warnings: List[str] = Field(default_factory=list, description="Extraction diagnostics and fallback notices")
    errors: List[str] = Field(default_factory=list, description="Error messages if extraction failed")

    # Raw Payloads
    raw_payload: Optional[str] = Field(default=None, description="Raw HTML or JSON source payload")
    raw_metadata: Dict[str, Any] = Field(default_factory=dict, description="Original unparsed marketplace metadata")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Result creation timestamp"
    )
