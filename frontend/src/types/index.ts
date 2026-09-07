export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data: T;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_verified: boolean;
  workspace_id?: string;
  role: string;
  avatar_url?: string;
}

export interface Workspace {
  id: string;
  name: string;
  industry: string;
  use_case: string;
  currency: string;
  default_dashboard: string;
  connected_sources: string[];
  is_setup_complete: boolean;
  owner_id: string;
}

export interface Product {
  id: string;
  name: string;
  category: string;
  sub_category?: string;
  trend_score: number;
  growth_rate: number;
  volume: number;
  velocity_label: string;
  status: string;
  price_range: string;
  primary_platform: string;
  platforms: string[];
  platform_shares: Record<string, number>;
  historical_scores: Array<{ date: string; score: number; volume: number }>;
  historical_prices: Array<{ date: string; price: number }>;
  ai_summary: string;
  signals_count: number;
  sentiment_score: number;
  image_url?: string;
  tags: string[];
  is_watchlisted: boolean;
  provenance?: string;
  observation_count?: number;
  historical_observation_count?: number;
  data_sufficiency?: string;
  raw_data?: Record<string, any>;
}

export interface IntelligenceSummary {
  environment: string;
  total_products: number;
  total_alerts: number;
  total_data_sources: number;
  metrics_summary: {
    trend_score: { mean: number; median: number; percentiles: Record<string, number> };
    growth_rate: { mean: number; median: number; percentiles: Record<string, number> };
    volume: { mean: number; median: number; percentiles: Record<string, number> };
    sentiment: { mean: number; median: number };
    demand_score: { mean: number; percentiles: Record<string, number> };
    viral_score: { mean: number; percentiles: Record<string, number> };
  };
  prediction_intelligence: {
    prediction_coverage_count: number;
    prediction_coverage_percent: number;
    backtest: Record<string, any>;
  };
  version_metadata: Record<string, string>;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  product_count: number;
  avg_trend_score: number;
  growth_rate: number;
  velocity_label: string;
  top_platforms: string[];
  description: string;
  provenance?: string;
  observation_count?: number;
}

export interface PlatformMetrics {
  id: string;
  name: string;
  slug: string;
  icon: string;
  total_signals: number;
  active_trends: number;
  velocity_growth: number;
  market_share: number;
  status: string;
  provenance?: string;
  observation_count?: number;
  recent_spikes: Array<{ hashtag: string; growth: string; signals: string }>;
}

export interface MetricCard {
  title: string;
  value: string;
  change: string;
  is_positive: boolean;
  subtext: string;
  icon: string;
}

export interface TrendPoint {
  timestamp: string;
  score: number;
  volume: number;
  sentiment: number;
  platform_tiktok: number;
  platform_daraz: number;
  platform_instagram: number;
  platform_youtube: number;
}

export interface LiveSignalItem {
  id: string;
  text: string;
  platform: string;
  growth: string;
  timestamp: string;
  category: string;
  product_id?: string;
  product_name?: string;
  signal_value?: string;
}

export interface DashboardProductItem {
  id: string;
  product_id?: string;
  name: string;
  category: string;
  price?: number;
  price_formatted?: string;
  original_price?: number;
  original_price_formatted?: string;
  discount?: number;
  discount_label?: string;
  rating?: number;
  review_count?: number;
  seller_name?: string;
  seller_rating?: number;
  in_stock?: boolean;
  location?: string;
  image_url?: string;
  product_url?: string;
  platform: string;
  source?: string;
  trend_score?: number;
  growth_rate?: number;
  volume?: number;
  velocity_label?: string;
  price_range?: string;
}

export interface DashboardSummary {
  metrics: MetricCard[];
  live_signals: LiveSignalItem[];
  top_surging: DashboardProductItem[];
  total_trends_monitored: number;
  system_status: string;
  is_live?: boolean;
  data_source?: "daraz_live" | "database_cache" | "none" | string;
  last_synced_at?: string | null;
  data_age_seconds?: number | null;
}

export interface Alert {
  id: string;
  title: string;
  description: string;
  severity: "Critical" | "Warning" | "Info";
  category: string;
  product_id?: string;
  product_name?: string;
  platform?: string;
  is_read: boolean;
  is_resolved: boolean;
  created_at: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  link?: string;
  created_at: string;
}

export interface Report {
  id: string;
  title: string;
  template: string;
  time_range: string;
  status: string;
  progress: number;
  category?: string;
  platforms: string[];
  key_findings: string[];
  ai_takeaways: string;
  total_signals_analyzed: number;
  high_conviction_count: number;
  products_evaluated?: number;
  provenance?: string;
  data_sufficiency?: string;
  observation_count?: number;
  historical_observation_count?: number;
  source_breakdown?: Record<string, number>;
  pdf_url?: string;
  csv_url?: string;
  created_by: string;
  created_at: string;
}

export interface DataSource {
  id: string;
  name: string;
  slug: string;
  icon: string;
  description: string;
  status: "Connected" | "Disconnected" | "Syncing" | "Error" | "Coming Soon" | "Simulated" | string;
  last_sync?: string;
  sync_frequency: string;
  records_synced: number;
  health_score: number;
}

export interface IngestionResult {
  source: string;
  is_live: boolean;
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  records_received: number;
  records_normalized: number;
  records_matched: number;
  records_unmatched: number;
  records_ambiguous: number;
  records_inserted: number;
  records_updated: number;
  records_skipped: number;
  records_failed: number;
  alerts_created: number;
  notifications_created: number;
  status: string;
  errors: string[];
}

export interface DataSourceConfigStatus {
  youtube: {
    is_live_configured: boolean;
    mode: "LIVE" | "MOCK";
    max_results: number;
    region_code: string;
    language: string;
  };
  platforms?: Record<string, {
    type: string;
    status: string;
    live: boolean;
  }>;
  environment: string;
}

export interface SearchResultItem {
  id: string;
  category: "products" | "categories" | "platforms" | "reports" | "alerts";
  title: string;
  subtitle: string;
  link: string;
  badge?: string;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchResultItem[];
}

