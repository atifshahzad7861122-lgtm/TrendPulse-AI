from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

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
    trend_score: float
    growth_rate: float
    volume: int
    velocity_label: str  # "Breakout", "Surging", "Steady", "Explosive"
    status: str = "Active"  # "Active", "Watching", "Saturated"
    price_range: str
    primary_platform: str
    platforms: List[str]
    platform_shares: Dict[str, float] = Field(default_factory=dict)
    historical_scores: List[Dict[str, Any]] = Field(default_factory=list)
    historical_prices: List[Dict[str, Any]] = Field(default_factory=list)
    ai_summary: str = ""
    signals_count: int = 0
    sentiment_score: float = 0.8
    image_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_watchlisted: bool = False
    raw_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Category(BaseModel):
    id: str
    name: str
    slug: str
    product_count: int
    avg_trend_score: float
    growth_rate: float
    velocity_label: str
    description: Optional[str] = None
    subcategories: List[str] = Field(default_factory=list)
    top_platforms: List[str] = Field(default_factory=list)
    top_driver: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



class PlatformMetrics(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    total_signals: int
    active_trends: int
    velocity_growth: float
    market_share: float
    status: str = "Connected"
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
    total_signals_analyzed: int
    high_conviction_count: int
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

