import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
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
import type { DashboardSummary, TrendPoint } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const DashboardPage: React.FC = () => {
  const [timeRange, setTimeRange] = useState<string>("30d");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { showToast } = useToast();
  const navigate = useNavigate();

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
      setError(err.message || "Failed to load dashboard signals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [timeRange, selectedCategory, selectedPlatform]);

  const handleQuickExport = () => {
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify({ summary, trends, exportedAt: new Date().toISOString() }, null, 2)
    )}`;
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonString);
    downloadAnchor.setAttribute("download", `trendpulse_dashboard_${timeRange}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast("Dashboard metrics exported to JSON", "success");
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Top Controls & Action Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            REAL-TIME MARKET PULSE
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Intelligence Overview
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Synthesized multi-platform velocity across regional consumer categories.
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
            <option value="Beauty & Personal Care">Beauty & Personal Care</option>
            <option value="Sports & Outdoor">Sports & Outdoor</option>
            <option value="Consumer Electronics">Consumer Electronics</option>
            <option value="Home & Kitchen">Home & Kitchen</option>
            <option value="Fashion & Apparel">Fashion & Apparel</option>
          </select>

          {/* Platform Filter */}
          <select
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className="bg-surface-container border border-outline-variant/20 rounded-xl px-3 py-2 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
          >
            <option value="all">All Platforms</option>
            <option value="TikTok">TikTok</option>
            <option value="Daraz">Daraz</option>
            <option value="Instagram">Instagram</option>
            <option value="YouTube">YouTube</option>
          </select>

          {/* Actions */}
          <button
            onClick={fetchData}
            className="p-2 rounded-xl bg-surface-container border border-outline-variant/20 text-on-surface-variant hover:text-primary hover:border-primary/40 transition-all"
            title="Refresh signals"
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
        <LoadingSpinner size="lg" label="Ingesting and computing market velocities..." />
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

                <div className="mt-4 flex items-baseline justify-between">
                  <span className="text-3xl font-mono-data font-bold text-on-surface tracking-tight">
                    {m.value}
                  </span>
                  <span
                    className={`text-xs font-mono-data font-semibold px-2 py-0.5 rounded ${
                      m.is_positive
                        ? "bg-primary/10 text-primary border border-primary/20"
                        : "bg-error/10 text-error border border-error/20"
                    }`}
                  >
                    {m.change}
                  </span>
                </div>

                <p className="text-[11px] text-on-surface-variant mt-2 truncate">{m.subtext}</p>
              </div>
            ))}
          </div>

          {/* Time Series Chart & Live Signals Split */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Chart Container */}
            <div className="lg:col-span-8 bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card flex flex-col justify-between">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-base font-bold text-on-surface">Trend Velocity Evolution</h3>
                  <p className="text-xs text-on-surface-variant">
                    Compound score calculated across social velocity & search anomalies
                  </p>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono-data">
                  <span className="flex items-center gap-1.5 text-primary">
                    <div className="w-2.5 h-2.5 rounded-full bg-primary" /> Velocity Index
                  </span>
                </div>
              </div>

              <div className="h-72 w-full">
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
                      name="Velocity Score"
                      stroke="#ffb68d"
                      strokeWidth={2.5}
                      fillOpacity={1}
                      fill="url(#scoreGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Live Signals Stream */}
            <div className="lg:col-span-4 bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card flex flex-col">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-outline-variant/15">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider font-label-caps">
                    Live Signal Stream
                  </h3>
                </div>
                <Link to="/alerts" className="text-xs text-primary hover:underline font-label-caps">
                  View All
                </Link>
              </div>

              <div className="space-y-3 flex-1 overflow-y-auto max-h-72 pr-1">
                {summary?.live_signals.map((sig) => (
                  <div
                    key={sig.id}
                    className="p-3 rounded-xl bg-surface-container border border-outline-variant/15 hover:border-primary/30 transition-colors"
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono-data mb-1">
                      <span className="text-primary font-semibold">{sig.platform}</span>
                      <span className="text-on-surface-variant">{sig.timestamp}</span>
                    </div>
                    <p className="text-xs text-on-surface leading-snug">{sig.text}</p>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-[10px] px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant font-mono-data">
                        {sig.category}
                      </span>
                      <span className="text-[11px] font-bold font-mono-data text-primary">
                        {sig.growth}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Top Surging Breakout Products */}
          <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-base font-bold text-on-surface">Top Surging Breakout Products</h3>
                <p className="text-xs text-on-surface-variant">
                  High conviction products exhibiting viral conversion patterns across channels.
                </p>
              </div>
              <Link
                to="/products"
                className="text-xs font-label-caps text-primary hover:underline flex items-center gap-1"
              >
                Explore Product Catalog
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {summary?.top_surging.map((p) => (
                <div
                  key={p.id}
                  onClick={() => navigate(`/products/${p.id}`)}
                  className="bg-surface-container p-5 rounded-xl border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.02] glass-card flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-mono-data font-semibold text-primary uppercase px-2 py-0.5 rounded bg-primary/10 border border-primary/20">
                        {p.velocity_label}
                      </span>
                      <span className="text-[11px] font-mono-data text-on-surface-variant">
                        {p.platform}
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-on-surface leading-snug line-clamp-2">
                      {p.name}
                    </h4>
                    <p className="text-xs text-on-surface-variant mt-1">{p.category}</p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-outline-variant/15 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-on-surface-variant uppercase font-label-caps">
                        Trend Score
                      </span>
                      <p className="text-lg font-bold font-mono-data text-primary">
                        {p.trend_score}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] text-on-surface-variant uppercase font-label-caps">
                        Growth
                      </span>
                      <p className="text-xs font-bold font-mono-data text-on-surface">
                        +{p.growth_rate}%
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
