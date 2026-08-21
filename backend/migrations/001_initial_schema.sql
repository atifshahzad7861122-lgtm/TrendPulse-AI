-- =============================================================================
-- TrendPulse AI - Initial Production Database Schema Migration
-- Source of Truth: backend/app/db/models.py
-- Target Platform: Supabase PostgreSQL (Standard PostgreSQL 15+)
-- Version: 001_initial_schema.sql
-- =============================================================================

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    role VARCHAR(50) NOT NULL DEFAULT 'Administrator',
    verification_token VARCHAR(255),
    reset_token VARCHAR(255),
    reset_token_expires_at TIMESTAMPTZ,
    workspace_id VARCHAR(64),
    avatar_url VARCHAR(512),
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token);
CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token);

-- =============================================================================
-- 2. WORKSPACES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS workspaces (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100) NOT NULL DEFAULT 'General',
    use_case VARCHAR(100) NOT NULL DEFAULT 'Competitor Tracking',
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    default_dashboard VARCHAR(50) NOT NULL DEFAULT 'signals',
    connected_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_setup_complete BOOLEAN NOT NULL DEFAULT FALSE,
    owner_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workspaces_id ON workspaces(id);
CREATE INDEX IF NOT EXISTS idx_workspaces_owner_id ON workspaces(owner_id);

