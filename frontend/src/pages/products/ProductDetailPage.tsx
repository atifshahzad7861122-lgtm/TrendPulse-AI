import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { productService, watchlistService } from "../../services/domainServices";
import type { Product } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const ProductDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [related, setRelated] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        // fetch related products in same category
        const relRes = await productService.list({ category: res.data.category });
        if (relRes.success && relRes.data) {
          setRelated(relRes.data.filter((p) => p.id !== id).slice(0, 3));
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
          <Link
            to={`/product-comparison?ids=${product.id}`}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-container border border-outline-variant/20 text-xs font-label-caps text-on-surface hover:text-primary transition-colors"
          >
            <span className="material-symbols-outlined text-sm">compare_arrows</span>
            Compare
          </Link>
          <button
            onClick={handleToggleWatchlist}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-label-caps font-semibold transition-all ${
              product.is_watchlisted
                ? "bg-primary text-on-primary shadow-[0_0_15px_rgba(255,182,141,0.3)]"
                : "bg-surface-container border border-primary/30 text-primary hover:bg-primary hover:text-on-primary"
            }`}
          >
            <span className="material-symbols-outlined text-sm">
              {product.is_watchlisted ? "bookmark_added" : "bookmark_add"}
            </span>
            {product.is_watchlisted ? "In Watchlist" : "Add to Watchlist"}
          </button>
        </div>
      </div>

      {/* Main Metrics Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-label-caps text-on-surface-variant uppercase">
            Aggregate Score
          </span>
          <div className="text-3xl font-mono-data font-bold text-primary mt-2">
            {product.trend_score}
          </div>
          <p className="text-xs text-on-surface-variant mt-1">Velocity Index: 98th Percentile</p>
        </div>

        <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-label-caps text-on-surface-variant uppercase">
            YoY Growth Rate
          </span>
          <div className="text-3xl font-mono-data font-bold text-on-surface mt-2">
            +{product.growth_rate}%
          </div>
          <p className="text-xs text-on-surface-variant mt-1">Sustained positive volume</p>
        </div>

        <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-label-caps text-on-surface-variant uppercase">
            Monthly Signal Volume
          </span>
          <div className="text-3xl font-mono-data font-bold text-on-surface mt-2">
            {(product.volume / 1000).toFixed(1)}K
          </div>
          <p className="text-xs text-on-surface-variant mt-1">Total active social mentions</p>
        </div>

        <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card">
          <span className="text-[11px] font-label-caps text-on-surface-variant uppercase">
            Net Sentiment
          </span>
          <div className="text-3xl font-mono-data font-bold text-primary mt-2">
            {Math.round(product.sentiment_score * 100)}%
          </div>
          <p className="text-xs text-on-surface-variant mt-1">Highly positive conversion intent</p>
        </div>
      </div>

      {/* AI Synthesis Narrative Block */}
      <div className="bg-surface-container-low p-8 rounded-3xl border border-primary/25 relative overflow-hidden glass-panel">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-lg">psychology</span>
          </div>
          <div>
            <span className="text-xs font-label-caps text-primary uppercase tracking-wider font-semibold">
              AI Market Intelligence Synthesis
            </span>
            <p className="text-[11px] text-on-surface-variant">
              Contextual analysis evaluated across cross-border channels
            </p>
          </div>
        </div>

        <p className="font-editorial-italic text-lg md:text-xl text-on-surface leading-relaxed italic max-w-4xl">
          "{product.ai_summary}"
        </p>

        {/* Explainability Contributors & Prediction Confidence */}
        {product.raw_data?.scoring_detail?.top_contributors && (
          <div className="mt-4 pt-4 border-t border-outline-variant/15 flex flex-wrap items-center gap-4 text-xs">
            <span className="text-on-surface font-semibold flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm text-primary">verified</span>
              Key Drivers:
            </span>
            <div className="flex flex-wrap gap-2">
              {product.raw_data.scoring_detail.top_contributors.map((contrib: string, i: number) => (
                <span key={i} className="px-2.5 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-primary font-medium">
                  {contrib}
                </span>
              ))}
            </div>
            {product.raw_data?.prediction?.confidence > 0 && (
              <span className="ml-auto text-[11px] font-mono-data text-on-surface-variant">
                Prediction Confidence: <strong className="text-primary font-bold">{product.raw_data.prediction.confidence}%</strong>
              </span>
            )}
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-2">
          {product.tags.map((tag, idx) => (
            <span
              key={idx}
              className="text-xs font-mono-data px-3 py-1 rounded-lg bg-surface-container border border-outline-variant/20 text-on-surface"
            >
              #{tag}
            </span>
          ))}
        </div>
      </div>

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
    </div>
  );
};
