import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { categoryService, marketIntelligenceService } from "../../services/domainServices";
import type { Category, CategoryIntelligenceItem } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";

export const CategoriesPage: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [intelMap, setIntelMap] = useState<Record<string, CategoryIntelligenceItem>>({});
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  const fetchCategories = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, intelRes] = await Promise.allSettled([
        categoryService.list(),
        marketIntelligenceService.getCategories()
      ]);
      if (res.status === "fulfilled" && res.value.success && res.value.data) {
        setCategories(res.value.data);
      }
      if (intelRes.status === "fulfilled" && intelRes.value.success && intelRes.value.data) {
        const map: Record<string, CategoryIntelligenceItem> = {};
        for (const item of intelRes.value.data.categories) {
          map[item.category_name.toLowerCase()] = item;
        }
        setIntelMap(map);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load categories");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  const filtered = categories.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    (c.description && c.description.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            SECTOR BREAKDOWNS & PROVENANCE
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Category Intelligence
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Macro demand velocity aggregated across verified e-commerce product taxonomy.
          </p>
        </div>

        <div className="w-full md:w-72">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter categories..."
            className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
          />
        </div>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Aggregating category demand..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchCategories} />
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-surface-container-low rounded-2xl border border-outline-variant/20 p-8 space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-surface-container-high border border-outline-variant/30 flex items-center justify-center mx-auto text-primary">
            <span className="material-symbols-outlined text-3xl">category</span>
          </div>
          <div>
            <h3 className="text-lg font-bold text-on-surface">No Category Intelligence Available</h3>
            <p className="text-xs text-on-surface-variant max-w-md mx-auto mt-1 leading-relaxed">
              No persisted marketplace products or ingested signals have been categorized yet. Launch a scraper or connect a data source to generate macro demand analytics.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((cat) => {
            const hasData = cat.product_count > 0;
            const hasGrowth = cat.growth_rate !== 0;
            const hasScore = cat.avg_trend_score > 0;

            return (
              <div
                key={cat.id}
                onClick={() => navigate(`/products?category=${encodeURIComponent(cat.name)}`)}
                className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.02] glass-card flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span
                      className={`text-[10px] font-mono-data font-bold uppercase px-2.5 py-0.5 rounded border ${
                        hasData
                          ? "bg-primary/10 text-primary border-primary/20"
                          : "bg-surface-container text-on-surface-variant border-outline-variant/30"
                      }`}
                    >
                      {hasData ? cat.velocity_label : "NO DATA"}
                    </span>
                    <span className="text-xs font-mono-data font-bold text-on-surface-variant">
                      {hasData ? `${cat.product_count} Products Monitored` : "0 Products (No Data)"}
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-on-surface group-hover:text-primary transition-colors">
                    {cat.name}
                  </h3>
                  <p className="text-xs text-on-surface-variant mt-2 leading-relaxed">
                    {cat.description}
                  </p>

                  {/* Phase 3 Market Intelligence Stats */}
                  {(() => {
                    const intel = intelMap[cat.name.toLowerCase()];
                    if (!intel) return null;
                    return (
                      <div className="mt-3 grid grid-cols-3 gap-2 p-2 rounded-xl bg-surface-container/60 border border-outline-variant/15 text-[10px] font-mono-data">
                        <div>
                          <span className="text-on-surface-variant block">Mkt Score</span>
                          <span className="font-bold text-primary">{intel.average_market_score}/100</span>
                        </div>
                        <div>
                          <span className="text-on-surface-variant block">Demand</span>
                          <span className="font-bold text-on-surface">{intel.demand_level}</span>
                        </div>
                        <div>
                          <span className="text-on-surface-variant block">Opportunity</span>
                          <span className="font-bold text-emerald-400">{intel.opportunity_level}</span>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                <div className="mt-6 pt-4 border-t border-outline-variant/15 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                      Sector Velocity
                    </span>
                    <p className={`text-xl font-mono-data font-bold ${hasScore ? "text-primary" : "text-on-surface-variant"}`}>
                      {hasScore ? cat.avg_trend_score : "—"}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                      YoY Growth
                    </span>
                    <p className="text-sm font-mono-data font-bold text-on-surface">
                      {hasGrowth ? (cat.growth_rate > 0 ? `+${cat.growth_rate}%` : `${cat.growth_rate}%`) : "—"}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
