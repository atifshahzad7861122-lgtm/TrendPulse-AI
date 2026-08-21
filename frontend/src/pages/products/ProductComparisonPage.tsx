import React, { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { productService } from "../../services/domainServices";
import type { Product } from "../../types";
import { LoadingSpinner, EmptyState, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

const LINE_COLORS = ["#ffb68d", "#c9c6c5", "#df7328", "#ffdcc2"];

export const ProductComparisonPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const rawIds = searchParams.get("ids") || "prod_01,prod_02";

  const [compareIds, setCompareIds] = useState<string[]>(
    rawIds.split(",").filter((i) => i.trim())
  );
  const [allProducts, setAllProducts] = useState<Product[]>([]);
  const [comparedProducts, setComparedProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { showToast } = useToast();

  useEffect(() => {
    const fetchAllAndCompare = async () => {
      setLoading(true);
      setError(null);
      try {
        const [allRes, compRes] = await Promise.all([
          productService.list(),
          productService.compare(compareIds),
        ]);
        if (allRes.success && allRes.data) setAllProducts(allRes.data);
        if (compRes.success && compRes.data) setComparedProducts(compRes.data);
      } catch (err: any) {
        setError(err.message || "Failed to load product comparison");
      } finally {
        setLoading(false);
      }
    };

    if (compareIds.length > 0) {
      fetchAllAndCompare();
    } else {
      setLoading(false);
    }
  }, [compareIds]);

  const removeProduct = (id: string) => {
    if (compareIds.length <= 1) {
      showToast("Comparison requires at least 1 product", "warning");
      return;
    }
    const updated = compareIds.filter((i) => i !== id);
    setCompareIds(updated);
    setSearchParams({ ids: updated.join(",") });
  };

  const addProduct = (id: string) => {
    if (compareIds.includes(id)) return;
    if (compareIds.length >= 4) {
      showToast("You can compare up to 4 products simultaneously", "warning");
      return;
    }
    const updated = [...compareIds, id];
    setCompareIds(updated);
    setSearchParams({ ids: updated.join(",") });
  };

  // Build chart dataset
  const chartData = [
    { day: "Day 1" },
    { day: "Day 2" },
    { day: "Day 3" },
    { day: "Day 4" },
    { day: "Day 5" },
    { day: "Day 6" },
    { day: "Today" },
  ].map((item, idx) => {
    const point: any = { day: item.day };
    comparedProducts.forEach((p) => {
      const score = p.historical_scores[idx]?.score || p.trend_score;
      point[p.name] = score;
    });
    return point;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            HEAD-TO-HEAD MATRIX
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Product Signal Comparison
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Analyze trajectory divergence, platform shares, and sentiment conviction side-by-side.
          </p>
        </div>

        {/* Add Product Dropdown */}
        <div className="flex items-center gap-3">
          <select
            onChange={(e) => {
              if (e.target.value) {
                addProduct(e.target.value);
                e.target.value = "";
              }
            }}
            className="bg-surface-container border border-primary/30 rounded-xl px-3.5 py-2 text-xs text-on-surface focus:outline-none focus:border-primary"
            defaultValue=""
          >
            <option value="" disabled>
              + Add Product to Compare
            </option>
            {allProducts
              .filter((p) => !compareIds.includes(p.id))
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.category})
                </option>
              ))}
          </select>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Aligning comparison matrices..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => setCompareIds(rawIds.split(","))} />
      ) : comparedProducts.length === 0 ? (
        <EmptyState
          title="No Products Selected"
          description="Select 2 to 4 products from the dropdown above to generate the comparative trajectory curve and dimensional matrix."
          icon="compare_arrows"
        />
      ) : (
        <>
          {/* Active Product Pills */}
          <div className="flex flex-wrap items-center gap-3">
            {comparedProducts.map((p, idx) => (
              <div
                key={p.id}
                className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-surface-container border border-outline-variant/30 glass-card"
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: LINE_COLORS[idx % LINE_COLORS.length] }}
                />
                <span className="text-xs font-semibold text-on-surface">{p.name}</span>
                <button
                  onClick={() => removeProduct(p.id)}
                  className="text-on-surface-variant hover:text-error transition-colors p-0.5"
                  title="Remove from comparison"
                >
                  <span className="material-symbols-outlined text-sm">close</span>
                </button>
              </div>
            ))}
          </div>

          {/* Overlapping Trajectory Chart */}
          <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card">
            <h3 className="text-base font-bold text-on-surface mb-1">Comparative Trajectory Curve</h3>
            <p className="text-xs text-on-surface-variant mb-6">
              7-Day normalized velocity divergence across compared products
            </p>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#292a27" />
                  <XAxis dataKey="day" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
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
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                  {comparedProducts.map((p, idx) => (
                    <Line
                      key={p.id}
                      type="monotone"
                      dataKey={p.name}
                      stroke={LINE_COLORS[idx % LINE_COLORS.length]}
                      strokeWidth={2.5}
                      dot={{ r: 4 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Comparison Matrix Table */}
          <div className="bg-surface-container-low rounded-2xl border border-outline-variant/20 overflow-hidden glass-card">
            <div className="p-5 border-b border-outline-variant/15">
              <h3 className="text-base font-bold text-on-surface">Dimensional Metrics Matrix</h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-outline-variant/20 bg-surface-container-lowest/50 text-on-surface-variant font-label-caps uppercase">
                    <th className="p-4">Dimension</th>
                    {comparedProducts.map((p) => (
                      <th key={p.id} className="p-4 font-bold text-on-surface min-w-[200px]">
                        {p.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10 text-on-surface">
                  <tr>
                    <td className="p-4 font-label-caps text-on-surface-variant uppercase">Trend Score</td>
                    {comparedProducts.map((p) => (
                      <td key={p.id} className="p-4 font-mono-data font-bold text-primary text-base">
                        {p.trend_score}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-4 font-label-caps text-on-surface-variant uppercase">Velocity Label</td>
                    {comparedProducts.map((p) => (
                      <td key={p.id} className="p-4 font-mono-data">
                        <span className="px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                          {p.velocity_label}
                        </span>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-4 font-label-caps text-on-surface-variant uppercase">YoY Growth</td>
                    {comparedProducts.map((p) => (
                      <td key={p.id} className="p-4 font-mono-data font-bold">
                        +{p.growth_rate}%
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-4 font-label-caps text-on-surface-variant uppercase">Monthly Volume</td>
                    {comparedProducts.map((p) => (
                      <td key={p.id} className="p-4 font-mono-data">
                        {p.volume.toLocaleString()} mentions
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-4 font-label-caps text-on-surface-variant uppercase">Sentiment Score</td>
                    {comparedProducts.map((p) => (
                      <td key={p.id} className="p-4 font-mono-data">
                        {Math.round(p.sentiment_score * 100)}% Positive
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-4 font-label-caps text-on-surface-variant uppercase">Primary Channel</td>
                    {comparedProducts.map((p) => (
                      <td key={p.id} className="p-4 font-medium">
                        {p.primary_platform}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-4 font-label-caps text-on-surface-variant uppercase">Price Band</td>
                    {comparedProducts.map((p) => (
                      <td key={p.id} className="p-4 font-mono-data">
                        {p.price_range}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-4 font-label-caps text-on-surface-variant uppercase">Actions</td>
                    {comparedProducts.map((p) => (
                      <td key={p.id} className="p-4">
                        <Link
                          to={`/products/${p.id}`}
                          className="text-xs text-primary font-semibold hover:underline flex items-center gap-1"
                        >
                          View Full Intel
                          <span className="material-symbols-outlined text-sm">arrow_forward</span>
                        </Link>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
