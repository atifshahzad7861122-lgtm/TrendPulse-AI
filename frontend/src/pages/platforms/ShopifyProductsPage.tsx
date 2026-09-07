import React, { useState, useEffect } from "react";
import { shopifyService } from "../../services/domainServices";
import type { ShopifyProduct, ShopifyStatusResponse } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const ShopifyProductsPage: React.FC = () => {
  const [products, setProducts] = useState<ShopifyProduct[]>([]);
  const [statusData, setStatusData] = useState<ShopifyStatusResponse | null>(null);
  const [storeDomain, setStoreDomain] = useState<string>("gymshark.com");
  const [inputDomain, setInputDomain] = useState<string>("gymshark.com");
  const [search, setSearch] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("synced");
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState<boolean>(false);
  const [sourceProvider, setSourceProvider] = useState<string>("database_cache");
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [dataAgeSeconds, setDataAgeSeconds] = useState<number | null>(null);

  const { showToast } = useToast();

  const fetchProductsAndStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const [prodsRes, statusRes] = await Promise.all([
        shopifyService.listProducts({
          store_domain: storeDomain || undefined,
          search: search || undefined,
          sort_by: sortBy,
          limit: 100
        }),
        shopifyService.getStatus().catch(() => null)
      ]);

      if (prodsRes.success && prodsRes.data) {
        setProducts(prodsRes.data.items);
        setIsLive(prodsRes.data.is_live);
        setSourceProvider(prodsRes.data.source_provider);
        setLastSyncedAt(prodsRes.data.last_synced_at || null);
        setDataAgeSeconds(prodsRes.data.data_age_seconds || null);
      }
      if (statusRes && statusRes.success && statusRes.data) {
        setStatusData(statusRes.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load Shopify products");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProductsAndStatus();
  }, [storeDomain, sortBy]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProductsAndStatus();
  };

  const handleSyncStore = async (domainToSync: string) => {
    if (!domainToSync || !domainToSync.trim()) {
      showToast("Please enter a valid Shopify store domain", "error");
      return;
    }
    setSyncing(true);
    try {
      const res = await shopifyService.sync({
        store_domain: domainToSync.trim(),
        limit: 50,
        force_live: true
      });
      if (res.success && res.data) {
        showToast(
          `[${res.data.source_provider}] Synced ${res.data.products_fetched} products (${res.data.products_inserted} new, ${res.data.products_updated} updated).`,
          "success"
        );
        setStoreDomain(domainToSync.trim());
        setProducts(res.data.products);
        setIsLive(res.data.is_live);
        setSourceProvider(res.data.source_provider);
        setLastSyncedAt(res.data.last_synced_at || null);
        // Refresh status
        const sRes = await shopifyService.getStatus().catch(() => null);
        if (sRes && sRes.success && sRes.data) setStatusData(sRes.data);
      } else {
        showToast(res.message || "Sync completed with fallback", "info");
      }
    } catch (err: any) {
      showToast(err.message || "Shopify sync failed", "error");
    } finally {
      setSyncing(false);
    }
  };

  const formatDataAge = (seconds?: number | null, lastSync?: string | null) => {
    if (seconds === null || seconds === undefined) {
      if (!lastSync) return "Not synced yet";
      return new Date(lastSync).toLocaleTimeString();
    }
    if (seconds < 60) return "Just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
  };

  return (
    <div className="space-y-8 animate-fade-in p-2 md:p-6">
      {/* Header & Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-outline-variant/20 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <span className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
              <span className="material-symbols-outlined text-2xl">shopping_cart</span>
            </span>
            <div>
              <h1 className="text-2xl font-headline font-bold text-on-surface flex items-center gap-3">
                Shopify Intelligence
                <span className="text-xs px-2.5 py-0.5 rounded-full font-mono-data border bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                  MULTI-PROVIDER FAILOVER
                </span>
              </h1>
              <p className="text-xs font-mono-data text-on-surface-variant mt-0.5">
                5-Tier Ordered Failover Pool: Scout → ShopScraper → Apps Spy → Xtracto → Bornoo
              </p>
            </div>
          </div>
        </div>

        {/* Sync Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSyncStore(inputDomain);
            }}
            className="flex items-center gap-2 bg-surface-container-high border border-outline-variant/30 rounded-xl px-3 py-1.5 focus-within:border-primary/50 transition-all"
          >
            <span className="material-symbols-outlined text-sm text-on-surface-variant">storefront</span>
            <input
              type="text"
              value={inputDomain}
              onChange={(e) => setInputDomain(e.target.value)}
              placeholder="e.g. gymshark.com"
              className="bg-transparent text-xs text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none w-36 md:w-48 font-mono-data"
            />
            <button
              type="submit"
              disabled={syncing}
              className="px-3 py-1 bg-primary text-on-primary text-xs font-semibold rounded-lg hover:bg-primary-container transition-all flex items-center gap-1.5"
            >
              {syncing ? (
                <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <span className="material-symbols-outlined text-xs">sync</span>
              )}
              {syncing ? "Ingesting..." : "Sync Store"}
            </button>
          </form>
        </div>
      </div>

      {/* Freshness & Failover Health Strip */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Status Card */}
        <div className="bg-surface-container/60 border border-outline-variant/30 rounded-2xl p-4 flex flex-col justify-between">
          <div className="text-[11px] font-label-caps text-on-surface-variant uppercase font-semibold">
            Ingestion Status
          </div>
          <div className="flex items-center gap-2 mt-2">
            {isLive ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono-data font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                LIVE DATA
              </span>
            ) : products.length > 0 ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono-data font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                CACHED DATA
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono-data font-bold bg-surface-container text-on-surface-variant border border-outline-variant/30">
                <span className="w-2 h-2 rounded-full bg-on-surface-variant/40" />
                UNAVAILABLE
              </span>
            )}
          </div>
          <div className="text-[11px] font-mono-data text-on-surface-variant mt-2">
            Source: <span className="text-on-surface font-semibold">{sourceProvider}</span>
          </div>
        </div>

        {/* Freshness Card */}
        <div className="bg-surface-container/60 border border-outline-variant/30 rounded-2xl p-4 flex flex-col justify-between">
          <div className="text-[11px] font-label-caps text-on-surface-variant uppercase font-semibold">
            Data Freshness
          </div>
          <div className="text-xl font-headline font-bold text-on-surface mt-2">
            {formatDataAge(dataAgeSeconds, lastSyncedAt)}
          </div>
          <div className="text-[11px] font-mono-data text-on-surface-variant mt-2">
            Store: <span className="text-on-surface font-semibold">{storeDomain}</span>
          </div>
        </div>

        {/* Total Products */}
        <div className="bg-surface-container/60 border border-outline-variant/30 rounded-2xl p-4 flex flex-col justify-between">
          <div className="text-[11px] font-label-caps text-on-surface-variant uppercase font-semibold">
            Catalog Size
          </div>
          <div className="text-xl font-headline font-bold text-primary mt-2">
            {products.length} Products
          </div>
          <div className="text-[11px] font-mono-data text-on-surface-variant mt-2">
            Snapshots tracked in Supabase
          </div>
        </div>

        {/* Preferred Provider */}
        <div className="bg-surface-container/60 border border-outline-variant/30 rounded-2xl p-4 flex flex-col justify-between">
          <div className="text-[11px] font-label-caps text-on-surface-variant uppercase font-semibold">
            Preferred Provider
          </div>
          <div className="text-sm font-headline font-bold text-emerald-400 mt-2 flex items-center gap-1.5">
            <span className="material-symbols-outlined text-base">verified</span>
            {statusData?.preferred_provider || "Shopify Scout (P1)"}
          </div>
          <div className="text-[11px] font-mono-data text-on-surface-variant mt-2">
            {statusData?.active_providers_count || 5}/5 Providers Healthy
          </div>
        </div>
      </div>

      {/* Provider Failover Hierarchy Strip */}
      {statusData && statusData.providers && (
        <div className="bg-surface-container-low/80 border border-outline-variant/20 rounded-2xl p-4">
          <div className="text-xs font-label-caps text-on-surface-variant uppercase tracking-wider mb-3">
            Failover Pool Ranking & Health
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {statusData.providers.map((p) => {
              const isHealthy = p.status === "healthy";
              const isRateLimited = p.status === "rate_limited";
              return (
                <div
                  key={p.provider_name}
                  className={`p-3 rounded-xl border flex flex-col justify-between ${
                    isHealthy
                      ? "bg-surface-container border-outline-variant/30"
                      : isRateLimited
                      ? "bg-amber-500/5 border-amber-500/30"
                      : "bg-error/5 border-error/30"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono-data font-bold px-1.5 py-0.5 rounded bg-surface-container-high text-on-surface-variant">
                      P{p.priority}
                    </span>
                    <span
                      className={`text-[9px] font-label-caps font-bold px-1.5 py-0.5 rounded ${
                        isHealthy
                          ? "bg-emerald-500/10 text-emerald-400"
                          : isRateLimited
                          ? "bg-amber-500/10 text-amber-400"
                          : "bg-error/10 text-error"
                      }`}
                    >
                      {p.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-on-surface mt-2 truncate">
                    {p.display_name}
                  </div>
                  <div className="text-[10px] font-mono-data text-on-surface-variant mt-1">
                    Reqs: {p.total_requests} | Succ: {p.successful_requests}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Search & Sort Filters */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-80">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-on-surface-variant">
            search
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search titles, vendors, tags..."
            className="w-full pl-9 pr-4 py-2 bg-surface-container border border-outline-variant/30 rounded-xl text-xs text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-primary/50"
          />
        </form>

        <div className="flex items-center gap-3 self-end">
          <label className="text-xs font-mono-data text-on-surface-variant">Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-surface-container border border-outline-variant/30 text-xs text-on-surface rounded-xl px-3 py-2 focus:outline-none focus:border-primary/50"
          >
            <option value="synced">Recently Synced</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="rating">Top Rated</option>
          </select>
        </div>
      </div>

      {/* Product Grid */}
      {loading ? (
        <LoadingSpinner label="Querying Shopify multi-provider catalogue..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchProductsAndStatus} />
      ) : products.length === 0 ? (
        <div className="text-center py-16 bg-surface-container-low/40 rounded-3xl border border-outline-variant/20">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant/40 mb-3">
            store
          </span>
          <h3 className="text-base font-headline font-semibold text-on-surface">
            No Shopify Products Found
          </h3>
          <p className="text-xs text-on-surface-variant max-w-md mx-auto mt-1">
            Enter a Shopify storefront domain (e.g. gymshark.com or allbirds.com) above and click "Sync Store" to ingest live products through the failover pool.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {products.map((p) => (
            <div
              key={p.id}
              className="bg-surface-container-low border border-outline-variant/20 rounded-2xl overflow-hidden hover:border-primary/40 transition-all flex flex-col justify-between group shadow-sm hover:shadow-md"
            >
              {/* Product Photo */}
              <div className="relative aspect-square bg-surface-container-high overflow-hidden">
                {p.image_url ? (
                  <img
                    src={p.image_url}
                    alt={p.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-on-surface-variant/30">
                    <span className="material-symbols-outlined text-4xl">image</span>
                  </div>
                )}
                {/* Discount Badge */}
                {p.discount_label && (
                  <span className="absolute top-2 left-2 px-2 py-0.5 bg-error text-on-error text-[10px] font-bold rounded-md uppercase tracking-wider">
                    {p.discount_label}
                  </span>
                )}
                {/* Provider Tag */}
                <span className="absolute bottom-2 right-2 px-2 py-0.5 bg-surface-container-highest/90 backdrop-blur text-on-surface text-[9px] font-mono-data rounded border border-outline-variant/30">
                  {p.source_provider}
                </span>
              </div>

              {/* Product Details */}
              <div className="p-4 flex-1 flex flex-col justify-between">
                <div>
                  <div className="text-[10px] font-label-caps text-on-surface-variant uppercase truncate font-semibold">
                    {p.vendor || p.store_domain}
                  </div>
                  <h4 className="text-sm font-headline font-semibold text-on-surface line-clamp-2 mt-1 group-hover:text-primary transition-colors">
                    {p.title}
                  </h4>
                </div>

                <div className="mt-4 pt-3 border-t border-outline-variant/15 flex items-center justify-between">
                  <div>
                    <div className="text-base font-headline font-bold text-on-surface">
                      {p.price_formatted}
                    </div>
                    {p.compare_at_price_formatted && (
                      <div className="text-xs font-mono-data text-on-surface-variant line-through">
                        {p.compare_at_price_formatted}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-1 text-xs text-amber-400 font-bold">
                    <span className="material-symbols-outlined text-sm">star</span>
                    <span>{p.rating.toFixed(1)}</span>
                    <span className="text-on-surface-variant text-[10px]">({p.review_count})</span>
                  </div>
                </div>

                {/* External Listing Link */}
                <a
                  href={p.product_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 w-full py-2 bg-surface-container border border-outline-variant/30 hover:border-primary/40 text-on-surface hover:text-primary rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <span>View on {p.store_domain}</span>
                  <span className="material-symbols-outlined text-xs">open_in_new</span>
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
