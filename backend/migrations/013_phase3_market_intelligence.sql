-- Phase 3 Market Intelligence and Social Demand Intelligence Schema
-- Migration: 013_phase3_market_intelligence.sql

CREATE TABLE IF NOT EXISTS market_intelligence_snapshots (
    id VARCHAR(64) PRIMARY KEY,
    product_id VARCHAR(100) NOT NULL,
    unified_product_id VARCHAR(64),
    marketplace VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    current_price FLOAT NOT NULL DEFAULT 0.0,
    historical_price FLOAT,
    price_change_pct FLOAT,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    rating FLOAT NOT NULL DEFAULT 0.0,
    review_count INTEGER NOT NULL DEFAULT 0,
    availability BOOLEAN NOT NULL DEFAULT TRUE,
    market_score FLOAT NOT NULL DEFAULT 0.0,
    market_score_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    demand_score FLOAT NOT NULL DEFAULT 0.0,
    demand_level VARCHAR(50) NOT NULL DEFAULT 'MODERATE',
    trend_velocity FLOAT,
    growth_7d FLOAT,
    growth_30d FLOAT,
    viral_score FLOAT,
    viral_level VARCHAR(50) NOT NULL DEFAULT 'unavailable',
    opportunity_score FLOAT NOT NULL DEFAULT 0.0,
    opportunity_level VARCHAR(50) NOT NULL DEFAULT 'Moderate',
    social_mentions_count INTEGER NOT NULL DEFAULT 0,
    social_total_views INTEGER NOT NULL DEFAULT 0,
    social_total_engagement INTEGER NOT NULL DEFAULT 0,
    confidence_score FLOAT NOT NULL DEFAULT 1.0,
    data_quality_score FLOAT NOT NULL DEFAULT 80.0,
    source_provenance VARCHAR(100) NOT NULL DEFAULT 'marketplace',
    ai_summary TEXT,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mkt_intel_prod_id ON market_intelligence_snapshots (product_id);
CREATE INDEX IF NOT EXISTS idx_mkt_intel_marketplace ON market_intelligence_snapshots (marketplace);
CREATE INDEX IF NOT EXISTS idx_mkt_intel_category ON market_intelligence_snapshots (category);
CREATE INDEX IF NOT EXISTS idx_mkt_intel_score ON market_intelligence_snapshots (market_score);
CREATE INDEX IF NOT EXISTS idx_mkt_intel_created_at ON market_intelligence_snapshots (created_at DESC);

CREATE TABLE IF NOT EXISTS social_signals (
    id VARCHAR(64) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL DEFAULT 'YouTube',
    external_id VARCHAR(100),
    content_title VARCHAR(512) NOT NULL,
    content_url VARCHAR(1024) NOT NULL,
    author_name VARCHAR(255),
    views INTEGER NOT NULL DEFAULT 0,
    likes INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    shares INTEGER NOT NULL DEFAULT 0,
    engagement_rate FLOAT NOT NULL DEFAULT 0.0,
    matched_product_id VARCHAR(100),
    matched_unified_id VARCHAR(64),
    match_confidence FLOAT NOT NULL DEFAULT 0.0,
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    raw_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_social_sig_platform ON social_signals (platform);
CREATE INDEX IF NOT EXISTS idx_social_sig_ext_id ON social_signals (external_id);
CREATE INDEX IF NOT EXISTS idx_social_sig_matched_pid ON social_signals (matched_product_id);
CREATE INDEX IF NOT EXISTS idx_social_sig_matched_uid ON social_signals (matched_unified_id);
CREATE INDEX IF NOT EXISTS idx_social_sig_created_at ON social_signals (created_at DESC);
