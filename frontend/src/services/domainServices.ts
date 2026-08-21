import { api } from "./api";
import type {
  User, Workspace, Product, Category, PlatformMetrics,
  DashboardSummary, TrendPoint, Alert, NotificationItem, Report,
  DataSource, SearchResponse, UserSettings, IngestionResult, DataSourceConfigStatus,
  IntelligenceSummary
} from "../types";

export const authService = {
  register: (data: { full_name: string; email: string; password: string; confirm_password: string; terms_accepted: boolean }) =>
    api.post<{ user_id: string; email: string; verification_token: string; dev_verification_url: string }>("/auth/register", data),

  login: (data: { email: string; password: string; remember_me?: boolean }) =>
    api.post<{ access_token: string; user_id: string; email: string; full_name: string; is_verified: boolean; workspace_id?: string; role: string }>("/auth/login", data),

  logout: () => api.post("/auth/logout"),

  verifyEmail: (token: string) =>
    api.post<{ access_token: string; user_id: string; is_verified: boolean; workspace_id?: string }>("/auth/verify-email", { token }),

  forgotPassword: (email: string) =>
    api.post<{ email: string; reset_token: string; dev_reset_url: string }>("/auth/forgot-password", { email }),

  resetPassword: (data: { token: string; new_password: string; confirm_password: string }) =>
    api.post<{ email: string }>("/auth/reset-password", data),

  getMe: () => api.get<User>("/auth/me"),
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
  list: (params: { category?: string; platform?: string; search?: string; sort_by?: string } = {}) => {
    const query = new URLSearchParams(params as any).toString();
    return api.get<Product[]>(`/products?${query}`);
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

export const settingsService = {
  getSettings: () => api.get<UserSettings>("/settings"),
  updateSettings: (settings: UserSettings) => api.put<UserSettings>("/settings", settings),
};

