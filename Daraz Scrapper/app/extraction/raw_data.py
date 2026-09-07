"""Raw extraction data preservation and audit records."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RawDataRecord(BaseModel):
    """Encapsulates raw unprocessed source payloads for future auditing or re-parsing."""

    product_id: str
    url: str
    http_status: int = 200
    structured_json: Optional[Dict[str, Any]] = None
    json_ld: Optional[Dict[str, Any]] = None
    html_snapshot_length: int = 0
    extraction_source: str = "http"
    captured_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to storage-friendly dictionary."""
        return {
            "product_id": self.product_id,
            "url": self.url,
            "http_status": self.http_status,
            "structured_json": self.structured_json,
            "json_ld": self.json_ld,
            "html_snapshot_length": self.html_snapshot_length,
            "extraction_source": self.extraction_source,
            "captured_at": self.captured_at,
        }
