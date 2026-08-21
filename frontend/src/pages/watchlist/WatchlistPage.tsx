import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { watchlistService } from "../../services/domainServices";
import type { Product } from "../../types";
import { LoadingSpinner, EmptyState, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const WatchlistPage: React.FC = () => {
  const [watchlist, setWatchlist] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchWatchlist = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await watchlistService.list();
      if (res.success && res.data) {
        setWatchlist(res.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const handleRemove = async (e: React.MouseEvent, id: string, name: string) => {
    e.stopPropagation();
    try {
      await watchlistService.remove(id);
      setWatchlist((prev) => prev.filter((p) => p.id !== id));
      showToast(`${name} removed from watchlist`, "info");
    } catch (err: any) {
      showToast(err.message || "Failed to remove item", "error");
    }
  };

  const handleExport = () => {
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(watchlist, null, 2)
    )}`;
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonString);
    downloadAnchor.setAttribute("download", "trendpulse_watchlist.json");
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast("Watchlist exported to JSON", "success");
  };

  const filtered = watchlist.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            SAVED ARBITRAGE TARGETS
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Product Watchlist
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Active tracking for high-conviction breakout products with automated anomaly alerts.
          </p>
        </div>

        {watchlist.length > 0 && (
          <div className="flex items-center gap-3">
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-surface-container border border-outline-variant/30 text-xs font-label-caps text-on-surface hover:text-primary hover:border-primary/40 transition-all"
            >
              <span className="material-symbols-outlined text-sm">download</span>
              Export Watchlist
            </button>
            <Link
              to="/products"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-on-primary text-xs font-label-caps font-semibold hover:bg-primary-container transition-all"
            >
              <span className="material-symbols-outlined text-sm">add</span>
              Add Products
            </Link>
          </div>
        )}
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Loading your saved products..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchWatchlist} />
      ) : watchlist.length === 0 ? (
        <EmptyState
          title="Your Watchlist is Empty"
          description="You have not saved any breakout products yet. Browse the catalog to start monitoring items."
          icon="bookmark_border"
          actionText="Browse Product Catalog"
          onAction={() => navigate("/products")}
        />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono-data text-on-surface-variant">
              {filtered.length} products monitored
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search watchlist..."
              className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-primary"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filtered.map((p) => (
              <div
                key={p.id}
                onClick={() => navigate(`/products/${p.id}`)}
                className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.01] glass-card flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-mono-data font-bold text-primary px-2.5 py-0.5 rounded bg-primary/10 border border-primary/20">
                      {p.velocity_label}
                    </span>
                    <button
                      onClick={(e) => handleRemove(e, p.id, p.name)}
                      className="text-on-surface-variant hover:text-error transition-colors p-1"
                      title="Remove from watchlist"
                    >
                      <span className="material-symbols-outlined text-base">delete</span>
                    </button>
                  </div>

                  <h3 className="text-base font-bold text-on-surface group-hover:text-primary transition-colors leading-snug">
                    {p.name}
                  </h3>
                  <p className="text-xs text-on-surface-variant mt-1">{p.category}</p>
                </div>

                <div className="mt-6 pt-4 border-t border-outline-variant/15 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                      Trend Score
                    </span>
                    <p className="text-xl font-mono-data font-bold text-primary">
                      {p.trend_score}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                      YoY Growth
                    </span>
                    <p className="text-xs font-mono-data font-bold text-on-surface">
                      +{p.growth_rate}%
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
