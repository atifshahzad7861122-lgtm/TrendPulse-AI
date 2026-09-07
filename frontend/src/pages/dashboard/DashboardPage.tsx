import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { dashboardService } from "../../services/domainServices";
import type { DashboardSummary, TrendPoint, DashboardProductItem, LiveSignalItem } from "../../types";
import { LoadingSpinner, ErrorState, EmptyState } from "../../components/common/StateComponents";
import { DarazProductModal } from "../../components/products/DarazProductModal";
import { useToast } from "../../context/ToastContext";
import { MarketIntelligenceDashboard } from "./MarketIntelligenceDashboard";

export const DashboardPage: React.FC = () => {
  const [dashboardMode, setDashboardMode] = useState<"market_intelligence" | "daraz_pulse">("market_intelligence");
  const [timeRange, setTimeRange] = useState<string>("30d");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Daraz detail modal state
  const [selectedDarazItemId, setSelectedDarazItemId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { showToast } = useToast();

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, trendRes] = await Promise.all([
        dashboardService.getSummary({
          time_range: timeRange,
          category: selectedCategory,
          platform: selectedPlatform,
        }),
        dashboardService.getTrends({
          time_range: timeRange,
          category: selectedCategory,
          platform: selectedPlatform,
        }),
      ]);

      if (sumRes.success && sumRes.data) setSummary(sumRes.data);
      if (trendRes.success && trendRes.data) setTrends(trendRes.data);
    } catch (err: any) {
      setError(err.message || "Failed to load live marketplace signals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [timeRange, selectedCategory, selectedPlatform]);

  const handleProductClick = (product: DashboardProductItem) => {
    const rawId = product.product_id || product.id.replace("daraz_", "");
    setSelectedDarazItemId(rawId);
    setIsModalOpen(true);
  };

  const handleSignalClick = (signal: LiveSignalItem) => {
    if (signal.product_id) {
      const rawId = signal.product_id.replace("daraz_", "");
      setSelectedDarazItemId(rawId);
      setIsModalOpen(true);
    }
  };

  const handleQuickExport = () => {
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify({ summary, trends, source: "Daraz Pakistan", exportedAt: new Date().toISOString() }, null, 2)
    )}`;
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonString);
    downloadAnchor.setAttribute("download", `trendpulse_live_daraz_dashboard_${timeRange}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast("Live marketplace data exported to JSON", "success");
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Perspective Toggle */}
      <div className="flex items-center gap-2 border-b border-outline-variant/15 pb-4">
        <button
          onClick={() => setDashboardMode("market_intelligence")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            dashboardMode === "market_intelligence"
              ? "bg-primary text-on-primary shadow-sm"
              : "bg-surface-container text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <span className="material-symbols-outlined text-sm">psychology</span>
          Market Intelligence & AI Analytics (Phase 3)
        </button>
        <button
          onClick={() => setDashboardMode("daraz_pulse")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            dashboardMode === "daraz_pulse"
              ? "bg-primary text-on-primary shadow-sm"
              : "bg-surface-container text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <span className="material-symbols-outlined text-sm">storefront</span>
          Daraz Live Pulse
        </button>
      </div>

      {dashboardMode === "market_intelligence" ? (
        <MarketIntelligenceDashboard />
      ) : (
        <div className="space-y-8">
          {/* Top Controls & Action Bar */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
                  REAL-TIME MARKET PULSE
                </span>
            {summary?.is_live ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono-data font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                LIVE DATA (Daraz Pakistan)
              </span>
            ) : summary?.data_source === "database_cache" ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-mono-data font-semibold" title={summary.system_status}>
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Cached Data ({summary.data_age_seconds !== null && summary.data_age_seconds !== undefined ? (summary.data_age_seconds < 60 ? `${summary.data_age_seconds}s ago` : summary.data_age_seconds < 3600 ? `${Math.floor(summary.data_age_seconds / 60)}m ago` : `${Math.floor(summary.data_age_seconds / 3600)}h ago`) : "Synced"})
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant border border-outline-variant/20 text-[10px] font-mono-data font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-on-surface-variant/50" />
                Waiting for marketplace data
              </span>
            )}
          </div>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Intelligence Overview
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Real marketplace pricing, buyer review sentiment, and verified catalog availability from Daraz Pakistan.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Timeframe Selector */}
          <div className="flex items-center bg-surface-container rounded-xl p-1 border border-outline-variant/20">
            {["7d", "30d", "all"].map((t) => (
              <button
                key={t}
                onClick={() => setTimeRange(t)}
                className={`px-3 py-1.5 rounded-lg text-xs font-label-caps uppercase transition-all ${
                  timeRange === t
                    ? "bg-primary text-on-primary font-bold shadow-[0_0_12px_rgba(255,182,141,0.25)]"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {t === "7d" ? "7 Days" : t === "30d" ? "30 Days" : "All Time"}
              </button>
            ))}
          </div>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-surface-container border border-outline-variant/20 rounded-xl px-3 py-2 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
          >
            <option value="all">All Categories</option>
            <option value="Consumer Electronics">Consumer Electronics</option>
            <option value="Earbuds">Wireless Earbuds & Audio</option>
            <option value="Laptops">Laptops & Computers</option>
            <option value="Watches">Smart Watches & Wearables</option>
            <option value="Keyboards">Keyboards & Accessories</option>
          </select>

          {/* Platform Filter */}
          <select
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className="bg-surface-container border border-outline-variant/20 rounded-xl px-3 py-2 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
          >
            <option value="all">All Platforms (Live: Daraz)</option>
            <option value="Daraz">Daraz Pakistan (Active)</option>
          </select>

          {/* Actions */}
          <button
            onClick={fetchData}
            className="p-2 rounded-xl bg-surface-container border border-outline-variant/20 text-on-surface-variant hover:text-primary hover:border-primary/40 transition-all"
            title="Refresh live marketplace data"
          >
            <span className="material-symbols-outlined text-lg">refresh</span>
          </button>

          <button
            onClick={handleQuickExport}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface-container border border-outline-variant/20 text-xs font-label-caps text-on-surface hover:text-primary hover:border-primary/40 transition-all"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            Export
          </button>

          <Link
            to="/report-generation"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-on-primary text-xs font-label-caps font-semibold hover:bg-primary-container transition-all shadow-[0_0_15px_rgba(255,182,141,0.2)]"
          >
            <span className="material-symbols-outlined text-sm">auto_awesome</span>
            Generate Report
          </Link>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Ingesting verified live marketplace data from Daraz Pakistan..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchData} />
      ) : (
        <>
          {/* KPI Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {summary?.metrics.map((m, idx) => (
              <div
                key={idx}
                className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card relative overflow-hidden group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider">
                    {m.title}
                  </span>
                  <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary group-hover:bg-primary/20 transition-colors">
                    <span className="material-symbols-outlined text-lg">{m.icon}</span>
                  </div>
                </div>

                <div className="mt-4 flex items-baseline justify-between gap-2">
                  <span className="text-2xl lg:text-3xl font-mono-data font-bold text-on-surface tracking-tight truncate">
                    {m.value}
                  </span>
                  <span
                    className={`text-[11px] font-mono-data font-semibold px-2 py-0.5 rounded shrink-0 ${
                      m.is_positive
                        ? "bg-primary/10 text-primary border border-primary/20"
                        : "bg-error/10 text-error border border-error/20"
                    }`}
                  >
                    {m.change}
                  </span>
                </div>

                <p className="text-[11px] text-on-surface-variant mt-2 truncate" title={m.subtext}>
                  {m.subtext}
                </p>
              </div>
            ))}
          </div>

          {/* Time Series Chart & Live Signals Split */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Chart Container */}
            <div className="lg:col-span-8 bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card flex flex-col justify-between">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-base font-bold text-on-surface">Market Price & Sentiment Trajectory</h3>
                  <p className="text-xs text-on-surface-variant">
                    Aggregated acclaim index derived from live buyer feedback and pricing distributions
                  </p>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono-data">
                  <span className="flex items-center gap-1.5 text-primary">
                    <div className="w-2.5 h-2.5 rounded-full bg-primary" /> Daraz Acclaim Index
                  </span>
                </div>
              </div>

              <div className="h-72 w-full">
                {trends.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#df7328" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#df7328" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#292a27" />
                      <XAxis
                        dataKey="timestamp"
                        stroke="#888888"
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="#888888"
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                        domain={["dataMin - 5", "dataMax + 5"]}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#1e201d",
                          borderColor: "#564338",
                          borderRadius: "0.75rem",
                          color: "#e3e3de",
                          fontSize: "12px",
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="score"
                        name="Acclaim Score"
                        stroke="#ffb68d"
                        strokeWidth={2.5}
                        fillOpacity={1}
                        fill="url(#scoreGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-on-surface-variant font-mono-data">
                    Insufficient live time-series data
                  </div>
                )}
              </div>
            </div>

            {/* Live Signals Stream */}
            <div className="lg:col-span-4 bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card flex flex-col">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-outline-variant/15">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider font-label-caps">
                    Live Marketplace Signals
                  </h3>
                </div>
                <span className="text-[10px] font-mono-data text-on-surface-variant">
                  {summary?.live_signals.length || 0} Events
                </span>
              </div>

              <div className="space-y-3 flex-1 overflow-y-auto max-h-72 pr-1">
                {summary?.live_signals && summary.live_signals.length > 0 ? (
                  summary.live_signals.map((sig) => (
                    <div
                      key={sig.id}
                      onClick={() => handleSignalClick(sig)}
                      className={`p-3 rounded-xl bg-surface-container border border-outline-variant/15 transition-all ${
                        sig.product_id ? "hover:border-primary/40 cursor-pointer hover:bg-surface-container-high" : ""
                      }`}
                      title={sig.product_id ? "Click to view full Daraz product details" : undefined}
                    >
                      <div className="flex items-center justify-between text-[11px] font-mono-data mb-1">
                        <span className="text-primary font-bold uppercase tracking-wider text-[10px] px-1.5 py-0.5 rounded bg-primary/10">
                          {sig.platform}
                        </span>
                        <span className="text-on-surface-variant text-[10px]">
                          {sig.timestamp.includes("T") ? "Just now" : sig.timestamp}
                        </span>
                      </div>
                      <p className="text-xs text-on-surface leading-snug line-clamp-2">{sig.text}</p>
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant font-mono-data truncate max-w-[140px]">
                          {sig.category}
                        </span>
                        <span className="text-[11px] font-bold font-mono-data text-primary shrink-0">
                          {sig.growth}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="h-40 flex items-center justify-center text-xs text-on-surface-variant text-center p-4">
                    Waiting for real-time signals from Daraz Pakistan...
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Top Surging Breakout Products */}
          <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-on-surface">Live Daraz Pakistan Catalog</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 font-mono-data">
                    Verified Marketplace Data
                  </span>
                </div>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  Real products directly ingested from Daraz Pakistan with real prices, seller ratings, and stock status.
                </p>
              </div>
              <Link
                to="/products"
                className="text-xs font-label-caps text-primary hover:underline flex items-center gap-1 shrink-0"
              >
                Global Product Catalog
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </Link>
            </div>

            {summary?.top_surging && summary.top_surging.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {summary.top_surging.map((p) => (
                  <div
                    key={p.id}
                    onClick={() => handleProductClick(p)}
                    className="bg-surface-container p-4 rounded-xl border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.02] glass-card flex flex-col justify-between group"
                  >
                    <div>
                      {/* Product Thumbnail & Badges */}
                      <div className="relative w-full h-36 rounded-lg bg-surface-container-high overflow-hidden mb-3 border border-outline-variant/10 flex items-center justify-center">
                        {p.image_url ? (
                          <img
                            src={p.image_url}
                            alt={p.name}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            loading="lazy"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                        ) : (
                          <div className="flex flex-col items-center justify-center text-on-surface-variant gap-1">
                            <span className="material-symbols-outlined text-2xl text-primary/60">shopping_bag</span>
                            <span className="text-[10px] font-mono-data">Daraz PK</span>
                          </div>
                        )}
                        <div className="absolute top-2 left-2 flex flex-col gap-1">
                          <span className="text-[9px] font-mono-data font-bold text-on-primary bg-primary/90 px-1.5 py-0.5 rounded shadow-sm">
                            {p.velocity_label || "Daraz PK"}
                          </span>
                          {p.discount_label && (
                            <span className="text-[9px] font-mono-data font-bold text-white bg-error px-1.5 py-0.5 rounded shadow-sm">
                              {p.discount_label}
                            </span>
                          )}
                        </div>
                        {p.in_stock && (
                          <span className="absolute bottom-2 right-2 text-[9px] font-mono-data font-semibold text-emerald-400 bg-surface-container-highest/90 px-1.5 py-0.5 rounded border border-emerald-500/30">
                            In Stock
                          </span>
                        )}
                      </div>

                      <div className="flex items-center justify-between mb-1.5 text-[11px] font-mono-data text-on-surface-variant">
                        <span className="truncate max-w-[130px]" title={p.seller_name || "Daraz Seller"}>
                          {p.seller_name || "Daraz Seller"}
                        </span>
                        <span className="text-primary font-semibold shrink-0">
                          {p.platform || "Daraz"}
                        </span>
                      </div>

                      <h4 className="text-xs font-bold text-on-surface leading-snug line-clamp-2 group-hover:text-primary transition-colors">
                        {p.name}
                      </h4>

                      <div className="flex items-center gap-2 mt-1 text-[11px] font-mono-data text-on-surface-variant">
                        {p.rating && p.rating > 0 ? (
                          <span className="flex items-center gap-0.5 text-amber-400 font-semibold">
                            <span className="material-symbols-outlined text-[13px]">star</span>
                            {p.rating.toFixed(1)}
                          </span>
                        ) : null}
                        {p.review_count && p.review_count > 0 ? (
                          <span>({p.review_count.toLocaleString()} reviews)</span>
                        ) : (
                          <span>Verified listing</span>
                        )}
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-outline-variant/15 flex items-end justify-between">
                      <div>
                        <span className="text-[10px] text-on-surface-variant uppercase font-label-caps block">
                          Current Price
                        </span>
                        <p className="text-base font-bold font-mono-data text-primary">
                          {p.price_formatted || (p.price ? `PKR ${p.price.toLocaleString()}` : "PKR 0")}
                        </p>
                        {p.original_price_formatted && (
                          <p className="text-[10px] font-mono-data text-on-surface-variant line-through">
                            {p.original_price_formatted}
                          </p>
                        )}
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-on-surface-variant uppercase font-label-caps block">
                          Demand Score
                        </span>
                        <p className="text-xs font-bold font-mono-data text-on-surface">
                          {p.trend_score || 75.0}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No Live Products Found"
                description="No marketplace products matching the selected criteria were found on Daraz Pakistan."
                actionText="Reset Category Filter"
                onAction={() => {
                  setSelectedCategory("all");
                  setSelectedPlatform("all");
                }}
              />
            )}
          </div>
        </>
      )}
        </div>
      )}

      {/* Real Product Detail Modal */}
      {selectedDarazItemId && (
        <DarazProductModal
          itemId={selectedDarazItemId}
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setSelectedDarazItemId(null);
          }}
        />
      )}
    </div>
  );
};
