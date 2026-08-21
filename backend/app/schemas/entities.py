from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class WorkspaceSetupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    industry: str
    use_case: str
    currency: str = "USD"
    default_dashboard: str = "signals"
    data_sources: List[str] = Field(default_factory=list)

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    industry: str
    use_case: str
    currency: str
    default_dashboard: str
    connected_sources: List[str]
    is_setup_complete: bool
    owner_id: str

class MetricCard(BaseModel):
    title: str
    value: str
    change: str
    is_positive: bool
    subtext: str
    icon: str

class TrendPoint(BaseModel):
    timestamp: str
    score: float
    volume: int
    sentiment: float
    platform_tiktok: float
    platform_daraz: float
    platform_instagram: float
    platform_youtube: float

class LiveSignalItem(BaseModel):
    id: str
    text: str
    platform: str
    growth: str
    timestamp: str
    category: str

class DashboardSummaryResponse(BaseModel):
    metrics: List[MetricCard]
    live_signals: List[LiveSignalItem]
    top_surging: List[Dict[str, Any]]
    total_trends_monitored: int
    system_status: str

class ProductFilterRequest(BaseModel):
    category: Optional[str] = "all"
    platform: Optional[str] = "all"
    search: Optional[str] = None
    sort_by: Optional[str] = "trend_score"
    time_range: Optional[str] = "30d"

class ReportGenerateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    template: str
    time_range: str
    category: Optional[str] = "All Categories"
    platforms: List[str] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)

class DataSourceActionRequest(BaseModel):
    slug: str
    action: str  # "connect" or "disconnect"

class SearchResultItem(BaseModel):
    id: str
    title: str
    subtitle: str
    category: str  # "products", "categories", "platforms", "reports", "alerts"
    link: str
    badge: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
