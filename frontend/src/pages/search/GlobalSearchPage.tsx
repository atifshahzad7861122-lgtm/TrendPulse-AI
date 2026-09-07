import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { searchService, marketplaceSearchService } from "../../services/domainServices";
import type {
  SearchResultItem,
  MarketplaceType,
  MarketplaceSearchStatus,
  MarketplaceSearchResult,
  MarketplaceSearchCandidate
} from "../../types";
import { LoadingSpinner, EmptyState } from "../../components/common/StateComponents";
import { DarazProductModal } from "../../components/products/DarazProductModal";

type SearchMode = "marketplace" | "internal";

export const GlobalSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const initialMode = (searchParams.get("mode") as SearchMode) || "marketplace";
  const initialMarketplace = (searchParams.get("marketplace") as MarketplaceType) || "daraz";

  const [mode, setMode] = useState<SearchMode>(initialMode);
  const [query, setQuery] = useState(initialQuery);
  const [selectedMarketplace, setSelectedMarketplace] = useState<MarketplaceType>(initialMarketplace);
  const candidateTarget = 250;


  // Marketplace Pipeline State
  const [mktLoading, setMktLoading] = useState(false);
  const [mktResult, setMktResult] = useState<MarketplaceSearchResult | null>(null);
  const [mktError, setMktError] = useState<string | null>(null);

  // Auto-restore / execute on mount/refresh if query params are present
  useEffect(() => {
    if (initialMode === "marketplace" && initialQuery.trim()) {
      setMktLoading(true);
      setMktError(null);
      marketplaceSearchService.search({
        marketplace: initialMarketplace,
        keyword: initialQuery.trim(),
        desired_results: 30,
        candidate_target: 250
      }, true).then(res => {
        if (res.success && res.data) {
          setMktResult(res.data);
        } else {
          setMktError(res.message || "Failed to load marketplace candidates");
          if (res.data) setMktResult(res.data);
        }
      }).catch((err: any) => {
        setMktError(err.message || "Connection failure");
      }).finally(() => {
        setMktLoading(false);
      });
    }
  }, []);

  // Internal Cross-Entity State
  const [internalResults, setInternalResults] = useState<SearchResultItem[]>([]);
  const [internalLoading, setInternalLoading] = useState(false);
  const [selectedDarazId, setSelectedDarazId] = useState<string | null>(null);

  const navigate = useNavigate();

  // Handle Internal Cross-Entity search when in internal mode
  useEffect(() => {
    if (mode !== "internal" || !query.trim()) {
      setInternalResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setInternalLoading(true);
      try {
        const res = await searchService.search(query.trim());
        if (res.success && res.data) {
          setInternalResults(res.data.results);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setInternalLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, mode]);

  const handleMarketplaceSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanKw = query.trim();
    if (!cleanKw) return;

    setSearchParams({ q: cleanKw, mode: "marketplace", marketplace: selectedMarketplace });
    setMktLoading(true);
    setMktError(null);

    try {
      const res = await marketplaceSearchService.search({
        marketplace: selectedMarketplace,
        keyword: cleanKw,
        desired_results: 30,
        candidate_target: candidateTarget
      }, true);

      if (res.success && res.data) {
        setMktResult(res.data);
      } else {
        setMktError(res.message || "Failed to acquire candidates from marketplace");
        if (res.data) setMktResult(res.data);
      }
    } catch (err: any) {
      setMktError(err.message || "Connection failure during candidate acquisition");
    } finally {
      setMktLoading(false);
    }
  };

  const handleInternalSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams({ q: query, mode: "internal" });
  };

  const formatPrice = (p: MarketplaceSearchCandidate) => {
    if (p.price === null || p.price === undefined) return "Price Unavailable";
    const curr = p.currency || "USD";
    if (curr === "PKR") return `Rs. ${p.price.toLocaleString()}`;
    return `${curr} ${p.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getStatusBadge = (status: MarketplaceSearchStatus) => {
    switch (status) {
      case "completed":
        return {
          label: "COMPLETED",
          classes: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
        };
      case "insufficient_data":
        return {
          label: "INSUFFICIENT DATA",
          classes: "bg-amber-500/10 text-amber-400 border-amber-500/30"
        };
      case "failed":
        return {
          label: "FAILED",
          classes: "bg-error/10 text-error border-error/30"
        };
      case "running":
        return {
          label: "ACQUIRING CANDIDATES",
          classes: "bg-sky-500/10 text-sky-400 border-sky-500/30 animate-pulse"
        };
      case "processing":
        return {
          label: "VERIFYING DATA QUALITY",
          classes: "bg-purple-500/10 text-purple-400 border-purple-500/30 animate-pulse"
        };
      default:
        return {
          label: status.toUpperCase(),
          classes: "bg-surface-container-high text-on-surface-variant border-outline-variant/30"
        };
    }
  };

  const getMarketplaceTheme = (m: MarketplaceType) => {
    switch (m) {
      case "daraz":
        return { name: "Daraz Pakistan", color: "text-[#f85606]", border: "border-[#f85606]/40", bg: "bg-[#f85606]/10" };
      case "amazon":
        return { name: "Amazon US", color: "text-amber-400", border: "border-amber-400/40", bg: "bg-amber-400/10" };
      case "ebay":
        return { name: "eBay Global", color: "text-blue-400", border: "border-blue-400/40", bg: "bg-blue-400/10" };
      case "shopify":
        return { name: "Shopify Stores", color: "text-emerald-400", border: "border-emerald-400/40", bg: "bg-emerald-400/10" };
    }
  };

  // Group internal results by category
  const products = internalResults.filter((r) => r.category === "products");
  const darazProducts = products.filter((r) => r.id.startsWith("daraz_") || r.badge === "Daraz Pakistan");
  const localProducts = products.filter((r) => !r.id.startsWith("daraz_") && r.badge !== "Daraz Pakistan");
  const categories = internalResults.filter((r) => r.category === "categories");
  const platforms = internalResults.filter((r) => r.category === "platforms");
  const reports = internalResults.filter((r) => r.category === "reports");
  const alerts = internalResults.filter((r) => r.category === "alerts");

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Header & Mode Switcher */}
      <div className="border-b border-outline-variant/15 pb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
              MARKETPLACE CANDIDATE ACQUISITION PIPELINE
            </span>
            <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
              Marketplace Search & Verification
            </h1>
            <p className="text-xs text-on-surface-variant mt-1">
              Real-time multi-page acquisition (target 200–250+ candidates), Data Quality filtering, deduplication, and ranking. Output strictly capped at 30 verified listings.
            </p>
          </div>

          {/* Mode Toggle */}
          <div className="inline-flex rounded-xl bg-surface-container-low p-1 border border-outline-variant/20">
            <button
              onClick={() => { setMode("marketplace"); setSearchParams({ mode: "marketplace" }); }}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                mode === "marketplace"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Marketplace Pipeline
            </button>
            <button
              onClick={() => { setMode("internal"); setSearchParams({ mode: "internal" }); }}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                mode === "internal"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Internal Entities
            </button>
          </div>
        </div>

        {/* Search Bar & Marketplace Selector (Marketplace Mode) */}
        {mode === "marketplace" ? (
          <div className="mt-6 space-y-4">
            {/* Marketplace Selectors */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1">
              {(["daraz", "amazon", "ebay", "shopify"] as MarketplaceType[]).map((m) => {
                const isSelected = selectedMarketplace === m;
                const theme = getMarketplaceTheme(m);
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setSelectedMarketplace(m)}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 border ${
                      isSelected
                        ? `${theme.bg} ${theme.color} ${theme.border} shadow-md`
                        : "bg-surface-container-low text-on-surface-variant/70 border-outline-variant/20 hover:border-outline-variant/50"
                    }`}
                  >
                    <span className="material-symbols-outlined text-base">
                      {m === "daraz" ? "local_mall" : m === "amazon" ? "storefront" : m === "ebay" ? "gavel" : "shopping_bag"}
                    </span>
                    {theme.name}
                  </button>
                );
              })}
            </div>

            {/* Keyword Form */}
            <form onSubmit={handleMarketplaceSearch} className="flex gap-3">
              <div className="relative flex-1">
                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-primary text-xl">
                  travel_explore
                </span>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={`Search ${getMarketplaceTheme(selectedMarketplace).name} (e.g. 'wireless earbuds', 'smart watch', 'mechanical keyboard')...`}
                  className="w-full bg-surface-container-low border border-primary/30 rounded-2xl pl-12 pr-4 py-3.5 text-sm text-on-surface placeholder-on-surface-variant/50 focus:outline-none focus:border-primary shadow-xl"
                  autoFocus
                />
              </div>
              <button
                type="submit"
                disabled={mktLoading || !query.trim()}
                className="px-6 py-3.5 rounded-2xl bg-primary text-on-primary font-bold text-sm hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg flex items-center gap-2"
              >
                {mktLoading ? (
                  <>
                    <span className="w-4 h-4 rounded-full border-2 border-on-primary border-t-transparent animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-lg">search</span>
                    <span>Acquire Candidates</span>
                  </>
                )}
              </button>
            </form>

            <div className="flex items-center justify-between text-[11px] text-on-surface-variant/70 px-1 font-mono-data">
              <span>Pipeline Configuration: Target = 250 real items | Output Limit = Max 30 verified</span>
              <span>Provider: {selectedMarketplace === "daraz" ? "Daraz Specialized Engine" : selectedMarketplace === "shopify" ? "Shopify Scout" : "ScrapeGraphAI Engine"}</span>
            </div>
          </div>
        ) : (
          /* Internal Cross-Entity Search Form */
          <form onSubmit={handleInternalSubmit} className="mt-4 relative">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-primary text-xl">
              search
            </span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search local products, market categories, platforms, reports, alerts..."
              className="w-full bg-surface-container-low border border-primary/30 rounded-2xl pl-12 pr-4 py-3.5 text-sm text-on-surface placeholder-on-surface-variant/50 focus:outline-none focus:border-primary shadow-xl"
              autoFocus
            />
          </form>
        )}
      </div>

      {/* ========================================================================= */}
      {/* MARKETPLACE MODE RESULTS & FUNNEL TELEMETRY */}
      {/* ========================================================================= */}
      {mode === "marketplace" && (
        <div className="space-y-6">
          {mktLoading ? (
            <div className="py-16 text-center space-y-4">
              <LoadingSpinner size="lg" label={`Executing candidate acquisition on ${getMarketplaceTheme(selectedMarketplace).name}...`} />
              <p className="text-xs text-on-surface-variant font-mono-data">
                Extracting multi-page catalog candidates → Normalizing → Running Data Quality Agent → Deduplicating → Ranking verified listings...
              </p>
            </div>
          ) : mktError ? (
            <div className="p-6 rounded-2xl bg-error/10 border border-error/20 text-error space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm">
                <span className="material-symbols-outlined text-lg">error</span>
                Candidate Acquisition Error
              </div>
              <p className="text-xs text-on-surface-variant">{mktError}</p>
            </div>
          ) : mktResult ? (
            <div className="space-y-6">
              {/* Funnel Metrics Banner */}
              <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-outline-variant/10 pb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-on-surface font-mono-data uppercase">
                      Search ID: {mktResult.search_id}
                    </span>
                    <span className={`text-[10px] font-label-caps uppercase px-2.5 py-0.5 rounded-full border font-bold ${getStatusBadge(mktResult.status).classes}`}>
                      {getStatusBadge(mktResult.status).label}
                    </span>
                  </div>
                  <span className="text-xs text-on-surface-variant">
                    Keyword: <strong className="text-on-surface">"{mktResult.keyword}"</strong> on {getMarketplaceTheme(mktResult.marketplace).name}
                  </span>
                </div>

                {/* Pipeline Funnel Counters */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <div className="p-3 rounded-xl bg-surface-container-lowest/60 border border-outline-variant/15 text-center">
                    <span className="text-[10px] font-label-caps uppercase text-on-surface-variant block">1. Acquired</span>
                    <span className="text-xl font-bold text-primary font-mono-data">{mktResult.candidate_count}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-container-lowest/60 border border-outline-variant/15 text-center">
                    <span className="text-[10px] font-label-caps uppercase text-on-surface-variant block">2. Normalized</span>
                    <span className="text-xl font-bold text-on-surface font-mono-data">{mktResult.normalized_count}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-container-lowest/60 border border-outline-variant/15 text-center">
                    <span className="text-[10px] font-label-caps uppercase text-on-surface-variant block">3. Passed DQ</span>
                    <span className="text-xl font-bold text-emerald-400 font-mono-data">{mktResult.quality_passed_count}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-container-lowest/60 border border-outline-variant/15 text-center">
                    <span className="text-[10px] font-label-caps uppercase text-on-surface-variant block">4. Deduplicated</span>
                    <span className="text-xl font-bold text-on-surface font-mono-data">{mktResult.deduplicated_count}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-container-lowest/60 border border-primary/30 text-center col-span-2 sm:col-span-1">
                    <span className="text-[10px] font-label-caps uppercase text-primary font-bold block">5. Displayed</span>
                    <span className="text-xl font-bold text-primary font-mono-data">{mktResult.returned_count} / 30</span>
                  </div>
                </div>

                {mktResult.message && (
                  <p className="text-xs text-on-surface-variant italic">
                    {mktResult.message}
                  </p>
                )}
              </div>

              {/* Verified Product Cards Grid */}
              {mktResult.products.length > 0 ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-label-caps uppercase text-primary tracking-wider font-semibold">
                      Verified Marketplace Products ({mktResult.products.length})
                    </h3>
                    <span className="text-[11px] text-on-surface-variant font-mono-data">
                      Strict cap: 30 products max
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {mktResult.products.map((p, idx) => (
                      <div
                        key={idx}
                        className="bg-surface-container-low rounded-2xl border border-outline-variant/20 hover:border-primary/40 transition-all p-4 flex flex-col justify-between glass-card group space-y-3"
                      >
                        <div className="space-y-3">
                          {/* Image & Marketplace Badge */}
                          <div className="relative aspect-video rounded-xl overflow-hidden bg-surface-container-lowest flex items-center justify-center">
                            {p.image_url ? (
                              <img
                                src={p.image_url}
                                alt={p.title}
                                className="w-full h-full object-contain p-2 group-hover:scale-105 transition-transform"
                                onError={(e) => {
                                  (e.target as HTMLElement).style.display = "none";
                                }}
                              />
                            ) : (
                              <span className="material-symbols-outlined text-3xl text-on-surface-variant/30">
                                image_not_supported
                              </span>
                            )}
                            <span className={`absolute top-2 left-2 text-[10px] font-mono-data font-bold px-2 py-0.5 rounded-md ${getMarketplaceTheme(p.marketplace).bg} ${getMarketplaceTheme(p.marketplace).color} border ${getMarketplaceTheme(p.marketplace).border}`}>
                              {p.marketplace.toUpperCase()}
                            </span>
                            <span className="absolute top-2 right-2 text-[10px] font-mono-data px-1.5 py-0.5 rounded bg-surface-container-lowest/80 text-on-surface-variant border border-outline-variant/30">
                              #{idx + 1}
                            </span>
                          </div>

                          {/* Title */}
                          <h4 className="text-sm font-bold text-on-surface line-clamp-2 group-hover:text-primary transition-colors" title={p.title}>
                            {p.title}
                          </h4>

                          {/* Seller & Brand */}
                          <div className="text-[11px] text-on-surface-variant space-y-0.5">
                            {p.seller && (
                              <div className="truncate">
                                Seller: <strong className="text-on-surface font-medium">{p.seller}</strong>
                              </div>
                            )}
                            {p.brand && (
                              <div className="truncate">
                                Brand: <strong className="text-on-surface font-medium">{p.brand}</strong>
                              </div>
                            )}
                            {p.category && (
                              <div className="truncate text-primary/80">
                                Category: {p.category}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Price, Ratings & Action */}
                        <div className="pt-3 border-t border-outline-variant/15 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-base font-bold text-on-surface font-mono-data">
                              {formatPrice(p)}
                            </span>
                            {p.rating !== null && p.rating !== undefined ? (
                              <div className="flex items-center gap-1 text-amber-400 text-xs font-bold font-mono-data">
                                <span className="material-symbols-outlined text-sm">star</span>
                                <span>{p.rating}</span>
                                {p.review_count !== null && p.review_count !== undefined && (
                                  <span className="text-[10px] text-on-surface-variant/70 font-normal">
                                    ({p.review_count.toLocaleString()})
                                  </span>
                                )}
                              </div>
                            ) : (
                              <span className="text-[10px] text-on-surface-variant/50 italic">
                                No rating
                              </span>
                            )}
                          </div>

                          <div className="flex items-center justify-between text-[10px] text-on-surface-variant font-mono-data pt-1">
                            <span>Provider: {p.source_provider}</span>
                            <a
                              href={p.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-primary hover:underline font-bold"
                            >
                              <span>View Listing</span>
                              <span className="material-symbols-outlined text-xs">open_in_new</span>
                            </a>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyState
                  title={mktResult.status === "insufficient_data" ? "Insufficient Verified Data" : "No Verified Products Found"}
                  description={
                    mktResult.message ||
                    `No verified products met the data quality standards for query "${query}" on ${getMarketplaceTheme(selectedMarketplace).name}.`
                  }
                  icon="inventory_2"
                />
              )}
            </div>
          ) : (
            <EmptyState
              title="Acquire Marketplace Candidates"
              description={`Select a marketplace (Daraz, Amazon, eBay, Shopify) and enter a product keyword above to initiate candidate acquisition and Data Quality verification.`}
              icon="manage_search"
            />
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* INTERNAL CROSS-ENTITY MODE RESULTS */}
      {/* ========================================================================= */}
      {mode === "internal" && (
        <div className="space-y-8">
          {internalLoading ? (
            <LoadingSpinner size="lg" label="Searching across all market databases..." />
          ) : query.trim() === "" ? (
            <EmptyState
              title="Search TrendPulse Intelligence"
              description="Type a keyword to discover matching products, velocity anomalies, and generated reports."
              icon="search"
            />
          ) : internalResults.length === 0 ? (
            <EmptyState
              title="No Matching Records Found"
              description={`No entities matched your query "${query}". Try searching for categories like 'Beauty', 'Electronics', or platforms like 'TikTok'.`}
              icon="manage_search"
            />
          ) : (
            <div className="space-y-8">
              {localProducts.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-label-caps uppercase text-primary tracking-wider font-semibold">
                    Ingested Products ({localProducts.length})
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {localProducts.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => navigate(item.link)}
                        className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.01] glass-card flex items-center justify-between"
                      >
                        <div>
                          <h4 className="text-sm font-bold text-on-surface line-clamp-1">{item.title}</h4>
                          <p className="text-xs text-on-surface-variant line-clamp-1">{item.subtitle}</p>
                        </div>
                        {item.badge && (
                          <span className="text-[10px] font-mono-data px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 flex-shrink-0 ml-2">
                            {item.badge}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {darazProducts.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-label-caps uppercase text-[#f85606] tracking-wider font-semibold flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#f85606] animate-pulse"></span>
                      Daraz Pakistan Live Marketplace ({darazProducts.length})
                    </h3>
                    <span className="text-[10px] text-on-surface-variant font-mono-data">Source: daraz.pk</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {darazProducts.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => setSelectedDarazId(item.id)}
                        className="p-4 rounded-xl bg-surface-container-low border border-[#f85606]/30 hover:border-[#f85606] cursor-pointer transition-all hover:scale-[1.01] glass-card flex items-center justify-between group"
                      >
                        <div className="flex-1 min-w-0 pr-2">
                          <h4 className="text-sm font-bold text-on-surface group-hover:text-[#f85606] transition-colors line-clamp-1">
                            {item.title}
                          </h4>
                          <p className="text-xs text-on-surface-variant line-clamp-1">{item.subtitle}</p>
                        </div>
                        <span className="text-[10px] font-mono-data px-2 py-0.5 rounded bg-[#f85606]/10 text-[#f85606] border border-[#f85606]/30 flex-shrink-0 font-bold">
                          Daraz PK
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {categories.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-label-caps uppercase text-primary tracking-wider font-semibold">
                    Categories ({categories.length})
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {categories.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => navigate(item.link)}
                        className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.01] glass-card"
                      >
                        <h4 className="text-sm font-bold text-on-surface">{item.title}</h4>
                        <p className="text-xs text-on-surface-variant">{item.subtitle}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {platforms.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-label-caps uppercase text-primary tracking-wider font-semibold">
                    Platforms ({platforms.length})
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {platforms.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => navigate(item.link)}
                        className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.01] glass-card"
                      >
                        <h4 className="text-sm font-bold text-on-surface">{item.title}</h4>
                        <p className="text-xs text-on-surface-variant">{item.subtitle}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {reports.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-label-caps uppercase text-primary tracking-wider font-semibold">
                    Reports ({reports.length})
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {reports.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => navigate(item.link)}
                        className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.01] glass-card"
                      >
                        <h4 className="text-sm font-bold text-on-surface">{item.title}</h4>
                        <p className="text-xs text-on-surface-variant">{item.subtitle}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {alerts.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-label-caps uppercase text-primary tracking-wider font-semibold">
                    Alerts ({alerts.length})
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {alerts.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => navigate(item.link)}
                        className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.01] glass-card flex items-center justify-between"
                      >
                        <div>
                          <h4 className="text-sm font-bold text-on-surface">{item.title}</h4>
                          <p className="text-xs text-on-surface-variant">{item.subtitle}</p>
                        </div>
                        {item.badge && (
                          <span className="text-[10px] font-mono-data px-2 py-0.5 rounded bg-error/10 text-error border border-error/20">
                            {item.badge}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
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
