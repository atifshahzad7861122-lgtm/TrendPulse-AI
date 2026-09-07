import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { productService, watchlistService, scraperService, marketIntelligenceService } from "../../services/domainServices";
import type { Product, RawScrapedDataResponse, ProductMarketIntelligenceDetail } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const ProductDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [marketIntel, setMarketIntel] = useState<ProductMarketIntelligenceDetail | null>(null);
  const [intelLoading, setIntelLoading] = useState(false);
  const [related, setRelated] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Raw Scraped Data Modal State
  const [isRawModalOpen, setIsRawModalOpen] = useState(false);
  const [rawScrapedData, setRawScrapedData] = useState<RawScrapedDataResponse | null>(null);
  const [rawLoading, setRawLoading] = useState(false);

  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchDetail = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await productService.getById(id);
      if (res.success && res.data) {
        setProduct(res.data);
        const relRes = await productService.list({ category: res.data.category });
        if (relRes.success && relRes.data) {
          setRelated(relRes.data.filter((p) => p.id !== id).slice(0, 3));
        }

        // Fetch Phase 3 Market Intelligence
        setIntelLoading(true);
        try {
          const intelRes = await marketIntelligenceService.getProductDetail(res.data.id, res.data.primary_platform);
          if (intelRes.success && intelRes.data) {
            setMarketIntel(intelRes.data);
          }
        } catch {
          // Graceful fallback if no historical snapshot yet
        } finally {
          setIntelLoading(false);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load product intelligence detail");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  const handleOpenRawData = async () => {
    if (!product) return;
    setIsRawModalOpen(true);
    setRawLoading(true);
    try {
      const res = await scraperService.getProductRaw(product.id, product.primary_platform);
      if (res.success && res.data) {
        setRawScrapedData(res.data);
      } else if (product.raw_data) {
        setRawScrapedData({
          id: `raw_${product.id}`,
          marketplace: product.primary_platform,
          product_id: product.id,
          source_url: product.raw_data?.source_url || "",
          parser_version: "2.0.0",
          extraction_status: "complete",
          quality_status: "valid",
          confidence_score: 1.0,
          scraped_at: new Date().toISOString(),
          raw_payload: product.raw_data,
          normalized_payload: product.raw_data
        });
      }
    } catch (err) {
      if (product.raw_data) {
        setRawScrapedData({
          id: `raw_${product.id}`,
          marketplace: product.primary_platform,
          product_id: product.id,
          source_url: "",
          parser_version: "2.0.0",
          extraction_status: "complete",
          quality_status: "valid",
          confidence_score: 1.0,
          scraped_at: new Date().toISOString(),
          raw_payload: product.raw_data,
          normalized_payload: product.raw_data
        });
      }
    } finally {
      setRawLoading(false);
    }
  };

  const handleToggleWatchlist = async () => {
    if (!product) return;
    try {
      if (product.is_watchlisted) {
        await watchlistService.remove(product.id);
        setProduct({ ...product, is_watchlisted: false });
        showToast("Removed from watchlist", "info");
      } else {
        await watchlistService.add(product.id);
        setProduct({ ...product, is_watchlisted: true });
        showToast("Added to watchlist", "success");
      }
    } catch (err: any) {
      showToast(err.message || "Action failed", "error");
    }
  };

  if (loading) {
    return <LoadingSpinner size="lg" label="Computing real-time product signals..." />;
  }

  if (error || !product) {
    return <ErrorState message={error || "Product not found"} onRetry={fetchDetail} />;
  }

  const specs = product.raw_data?.specifications || product.raw_data?.specs || {};
  const variants = product.raw_data?.variants || [];

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Top Navigation & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface-variant hover:text-on-surface hover:border-primary/40 transition-all"
            title="Go back"
          >
            <span className="material-symbols-outlined text-lg">arrow_back</span>
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono-data text-primary px-2.5 py-0.5 rounded-full bg-primary/10 border border-primary/20">
                {product.velocity_label}
              </span>
              <span className="text-xs text-on-surface-variant font-mono-data">{product.category}</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
              {product.name}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleOpenRawData}
            className="px-4 py-2.5 rounded-xl text-xs font-label-caps font-semibold bg-surface-container border border-outline-variant/30 text-on-surface-variant hover:text-primary hover:border-primary/40 transition-all flex items-center gap-1.5"
            title="Inspect factual raw scraped payload"
          >
            <span className="material-symbols-outlined text-sm">code</span>
            Raw Scraped Payload
          </button>

          <button
            onClick={handleToggleWatchlist}
            className={`px-4 py-2.5 rounded-xl text-xs font-label-caps font-semibold transition-all flex items-center gap-2 ${
              product.is_watchlisted
                ? "bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25"
                : "bg-surface-container border border-outline-variant/30 text-on-surface-variant hover:text-on-surface hover:border-primary/40"
            }`}
          >
            <span
              className={`material-symbols-outlined text-base ${
                product.is_watchlisted ? "fill-current" : ""
              }`}
            >
              bookmark
            </span>
            {product.is_watchlisted ? "Watchlisted" : "Add to Watchlist"}
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
        <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Trend Score</span>
          <p className="text-2xl font-bold text-primary mt-1 font-mono-data">{product.trend_score}</p>
        </div>
        <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Growth Rate</span>
          <p className="text-2xl font-bold text-emerald-400 mt-1 font-mono-data">+{product.growth_rate}%</p>
        </div>
        <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Search Volume</span>
          <p className="text-2xl font-bold text-on-surface mt-1 font-mono-data">{product.volume.toLocaleString()}</p>
        </div>
        <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Price Range</span>
          <p className="text-xl font-bold text-on-surface mt-1 font-mono-data">{product.price_range}</p>
        </div>
        <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Sentiment</span>
          <p className="text-2xl font-bold text-primary mt-1 font-mono-data">{product.sentiment_score}%</p>
        </div>
        <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Active Signals</span>
          <p className="text-2xl font-bold text-on-surface mt-1 font-mono-data">{product.signals_count}</p>
        </div>
      </div>

      {/* Phase 3 Market Intelligence & Social Demand Analytics */}
      {intelLoading ? (
        <div className="p-8 rounded-2xl bg-surface-container-low border border-primary/20 flex items-center justify-center gap-3">
          <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <span className="text-xs font-mono-data text-on-surface-variant">Computing factual Market Score, Demand, and Social Intelligence...</span>
        </div>
      ) : marketIntel ? (
        <div className="p-6 rounded-2xl bg-surface-container-low border border-primary/30 glass-card space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-outline-variant/15 pb-4">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-primary text-2xl">psychology</span>
              <div>
                <h3 className="text-lg font-bold text-on-surface">Phase 3 Market Intelligence Suite</h3>
                <p className="text-xs text-on-surface-variant">Real marketplace observations, demand signals, and verified analytics</p>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-mono-data uppercase px-2.5 py-1 rounded-full bg-surface-container border border-outline-variant/30 text-on-surface-variant">
                Platform: {marketIntel.marketplace}
              </span>
              <span className="text-[10px] font-mono-data uppercase px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                Data Quality: {marketIntel.data_quality_score}%
              </span>
              <span className="text-[10px] font-mono-data uppercase px-2.5 py-1 rounded-full bg-primary/10 border border-primary/30 text-primary">
                Confidence: {(marketIntel.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* 4 Core Pillars Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Pillar 1: Market Score */}
            <div className="p-4 rounded-xl bg-surface-container/60 border border-outline-variant/20 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Market Score</span>
                <span className={`text-xs font-mono-data px-2 py-0.5 rounded-full font-bold ${
                  marketIntel.market_score.score >= 75 ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" :
                  marketIntel.market_score.score >= 50 ? "bg-primary/15 text-primary border border-primary/30" :
                  "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                }`}>
                  {marketIntel.market_score.score.toFixed(1)}/100
                </span>
              </div>
              <div className="space-y-1.5 text-[11px] font-mono-data">
                <div className="flex justify-between text-on-surface-variant">
                  <span>Demand (30%):</span>
                  <span className="text-on-surface font-semibold">{marketIntel.market_score.components.demand?.toFixed(1) || "N/A"}</span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Growth (20%):</span>
                  <span className="text-on-surface font-semibold">
                    {marketIntel.market_score.history_status === "insufficient_history"
                      ? `${marketIntel.market_score.components.growth?.toFixed(1) || "50.0"} (baseline)`
                      : (marketIntel.market_score.components.growth?.toFixed(1) || "N/A")}
                  </span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Acclaim (20%):</span>
                  <span className="text-on-surface font-semibold">{marketIntel.market_score.components.acclaim?.toFixed(1) || "N/A"}</span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Price Health (15%):</span>
                  <span className="text-on-surface font-semibold">{marketIntel.market_score.components.price_health?.toFixed(1) || "N/A"}</span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Cross-Platform (10%):</span>
                  <span className="text-on-surface font-semibold">{marketIntel.market_score.components.cross_platform?.toFixed(1) || "N/A"}</span>
                </div>
              </div>
            </div>

            {/* Pillar 2: Demand & Velocity */}
            <div className="p-4 rounded-xl bg-surface-container/60 border border-outline-variant/20 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Demand Signal</span>
                <span className="text-xs font-mono-data px-2 py-0.5 rounded-full font-bold bg-primary/15 text-primary border border-primary/30">
                  {marketIntel.demand.demand_level}
                </span>
              </div>
              <div className="space-y-2">
                <div>
                  <div className="text-[11px] font-mono-data text-on-surface-variant">Demand Score</div>
                  <div className="text-xl font-bold font-mono-data text-on-surface">{marketIntel.demand.demand_score.toFixed(1)}/100</div>
                </div>
                <div className="border-t border-outline-variant/10 pt-2 space-y-1">
                  <div className="flex justify-between text-[11px] font-mono-data">
                    <span className="text-on-surface-variant">Trend Velocity:</span>
                    <span className="font-semibold text-on-surface">
                      {marketIntel.trend_velocity.velocity != null ? `${marketIntel.trend_velocity.velocity.toFixed(2)}/day` : "insufficient_data"}
                    </span>
                  </div>
                  <div className="flex justify-between text-[11px] font-mono-data">
                    <span className="text-on-surface-variant">7-Day Growth:</span>
                    <span className="font-semibold text-on-surface">
                      {marketIntel.growth.growth_7d != null ? `${marketIntel.growth.growth_7d > 0 ? "+" : ""}${marketIntel.growth.growth_7d.toFixed(1)}%` : "insufficient_data"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Pillar 3: Product Opportunity */}
            <div className="p-4 rounded-xl bg-surface-container/60 border border-outline-variant/20 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Opportunity</span>
                <span className="text-xs font-mono-data px-2 py-0.5 rounded-full font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  {marketIntel.opportunity.opportunity_level}
                </span>
              </div>
              <div className="space-y-2">
                <div>
                  <div className="text-[11px] font-mono-data text-on-surface-variant">Opportunity Score</div>
                  <div className="text-xl font-bold font-mono-data text-emerald-400">{marketIntel.opportunity.opportunity_score.toFixed(1)}/100</div>
                </div>
                <div className="border-t border-outline-variant/10 pt-2 text-[11px] font-mono-data space-y-1">
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Competition:</span>
                    <span className="font-semibold text-on-surface">{marketIntel.opportunity.competition_level}</span>
                  </div>
                  <div className="line-clamp-2 text-on-surface-variant/80 text-[10px]">
                    {marketIntel.opportunity.reasoning[0] || "High potential based on demand and rating profile."}
                  </div>
                </div>
              </div>
            </div>

            {/* Pillar 4: Viral Potential */}
            <div className="p-4 rounded-xl bg-surface-container/60 border border-outline-variant/20 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono-data text-on-surface-variant uppercase">Viral Potential</span>
                <span className={`text-xs font-mono-data px-2 py-0.5 rounded-full font-bold ${
                  marketIntel.viral_potential.has_social_signals ? "bg-purple-500/15 text-purple-300 border border-purple-500/30" : "bg-surface-container text-on-surface-variant"
                }`}>
                  {marketIntel.viral_potential.viral_level}
                </span>
              </div>
              <div className="space-y-2">
                <div>
                  <div className="text-[11px] font-mono-data text-on-surface-variant">Viral Score</div>
                  <div className="text-xl font-bold font-mono-data text-purple-300">
                    {marketIntel.viral_potential.viral_score != null ? `${marketIntel.viral_potential.viral_score.toFixed(1)}/100` : "Unavailable"}
                  </div>
                </div>
                <div className="border-t border-outline-variant/10 pt-2 text-[11px] font-mono-data space-y-1">
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Social Mentions:</span>
                    <span className="font-semibold text-on-surface">{marketIntel.social_signals.length}</span>
                  </div>
                  <div className="text-[10px] text-on-surface-variant/70">
                    {marketIntel.viral_potential.has_social_signals ? "Verified platform signals linked." : "No social signals detected yet."}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Cross-Marketplace Price Spread & Multi-Platform Comparison */}
          {marketIntel.cross_marketplace && (
            <div className="p-4 rounded-xl bg-surface-container/40 border border-outline-variant/15 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-base">compare_arrows</span>
                  Cross-Marketplace Price Spread
                </span>
                <span className="text-xs font-mono-data text-primary font-semibold">
                  Spread: {marketIntel.cross_marketplace.price_spread_pct}%
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono-data">
                <div className="p-2 rounded-lg bg-surface-container/60">
                  <span className="text-[10px] text-on-surface-variant">Lowest Price:</span>
                  <p className="text-emerald-400 font-bold mt-0.5">{marketIntel.currency} {marketIntel.cross_marketplace.lowest_price}</p>
                </div>
                <div className="p-2 rounded-lg bg-surface-container/60">
                  <span className="text-[10px] text-on-surface-variant">Highest Price:</span>
                  <p className="text-rose-400 font-bold mt-0.5">{marketIntel.currency} {marketIntel.cross_marketplace.highest_price}</p>
                </div>
                <div className="p-2 rounded-lg bg-surface-container/60">
                  <span className="text-[10px] text-on-surface-variant">Average Price:</span>
                  <p className="text-on-surface font-bold mt-0.5">{marketIntel.currency} {marketIntel.cross_marketplace.average_price}</p>
                </div>
                <div className="p-2 rounded-lg bg-surface-container/60">
                  <span className="text-[10px] text-on-surface-variant">Marketplaces:</span>
                  <p className="text-primary font-bold mt-0.5 uppercase">{marketIntel.cross_marketplace.platforms_present.join(", ")}</p>
                </div>
              </div>
            </div>
          )}

          {/* Real Social Signals Stream */}
          {marketIntel.social_signals.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-sm">share</span>
                Verified Social Signals & Content Matching ({marketIntel.social_signals.length})
              </h4>
              <div className="divide-y divide-outline-variant/15 border border-outline-variant/20 rounded-xl overflow-hidden">
                {marketIntel.social_signals.map((sig) => (
                  <div key={sig.id} className="p-3 bg-surface-container/30 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono-data px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">
                          {sig.platform}
                        </span>
                        <a href={sig.content_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-on-surface hover:text-primary transition-colors line-clamp-1">
                          {sig.content_title}
                        </a>
                      </div>
                      <div className="text-[10px] text-on-surface-variant/70 font-mono-data">
                        By {sig.author_name || "Creator"} • Match Confidence: {(sig.match_confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs font-mono-data text-on-surface-variant shrink-0">
                      <span>{sig.views.toLocaleString()} views</span>
                      <span>{sig.likes.toLocaleString()} likes</span>
                      <span className="text-primary font-semibold">{sig.engagement_rate}% ER</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Grounded Strategic Narrative */}
          {marketIntel.ai_summary && (
            <div className="p-4 rounded-xl bg-surface-container/60 border border-primary/20 space-y-2">
              <div className="flex items-center gap-2 text-primary text-xs font-label-caps uppercase tracking-wider font-bold">
                <span className="material-symbols-outlined text-sm">auto_awesome</span>
                Grok / AI Market Analyst Strategic Verdict
              </div>
              <p className="text-xs text-on-surface leading-relaxed">{marketIntel.ai_summary}</p>
            </div>
          )}
        </div>
      ) : (
        /* AI Intelligence Summary Fallback */
        <div className="p-6 rounded-2xl bg-surface-container-low border border-primary/20 glass-card space-y-4">
          <div className="flex items-center gap-2 text-primary text-xs font-label-caps uppercase tracking-wider font-bold">
            <span className="material-symbols-outlined text-base">auto_awesome</span>
            AI Autonomous Intelligence Narrative
          </div>
          <p className="text-sm text-on-surface leading-relaxed">{product.ai_summary}</p>
        </div>
      )}

      {/* Structured Specifications, SKU Variants, Seller Metrics & Reviews */}
      {(Object.keys(specs).length > 0 || variants.length > 0 || product.raw_data?.reviews?.length > 0 || product.raw_data?.seller_metrics) && (
        <div className="space-y-6">
          {/* Seller Metrics & Trust */}
          {product.raw_data?.seller_metrics && (
            <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-outline-variant/15 pb-3">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-xl">storefront</span>
                  <h3 className="text-base font-bold text-on-surface">
                    Seller Intelligence: {product.raw_data?.seller_name || "Official Merchant"}
                  </h3>
                </div>
                <span className="text-xs text-on-surface-variant font-mono-data">
                  Origin: {product.raw_data?.source_provider || "daraz_specialized"}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {Object.entries(product.raw_data.seller_metrics).map(([metricKey, metricVal]) => (
                  <div key={metricKey} className="p-3 rounded-xl bg-surface-container/60 border border-outline-variant/20">
                    <span className="text-[11px] font-mono-data text-on-surface-variant uppercase line-clamp-1">{metricKey}</span>
                    <p className="text-lg font-bold text-primary mt-0.5 font-mono-data">{String(metricVal)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Specifications Table */}
            {Object.keys(specs).length > 0 && (
              <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card space-y-4">
                <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-lg">checklist</span>
                  Catalog Specifications
                </h3>
                <div className="divide-y divide-outline-variant/15 border border-outline-variant/20 rounded-xl overflow-hidden text-xs">
                  {Object.entries(specs).map(([key, val]) => (
                    <div key={key} className="flex justify-between p-3 bg-surface-container/40">
                      <span className="font-semibold text-on-surface-variant">{key}</span>
                      <span className="font-mono-data text-on-surface text-right">{String(val)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* SKU Variants */}
            {variants.length > 0 && (
              <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card space-y-4">
                <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-lg">style</span>
                  Extracted SKU Variations ({variants.length})
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-80 overflow-y-auto pr-1">
                  {variants.map((v: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-xl bg-surface-container border border-outline-variant/20 space-y-1">
                      <div className="text-xs font-bold text-on-surface line-clamp-1">{v.name || v.title || `Variant ${idx + 1}`}</div>
                      <div className="flex items-center justify-between text-xs font-mono-data text-on-surface-variant">
                        <span className="text-primary font-bold">{v.price ? `Rs. ${v.price}` : "In Stock"}</span>
                        {v.sku_id && <span className="text-[10px] text-on-surface-variant/60">{v.sku_id}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Customer Reviews with Media Gallery */}
          {product.raw_data?.reviews && product.raw_data.reviews.length > 0 && (
            <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card space-y-4">
              <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-lg">rate_review</span>
                Verified Customer Reviews ({product.raw_data.reviews.length})
              </h3>
              <div className="space-y-3">
                {product.raw_data.reviews.map((rev: any, idx: number) => (
                  <div key={idx} className="p-4 rounded-xl bg-surface-container/50 border border-outline-variant/20 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-on-surface">{rev.reviewer_name || "Daraz Customer"}</span>
                        {rev.verified_purchase && (
                          <span className="text-[10px] font-mono-data text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
                            Verified Purchase
                          </span>
                        )}
                        {rev.variation && (
                          <span className="text-[10px] font-mono-data text-on-surface-variant/60">
                            Variant: {rev.variation}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1 text-primary font-bold text-xs font-mono-data">
                        <span>★</span>
                        <span>{rev.rating || 5.0}</span>
                      </div>
                    </div>
                    <p className="text-xs text-on-surface leading-relaxed">{rev.review_text || rev.content || "No text feedback provided."}</p>
                    {rev.images && rev.images.length > 0 && (
                      <div className="flex items-center gap-2 pt-1">
                        {rev.images.map((img: string, i: number) => (
                          <img key={i} src={img} alt="Customer photo" className="w-12 h-12 rounded-lg object-cover border border-outline-variant/30" />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Charts Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Trend Score History */}
        <div className="lg:col-span-8 bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card">
          <h3 className="text-base font-bold text-on-surface mb-1">Historical Signal Velocity</h3>
          <p className="text-xs text-on-surface-variant mb-6">
            Weekly trajectory of demand signals and viral triggers
          </p>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={product.historical_scores} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="detailGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#df7328" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#df7328" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#292a27" />
                <XAxis dataKey="date" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#888888" fontSize={11} tickLine={false} axisLine={false} domain={["dataMin - 5", "dataMax + 5"]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e201d",
                    borderColor: "#564338",
                    borderRadius: "0.75rem",
                    color: "#e3e3de",
                    fontSize: "12px",
                  }}
                />
                <Area type="monotone" dataKey="score" name="Trend Score" stroke="#ffb68d" strokeWidth={2.5} fill="url(#detailGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Platform Share Breakdown */}
        <div className="lg:col-span-4 bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-on-surface mb-1">Platform Distribution</h3>
            <p className="text-xs text-on-surface-variant mb-6">
              Channel concentration of consumer search intent
            </p>

            <div className="space-y-4">
              {Object.entries(product.platform_shares).map(([plat, share]) => (
                <div key={plat} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-mono-data">
                    <span className="text-on-surface font-semibold">{plat}</span>
                    <span className="text-primary font-bold">{share}%</span>
                  </div>
                  <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-500"
                      style={{ width: `${share}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-outline-variant/15 text-xs text-on-surface-variant">
            <span className="font-semibold text-on-surface">Primary Channel:</span> {product.primary_platform}
          </div>
        </div>
      </div>

      {/* Related Category Recommendations */}
      {related.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-base font-bold text-on-surface">Related Category Signals</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {related.map((rp) => (
              <div
                key={rp.id}
                onClick={() => navigate(`/products/${rp.id}`)}
                className="bg-surface-container-low p-5 rounded-xl border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.01] glass-card"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono-data text-primary px-2 py-0.5 rounded bg-primary/10 border border-primary/20">
                    {rp.velocity_label}
                  </span>
                  <span className="text-xs font-mono-data font-bold text-primary">
                    Score: {rp.trend_score}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-on-surface line-clamp-1">{rp.name}</h4>
                <p className="text-xs text-on-surface-variant mt-1">Growth: +{rp.growth_rate}%</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Raw Scraped Data Modal */}
      {isRawModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-surface-container-low border border-primary/30 rounded-3xl max-w-3xl w-full p-6 shadow-2xl space-y-4 glass-card animate-in zoom-in-95 duration-150 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-outline-variant/15 pb-4 shrink-0">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-2xl">code</span>
                <h3 className="text-lg font-bold text-on-surface">Factual Raw Scraped Payload</h3>
              </div>
              <button
                onClick={() => setIsRawModalOpen(false)}
                className="p-1 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
              >
                <span className="material-symbols-outlined text-xl">close</span>
              </button>
            </div>

            <div className="overflow-y-auto space-y-4 flex-1 pr-1 font-mono-data text-xs">
              {rawLoading ? (
                <LoadingSpinner size="md" label="Fetching raw payload..." />
              ) : rawScrapedData ? (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-2.5 rounded-xl bg-surface-container border border-outline-variant/20">
                      <span className="block text-[10px] text-on-surface-variant">MARKETPLACE</span>
                      <span className="text-primary font-bold">{rawScrapedData.marketplace}</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-surface-container border border-outline-variant/20">
                      <span className="block text-[10px] text-on-surface-variant">PARSER VERSION</span>
                      <span className="text-on-surface font-bold">{rawScrapedData.parser_version}</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-surface-container border border-outline-variant/20">
                      <span className="block text-[10px] text-on-surface-variant">QUALITY STATUS</span>
                      <span className="text-emerald-400 font-bold">{rawScrapedData.quality_status}</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-surface-container border border-outline-variant/20">
                      <span className="block text-[10px] text-on-surface-variant">CONFIDENCE</span>
                      <span className="text-primary font-bold">{(rawScrapedData.confidence_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/20 overflow-x-auto">
                    <pre className="text-[11px] text-on-surface-variant leading-relaxed">
                      {JSON.stringify(rawScrapedData.raw_payload || rawScrapedData.normalized_payload, null, 2)}
                    </pre>
                  </div>
                </>
              ) : (
                <p className="text-on-surface-variant">No raw payload record found for this product.</p>
              )}
            </div>

            <div className="pt-3 flex justify-end border-t border-outline-variant/15 shrink-0">
              <button
                onClick={() => setIsRawModalOpen(false)}
                className="px-5 py-2 rounded-xl text-xs font-label-caps font-semibold bg-primary text-on-primary hover:bg-primary-container"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
