"""Universal Multi-Marketplace Product Intelligence Engine."""

from app.intelligence.history.snapshot_manager import HistoricalSnapshotManager
from app.intelligence.models.product import ImageRecord, ProductIntelligence, Specification, Variant
from app.intelligence.models.result import ExtractionStatus, FieldConfidence, IntelligenceExtractionResult
from app.intelligence.models.review import IntelligenceReview
from app.intelligence.models.snapshot import HistoricalSnapshot
from app.intelligence.pipeline.config import IntelligencePipelineConfig
from app.intelligence.pipeline.engine import ProductIntelligenceEngine
from app.intelligence.validation.confidence import ConfidenceScorer
from app.intelligence.validation.quality_gate import DataQualityGate

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
    "DataQualityGate",
    "ConfidenceScorer",
    "HistoricalSnapshotManager",
    "IntelligencePipelineConfig",
    "ProductIntelligenceEngine",
]
