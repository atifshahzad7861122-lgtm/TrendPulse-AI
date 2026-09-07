-- =============================================================================
-- TrendPulse AI - Real Marketplace Products & Market Snapshots Schema Migration
-- Source of Truth: backend/app/db/models.py
-- Target Platform: Supabase PostgreSQL (Standard PostgreSQL 15+)
-- Version: 002_marketplace_products.sql
-- =============================================================================

-- =============================================================================
-- 1. MARKETPLACE PRODUCTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS marketplace_products (
    id VARCHAR(64) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL DEFAULT 'daraz',
    product_id VARCHAR(64) NOT NULL,
    product_name VARCHAR(512) NOT NULL,
    product_url VARCHAR(1024),
    image_url VARCHAR(1024),
    seller_name VARCHAR(255),
    seller_id VARCHAR(64),
    category VARCHAR(100),
    price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    original_price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    discount_percentage DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    discount_label VARCHAR(50),
    rating DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    review_count INTEGER NOT NULL DEFAULT 0,
    stock_status VARCHAR(50) NOT NULL DEFAULT 'in_stock',
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,
    currency VARCHAR(10) NOT NULL DEFAULT 'PKR',
    location VARCHAR(100),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    raw_source_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_marketplace_products_platform_product_id UNIQUE (platform, product_id)
);

CREATE INDEX IF NOT EXISTS idx_marketplace_products_id ON marketplace_products(id);
CREATE INDEX IF NOT EXISTS idx_marketplace_products_platform ON marketplace_products(platform);
CREATE INDEX IF NOT EXISTS idx_marketplace_products_product_id ON marketplace_products(product_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_products_category ON marketplace_products(category);
CREATE INDEX IF NOT EXISTS idx_marketplace_products_last_synced_at ON marketplace_products(last_synced_at);

-- =============================================================================
-- 2. PRODUCT MARKET SNAPSHOTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS product_market_snapshots (
    id VARCHAR(64) PRIMARY KEY,
    product_id VARCHAR(64) NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT 'daraz',
    price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    original_price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    discount DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    rating DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    review_count INTEGER NOT NULL DEFAULT 0,
    stock_status VARCHAR(50) NOT NULL DEFAULT 'in_stock',
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_product_market_snapshots_id ON product_market_snapshots(id);
CREATE INDEX IF NOT EXISTS idx_product_market_snapshots_product_id ON product_market_snapshots(product_id);
CREATE INDEX IF NOT EXISTS idx_product_market_snapshots_platform ON product_market_snapshots(platform);
CREATE INDEX IF NOT EXISTS idx_product_market_snapshots_observed_at ON product_market_snapshots(observed_at);
