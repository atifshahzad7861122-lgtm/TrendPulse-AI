import { api } from "./api";
import type {
  User, Workspace, Product, Category, PlatformMetrics,
  DashboardSummary, TrendPoint, Alert, NotificationItem, Report,
  DataSource, SearchResponse, UserSettings, IngestionResult, DataSourceConfigStatus,
  IntelligenceSummary, DarazCategory, DarazProductDetails, DarazSearchResponse,
  LiveSignalsResponse, ShopifyProduct, ShopifyProductListResponse, ShopifySyncRequest,
  ShopifySyncResponse, ShopifyStatusResponse,
  UnifiedProductListResponse, UnifiedProductDetailResponse,
  UnifiedProductHistoryResponse, UnifiedSearchResponse,
  AIProductAnalysisResponse, AIProductSummaryResponse,
  AIMarketComparisonResponse, AITrendAnalysisResponse,
  AICategoryAnalysisResponse, LLMUsageSummaryResponse,
  DataQualityValidationResponse, DataQualityBatchValidationResponse,
  DataQualityStatusResponse, DataQualityMemoryListResponse,
  DataQualityRunHistoryResponse, DataQualityValidationListResponse,
  AIAgentMemoryEvent,
  PublicDataQualityFeedResponse, PublicDataQualityStatsResponse, PublicDataQualityHistoryResponse,
  TaxonomyTreeResponse, TaxonomyCategoriesListResponse,
  TaxonomySearchResponse, ProductTaxonomyAssignmentResponse,
  ProductTaxonomyHistoryResponse, AgentCategorizationMemoryListResponse,
  ProductTaxonomyCandidateItem,
  ProductMatchDecisionItem, ProductMatchHistoryResponse, ProductMatchCandidateItem,
  EntityMatchingStatsItem, EntityMatchingMemoryListResponse,
  ProductTrendSummaryItem, TrendSignalCandidateItem,
  AgentTrendDetectionStatsItem, TrendSignalsListResponse, TrendCandidatesListResponse,
  TrendObservationItem,
  ProductAnomalySummaryItem, AnomalyCandidateItem,
  AgentAnomalyDetectionStatsItem, AnomalyListResponse, AnomalyCandidateListResponse, AnomalyObservationListResponse,
  ProductRecommendationItem, RecommendationCandidateItem, RecommendationInteractionItem,
  ProductRecommendationSummaryItem, AgentRecommendationStatsItem,
  RecommendationListResponse, RecommendationCandidateListResponse,
  MarketOpportunityItem, MarketOpportunityCandidateItem,
  MarketOpportunitySummaryItem, AgentMarketOpportunityStatsItem,
  OpportunityListResponse, OpportunityCandidateListResponse, OpportunityMemoryListResponse,
  StartScraperJobPayload, ScraperJobProgress, ScraperJobListResponse,
  ScraperMarketplaceHealth, ScraperProductItem, ScraperProductListResponse,
  RawScrapedDataResponse, ScraperProductHistoryResponse,
  MarketplaceSearchRequest, MarketplaceSearchResult,
  MarketOverviewResponse, ProductMarketIntelligenceDetail, CategoryIntelligenceResponse,
  MarketplacesIntelligenceResponse, SocialIntelligenceResponse, MarketIntelligenceReportResponse,
  AnalyzeIntelligenceRequest
} from "../types";






export const authService = {
  register: (data: { full_name: string; email: string; password: string; confirm_password: string; terms_accepted: boolean }) =>
    api.post<{ user_id: string; email: string; is_verified?: boolean; access_token?: string; workspace_id?: string; email_verification_enabled?: boolean }>("/auth/register", data),

  login: (data: { email: string; password: string; remember_me?: boolean }) =>
    api.post<{ access_token: string; user_id: string; email: string; full_name: string; is_verified: boolean; workspace_id?: string; role: string; avatar_url?: string }>("/auth/login", data),

  getDemoSession: () =>
    api.post<{ access_token: string; user_id: string; email: string; full_name: string; is_verified: boolean; workspace_id?: string; role: string; avatar_url?: string }>("/auth/demo-session"),

  logout: () => api.post("/auth/logout"),

  verifyEmail: (token: string, email?: string) =>
    api.post<{ access_token: string; user_id: string; is_verified: boolean; workspace_id?: string }>("/auth/verify-email", { token, email: email || undefined }),

  resendVerification: (email: string) =>
    api.post<{ email: string; message: string; delivery_status?: string }>("/auth/resend-verification", { email }),

  forgotPassword: (email: string) =>
    api.post<{ email: string; reset_token: string; dev_reset_url: string }>("/auth/forgot-password", { email }),

  resetPassword: (data: { token: string; new_password: string; confirm_password: string }) =>
    api.post<{ email: string }>("/auth/reset-password", data),

  getMe: () => api.get<User>("/auth/me"),
  updateProfile: (data: { full_name?: string; avatar_url?: string; role?: string; email?: string }) =>
    api.patch<User>("/auth/me", data),
};

