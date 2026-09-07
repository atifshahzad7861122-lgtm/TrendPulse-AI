-- =============================================================================
-- TrendPulse AI - Agent 2: Product Categorization & Taxonomy Migration
-- Source of Truth: backend/app/db/models.py
-- Target Platform: Supabase PostgreSQL (Standard PostgreSQL 15+)
-- Version: 006_product_taxonomy_agent.sql
-- =============================================================================

-- =============================================================================
-- 1. TAXONOMY CATEGORIES HIERARCHICAL TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS taxonomy_categories (
    id VARCHAR(64) PRIMARY KEY,
    parent_id VARCHAR(64) REFERENCES taxonomy_categories(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(150) NOT NULL UNIQUE,
    level INTEGER NOT NULL DEFAULT 1,  -- 1 = Category, 2 = Subcategory, 3 = Group, 4 = Product Type
    description TEXT DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_taxonomy_categories_id ON taxonomy_categories(id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_categories_parent_id ON taxonomy_categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_categories_slug ON taxonomy_categories(slug);
CREATE INDEX IF NOT EXISTS idx_taxonomy_categories_level ON taxonomy_categories(level);
CREATE INDEX IF NOT EXISTS idx_taxonomy_categories_is_active ON taxonomy_categories(is_active);

-- =============================================================================
-- 2. PRODUCT TAXONOMY ASSIGNMENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS product_taxonomy_assignments (
    id VARCHAR(64) PRIMARY KEY,
    unified_product_id VARCHAR(64) NOT NULL REFERENCES unified_products(unified_product_id) ON DELETE CASCADE,
    category VARCHAR(150) NOT NULL,
    subcategory VARCHAR(150) NOT NULL DEFAULT 'Unknown',
    product_type VARCHAR(150) NOT NULL DEFAULT 'Unknown',
    taxonomy_path JSONB NOT NULL DEFAULT '[]'::jsonb,
    brand VARCHAR(150),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    classification_method VARCHAR(50) NOT NULL DEFAULT 'keyword_rule', -- "exact_marketplace_map", "brand_rule", "keyword_rule", "memory", "llm", "unknown"
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    agent_id VARCHAR(64) NOT NULL REFERENCES ai_agents(id) ON DELETE CASCADE,
    agent_run_id VARCHAR(64) REFERENCES ai_agent_runs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_id ON product_taxonomy_assignments(id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_unified_id ON product_taxonomy_assignments(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_category ON product_taxonomy_assignments(category);
CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_subcategory ON product_taxonomy_assignments(subcategory);
CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_product_type ON product_taxonomy_assignments(product_type);
CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_brand ON product_taxonomy_assignments(brand);
CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_confidence ON product_taxonomy_assignments(confidence);
CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_needs_review ON product_taxonomy_assignments(needs_review);
CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_method ON product_taxonomy_assignments(classification_method);
CREATE INDEX IF NOT EXISTS idx_taxonomy_assignments_created_at ON product_taxonomy_assignments(created_at);

-- =============================================================================
-- 3. PRODUCT TAXONOMY CANDIDATES (For low confidence & review items)
-- =============================================================================
CREATE TABLE IF NOT EXISTS product_taxonomy_candidates (
    id VARCHAR(64) PRIMARY KEY,
    product_id VARCHAR(100) NOT NULL,
    unified_product_id VARCHAR(64) REFERENCES unified_products(unified_product_id) ON DELETE CASCADE,
    candidate_category VARCHAR(150) NOT NULL,
    candidate_subcategory VARCHAR(150) NOT NULL,
    candidate_product_type VARCHAR(150) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    reason TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_taxonomy_candidates_id ON product_taxonomy_candidates(id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_candidates_product_id ON product_taxonomy_candidates(product_id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_candidates_unified_id ON product_taxonomy_candidates(unified_product_id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_candidates_confidence ON product_taxonomy_candidates(confidence);
CREATE INDEX IF NOT EXISTS idx_taxonomy_candidates_created_at ON product_taxonomy_candidates(created_at);

-- =============================================================================
-- 4. SEED AGENT 2 RECORD IN AI_AGENTS
-- =============================================================================
INSERT INTO ai_agents (id, name, slug, agent_type, status, description, version, capabilities, configuration, metadata_json, created_at, updated_at)
VALUES (
    'agent_categorization',
    'Product Categorization & Taxonomy Agent',
    'categorization',
    'categorization',
    'active',
    'Deterministic and AI-driven hierarchical product classification, attribute extraction, brand normalization, taxonomy path generation, and persistent memory learning.',
    '1.0.0',
    '["brand_recognition", "marketplace_taxonomy_mapping", "keyword_taxonomy_scoring", "attribute_extraction", "gemini_semantic_categorization", "persistent_taxonomy_memory", "candidate_generation"]'::jsonb,
    '{"strict_mode": true, "gemini_enabled": true, "confidence_threshold_high": 0.90, "confidence_threshold_med": 0.75, "review_threshold": 0.50}'::jsonb,
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

-- =============================================================================
-- 5. SEED INITIAL 18 TOP-LEVEL TAXONOMY CATEGORIES
-- =============================================================================
INSERT INTO taxonomy_categories (id, parent_id, name, slug, level, description, is_active, created_at, updated_at)
VALUES
    ('cat_electronics', NULL, 'Electronics', 'electronics', 1, 'Consumer electronics, computing, audio, mobile, smart home, and digital hardware', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_fashion', NULL, 'Fashion', 'fashion', 1, 'Apparel, clothing, footwear, activewear, and outerwear', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_beauty_personal_care', NULL, 'Beauty & Personal Care', 'beauty-personal-care', 1, 'Skincare, haircare, makeup, fragrances, and personal grooming', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_home_living', NULL, 'Home & Living', 'home-living', 1, 'Kitchen, furniture, home decor, bedding, and domestic appliances', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_health_wellness', NULL, 'Health & Wellness', 'health-wellness', 1, 'Vitamins, supplements, medical supplies, and personal well-being', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_sports_fitness', NULL, 'Sports & Fitness', 'sports-fitness', 1, 'Athletic gear, gym equipment, endurance, outdoor recreation, and sports apparel', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_toys_collectibles', NULL, 'Toys & Collectibles', 'toys-collectibles', 1, 'Toys, games, action figures, board games, and collectible novelties', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_automotive', NULL, 'Automotive', 'automotive', 1, 'Car electronics, replacement parts, car care, and automotive accessories', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_groceries_food', NULL, 'Groceries & Food', 'groceries-food', 1, 'Beverages, pantry staples, snacks, and gourmet specialty goods', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_baby_kids', NULL, 'Baby & Kids', 'baby-kids', 1, 'Baby care, nursery items, gear, and children apparel', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_books_media', NULL, 'Books & Media', 'books-media', 1, 'Books, digital media, music, movies, and video games', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_pet_supplies', NULL, 'Pet Supplies', 'pet-supplies', 1, 'Pet food, toys, grooming, and care supplies for domestic animals', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_jewelry_accessories', NULL, 'Jewelry & Accessories', 'jewelry-accessories', 1, 'Fine & fashion jewelry, watches, sunglasses, bags, and luxury accessories', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_tools_hardware', NULL, 'Tools & Hardware', 'tools-hardware', 1, 'Power tools, hand tools, electrical supplies, and building hardware', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_office_stationery', NULL, 'Office & Stationery', 'office-stationery', 1, 'Office supplies, writing instruments, desk organization, and paper products', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_industrial_business', NULL, 'Industrial & Business', 'industrial-business', 1, 'MRO, commercial equipment, test instruments, and industrial supplies', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_other', NULL, 'Other', 'other', 1, 'Miscellaneous and specialized marketplace products', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cat_unknown', NULL, 'Unknown', 'unknown', 1, 'Unclassified marketplace records requiring human or AI review', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO NOTHING;
