"""Data contracts and result models for the product extraction layer."""

from datetime import datetime, timezone
from typing import Dict, Iterator, List, Optional
from pydantic import BaseModel, Field

from app.extraction.confidence import FieldConfidenceScore
from app.extraction.raw_data import RawDataRecord
from app.extraction.validator import ValidationReport, ValidationStatus
from app.models.product import Product


class ExtractionResult(BaseModel):
    """Encapsulates the complete result, diagnostics, confidence, and quality metadata for a product extraction job."""

    product: Optional[Product] = Field(default=None, description="The validated Product data model")
    success: bool = Field(default=True, description="Whether extraction successfully produced a valid Product")
    validation_status: ValidationStatus = Field(default=ValidationStatus.VALID, description="Quality classification")
    validation_report: Optional[ValidationReport] = Field(default=None, description="Detailed validation breakdown")
    overall_confidence: float = Field(default=1.0, description="Weighted aggregate confidence score (0.0 to 1.0)")
    field_confidence: Dict[str, FieldConfidenceScore] = Field(default_factory=dict, description="Field-level confidence")
    raw_data: Optional[RawDataRecord] = Field(default=None, description="Raw source snapshot record")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings regarding optional fields")
    errors: List[str] = Field(default_factory=list, description="Fatal or diagnostic error messages")
    fields_extracted: List[str] = Field(default_factory=list, description="List of fields successfully extracted")
    fields_missing: List[str] = Field(default_factory=list, description="List of expected fields that were not found")
    extraction_duration_ms: float = Field(default=0.0, description="Total extraction duration in milliseconds")
    source_engine: str = Field(default="http", description="Underlying retrieval engine used (http, browser, etc.)")
    extracted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __iter__(self) -> Iterator:
        """Allow backward-compatible 4-tuple unpacking: (product, fields_extracted, fields_missing, warnings)."""
        yield self.product
        yield self.fields_extracted
        yield self.fields_missing
        yield self.warnings
