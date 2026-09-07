from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class LiveSignalItem(BaseModel):
    """
    Standardized live market signal representation across all connected platforms.
    """
    id: str
    type: str = Field(description="Signal type: PRODUCT, PRICE, RATING, SELLER, TREND, NEW, AVAILABILITY, CATEGORY")
    platform: str = Field(description="Origin platform: daraz, youtube, tiktok, instagram, facebook")
    title: str = Field(description="Short human-readable signal badge/header")
    description: str = Field(description="Factual, data-driven signal description")
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    signal_value: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "daraz.pk"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class LiveSignalsResponse(BaseModel):
    """
    Response payload for live market signals feed.
    """
    signals: List[LiveSignalItem] = Field(default_factory=list)
    total: int = 0
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
