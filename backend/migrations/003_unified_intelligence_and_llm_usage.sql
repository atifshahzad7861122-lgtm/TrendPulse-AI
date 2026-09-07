-- =============================================================================
-- TrendPulse AI - Unified Product Intelligence & LLM Usage Tracking Migration
-- Source of Truth: backend/app/db/models.py
-- Target Platform: Supabase PostgreSQL (Standard PostgreSQL 15+)
-- Version: 003_unified_intelligence_and_llm_usage.sql
-- =============================================================================

-- =============================================================================
-- 1. UNIFIED PRODUCTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS unified_products (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL UNIQUE,
    canonical_name VARCHAR(512) NOT NULL,
    normalized_name VARCHAR(512) NOT NULL,
    brand VARCHAR(150),
    category VARCHAR(150),
    subcategory VARCHAR(150),
    product_type VARCHAR(150),
    description TEXT,
    primary_image VARCHAR(1024),
    identifiers JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_unified_products_id ON unified_products(id);
CREATE INDEX IF NOT EXISTS idx_unified_products_unified_id ON unified_products(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_unified_products_brand ON unified_products(brand);
CREATE INDEX IF NOT EXISTS idx_unified_products_category ON unified_products(category);
CREATE INDEX IF NOT EXISTS idx_unified_products_updated_at ON unified_products(updated_at);

-- =============================================================================
-- 2. PRODUCT PLATFORM LISTINGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS product_platform_listings (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL REFERENCES unified_products(unified_product_id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_product_id VARCHAR(100) NOT NULL,
    store_domain VARCHAR(255),
    product_url VARCHAR(1024) NOT NULL,
    title VARCHAR(512) NOT NULL,
    normalized_title VARCHAR(512) NOT NULL,
    price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    original_price DOUBLE PRECISION,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    discount_percentage DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    discount_label VARCHAR(50),
    seller_name VARCHAR(255),
    vendor VARCHAR(255),
    rating DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    review_count INTEGER NOT NULL DEFAULT 0,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    image_url VARCHAR(1024),
    source_provider VARCHAR(50) NOT NULL DEFAULT 'direct',
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completeness_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_platform_listings_platform_prod_store UNIQUE (platform, platform_product_id, store_domain)
);

CREATE INDEX IF NOT EXISTS idx_platform_listings_unified_id ON product_platform_listings(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_platform_listings_platform ON product_platform_listings(platform);
CREATE INDEX IF NOT EXISTS idx_platform_listings_price ON product_platform_listings(price);
CREATE INDEX IF NOT EXISTS idx_platform_listings_last_synced ON product_platform_listings(last_synced_at);

-- =============================================================================
-- 3. PRODUCT MATCH CANDIDATES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS product_match_candidates (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL REFERENCES unified_products(unified_product_id) ON DELETE CASCADE,
    candidate_unified_id VARCHAR(64) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_product_id VARCHAR(100) NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    method VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'probable',
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_match_candidates_unified_id ON product_match_candidates(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_match_candidates_status ON product_match_candidates(status);

-- =============================================================================
-- 4. PRODUCT MATCH AUDIT TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS product_match_audit (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL REFERENCES unified_products(unified_product_id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_product_id VARCHAR(100) NOT NULL,
    matching_method VARCHAR(50) NOT NULL,
    matching_confidence DOUBLE PRECISION NOT NULL,
    matched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_match_audit_unified_id ON product_match_audit(unified_product_id);

-- =============================================================================
-- 5. LLM USAGE RECORDS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS llm_usage_records (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE SET NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    request_type VARCHAR(50) NOT NULL,
    prompt_version VARCHAR(20) NOT NULL DEFAULT 'v1',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    error_code INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_user_id ON llm_usage_records(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_workspace_id ON llm_usage_records(workspace_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created_at ON llm_usage_records(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_usage_request_type ON llm_usage_records(request_type);
CREATE INDEX IF NOT EXISTS idx_llm_usage_provider ON llm_usage_records(provider);
