"""Product intelligence data contracts and schemas."""

from app.intelligence.models.product import (
    ImageRecord,
    ProductIntelligence,
    Specification,
    Variant,
)
from app.intelligence.models.result import (
    ExtractionStatus,
    FieldConfidence,
    IntelligenceExtractionResult,
)
from app.intelligence.models.review import IntelligenceReview
from app.intelligence.models.snapshot import HistoricalSnapshot

__all__ = [
    "ProductIntelligence",
    "Variant",
    "Specification",
    "ImageRecord",
    "IntelligenceReview",
    "HistoricalSnapshot",
    "IntelligenceExtractionResult",
    "ExtractionStatus",
    "FieldConfidence",
]
