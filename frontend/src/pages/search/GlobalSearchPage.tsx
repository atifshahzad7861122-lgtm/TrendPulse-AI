import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { searchService } from "../../services/domainServices";
import type { SearchResultItem } from "../../types";
import { LoadingSpinner, EmptyState } from "../../components/common/StateComponents";

export const GlobalSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await searchService.search(query.trim());
        if (res.success && res.data) {
          setResults(res.data.results);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams({ q: query });
  };

  // Group by category
  const products = results.filter((r) => r.category === "products");
  const categories = results.filter((r) => r.category === "categories");
  const platforms = results.filter((r) => r.category === "platforms");
  const reports = results.filter((r) => r.category === "reports");
  const alerts = results.filter((r) => r.category === "alerts");

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Header & Search Bar */}
      <div className="border-b border-outline-variant/15 pb-6">
        <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
          CROSS-ENTITY QUERY ENGINE
        </span>
        <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
          Global Intelligence Search
        </h1>
        <form onSubmit={handleSearchSubmit} className="mt-4 relative">
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-primary text-xl">
            search
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search products, market categories, platforms, reports, alerts..."
            className="w-full bg-surface-container-low border border-primary/30 rounded-2xl pl-12 pr-4 py-3.5 text-sm text-on-surface placeholder-on-surface-variant/50 focus:outline-none focus:border-primary shadow-xl"
            autoFocus
          />
        </form>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Searching across all market databases..." />
      ) : query.trim() === "" ? (
        <EmptyState
          title="Search TrendPulse Intelligence"
          description="Type a keyword to discover matching products, velocity anomalies, and generated reports."
          icon="search"
        />
      ) : results.length === 0 ? (
        <EmptyState
          title="No Matching Records Found"
          description={`No entities matched your query "${query}". Try searching for categories like 'Beauty', 'Electronics', or platforms like 'TikTok'.`}
          icon="manage_search"
        />
      ) : (
        <div className="space-y-8">
          {products.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-label-caps uppercase text-primary tracking-wider font-semibold">
                Products ({products.length})
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {products.map((item) => (
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
                      <span className="text-[10px] font-mono-data px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                        {item.badge}
                      </span>
                    )}
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
  );
};