export const workspaceService = {
  getWorkspace: () => api.get<Workspace>("/workspace"),
  setupWorkspace: (data: { name: string; industry: string; use_case: string; currency: string; default_dashboard: string; data_sources: string[] }) =>
    api.post<Workspace>("/workspace/setup", data),
};

export const dashboardService = {
  getSummary: (params: { time_range?: string; category?: string; platform?: string } = {}) => {
    const query = new URLSearchParams(params as any).toString();
    return api.get<DashboardSummary>(`/dashboard/summary?${query}`);
  },
  getTrends: (params: { time_range?: string; category?: string; platform?: string } = {}) => {
    const query = new URLSearchParams(params as any).toString();
    return api.get<TrendPoint[]>(`/dashboard/trends?${query}`);
  },
};

export const productService = {
  list: (params: { category?: string; platform?: string; search?: string; sort_by?: string; page?: number; limit?: number } = {}) => {
    const cleanParams: Record<string, string> = {};
    if (params.category && params.category !== "all") cleanParams.category = params.category;
    if (params.platform && params.platform !== "all") cleanParams.platform = params.platform;
    if (params.search && params.search.trim()) cleanParams.search = params.search.trim();
    if (params.sort_by) cleanParams.sort_by = params.sort_by;
    if (params.page) cleanParams.page = String(params.page);
    if (params.limit) cleanParams.limit = String(params.limit);
    const query = new URLSearchParams(cleanParams).toString();
    return api.get<Product[]>(query ? `/products?${query}` : "/products");
  },
  getById: (id: string) => api.get<Product>(`/products/${id}`),
  compare: (ids: string[]) => api.get<Product[]>(`/products/compare?ids=${ids.join(",")}`),
};

export const categoryService = {
  list: () => api.get<Category[]>("/categories"),
  getById: (id: string) => api.get<Category>(`/categories/${id}`),
};

export const platformService = {
  list: () => api.get<PlatformMetrics[]>("/platforms"),
  getBySlug: (slug: string) => api.get<PlatformMetrics>(`/platforms/${slug}`),
};

export const watchlistService = {
  list: () => api.get<Product[]>("/watchlist"),
  add: (productId: string) => api.post<{ product_id: string; is_watchlisted: boolean }>(`/watchlist/${productId}`),
  remove: (productId: string) => api.delete<{ product_id: string; is_watchlisted: boolean }>(`/watchlist/${productId}`),
};

export const alertService = {
  list: (params: { severity?: string; unread_only?: boolean } = {}) => {
    const query = new URLSearchParams(params as any).toString();
    return api.get<Alert[]>(`/alerts?${query}`);
  },
  markRead: (id: string) => api.post<Alert>(`/alerts/${id}/read`),
  resolve: (id: string) => api.post<Alert>(`/alerts/${id}/resolve`),
};

export const notificationService = {
  list: (unreadOnly: boolean = false) => api.get<NotificationItem[]>(`/notifications?unread_only=${unreadOnly}`),
  markRead: (id: string) => api.post<NotificationItem>(`/notifications/${id}/read`),
  markAllRead: () => api.post<{ count: number }>("/notifications/read-all"),
};

export const reportService = {
  list: () => api.get<Report[]>("/reports"),
  getById: (id: string) => api.get<Report>(`/reports/${id}`),
  generate: (data: { title: string; template: string; time_range: string; category?: string; platforms?: string[]; sections?: string[] }) =>
    api.post<Report>("/reports/generate", data),
  export: (id: string, format: string = "json") => api.get<any>(`/reports/${id}/export?format=${format}`),
};

export const dataSourceService = {
  list: () => api.get<DataSource[]>("/data-sources"),
  getConfigStatus: () => api.get<DataSourceConfigStatus>("/data-sources/config/status"),
  connect: (slug: string) => api.post<DataSource>(`/data-sources/${slug}/connect`),
  disconnect: (slug: string) => api.post<DataSource>(`/data-sources/${slug}/disconnect`),
  sync: (slug: string) => api.post<IngestionResult>(`/data-sources/${slug}/sync`),
  syncAll: () => api.post<{ total_records: number; ingested_at: string }>("/data-sources/sync-all"),
};

export const devService = {
  resetData: () => api.post<{ environment: string; reset: boolean }>("/dev/reset-data"),
  getIntelligenceSummary: () => api.get<IntelligenceSummary>("/dev/intelligence/summary"),
};

export const searchService = {
  search: (query: string) => api.get<SearchResponse>(`/search?q=${encodeURIComponent(query)}`),
};

export const marketplaceSearchService = {
  search: (payload: MarketplaceSearchRequest, execute: boolean = true) =>
    api.post<MarketplaceSearchResult>(`/marketplace-search?execute=${execute}`, payload),
};


export const settingsService = {
  getSettings: () => api.get<UserSettings>("/settings"),
  updateSettings: (settings: UserSettings) => api.put<UserSettings>("/settings", settings),
};

