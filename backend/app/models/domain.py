import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class User(BaseModel):
    id: str
    email: str
    full_name: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    verification_token: Optional[str] = None
    reset_token: Optional[str] = None
    reset_token_expires_at: Optional[datetime] = None
    workspace_id: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "Administrator"
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Workspace(BaseModel):
    id: str
    name: str
    industry: str
    use_case: str
    currency: str = "USD"
    default_dashboard: str = "signals"
    connected_sources: List[str] = Field(default_factory=list)
    is_setup_complete: bool = False
    owner_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WorkspaceMember(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: str = "Administrator"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    id: str
    user_id: str
    token_hash: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool = False
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmailVerification(BaseModel):
    id: str
    user_id: str
    token: str
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PasswordResetToken(BaseModel):
    id: str
    user_id: str
    token: str
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LoginEvent(BaseModel):
    id: str
    user_id: Optional[str] = None
    email: str
    event_type: str  # "login_success", "login_failed", "logout", "password_reset", "email_verified"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Product(BaseModel):
    id: str
    name: str
    category: str
    sub_category: Optional[str] = None
    trend_score: float = 0.0
    growth_rate: float = 0.0
    volume: int = 0
    velocity_label: str = "Steady"  # "Breakout", "Surging", "Steady", "Explosive"
    status: str = "Active"  # "Active", "Watching", "Saturated"
    price_range: str = "$0.00"
    primary_platform: str = "Daraz"
    platforms: List[str] = Field(default_factory=list)
    platform_shares: Dict[str, float] = Field(default_factory=dict)
    historical_scores: List[Dict[str, Any]] = Field(default_factory=list)
    historical_prices: List[Dict[str, Any]] = Field(default_factory=list)
    ai_summary: str = ""
    signals_count: int = 0
    sentiment_score: float = 0.0
    image_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_watchlisted: bool = False
    provenance: str = "none"
    observation_count: int = 0
    historical_observation_count: int = 0
    data_sufficiency: str = "insufficient_data"
    raw_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Category(BaseModel):
    id: str
    name: str
    slug: str
    product_count: int = 0
    avg_trend_score: float = 0.0
    growth_rate: float = 0.0
    velocity_label: str = "Steady"
    description: Optional[str] = None
    subcategories: List[str] = Field(default_factory=list)
    top_platforms: List[str] = Field(default_factory=list)
    top_driver: str = ""
    provenance: str = "none"
    observation_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



class PlatformMetrics(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    total_signals: int = 0
    active_trends: int = 0
    velocity_growth: float = 0.0
    market_share: float = 0.0
    status: str = "Connected"
    provenance: str = "none"
    observation_count: int = 0
    recent_spikes: List[Any] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Alert(BaseModel):
    id: str
    title: str
    description: str
    severity: str  # "Critical", "Warning", "Info"
    category: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    platform: Optional[str] = None
    trigger: Optional[str] = None
    threshold: Optional[float] = None
    actual_value: Optional[float] = None
    is_read: bool = False
    is_resolved: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Notification(BaseModel):
    id: str
    title: str
    message: str
    type: str = "alert"  # "alert", "report", "system"
    is_read: bool = False
    link: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Report(BaseModel):
    id: str
    title: str
    template: str  # "Weekly Intelligence Summary", "Viral Product Deep Dive", "Category Momentum Analysis", "Custom AI Synthesis"
    time_range: str
    format: str = "PDF"  # "PDF", "CSV", "JSON"
    status: str = "Ready"  # "Preparing", "Analyzing", "Building", "Ready", "Failed"
    progress: int = 100  # 0 to 100
    category: Optional[str] = None
    platforms: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    ai_takeaways: str
    total_signals_analyzed: int = 0
    high_conviction_count: int = 0
    products_evaluated: int = 0
    provenance: str = "persisted_observations"
    data_sufficiency: str = "insufficient_data"  # "live_data", "insufficient_data", "no_data"
    observation_count: int = 0
    historical_observation_count: int = 0
    source_breakdown: Dict[str, int] = Field(default_factory=dict)
    pdf_url: Optional[str] = None
    csv_url: Optional[str] = None
    created_by: str = "Admin"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DataSource(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    description: str
    status: str = "Disconnected"  # "Connected", "Disconnected", "Syncing", "Error"
    last_sync: Optional[datetime] = None
    sync_frequency: str = "Hourly"
    records_synced: int = 0
    health_score: int = 100

class UserSettings(BaseModel):
    user_id: str
    full_name: str
    email: str
    avatar_url: Optional[str] = None
    role: str = "Administrator"
    company_name: str = "TrendPulse Global Intelligence"
    timezone: str = "UTC"
    currency: str = "USD"
    email_notifications: bool = True
    alert_critical_only: bool = False
    weekly_digest: bool = True
    ai_model_preference: str = "Qwen 2.5 Max (Simulated)"
    ai_confidence_threshold: int = 80
    auto_generate_reports: bool = False
    dark_mode: bool = True
    table_dense_view: bool = False
    live_ticker_enabled: bool = True

class UserSettingsUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = None
    company_name: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    email_notifications: Optional[bool] = None
    alert_critical_only: Optional[bool] = None
    weekly_digest: Optional[bool] = None
    ai_model_preference: Optional[str] = None
    ai_confidence_threshold: Optional[int] = None
    auto_generate_reports: Optional[bool] = None
    dark_mode: Optional[bool] = None
    table_dense_view: Optional[bool] = None
    live_ticker_enabled: Optional[bool] = None

class SubscriptionPlan(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    price: float = 0.0
    currency: str = "USD"
    billing_interval: str = "monthly"
    monthly_credits: int = 100
    is_active: bool = True
    features: List[str] = Field(default_factory=list)
    limits: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSubscription(BaseModel):
    id: str
    user_id: str
    plan_id: str
    status: str = "active"  # "active", "trialing", "cancelled", "expired", "paused"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_period_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_period_end: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cancelled_at: Optional[datetime] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CreditAccount(BaseModel):
    id: str
    user_id: str
    current_balance: int = 0
    lifetime_granted: int = 0
    lifetime_used: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CreditTransaction(BaseModel):
    id: str
    credit_account_id: str
    user_id: str
    amount: int
    transaction_type: str  # "grant", "usage", "refund", "adjustment", "expiration", "subscription_allocation"
    balance_before: int
    balance_after: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    description: str = ""
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CreditUsage(BaseModel):
    id: str
    user_id: str
    credit_account_id: str
    feature: str
    action: str
    credits_used: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MarketplaceProduct(BaseModel):
    id: str
    platform: str = "daraz"
    product_id: str
    product_name: str
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    seller_name: Optional[str] = None
    seller_id: Optional[str] = None
    category: Optional[str] = None
    price: float = 0.0
    original_price: float = 0.0
    discount_percentage: float = 0.0
    discount_label: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    stock_status: str = "in_stock"
    in_stock: bool = True
    currency: str = "PKR"
    location: Optional[str] = None
    raw_source_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def _populate_title_or_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "product_name" not in data and "title" in data:
                data["product_name"] = data["title"]
        return data

    @property
    def title(self) -> str:
        return self.product_name

    @title.setter
    def title(self, value: str):
        self.product_name = value

class ProductMarketSnapshot(BaseModel):
    id: str
    product_id: str
    platform: str = "daraz"
    price: float = 0.0
    original_price: float = 0.0
    discount: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    stock_status: str = "in_stock"
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ShopifyProduct(BaseModel):
    id: str
    store_domain: str
    product_id: str
    title: str
    handle: Optional[str] = None
    product_url: str
    image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    price: float = 0.0
    compare_at_price: Optional[float] = None
    discount_percentage: float = 0.0
    discount_label: Optional[str] = None
    currency: str = "USD"
    available: bool = True
    rating: float = 0.0
    review_count: int = 0
    source_provider: str = "shopify_scout"
    variants_count: int = 1
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ShopifyProductSnapshot(BaseModel):
    id: str
    shopify_product_id: str
    store_domain: str
    product_id: str
    price: float = 0.0
    compare_at_price: Optional[float] = None
    available: bool = True
    rating: float = 0.0
    review_count: int = 0
    inventory_status: str = "in_stock"
    source_provider: str = "shopify_scout"
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ShopifyProviderHealth(BaseModel):
    id: str
    provider_name: str
    priority: int
    enabled: bool = True
    status: str = "healthy"  # "healthy", "degraded", "rate_limited", "unhealthy"
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    last_error_code: Optional[int] = None
    last_error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ShopifySyncRun(BaseModel):
    id: str
    store_domain: str
    provider_name: str
    status: str = "success"  # "success", "partial", "failed", "fallback_cache"
    products_fetched: int = 0
    products_inserted: int = 0
    products_updated: int = 0
    snapshots_created: int = 0
    provider_attempts: List[Dict[str, Any]] = Field(default_factory=list)
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DarazAuthSession(BaseModel):
    id: str
    account: Optional[str] = None
    seller_id: Optional[str] = None
    user_id: Optional[str] = None
    country: str = "pk"
    access_token: Optional[str] = None  # Stored securely server-side only
    refresh_token: Optional[str] = None  # Stored securely server-side only
    expires_in: Optional[int] = None
    refresh_expires_in: Optional[int] = None
    token_type: Optional[str] = "Bearer"
    status: str = "authorized"  # "authorized", "expired", "revoked", "pending"
    authorized_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DarazProviderHealth(BaseModel):
    id: str
    provider_name: str
    priority: int
    enabled: bool = True
    status: str = "healthy"  # "healthy", "degraded", "rate_limited", "unhealthy"
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    last_error_code: Optional[int] = None
    last_error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DarazSeller(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    seller_id: str
    seller_name: str
    shop_url: Optional[str] = None
    rating: float = 0.0
    positive_ratings_percentage: float = 0.0
    location: Optional[str] = None
    is_official_store: bool = False
    total_products: int = 0
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DarazCategory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str
    parent_id: Optional[str] = None
    name: str
    slug: str
    level: int = 1
    leaf: bool = True
    product_count: int = 0
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DarazReview(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    review_id: str
    product_id: str
    seller_id: Optional[str] = None
    rating: float = 0.0
    reviewer_name: Optional[str] = None
    review_title: Optional[str] = None
    review_content: Optional[str] = None
    verified_purchase: bool = True
    review_date: Optional[datetime] = None
    sentiment_score: float = 0.0
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DarazIngestionRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider_name: str
    status: str = "success"  # "running", "success", "partial", "failed"
    trigger_type: str = "scheduled"
    category: Optional[str] = None
    search_query: Optional[str] = None
    products_fetched: int = 0
    products_inserted: int = 0
    products_updated: int = 0
    snapshots_created: int = 0
    reviews_fetched: int = 0
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DarazApiTelemetry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    endpoint: str
    method: str = "GET"
    provider_name: str = "daraz_official_open_platform"
    status_code: int = 200
    latency_ms: float = 0.0
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    request_params: Dict[str, Any] = Field(default_factory=dict)
    response_size_bytes: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DarazDailyQuota(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str  # YYYY-MM-DD
    requests_used: int = 0
    daily_limit: int = 6000000
    remaining: int = 6000000
    rate_limit_hits: int = 0
    last_request_at: Optional[datetime] = None
    reset_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DarazTrainingDataset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    unified_product_id: Optional[str] = None
    title: str
    category: str
    brand: Optional[str] = None
    price: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    features: Dict[str, Any] = Field(default_factory=dict)
    quality_score: float = 100.0
    agent_label: str = "clean_catalog"
    is_validated: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UnifiedProduct(BaseModel):
    id: str
    unified_product_id: str
    canonical_name: str
    normalized_name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    product_type: Optional[str] = None
    description: Optional[str] = None
    primary_image: Optional[str] = None
    identifiers: Dict[str, Any] = Field(default_factory=dict)  # sku, gtin, upc, ean, mpn, model, etc.
    platforms: List[str] = Field(default_factory=list)
    platform_count: int = 0
    listings_count: int = 0
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    average_price: Optional[float] = None
    primary_currency: str = "USD"
    avg_rating: float = 0.0
    total_reviews: int = 0
    completeness_score: float = 1.0
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductPlatformListing(BaseModel):
    id: str
    unified_product_id: str
    platform: str  # "Daraz", "Shopify", "Amazon", "eBay", etc.
    platform_product_id: str
    store_domain: Optional[str] = None
    product_url: str
    title: str
    normalized_title: str
    price: float = 0.0
    original_price: Optional[float] = None
    currency: str = "USD"
    discount_percentage: float = 0.0
    discount_label: Optional[str] = None
    seller_name: Optional[str] = None
    vendor: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    available: bool = True
    image_url: Optional[str] = None
    source_provider: str = "direct"
    last_synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completeness_score: float = 1.0  # 0.0 - 1.0 (data quality)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductMatchCandidate(BaseModel):
    id: str
    unified_product_id: str
    candidate_unified_id: str
    platform: str
    platform_product_id: str
    confidence_score: float
    method: str  # "sku_exact", "brand_model_exact", "normalized_name_similarity", etc.
    status: str = "probable"  # "matched", "probable", "rejected"
    reasons: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductMatchAudit(BaseModel):
    id: str
    unified_product_id: str
    platform: str
    platform_product_id: str
    matching_method: str
    matching_confidence: float
    matched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LLMUsageRecord(BaseModel):
    id: str
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    provider: str
    model: str
    request_type: str  # "product_analysis", "product_summary", "category_analysis", "market_comparison", "trend_analysis"
    prompt_version: str = "v1"
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: float = 0.0
    status: str = "success"  # "success", "failed", "cached"
    error_code: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIAgent(BaseModel):
    id: str
    name: str
    slug: str
    agent_type: str  # "data_quality", "trend_prediction", etc.
    status: str = "active"  # "active", "paused", "disabled", "error"
    description: str = ""
    version: str = "1.0.0"
    capabilities: List[str] = Field(default_factory=list)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIAgentRun(BaseModel):
    id: str
    agent_id: str
    workspace_id: Optional[str] = None
    run_type: str = "scheduled"  # "scheduled", "ingestion_stream", "ad_hoc_batch", "manual"
    status: str = "completed"  # "pending", "running", "completed", "failed"
    trigger_source: str = "system"
    items_processed: int = 0
    items_valid: int = 0
    items_warning: int = 0
    items_needs_review: int = 0
    items_rejected: int = 0
    avg_quality_score: float = 100.0
    gemini_calls_count: int = 0
    execution_time_ms: float = 0.0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIAgentMemory(BaseModel):
    id: str
    agent_id: str
    memory_type: str  # "missing_fields_pattern", "provider_formatting", "duplicate_pattern", "category_anomaly", "reliability_score"
    memory_key: str
    memory_value: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 1.0
    occurrence_count: int = 1
    last_observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIAgentMemoryEvent(BaseModel):
    id: str
    agent_id: str
    memory_id: str
    event_type: str  # "created", "updated", "decayed", "invalidated", "reinforced"
    old_value: Optional[Dict[str, Any]] = None
    new_value: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    trigger_run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DataQualityRuleViolation(BaseModel):
    field: str
    rule_name: str
    severity: str  # "critical", "warning", "info"
    message: str
    observed_value: Any = None
    penalty_score: float = 0.0

class DataQualityValidationResult(BaseModel):
    id: str
    agent_id: str = "agent_data_quality"
    run_id: Optional[str] = None
    workspace_id: Optional[str] = None
    platform: str
    source_provider: str = "direct"
    platform_product_id: str
    unified_product_id: Optional[str] = None
    product_title: str
    product_name: Optional[str] = None
    original_category: Optional[str] = None
    normalized_category: str = "Unknown"
    data_quality_category: str = ""
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    currency: str = "PKR"
    rating: Optional[float] = None
    review_count: int = 0
    availability: bool = True
    overall_score: float = 100.0
    quality_score: float = 100.0
    classification: str = "valid"  # "valid", "valid_with_warnings", "needs_review", "rejected"
    is_trusted: bool = True
    issues: List[DataQualityRuleViolation] = Field(default_factory=list)
    warnings: List[DataQualityRuleViolation] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    invalid_fields: List[str] = Field(default_factory=list)
    suspicious_fields: List[str] = Field(default_factory=list)
    field_scores: Dict[str, float] = Field(default_factory=dict)
    raw_payload_hash: Optional[str] = None
    used_llm: bool = False
    llm_used: bool = False
    llm_provider: Optional[str] = "gemini"
    llm_resolution: Optional[Dict[str, Any]] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    validated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PublicDataQualityItem(BaseModel):
    id: str
    product_id: str = ""
    product_name: str
    platform: str
    provider: str
    data_quality_category: str = ""

    original_category: Optional[str] = None
    normalized_category: str = "Unknown"
    price: Optional[float] = None
    currency: str = "PKR"
    rating: Optional[float] = None
    review_count: int = 0
    availability: bool = True
    image: Optional[str] = None
    product_url: Optional[str] = None
    quality_score: float = 100.0
    classification: str = "valid"
    public_status: str = "Real Data"  # "Real Data", "Real Data With Warnings", "Needs Review", "Rejected By Data Quality Checks"
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    invalid_fields: List[str] = Field(default_factory=list)
    suspicious_fields: List[str] = Field(default_factory=list)
    llm_used: bool = False
    last_validated_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PublicDataQualityFeedResponse(BaseModel):
    items: List[PublicDataQualityItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1

class PublicDataQualityStatsResponse(BaseModel):
    total_inspected: int = 0
    total_rejected: int = 0
    total_warnings: int = 0
    total_valid: int = 0
    rejection_rate: float = 0.0
    clean_rate: float = 0.0
    average_quality_score: float = 100.0
    top_rejection_reasons: List[Dict[str, Any]] = Field(default_factory=list)
    platform_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    category_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaxonomyCategory(BaseModel):
    id: str
    parent_id: Optional[str] = None
    name: str
    slug: str
    level: int = 1  # 1=Category, 2=Subcategory, 3=Group, 4=Product Type
    description: str = ""
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    product_count: int = 0
    children: List["TaxonomyCategory"] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductTaxonomyAssignment(BaseModel):
    id: str
    unified_product_id: str
    category: str
    subcategory: str = "Unknown"
    product_type: str = "Unknown"
    taxonomy_path: List[str] = Field(default_factory=list)
    brand: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    classification_method: str = "keyword_rule"  # "exact_marketplace_map", "brand_rule", "keyword_rule", "memory", "llm", "unknown"
    needs_review: bool = False
    agent_id: str = "agent_categorization"
    agent_run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductTaxonomyCandidate(BaseModel):
    id: str
    product_id: str
    unified_product_id: Optional[str] = None
    candidate_category: str
    candidate_subcategory: str
    candidate_product_type: str
    confidence: float = 0.5
    reason: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductSignature(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    product_type: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    currency: Optional[str] = None
    normalized_title: str = ""
    cleaned_tokens: List[str] = Field(default_factory=list)
    key_attributes: Dict[str, Any] = Field(default_factory=dict)
    identifiers: Dict[str, Any] = Field(default_factory=dict)
    signature_hash: str = ""

class ProductMatchDecision(BaseModel):
    id: str
    product_a_id: str
    product_b_id: Optional[str] = None
    unified_product_id: Optional[str] = None
    platform_a: str = "unknown"
    platform_b: Optional[str] = None
    decision: str = "NO_MATCH"  # EXACT_MATCH, HIGH_CONFIDENCE_MATCH, PROBABLE_MATCH, VARIANT, RELATED_PRODUCT, NO_MATCH, NEEDS_REVIEW
    confidence: float = 0.0
    match_method: str = "signature_rule"
    reasons: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    variant_attributes: Dict[str, Any] = Field(default_factory=dict)
    base_product_id: Optional[str] = None
    llm_used: bool = False
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    agent_id: str = "agent_entity_matching"
    agent_run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============================================================================
# AGENT 4: TREND DETECTION & SIGNAL DISCOVERY DOMAIN MODELS
# ============================================================================

class TrendObservation(BaseModel):
    id: str
    unified_product_id: str
    platform: str
    metric_type: str  # price, rating, review_count, inventory, availability, platform_presence, discount, category_position
    metric_value: float
    previous_value: Optional[float] = None
    change_value: Optional[float] = None
    change_percent: Optional[float] = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "marketplace_sync"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrendSignal(BaseModel):
    id: str
    unified_product_id: str
    signal_type: str  # demand_surge, price_drop, price_increase, large_discount, price_volatility, rating_momentum, review_momentum, inventory_change, out_of_stock, restocked, cross_platform_surge, breakout_candidate, emerging_product, declining_product, unusual_activity
    signal_strength: float = 0.0  # 0.0 to 100.0
    confidence: float = 0.0  # 0.0 to 1.0
    direction: str = "stable"  # up, down, stable, volatile, unknown
    severity: str = "medium"  # low, medium, high, critical
    status: str = "active"  # active, resolved, dismissed, insufficient_data
    evidence: Dict[str, Any] = Field(default_factory=dict)
    platforms: List[str] = Field(default_factory=list)
    fingerprint: str = ""
    llm_used: bool = False
    llm_explanation: Optional[str] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrendSignalCandidate(BaseModel):
    id: str
    unified_product_id: str
    candidate_type: str = "breakout_candidate"  # breakout_candidate, emerging_product, unusual_activity, low_confidence_signal
    composite_score: float = 0.0
    confidence: float = 0.0
    status: str = "pending_review"  # pending_review, confirmed, rejected, auto_promoted
    reasons: List[str] = Field(default_factory=list)
    supporting_signals: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrendDetectionAudit(BaseModel):
    id: str
    agent_id: str = "agent_trend_detection"
    run_id: Optional[str] = None
    product_id: str
    signal_id: Optional[str] = None
    detection_method: str = "deterministic_rules"  # deterministic_rules, composite_scoring, selective_gemini_reasoning, memory_recall
    rule_name: Optional[str] = None
    confidence: float = 0.0
    evidence: Dict[str, Any] = Field(default_factory=dict)
    decision: str = "active"
    llm_used: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrendScoreBreakdown(BaseModel):
    demand_review_score: float = 0.0  # weight: 35%
    price_health_score: float = 0.0   # weight: 20%
    cross_platform_score: float = 0.0 # weight: 20%
    inventory_health_score: float = 0.0 # weight: 15%
    freshness_confidence_score: float = 0.0 # weight: 10%
    total_trend_score: float = 0.0    # 0.0 to 100.0
    trend_state: str = "insufficient_data"  # breakout, accelerating, emerging, stable, declining, insufficient_data


class ProductTrendSummary(BaseModel):
    unified_product_id: str
    canonical_name: str
    brand: Optional[str] = None
    category: str = "Unknown"
    platforms: List[str] = Field(default_factory=list)
    trend_score: float = 0.0
    trend_state: str = "insufficient_data"
    confidence: float = 0.0
    freshness_status: str = "insufficient_data"  # fresh, recent, stale, insufficient_data
    active_signals: List[TrendSignal] = Field(default_factory=list)
    score_breakdown: TrendScoreBreakdown = Field(default_factory=TrendScoreBreakdown)
    recent_observations: List[TrendObservation] = Field(default_factory=list)
    last_analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentTrendDetectionStats(BaseModel):
    total_analyzed_products: int = 0
    total_signals_detected: int = 0
    active_signals_count: int = 0
    breakout_candidates_count: int = 0
    gemini_invocations_count: int = 0
    signals_by_type: Dict[str, int] = Field(default_factory=dict)
    signals_by_direction: Dict[str, int] = Field(default_factory=dict)
    signals_by_severity: Dict[str, int] = Field(default_factory=dict)
    platform_breakdown: Dict[str, int] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# AGENT 5: ANOMALY DETECTION AGENT DOMAIN MODELS
# ============================================================================

class AnomalyObservation(BaseModel):
    id: str
    unified_product_id: str
    platform: str
    metric_type: str  # price, rating, review_count, availability, discount, inventory
    metric_value: float
    previous_value: Optional[float] = None
    change_value: Optional[float] = None
    change_percent: Optional[float] = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "marketplace_sync"
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnomalyDetection(BaseModel):
    id: str
    unified_product_id: str
    anomaly_type: str  # price_spike, price_crash, unusual_discount, rating_jump, rating_drop, review_velocity_spike, review_velocity_drop, availability_change, inventory_anomaly, cross_platform_price_anomaly, platform_presence_anomaly, category_activity_anomaly, provider_data_anomaly, unusual_activity
    severity: str = "medium"  # low, medium, high, critical
    score: float = 50.0  # 0.0 to 100.0
    confidence: float = 0.85  # 0.0 to 1.0
    baseline: Optional[float] = None
    observed_value: Optional[float] = None
    deviation: Optional[float] = None
    deviation_percent: Optional[float] = None
    baseline_method: str = "rolling_median"  # rolling_mean, rolling_median, std_dev, mad, category_baseline, platform_baseline, cross_platform
    evidence: Dict[str, Any] = Field(default_factory=dict)
    platforms: List[str] = Field(default_factory=list)
    provider: Optional[str] = None
    fingerprint: Optional[str] = None
    status: str = "active"  # active, resolved, suppressed, false_positive
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnomalyCandidate(BaseModel):
    id: str
    unified_product_id: str
    anomaly_id: Optional[str] = None
    candidate_type: str
    composite_score: float = 50.0
    confidence: float = 0.85
    status: str = "pending_review"  # pending_review, confirmed, dismissed, false_positive, auto_promoted
    reasons: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnomalyDetectionAudit(BaseModel):
    id: str
    agent_id: str = "agent_anomaly_detection"
    run_id: Optional[str] = None
    anomaly_id: Optional[str] = None
    product_id: str
    detection_method: str = "statistical_baseline"  # statistical_baseline, percentage_deviation, mad_threshold, cross_platform_comparison, provider_health_check, selective_gemini
    rule_name: Optional[str] = None
    confidence: float = 1.0
    evidence: Dict[str, Any] = Field(default_factory=dict)
    decision: str = "anomaly_detected"  # anomaly_detected, normal_variance, insufficient_data, false_positive_suppressed
    llm_used: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnomalyScoreBreakdown(BaseModel):
    deviation_magnitude_score: float = 0.0   # weight: 35%
    historical_consistency_score: float = 0.0 # weight: 25%
    data_freshness_score: float = 0.0        # weight: 15%
    baseline_quality_score: float = 0.0      # weight: 15%
    cross_platform_score: float = 0.0        # weight: 10%
    total_anomaly_score: float = 0.0         # 0.0 to 100.0
    status: str = "insufficient_data"        # active, normal, insufficient_data


class ProductAnomalySummary(BaseModel):
    unified_product_id: str
    canonical_name: str
    brand: Optional[str] = None
    category: str = "Unknown"
    platforms: List[str] = Field(default_factory=list)
    anomaly_score: float = 0.0
    status: str = "insufficient_data"  # anomaly_detected, normal, insufficient_data
    confidence: float = 0.0
    freshness_status: str = "insufficient_data"
    active_anomalies: List[AnomalyDetection] = Field(default_factory=list)
    score_breakdown: AnomalyScoreBreakdown = Field(default_factory=AnomalyScoreBreakdown)
    recent_observations: List[AnomalyObservation] = Field(default_factory=list)
    last_analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentAnomalyDetectionStats(BaseModel):
    total_analyzed_products: int = 0
    total_anomalies_detected: int = 0
    active_anomalies_count: int = 0
    critical_anomalies_count: int = 0
    high_severity_count: int = 0
    candidates_pending_review: int = 0
    false_positives_count: int = 0
    anomalies_by_type: Dict[str, int] = Field(default_factory=dict)
    anomalies_by_severity: Dict[str, int] = Field(default_factory=dict)
    anomalies_by_platform: Dict[str, int] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# AGENT 06: RECOMMENDATION & PRODUCT INTELLIGENCE AGENT DOMAIN MODELS
# ============================================================================

class ProductRecommendation(BaseModel):
    id: str
    unified_product_id: str
    target_product_id: Optional[str] = None
    recommendation_type: str  # similar_product, alternative_product, better_price, trending_product, high_quality, cross_platform, category_recommendation, rising_product, opportunity, best_value
    score: float = 50.0       # 0.0 to 100.0
    confidence: float = 0.85  # 0.0 to 1.0
    reasons: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    source_agents: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    platforms: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    brand: Optional[str] = None
    fingerprint: Optional[str] = None
    status: str = "active"    # active, archived, dismissed, expired
    freshness_status: str = "fresh"  # fresh, recent, stale, insufficient_data
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class RecommendationCandidate(BaseModel):
    id: str
    unified_product_id: str
    target_product_id: Optional[str] = None
    candidate_type: str
    composite_score: float = 50.0
    confidence: float = 0.85
    status: str = "pending"   # pending, approved, dismissed, rejected
    reasons: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    source_agents: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecommendationInteraction(BaseModel):
    id: str
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    product_id: str
    interaction_type: str  # view, click, save, dismiss, compare, external_link_click
    metadata: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecommendationAudit(BaseModel):
    id: str
    agent_id: str = "agent_recommendation_engine"
    run_id: str
    recommendation_id: Optional[str] = None
    product_id: str
    decision: str  # generated, candidate_queued, quality_rejected, anomaly_blocked, insufficient_data
    score: float = 50.0
    confidence: float = 1.0
    evidence: Dict[str, Any] = Field(default_factory=dict)
    source_agents: List[str] = Field(default_factory=list)
    llm_used: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecommendationScoreBreakdown(BaseModel):
    data_quality_score: float = 0.0       # weight: 15%
    product_similarity_score: float = 0.0 # weight: 20%
    price_value_score: float = 0.0        # weight: 20%
    rating_quality_score: float = 0.0     # weight: 15%
    trend_strength_score: float = 0.0     # weight: 15%
    availability_score: float = 0.0       # weight: 5%
    cross_platform_score: float = 0.0     # weight: 5%
    freshness_score: float = 0.0          # weight: 5%
    total_recommendation_score: float = 0.0  # 0.0 to 100.0
    eligibility_status: str = "eligible"  # eligible, quality_gated, anomaly_blocked, insufficient_data


class ProductRecommendationSummary(BaseModel):
    unified_product_id: str
    canonical_name: str
    brand: Optional[str] = None
    category: str = "Unknown"
    platforms: List[str] = Field(default_factory=list)
    recommendation_score: float = 0.0
    status: str = "ready"  # ready, quality_gated, anomaly_blocked, insufficient_data
    confidence: float = 0.0
    freshness_status: str = "fresh"
    recommendations: List[ProductRecommendation] = Field(default_factory=list)
    score_breakdown: RecommendationScoreBreakdown = Field(default_factory=RecommendationScoreBreakdown)
    warnings: List[str] = Field(default_factory=list)
    last_generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentRecommendationStats(BaseModel):
    total_recommendations: int = 0
    active_recommendations_count: int = 0
    best_value_count: int = 0
    trending_recommendations_count: int = 0
    cross_platform_count: int = 0
    candidates_pending_review: int = 0
    total_interactions_logged: int = 0
    recommendations_by_type: Dict[str, int] = Field(default_factory=dict)
    recommendations_by_category: Dict[str, int] = Field(default_factory=dict)
    interactions_by_type: Dict[str, int] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# AGENT 07: MARKET OPPORTUNITY INTELLIGENCE AGENT MODELS
# ============================================================================

class MarketOpportunity(BaseModel):
    id: str
    unified_product_id: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    opportunity_type: str  # product_gap, price_opportunity, category_opportunity, competitive_gap, cross_platform_gap, availability_opportunity, quality_gap, rising_category, rising_product, marketplace_expansion, underserved_category, product_launch_opportunity
    score: float = 50.0   # 0.0 to 100.0
    confidence: float = 0.85 # 0.0 to 1.0
    status: str = "active" # active, archived, dismissed, insufficient_data, quality_gated, anomaly_blocked
    reasons: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    source_agent_ids: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    current_platforms: List[str] = Field(default_factory=list)
    missing_observed_platforms: List[str] = Field(default_factory=list)
    fingerprint: Optional[str] = None
    data_freshness: str = "fresh" # fresh, recent, stale, insufficient_data
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class MarketOpportunityCandidate(BaseModel):
    id: str
    unified_product_id: Optional[str] = None
    category: Optional[str] = None
    candidate_type: str
    composite_score: float = 50.0
    confidence: float = 0.85
    status: str = "pending" # pending, approved, dismissed, rejected
    reasons: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    source_agent_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MarketOpportunityAudit(BaseModel):
    id: str
    agent_id: str = "agent_market_opportunity_intelligence"
    run_id: str
    opportunity_id: Optional[str] = None
    rule_name: str
    decision: str # generated, candidate_queued, quality_rejected, anomaly_blocked, insufficient_data
    score: float = 50.0
    confidence: float = 1.0
    evidence: Dict[str, Any] = Field(default_factory=dict)
    source_agent_ids: List[str] = Field(default_factory=list)
    llm_used: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MarketOpportunityScoreBreakdown(BaseModel):
    evidence_strength_score: float = 0.0      # weight: 25%
    trend_strength_score: float = 0.0         # weight: 20%
    market_coverage_gap_score: float = 0.0    # weight: 15%
    price_opportunity_score: float = 0.0      # weight: 15%
    product_quality_score: float = 0.0        # weight: 10%
    cross_platform_evidence_score: float = 0.0# weight: 10%
    freshness_score: float = 0.0              # weight: 5%
    total_opportunity_score: float = 0.0      # 0.0 to 100.0
    eligibility_status: str = "eligible"      # eligible, quality_gated, anomaly_blocked, insufficient_data


class MarketOpportunitySummary(BaseModel):
    target_id: str
    target_type: str = "product" # product, category, market
    name: str = "Unknown"
    category: Optional[str] = None
    status: str = "ready" # ready, quality_gated, anomaly_blocked, insufficient_data
    opportunity_score: float = 0.0
    confidence: float = 0.0
    data_freshness: str = "fresh"
    opportunities: List[MarketOpportunity] = Field(default_factory=list)
    score_breakdown: MarketOpportunityScoreBreakdown = Field(default_factory=MarketOpportunityScoreBreakdown)
    warnings: List[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMarketOpportunityStats(BaseModel):
    total_opportunities: int = 0
    active_opportunities_count: int = 0
    high_confidence_count: int = 0
    high_score_count: int = 0
    pending_review_count: int = 0
    confirmed_count: int = 0
    dismissed_count: int = 0
    opportunities_by_type: Dict[str, int] = Field(default_factory=dict)
    opportunities_by_category: Dict[str, int] = Field(default_factory=dict)
    opportunities_by_platform: Dict[str, int] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScraperCrawlJob(BaseModel):
    id: str
    marketplace: str = "daraz"  # daraz, amazon, ebay, aliexpress, shopify
    trigger_type: str = "manual"  # manual, scheduled, source_sync
    keywords: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    category_id: Optional[str] = None
    target_count: int = 10
    max_workers: int = 2
    status: str = "queued"  # queued, running, paused, completed, failed, cancelled, completed_with_challenges
    products_fetched: int = 0
    products_persisted: int = 0
    products_rejected: int = 0
    challenged_count: int = 0
    failed_count: int = 0
    current_throughput: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RawScrapedPayload(BaseModel):
    id: str
    marketplace: str = "daraz"
    product_id: str
    crawl_job_id: Optional[str] = None
    source_url: str
    canonical_url: Optional[str] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    normalized_payload: Dict[str, Any] = Field(default_factory=dict)
    parser_version: str = "1.0.0"
    extraction_status: str = "complete"  # complete, partial, invalid, challenge, not_found
    quality_status: str = "valid"  # valid, warning, needs_review, rejected
    confidence_score: float = 1.0
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScraperMarketplaceHealth(BaseModel):
    marketplace: str
    status: str = "healthy"  # healthy, degraded, rate_limited, challenged, offline
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    challenge_count: int = 0
    average_latency_ms: float = 0.0
    last_scraped_at: Optional[datetime] = None
    last_challenge_at: Optional[datetime] = None


# ==============================================================================
# Phase 3: Canonical Market Intelligence & Social Demand Domain Models
# ==============================================================================

class MarketScoreBreakdown(BaseModel):
    demand_component: float = 0.0
    growth_component: float = 0.0
    marketplace_acclaim_component: float = 0.0
    price_health_component: float = 0.0
    cross_platform_component: float = 0.0
    total_score: float = 0.0
    weights: Dict[str, float] = Field(default_factory=lambda: {
        "demand": 0.30,
        "growth": 0.20,
        "acclaim": 0.20,
        "price_health": 0.15,
        "cross_platform": 0.15
    })
    confidence: float = 0.0
    data_quality_score: float = 0.0
    history_status: str = "insufficient_history"
    calculation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DemandSignalEvaluation(BaseModel):
    demand_score: float = 0.0
    demand_level: str = "LOW"  # LOW, MEDIUM, HIGH, VERY_HIGH
    demand_trend: str = "stable"  # rising, stable, declining
    confidence: float = 0.0
    contributors: List[str] = Field(default_factory=list)

class TrendVelocityEvaluation(BaseModel):
    velocity: Optional[float] = None
    window_days: Optional[float] = None
    status: str = "insufficient_data"  # calculated, insufficient_data
    observation_count: int = 0

class GrowthEvaluation(BaseModel):
    growth_7d: Optional[float] = None
    growth_30d: Optional[float] = None
    window_days: Optional[float] = None
    status: str = "insufficient_data"  # calculated, insufficient_data
    observation_count: int = 0

class ViralPotentialEvaluation(BaseModel):
    viral_score: Optional[float] = None
    viral_level: str = "unavailable"  # unavailable, Low, Moderate, High, Very High
    confidence: float = 0.0
    has_social_signals: bool = False
    supporting_signals: List[str] = Field(default_factory=list)

class ProductOpportunityEvaluation(BaseModel):
    opportunity_score: float = 0.0
    opportunity_level: str = "Low"  # Low, Moderate, High, Exceptional
    confidence: float = 0.0
    competition_level: str = "unavailable"  # unavailable, Low, Moderate, High
    reasoning: List[str] = Field(default_factory=list)
    supporting_signals: List[str] = Field(default_factory=list)

class SocialSignal(BaseModel):
    id: str
    platform: str  # YouTube, TikTok, Instagram, X, Facebook
    external_id: Optional[str] = None
    content_title: str
    content_url: Optional[str] = None
    author_name: Optional[str] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: float = 0.0
    matched_product_id: Optional[str] = None
    matched_unified_id: Optional[str] = None
    match_confidence: float = 0.0
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MarketIntelligenceSnapshot(BaseModel):
    id: str
    product_id: str
    unified_product_id: Optional[str] = None
    marketplace: str
    category: Optional[str] = None
    current_price: float = 0.0
    historical_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    currency: str = "USD"
    rating: float = 0.0
    review_count: int = 0
    availability: bool = True
    market_score: float = 0.0
    market_score_breakdown: Optional[Dict[str, Any]] = None
    demand_score: float = 0.0
    demand_level: str = "LOW"
    trend_velocity: Optional[float] = None
    growth_7d: Optional[float] = None
    growth_30d: Optional[float] = None
    viral_score: Optional[float] = None
    viral_level: str = "unavailable"
    opportunity_score: float = 0.0
    opportunity_level: str = "Low"
    social_mentions_count: int = 0
    social_total_views: int = 0
    social_total_engagement: int = 0
    confidence_score: float = 0.0
    data_quality_score: float = 0.0
    source_provenance: str = "marketplace"
    ai_summary: Optional[str] = None
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Canonical Marketplace Search Architecture (Phase 1)
from backend.app.services.scraper.marketplace_search import (
    MarketplaceType,
    MarketplaceSearchStatus,
    SearchProviderName,
    MarketplaceSearchRequest,
    MarketplaceSearchCandidate,
    MarketplaceSearchResult,
    MIN_CANDIDATES,
    DEFAULT_CANDIDATE_TARGET,
    DEFAULT_RESULT_LIMIT,
    MAX_RESULT_LIMIT,
)















