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
}

export interface DashboardSummary {
  metrics: MetricCard[];
  live_signals: LiveSignalItem[];
  top_surging: Array<{
    id: string;
    name: string;
    category: string;
    trend_score: number;
    growth_rate: number;
    volume: number;
    platform: string;
    velocity_label: string;
    price_range: string;
  }>;
  total_trends_monitored: number;
  system_status: string;
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
  status: "Connected" | "Disconnected" | "Syncing" | "Error";
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
