import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { categoryService } from "../../services/domainServices";
import type { Category } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";

export const CategoriesPage: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  const fetchCategories = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await categoryService.list();
      if (res.success && res.data) {
        setCategories(res.data);
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
    c.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            SECTOR BREAKDOWNS
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Category Intelligence
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Macro demand velocity aggregated across e-commerce product taxonomy.
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
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((cat) => (
            <div
              key={cat.id}
              onClick={() => navigate(`/products?category=${encodeURIComponent(cat.name)}`)}
              className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.02] glass-card flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-mono-data font-bold text-primary px-2.5 py-0.5 rounded bg-primary/10 border border-primary/20">
                    {cat.velocity_label}
                  </span>
                  <span className="text-xs font-mono-data font-bold text-on-surface-variant">
                    {cat.product_count} Products Monitored
                  </span>
                </div>

                <h3 className="text-lg font-bold text-on-surface group-hover:text-primary transition-colors">
                  {cat.name}
                </h3>
                <p className="text-xs text-on-surface-variant mt-2 leading-relaxed">
                  {cat.description}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-outline-variant/15 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                    Sector Velocity
                  </span>
                  <p className="text-xl font-mono-data font-bold text-primary">
                    {cat.avg_trend_score}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                    YoY Growth
                  </span>
                  <p className="text-sm font-mono-data font-bold text-on-surface">
                    +{cat.growth_rate}%
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
