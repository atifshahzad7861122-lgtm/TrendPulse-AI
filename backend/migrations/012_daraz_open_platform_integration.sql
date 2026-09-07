-- =============================================================================
-- TrendPulse AI - Daraz Open Platform & Supabase Integration Schema
-- Source of Truth: backend/app/db/models.py
-- Target Platform: Supabase PostgreSQL (Standard PostgreSQL 15+)
-- Version: 012_daraz_open_platform_integration.sql
-- =============================================================================

-- =============================================================================
-- 1. DARAZ SELLERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS daraz_sellers (
    id VARCHAR(64) PRIMARY KEY,
    seller_id VARCHAR(64) NOT NULL UNIQUE,
    seller_name VARCHAR(255) NOT NULL,
    shop_url VARCHAR(1024),
    rating DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    positive_ratings_percentage DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    location VARCHAR(100),
    is_official_store BOOLEAN NOT NULL DEFAULT FALSE,
    total_products INTEGER NOT NULL DEFAULT 0,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daraz_sellers_seller_id ON daraz_sellers(seller_id);
CREATE INDEX IF NOT EXISTS idx_daraz_sellers_seller_name ON daraz_sellers(seller_name);

-- =============================================================================
-- 2. DARAZ CATEGORIES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS daraz_categories (
    id VARCHAR(64) PRIMARY KEY,
    category_id VARCHAR(64) NOT NULL UNIQUE,
    parent_id VARCHAR(64),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    leaf BOOLEAN NOT NULL DEFAULT TRUE,
    product_count INTEGER NOT NULL DEFAULT 0,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daraz_categories_category_id ON daraz_categories(category_id);
CREATE INDEX IF NOT EXISTS idx_daraz_categories_parent_id ON daraz_categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_daraz_categories_slug ON daraz_categories(slug);

-- =============================================================================
-- 3. DARAZ REVIEWS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS daraz_reviews (
    id VARCHAR(64) PRIMARY KEY,
    review_id VARCHAR(64) NOT NULL UNIQUE,
    product_id VARCHAR(64) NOT NULL,
    seller_id VARCHAR(64),
    rating DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    reviewer_name VARCHAR(255),
    review_title VARCHAR(512),
    review_content TEXT,
    verified_purchase BOOLEAN NOT NULL DEFAULT TRUE,
    review_date TIMESTAMPTZ,
    sentiment_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daraz_reviews_review_id ON daraz_reviews(review_id);
CREATE INDEX IF NOT EXISTS idx_daraz_reviews_product_id ON daraz_reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_daraz_reviews_seller_id ON daraz_reviews(seller_id);
CREATE INDEX IF NOT EXISTS idx_daraz_reviews_rating ON daraz_reviews(rating);

-- =============================================================================
-- 4. DARAZ INGESTION RUNS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS daraz_ingestion_runs (
    id VARCHAR(64) PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    trigger_type VARCHAR(50) NOT NULL DEFAULT 'scheduled',
    category VARCHAR(100),
    search_query VARCHAR(255),
    products_fetched INTEGER NOT NULL DEFAULT 0,
    products_inserted INTEGER NOT NULL DEFAULT 0,
    products_updated INTEGER NOT NULL DEFAULT 0,
    snapshots_created INTEGER NOT NULL DEFAULT 0,
    reviews_fetched INTEGER NOT NULL DEFAULT 0,
    error_code INTEGER,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daraz_ingestion_runs_status ON daraz_ingestion_runs(status);
CREATE INDEX IF NOT EXISTS idx_daraz_ingestion_runs_provider ON daraz_ingestion_runs(provider_name);
CREATE INDEX IF NOT EXISTS idx_daraz_ingestion_runs_started_at ON daraz_ingestion_runs(started_at);

-- =============================================================================
-- 5. DARAZ API REQUEST TELEMETRY TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS daraz_api_telemetry (
    id VARCHAR(64) PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL DEFAULT 'GET',
    provider_name VARCHAR(50) NOT NULL DEFAULT 'daraz_official_open_platform',
    status_code INTEGER NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_code VARCHAR(100),
    error_message TEXT,
    request_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_size_bytes INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daraz_telemetry_endpoint ON daraz_api_telemetry(endpoint);
CREATE INDEX IF NOT EXISTS idx_daraz_telemetry_status_code ON daraz_api_telemetry(status_code);
CREATE INDEX IF NOT EXISTS idx_daraz_telemetry_created_at ON daraz_api_telemetry(created_at);

-- =============================================================================
-- 6. DARAZ DAILY QUOTA TRACKING TABLE (6,000,000 requests/day)
-- =============================================================================
CREATE TABLE IF NOT EXISTS daraz_daily_quotas (
    id VARCHAR(64) PRIMARY KEY,
    date VARCHAR(10) NOT NULL UNIQUE,
    requests_used INTEGER NOT NULL DEFAULT 0,
    daily_limit INTEGER NOT NULL DEFAULT 6000000,
    remaining INTEGER NOT NULL DEFAULT 6000000,
    rate_limit_hits INTEGER NOT NULL DEFAULT 0,
    last_request_at TIMESTAMPTZ,
    reset_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daraz_quotas_date ON daraz_daily_quotas(date);

-- =============================================================================
-- 7. DARAZ AGENT TRAINING & REFINED DATASET TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS daraz_training_dataset (
    id VARCHAR(64) PRIMARY KEY,
    product_id VARCHAR(64) NOT NULL,
    unified_product_id VARCHAR(64),
    title VARCHAR(512) NOT NULL,
    category VARCHAR(255) NOT NULL,
    brand VARCHAR(255),
    price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    rating DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    review_count INTEGER NOT NULL DEFAULT 0,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    quality_score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    agent_label VARCHAR(100) DEFAULT 'clean_catalog',
    is_validated BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daraz_training_product_id ON daraz_training_dataset(product_id);
CREATE INDEX IF NOT EXISTS idx_daraz_training_category ON daraz_training_dataset(category);
CREATE INDEX IF NOT EXISTS idx_daraz_training_quality_score ON daraz_training_dataset(quality_score);
CREATE INDEX IF NOT EXISTS idx_daraz_training_created_at ON daraz_training_dataset(created_at);
