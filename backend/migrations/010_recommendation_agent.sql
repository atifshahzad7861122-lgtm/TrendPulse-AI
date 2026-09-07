-- ============================================================================
-- Migration: 010_recommendation_agent.sql
-- Description: Database schema for AI Agent 06: Recommendation & Product Intelligence Agent
-- Tables: product_recommendations, recommendation_candidates, recommendation_interactions, recommendation_audit
-- Seed: Registers agent_recommendation_engine in ai_agents
-- ============================================================================

-- 1. Product Recommendations Table (evidence-grounded recommendations)
CREATE TABLE IF NOT EXISTS public.product_recommendations (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL,
    target_product_id VARCHAR(64), -- optional reference if recommendation is an alternative/similar to a target
    recommendation_type VARCHAR(64) NOT NULL, -- similar_product, alternative_product, better_price, trending_product, high_quality, cross_platform, category_recommendation, rising_product, opportunity, best_value
    score NUMERIC(6, 2) NOT NULL DEFAULT 50.0, -- 0.00 to 100.00
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.85, -- 0.000 to 1.000
    reasons TEXT[] DEFAULT ARRAY[]::TEXT[],
    evidence JSONB DEFAULT '{}'::jsonb,
    source_agents TEXT[] DEFAULT ARRAY[]::TEXT[], -- agent_data_quality, agent_taxonomy, agent_entity_matching, agent_trend_detection, agent_anomaly_detection
    warnings TEXT[] DEFAULT ARRAY[]::TEXT[],
    platforms TEXT[] DEFAULT ARRAY[]::TEXT[],
    category VARCHAR(128),
    brand VARCHAR(128),
    fingerprint VARCHAR(128) UNIQUE, -- SHA-256 idempotency hash
    status VARCHAR(16) NOT NULL DEFAULT 'active', -- active, archived, dismissed, expired
    freshness_status VARCHAR(32) NOT NULL DEFAULT 'fresh', -- fresh, recent, stale, insufficient_data
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_rec_prod ON public.product_recommendations(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_rec_target_prod ON public.product_recommendations(target_product_id);
CREATE INDEX IF NOT EXISTS idx_rec_type ON public.product_recommendations(recommendation_type);
CREATE INDEX IF NOT EXISTS idx_rec_score ON public.product_recommendations(score DESC);
CREATE INDEX IF NOT EXISTS idx_rec_status ON public.product_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_rec_category ON public.product_recommendations(category);
CREATE INDEX IF NOT EXISTS idx_rec_created_at ON public.product_recommendations(created_at DESC);

-- 2. Recommendation Candidates Table (human-in-the-loop review queue for ambiguous or low-confidence recommendations)
CREATE TABLE IF NOT EXISTS public.recommendation_candidates (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL,
    target_product_id VARCHAR(64),
    candidate_type VARCHAR(64) NOT NULL,
    composite_score NUMERIC(6, 2) NOT NULL DEFAULT 50.0,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.85,
    status VARCHAR(32) NOT NULL DEFAULT 'pending', -- pending, approved, dismissed, rejected
    reasons TEXT[] DEFAULT ARRAY[]::TEXT[],
    evidence JSONB DEFAULT '{}'::jsonb,
    source_agents TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rec_cand_status ON public.recommendation_candidates(status);
CREATE INDEX IF NOT EXISTS idx_rec_cand_prod ON public.recommendation_candidates(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_rec_cand_created_at ON public.recommendation_candidates(created_at DESC);

-- 3. Recommendation Interactions Table (real user behavioral tracking events)
CREATE TABLE IF NOT EXISTS public.recommendation_interactions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64),
    workspace_id VARCHAR(64),
    recommendation_id VARCHAR(64),
    product_id VARCHAR(64) NOT NULL,
    interaction_type VARCHAR(64) NOT NULL, -- view, click, save, dismiss, compare, external_link_click
    metadata JSONB DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rec_int_user ON public.recommendation_interactions(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_rec_int_prod ON public.recommendation_interactions(product_id);
CREATE INDEX IF NOT EXISTS idx_rec_int_type ON public.recommendation_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_rec_int_rec ON public.recommendation_interactions(recommendation_id);

-- 4. Recommendation Audit Table
CREATE TABLE IF NOT EXISTS public.recommendation_audit (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL DEFAULT 'agent_recommendation_engine',
    run_id VARCHAR(64) NOT NULL,
    recommendation_id VARCHAR(64),
    product_id VARCHAR(64) NOT NULL,
    decision VARCHAR(64) NOT NULL, -- generated, candidate_queued, quality_rejected, anomaly_blocked, insufficient_data
    score NUMERIC(6, 2) NOT NULL DEFAULT 50.0,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 1.0,
    evidence JSONB DEFAULT '{}'::jsonb,
    source_agents TEXT[] DEFAULT ARRAY[]::TEXT[],
    llm_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rec_audit_run ON public.recommendation_audit(run_id);
CREATE INDEX IF NOT EXISTS idx_rec_audit_prod ON public.recommendation_audit(product_id);
CREATE INDEX IF NOT EXISTS idx_rec_audit_decision ON public.recommendation_audit(decision);

-- 5. Seed Agent 06 in ai_agents registry
INSERT INTO public.ai_agents (
    id, name, slug, agent_type, status, description, version, capabilities, configuration, metadata_json, created_at, updated_at
) VALUES (
    'agent_recommendation_engine',
    'Recommendation & Product Intelligence Agent',
    'recommendation-engine',
    'recommendation',
    'active',
    'Transforms verified multi-agent marketplace intelligence into evidence-grounded, explainable recommendations and rankings.',
    '1.0.0',
    ARRAY['product_recommendations', 'similar_products', 'alternative_products', 'better_price_discovery', 'trending_recommendations', 'cross_platform_discovery', 'category_recommendations', 'opportunity_detection', 'best_value_ranking', 'user_personalization'],
    '{"data_quality_min_score": 70, "confidence_threshold": 0.75, "max_recommendations_per_product": 10, "lookback_days": 30}'::jsonb,
    '{"agent_number": 6, "pipeline_stage": "recommendation", "category": "intelligence"}'::jsonb,
    NOW(),
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    capabilities = EXCLUDED.capabilities,
    configuration = EXCLUDED.configuration,
    updated_at = NOW();
