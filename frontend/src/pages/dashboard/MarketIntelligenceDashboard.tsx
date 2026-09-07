import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { marketIntelligenceService } from "../../services/domainServices";
import type {
  MarketOverviewResponse,
  ProductMarketIntelligenceDetail,
  MarketplaceComparisonResponse,
} from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const MarketIntelligenceDashboard: React.FC = () => {
  const [overview, setOverview] = useState<MarketOverviewResponse | null>(null);
  const [marketplaces, setMarketplaces] = useState<MarketplaceComparisonResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedMarketplace, setSelectedMarketplace] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchKeyword, setSearchKeyword] = useState<string>("");
  const [activeTab, setActiveTab] = useState<
    "top" | "trending" | "rising" | "declining" | "opportunity" | "social"
  >("top");

  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchIntelligence = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewRes, mktRes] = await Promise.all([
        marketIntelligenceService.getOverview({
          marketplace: selectedMarketplace !== "all" ? selectedMarketplace : undefined,
          category: selectedCategory !== "all" && selectedCategory.trim() ? selectedCategory.trim() : undefined,
          keyword: searchKeyword.trim() ? searchKeyword.trim() : undefined,
          limit: 30,
        }),
        marketIntelligenceService.getMarketplaces(),
      ]);

      if (overviewRes.success && overviewRes.data) {
        setOverview(overviewRes.data);
      }
      if (mktRes.success && mktRes.data) {
        setMarketplaces(mktRes.data.marketplaces || []);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load market intelligence data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntelligence();
  }, [selectedMarketplace]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchIntelligence();
  };

  const handleExportJson = () => {
    if (!overview) return;
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(overview, null, 2)
    )}`;
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonString);
    downloadAnchor.setAttribute(
      "download",
      `trendpulse_market_intelligence_${selectedMarketplace}_${new Date().toISOString().slice(0, 10)}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast("Market Intelligence report exported to JSON", "success");
  };

  // Select list of products based on active tab
  const getTabProducts = (): ProductMarketIntelligenceDetail[] => {
    if (!overview) return [];
    switch (activeTab) {
      case "top":
        return overview.top_products || [];
      case "trending":
        return overview.trending_products || [];
      case "rising":
        return overview.rising_products || [];
      case "declining":
        return overview.declining_products || [];
      case "opportunity":
        return overview.high_opportunity_products || [];
      case "social":
        return overview.socially_trending_products || [];
      default:
        return overview.top_products || [];
    }
  };

  const activeProducts = getTabProducts();

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Top Header & Context Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-label-caps text-primary uppercase tracking-widest font-bold">
              PHASE 3 MARKET INTELLIGENCE
            </span>
            <span className="text-[10px] font-mono-data bg-primary/10 text-primary px-2 py-0.5 rounded-full border border-primary/20">
              ZERO SYNTHETIC DATA
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Market Intelligence & Social Demand
          </h1>
          <p className="text-xs text-on-surface-variant mt-1 max-w-2xl">
            Real cross-marketplace observations, deterministic 5-factor scoring, trend velocity,
            and AI Analyst interpretations grounded strictly in persisted facts.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={fetchIntelligence}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 bg-surface-container border border-outline-variant/30 rounded-xl text-xs font-medium text-on-surface hover:bg-surface-container-high transition-colors"
          >
            <span className={`material-symbols-outlined text-sm ${loading ? "animate-spin" : ""}`}>
              refresh
            </span>
            Refresh
          </button>
          <button
            onClick={handleExportJson}
            disabled={!overview}
            className="flex items-center gap-1.5 px-3 py-2 bg-surface-container border border-outline-variant/30 rounded-xl text-xs font-medium text-on-surface hover:bg-surface-container-high transition-colors"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            Export Audit
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/20 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Marketplace Selection */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
          <span className="text-xs text-on-surface-variant font-medium whitespace-nowrap mr-1">
            Marketplace:
          </span>
          {[
            { label: "All Marketplaces", value: "all" },
            { label: "Daraz", value: "daraz" },
            { label: "Amazon", value: "amazon" },
            { label: "eBay", value: "ebay" },
            { label: "Shopify", value: "shopify" },
          ].map((m) => (
            <button
              key={m.value}
              onClick={() => setSelectedMarketplace(m.value)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap ${
                selectedMarketplace === m.value
                  ? "bg-primary text-on-primary shadow-sm"
                  : "bg-surface-container text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {m.label}
            </button>
          ))}

          {/* Category Dropdown */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors ml-2"
          >
            <option value="all">All Categories</option>
            <option value="Electronics">Electronics</option>
            <option value="Audio">Audio</option>
            <option value="Fashion">Fashion</option>
            <option value="Home & Kitchen">Home & Kitchen</option>
            <option value="Beauty">Beauty</option>
          </select>
        </div>

        {/* Keyword Search Form */}
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Search keyword (e.g. earbuds)..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors w-full md:w-56"
          />
          <button
            type="submit"
            className="px-3 py-1.5 bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 rounded-xl text-xs font-medium transition-colors"
          >
            Filter
          </button>
        </form>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Synthesizing multi-marketplace intelligence..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchIntelligence} />
      ) : !overview ? (
        <div className="text-center py-12 text-on-surface-variant text-xs">
          No market intelligence available. Please ensure marketplace scrapers have ingested data.
        </div>
      ) : (
        <>
          {/* Top 4 KPI Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Market Score */}
            <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card">
              <div className="flex items-center justify-between text-on-surface-variant mb-2">
                <span className="text-xs font-medium">Average Market Score</span>
                <span className="material-symbols-outlined text-primary text-base">analytics</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-mono-data font-bold text-on-surface">
                  {overview.average_market_score.toFixed(1)}
                </span>
                <span className="text-xs font-mono-data text-on-surface-variant">/100</span>
              </div>
              <div className="mt-3 flex items-center justify-between text-[11px] text-on-surface-variant border-t border-outline-variant/10 pt-2">
                <span>Confidence</span>
                <span className="font-mono-data text-primary font-semibold">
                  {Math.round(overview.overall_confidence * 100)}%
                </span>
              </div>
            </div>

            {/* 2. Total Verified Products */}
            <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card">
              <div className="flex items-center justify-between text-on-surface-variant mb-2">
                <span className="text-xs font-medium">Verified Products Analyzed</span>
                <span className="material-symbols-outlined text-secondary text-base">verified</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-mono-data font-bold text-on-surface">
                  {overview.total_products_analyzed}
                </span>
                <span className="text-xs text-on-surface-variant">listings</span>
              </div>
              <div className="mt-3 flex items-center justify-between text-[11px] text-on-surface-variant border-t border-outline-variant/10 pt-2">
                <span>Data Quality Avg</span>
                <span className="font-mono-data text-secondary font-semibold">
                  {overview.data_quality_average.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* 3. High Demand Signals */}
            <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card">
              <div className="flex items-center justify-between text-on-surface-variant mb-2">
                <span className="text-xs font-medium">High Demand Products</span>
                <span className="material-symbols-outlined text-amber-500 text-base">bolt</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-mono-data font-bold text-on-surface">
                  {overview.high_demand_count}
                </span>
                <span className="text-xs text-on-surface-variant">accelerating</span>
              </div>
              <div className="mt-3 flex items-center justify-between text-[11px] text-on-surface-variant border-t border-outline-variant/10 pt-2">
                <span>Marketplaces</span>
                <span className="font-mono-data text-on-surface font-semibold">
                  {overview.marketplaces_covered.join(", ") || "All"}
                </span>
              </div>
            </div>

            {/* 4. Commercial Opportunity */}
            <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card">
              <div className="flex items-center justify-between text-on-surface-variant mb-2">
                <span className="text-xs font-medium">Expansion Opportunities</span>
                <span className="material-symbols-outlined text-emerald-500 text-base">trending_up</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-mono-data font-bold text-on-surface">
                  {overview.high_opportunity_count}
                </span>
                <span className="text-xs text-on-surface-variant">high-conviction</span>
              </div>
              <div className="mt-3 flex items-center justify-between text-[11px] text-on-surface-variant border-t border-outline-variant/10 pt-2">
                <span>Social Active</span>
                <span className="font-mono-data text-emerald-500 font-semibold">
                  {overview.social_active_count} products
                </span>
              </div>
            </div>
          </div>

          {/* AI Executive Summary & Marketplace Comparison */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: AI Market Analyst Narrative */}
            <div className="lg:col-span-2 bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary text-xl">psychology</span>
                    <h2 className="text-base font-bold text-on-surface">AI Market Analyst Insight</h2>
                  </div>
                  <span className="text-[10px] font-mono-data px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                    Grok / LLM Grounded
                  </span>
                </div>
                <p className="text-xs md:text-sm text-on-surface-variant leading-relaxed mb-4 bg-surface-container p-4 rounded-xl border border-outline-variant/15">
                  {overview.ai_executive_summary ||
                    "Deterministic analytics synthesis complete across real marketplace observations."}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                <div className="p-3 bg-surface-container/60 rounded-xl border border-outline-variant/10">
                  <span className="text-[10px] uppercase text-on-surface-variant font-semibold block mb-1">
                    Provenance
                  </span>
                  <span className="text-xs font-mono-data text-on-surface font-medium">
                    {overview.marketplaces_covered.length > 0
                      ? overview.marketplaces_covered.join(", ")
                      : "Verified Scrapers"}
                  </span>
                </div>
                <div className="p-3 bg-surface-container/60 rounded-xl border border-outline-variant/10">
                  <span className="text-[10px] uppercase text-on-surface-variant font-semibold block mb-1">
                    Confidence Tier
                  </span>
                  <span className="text-xs font-mono-data text-emerald-500 font-medium">
                    {overview.overall_confidence >= 0.8
                      ? "High Conviction"
                      : overview.overall_confidence >= 0.5
                      ? "Moderate"
                      : "Developing"}
                  </span>
                </div>
                <div className="p-3 bg-surface-container/60 rounded-xl border border-outline-variant/10">
                  <span className="text-[10px] uppercase text-on-surface-variant font-semibold block mb-1">
                    Generated At
                  </span>
                  <span className="text-xs font-mono-data text-on-surface font-medium">
                    {new Date(overview.generated_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>
            </div>

            {/* Right: Cross-Marketplace Comparison Chart */}
            <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 flex flex-col justify-between">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-on-surface">Cross-Marketplace Acclaim</h3>
                <span className="text-[10px] font-mono-data text-on-surface-variant">Market Score</span>
              </div>
              <div className="h-44 w-full">
                {marketplaces.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={marketplaces} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="marketplace" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                      <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 10 }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#1e293b",
                          borderColor: "rgba(255,255,255,0.1)",
                          borderRadius: "8px",
                          fontSize: "11px",
                        }}
                      />
                      <Bar dataKey="average_market_score" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-on-surface-variant">
                    No marketplace comparison data yet
                  </div>
                )}
              </div>
              <div className="text-[11px] text-on-surface-variant text-center pt-2 border-t border-outline-variant/10">
                Calculated strictly from real product listings
              </div>
            </div>
          </div>

          {/* Tabbed Product Intelligence Table */}
          <div className="bg-surface-container-low rounded-2xl border border-outline-variant/20 overflow-hidden">
            {/* Table Navigation Tabs */}
            <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-outline-variant/15 flex-wrap gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                {[
                  { key: "top", label: "Top Market Score" },
                  { key: "trending", label: "High Demand" },
                  { key: "rising", label: "Rising Products" },
                  { key: "declining", label: "Declining Products" },
                  { key: "opportunity", label: "High Opportunity" },
                  { key: "social", label: "Social Demand" },
                ].map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setActiveTab(t.key as any)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all ${
                      activeTab === t.key
                        ? "bg-primary text-on-primary shadow-sm"
                        : "bg-surface-container text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <span className="text-[11px] font-mono-data text-on-surface-variant">
                Showing {activeProducts.length} real products
              </span>
            </div>

            {/* Products Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface-container/50 text-on-surface-variant uppercase text-[10px] font-semibold border-b border-outline-variant/10">
                  <tr>
                    <th className="py-3.5 px-6">Product & Marketplace</th>
                    <th className="py-3.5 px-4">Price</th>
                    <th className="py-3.5 px-4">Market Score</th>
                    <th className="py-3.5 px-4">Demand</th>
                    <th className="py-3.5 px-4">Trend Velocity</th>
                    <th className="py-3.5 px-4">Opportunity</th>
                    <th className="py-3.5 px-4">Social Signal</th>
                    <th className="py-3.5 px-6 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10">
                  {activeProducts.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-12 text-center text-on-surface-variant">
                        No products meet the criteria for this filter. Zero synthetic products fabricated.
                      </td>
                    </tr>
                  ) : (
                    activeProducts.map((p) => {
                      const velocityVal = p.trend_velocity?.velocity;
                      const growthVal = p.growth?.growth_7d;

                      return (
                        <tr
                          key={`${p.marketplace}_${p.product_id}`}
                          className="hover:bg-surface-container/40 transition-colors group cursor-pointer"
                          onClick={() =>
                            navigate(
                              `/products/${encodeURIComponent(p.product_id)}?platform=${encodeURIComponent(
                                p.marketplace
                              )}`
                            )
                          }
                        >
                          {/* Product & Marketplace */}
                          <td className="py-4 px-6 max-w-xs">
                            <div className="flex items-center gap-3">
                              {p.image_url ? (
                                <img
                                  src={p.image_url}
                                  alt={p.title}
                                  className="w-10 h-10 rounded-lg object-cover bg-surface-container border border-outline-variant/20 flex-shrink-0"
                                />
                              ) : (
                                <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center text-on-surface-variant flex-shrink-0">
                                  <span className="material-symbols-outlined text-lg">shopping_bag</span>
                                </div>
                              )}
                              <div className="truncate">
                                <div className="font-semibold text-on-surface truncate group-hover:text-primary transition-colors">
                                  {p.title}
                                </div>
                                <div className="flex items-center gap-2 text-[10px] text-on-surface-variant mt-0.5">
                                  <span className="uppercase font-mono-data font-bold text-primary">
                                    {p.marketplace}
                                  </span>
                                  <span>•</span>
                                  <span>{p.category || "General"}</span>
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Price */}
                          <td className="py-4 px-4 font-mono-data">
                            {p.current_price > 0 ? (
                              <span className="font-semibold text-on-surface">
                                {p.currency} {p.current_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                              </span>
                            ) : (
                              <span className="text-on-surface-variant">N/A</span>
                            )}
                          </td>

                          {/* Market Score */}
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-2">
                              <span className="font-mono-data font-bold text-sm text-primary">
                                {p.market_score.score.toFixed(1)}
                              </span>
                              <div className="w-12 bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                                <div
                                  className="bg-primary h-full rounded-full"
                                  style={{ width: `${Math.min(p.market_score.score, 100)}%` }}
                                />
                              </div>
                            </div>
                          </td>

                          {/* Demand */}
                          <td className="py-4 px-4">
                            <span
                              className={`text-[10px] font-mono-data font-bold uppercase px-2 py-0.5 rounded border ${
                                p.demand.demand_level === "VERY_HIGH" || p.demand.demand_level === "Very Strong"
                                  ? "bg-amber-500/10 text-amber-500 border-amber-500/20"
                                  : p.demand.demand_level === "HIGH" || p.demand.demand_level === "Strong"
                                  ? "bg-primary/10 text-primary border-primary/20"
                                  : "bg-surface-container text-on-surface-variant border-outline-variant/20"
                              }`}
                            >
                              {p.demand.demand_level}
                            </span>
                          </td>

                          {/* Trend Velocity & Growth */}
                          <td className="py-4 px-4 font-mono-data text-[11px]">
                            {velocityVal !== null && velocityVal !== undefined ? (
                              <span
                                className={velocityVal >= 0 ? "text-emerald-500 font-semibold" : "text-rose-500 font-semibold"}
                              >
                                {velocityVal >= 0 ? "+" : ""}
                                {velocityVal.toFixed(1)}/day
                              </span>
                            ) : growthVal !== null && growthVal !== undefined ? (
                              <span
                                className={growthVal >= 0 ? "text-emerald-500 font-semibold" : "text-rose-500 font-semibold"}
                              >
                                {growthVal >= 0 ? "+" : ""}
                                {growthVal.toFixed(1)}% 7d
                              </span>
                            ) : (
                              <span className="text-on-surface-variant/60">insufficient_data</span>
                            )}
                          </td>

                          {/* Opportunity */}
                          <td className="py-4 px-4">
                            <span
                              className={`text-[10px] font-mono-data font-bold uppercase px-2 py-0.5 rounded border ${
                                p.opportunity.opportunity_level === "Exceptional"
                                  ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                                  : p.opportunity.opportunity_level === "High"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                  : "bg-surface-container text-on-surface-variant border-outline-variant/20"
                              }`}
                            >
                              {p.opportunity.opportunity_level}
                            </span>
                          </td>

                          {/* Social Signal */}
                          <td className="py-4 px-4">
                            {p.viral_potential.has_social_signals ? (
                              <div className="flex items-center gap-1.5 text-xs text-primary font-medium">
                                <span className="material-symbols-outlined text-sm">campaign</span>
                                <span>{p.social_signals.length} mentions</span>
                              </div>
                            ) : (
                              <span className="text-[11px] text-on-surface-variant/50">None</span>
                            )}
                          </td>

                          {/* Action */}
                          <td className="py-4 px-6 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(
                                  `/products/${encodeURIComponent(p.product_id)}?platform=${encodeURIComponent(
                                    p.marketplace
                                  )}`
                                );
                              }}
                              className="px-3 py-1 bg-surface-container hover:bg-primary/20 hover:text-primary rounded-lg text-xs font-medium transition-colors"
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
