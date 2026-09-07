-- =============================================================================
-- TrendPulse AI - AI Agents Framework & Data Quality Validation Migration
-- Source of Truth: backend/app/db/models.py
-- Target Platform: Supabase PostgreSQL (Standard PostgreSQL 15+)
-- Version: 004_ai_agents_and_data_quality.sql
-- =============================================================================

-- =============================================================================
-- 1. AI AGENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS ai_agents (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    agent_type VARCHAR(50) NOT NULL,  -- "data_quality", "trend_prediction", "market_arbiter", etc.
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- "active", "paused", "disabled", "error"
    description TEXT NOT NULL DEFAULT '',
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_agents_id ON ai_agents(id);
CREATE INDEX IF NOT EXISTS idx_ai_agents_slug ON ai_agents(slug);
CREATE INDEX IF NOT EXISTS idx_ai_agents_type ON ai_agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_ai_agents_status ON ai_agents(status);

-- Seed Agent 1: Data Quality & Validation Agent
INSERT INTO ai_agents (id, name, slug, agent_type, status, description, version, capabilities, configuration, metadata_json, created_at, updated_at)
VALUES (
    'agent_data_quality',
    'Data Quality & Validation Agent',
    'data-quality',
    'data_quality',
    'active',
    'Continuous marketplace data validation, anomaly detection, deterministic scoring (0-100), and selective Gemini LLM ambiguity resolution.',
    '1.0.0',
    '["missing_field_detection", "impossible_value_sanity", "freshness_enforcement", "duplicate_detection", "deterministic_scoring", "gemini_ambiguity_resolution", "provider_memory_learning"]'::jsonb,
    '{"strict_mode": true, "gemini_enabled": true, "rejection_threshold": 50.0, "warning_threshold": 70.0, "staleness_days": 30}'::jsonb,
    '{"author": "TrendPulse AI Team", "tier": "production"}'::jsonb,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- 2. AI AGENT RUNS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS ai_agent_runs (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES ai_agents(id) ON DELETE CASCADE,
    workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE SET NULL,
    run_type VARCHAR(50) NOT NULL DEFAULT 'scheduled',  -- "scheduled", "ingestion_stream", "ad_hoc_batch", "manual"
    status VARCHAR(50) NOT NULL DEFAULT 'completed',  -- "pending", "running", "completed", "failed"
    trigger_source VARCHAR(100) NOT NULL DEFAULT 'system',
    items_processed INTEGER NOT NULL DEFAULT 0,
    items_valid INTEGER NOT NULL DEFAULT 0,
    items_warning INTEGER NOT NULL DEFAULT 0,
    items_needs_review INTEGER NOT NULL DEFAULT 0,
    items_rejected INTEGER NOT NULL DEFAULT 0,
    avg_quality_score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    gemini_calls_count INTEGER NOT NULL DEFAULT 0,
    execution_time_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_agent_runs_id ON ai_agent_runs(id);
CREATE INDEX IF NOT EXISTS idx_ai_agent_runs_agent_id ON ai_agent_runs(agent_id);
CREATE INDEX IF NOT EXISTS idx_ai_agent_runs_workspace_id ON ai_agent_runs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_ai_agent_runs_status ON ai_agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_ai_agent_runs_created_at ON ai_agent_runs(created_at DESC);

-- =============================================================================
-- 3. AI AGENT MEMORY TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS ai_agent_memory (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES ai_agents(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,  -- "missing_fields_pattern", "provider_formatting", "duplicate_pattern", "category_anomaly", "reliability_score"
    memory_key VARCHAR(255) NOT NULL,
    memory_value JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_agent_memory_key UNIQUE (agent_id, memory_type, memory_key)
);

CREATE INDEX IF NOT EXISTS idx_ai_agent_memory_agent_id ON ai_agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_ai_agent_memory_type ON ai_agent_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_ai_agent_memory_key ON ai_agent_memory(memory_key);
CREATE INDEX IF NOT EXISTS idx_ai_agent_memory_updated_at ON ai_agent_memory(updated_at DESC);

-- =============================================================================
-- 4. AI AGENT MEMORY EVENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS ai_agent_memory_events (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES ai_agents(id) ON DELETE CASCADE,
    memory_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- "created", "updated", "decayed", "invalidated", "reinforced"
    old_value JSONB,
    new_value JSONB NOT NULL,
    reason VARCHAR(512) NOT NULL DEFAULT '',
    trigger_run_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_memory_events_agent_id ON ai_agent_memory_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_ai_memory_events_memory_id ON ai_agent_memory_events(memory_id);
CREATE INDEX IF NOT EXISTS idx_ai_memory_events_created_at ON ai_agent_memory_events(created_at DESC);

-- =============================================================================
-- 5. DATA QUALITY VALIDATION RESULTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS data_quality_validation_results (
    id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) REFERENCES ai_agent_runs(id) ON DELETE SET NULL,
    workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE SET NULL,
    platform VARCHAR(50) NOT NULL,
    source_provider VARCHAR(50) NOT NULL DEFAULT 'direct',
    platform_product_id VARCHAR(100) NOT NULL,
    unified_product_id VARCHAR(64),
    product_title VARCHAR(512) NOT NULL,
    overall_score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    classification VARCHAR(50) NOT NULL DEFAULT 'valid',  -- "valid", "valid_with_warnings", "needs_review", "rejected"
    is_trusted BOOLEAN NOT NULL DEFAULT TRUE,
    issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    field_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_payload_hash VARCHAR(64),
    used_llm BOOLEAN NOT NULL DEFAULT FALSE,
    llm_resolution JSONB,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    validated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dq_validation_platform ON data_quality_validation_results(platform);
CREATE INDEX IF NOT EXISTS idx_dq_validation_provider ON data_quality_validation_results(source_provider);
CREATE INDEX IF NOT EXISTS idx_dq_validation_classification ON data_quality_validation_results(classification);
CREATE INDEX IF NOT EXISTS idx_dq_validation_product_id ON data_quality_validation_results(platform_product_id);
CREATE INDEX IF NOT EXISTS idx_dq_validation_unified_id ON data_quality_validation_results(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_dq_validation_created_at ON data_quality_validation_results(created_at DESC);
