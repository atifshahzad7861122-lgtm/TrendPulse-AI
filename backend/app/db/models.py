from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, DateTime, Text, JSON, ForeignKey, Table
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

