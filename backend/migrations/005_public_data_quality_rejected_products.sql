-- =============================================================================
-- TrendPulse AI - Public Data Quality & Rejected Product Database Layer Migration
-- Source of Truth: backend/app/db/models.py
-- Target Platform: Supabase PostgreSQL (Standard PostgreSQL 15+)
-- Version: 005_public_data_quality_rejected_products.sql
-- =============================================================================

-- 1. Ensure Table Exists with All Core & Public Visibility Columns
CREATE TABLE IF NOT EXISTS data_quality_validation_results (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL DEFAULT 'agent_data_quality' REFERENCES ai_agents(id) ON DELETE CASCADE,
    run_id VARCHAR(64) REFERENCES ai_agent_runs(id) ON DELETE SET NULL,
    workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE SET NULL,
    platform VARCHAR(50) NOT NULL,
    source_provider VARCHAR(50) NOT NULL DEFAULT 'direct',
    platform_product_id VARCHAR(100) NOT NULL,
    unified_product_id VARCHAR(64),
    product_title VARCHAR(512) NOT NULL,
    product_name VARCHAR(512),
    original_category VARCHAR(255),
    normalized_category VARCHAR(255) NOT NULL DEFAULT 'Unknown',
    data_quality_category VARCHAR(255) NOT NULL DEFAULT '',
    product_url TEXT,
    image_url TEXT,
    price DOUBLE PRECISION,
    currency VARCHAR(10) NOT NULL DEFAULT 'PKR',
    rating DOUBLE PRECISION,
    review_count INTEGER NOT NULL DEFAULT 0,
    availability BOOLEAN NOT NULL DEFAULT TRUE,
    overall_score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    quality_score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    classification VARCHAR(50) NOT NULL DEFAULT 'valid',  -- "valid", "valid_with_warnings", "needs_review", "rejected"
    is_trusted BOOLEAN NOT NULL DEFAULT TRUE,
    issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    rejection_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    missing_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    invalid_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    suspicious_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    field_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_payload_hash VARCHAR(64),
    used_llm BOOLEAN NOT NULL DEFAULT FALSE,
    llm_used BOOLEAN NOT NULL DEFAULT FALSE,
    llm_provider VARCHAR(50) DEFAULT 'gemini',
    llm_resolution JSONB,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    validated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Add Columns Safely If Table Already Existed
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS agent_id VARCHAR(64) NOT NULL DEFAULT 'agent_data_quality';
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS product_name VARCHAR(512);
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS original_category VARCHAR(255);
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS normalized_category VARCHAR(255) NOT NULL DEFAULT 'Unknown';
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS data_quality_category VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS product_url TEXT;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS price DOUBLE PRECISION;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'PKR';
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS rating DOUBLE PRECISION;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS review_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS availability BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS quality_score DOUBLE PRECISION NOT NULL DEFAULT 100.0;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS rejection_reasons JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS missing_fields JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS invalid_fields JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS suspicious_fields JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS llm_used BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(50) DEFAULT 'gemini';
ALTER TABLE data_quality_validation_results ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- 3. Synchronize Backfill for Any Existing Records
UPDATE data_quality_validation_results
SET 
    product_name = COALESCE(product_name, product_title),
    quality_score = COALESCE(quality_score, overall_score),
    llm_used = COALESCE(llm_used, used_llm),
    data_quality_category = CASE 
        WHEN LOWER(classification) = 'rejected' THEN 'Data Quality Issues'
        ELSE ''
    END,
    normalized_category = CASE 
        WHEN normalized_category IS NULL OR normalized_category = '' THEN 'Unknown'
        ELSE normalized_category
    END
WHERE product_name IS NULL OR quality_score IS NULL OR normalized_category IS NULL;

-- 4. Create Performance & Filter Indexes
CREATE INDEX IF NOT EXISTS idx_dq_validation_platform ON data_quality_validation_results(platform);
CREATE INDEX IF NOT EXISTS idx_dq_validation_source_provider ON data_quality_validation_results(source_provider);
CREATE INDEX IF NOT EXISTS idx_dq_validation_classification ON data_quality_validation_results(classification);
CREATE INDEX IF NOT EXISTS idx_dq_validation_normalized_category ON data_quality_validation_results(normalized_category);
CREATE INDEX IF NOT EXISTS idx_dq_validation_validated_at ON data_quality_validation_results(validated_at DESC);
CREATE INDEX IF NOT EXISTS idx_dq_validation_product_id ON data_quality_validation_results(platform_product_id);
CREATE INDEX IF NOT EXISTS idx_dq_public_rejected_feed ON data_quality_validation_results(classification, validated_at DESC);
CREATE INDEX IF NOT EXISTS idx_dq_public_category_filter ON data_quality_validation_results(normalized_category, classification);
CREATE INDEX IF NOT EXISTS idx_dq_public_platform_filter ON data_quality_validation_results(platform, classification);

-- 5. Safe Public Read View (Hides Sensitive Memory, Prompts, IDs, Error Traces)
CREATE OR REPLACE VIEW public_data_quality_feed_view AS
SELECT
    id AS record_id,
    COALESCE(product_name, product_title) AS product_name,
    platform,
    source_provider AS provider,
    data_quality_category,
    original_category,
    COALESCE(normalized_category, 'Unknown') AS normalized_category,
    price,
    currency,
    rating,
    review_count,
    image_url AS image,
    product_url,
    quality_score,
    classification,
    CASE
        WHEN LOWER(classification) = 'rejected' THEN 'Rejected By Data Quality Checks'
        WHEN LOWER(classification) = 'valid_with_warnings' THEN 'Real Data With Warnings'
        WHEN LOWER(classification) = 'needs_review' THEN 'Needs Review'
        ELSE 'Real Data'
    END AS public_status,
    issues,
    warnings,
    rejection_reasons,
    missing_fields,
    invalid_fields,
    suspicious_fields,
    llm_used,
    validated_at AS last_validated_time
FROM data_quality_validation_results
ORDER BY validated_at DESC;