export interface UserSettings {
  user_id: string;
  full_name: string;
  email: string;
  avatar_url?: string;
  role: string;
  company_name: string;
  timezone: string;
  currency: string;
  email_notifications: boolean;
  alert_critical_only: boolean;
  weekly_digest: boolean;
  ai_model_preference: string;
  ai_confidence_threshold: number;
  auto_generate_reports: boolean;
  dark_mode: boolean;
  table_dense_view: boolean;
  live_ticker_enabled: boolean;
}

export interface DarazProduct {
  platform: string;
  product_id: string;
  name: string;
  price: number;
  original_price: number;
  discount: number;
  discount_label?: string;
  currency: string;
  rating: number;
  review_count: number;
  seller_name?: string;
  seller_id?: string;
  brand?: string;
  category?: string;
  image_url?: string;
  product_url?: string;
  sku?: string;
  in_stock: boolean;
  location?: string;
  sold_count: number;
  source: string;
  raw_data?: any;
}

export interface DarazSellerInfo {
  seller_id?: string;
  name?: string;
  shop_id?: number;
  seller_url?: string;
  positive_seller_rating?: string;
  ship_on_time?: string;
  chat_response_rate?: string;
  chat_url?: string;
}

export interface DarazSkuVariant {
  sku_id?: string;
  sku_name?: string;
  price?: number;
  original_price?: number;
  in_stock: boolean;
  image?: string;
}

export interface DarazProductDetails {
  platform: string;
  product_id: string;
  name: string;
  price: number;
  original_price: number;
  discount: number;
  discount_label?: string;
  currency: string;
  rating: number;
  review_count: number;
  in_stock: boolean;
  brand?: string;
  category?: string;
  category_breadcrumbs: string[];
  description?: string;
  highlights: string[];
  specifications: Record<string, any>;
  warranty?: string;
  images: string[];
  main_image?: string;
  product_url?: string;
  seller?: DarazSellerInfo;
  sku_variants: DarazSkuVariant[];
  ratings_breakdown?: Record<string, any>;
  qa_list?: any[];
  reviews_sample?: any[];
  source: string;
}

export interface DarazCategory {
  id: string;
  name: string;
  icon?: string;
  url?: string;
  level: number;
  subcategories: { id: string; name: string; url?: string }[];
}

export interface DarazSearchResponse {
  query: string;
  page: number;
  total_products: number;
  has_next: boolean;
  source: string;
  products: DarazProduct[];
}

export interface LiveSignalItem {
  id: string;
  type: "PRODUCT" | "PRICE" | "RATING" | "SELLER" | "TREND" | "NEW" | "AVAILABILITY" | "CATEGORY" | string;
  platform: "daraz" | "youtube" | "tiktok" | "instagram" | "facebook" | string;
  title: string;
  description: string;
  product_id?: string;
  product_name?: string;
  signal_value?: string;
  timestamp: string;
  source: string;
  metadata?: Record<string, any>;
}

export interface LiveSignalsResponse {
  signals: LiveSignalItem[];
  total: number;
  generated_at: string;
}

export interface ShopifyProduct {
  id: string;
  store_domain: string;
  product_id: string;
  title: string;
  handle?: string;
  product_url: string;
  image_url?: string;
  images: string[];
  vendor?: string;
  product_type?: string;
  category?: string;
  tags: string[];
  price: number;
  price_formatted: string;
  compare_at_price?: number;
  compare_at_price_formatted?: string;
  discount_percentage: number;
  discount_label?: string;
  currency: string;
  available: boolean;
  rating: number;
  review_count: number;
  source_provider: string;
  variants_count: number;
  first_seen_at: string;
  last_seen_at: string;
  last_synced_at: string;
  raw_data?: Record<string, any>;
}

export interface ShopifyProductListResponse {
  items: ShopifyProduct[];
  total: number;
  page: number;
  limit: number;
  store_domain?: string;
  source_platform: string;
  source_provider: string;
  is_live: boolean;
  last_synced_at?: string;
  data_age_seconds?: number;
  message?: string;
}

export interface ShopifySyncRequest {
  store_domain: string;
  limit?: number;
  page?: number;
  collection?: string;
  force_live?: boolean;
}

export interface ShopifySyncResponse {
  success: boolean;
  store_domain: string;
  source_platform: string;
  source_provider: string;
  is_live: boolean;
  status: "success" | "cached" | "unavailable" | "failed" | string;
  products_fetched: number;
  products_inserted: number;
  products_updated: number;
  snapshots_created: number;
  last_synced_at?: string;
  data_age_seconds?: number;
  provider_attempts: Array<{
    provider_name: string;
    priority: number;
    status: string;
    error_code?: number;
    error_message?: string;
    duration_ms?: number;
  }>;
  products: ShopifyProduct[];
  message: string;
}

export interface ShopifyProviderHealth {
  provider_name: string;
  display_name: string;
  priority: number;
  enabled: boolean;
  status: "healthy" | "degraded" | "rate_limited" | "unhealthy" | string;
  consecutive_failures: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  rate_limited_requests: number;
  success_rate: number;
  last_success_at?: string;
  last_failure_at?: string;
  cooldown_until?: string;
  is_in_cooldown: boolean;
  cooldown_remaining_seconds: number;
  last_error_code?: number;
  last_error_message?: string;
}

export interface ShopifyStatusResponse {
  overall_status: "healthy" | "degraded" | "all_down" | "cached_fallback" | string;
  preferred_provider: string;
  active_providers_count: number;
  total_products_stored: number;
  total_snapshots_stored: number;
  providers: ShopifyProviderHealth[];
  recent_sync_runs: any[];
}

export interface UnifiedPlatformListing {
  id: string;
  unified_product_id: string;
  platform: string;
  platform_product_id: string;
  store_domain?: string;
  product_url: string;
  title: string;
  normalized_title: string;
  price: number;
  price_formatted: string;
  original_price?: number;
  original_price_formatted?: string;
  currency: string;
  discount_percentage: number;
  discount_label?: string;
  seller_name?: string;
  vendor?: string;
  rating: number;
  review_count: number;
  available: boolean;
  image_url?: string;
  source_provider: string;
  last_synced_at: string;
  completeness_score: number;
  match_confidence?: number;
  match_method?: string;
  match_status?: string;
  raw_title?: string;
  raw_data?: Record<string, any>;
}

