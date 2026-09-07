-- ============================================================================
-- Migration: 009_anomaly_detection_agent.sql
-- Description: Database schema for AI Agent 05: Anomaly Detection Agent
-- Tables: anomaly_observations, anomaly_detections, anomaly_candidates, anomaly_detection_audit
-- Seed: Registers agent_anomaly_detection in ai_agents
-- ============================================================================

-- 1. Anomaly Observations Table (raw metric snapshots for anomaly baseline calculation)
CREATE TABLE IF NOT EXISTS public.anomaly_observations (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    metric_type VARCHAR(32) NOT NULL, -- price, rating, review_count, availability, discount, inventory
    metric_value NUMERIC(12, 4) NOT NULL,
    previous_value NUMERIC(12, 4),
    change_value NUMERIC(12, 4),
    change_percent NUMERIC(8, 4),
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(64) DEFAULT 'marketplace_sync',
    metadata_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_obs_prod_metric ON public.anomaly_observations(unified_product_id, metric_type, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_obs_platform ON public.anomaly_observations(platform, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_obs_observed_at ON public.anomaly_observations(observed_at DESC);

-- 2. Anomaly Detections Table (detected abnormal behaviors)
CREATE TABLE IF NOT EXISTS public.anomaly_detections (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL,
    anomaly_type VARCHAR(64) NOT NULL, -- price_spike, price_crash, unusual_discount, rating_jump, rating_drop, review_velocity_spike, review_velocity_drop, availability_change, inventory_anomaly, cross_platform_price_anomaly, platform_presence_anomaly, category_activity_anomaly, provider_data_anomaly, unusual_activity
    severity VARCHAR(16) NOT NULL DEFAULT 'medium', -- low, medium, high, critical
    score NUMERIC(6, 2) NOT NULL DEFAULT 50.0, -- 0.00 to 100.00
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.85, -- 0.000 to 1.000
    baseline NUMERIC(12, 4),
    observed_value NUMERIC(12, 4),
    deviation NUMERIC(12, 4),
    deviation_percent NUMERIC(8, 4),
    baseline_method VARCHAR(64) DEFAULT 'rolling_median', -- rolling_mean, rolling_median, std_dev, mad, category_baseline, platform_baseline
    evidence JSONB DEFAULT '{}'::jsonb,
    platforms TEXT[] DEFAULT ARRAY[]::TEXT[],
    provider VARCHAR(64),
    fingerprint VARCHAR(128) UNIQUE, -- SHA-256 idempotency hash
    status VARCHAR(16) NOT NULL DEFAULT 'active', -- active, resolved, suppressed, false_positive
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_det_prod ON public.anomaly_detections(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_det_type ON public.anomaly_detections(anomaly_type);
CREATE INDEX IF NOT EXISTS idx_anomaly_det_severity ON public.anomaly_detections(severity);
CREATE INDEX IF NOT EXISTS idx_anomaly_det_status ON public.anomaly_detections(status);
CREATE INDEX IF NOT EXISTS idx_anomaly_det_score ON public.anomaly_detections(score DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_det_detected_at ON public.anomaly_detections(detected_at DESC);

-- 3. Anomaly Candidates Table (human-in-the-loop review queue for ambiguous or low-confidence anomalies)
CREATE TABLE IF NOT EXISTS public.anomaly_candidates (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL,
    anomaly_id VARCHAR(64),
    candidate_type VARCHAR(64) NOT NULL,
    composite_score NUMERIC(6, 2) NOT NULL DEFAULT 50.0,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.85,
    status VARCHAR(32) NOT NULL DEFAULT 'pending_review', -- pending_review, confirmed, dismissed, false_positive, auto_promoted
    reasons TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_cand_status ON public.anomaly_candidates(status);
CREATE INDEX IF NOT EXISTS idx_anomaly_cand_prod ON public.anomaly_candidates(unified_product_id);

-- 4. Anomaly Detection Audit Table
CREATE TABLE IF NOT EXISTS public.anomaly_detection_audit (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL DEFAULT 'agent_anomaly_detection',
    run_id VARCHAR(64) NOT NULL,
    anomaly_id VARCHAR(64),
    product_id VARCHAR(64) NOT NULL,
    detection_method VARCHAR(64) NOT NULL,
    rule_name VARCHAR(64) NOT NULL,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 1.0,
    evidence JSONB DEFAULT '{}'::jsonb,
    decision VARCHAR(32) NOT NULL, -- anomaly_detected, normal_variance, insufficient_data, false_positive_suppressed
    llm_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_audit_run ON public.anomaly_detection_audit(run_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_audit_prod ON public.anomaly_detection_audit(product_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_audit_decision ON public.anomaly_detection_audit(decision);

-- 5. Seed Agent 05 in ai_agents registry
INSERT INTO public.ai_agents (
    id, name, slug, agent_type, status, description, version, capabilities, configuration, metadata_json, created_at, updated_at
) VALUES (
    'agent_anomaly_detection',
    'Anomaly Detection Agent',
    'agent-anomaly-detection',
    'anomaly_detection',
    'active',
    'Detects statistical outliers, extreme price shifts, rating jumps/drops, review velocity anomalies, availability transitions, cross-platform disparities, and provider data anomalies.',
    '1.0.0',
    ARRAY['statistical_baselines', 'price_anomaly_detection', 'rating_velocity_anomaly', 'cross_platform_disparity', 'provider_quality_monitoring', 'memory_reinforcement'],
    '{"min_observations": 2, "price_spike_threshold": 0.40, "price_crash_threshold": -0.40, "rating_jump_threshold": 0.5, "review_velocity_multiplier": 2.5}'::jsonb,
    '{"pipeline_stage": 5, "deterministic_first": true, "anti_fabrication": true}'::jsonb,
    NOW(),
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    capabilities = EXCLUDED.capabilities,
    configuration = EXCLUDED.configuration,
    updated_at = NOW();