export const darazService = {
  search: (params: {
    query?: string;
    q?: string;
    page?: number;
    category?: string;
    min_rating?: number;
    min_price?: number;
    max_price?: number;
    sort_by?: string;
  }) => {
    const query = new URLSearchParams(params as any).toString();
    return api.get<DarazSearchResponse>(`/platforms/daraz/products/search${query ? `?${query}` : ""}`);
  },

  getDetails: (itemId: string, url?: string) => {
    const query = url ? `?url=${encodeURIComponent(url)}` : "";
    return api.get<DarazProductDetails>(`/platforms/daraz/products/${itemId}${query}`);
  },

  getCategories: () => api.get<DarazCategory[]>("/platforms/daraz/categories"),

  getSellerProducts: (sellerId: string, page: number = 1) =>
    api.get<DarazSearchResponse>(`/platforms/daraz/sellers/${sellerId}/products?page=${page}`),
};

export const signalService = {
  getLiveSignals: (limit: number = 20) =>
    api.get<LiveSignalsResponse>(`/signals/live?limit=${limit}`),
};

export const shopifyService = {
  listProducts: (params?: {
    store_domain?: string;
    category?: string;
    search?: string;
    sort_by?: string;
    page?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams((params || {}) as any).toString();
    return api.get<ShopifyProductListResponse>(`/platforms/shopify/products${query ? `?${query}` : ""}`);
  },

  getProduct: (productId: string) =>
    api.get<ShopifyProduct>(`/platforms/shopify/products/${productId}`),

  sync: (payload: ShopifySyncRequest) =>
    api.post<ShopifySyncResponse>("/platforms/shopify/sync", payload),

  getStatus: () =>
    api.get<ShopifyStatusResponse>("/platforms/shopify/status"),
};

export const intelligenceService = {
  listUnifiedProducts: (params?: {
    category?: string;
    brand?: string;
    platform?: string;
    search?: string;
    min_price?: number;
    max_price?: number;
    available?: boolean;
    min_rating?: number;
    sort_by?: string;
    page?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams((params || {}) as any).toString();
    return api.get<UnifiedProductListResponse>(`/products/intelligence${query ? `?${query}` : ""}`);
  },

  getUnifiedProductDetail: (unifiedProductId: string) =>
    api.get<UnifiedProductDetailResponse>(`/products/intelligence/${unifiedProductId}`),

  getUnifiedProductHistory: (unifiedProductId: string) =>
    api.get<UnifiedProductHistoryResponse>(`/products/intelligence/${unifiedProductId}/history`),

  searchUnifiedProducts: (query: string, page: number = 1, limit: number = 50) =>
    api.get<UnifiedSearchResponse>(`/products/intelligence/search?q=${encodeURIComponent(query)}&page=${page}&limit=${limit}`),
};

export const llmService = {
  analyzeProduct: (unifiedProductId: string, forceRefresh: boolean = false) =>
    api.post<AIProductAnalysisResponse>("/llm/product-analysis", {
      unified_product_id: unifiedProductId,
      force_refresh: forceRefresh
    }),

  summarizeProduct: (unifiedProductId: string, forceRefresh: boolean = false) =>
    api.post<AIProductSummaryResponse>("/llm/product-summary", {
      unified_product_id: unifiedProductId,
      force_refresh: forceRefresh
    }),

  compareMarket: (unifiedProductId: string, forceRefresh: boolean = false) =>
    api.post<AIMarketComparisonResponse>("/llm/market-comparison", {
      unified_product_id: unifiedProductId,
      force_refresh: forceRefresh
    }),

  analyzeTrend: (unifiedProductId: string, forceRefresh: boolean = false) =>
    api.post<AITrendAnalysisResponse>("/llm/trend-analysis", {
      unified_product_id: unifiedProductId,
      force_refresh: forceRefresh
    }),

  analyzeCategory: (category: string, forceRefresh: boolean = false) =>
    api.post<AICategoryAnalysisResponse>("/llm/category-analysis", {
      category,
      force_refresh: forceRefresh
    }),

  getUsageSummary: () =>
    api.get<LLMUsageSummaryResponse>("/llm/usage/summary"),
};

export const dataQualityService = {
  validateSingle: (productPayload: Record<string, any>, platform?: string, sourceProvider?: string, allowLLM: boolean = true) =>
    api.post<DataQualityValidationResponse>("/agents/data-quality/validate", {
      product_payload: productPayload,
      platform,
      source_provider: sourceProvider,
      allow_llm: allowLLM
    }),

  validateBatch: (products: Record<string, any>[], platform?: string, sourceProvider?: string, allowLLM: boolean = true) =>
    api.post<DataQualityBatchValidationResponse>("/agents/data-quality/validate-batch", {
      products,
      platform,
      source_provider: sourceProvider,
      allow_llm: allowLLM
    }),

  getStatus: (workspaceId?: string) =>
    api.get<DataQualityStatusResponse>(`/agents/data-quality/status${workspaceId ? `?workspace_id=${workspaceId}` : ""}`),

  getResults: (params?: { platform?: string; classification?: string; source_provider?: string; min_score?: number; max_score?: number; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.platform) query.set("platform", params.platform);
    if (params?.classification) query.set("classification", params.classification);
    if (params?.source_provider) query.set("source_provider", params.source_provider);
    if (params?.min_score !== undefined) query.set("min_score", params.min_score.toString());
    if (params?.max_score !== undefined) query.set("max_score", params.max_score.toString());
    if (params?.page) query.set("page", params.page.toString());
    if (params?.page_size) query.set("page_size", params.page_size.toString());
    const qStr = query.toString();
    return api.get<DataQualityValidationListResponse>(`/agents/data-quality/results${qStr ? `?${qStr}` : ""}`);
  },

  getResultDetail: (resultId: string) =>
    api.get<DataQualityValidationResponse>(`/agents/data-quality/results/${resultId}`),

  getRunHistory: (limit: number = 50, offset: number = 0) =>
    api.get<DataQualityRunHistoryResponse>(`/agents/data-quality/history?limit=${limit}&offset=${offset}`),

  getMemoryItems: (memoryType?: string) =>
    api.get<DataQualityMemoryListResponse>(`/agents/data-quality/memory${memoryType ? `?memory_type=${memoryType}` : ""}`),

  getMemoryEvents: (memoryId?: string, limit: number = 50) =>
    api.get<AIAgentMemoryEvent[]>(`/agents/data-quality/memory/events?limit=${limit}${memoryId ? `&memory_id=${memoryId}` : ""}`)
};

export const publicDataQualityService = {
  getRejectedProducts: (params?: {
    platform?: string;
    provider?: string;
    category?: string;
    rejection_reason?: string;
    search?: string;
    min_score?: number;
    max_score?: number;
    date_from?: string;
    date_to?: string;
    sort_by?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.platform && params.platform !== "all") query.set("platform", params.platform);
    if (params?.provider && params.provider !== "all") query.set("provider", params.provider);
    if (params?.category && params.category !== "all") query.set("category", params.category);
    if (params?.rejection_reason && params.rejection_reason !== "all") query.set("rejection_reason", params.rejection_reason);
    if (params?.search) query.set("search", params.search);
    if (params?.min_score !== undefined) query.set("min_score", params.min_score.toString());
    if (params?.max_score !== undefined) query.set("max_score", params.max_score.toString());
    if (params?.date_from) query.set("date_from", params.date_from);
    if (params?.date_to) query.set("date_to", params.date_to);
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.page) query.set("page", params.page.toString());
    if (params?.page_size) query.set("page_size", params.page_size.toString());
    const qStr = query.toString();
    return api.get<PublicDataQualityFeedResponse>(`/public/data-quality/rejected${qStr ? `?${qStr}` : ""}`);
  },

  getValidationFeed: (params?: {
    platform?: string;
    provider?: string;
    classification?: string;
    category?: string;
    rejection_reason?: string;
    search?: string;
    min_score?: number;
    max_score?: number;
    date_from?: string;
    date_to?: string;
    sort_by?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.platform && params.platform !== "all") query.set("platform", params.platform);
    if (params?.provider && params.provider !== "all") query.set("provider", params.provider);
    if (params?.classification && params.classification !== "all") query.set("classification", params.classification);
    if (params?.category && params.category !== "all") query.set("category", params.category);
    if (params?.rejection_reason && params.rejection_reason !== "all") query.set("rejection_reason", params.rejection_reason);
    if (params?.search) query.set("search", params.search);
    if (params?.min_score !== undefined) query.set("min_score", params.min_score.toString());
    if (params?.max_score !== undefined) query.set("max_score", params.max_score.toString());
    if (params?.date_from) query.set("date_from", params.date_from);
    if (params?.date_to) query.set("date_to", params.date_to);
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.page) query.set("page", params.page.toString());
    if (params?.page_size) query.set("page_size", params.page_size.toString());
    const qStr = query.toString();
    return api.get<PublicDataQualityFeedResponse>(`/public/data-quality/feed${qStr ? `?${qStr}` : ""}`);
  },

  getPublicStats: () =>
    api.get<PublicDataQualityStatsResponse>("/public/data-quality/stats"),

  getProductHistory: (platform: string, productId: string, limit: number = 50, page: number = 1) =>
    api.get<PublicDataQualityHistoryResponse>(`/public/data-quality/history/${encodeURIComponent(platform)}/${encodeURIComponent(productId)}?limit=${limit}&page=${page}`)
};

