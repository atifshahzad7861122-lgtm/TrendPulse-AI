-- =============================================================================
-- TrendPulse AI - Agent 3: Product Entity Matching & Deduplication Migration
-- Source of Truth: backend/app/db/models.py
-- Target Platform: Supabase PostgreSQL (Standard PostgreSQL 15+)
-- Version: 007_product_entity_matching_agent.sql
-- =============================================================================

-- =============================================================================
-- 1. PRODUCT MATCH DECISIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS product_match_decisions (
    id VARCHAR(64) PRIMARY KEY,
    product_a_id VARCHAR(100) NOT NULL,
    product_b_id VARCHAR(100),
    unified_product_id VARCHAR(64) REFERENCES unified_products(unified_product_id) ON DELETE CASCADE,
    platform_a VARCHAR(50) NOT NULL,
    platform_b VARCHAR(50),
    decision VARCHAR(50) NOT NULL DEFAULT 'NO_MATCH', -- EXACT_MATCH, HIGH_CONFIDENCE_MATCH, PROBABLE_MATCH, VARIANT, RELATED_PRODUCT, NO_MATCH, NEEDS_REVIEW
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    match_method VARCHAR(50) NOT NULL DEFAULT 'signature_rule',
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    conflicts JSONB NOT NULL DEFAULT '[]'::jsonb,
    variant_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    base_product_id VARCHAR(64),
    llm_used BOOLEAN NOT NULL DEFAULT FALSE,
    llm_provider VARCHAR(50),
    llm_model VARCHAR(50),
    agent_id VARCHAR(64) NOT NULL REFERENCES ai_agents(id) ON DELETE CASCADE,
    agent_run_id VARCHAR(64) REFERENCES ai_agent_runs(id) ON DELETE SET NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_match_decisions_id ON product_match_decisions(id);
CREATE INDEX IF NOT EXISTS idx_match_decisions_product_a ON product_match_decisions(product_a_id);
CREATE INDEX IF NOT EXISTS idx_match_decisions_product_b ON product_match_decisions(product_b_id);
CREATE INDEX IF NOT EXISTS idx_match_decisions_unified_id ON product_match_decisions(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_match_decisions_decision ON product_match_decisions(decision);
CREATE INDEX IF NOT EXISTS idx_match_decisions_confidence ON product_match_decisions(confidence);
CREATE INDEX IF NOT EXISTS idx_match_decisions_method ON product_match_decisions(match_method);
CREATE INDEX IF NOT EXISTS idx_match_decisions_created_at ON product_match_decisions(created_at);

-- =============================================================================
-- 2. EXTEND PRODUCT MATCH CANDIDATES COLUMNS
-- =============================================================================
ALTER TABLE product_match_candidates ADD COLUMN IF NOT EXISTS product_a_title TEXT;
ALTER TABLE product_match_candidates ADD COLUMN IF NOT EXISTS product_b_title TEXT;
ALTER TABLE product_match_candidates ADD COLUMN IF NOT EXISTS conflicts JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE product_match_candidates ADD COLUMN IF NOT EXISTS variant_attributes JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE product_match_candidates ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(64);
ALTER TABLE product_match_candidates ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_match_candidates_platform ON product_match_candidates(platform, platform_product_id);

-- =============================================================================
-- 3. SEED AGENT 3 RECORD IN AI_AGENTS
-- =============================================================================
INSERT INTO ai_agents (id, name, slug, agent_type, status, description, version, capabilities, configuration, metadata_json, created_at, updated_at)
VALUES (
    'agent_entity_matching',
    'Product Entity Matching & Deduplication Agent',
    'entity-matching',
    'entity_matching',
    'active',
    'Cross-platform product entity resolution, deterministic multi-tier identifier matching, signature candidate blocking, variant detection, false-positive protection, and persistent memory learning.',
    '1.0.0',
    '["exact_sku_matching", "exact_gtin_matching", "brand_model_resolution", "signature_blocking", "variant_attribute_detection", "false_positive_guard", "selective_gemini_reasoning", "persistent_entity_memory"]'::jsonb,
    '{"exact_threshold": 0.99, "high_threshold": 0.95, "probable_threshold": 0.85, "review_threshold": 0.75, "allow_llm": true, "max_candidates": 50}'::jsonb,
    '{"author": "TrendPulse AI Team", "tier": "production"}'::jsonb,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    capabilities = EXCLUDED.capabilities,
    configuration = EXCLUDED.configuration,
    updated_at = CURRENT_TIMESTAMP;
