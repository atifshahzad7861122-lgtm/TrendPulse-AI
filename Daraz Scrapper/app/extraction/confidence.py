"""Deterministic field-level confidence scoring for extracted product data."""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ExtractionSource(str, Enum):
    """Source tier used to retrieve a specific product field."""

    STRUCTURED_DATA = "structured_data"  # window.pageData, __INITIAL_STATE__, React state
    JSON_LD = "json_ld"                  # schema.org JSON-LD
    DOM = "dom"                          # Explicit DOM CSS / XPath selectors
    OPENGRAPH = "opengraph"              # Meta tags (og:title, og:image, etc.)
    FALLBACK = "fallback"                # Text regex / heuristic scanning
    BROWSER_DOM = "browser_dom"          # Dynamic DOM rendered via browser engine
    INFERRED = "inferred"                # Calculated / computed (e.g. discount %)


class FieldConfidenceScore(BaseModel):
    """Confidence evaluation for an individual product attribute."""

    field_name: str
    source: ExtractionSource
    confidence: float = Field(ge=0.0, le=1.0)
    is_valid: bool = True
    message: Optional[str] = None


class ConfidenceCalculator:
    """Computes deterministic confidence scores based on extraction source and field quality."""

    # Base confidence priors by source
    SOURCE_BASE_SCORES: Dict[ExtractionSource, float] = {
        ExtractionSource.STRUCTURED_DATA: 0.98,
        ExtractionSource.JSON_LD: 0.95,
        ExtractionSource.BROWSER_DOM: 0.92,
        ExtractionSource.DOM: 0.88,
        ExtractionSource.OPENGRAPH: 0.78,
        ExtractionSource.INFERRED: 0.70,
        ExtractionSource.FALLBACK: 0.55,
    }

    @classmethod
    def score_field(
        cls,
        field_name: str,
        source: ExtractionSource,
        has_value: bool,
        is_valid_format: bool = True,
    ) -> FieldConfidenceScore:
        """Calculate confidence for a single extracted field."""
        if not has_value:
            return FieldConfidenceScore(
                field_name=field_name,
                source=source,
                confidence=0.0,
                is_valid=False,
                message="Field missing or empty",
            )

        base_score = cls.SOURCE_BASE_SCORES.get(source, 0.50)
        confidence = base_score if is_valid_format else round(base_score * 0.5, 2)

        return FieldConfidenceScore(
            field_name=field_name,
            source=source,
            confidence=round(confidence, 2),
            is_valid=is_valid_format,
            message="Extracted successfully" if is_valid_format else "Value format anomaly detected",
        )

    @classmethod
    def calculate_overall_confidence(
        cls,
        field_scores: Dict[str, FieldConfidenceScore],
        field_weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Calculate weighted aggregate confidence score across all extracted fields."""
        weights = field_weights or {
            "title": 0.25,
            "price": 0.25,
            "images": 0.15,
            "seller": 0.10,
            "category": 0.10,
            "rating": 0.05,
            "description": 0.05,
            "specifications": 0.05,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for field, weight in weights.items():
            score_obj = field_scores.get(field)
            field_score = score_obj.confidence if score_obj else 0.0
            weighted_sum += field_score * weight
            total_weight += weight

        if total_weight == 0.0:
            return 0.0

        return round(weighted_sum / total_weight, 3)