export interface PriceComparisonItem {
  platform: string;
  store_domain?: string;
  price: number;
  price_formatted: string;
  original_price?: number;
  original_price_formatted?: string;
  currency: string;
  discount_percentage: number;
  discount_label?: string;
  available: boolean;
  seller_or_vendor?: string;
  product_url: string;
  last_updated: string;
}

export interface PlatformComparisonItem {
  platform: string;
  store_domain?: string;
  title: string;
  price: number;
  price_formatted: string;
  currency: string;
  discount_percentage: number;
  rating: number;
  review_count: number;
  available: boolean;
  seller_name?: string;
  vendor?: string;
  product_url: string;
  image_url?: string;
  source_provider: string;
}

export interface UnifiedProduct {
  id: string;
  unified_product_id: string;
  canonical_name: string;
  normalized_name: string;
  brand?: string;
  category?: string;
  subcategory?: string;
  product_type?: string;
  taxonomy_path?: string[];
  attributes?: Record<string, any>;
  category_confidence?: number;
  classification_method?: string;
  needs_review?: boolean;
  description?: string;
  primary_image?: string;
  identifiers: Record<string, any>;
  platforms: string[];
  platform_count: number;
  listings_count: number;
  lowest_price: number;
  highest_price: number;
  average_price: number;
  primary_currency: string;
  price_range_formatted: string;
  avg_rating: number;
  total_reviews: number;
  completeness_score: number;
  first_seen_at: string;
  last_seen_at: string;
  last_synced_at: string;
}


export interface UnifiedProductDetailResponse {
  unified_product: UnifiedProduct;
  platform_listings: UnifiedPlatformListing[];
  price_comparison: PriceComparisonItem[];
  platform_comparison: PlatformComparisonItem[];
  match_audit?: Record<string, any>;
}

export interface UnifiedProductListResponse {
  items: UnifiedProduct[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  filters_applied: Record<string, any>;
}

export interface UnifiedHistoricalPoint {
  timestamp: string;
  platform: string;
  store_domain?: string;
  price: number;
  currency: string;
  available: boolean;
  rating: number;
  review_count: number;
  source_provider: string;
}

export interface UnifiedProductHistoryResponse {
  unified_product_id: string;
  canonical_name: string;
  timeline: UnifiedHistoricalPoint[];
  snapshots?: UnifiedHistoricalPoint[];
  total_observations: number;
  platforms: string[];
}

export interface UnifiedSearchResponse {
  query: string;
  total_matches: number;
  items: UnifiedProduct[];
  page: number;
  limit: number;
}

export interface DataFreshnessMeta {
  source_platforms: string[];
  source_providers: string[];
  last_synced_at?: string;
  data_age_seconds: number;
  data_status: 'live' | 'cached';
}

export interface AIProductAnalysisResponse {
  unified_product_id: string;
  canonical_name: string;
  summary: string;
  category?: string;
  confidence_score: number;
  key_signals: string[];
  opportunities: string[];
  risks: string[];
  recommendations: string[];
  pricing_analysis: Record<string, any>;
  data_freshness: DataFreshnessMeta;
  is_cached: boolean;
  prompt_version: string;
  provider: string;
  model: string;
  tokens_used: number;
  latency_ms: number;
}

export interface AIProductSummaryResponse {
  unified_product_id: string;
  canonical_name: string;
  executive_summary: string;
  key_takeaways: string[];
  target_audience?: string;
  competitive_edge?: string;
  data_freshness: DataFreshnessMeta;
  is_cached: boolean;
  prompt_version: string;
  provider: string;
  model: string;
  tokens_used: number;
  latency_ms: number;
}

export interface AIMarketComparisonResponse {
  unified_product_id: string;
  canonical_name: string;
  cross_platform_overview: string;
  price_arbitrage_analysis: string;
  seller_and_vendor_landscape: string;
  platform_comparison_breakdown: Array<{
    platform: string;
    competitive_strength: string;
    risk_factor: string;
  }>;
  recommendations: string[];
  data_freshness: DataFreshnessMeta;
  is_cached: boolean;
  prompt_version: string;
  provider: string;
  model: string;
  tokens_used: number;
  latency_ms: number;
}

export interface AITrendAnalysisResponse {
  unified_product_id: string;
  canonical_name: string;
  trend_trajectory: string;
  velocity_assessment: string;
  volatility_risk: string;
  historical_price_action: string;
  predictive_outlook_30d: string;
  data_freshness: DataFreshnessMeta;
  is_cached: boolean;
  prompt_version: string;
  provider: string;
  model: string;
  tokens_used: number;
  latency_ms: number;
}

export interface AICategoryAnalysisResponse {
  category: string;
  market_overview: string;
  demand_state: string;
  price_range_summary: string;
  growth_drivers: string[];
  threats_and_challenges: string[];
  strategic_advice: string[];
  data_freshness: DataFreshnessMeta;
  is_cached: boolean;
  prompt_version: string;
  provider: string;
  model: string;
  tokens_used: number;
  latency_ms: number;
}

export interface LLMUsageSummaryResponse {
  total_requests: number;
  successful_requests: number;
  cached_requests: number;
  failed_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  average_latency_ms: number;
}

// -----------------------------------------------------------------------------
// Agent 1: Data Quality & Validation Agent Types
// -----------------------------------------------------------------------------

export interface DataQualityRuleViolation {
  field: string;
  rule_name: string;
  severity: "critical" | "warning" | "info";
  message: string;
  observed_value?: any;
  penalty_score: number;
}

export interface DataQualityValidationResponse {
  id: string;
  platform: string;
  source_provider: string;
  platform_product_id: string;
  unified_product_id?: string;
  product_title: string;
  overall_score: number;
  classification: "valid" | "valid_with_warnings" | "needs_review" | "rejected";
  is_trusted: boolean;
  issues: DataQualityRuleViolation[];
  warnings: DataQualityRuleViolation[];
  field_scores: Record<string, number>;
  used_llm: boolean;
  llm_resolution?: {
    extracted_brand?: string;
    mapped_category?: string;
    is_spam?: boolean;
    is_duplicate?: boolean;
    quality_assessment?: string;
    confidence?: number;
    tokens_used?: number;
    provider?: string;
    model?: string;
  };
  validated_at: string;
  run_id?: string;
}

export interface DataQualityBatchValidationResponse {
  run_id: string;
  total_processed: number;
  valid_count: number;
  warning_count: number;
  needs_review_count: number;
  rejected_count: number;
  avg_quality_score: number;
  gemini_calls_count: number;
  execution_time_ms: number;
  results: DataQualityValidationResponse[];
}

export interface ProviderReliabilityMetric {
  provider: string;
  platform: string;
  total_evaluated: number;
  valid_rate: number;
  warning_rate: number;
  rejection_rate: number;
  avg_score: number;
  top_issues: string[];
}

export interface DataQualityStatusResponse {
  agent_id: string;
  agent_name: string;
  status: string;
  version: string;
  capabilities: string[];
  total_runs: number;
  total_products_validated: number;
  valid_count: number;
  warning_count: number;
  needs_review_count: number;
  rejected_count: number;
  overall_average_score: number;
  total_memory_items: number;
  provider_reliabilities: ProviderReliabilityMetric[];
  last_run_at?: string;
}

export interface DataQualityMemoryItem {
  id: string;
  agent_id: string;
  memory_type: string;
  memory_key: string;
  memory_value: Record<string, any>;
  confidence_score: number;
  occurrence_count: number;
  last_observed_at: string;
  updated_at: string;
}

export interface DataQualityMemoryListResponse {
  items: DataQualityMemoryItem[];
  total: number;
}

export interface AIAgentMemoryEvent {
  id: string;
  agent_id: string;
  memory_id: string;
  event_type: string;
  old_value?: Record<string, any>;
  new_value?: Record<string, any>;
  reason?: string;
  trigger_run_id?: string;
  created_at: string;
}

export interface AIAgentRunItem {