export const taxonomyService = {
  getCategories: (params?: { parent_id?: string; level?: number }) => {
    const query = new URLSearchParams();
    if (params?.parent_id) query.set("parent_id", params.parent_id);
    if (params?.level !== undefined) query.set("level", params.level.toString());
    const qStr = query.toString();
    return api.get<TaxonomyCategoriesListResponse>(`/taxonomy/categories${qStr ? `?${qStr}` : ""}`);
  },

  getTree: () =>
    api.get<TaxonomyTreeResponse>("/taxonomy/tree"),

  search: (q: string, limit: number = 20) =>
    api.get<TaxonomySearchResponse>(`/taxonomy/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  getCounts: () =>
    api.get<Record<string, number>>("/taxonomy/counts"),
};

export const categorizationAgentService = {
  classify: (unifiedProductId: string, data?: { allow_llm?: boolean; force_reclassify?: boolean }) =>
    api.post<ProductTaxonomyAssignmentResponse>(`/agents/categorization/classify/${unifiedProductId}`, data || {}),

  getAssignment: (unifiedProductId: string) =>
    api.get<ProductTaxonomyAssignmentResponse>(`/agents/categorization/${unifiedProductId}`),

  getHistory: (unifiedProductId: string, limit: number = 50) =>
    api.get<ProductTaxonomyHistoryResponse>(`/agents/categorization/${unifiedProductId}/history?limit=${limit}`),

  getMemory: (memoryType?: string) => {
    const qStr = memoryType ? `?memory_type=${encodeURIComponent(memoryType)}` : "";
    return api.get<AgentCategorizationMemoryListResponse>(`/agents/categorization/memory${qStr}`);
  },

  getCandidates: (limit: number = 50, offset: number = 0) =>
    api.get<ProductTaxonomyCandidateItem[]>(`/agents/categorization/candidates?limit=${limit}&offset=${offset}`),
};

export const entityMatchingService = {
  matchProduct: (payload: Record<string, any>) =>
    api.post<ProductMatchDecisionItem>("/agents/entity-matching/match", payload),

  compareProducts: (productA: Record<string, any>, productB: Record<string, any>, allowLlm: boolean = true) =>
    api.post<ProductMatchDecisionItem>("/agents/entity-matching/compare", { product_a: productA, product_b: productB, allow_llm: allowLlm }),

  listCandidates: (status?: string, limit: number = 50, offset: number = 0) => {
    const query = new URLSearchParams();
    if (status && status !== "all") query.set("status", status);
    query.set("limit", limit.toString());
    query.set("offset", offset.toString());
    return api.get<ProductMatchCandidateItem[]>(`/agents/entity-matching/candidates?${query.toString()}`);
  },

  resolveCandidate: (candidateId: string, data: { action: "confirm_match" | "confirm_variant" | "reject_match"; notes?: string; variant_attributes?: Record<string, any> }) =>
    api.post<ProductMatchCandidateItem>(`/agents/entity-matching/candidates/${encodeURIComponent(candidateId)}/resolve`, data),

  getMemory: (memoryType?: string) => {
    const qStr = memoryType ? `?memory_type=${encodeURIComponent(memoryType)}` : "";
    return api.get<EntityMatchingMemoryListResponse>(`/agents/entity-matching/memory${qStr}`);
  },

  getStats: () =>
    api.get<EntityMatchingStatsItem>("/agents/entity-matching/stats"),

  getProductMatches: (productId: string) =>
    api.get<ProductMatchDecisionItem[]>(`/agents/entity-matching/${encodeURIComponent(productId)}`),

  getProductMatchHistory: (productId: string, limit: number = 50) =>
    api.get<ProductMatchHistoryResponse>(`/agents/entity-matching/${encodeURIComponent(productId)}/history?limit=${limit}`),
};

export const trendDetectionService = {
  analyzeProduct: (unifiedProductId: string, newListing?: Record<string, any>, allowLlm: boolean = true) =>
    api.post<ProductTrendSummaryItem>(`/agents/trend-detection/analyze/${encodeURIComponent(unifiedProductId)}`, {
      new_listing: newListing,
      allow_llm: allowLlm
    }),

  listSignals: (params?: {
    unified_product_id?: string;
    signal_type?: string;
    direction?: string;
    severity?: string;
    status?: string;
    min_strength?: number;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.unified_product_id) query.set("unified_product_id", params.unified_product_id);
    if (params?.signal_type && params.signal_type !== "all") query.set("signal_type", params.signal_type);
    if (params?.direction && params.direction !== "all") query.set("direction", params.direction);
    if (params?.severity && params.severity !== "all") query.set("severity", params.severity);
    if (params?.status && params.status !== "all") query.set("status", params.status);
    if (params?.min_strength) query.set("min_strength", params.min_strength.toString());
    if (params?.page) query.set("page", params.page.toString());
    if (params?.page_size) query.set("page_size", params.page_size.toString());
    return api.get<TrendSignalsListResponse>(`/agents/trend-detection/signals?${query.toString()}`);
  },

  listCandidates: (status?: string, candidateType?: string, limit: number = 50, offset: number = 0) => {
    const query = new URLSearchParams();
    if (status && status !== "all") query.set("status", status);
    if (candidateType && candidateType !== "all") query.set("candidate_type", candidateType);
    query.set("limit", limit.toString());
    query.set("offset", offset.toString());
    return api.get<TrendCandidatesListResponse>(`/agents/trend-detection/candidates?${query.toString()}`);
  },

  resolveCandidate: (candidateId: string, data: { status: "confirmed" | "rejected" | "auto_promoted"; notes?: string }) =>
    api.post<TrendSignalCandidateItem>(`/agents/trend-detection/candidates/${encodeURIComponent(candidateId)}/resolve`, data),

  getStats: () =>
    api.get<AgentTrendDetectionStatsItem>("/agents/trend-detection/stats"),

  getProductSummary: (unifiedProductId: string) =>
    api.get<ProductTrendSummaryItem>(`/agents/trend-detection/${encodeURIComponent(unifiedProductId)}`),

  getProductObservationsHistory: (unifiedProductId: string, metricType?: string, platform?: string, limit: number = 50) => {
    const query = new URLSearchParams();
    if (metricType) query.set("metric_type", metricType);
    if (platform) query.set("platform", platform);
    query.set("limit", limit.toString());
    return api.get<{ unified_product_id: string; items: TrendObservationItem[]; total: number }>(
      `/agents/trend-detection/${encodeURIComponent(unifiedProductId)}/history?${query.toString()}`
    );
  },
};

export const anomalyDetectionService = {
  analyzeProduct: (unifiedProductId: string, data?: { new_listing?: Record<string, any>; provider_data?: Record<string, any> }) =>
    api.post<ProductAnomalySummaryItem>(`/agents/anomaly-detection/analyze/${encodeURIComponent(unifiedProductId)}`, data || {}),

  listAnomalies: (params?: {
    unified_product_id?: string;
    anomaly_type?: string;
    severity?: string;
    status?: string;
    platform?: string;
    min_score?: number;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.unified_product_id) query.set("unified_product_id", params.unified_product_id);
    if (params?.anomaly_type && params.anomaly_type !== "all") query.set("anomaly_type", params.anomaly_type);
    if (params?.severity && params.severity !== "all") query.set("severity", params.severity);
    if (params?.status && params.status !== "all") query.set("status", params.status);
    if (params?.platform && params.platform !== "all") query.set("platform", params.platform);
    if (params?.min_score !== undefined) query.set("min_score", params.min_score.toString());
    if (params?.page) query.set("page", params.page.toString());
    if (params?.page_size) query.set("page_size", params.page_size.toString());
    return api.get<AnomalyListResponse>(`/agents/anomaly-detection/signals?${query.toString()}`);
  },

  listCandidates: (status?: string, candidateType?: string) => {
    const query = new URLSearchParams();
    if (status && status !== "all") query.set("status", status);
    if (candidateType && candidateType !== "all") query.set("candidate_type", candidateType);
    return api.get<AnomalyCandidateListResponse>(`/agents/anomaly-detection/candidates?${query.toString()}`);
  },

  resolveCandidate: (candidateId: string, data: { status: "confirmed" | "dismissed" | "false_positive" | "resolved"; notes?: string }) =>
    api.post<AnomalyCandidateItem>(`/agents/anomaly-detection/candidates/${encodeURIComponent(candidateId)}/resolve`, data),

  getStats: () =>
    api.get<AgentAnomalyDetectionStatsItem>("/agents/anomaly-detection/stats"),

  getProductSummary: (unifiedProductId: string) =>
    api.get<ProductAnomalySummaryItem>(`/agents/anomaly-detection/${encodeURIComponent(unifiedProductId)}`),

  getProductObservationsHistory: (unifiedProductId: string, metricType?: string, platform?: string, limit: number = 50) => {
    const query = new URLSearchParams();
    if (metricType) query.set("metric_type", metricType);
    if (platform) query.set("platform", platform);
    query.set("limit", limit.toString());
    return api.get<AnomalyObservationListResponse>(
      `/agents/anomaly-detection/${encodeURIComponent(unifiedProductId)}/history?${query.toString()}`
    );
  },
};

export const recommendationService = {
  generateCatalog: (data?: { recommendation_type?: string; category?: string; min_score?: number; limit?: number }) =>
    api.post<ProductRecommendationItem[]>("/agents/recommendations/generate", data || {}),

  generateForProduct: (unifiedProductId: string, data?: { include_similar?: boolean; include_alternatives?: boolean; include_better_price?: boolean; include_cross_platform?: boolean; include_best_value?: boolean; limit_per_type?: number }) =>
    api.post<ProductRecommendationSummaryItem>(`/agents/recommendations/product/${encodeURIComponent(unifiedProductId)}`, data || {}),

  list: (params?: {
    unified_product_id?: string;
    recommendation_type?: string;
    category?: string;
    brand?: string;
    platform?: string;
    status?: string;
    min_score?: number;
    min_confidence?: number;
    search?: string;
    sort_by?: string;
    page?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.unified_product_id) query.set("unified_product_id", params.unified_product_id);
    if (params?.recommendation_type && params.recommendation_type !== "all") query.set("recommendation_type", params.recommendation_type);
    if (params?.category && params.category !== "all") query.set("category", params.category);
    if (params?.brand) query.set("brand", params.brand);
    if (params?.platform && params.platform !== "all") query.set("platform", params.platform);
    if (params?.status && params.status !== "all") query.set("status", params.status);
    if (params?.min_score) query.set("min_score", params.min_score.toString());
    if (params?.min_confidence) query.set("min_confidence", params.min_confidence.toString());
    if (params?.search) query.set("search", params.search);
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.page) query.set("page", params.page.toString());
    if (params?.limit) query.set("limit", params.limit.toString());
    return api.get<RecommendationListResponse>(`/agents/recommendations?${query.toString()}`);
  },

  getById: (id: string) =>
    api.get<ProductRecommendationItem>(`/agents/recommendations/${encodeURIComponent(id)}`),

  getProductRecommendations: (unifiedProductId: string, recommendationType?: string, limit: number = 10) => {
    const query = new URLSearchParams();
    if (recommendationType && recommendationType !== "all") query.set("recommendation_type", recommendationType);
    query.set("limit", limit.toString());
    return api.get<ProductRecommendationItem[]>(`/agents/recommendations/product/${encodeURIComponent(unifiedProductId)}?${query.toString()}`);
  },

  listCandidates: (status: string = "pending", candidateType?: string, limit: number = 50) => {
    const query = new URLSearchParams();
    if (status && status !== "all") query.set("status", status);
    if (candidateType && candidateType !== "all") query.set("candidate_type", candidateType);
    query.set("limit", limit.toString());
    return api.get<RecommendationCandidateListResponse>(`/agents/recommendations/candidates?${query.toString()}`);
  },

  resolveCandidate: (candidateId: string, data: { status: "approved" | "dismissed" | "rejected"; notes?: string }) =>
    api.post<RecommendationCandidateItem>(`/agents/recommendations/candidates/${encodeURIComponent(candidateId)}/resolve`, data),

  logInteraction: (data: { recommendation_id?: string; product_id: string; interaction_type: 'view' | 'click' | 'save' | 'dismiss' | 'compare' | 'external_link_click'; metadata?: Record<string, any> }) =>
    api.post<RecommendationInteractionItem>("/agents/recommendations/interactions", data),

  getStats: () =>
    api.get<AgentRecommendationStatsItem>("/agents/recommendations/stats"),
};

export const marketOpportunityService = {
  analyzeCatalog: (data?: { category?: string; min_score?: number; limit?: number }) =>
    api.post<MarketOpportunityItem[]>("/agents/market-opportunities/analyze", data || {}),

  analyzeProduct: (unifiedProductId: string, isComplexStrategy: boolean = false) =>
    api.post<MarketOpportunitySummaryItem>(
      `/agents/market-opportunities/product/${encodeURIComponent(unifiedProductId)}?is_complex_strategy=${isComplexStrategy}`,
      {}
    ),

  list: (params?: {
    unified_product_id?: string;
    opportunity_type?: string;
    category?: string;
    brand?: string;
    platform?: string;
    status?: string;
    min_score?: number;
    min_confidence?: number;
    search?: string;
    sort_by?: string;
    page?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.unified_product_id) query.set("unified_product_id", params.unified_product_id);
    if (params?.opportunity_type && params.opportunity_type !== "all") query.set("opportunity_type", params.opportunity_type);
    if (params?.category && params.category !== "all") query.set("category", params.category);
    if (params?.brand) query.set("brand", params.brand);
    if (params?.platform && params.platform !== "all") query.set("platform", params.platform);
    if (params?.status && params.status !== "all") query.set("status", params.status);
    if (params?.min_score) query.set("min_score", params.min_score.toString());
    if (params?.min_confidence) query.set("min_confidence", params.min_confidence.toString());
    if (params?.search) query.set("search", params.search);
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.page) query.set("page", params.page.toString());
    if (params?.limit) query.set("limit", params.limit.toString());
    return api.get<OpportunityListResponse>(`/agents/market-opportunities?${query.toString()}`);
  },

  getById: (id: string) =>
    api.get<MarketOpportunityItem>(`/agents/market-opportunities/${encodeURIComponent(id)}`),

  getProductOpportunities: (unifiedProductId: string) =>
    api.get<MarketOpportunityItem[]>(`/agents/market-opportunities/product/${encodeURIComponent(unifiedProductId)}`),

  listCandidates: (status: string = "pending", candidateType?: string, limit: number = 50) => {
    const query = new URLSearchParams();
    if (status && status !== "all") query.set("status", status);
    if (candidateType && candidateType !== "all") query.set("candidate_type", candidateType);
    query.set("limit", limit.toString());
    return api.get<OpportunityCandidateListResponse>(`/agents/market-opportunities/candidates?${query.toString()}`);
  },

  resolveCandidate: (candidateId: string, data: { status: "approved" | "dismissed" | "rejected"; notes?: string }) =>
    api.post<MarketOpportunityCandidateItem>(`/agents/market-opportunities/candidates/${encodeURIComponent(candidateId)}/resolve`, data),

  getStats: () =>
    api.get<AgentMarketOpportunityStatsItem>("/agents/market-opportunities/stats"),

  getMemories: () =>
    api.get<OpportunityMemoryListResponse>("/agents/market-opportunities/memory"),
};

export const scraperService = {
  startJob: (payload: StartScraperJobPayload) =>
    api.post<ScraperJobProgress>("/scraper/jobs/start", payload),

  getJobStatus: (jobId: string) =>
    api.get<ScraperJobProgress>(`/scraper/jobs/${encodeURIComponent(jobId)}/status`),

  pauseJob: (jobId: string) =>
    api.post<{ job_id: string; paused: boolean }>(`/scraper/jobs/${encodeURIComponent(jobId)}/pause`),

  stopJob: (jobId: string) =>
    api.post<{ job_id: string; stopped: boolean }>(`/scraper/jobs/${encodeURIComponent(jobId)}/stop`),

  listJobs: (params?: { marketplace?: string; status?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.marketplace && params.marketplace !== "all") query.set("marketplace", params.marketplace);
    if (params?.status && params.status !== "all") query.set("status", params.status);
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    return api.get<ScraperJobListResponse>(`/scraper/jobs?${query.toString()}`);
  },

  getMarketplaceHealth: () =>
    api.get<ScraperMarketplaceHealth[]>("/scraper/marketplaces/health"),

  listProducts: (params?: {
    marketplace?: string;
    category?: string;
    search?: string;
    min_price?: number;
    max_price?: number;
    sort_by?: string;
    page?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.marketplace && params.marketplace !== "all") query.set("marketplace", params.marketplace);
    if (params?.category) query.set("category", params.category);
    if (params?.search) query.set("search", params.search);
    if (params?.min_price !== undefined) query.set("min_price", params.min_price.toString());
    if (params?.max_price !== undefined) query.set("max_price", params.max_price.toString());
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.page) query.set("page", params.page.toString());
    if (params?.limit) query.set("limit", params.limit.toString());
    return api.get<ScraperProductListResponse>(`/scraper/products?${query.toString()}`);
  },

  getProduct: (productId: string, marketplace?: string) => {
    const query = marketplace ? `?marketplace=${encodeURIComponent(marketplace)}` : "";
    return api.get<ScraperProductItem>(`/scraper/products/${encodeURIComponent(productId)}${query}`);
  },

  getProductRaw: (productId: string, marketplace?: string) => {
    const query = marketplace ? `?marketplace=${encodeURIComponent(marketplace)}` : "";
    return api.get<RawScrapedDataResponse>(`/scraper/products/${encodeURIComponent(productId)}/raw${query}`);
  },

  getProductHistory: (productId: string, marketplace?: string) => {
    const query = marketplace ? `?marketplace=${encodeURIComponent(marketplace)}` : "";
    return api.get<ScraperProductHistoryResponse>(`/scraper/products/${encodeURIComponent(productId)}/history${query}`);
  },
};

export const marketIntelligenceService = {
  getOverview: (params?: { category?: string; marketplace?: string; keyword?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.category && params.category !== "all") query.set("category", params.category);
    if (params?.marketplace && params.marketplace !== "all") query.set("marketplace", params.marketplace);
    if (params?.keyword) query.set("keyword", params.keyword);
    if (params?.limit) query.set("limit", params.limit.toString());
    const qs = query.toString() ? `?${query.toString()}` : "";
    return api.get<MarketOverviewResponse>(`/intelligence/overview${qs}`);
  },

  listProducts: (params?: {
    category?: string;
    marketplace?: string;
    keyword?: string;
    min_market_score?: number;
    min_demand_score?: number;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.category && params.category !== "all") query.set("category", params.category);
    if (params?.marketplace && params.marketplace !== "all") query.set("marketplace", params.marketplace);
    if (params?.keyword) query.set("keyword", params.keyword);
    if (params?.min_market_score !== undefined) query.set("min_market_score", params.min_market_score.toString());
    if (params?.min_demand_score !== undefined) query.set("min_demand_score", params.min_demand_score.toString());
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    const qs = query.toString() ? `?${query.toString()}` : "";
    return api.get<ProductMarketIntelligenceDetail[]>(`/intelligence/products${qs}`);
  },

  getProductDetail: (productId: string, platform?: string) => {
    const query = platform ? `?platform=${encodeURIComponent(platform)}` : "";
    return api.get<ProductMarketIntelligenceDetail>(`/intelligence/products/${encodeURIComponent(productId)}${query}`);
  },

  getCategories: () => api.get<CategoryIntelligenceResponse>("/intelligence/categories"),

  getMarketplaces: () => api.get<MarketplacesIntelligenceResponse>("/intelligence/marketplaces"),

  getSocialSignals: (params?: { platform?: string; product_id?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.platform && params.platform !== "all") query.set("platform", params.platform);
    if (params?.product_id) query.set("product_id", params.product_id);
    if (params?.limit) query.set("limit", params.limit.toString());
    const qs = query.toString() ? `?${query.toString()}` : "";
    return api.get<SocialIntelligenceResponse>(`/intelligence/social${qs}`);
  },

  getReport: (params?: { marketplace?: string; category?: string; keyword?: string }) => {
    const query = new URLSearchParams();
    if (params?.marketplace) query.set("marketplace", params.marketplace);
    if (params?.category) query.set("category", params.category);
    if (params?.keyword) query.set("keyword", params.keyword);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return api.get<MarketIntelligenceReportResponse>(`/intelligence/reports${qs}`);
  },

  analyzeCustom: (request: AnalyzeIntelligenceRequest) =>
    api.post<MarketIntelligenceReportResponse>("/intelligence/analyze", request),
};















