"""Raw source data preservation model for reprocessing and auditing."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
import uuid
from pydantic import BaseModel, Field

from app.core.constants import PARSER_VERSION, SCHEMA_VERSION


class RawDataRecord(BaseModel):
    """Immutable representation of unparsed HTTP/Browser response payload."""

    raw_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique raw capture ID")
    source_url: str = Field(..., description="Target origin URL")
    content_type: str = Field(default="html", description="Payload format: html, json, or text")
    payload: Union[str, Dict[str, Any]] = Field(..., description="Raw unprocessed response body")
    response_status: int = Field(default=200, description="HTTP response status code")
    request_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Capture timestamp"
    )
    parser_version: str = Field(default=PARSER_VERSION, description="Parser version active at capture")
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version active at capture")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional transport headers and context")
