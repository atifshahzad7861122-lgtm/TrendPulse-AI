-- Migration 008: AI Agent 04 - Trend Detection & Signal Discovery Agent
-- TrendPulse AI: Grounded marketplace trend observations, deterministic signals, breakout candidates, and audit trail

-- 1. Trend Observations Table (Historical snapshots of metrics across platforms)
CREATE TABLE IF NOT EXISTS trend_observations (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- price, rating, review_count, inventory, availability, platform_presence, discount, category_position
    metric_value DOUBLE PRECISION NOT NULL,
    previous_value DOUBLE PRECISION,
    change_value DOUBLE PRECISION,
    change_percent DOUBLE PRECISION,
    observed_at TIMESTAMPTZ NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT 'marketplace_sync',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trend_obs_unified ON trend_observations(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_trend_obs_query ON trend_observations(unified_product_id, metric_type, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_obs_platform ON trend_observations(platform);
CREATE INDEX IF NOT EXISTS idx_trend_obs_observed_at ON trend_observations(observed_at DESC);

-- 2. Trend Signals Table (Detected product and market signals with evidence)
CREATE TABLE IF NOT EXISTS trend_signals (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL,
    signal_type VARCHAR(50) NOT NULL, -- demand_surge, price_drop, price_increase, large_discount, price_volatility, rating_momentum, review_momentum, inventory_change, out_of_stock, restocked, cross_platform_surge, breakout_candidate, emerging_product, declining_product, unusual_activity
    signal_strength DOUBLE PRECISION NOT NULL DEFAULT 0.0, -- 0.0 to 100.0
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0, -- 0.0 to 1.0
    direction VARCHAR(20) NOT NULL DEFAULT 'stable', -- up, down, stable, volatile, unknown
    severity VARCHAR(20) NOT NULL DEFAULT 'medium', -- low, medium, high, critical
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, resolved, dismissed, insufficient_data
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    platforms JSONB NOT NULL DEFAULT '[]'::jsonb,
    fingerprint VARCHAR(128) NOT NULL,
    llm_used BOOLEAN NOT NULL DEFAULT FALSE,
    llm_explanation TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trend_signals_unified ON trend_signals(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_trend_signals_type ON trend_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_trend_signals_direction ON trend_signals(direction);
CREATE INDEX IF NOT EXISTS idx_trend_signals_severity ON trend_signals(severity);
CREATE INDEX IF NOT EXISTS idx_trend_signals_status ON trend_signals(status);
CREATE INDEX IF NOT EXISTS idx_trend_signals_detected_at ON trend_signals(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_signals_fingerprint ON trend_signals(fingerprint);

-- 3. Trend Signal Candidates Table (Multi-signal breakout and review candidates)
CREATE TABLE IF NOT EXISTS trend_signal_candidates (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL,
    candidate_type VARCHAR(50) NOT NULL, -- breakout_candidate, emerging_product, unusual_activity, low_confidence_signal
    composite_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(50) NOT NULL DEFAULT 'pending_review', -- pending_review, confirmed, rejected, auto_promoted
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    supporting_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trend_candidates_unified ON trend_signal_candidates(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_trend_candidates_status ON trend_signal_candidates(status);
CREATE INDEX IF NOT EXISTS idx_trend_candidates_type ON trend_signal_candidates(candidate_type);

-- 4. Trend Detection Audit Table (Explainability and provenance trail)
CREATE TABLE IF NOT EXISTS trend_detection_audit (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL DEFAULT 'agent_trend_detection',
    run_id VARCHAR(64),
    product_id VARCHAR(64) NOT NULL,
    signal_id VARCHAR(64),
    detection_method VARCHAR(50) NOT NULL, -- deterministic_rules, composite_scoring, selective_gemini_reasoning, memory_recall
    rule_name VARCHAR(100),
    confidence DOUBLE PRECISION NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    decision VARCHAR(50) NOT NULL,
    llm_used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trend_audit_product ON trend_detection_audit(product_id);
CREATE INDEX IF NOT EXISTS idx_trend_audit_agent ON trend_detection_audit(agent_id);
CREATE INDEX IF NOT EXISTS idx_trend_audit_created_at ON trend_detection_audit(created_at DESC);

-- 5. Seed Agent 4 into ai_agents registry if not present
INSERT INTO ai_agents (id, name, slug, agent_type, status, description, version, capabilities, configuration, metadata_json, created_at, updated_at)
VALUES (
    'agent_trend_detection',
    'Trend Detection & Signal Discovery Agent',
    'trend-detection',
    'trend_detection',
    'active',
    'Analyzes verified multi-platform marketplace observations to discover real product and market trends with explainable evidence, deterministic scoring, and selective Gemini reasoning.',
    '1.0.0',
    '["demand_surge_detection", "price_movement_tracking", "rating_momentum", "review_momentum", "inventory_signals", "cross_platform_surge", "breakout_candidate_scoring", "emerging_product_discovery", "deterministic_trend_scoring", "selective_gemini_reasoning", "persistent_memory_calibration"]'::jsonb,
    '{"strict_mode": true, "gemini_enabled": true, "min_observations_for_trend": 2, "breakout_threshold": 75.0, "staleness_days": 14}'::jsonb,
    '{"author": "TrendPulse AI Team", "tier": "production"}'::jsonb,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO UPDATE
SET description = EXCLUDED.description,
    capabilities = EXCLUDED.capabilities,
    configuration = EXCLUDED.configuration,
    updated_at = CURRENT_TIMESTAMP;
