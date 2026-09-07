import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { productService, watchlistService } from "../../services/domainServices";
import type { Product } from "../../types";
import { LoadingSpinner, EmptyState, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";
import { DarazProductModal } from "../../components/products/DarazProductModal";

export const ProductListPage: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [platform, setPlatform] = useState("all");
  const [sortBy, setSortBy] = useState("trend_score");
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [selectedDarazId, setSelectedDarazId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);


  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await productService.list({
        category,
        platform,
        search: search.trim() || undefined,
        sort_by: sortBy,
      });
      if (res.success && Array.isArray(res.data)) {
        setProducts(res.data);
      } else if (!res.success) {
        setError(res.message || "Failed to load product catalog");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load product catalog");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchProducts();
    }, 300);
    return () => clearTimeout(timer);
  }, [search, category, platform, sortBy]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProducts();
  };

  const handleToggleWatchlist = async (e: React.MouseEvent, p: Product) => {
    e.stopPropagation();
    try {
      if (p.is_watchlisted) {
        await watchlistService.remove(p.id);
        setProducts((prev) =>
          prev.map((item) => (item.id === p.id ? { ...item, is_watchlisted: false } : item))
        );
        showToast(`${p.name} removed from watchlist`, "info");
      } else {
        await watchlistService.add(p.id);
        setProducts((prev) =>
          prev.map((item) => (item.id === p.id ? { ...item, is_watchlisted: true } : item))
        );
        showToast(`${p.name} added to watchlist`, "success");
      }
    } catch (err: any) {
      showToast(err.message || "Failed to update watchlist", "error");
    }
  };

  const toggleCompare = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSelectedForCompare((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : prev.length < 4 ? [...prev, id] : prev
    );
  };

  const handleLaunchComparison = () => {
    if (selectedForCompare.length >= 2) {
      navigate(`/product-comparison?ids=${selectedForCompare.join(",")}`);
    } else {
      showToast("Please select at least 2 products to compare", "warning");
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            MARKET INTELLIGENCE CATALOG
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Trending Products
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Real-time multi-channel breakout signals scored by velocity algorithms.
          </p>
        </div>

        {selectedForCompare.length > 0 && (
          <div className="flex items-center gap-3 bg-surface-container px-4 py-2 rounded-xl border border-primary/30">
            <span className="text-xs font-mono-data text-primary">
              {selectedForCompare.length} selected for comparison
            </span>
            <button
              onClick={handleLaunchComparison}
              className="bg-primary text-on-primary font-label-caps text-xs px-3 py-1.5 rounded-lg hover:bg-primary-container font-semibold"
            >
              Compare Now
            </button>
            <button
              onClick={() => setSelectedForCompare([])}
              className="text-xs text-on-surface-variant hover:text-on-surface"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/20 flex flex-wrap items-center justify-between gap-4 glass-panel">
        <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[240px] relative">
          <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">
            search
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by product name, category, or hashtag..."
            className="w-full bg-surface-container border border-outline-variant/30 rounded-xl pl-10 pr-4 py-2.5 text-xs text-on-surface placeholder-on-surface-variant/50 focus:outline-none focus:border-primary transition-colors"
          />
        </form>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
          >
            <option value="all">All Categories</option>
            <option value="Beauty & Personal Care">Beauty & Personal Care</option>
            <option value="Sports & Outdoor">Sports & Outdoor</option>
            <option value="Consumer Electronics">Consumer Electronics</option>
            <option value="Home & Kitchen">Home & Kitchen</option>
            <option value="Fashion & Apparel">Fashion & Apparel</option>
          </select>

          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
          >
            <option value="all">All Platforms</option>
            <option value="TikTok">TikTok</option>
            <option value="Daraz">Daraz</option>
            <option value="Instagram">Instagram</option>
            <option value="YouTube">YouTube</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
          >
            <option value="trend_score">Sort: Trend Score</option>
            <option value="growth">Sort: Velocity Growth</option>
            <option value="volume">Sort: Signal Volume</option>
            <option value="sentiment">Sort: Sentiment Score</option>
          </select>
        </div>
      </div>

      {/* Product List */}
      {loading ? (
        <LoadingSpinner size="lg" label="Loading product signals..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchProducts} />
      ) : products.length === 0 ? (
        <EmptyState
          title="No Products Found"
          description="No products matched your active filters or keyword search. Try broadening your criteria."
          actionText="Reset Filters"
          onAction={() => {
            setCategory("all");
            setPlatform("all");
            setSearch("");
            setSortBy("trend_score");
          }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map((p) => {
            const isComparing = selectedForCompare.includes(p.id);
            const isDaraz = p.id.startsWith("daraz_") || p.primary_platform === "Daraz";
            return (
              <div
                key={p.id}
                onClick={() => {
                  if (isDaraz) {
                    setSelectedDarazId(p.id);
                  } else {
                    navigate(`/products/${p.id}`);
                  }
                }}
                className={`bg-surface-container-low rounded-2xl border ${
                  isDaraz ? "border-[#f85606]/30 hover:border-[#f85606]" : "border-outline-variant/20 hover:border-primary/40"
                } cursor-pointer transition-all hover:scale-[1.01] glass-card overflow-hidden flex flex-col justify-between group`}
              >
                {/* Product Image Banner */}
                <div className="h-44 w-full bg-surface-container relative overflow-hidden">
                  {p.image_url ? (
                    <img
                      src={p.image_url}
                      alt={p.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-primary/40">
                      <span className="material-symbols-outlined text-4xl">inventory_2</span>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-surface-container-low via-transparent to-transparent" />

                  {/* Top Badges on Image */}
                  <div className="absolute top-3 left-3 flex items-center gap-2">
                    <span className="text-[10px] font-mono-data font-bold text-primary px-2.5 py-1 rounded-full bg-surface/90 border border-primary/30 backdrop-blur-md">
                      {p.velocity_label}
                    </span>
                    <span className={`text-[10px] font-mono-data px-2.5 py-1 rounded-full bg-surface/80 border backdrop-blur-md font-semibold ${
                      isDaraz ? "text-[#f85606] border-[#f85606]/40" : "text-on-surface border-outline-variant/30"
                    }`}>
                      {isDaraz ? "Daraz Pakistan" : p.primary_platform}
                    </span>
                  </div>

                  <div className="absolute top-3 right-3 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={(e) => toggleCompare(e, p.id)}
                      className={`p-2 rounded-full backdrop-blur-md transition-colors ${
                        isComparing
                          ? "bg-primary text-on-primary font-bold shadow-md"
                          : "bg-surface/80 text-on-surface-variant hover:text-on-surface"
                      }`}
                      title="Compare product"
                    >
                      <span className="material-symbols-outlined text-sm">compare_arrows</span>
                    </button>
                    <button
                      type="button"
                      onClick={(e) => handleToggleWatchlist(e, p)}
                      className={`p-2 rounded-full backdrop-blur-md transition-colors ${
                        p.is_watchlisted
                          ? "bg-primary text-on-primary"
                          : "bg-surface/80 text-on-surface-variant hover:text-primary"
                      }`}
                      title={p.is_watchlisted ? "In Watchlist" : "Add to Watchlist"}
                    >
                      <span className="material-symbols-outlined text-sm">
                        {p.is_watchlisted ? "bookmark_added" : "bookmark_add"}
                      </span>
                    </button>
                  </div>
                </div>

                {/* Content Details */}
                <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                        {p.category}
                      </span>
                      {isDaraz && (
                        <span className="text-[10px] font-mono-data text-[#f85606] font-bold">
                          Live Data
                        </span>
                      )}
                    </div>
                    <h3 className="text-base font-bold text-on-surface mt-1 group-hover:text-primary transition-colors leading-snug line-clamp-1">
                      {p.name}
                    </h3>
                    <p className="text-xs text-on-surface-variant line-clamp-2 mt-2 leading-relaxed">
                      {p.ai_summary}
                    </p>
                  </div>

                  {/* Metrics Bar */}
                  <div className="pt-3 border-t border-outline-variant/15 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-on-surface-variant font-label-caps uppercase">
                        {isDaraz ? "Market Rating" : "Trend Score"}
                      </span>
                      <p className={`text-xl font-mono-data font-bold ${isDaraz ? "text-[#f85606]" : "text-primary"}`}>
                        {isDaraz && p.raw_data?.daraz_product?.rating ? `★ ${p.raw_data.daraz_product.rating.toFixed(1)}` : p.trend_score}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] text-on-surface-variant font-label-caps uppercase">
                        {isDaraz ? "Discount" : "YoY Velocity"}
                      </span>
                      <p className="text-xs font-mono-data font-bold text-on-surface">
                        {isDaraz ? (p.raw_data?.discount_label || `${p.growth_rate}% Off`) : `+${p.growth_rate}%`}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] text-on-surface-variant font-label-caps uppercase">
                        {isDaraz ? "Price (PKR)" : "Est. Range"}
                      </span>
                      <p className="text-xs font-mono-data text-on-surface-variant font-semibold">
                        {p.price_range}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Daraz Product Detail Modal */}
      {selectedDarazId && (
        <DarazProductModal
          itemId={selectedDarazId}
          isOpen={!!selectedDarazId}
          onClose={() => setSelectedDarazId(null)}
        />
      )}
    </div>
  );
};