  id: string;
  agent_id: string;
  workspace_id?: string;
  run_type: string;
  status: string;
  trigger_source: string;
  items_processed: number;
  items_valid: number;
  items_warning: number;
  items_needs_review: number;
  items_rejected: number;
  avg_quality_score: number;
  gemini_calls_count: number;
  execution_time_ms: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  created_at: string;
}

export interface DataQualityRunHistoryResponse {
  runs: AIAgentRunItem[];
  total: number;
}

export interface DataQualityValidationListResponse {
  items: DataQualityValidationResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface PublicDataQualityItem {
  id: string;
  product_id?: string;
  product_name: string;
  platform: string;
  provider: string;
  data_quality_category: string;

  original_category?: string;
  normalized_category: string;
  price?: number;
  currency: string;
  rating?: number;
  review_count: number;
  availability: boolean;
  image?: string;
  product_url?: string;
  quality_score: number;
  classification: string;
  public_status: string;
  issues: Array<{
    field: string;
    rule_name: string;
    severity: string;
    message: string;
    observed_value?: any;
    penalty_score: number;
  }>;
  warnings: Array<{
    field: string;
    rule_name: string;
    severity: string;
    message: string;
    observed_value?: any;
    penalty_score: number;
  }>;
  rejection_reasons: string[];
  missing_fields: string[];
  invalid_fields: string[];
  suspicious_fields: string[];
  llm_used: boolean;
  last_validated_time: string;
}

export interface PublicDataQualityFeedResponse {
  items: PublicDataQualityItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PublicDataQualityStatsResponse {
  total_inspected: number;
  total_rejected: number;
  total_warnings: number;
  total_valid: number;
  rejection_rate: number;
  clean_rate: number;
  average_quality_score: number;
  top_rejection_reasons: Array<{ reason: string; count: number }>;
  platform_breakdown: Array<{
    platform: string;
    total: number;
    rejected: number;
    valid: number;
    warnings: number;
  }>;
  category_breakdown: Array<{
    category: string;
    total: number;
    rejected: number;
  }>;
  last_updated: string;
}

export interface PublicDataQualityHistoryResponse {
  platform: string;
  product_id: string;
  total_evaluations: number;
  history: PublicDataQualityItem[];
}

// -----------------------------------------------------------------------------
// Agent 2: Product Categorization & Taxonomy Agent Types
// -----------------------------------------------------------------------------

export interface TaxonomyCategoryItem {
  id: string;
  parent_id?: string;
  name: string;
  slug: string;
  level: number;
  description: string;
  is_active: boolean;
  product_count: number;
  created_at: string;
  updated_at: string;
}

export interface TaxonomyTreeNode {
  id: string;
  parent_id?: string;
  name: string;
  slug: string;
  level: number;
  description: string;
  is_active: boolean;
  product_count: number;
  children: TaxonomyTreeNode[];
}

export interface TaxonomyTreeResponse {
  total_nodes: number;
  categories: TaxonomyTreeNode[];
}

export interface TaxonomyCategoriesListResponse {
  total: number;
  items: TaxonomyCategoryItem[];
}

export interface TaxonomySearchResult {
  id: string;
  name: string;
  slug: string;
  level: number;
  path: string[];
  product_count: number;
}

export interface TaxonomySearchResponse {
  query: string;
  total: number;
  results: TaxonomySearchResult[];
}

export interface ProductTaxonomyAssignmentResponse {
  id: string;
  unified_product_id: string;
  category: string;
  subcategory: string;
  product_type: string;
  taxonomy_path: string[];
  brand?: string;
  attributes: Record<string, any>;
  confidence: number;
  classification_method: string;
  needs_review: boolean;
  agent_id: string;
  agent_run_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ProductTaxonomyHistoryResponse {
  unified_product_id: string;
  total: number;
  items: ProductTaxonomyAssignmentResponse[];
}

export interface AgentCategorizationMemoryItem {
  id: string;
  agent_id: string;
  memory_type: string;
  memory_key: string;
  memory_value: Record<string, any>;
  confidence_score: number;
  occurrence_count: number;
  last_observed_at: string;
  created_at: string;
  updated_at: string;
}

export interface AgentCategorizationMemoryListResponse {
  agent_id: string;
  total: number;
  items: AgentCategorizationMemoryItem[];
}

export interface ProductTaxonomyCandidateItem {
  id: string;
  product_id: string;
  unified_product_id: string;
  candidate_category: string;
  candidate_subcategory: string;
  candidate_product_type: string;
  confidence: number;
  reason: string;
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface ProductMatchDecisionItem {
  id: string;
  product_a_id: string;
  product_b_id?: string;
  unified_product_id?: string;
  platform_a: string;
  platform_b?: string;
  decision: string;
  confidence: number;
  match_method: string;
  reasons: string[];
  conflicts: string[];
  variant_attributes: Record<string, any>;
  base_product_id?: string;
  llm_used: boolean;
  llm_provider?: string;
  llm_model?: string;
  agent_id: string;
  agent_run_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ProductMatchHistoryResponse {
  product_id: string;
  total: number;
  items: ProductMatchDecisionItem[];
}

export interface ProductMatchCandidateItem {
  id: string;
  unified_product_id: string;
  candidate_unified_id: string;
  platform: string;
  platform_product_id: string;
  confidence_score: number;
  method: string;
  status: string;
  reasons: string[];
  product_a_title?: string;
  product_b_title?: string;
  conflicts?: string[];
  variant_attributes?: Record<string, any>;
  created_at: string;
}

export interface EntityMatchingStatsItem {
  total_evaluations: number;
  exact_matches: number;
  high_confidence_matches: number;
  probable_matches: number;
  variants_detected: number;
  related_products: number;
  no_matches: number;
  review_queue_count: number;
  deterministic_match_rate: number;
  llm_match_rate: number;
  memory_hit_count: number;
  average_confidence: number;
}

export interface EntityMatchingMemoryItem {
  id: string;
  agent_id: string;
  memory_type: string;
  memory_key: string;
  memory_value: Record<string, any>;
  confidence_score: number;
  occurrence_count: number;
  last_observed_at: string;
  created_at: string;
  updated_at: string;
}

export interface EntityMatchingMemoryListResponse {
  agent_id: string;
  total: number;
  items: EntityMatchingMemoryItem[];
}

// ==========================================
// Agent 04: Trend Detection & Signal Discovery Types
// ==========================================

export type TrendSignalType =
  | 'demand_surge'
  | 'price_drop'
  | 'price_increase'
  | 'large_discount'
  | 'price_volatility'
  | 'price_movement'
  | 'rating_momentum'
  | 'review_momentum'
  | 'out_of_stock'
  | 'restocked'
  | 'cross_platform_surge'
  | 'breakout_candidate'
  | 'emerging_product'
  | 'declining_product'
  | 'unusual_activity';

export type TrendDirection = 'up' | 'down' | 'stable' | 'volatile';
export type TrendSeverity = 'low' | 'medium' | 'high' | 'critical';
export type TrendState = 'breakout' | 'accelerating' | 'emerging' | 'stable' | 'cooling' | 'declining' | 'insufficient_data';
export type TrendFreshnessStatus = 'fresh' | 'recent' | 'stale' | 'insufficient_data';

export interface TrendObservationItem {
  id: string;
  unified_product_id: string;
  platform: string;
  metric_type: 'price' | 'rating' | 'review_count' | 'availability' | 'demand_score';
  metric_value: number;
  previous_value?: number;
  change_value?: number;
  change_percent?: number;
  observed_at: string;
  created_at: string;
}

export interface TrendSignalItem {
  id: string;
  unified_product_id: string;
  signal_type: TrendSignalType;
  signal_strength: number; // 0.0 - 100.0
  direction: TrendDirection;
  severity: TrendSeverity;
  status: 'active' | 'resolved' | 'suppressed';
  confidence: number;
  evidence: Record<string, any>;
  platforms: string[];
  fingerprint: string;
  detected_at: string;
  expires_at?: string;
  resolved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TrendScoreBreakdownItem {
  demand_review_score: number;
  price_health_score: number;
  cross_platform_score: number;
  inventory_health_score: number;
  freshness_confidence_score: number;
  total_trend_score: number;
  trend_state: TrendState;
}

export interface ProductTrendSummaryItem {
  unified_product_id: string;
  canonical_name: string;
  brand?: string;
  category?: string;
  platforms: string[];
  trend_score: number;
  trend_state: TrendState;
  confidence: number;
  freshness_status: TrendFreshnessStatus;
  active_signals: TrendSignalItem[];
  score_breakdown: TrendScoreBreakdownItem;
  recent_observations: TrendObservationItem[];
  last_analyzed_at: string;
}

export interface TrendSignalCandidateItem {
  id: string;
  unified_product_id: string;
  candidate_type: string;
  composite_score: number;
  confidence: number;
  status: 'pending_review' | 'confirmed' | 'rejected' | 'auto_promoted';
  reasons: string[];
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface AgentTrendDetectionStatsItem {
  total_signals_detected: number;
  active_signals_count: number;
  breakout_candidates_count: number;
  high_severity_signals: number;
  multi_platform_signals: number;
  average_trend_score: number;
  signals_by_type: Record<string, number>;
  signals_by_severity: Record<string, number>;
  signals_by_direction: Record<string, number>;
}

export interface TrendSignalsListResponse {
  items: TrendSignalItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface TrendCandidatesListResponse {
  items: TrendSignalCandidateItem[];
  total: number;
}


// ============================================================================
// AGENT 5: ANOMALY DETECTION DOMAIN TYPES
// ============================================================================

export interface AnomalyObservationItem {
  id: string;
  unified_product_id: string;
  platform: string;
  metric_type: string;
  metric_value: number;
  previous_value?: number;
  change_value?: number;
  change_percent?: number;
  observed_at: string;
  source?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface AnomalyDetectionItem {
  id: string;
  unified_product_id: string;
  anomaly_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  score: number;
  confidence: number;
  baseline?: number;
  observed_value?: number;
  deviation?: number;
  deviation_percent?: number;
  baseline_method: string;
  evidence: Record<string, any>;
  platforms: string[];
  provider?: string;
  fingerprint?: string;
  status: 'active' | 'resolved' | 'suppressed' | 'false_positive';
  detected_at: string;
  resolved_at?: string;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface AnomalyCandidateItem {
  id: string;
  unified_product_id: string;
  anomaly_id?: string;
  candidate_type: string;
  composite_score: number;
  confidence: number;
  status: 'pending_review' | 'confirmed' | 'dismissed' | 'false_positive' | 'auto_promoted';
  reasons: string[];
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface AnomalyScoreBreakdownItem {
  deviation_magnitude_score: number;
  historical_consistency_score: number;
  data_freshness_score: number;
  baseline_quality_score: number;
  cross_platform_score: number;
  total_anomaly_score: number;
  status: string;
}

export interface ProductAnomalySummaryItem {
  unified_product_id: string;
  canonical_name: string;
  brand?: string;
  category: string;
  platforms: string[];
  anomaly_score: number;
  status: 'anomaly_detected' | 'normal' | 'insufficient_data';
  confidence: number;
  freshness_status: 'fresh' | 'recent' | 'stale' | 'insufficient_data';
  active_anomalies: AnomalyDetectionItem[];
  score_breakdown: AnomalyScoreBreakdownItem;
  recent_observations: AnomalyObservationItem[];
  last_analyzed_at: string;
}

export interface AgentAnomalyDetectionStatsItem {
  total_analyzed_products: number;
  total_anomalies_detected: number;
  active_anomalies_count: number;
  critical_anomalies_count: number;
  high_severity_count: number;
  candidates_pending_review: number;
  false_positives_count: number;
  anomalies_by_type: Record<string, number>;
  anomalies_by_severity: Record<string, number>;
  anomalies_by_platform: Record<string, number>;
  last_updated: string;
}

export interface AnomalyListResponse {
  items: AnomalyDetectionItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AnomalyCandidateListResponse {
  items: AnomalyCandidateItem[];
  total: number;
}

export interface AnomalyObservationListResponse {
  unified_product_id: string;
  items: AnomalyObservationItem[];
  total: number;
}

// ============================================================================
// AGENT 06: RECOMMENDATION & PRODUCT INTELLIGENCE INTERFACES
// ============================================================================

export interface ProductRecommendationItem {
  id: string;
  unified_product_id: string;
  target_product_id?: string;
  recommendation_type: 'similar_product' | 'alternative_product' | 'better_price' | 'trending_product' | 'high_quality' | 'cross_platform' | 'category_recommendation' | 'rising_product' | 'opportunity' | 'best_value';
  score: number;
  confidence: number;
  reasons: string[];
  evidence: Record<string, any>;
  source_agents: string[];
  warnings: string[];
  platforms: string[];
  category?: string;
  brand?: string;
  fingerprint?: string;
  status: 'active' | 'archived' | 'dismissed' | 'expired';
  freshness_status: 'fresh' | 'recent' | 'stale' | 'insufficient_data';
  created_at: string;
  updated_at: string;
  expires_at?: string;
}

export interface RecommendationCandidateItem {
  id: string;
  unified_product_id: string;
  target_product_id?: string;
  candidate_type: string;
  composite_score: number;
  confidence: number;
  status: 'pending' | 'approved' | 'dismissed' | 'rejected';
  reasons: string[];
  evidence: Record<string, any>;
  source_agents: string[];
  metadata: Record<string, any>;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface RecommendationInteractionItem {
  id: string;
  user_id?: string;
  workspace_id?: string;
  recommendation_id?: string;
  product_id: string;
  interaction_type: 'view' | 'click' | 'save' | 'dismiss' | 'compare' | 'external_link_click';
  metadata: Record<string, any>;
  occurred_at: string;
}

export interface RecommendationScoreBreakdownItem {
  data_quality_score: number;
  product_similarity_score: number;
  price_value_score: number;
  rating_quality_score: number;
  trend_strength_score: number;
  availability_score: number;
  cross_platform_score: number;
  freshness_score: number;
  total_recommendation_score: number;
  eligibility_status: string;
}

export interface ProductRecommendationSummaryItem {
  unified_product_id: string;
  canonical_name: string;
  brand?: string;
  category: string;
  platforms: string[];
  recommendation_score: number;
  status: 'ready' | 'quality_gated' | 'anomaly_blocked' | 'insufficient_data';
  confidence: number;
  freshness_status: string;
  recommendations: ProductRecommendationItem[];
  score_breakdown: RecommendationScoreBreakdownItem;
  warnings: string[];
  last_generated_at: string;
}

export interface AgentRecommendationStatsItem {
  total_recommendations: number;
  active_recommendations_count: number;
  best_value_count: number;
  trending_recommendations_count: number;
  cross_platform_count: number;
  candidates_pending_review: number;
  total_interactions_logged: number;
  recommendations_by_type: Record<string, number>;
  recommendations_by_category: Record<string, number>;
  interactions_by_type: Record<string, number>;
  last_updated: string;
}

export interface RecommendationListResponse {
  items: ProductRecommendationItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface RecommendationCandidateListResponse {
  items: RecommendationCandidateItem[];
  total: number;
}

export interface RecommendationMemoryListResponse {
  memories: any[];
  events: any[];
}

// ============================================================================
// AGENT 07: MARKET OPPORTUNITY INTELLIGENCE INTERFACES
// ============================================================================

export interface MarketOpportunityItem {
  id: string;
  unified_product_id?: string;
  category?: string;
  subcategory?: string;
  brand?: string;
  opportunity_type: 'product_gap' | 'price_opportunity' | 'category_opportunity' | 'competitive_gap' | 'cross_platform_gap' | 'availability_opportunity' | 'quality_gap' | 'rising_category' | 'rising_product' | 'marketplace_expansion' | 'underserved_category' | 'product_launch_opportunity';
  score: number;
  confidence: number;
  status: 'active' | 'archived' | 'dismissed' | 'insufficient_data' | 'quality_gated' | 'anomaly_blocked';
  reasons: string[];
  evidence: Record<string, any>;
  source_agent_ids: string[];
  warnings: string[];
  current_platforms: string[];
  missing_observed_platforms: string[];
  fingerprint?: string;
  data_freshness: 'fresh' | 'recent' | 'stale' | 'insufficient_data';
  detected_at: string;
  created_at: string;
  updated_at: string;
  expires_at?: string;
}

export interface MarketOpportunityCandidateItem {
  id: string;
  unified_product_id?: string;
  category?: string;
  candidate_type: string;
  composite_score: number;
  confidence: number;
  status: 'pending' | 'approved' | 'dismissed' | 'rejected';
  reasons: string[];
  evidence: Record<string, any>;
  source_agent_ids: string[];
  metadata: Record<string, any>;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface MarketOpportunityScoreBreakdownItem {
  evidence_strength_score: number;
  trend_strength_score: number;
  market_coverage_gap_score: number;
  price_opportunity_score: number;
  product_quality_score: number;
  cross_platform_evidence_score: number;
  freshness_score: number;
  total_opportunity_score: number;
  eligibility_status: string;
}

export interface MarketOpportunitySummaryItem {
  target_id: string;
  target_type: 'product' | 'category' | 'market';
  name: string;
  category?: string;
  status: 'ready' | 'quality_gated' | 'anomaly_blocked' | 'insufficient_data';
  opportunity_score: number;
  confidence: number;
  data_freshness: string;
  opportunities: MarketOpportunityItem[];
  score_breakdown: MarketOpportunityScoreBreakdownItem;
  warnings: string[];
  analyzed_at: string;
}

export interface AgentMarketOpportunityStatsItem {
  total_opportunities: number;
  active_opportunities_count: number;
  high_confidence_count: number;
  high_score_count: number;
  pending_review_count: number;
  confirmed_count: number;
  dismissed_count: number;
  opportunities_by_type: Record<string, number>;
  opportunities_by_category: Record<string, number>;
  opportunities_by_platform: Record<string, number>;
  last_updated: string;
}

export interface OpportunityListResponse {
  items: MarketOpportunityItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface OpportunityCandidateListResponse {
  items: MarketOpportunityCandidateItem[];
  total: number;
}

export interface OpportunityMemoryListResponse {
  memories: any[];
  events: any[];
}

export interface StartScraperJobPayload {
  marketplace: string;
  provider?: string;
  keywords?: string[];
  keyword?: string;
  urls?: string[];
  url?: string;
  category?: string;
  max_products?: number;
  max_workers?: number;
  export_format?: string;
  dry_run?: boolean;
}

export interface ScraperJobProgress {
  job_id: string;
  marketplace: string;
  provider?: string;
  trigger_type: string;
  status: 'queued' | 'running' | 'paused' | 'completed' | 'completed_with_challenges' | 'failed' | 'cancelled' | 'stopped';
  target_count: number;
  products_fetched: number;
  products_persisted: number;
  products_rejected: number;
  challenged_count: number;
  failed_count: number;
  current_throughput: number;
  duration_seconds: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface ScraperJobListResponse {
  total: number;
  jobs: ScraperJobProgress[];
}

export interface ScraperMarketplaceHealth {
  marketplace: string;
  status: 'healthy' | 'degraded' | 'challenged' | 'offline';
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  challenge_count: number;
  average_latency_ms: number;
  last_scraped_at?: string | null;
  last_challenge_at?: string | null;
}

export interface ScraperProductItem {
  id: string;
  marketplace: string;
  provider?: string;
  product_id: string;
  title: string;
  brand?: string | null;
  price: number;
  original_price?: number | null;
  discount?: number | null;
  discount_label?: string | null;
  currency: string;
  rating?: number | null;
  review_count: number;
  sold_count?: number | null;
  seller_name?: string | null;
  seller_id?: string | null;
  seller_rating?: number | null;
  seller_metrics?: Record<string, any>;
  category?: string | null;
  availability: boolean;
  image_url?: string | null;
  images: string[];
  product_url: string;
  source_url?: string | null;
  extraction_status: string;
  quality_status: string;
  confidence_score: number;
  challenge_status?: string | null;
  description_text?: string | null;
  specifications: Record<string, any>;
  variants: Array<Record<string, any>>;
  reviews?: Array<Record<string, any>>;
  first_seen_at: string;
  last_seen_at: string;
  raw_payload_available: boolean;
}

export interface ScraperProductListResponse {
  total: number;
  products: ScraperProductItem[];
}

export interface RawScrapedDataResponse {
  id: string;
  marketplace: string;
  product_id: string;
  crawl_job_id?: string | null;
  source_url: string;
  canonical_url?: string | null;
  parser_version: string;
  extraction_status: string;
  quality_status: string;
  confidence_score: number;
  scraped_at: string;
  raw_payload: Record<string, any>;
  normalized_payload: Record<string, any>;
}

export interface ScraperProductHistoryResponse {
  product_id: string;
  marketplace: string;
  total_snapshots: number;
  snapshots: Array<{
    id: string;
    product_id: string;
    platform: string;
    price: number;
    original_price?: number | null;
    discount?: number | null;
    rating?: number | null;
    review_count: number;
    stock_status: string;
    observed_at: string;
  }>;
}

// ============================================================================
// Canonical Marketplace Search Architecture (Phase 1)
// ============================================================================

export type MarketplaceType = 'daraz' | 'amazon' | 'ebay' | 'shopify';

export type MarketplaceSearchStatus =
  | 'queued'
  | 'running'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'insufficient_data';

export interface MarketplaceSearchRequest {
  marketplace: MarketplaceType;
  keyword: string;
  desired_results?: number;
  candidate_target?: number;
  user_id?: string | null;
  session_id?: string | null;
}

export interface MarketplaceSearchCandidate {
  external_product_id?: string | null;
  marketplace: MarketplaceType;
  title: string;
  url: string;
  image_url?: string | null;
  price?: number | null;
  currency?: string | null;
  original_price?: number | null;
  seller?: string | null;
  brand?: string | null;
  category?: string | null;
  rating?: number | null;
  review_count?: number | null;
  availability?: boolean | null;
  description?: string | null;
  source_provider: string;
  source_url?: string | null;
  observed_at: string;
  raw_payload_reference?: Record<string, any> | null;
}

export interface MarketplaceSearchResult {
  search_id: string;
  marketplace: MarketplaceType;
  keyword: string;
  status: MarketplaceSearchStatus;
  candidate_count: number;
  normalized_count: number;
  quality_passed_count: number;
  deduplicated_count: number;
  returned_count: number;
  products: MarketplaceSearchCandidate[];
  created_at: string;
  completed_at?: string | null;
  error?: string | null;
  message?: string | null;
}

// ==========================================
// PHASE 3: MARKET INTELLIGENCE INTERFACES
// ==========================================

export interface MarketScoreComponents {
  demand: number;
  growth: number;
  acclaim: number;
  price_health: number;
  cross_platform: number;
}

export interface MarketScoreResponse {
  score: number;
  components: MarketScoreComponents;
  weights: Record<string, number>;
  confidence: number;
  data_quality_score: number;
  history_status?: string;
  calculation_timestamp: string;
}

export interface DemandIntelligenceResponse {
  demand_score: number;
  demand_level: string;
  demand_trend: string;
  confidence: number;
  contributors: string[];
}

export interface TrendVelocityResponse {
  velocity?: number | null;
  window_days: number;
  status: string;
  observation_count: number;
}

export interface GrowthIntelligenceResponse {
  growth_7d?: number | null;
  growth_30d?: number | null;
  window_days: number;
  status: string;
  observation_count: number;
}

export interface ViralPotentialResponse {
  viral_score?: number | null;
  viral_level: string;
  confidence: number;
  has_social_signals: boolean;
  supporting_signals: string[];
}

export interface ProductOpportunityResponse {
  opportunity_score: number;
  opportunity_level: string;
  confidence: number;
  competition_level: string;
  reasoning: string;
  supporting_signals: string[];
}

export interface CrossMarketplaceComparisonItem {
  platforms_present: string[];
  lowest_price: number;
  highest_price: number;
  average_price: number;
  price_spread_pct: number;
  currency: string;
  rating_avg: number;
  total_reviews: number;
  listings_count: number;
}

export interface SocialSignalItem {
  id: string;
  platform: string;
  content_title: string;
  content_url: string;
  author_name?: string | null;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  engagement_rate: number;
  matched_product_id?: string | null;
  match_confidence: number;
  observed_at: string;
}

export interface ProductMarketIntelligenceDetail {
  product_id: string;
  title: string;
  marketplace: string;
  category?: string | null;
  current_price: number;
  original_price?: number | null;
  currency: string;
  rating: number;
  review_count: number;
  availability: boolean;
  url: string;
  image_url?: string | null;
  market_score: MarketScoreResponse;
  demand: DemandIntelligenceResponse;
  trend_velocity: TrendVelocityResponse;
  growth: GrowthIntelligenceResponse;
  viral_potential: ViralPotentialResponse;
  opportunity: ProductOpportunityResponse;
  cross_marketplace?: CrossMarketplaceComparisonItem | null;
  social_signals: SocialSignalItem[];
  ai_summary?: string | null;
  data_quality_score: number;
  confidence: number;
  source_provenance: string;
  calculated_at: string;
}

export interface MarketOverviewResponse {
  average_market_score: number;
  total_products_analyzed: number;
  high_demand_count: number;
  high_opportunity_count: number;
  social_active_count: number;
  marketplaces_covered: string[];
  top_products: ProductMarketIntelligenceDetail[];
  trending_products: ProductMarketIntelligenceDetail[];
  rising_products?: ProductMarketIntelligenceDetail[];
  declining_products?: ProductMarketIntelligenceDetail[];
  high_demand_products: ProductMarketIntelligenceDetail[];
  high_opportunity_products: ProductMarketIntelligenceDetail[];
  socially_trending_products: ProductMarketIntelligenceDetail[];
  ai_executive_summary?: string | null;
  data_quality_average: number;
  overall_confidence: number;
  generated_at: string;
}

export interface CategoryIntelligenceItem {
  category_name: string;
  product_count: number;
  average_price: number;
  average_rating: number;
  average_market_score: number;
  demand_level: string;
  opportunity_level: string;
  social_interest_score: number;
  data_confidence: number;
}

export interface CategoryIntelligenceResponse {
  categories: CategoryIntelligenceItem[];
  total_categories: number;
}

export interface MarketplaceComparisonResponse {
  marketplace: string;
  product_count: number;
  average_price: number;
  average_rating: number;
  in_stock_rate_pct: number;
  average_discount_pct: number;
  average_market_score: number;
  currency: string;
}

export interface MarketplacesIntelligenceResponse {
  marketplaces: MarketplaceComparisonResponse[];
  primary_marketplace: string;
  generated_at: string;
}

export interface SocialIntelligenceResponse {
  signals: SocialSignalItem[];
  total_signals: number;
  total_views: number;
  total_engagement: number;
  platforms: string[];
}

export interface MarketIntelligenceReportResponse {
  report_id: string;
  title: string;
  marketplace: string;
  category?: string | null;
  keyword?: string | null;
  overview: MarketOverviewResponse;
  ai_market_narrative?: string | null;
  ai_trend_drivers: string[];
  ai_market_opportunities: string[];
  ai_risk_factors: string[];
  ai_strategic_recommendations: string[];
  data_quality_score: number;
  confidence: number;
  sources_audited: string[];
  created_at: string;
}

export interface AnalyzeIntelligenceRequest {
  marketplace?: string;
  keyword?: string;
  category?: string;
  product_ids?: string[];
  include_ai_narrative?: boolean;
  force_refresh?: boolean;
}














