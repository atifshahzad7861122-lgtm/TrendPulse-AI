from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class DataFreshnessMeta(BaseModel):
    source_platforms: List[str] = Field(default_factory=list, description="Platforms contributing to this analysis")
    source_providers: List[str] = Field(default_factory=list, description="Data providers utilized")
    last_synced_at: Optional[str] = Field(None, description="ISO timestamp of most recent source sync")
    data_age_seconds: int = Field(0, description="Age of data in seconds at analysis time")
    data_status: str = Field("live", description="'live' or 'cached'")

class AIProductAnalysisRequest(BaseModel):
    unified_product_id: str
    force_refresh: bool = False

class AIProductAnalysisResponse(BaseModel):
    unified_product_id: str
    canonical_name: str
    summary: str
    category: Optional[str] = None
    confidence_score: float = Field(0.9, ge=0.0, le=1.0)
    key_signals: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    pricing_analysis: Dict[str, Any] = Field(default_factory=dict)
    data_freshness: DataFreshnessMeta
    is_cached: bool = False
    prompt_version: str = "product_analysis_v1"
    provider: str = "mock"
    model: str = "default"
    tokens_used: int = 0
    latency_ms: float = 0.0

class AIProductSummaryRequest(BaseModel):
    unified_product_id: str
    force_refresh: bool = False

class AIProductSummaryResponse(BaseModel):
    unified_product_id: str
    canonical_name: str
    executive_summary: str
    key_takeaways: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    competitive_edge: Optional[str] = None
    data_freshness: DataFreshnessMeta
    is_cached: bool = False
    prompt_version: str = "product_summary_v1"
    provider: str = "mock"
    model: str = "default"
    tokens_used: int = 0
    latency_ms: float = 0.0

class AICategoryAnalysisRequest(BaseModel):
    category: str
    force_refresh: bool = False

class AICategoryAnalysisResponse(BaseModel):
    category: str
    market_overview: str
    demand_state: str
    price_range_summary: str
    growth_drivers: List[str] = Field(default_factory=list)
    threats_and_challenges: List[str] = Field(default_factory=list)
    strategic_advice: List[str] = Field(default_factory=list)
    data_freshness: DataFreshnessMeta
    is_cached: bool = False
    prompt_version: str = "category_analysis_v1"
    provider: str = "mock"
    model: str = "default"
    tokens_used: int = 0
    latency_ms: float = 0.0

class AIMarketComparisonRequest(BaseModel):
    unified_product_id: str
    force_refresh: bool = False

class AIMarketComparisonResponse(BaseModel):
    unified_product_id: str
    canonical_name: str
    cross_platform_overview: str
    price_arbitrage_analysis: str
    seller_and_vendor_landscape: str
    platform_comparison_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    data_freshness: DataFreshnessMeta
    is_cached: bool = False
    prompt_version: str = "market_comparison_v1"
    provider: str = "mock"
    model: str = "default"
    tokens_used: int = 0
    latency_ms: float = 0.0

class AITrendAnalysisRequest(BaseModel):
    unified_product_id: str
    force_refresh: bool = False

class AITrendAnalysisResponse(BaseModel):
    unified_product_id: str
    canonical_name: str
    trend_trajectory: str
    velocity_assessment: str
    volatility_risk: str
    historical_price_action: str
    predictive_outlook_30d: str
    data_freshness: DataFreshnessMeta
    is_cached: bool = False
    prompt_version: str = "trend_analysis_v1"
    provider: str = "mock"
    model: str = "default"
    tokens_used: int = 0
    latency_ms: float = 0.0

class LLMUsageSummaryResponse(BaseModel):
    total_requests: int
    successful_requests: int
    cached_requests: int
    failed_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    average_latency_ms: float
