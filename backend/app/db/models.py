from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, DateTime, Text, JSON, ForeignKey, Table, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), default="Administrator", nullable=False)
    verification_token = Column(String(255), nullable=True, index=True)
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    workspace_id = Column(String(64), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), default="General", nullable=False)
    use_case = Column(String(100), default="Competitor Tracking", nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    default_dashboard = Column(String(50), default="signals", nullable=False)
    connected_sources = Column(JSON, default=list, nullable=False)
    is_setup_complete = Column(Boolean, default=False, nullable=False)
    owner_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class WorkspaceMemberModel(Base):
    __tablename__ = "workspace_members"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(50), default="Administrator", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(255), nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class EmailVerificationModel(Base):
    __tablename__ = "email_verifications"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class LoginEventModel(Base):
    __tablename__ = "login_events"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(255), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class UserSettingsModel(Base):
    __tablename__ = "user_settings"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False, default="")
    email = Column(String(255), nullable=False, default="")
    avatar_url = Column(String(512), nullable=True)
    role = Column(String(50), default="Administrator", nullable=False)
    company_name = Column(String(255), default="TrendPulse Global Intelligence", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    email_notifications = Column(Boolean, default=True, nullable=False)
    alert_critical_only = Column(Boolean, default=False, nullable=False)
    weekly_digest = Column(Boolean, default=True, nullable=False)
    ai_model_preference = Column(String(100), default="Qwen 2.5 Max (Simulated)", nullable=False)
    ai_confidence_threshold = Column(Integer, default=80, nullable=False)
    auto_generate_reports = Column(Boolean, default=False, nullable=False)
    dark_mode = Column(Boolean, default=True, nullable=False)
    table_dense_view = Column(Boolean, default=False, nullable=False)
    live_ticker_enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

# Backward-compatibility alias
SettingsModel = UserSettingsModel

class ProductModel(Base):
    __tablename__ = "products"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    sub_category = Column(String(100), nullable=True)
    trend_score = Column(Float, default=50.0, nullable=False, index=True)
    growth_rate = Column(Float, default=0.0, nullable=False)
    volume = Column(Integer, default=0, nullable=False)
    velocity_label = Column(String(50), default="Steady", nullable=False)
    status = Column(String(50), default="Active", nullable=False)
    price_range = Column(String(50), default="$25 - $50", nullable=False)
    primary_platform = Column(String(50), default="TikTok", nullable=False)
    platforms = Column(JSON, default=list, nullable=False)
    platform_shares = Column(JSON, default=dict, nullable=False)
    historical_scores = Column(JSON, default=list, nullable=False)
    historical_prices = Column(JSON, default=list, nullable=False)
    ai_summary = Column(Text, default="", nullable=False)
    signals_count = Column(Integer, default=0, nullable=False)
    sentiment_score = Column(Float, default=0.8, nullable=False)
    image_url = Column(String(512), nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    is_watchlisted = Column(Boolean, default=False, nullable=False)
    raw_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class CategoryModel(Base):
    __tablename__ = "categories"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    product_count = Column(Integer, default=0, nullable=False)
    avg_trend_score = Column(Float, default=50.0, nullable=False)
    growth_rate = Column(Float, default=0.0, nullable=False)
    velocity_label = Column(String(50), default="Steady", nullable=False)
    subcategories = Column(JSON, default=list, nullable=False)
    top_driver = Column(String(255), default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class PlatformModel(Base):
    __tablename__ = "platforms"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    icon = Column(String(50), default="share", nullable=False)
    total_signals = Column(Integer, default=0, nullable=False)
    active_trends = Column(Integer, default=0, nullable=False)
    velocity_growth = Column(Float, default=0.0, nullable=False)
    market_share = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="Connected", nullable=False)
    recent_spikes = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class WatchlistModel(Base):
    __tablename__ = "watchlists"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    product_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class AlertModel(Base):
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), default="Warning", nullable=False, index=True)
    category = Column(String(100), nullable=False)
    product_id = Column(String(64), nullable=True)
    product_name = Column(String(255), nullable=True)
    platform = Column(String(50), nullable=True)
    trigger = Column(String(100), nullable=True)
    threshold = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="alert", nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    link = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ReportModel(Base):
    __tablename__ = "reports"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    template = Column(String(100), default="executive_summary", nullable=False)
    time_range = Column(String(50), default="7d", nullable=False)
    status = Column(String(50), default="ready", nullable=False)
    download_url = Column(String(512), nullable=True)
    file_size = Column(String(50), default="1.2 MB", nullable=False)
    category_focus = Column(String(100), default="All Categories", nullable=False)
    data_snapshot = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class DataSourceModel(Base):
    __tablename__ = "data_sources"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(String(50), default="Connected", nullable=False)
    health_score = Column(Integer, default=95, nullable=False)
    records_synced = Column(Integer, default=0, nullable=False)
    last_sync = Column(String(50), default="Just now", nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    icon = Column(String(50), default="database", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class SubscriptionPlanModel(Base):
    __tablename__ = "subscription_plans"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False, default="")
    price = Column(Float, default=0.0, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    billing_interval = Column(String(20), default="monthly", nullable=False)
    monthly_credits = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    features = Column(JSON, default=list, nullable=False)
    limits = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class UserSubscriptionModel(Base):
    __tablename__ = "user_subscriptions"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, unique=True, index=True)
    plan_id = Column(String(64), nullable=False, index=True)
    status = Column(String(50), default="active", nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    current_period_start = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    current_period_end = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class CreditAccountModel(Base):
    __tablename__ = "credit_accounts"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, unique=True, index=True)
    current_balance = Column(Integer, default=0, nullable=False)
    lifetime_granted = Column(Integer, default=0, nullable=False)
    lifetime_used = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class CreditTransactionModel(Base):
    __tablename__ = "credit_transactions"

    id = Column(String(64), primary_key=True, index=True)
    credit_account_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(String(50), nullable=False, index=True)
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    reference_type = Column(String(100), nullable=True, index=True)
    reference_id = Column(String(255), nullable=True, index=True)
    description = Column(String(255), default="", nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

class CreditUsageModel(Base):
    __tablename__ = "credit_usage"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    credit_account_id = Column(String(64), nullable=False, index=True)
    feature = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    credits_used = Column(Integer, nullable=False)
    reference_type = Column(String(100), nullable=True, index=True)
    reference_id = Column(String(255), nullable=True, index=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

class MarketplaceProductModel(Base):
    __tablename__ = "marketplace_products"
    __table_args__ = (
        UniqueConstraint("platform", "product_id", name="uq_marketplace_products_platform_product_id"),
    )

    id = Column(String(64), primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True, default="daraz")
    product_id = Column(String(64), nullable=False, index=True)
    product_name = Column(String(512), nullable=False, index=True)
    product_url = Column(String(1024), nullable=True)
    image_url = Column(String(1024), nullable=True)
    seller_name = Column(String(255), nullable=True)
    seller_id = Column(String(64), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    price = Column(Float, default=0.0, nullable=False)
    original_price = Column(Float, default=0.0, nullable=False)
    discount_percentage = Column(Float, default=0.0, nullable=False)
    discount_label = Column(String(50), nullable=True)
    rating = Column(Float, default=0.0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    stock_status = Column(String(50), default="in_stock", nullable=False)
    in_stock = Column(Boolean, default=True, nullable=False)
    currency = Column(String(10), default="PKR", nullable=False)
    location = Column(String(100), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    raw_source_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ProductMarketSnapshotModel(Base):
    __tablename__ = "product_market_snapshots"

    id = Column(String(64), primary_key=True, index=True)
    product_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True, default="daraz")
    price = Column(Float, default=0.0, nullable=False)
    original_price = Column(Float, default=0.0, nullable=False)
    discount = Column(Float, default=0.0, nullable=False)
    rating = Column(Float, default=0.0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    stock_status = Column(String(50), default="in_stock", nullable=False)
    observed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ShopifyProductModel(Base):
    __tablename__ = "shopify_products"
    __table_args__ = (
        UniqueConstraint("store_domain", "product_id", name="uq_shopify_products_store_product_id"),
    )

    id = Column(String(64), primary_key=True, index=True)
    store_domain = Column(String(255), nullable=False, index=True)
    product_id = Column(String(64), nullable=False, index=True)
    title = Column(String(512), nullable=False, index=True)
    handle = Column(String(255), nullable=True)
    product_url = Column(String(1024), nullable=False)
    image_url = Column(String(1024), nullable=True)
    images = Column(JSON, default=list, nullable=False)
    vendor = Column(String(255), nullable=True, index=True)
    product_type = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    tags = Column(JSON, default=list, nullable=False)
    price = Column(Float, default=0.0, nullable=False)
    compare_at_price = Column(Float, nullable=True)
    discount_percentage = Column(Float, default=0.0, nullable=False)
    discount_label = Column(String(50), nullable=True)
    currency = Column(String(10), default="USD", nullable=False)
    available = Column(Boolean, default=True, nullable=False)
    rating = Column(Float, default=0.0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    source_provider = Column(String(50), default="shopify_scout", nullable=False)
    variants_count = Column(Integer, default=1, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    raw_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ShopifyProductSnapshotModel(Base):
    __tablename__ = "shopify_product_snapshots"

    id = Column(String(64), primary_key=True, index=True)
    shopify_product_id = Column(String(64), nullable=False, index=True)
    store_domain = Column(String(255), nullable=False, index=True)
    product_id = Column(String(64), nullable=False, index=True)
    price = Column(Float, default=0.0, nullable=False)
    compare_at_price = Column(Float, nullable=True)
    available = Column(Boolean, default=True, nullable=False)
    rating = Column(Float, default=0.0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    inventory_status = Column(String(50), default="in_stock", nullable=False)
    source_provider = Column(String(50), default="shopify_scout", nullable=False)
    observed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    raw_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ShopifyProviderHealthModel(Base):
    __tablename__ = "shopify_provider_health"

    id = Column(String(64), primary_key=True, index=True)
    provider_name = Column(String(50), unique=True, nullable=False, index=True)
    priority = Column(Integer, nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="healthy", nullable=False, index=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    total_requests = Column(Integer, default=0, nullable=False)
    successful_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    rate_limited_requests = Column(Integer, default=0, nullable=False)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    cooldown_until = Column(DateTime(timezone=True), nullable=True, index=True)
    last_error_code = Column(Integer, nullable=True)
    last_error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ShopifySyncRunModel(Base):
    __tablename__ = "shopify_sync_runs"

    id = Column(String(64), primary_key=True, index=True)
    store_domain = Column(String(255), nullable=False, index=True)
    provider_name = Column(String(50), nullable=False, index=True)
    status = Column(String(50), default="success", nullable=False, index=True)
    products_fetched = Column(Integer, default=0, nullable=False)
    products_inserted = Column(Integer, default=0, nullable=False)
    products_updated = Column(Integer, default=0, nullable=False)
    snapshots_created = Column(Integer, default=0, nullable=False)
    provider_attempts = Column(JSON, default=list, nullable=False)
    error_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class UnifiedProductModel(Base):
    __tablename__ = "unified_products"

    id = Column(String(64), primary_key=True, index=True)
    unified_product_id = Column(String(64), unique=True, nullable=False, index=True)
    canonical_name = Column(String(500), nullable=False, index=True)
    normalized_name = Column(String(500), nullable=False, index=True)
    brand = Column(String(255), nullable=True, index=True)
    category = Column(String(255), nullable=True, index=True)
    subcategory = Column(String(255), nullable=True)
    product_type = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    primary_image = Column(Text, nullable=True)
    identifiers = Column(JSON, default=dict, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ProductPlatformListingModel(Base):
    __tablename__ = "product_platform_listings"
    __table_args__ = (
        UniqueConstraint("platform", "platform_product_id", "store_domain", name="uq_listing_platform_prod_store"),
    )

    id = Column(String(64), primary_key=True, index=True)
    unified_product_id = Column(String(64), ForeignKey("unified_products.unified_product_id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    platform_product_id = Column(String(100), nullable=False, index=True)
    store_domain = Column(String(255), nullable=True, index=True)
    product_url = Column(Text, nullable=False)
    title = Column(String(500), nullable=False)
    normalized_title = Column(String(500), nullable=False, index=True)
    price = Column(Float, default=0.0, nullable=False, index=True)
    original_price = Column(Float, nullable=True)
    currency = Column(String(10), default="USD", nullable=False)
    discount_percentage = Column(Float, default=0.0, nullable=False)
    discount_label = Column(String(50), nullable=True)
    seller_name = Column(String(255), nullable=True)
    vendor = Column(String(255), nullable=True)
    rating = Column(Float, default=0.0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    available = Column(Boolean, default=True, nullable=False)
    image_url = Column(Text, nullable=True)
    source_provider = Column(String(50), default="direct", nullable=False)
    last_synced_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    completeness_score = Column(Float, default=1.0, nullable=False)
    raw_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ProductMatchCandidateModel(Base):
    __tablename__ = "product_match_candidates"

    id = Column(String(64), primary_key=True, index=True)
    unified_product_id = Column(String(64), ForeignKey("unified_products.unified_product_id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_unified_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    platform_product_id = Column(String(100), nullable=False, index=True)
    confidence_score = Column(Float, nullable=False, index=True)
    method = Column(String(50), nullable=False)
    status = Column(String(50), default="probable", nullable=False, index=True)
    reasons = Column(JSON, default=list, nullable=False)
    product_a_title = Column(Text, nullable=True)
    product_b_title = Column(Text, nullable=True)
    conflicts = Column(JSON, default=list, nullable=False)
    variant_attributes = Column(JSON, default=dict, nullable=False)
    resolved_by = Column(String(64), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ProductMatchDecisionModel(Base):
    __tablename__ = "product_match_decisions"

    id = Column(String(64), primary_key=True, index=True)
    product_a_id = Column(String(100), nullable=False, index=True)
    product_b_id = Column(String(100), nullable=True, index=True)
    unified_product_id = Column(String(64), ForeignKey("unified_products.unified_product_id", ondelete="CASCADE"), nullable=True, index=True)
    platform_a = Column(String(50), nullable=False, index=True)
    platform_b = Column(String(50), nullable=True, index=True)
    decision = Column(String(50), default="NO_MATCH", nullable=False, index=True)
    confidence = Column(Float, default=0.0, nullable=False, index=True)
    match_method = Column(String(50), default="signature_rule", nullable=False, index=True)
    reasons = Column(JSON, default=list, nullable=False)
    conflicts = Column(JSON, default=list, nullable=False)
    variant_attributes = Column(JSON, default=dict, nullable=False)
    base_product_id = Column(String(64), nullable=True)
    llm_used = Column(Boolean, default=False, nullable=False)
    llm_provider = Column(String(50), nullable=True)
    llm_model = Column(String(50), nullable=True)
    agent_id = Column(String(64), ForeignKey("ai_agents.id", ondelete="CASCADE"), default="agent_entity_matching", nullable=False, index=True)
    agent_run_id = Column(String(64), ForeignKey("ai_agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    details = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ProductMatchAuditModel(Base):
    __tablename__ = "product_match_audit"

    id = Column(String(64), primary_key=True, index=True)
    unified_product_id = Column(String(64), ForeignKey("unified_products.unified_product_id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    platform_product_id = Column(String(100), nullable=False, index=True)
    matching_method = Column(String(50), nullable=False)
    matching_confidence = Column(Float, nullable=False)
    matched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    details = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class LLMUsageRecordModel(Base):
    __tablename__ = "llm_usage_records"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    request_type = Column(String(50), nullable=False, index=True)
    prompt_version = Column(String(20), default="v1", nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost = Column(Float, default=0.0, nullable=False)
    latency_ms = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="success", nullable=False, index=True)
    error_code = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

class AIAgentModel(Base):
    __tablename__ = "ai_agents"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    agent_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), default="active", nullable=False, index=True)
    description = Column(Text, default="", nullable=False)
    version = Column(String(20), default="1.0.0", nullable=False)
    capabilities = Column(JSON, default=list, nullable=False)
    configuration = Column(JSON, default=dict, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class AIAgentRunModel(Base):
    __tablename__ = "ai_agent_runs"

    id = Column(String(64), primary_key=True, index=True)
    agent_id = Column(String(64), ForeignKey("ai_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    run_type = Column(String(50), default="scheduled", nullable=False)
    status = Column(String(50), default="completed", nullable=False, index=True)
    trigger_source = Column(String(100), default="system", nullable=False)
    items_processed = Column(Integer, default=0, nullable=False)
    items_valid = Column(Integer, default=0, nullable=False)
    items_warning = Column(Integer, default=0, nullable=False)
    items_needs_review = Column(Integer, default=0, nullable=False)
    items_rejected = Column(Integer, default=0, nullable=False)
    avg_quality_score = Column(Float, default=100.0, nullable=False)
    gemini_calls_count = Column(Integer, default=0, nullable=False)
    execution_time_ms = Column(Float, default=0.0, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

class AIAgentMemoryModel(Base):
    __tablename__ = "ai_agent_memory"

    id = Column(String(64), primary_key=True, index=True)
    agent_id = Column(String(64), ForeignKey("ai_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False, index=True)
    memory_key = Column(String(255), nullable=False, index=True)
    memory_value = Column(JSON, default=dict, nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    occurrence_count = Column(Integer, default=1, nullable=False)
    last_observed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("agent_id", "memory_type", "memory_key", name="uq_agent_memory_key"),
    )

class AIAgentMemoryEventModel(Base):
    __tablename__ = "ai_agent_memory_events"

    id = Column(String(64), primary_key=True, index=True)
    agent_id = Column(String(64), ForeignKey("ai_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, default=dict, nullable=False)
    reason = Column(String(512), default="", nullable=False)
    trigger_run_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

class DataQualityValidationResultModel(Base):
    __tablename__ = "data_quality_validation_results"

    id = Column(String(64), primary_key=True, index=True)
    agent_id = Column(String(64), ForeignKey("ai_agents.id", ondelete="CASCADE"), default="agent_data_quality", nullable=False, index=True)
    run_id = Column(String(64), ForeignKey("ai_agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    source_provider = Column(String(50), default="direct", nullable=False, index=True)
    platform_product_id = Column(String(100), nullable=False, index=True)
    unified_product_id = Column(String(64), nullable=True, index=True)
    product_title = Column(String(512), nullable=False)
    product_name = Column(String(512), nullable=True)
    original_category = Column(String(255), nullable=True)
    normalized_category = Column(String(255), default="Unknown", nullable=False, index=True)
    data_quality_category = Column(String(255), default="", nullable=False)
    product_url = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String(10), default="PKR", nullable=False)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0, nullable=False)
    availability = Column(Boolean, default=True, nullable=False)
    overall_score = Column(Float, default=100.0, nullable=False)
    quality_score = Column(Float, default=100.0, nullable=False)
    classification = Column(String(50), default="valid", nullable=False, index=True)
    is_trusted = Column(Boolean, default=True, nullable=False)
    issues = Column(JSON, default=list, nullable=False)
    warnings = Column(JSON, default=list, nullable=False)
    rejection_reasons = Column(JSON, default=list, nullable=False)
    missing_fields = Column(JSON, default=list, nullable=False)
    invalid_fields = Column(JSON, default=list, nullable=False)
    suspicious_fields = Column(JSON, default=list, nullable=False)
    field_scores = Column(JSON, default=dict, nullable=False)
    raw_payload_hash = Column(String(64), nullable=True)
    used_llm = Column(Boolean, default=False, nullable=False)
    llm_used = Column(Boolean, default=False, nullable=False)
    llm_provider = Column(String(50), default="gemini", nullable=True)
    llm_resolution = Column(JSON, nullable=True)
    raw_payload = Column(JSON, default=dict, nullable=False)
    validated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class TaxonomyCategoryModel(Base):
    __tablename__ = "taxonomy_categories"

    id = Column(String(64), primary_key=True, index=True)
    parent_id = Column(String(64), ForeignKey("taxonomy_categories.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(150), unique=True, index=True, nullable=False)
    level = Column(Integer, default=1, nullable=False, index=True)
    description = Column(Text, default="", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ProductTaxonomyAssignmentModel(Base):
    __tablename__ = "product_taxonomy_assignments"

    id = Column(String(64), primary_key=True, index=True)
    unified_product_id = Column(String(64), ForeignKey("unified_products.unified_product_id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(150), nullable=False, index=True)
    subcategory = Column(String(150), default="Unknown", nullable=False, index=True)
    product_type = Column(String(150), default="Unknown", nullable=False, index=True)
    taxonomy_path = Column(JSON, default=list, nullable=False)
    brand = Column(String(150), nullable=True, index=True)
    attributes = Column(JSON, default=dict, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False, index=True)
    classification_method = Column(String(50), default="keyword_rule", nullable=False, index=True)
    needs_review = Column(Boolean, default=False, nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("ai_agents.id", ondelete="CASCADE"), default="agent_categorization", nullable=False, index=True)
    agent_run_id = Column(String(64), ForeignKey("ai_agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ProductTaxonomyCandidateModel(Base):
    __tablename__ = "product_taxonomy_candidates"

    id = Column(String(64), primary_key=True, index=True)
    product_id = Column(String(100), nullable=False, index=True)
    unified_product_id = Column(String(64), ForeignKey("unified_products.unified_product_id", ondelete="CASCADE"), nullable=True, index=True)
    candidate_category = Column(String(150), nullable=False)
    candidate_subcategory = Column(String(150), nullable=False)
    candidate_product_type = Column(String(150), nullable=False)
    confidence = Column(Float, default=0.5, nullable=False, index=True)
    reason = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

class DarazSellerModel(Base):
    __tablename__ = "daraz_sellers"

    id = Column(String(64), primary_key=True, index=True)
    seller_id = Column(String(64), unique=True, nullable=False, index=True)
    seller_name = Column(String(255), nullable=False, index=True)
    shop_url = Column(String(1024), nullable=True)
    rating = Column(Float, default=0.0, nullable=False)
    positive_ratings_percentage = Column(Float, default=0.0, nullable=False)
    location = Column(String(100), nullable=True)
    is_official_store = Column(Boolean, default=False, nullable=False)
    total_products = Column(Integer, default=0, nullable=False)
    raw_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class DarazCategoryModel(Base):
    __tablename__ = "daraz_categories"

    id = Column(String(64), primary_key=True, index=True)
    category_id = Column(String(64), unique=True, nullable=False, index=True)
    parent_id = Column(String(64), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    level = Column(Integer, default=1, nullable=False)
    leaf = Column(Boolean, default=True, nullable=False)
    product_count = Column(Integer, default=0, nullable=False)
    raw_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class DarazReviewModel(Base):
    __tablename__ = "daraz_reviews"

    id = Column(String(64), primary_key=True, index=True)
    review_id = Column(String(64), unique=True, nullable=False, index=True)
    product_id = Column(String(64), nullable=False, index=True)
    seller_id = Column(String(64), nullable=True, index=True)
    rating = Column(Float, default=0.0, nullable=False, index=True)
    reviewer_name = Column(String(255), nullable=True)
    review_title = Column(String(512), nullable=True)
    review_content = Column(Text, nullable=True)
    verified_purchase = Column(Boolean, default=True, nullable=False)
    review_date = Column(DateTime(timezone=True), nullable=True)
    sentiment_score = Column(Float, default=0.0, nullable=False)
    raw_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class DarazIngestionRunModel(Base):
    __tablename__ = "daraz_ingestion_runs"

    id = Column(String(64), primary_key=True, index=True)
    provider_name = Column(String(50), nullable=False, index=True)
    status = Column(String(50), default="success", nullable=False, index=True)
    trigger_type = Column(String(50), default="scheduled", nullable=False)
    category = Column(String(100), nullable=True)
    search_query = Column(String(255), nullable=True)
    products_fetched = Column(Integer, default=0, nullable=False)
    products_inserted = Column(Integer, default=0, nullable=False)
    products_updated = Column(Integer, default=0, nullable=False)
    snapshots_created = Column(Integer, default=0, nullable=False)
    reviews_fetched = Column(Integer, default=0, nullable=False)
    error_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class DarazApiTelemetryModel(Base):
    __tablename__ = "daraz_api_telemetry"

    id = Column(String(64), primary_key=True, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), default="GET", nullable=False)
    provider_name = Column(String(50), default="daraz_official_open_platform", nullable=False)
    status_code = Column(Integer, nullable=False, index=True)
    latency_ms = Column(Float, default=0.0, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    request_params = Column(JSON, default=dict, nullable=False)
    response_size_bytes = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

class DarazDailyQuotaModel(Base):
    __tablename__ = "daraz_daily_quotas"

    id = Column(String(64), primary_key=True, index=True)
    date = Column(String(10), unique=True, nullable=False, index=True)
    requests_used = Column(Integer, default=0, nullable=False)
    daily_limit = Column(Integer, default=6000000, nullable=False)
    remaining = Column(Integer, default=6000000, nullable=False)
    rate_limit_hits = Column(Integer, default=0, nullable=False)
    last_request_at = Column(DateTime(timezone=True), nullable=True)
    reset_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class DarazTrainingDatasetModel(Base):
    __tablename__ = "daraz_training_dataset"

    id = Column(String(64), primary_key=True, index=True)
    product_id = Column(String(64), nullable=False, index=True)
    unified_product_id = Column(String(64), nullable=True, index=True)
    title = Column(String(512), nullable=False)
    category = Column(String(255), nullable=False, index=True)
    brand = Column(String(255), nullable=True)
    price = Column(Float, default=0.0, nullable=False)
    rating = Column(Float, default=0.0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    features = Column(JSON, default=dict, nullable=False)
    quality_score = Column(Float, default=100.0, nullable=False, index=True)
    agent_label = Column(String(100), default="clean_catalog", nullable=False)
    is_validated = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class ScraperCrawlJobModel(Base):
    __tablename__ = "scraper_crawl_jobs"

    id = Column(String(64), primary_key=True, index=True)
    marketplace = Column(String(50), default="daraz", nullable=False, index=True)
    trigger_type = Column(String(50), default="manual", nullable=False)
    keywords = Column(JSON, default=list, nullable=False)
    urls = Column(JSON, default=list, nullable=False)
    category_id = Column(String(64), nullable=True)
    target_count = Column(Integer, default=10, nullable=False)
    max_workers = Column(Integer, default=2, nullable=False)
    status = Column(String(50), default="queued", nullable=False, index=True)
    products_fetched = Column(Integer, default=0, nullable=False)
    products_persisted = Column(Integer, default=0, nullable=False)
    products_rejected = Column(Integer, default=0, nullable=False)
    challenged_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    current_throughput = Column(Float, default=0.0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class RawScrapedPayloadModel(Base):
    __tablename__ = "raw_scraped_payloads"

    id = Column(String(64), primary_key=True, index=True)
    marketplace = Column(String(50), default="daraz", nullable=False, index=True)
    product_id = Column(String(100), nullable=False, index=True)
    crawl_job_id = Column(String(64), nullable=True, index=True)
    source_url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=True)
    raw_payload = Column(JSON, default=dict, nullable=False)
    normalized_payload = Column(JSON, default=dict, nullable=False)
    parser_version = Column(String(50), default="1.0.0", nullable=False)
    extraction_status = Column(String(50), default="complete", nullable=False, index=True)
    quality_status = Column(String(50), default="valid", nullable=False, index=True)
    confidence_score = Column(Float, default=1.0, nullable=False)
    scraped_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class MarketIntelligenceSnapshotModel(Base):
    __tablename__ = "market_intelligence_snapshots"

    id = Column(String(64), primary_key=True, index=True)
    product_id = Column(String(100), nullable=False, index=True)
    unified_product_id = Column(String(64), nullable=True, index=True)
    marketplace = Column(String(50), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    current_price = Column(Float, default=0.0, nullable=False)
    historical_price = Column(Float, nullable=True)
    price_change_pct = Column(Float, nullable=True)
    currency = Column(String(10), default="USD", nullable=False)
    rating = Column(Float, default=0.0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    availability = Column(Boolean, default=True, nullable=False)
    market_score = Column(Float, default=0.0, nullable=False, index=True)
    market_score_breakdown = Column(JSON, default=dict, nullable=False)
    demand_score = Column(Float, default=0.0, nullable=False)
    demand_level = Column(String(50), default="MODERATE", nullable=False)
    trend_velocity = Column(Float, nullable=True)
    growth_7d = Column(Float, nullable=True)
    growth_30d = Column(Float, nullable=True)
    viral_score = Column(Float, nullable=True)
    viral_level = Column(String(50), default="unavailable", nullable=False)
    opportunity_score = Column(Float, default=0.0, nullable=False)
    opportunity_level = Column(String(50), default="Moderate", nullable=False)
    social_mentions_count = Column(Integer, default=0, nullable=False)
    social_total_views = Column(Integer, default=0, nullable=False)
    social_total_engagement = Column(Integer, default=0, nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    data_quality_score = Column(Float, default=80.0, nullable=False)
    source_provenance = Column(String(100), default="marketplace", nullable=False)
    ai_summary = Column(Text, nullable=True)
    calculated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class SocialSignalModel(Base):
    __tablename__ = "social_signals"

    id = Column(String(64), primary_key=True, index=True)
    platform = Column(String(50), default="YouTube", nullable=False, index=True)
    external_id = Column(String(100), nullable=True, index=True)
    content_title = Column(String(512), nullable=False)
    content_url = Column(String(1024), nullable=False)
    author_name = Column(String(255), nullable=True)
    views = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    engagement_rate = Column(Float, default=0.0, nullable=False)
    matched_product_id = Column(String(100), nullable=True, index=True)
    matched_unified_id = Column(String(64), nullable=True, index=True)
    match_confidence = Column(Float, default=0.0, nullable=False)
    observed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    raw_metadata = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)