-- =============================================================================
-- 3. WORKSPACE MEMBERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS workspace_members (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'Administrator',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workspace_members_id ON workspace_members(id);
CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace_id ON workspace_members(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_members_user_id ON workspace_members(user_id);

-- =============================================================================
-- 4. USER SESSIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    ip_address VARCHAR(100),
    user_agent VARCHAR(255),
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_id ON user_sessions(id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_user_sessions_is_revoked ON user_sessions(is_revoked);

-- =============================================================================
-- 5. EMAIL VERIFICATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS email_verifications (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_verifications_id ON email_verifications(id);
CREATE INDEX IF NOT EXISTS idx_email_verifications_user_id ON email_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_email_verifications_token ON email_verifications(token);

-- =============================================================================
-- 6. PASSWORD RESET TOKENS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_id ON password_reset_tokens(id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);

-- =============================================================================
-- 7. LOGIN EVENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS login_events (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64),
    email VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    ip_address VARCHAR(100),
    user_agent VARCHAR(255),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_events_id ON login_events(id);
CREATE INDEX IF NOT EXISTS idx_login_events_user_id ON login_events(user_id);
CREATE INDEX IF NOT EXISTS idx_login_events_email ON login_events(email);
CREATE INDEX IF NOT EXISTS idx_login_events_event_type ON login_events(event_type);

-- =============================================================================
-- 8. USER SETTINGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_settings (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL DEFAULT '',
    email VARCHAR(255) NOT NULL DEFAULT '',
    avatar_url VARCHAR(512),
    role VARCHAR(50) NOT NULL DEFAULT 'Administrator',
    company_name VARCHAR(255) NOT NULL DEFAULT 'TrendPulse Global Intelligence',
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    email_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    alert_critical_only BOOLEAN NOT NULL DEFAULT FALSE,
    weekly_digest BOOLEAN NOT NULL DEFAULT TRUE,
    ai_model_preference VARCHAR(100) NOT NULL DEFAULT 'Qwen 2.5 Max (Simulated)',
    ai_confidence_threshold INTEGER NOT NULL DEFAULT 80,
    auto_generate_reports BOOLEAN NOT NULL DEFAULT FALSE,
    dark_mode BOOLEAN NOT NULL DEFAULT TRUE,
    table_dense_view BOOLEAN NOT NULL DEFAULT FALSE,
    live_ticker_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_settings_id ON user_settings(id);
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);

-- =============================================================================
-- 9. PRODUCTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    sub_category VARCHAR(100),
    trend_score DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    growth_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    volume INTEGER NOT NULL DEFAULT 0,
    velocity_label VARCHAR(50) NOT NULL DEFAULT 'Steady',
    status VARCHAR(50) NOT NULL DEFAULT 'Active',
    price_range VARCHAR(50) NOT NULL DEFAULT '$25 - $50',
    primary_platform VARCHAR(50) NOT NULL DEFAULT 'TikTok',
    platforms JSONB NOT NULL DEFAULT '[]'::jsonb,
    platform_shares JSONB NOT NULL DEFAULT '{}'::jsonb,
    historical_scores JSONB NOT NULL DEFAULT '[]'::jsonb,
    historical_prices JSONB NOT NULL DEFAULT '[]'::jsonb,
    ai_summary TEXT NOT NULL DEFAULT '',
    signals_count INTEGER NOT NULL DEFAULT 0,
    sentiment_score DOUBLE PRECISION NOT NULL DEFAULT 0.8,
    image_url VARCHAR(512),
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_watchlisted BOOLEAN NOT NULL DEFAULT FALSE,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_id ON products(id);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_trend_score ON products(trend_score);

-- =============================================================================
-- 10. CATEGORIES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS categories (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    product_count INTEGER NOT NULL DEFAULT 0,
    avg_trend_score DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    growth_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    velocity_label VARCHAR(50) NOT NULL DEFAULT 'Steady',
    subcategories JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_driver VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_categories_id ON categories(id);
CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);

-- =============================================================================
-- 11. PLATFORMS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS platforms (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    icon VARCHAR(50) NOT NULL DEFAULT 'share',
    total_signals INTEGER NOT NULL DEFAULT 0,
    active_trends INTEGER NOT NULL DEFAULT 0,
    velocity_growth DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    market_share DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(50) NOT NULL DEFAULT 'Connected',
    recent_spikes JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_platforms_id ON platforms(id);
CREATE INDEX IF NOT EXISTS idx_platforms_slug ON platforms(slug);

-- =============================================================================
-- 12. WATCHLISTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS watchlists (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    product_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_watchlists_id ON watchlists(id);
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlists_product_id ON watchlists(product_id);

-- =============================================================================
-- 13. ALERTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL DEFAULT 'Warning',
    category VARCHAR(100) NOT NULL,
    product_id VARCHAR(64),
    product_name VARCHAR(255),
    platform VARCHAR(50),
    trigger VARCHAR(100),
    threshold DOUBLE PRECISION,
    actual_value DOUBLE PRECISION,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_id ON alerts(id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_is_read ON alerts(is_read);

-- =============================================================================
-- 14. NOTIFICATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'alert',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    link VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_id ON notifications(id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);

-- =============================================================================
-- 15. REPORTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    template VARCHAR(100) NOT NULL DEFAULT 'executive_summary',
    time_range VARCHAR(50) NOT NULL DEFAULT '7d',
    status VARCHAR(50) NOT NULL DEFAULT 'ready',
    download_url VARCHAR(512),
    file_size VARCHAR(50) NOT NULL DEFAULT '1.2 MB',
    category_focus VARCHAR(100) NOT NULL DEFAULT 'All Categories',
    data_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reports_id ON reports(id);

-- =============================================================================
-- 16. DATA SOURCES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS data_sources (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'Connected',
    health_score INTEGER NOT NULL DEFAULT 95,
    records_synced INTEGER NOT NULL DEFAULT 0,
    last_sync VARCHAR(50) NOT NULL DEFAULT 'Just now',
    error_count INTEGER NOT NULL DEFAULT 0,
    icon VARCHAR(50) NOT NULL DEFAULT 'database',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_data_sources_id ON data_sources(id);
CREATE INDEX IF NOT EXISTS idx_data_sources_slug ON data_sources(slug);

-- =============================================================================
-- 17. SUBSCRIPTION PLANS TABLE (Phase 2E.3)
-- =============================================================================
CREATE TABLE IF NOT EXISTS subscription_plans (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    billing_interval VARCHAR(20) NOT NULL DEFAULT 'monthly',
    monthly_credits INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    features JSONB NOT NULL DEFAULT '[]'::jsonb,
    limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscription_plans_id ON subscription_plans(id);
CREATE INDEX IF NOT EXISTS idx_subscription_plans_slug ON subscription_plans(slug);

-- =============================================================================
-- 18. USER SUBSCRIPTIONS TABLE (Phase 2E.3)
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL UNIQUE,
    plan_id VARCHAR(64) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    current_period_start TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    current_period_end TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cancelled_at TIMESTAMPTZ,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_id ON user_subscriptions(id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_plan_id ON user_subscriptions(plan_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_current_period_end ON user_subscriptions(current_period_end);

-- =============================================================================
-- 19. CREDIT ACCOUNTS TABLE (Phase 2E.3)
-- =============================================================================
CREATE TABLE IF NOT EXISTS credit_accounts (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL UNIQUE,
    current_balance INTEGER NOT NULL DEFAULT 0,
    lifetime_granted INTEGER NOT NULL DEFAULT 0,
    lifetime_used INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_credit_accounts_id ON credit_accounts(id);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_user_id ON credit_accounts(user_id);

-- =============================================================================
-- 20. CREDIT TRANSACTIONS TABLE (Phase 2E.3)
-- =============================================================================
CREATE TABLE IF NOT EXISTS credit_transactions (
    id VARCHAR(64) PRIMARY KEY,
    credit_account_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    amount INTEGER NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    reference_type VARCHAR(100),
    reference_id VARCHAR(255),
    description VARCHAR(255) NOT NULL DEFAULT '',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_id ON credit_transactions(id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_credit_account_id ON credit_transactions(credit_account_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON credit_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_ref_type ON credit_transactions(reference_type);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_ref_id ON credit_transactions(reference_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON credit_transactions(created_at);

-- =============================================================================
-- 21. CREDIT USAGE TABLE (Phase 2E.3)
-- =============================================================================
CREATE TABLE IF NOT EXISTS credit_usage (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    credit_account_id VARCHAR(64) NOT NULL,
    feature VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    credits_used INTEGER NOT NULL,
    reference_type VARCHAR(100),
    reference_id VARCHAR(255),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_credit_usage_id ON credit_usage(id);
CREATE INDEX IF NOT EXISTS idx_credit_usage_user_id ON credit_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_usage_credit_account_id ON credit_usage(credit_account_id);
CREATE INDEX IF NOT EXISTS idx_credit_usage_ref_type ON credit_usage(reference_type);
CREATE INDEX IF NOT EXISTS idx_credit_usage_ref_id ON credit_usage(reference_id);
CREATE INDEX IF NOT EXISTS idx_credit_usage_created_at ON credit_usage(created_at);

-- =============================================================================
-- SEED DEFAULT SUBSCRIPTION PLANS
-- =============================================================================
INSERT INTO subscription_plans (id, name, slug, description, price, currency, billing_interval, monthly_credits, is_active, features, limits, created_at, updated_at)
VALUES 
(
    'plan_free', 'Free Tier', 'free', 'Core e-commerce trend explorer for emerging sellers and market researchers.',
    0.0, 'USD', 'monthly', 100, TRUE,
    '["Top 50 trending products", "3 daily AI report exports", "Standard market sentiment analysis", "Community data connectors"]'::jsonb,
    '{"max_watchlists": 5, "export_formats": ["pdf"], "rate_limit_per_minute": 30}'::jsonb,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'plan_pro', 'Professional', 'pro', 'Advanced arbitrage signals, real-time alerts, and predictive velocity metrics for power merchants.',
    49.0, 'USD', 'monthly', 1000, TRUE,
    '["Unlimited trending products", "Live price spike & viral momentum alerts", "Comprehensive competitor arbitrage feeds", "Historical backtesting engine", "Priority data sync"]'::jsonb,
    '{"max_watchlists": 50, "export_formats": ["pdf", "csv", "json"], "rate_limit_per_minute": 120}'::jsonb,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'plan_business', 'Business Enterprise', 'business', 'Full enterprise market intelligence platform with custom webhook signals and multi-seat workspaces.',
    199.0, 'USD', 'monthly', 5000, TRUE,
    '["Everything in Professional", "Multi-tenant workspace collaboration", "Custom webhook alert destinations", "Custom predictive model tuning", "Dedicated ingestion pipelines"]'::jsonb,
    '{"max_watchlists": 500, "export_formats": ["pdf", "csv", "json", "parquet"], "rate_limit_per_minute": 600}'::jsonb,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (slug) DO NOTHING;
