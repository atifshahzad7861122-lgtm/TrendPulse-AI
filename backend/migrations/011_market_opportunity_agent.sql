-- ============================================================================
-- Migration: 011_market_opportunity_agent.sql
-- Description: Database schema for AI Agent 07: Market Opportunity Intelligence Agent
-- Tables: market_opportunities, market_opportunity_candidates, market_opportunity_audit
-- Seed: Registers agent_market_opportunity_intelligence in ai_agents
-- ============================================================================

-- 1. Market Opportunities Table (evidence-grounded market opportunities)
CREATE TABLE IF NOT EXISTS public.market_opportunities (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64),
    category VARCHAR(128),
    subcategory VARCHAR(128),
    brand VARCHAR(128),
    opportunity_type VARCHAR(64) NOT NULL, -- product_gap, price_opportunity, category_opportunity, competitive_gap, cross_platform_gap, availability_opportunity, quality_gap, rising_category, rising_product, marketplace_expansion, underserved_category, product_launch_opportunity
    score NUMERIC(6, 2) NOT NULL DEFAULT 50.0, -- 0.00 to 100.00
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.85, -- 0.000 to 1.000
    status VARCHAR(32) NOT NULL DEFAULT 'active', -- active, archived, dismissed, insufficient_data, quality_gated, anomaly_blocked
    reasons TEXT[] DEFAULT ARRAY[]::TEXT[],
    evidence JSONB DEFAULT '{}'::jsonb,
    source_agent_ids TEXT[] DEFAULT ARRAY[]::TEXT[], -- agent_data_quality, agent_taxonomy, agent_entity_matching, agent_trend_detection, agent_anomaly_detection, agent_recommendation_engine
    warnings TEXT[] DEFAULT ARRAY[]::TEXT[],
    current_platforms TEXT[] DEFAULT ARRAY[]::TEXT[],
    missing_observed_platforms TEXT[] DEFAULT ARRAY[]::TEXT[],
    fingerprint VARCHAR(128) UNIQUE, -- SHA-256 idempotency hash
    data_freshness VARCHAR(32) NOT NULL DEFAULT 'fresh', -- fresh, recent, stale, insufficient_data
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_opp_prod ON public.market_opportunities(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_opp_category ON public.market_opportunities(category);
CREATE INDEX IF NOT EXISTS idx_opp_type ON public.market_opportunities(opportunity_type);
CREATE INDEX IF NOT EXISTS idx_opp_score ON public.market_opportunities(score DESC);
CREATE INDEX IF NOT EXISTS idx_opp_status ON public.market_opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opp_detected_at ON public.market_opportunities(detected_at DESC);

-- 2. Market Opportunity Candidates Table (human-in-the-loop review queue for low-confidence or ambiguous opportunities)
CREATE TABLE IF NOT EXISTS public.market_opportunity_candidates (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64),
    category VARCHAR(128),
    candidate_type VARCHAR(64) NOT NULL,
    composite_score NUMERIC(6, 2) NOT NULL DEFAULT 50.0,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.85,
    status VARCHAR(32) NOT NULL DEFAULT 'pending', -- pending, approved, dismissed, rejected
    reasons TEXT[] DEFAULT ARRAY[]::TEXT[],
    evidence JSONB DEFAULT '{}'::jsonb,
    source_agent_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_opp_cand_status ON public.market_opportunity_candidates(status);
CREATE INDEX IF NOT EXISTS idx_opp_cand_prod ON public.market_opportunity_candidates(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_opp_cand_created_at ON public.market_opportunity_candidates(created_at DESC);

-- 3. Market Opportunity Audit Table
CREATE TABLE IF NOT EXISTS public.market_opportunity_audit (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL DEFAULT 'agent_market_opportunity_intelligence',
    run_id VARCHAR(64) NOT NULL,
    opportunity_id VARCHAR(64),
    rule_name VARCHAR(128) NOT NULL,
    decision VARCHAR(64) NOT NULL, -- generated, candidate_queued, quality_rejected, anomaly_blocked, insufficient_data
    score NUMERIC(6, 2) NOT NULL DEFAULT 50.0,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 1.0,
    evidence JSONB DEFAULT '{}'::jsonb,
    source_agent_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    llm_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_opp_audit_run ON public.market_opportunity_audit(run_id);
CREATE INDEX IF NOT EXISTS idx_opp_audit_opp ON public.market_opportunity_audit(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_opp_audit_decision ON public.market_opportunity_audit(decision);

-- 4. Seed Agent 07 in ai_agents registry
INSERT INTO public.ai_agents (
    id, name, slug, agent_type, status, description, version, capabilities, configuration, metadata_json, created_at, updated_at
) VALUES (
    'agent_market_opportunity_intelligence',
    'Market Opportunity Intelligence Agent',
    'market-opportunity-intelligence',
    'opportunity_discovery',
    'active',
    'Identifies evidence-grounded product and market opportunities, gaps, competitive advantages, and expansion avenues from verified marketplace data.',
    '1.0.0',
    ARRAY['product_gap_detection', 'price_opportunity_analysis', 'category_opportunity_discovery', 'competitive_gap_identification', 'cross_platform_gap_analysis', 'availability_opportunity_tracking', 'quality_gap_detection', 'marketplace_expansion_discovery', 'underserved_category_mapping', 'product_launch_opportunity_evaluation'],
    '{"min_evidence_score": 50.0, "confidence_threshold": 0.75, "max_opportunities_per_run": 50, "lookback_days": 30, "memory_key": "mem_market_opportunity_rules"}'::jsonb,
    '{"agent_number": 7, "pipeline_stage": "opportunity_intelligence", "category": "market_strategy"}'::jsonb,
    NOW(),
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    capabilities = EXCLUDED.capabilities,
    configuration = EXCLUDED.configuration,
    updated_at = NOW();
