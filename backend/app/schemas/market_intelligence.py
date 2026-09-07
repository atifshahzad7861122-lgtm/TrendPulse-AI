"""
Canonical Pydantic Schemas for Phase 3 Market Intelligence REST API.

Defines the request and response models for market score, demand intelligence,
trend velocity, growth, viral potential, product opportunities, social signals,
cross-marketplace comparisons, and AI market analyst reports.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MarketScoreResponse(BaseModel):
    score: float = Field(..., description="Calibrated market score (0-100)")
    components: Dict[str, float] = Field(..., description="Component breakdown scores")
    weights: Dict[str, float] = Field(..., description="Component weights applied")
    confidence: float = Field(..., description="Statistical confidence (0.0 - 1.0)")
    data_quality_score: float = Field(..., description="Underlying Data Quality score")
    history_status: str = Field("insufficient_history", description="'measured' if historical snapshots exist, else 'insufficient_history'")
    calculation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DemandIntelligenceResponse(BaseModel):
    demand_score: float = Field(..., description="Demand conviction score (0-100)")
    demand_level: str = Field(..., description="Classification: LOW, MEDIUM, HIGH, VERY_HIGH")
    demand_trend: str = Field(..., description="Trajectory: rising, stable, declining")
    confidence: float = Field(..., description="Demand confidence (0.0 - 1.0)")
    contributors: List[str] = Field(default_factory=list, description="Traceable positive/negative drivers")


class TrendVelocityResponse(BaseModel):
    velocity: Optional[float] = Field(None, description="Average change per unit time, or null if insufficient history")
    window_days: Optional[float] = Field(None, description="Observation window in days")
    status: str = Field("insufficient_data", description="'calculated' or 'insufficient_data'")
    observation_count: int = Field(0, description="Number of historical snapshot observations")


class GrowthIntelligenceResponse(BaseModel):
    growth_7d: Optional[float] = Field(None, description="7-day percentage growth, or null")
    growth_30d: Optional[float] = Field(None, description="30-day percentage growth, or null")
    window_days: Optional[float] = Field(None, description="Observed window span in days")
    status: str = Field("insufficient_data", description="'calculated' or 'insufficient_data'")
    observation_count: int = Field(0, description="Total observations in window")


class ViralPotentialResponse(BaseModel):
    viral_score: Optional[float] = Field(None, description="Viral momentum score (0-100) or null")
    viral_level: str = Field("unavailable", description="unavailable, Low, Moderate, High, Very High")
    confidence: float = Field(0.0, description="Virality confidence based on social signals")
    has_social_signals: bool = Field(False, description="Whether real social observations exist")
    supporting_signals: List[str] = Field(default_factory=list, description="Documented social drivers")


class ProductOpportunityResponse(BaseModel):
    opportunity_score: float = Field(..., description="Commercial opportunity score (0-100)")
    opportunity_level: str = Field("Low", description="Low, Moderate, High, Exceptional")
    confidence: float = Field(..., description="Opportunity confidence score (0.0 - 1.0)")
    competition_level: str = Field("unavailable", description="unavailable, Low, Moderate, High")
    reasoning: List[str] = Field(default_factory=list, description="Analytical reasoning")
    supporting_signals: List[str] = Field(default_factory=list, description="Positive supporting signals")


class SocialSignalItem(BaseModel):
    id: str
    platform: str
    content_title: str
    content_url: Optional[str] = None
    author_name: Optional[str] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: float = 0.0
    matched_product_id: Optional[str] = None
    match_confidence: float = 0.0
    observed_at: datetime


class CrossMarketplaceComparisonItem(BaseModel):
    platforms_present: List[str] = Field(default_factory=list)
    lowest_price: float = 0.0
    highest_price: float = 0.0
    average_price: float = 0.0
    price_spread_pct: float = 0.0
    currency: str = "USD"
    rating_avg: float = 0.0
    total_reviews: int = 0
    listings_count: int = 0


class ProductMarketIntelligenceDetail(BaseModel):
    product_id: str
    title: str
    marketplace: str
    category: Optional[str] = None
    current_price: float = 0.0
    original_price: Optional[float] = None
    currency: str = "USD"
    rating: float = 0.0
    review_count: int = 0
    availability: bool = True
    url: Optional[str] = None
    image_url: Optional[str] = None

    # Analytical Intelligence
    market_score: MarketScoreResponse
    demand: DemandIntelligenceResponse
    trend_velocity: TrendVelocityResponse
    growth: GrowthIntelligenceResponse
    viral_potential: ViralPotentialResponse
    opportunity: ProductOpportunityResponse
    cross_marketplace: Optional[CrossMarketplaceComparisonItem] = None
    social_signals: List[SocialSignalItem] = Field(default_factory=list)
    ai_summary: Optional[str] = None

    # Meta
    data_quality_score: float = 0.0
    confidence: float = 0.0
    source_provenance: str = "marketplace"
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MarketOverviewResponse(BaseModel):
    average_market_score: float = 0.0
    total_products_analyzed: int = 0
    high_demand_count: int = 0
    high_opportunity_count: int = 0
    social_active_count: int = 0
    marketplaces_covered: List[str] = Field(default_factory=list)

    top_products: List[ProductMarketIntelligenceDetail] = Field(default_factory=list)
    trending_products: List[ProductMarketIntelligenceDetail] = Field(default_factory=list)
    rising_products: List[ProductMarketIntelligenceDetail] = Field(default_factory=list)
    declining_products: List[ProductMarketIntelligenceDetail] = Field(default_factory=list)
    high_demand_products: List[ProductMarketIntelligenceDetail] = Field(default_factory=list)
    high_opportunity_products: List[ProductMarketIntelligenceDetail] = Field(default_factory=list)
    socially_trending_products: List[ProductMarketIntelligenceDetail] = Field(default_factory=list)

    ai_executive_summary: Optional[str] = None
    data_quality_average: float = 0.0
    overall_confidence: float = 0.0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CategoryIntelligenceItem(BaseModel):
    category_name: str
    product_count: int = 0
    average_price: float = 0.0
    average_rating: float = 0.0
    average_market_score: float = 0.0
    demand_level: str = "MODERATE"
    opportunity_level: str = "Moderate"
    social_interest_score: float = 0.0
    data_confidence: float = 0.0


class CategoryIntelligenceResponse(BaseModel):
    categories: List[CategoryIntelligenceItem] = Field(default_factory=list)
    total_categories: int = 0


class MarketplaceComparisonResponse(BaseModel):
    marketplace: str
    product_count: int = 0
    average_price: float = 0.0
    average_rating: float = 0.0
    in_stock_rate_pct: float = 0.0
    average_discount_pct: float = 0.0
    average_market_score: float = 0.0
    currency: str = "USD"


class MarketplacesIntelligenceResponse(BaseModel):
    marketplaces: List[MarketplaceComparisonResponse] = Field(default_factory=list)
    primary_marketplace: str = "amazon"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SocialIntelligenceResponse(BaseModel):
    signals: List[SocialSignalItem] = Field(default_factory=list)
    total_signals: int = 0
    total_views: int = 0
    total_engagement: int = 0
    platforms: List[str] = Field(default_factory=list)


class MarketIntelligenceReportResponse(BaseModel):
    report_id: str
    title: str
    marketplace: str
    category: Optional[str] = None
    keyword: Optional[str] = None

    overview: MarketOverviewResponse
    ai_market_narrative: Optional[str] = None
    ai_trend_drivers: List[str] = Field(default_factory=list)
    ai_market_opportunities: List[str] = Field(default_factory=list)
    ai_risk_factors: List[str] = Field(default_factory=list)
    ai_strategic_recommendations: List[str] = Field(default_factory=list)

    data_quality_score: float = 0.0
    confidence: float = 0.0
    sources_audited: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnalyzeIntelligenceRequest(BaseModel):
    marketplace: Optional[str] = "amazon"
    keyword: Optional[str] = None
    category: Optional[str] = None
    product_ids: Optional[List[str]] = None
    include_ai_narrative: bool = True
    force_refresh: bool = False
