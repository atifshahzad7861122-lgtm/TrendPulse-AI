"""Configuration for Product Intelligence Extraction Pipeline."""

from pydantic import BaseModel, Field


class IntelligencePipelineConfig(BaseModel):
    """Execution parameters for Product Intelligence Pipeline."""

    max_concurrency: int = Field(default=3, ge=1, le=20, description="Max concurrent product extractions")
    preserve_raw_payloads: bool = Field(default=True, description="Whether to preserve raw HTML/JSON snippets")
    record_historical_snapshots: bool = Field(default=True, description="Whether to capture point-in-time snapshots")
    enforce_quality_gate: bool = Field(default=True, description="Whether to run DataQualityGate validations")
    snapshots_dir: str = Field(default="data/intelligence/snapshots", description="Ledger storage path for snapshots")
    checkpoints_dir: str = Field(default="data/intelligence/checkpoints", description="Checkpoint persistence path")
