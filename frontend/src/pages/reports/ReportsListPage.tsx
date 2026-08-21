import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { reportService } from "../../services/domainServices";
import type { Report } from "../../types";
import { LoadingSpinner, EmptyState, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const ReportsListPage: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await reportService.list();
      if (res.success && res.data) {
        setReports(res.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load intelligence reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleExport = (e: React.MouseEvent, r: Report) => {
    e.stopPropagation();
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(r, null, 2)
    )}`;
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonString);
    downloadAnchor.setAttribute("download", `report_${r.id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast(`Report ${r.id} exported to JSON`, "success");
  };

  const filtered = reports.filter((r) =>
    r.title.toLowerCase().includes(search.toLowerCase()) ||
    r.template.toLowerCase().includes(search.toLowerCase()) ||
    (r.category && r.category.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            SYNTHESIZED INTELLIGENCE DOSSIERS
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Market Reports
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Executive briefings, category velocity surges, and cross-platform arbitrage opportunities.
          </p>
        </div>

        <Link
          to="/report-generation"
          className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-primary text-on-primary text-xs font-label-caps font-semibold hover:bg-primary-container transition-all shadow-[0_0_20px_rgba(255,182,141,0.25)] self-start md:self-auto"
        >
          <span className="material-symbols-outlined text-base">auto_awesome</span>
          Generate New Report
        </Link>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Retrieving report archives..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchReports} />
      ) : reports.length === 0 ? (
        <EmptyState
          title="No Reports Generated Yet"
          description="Generate your first executive market briefing using our synthesized multi-platform AI pipeline."
          icon="analytics"
          actionText="Generate Report"
          onAction={() => navigate("/report-generation")}
        />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono-data text-on-surface-variant">
              {filtered.length} reports archived
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search reports..."
              className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-primary"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filtered.map((rep) => (
              <div
                key={rep.id}
                onClick={() => navigate(`/reports/${rep.id}`)}
                className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all hover:scale-[1.01] glass-card flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-mono-data font-bold text-primary uppercase px-2.5 py-0.5 rounded bg-primary/10 border border-primary/20">
                      {rep.template.replace("_", " ")}
                    </span>
                    <span className="text-xs font-mono-data text-on-surface-variant">
                      {new Date(rep.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-on-surface group-hover:text-primary transition-colors leading-snug">
                    {rep.title}
                  </h3>
                  <p className="text-xs text-on-surface-variant mt-2 line-clamp-2 leading-relaxed">
                    {rep.ai_takeaways}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-outline-variant/15 flex items-center justify-between">
                  <div className="flex items-center gap-4 text-xs font-mono-data text-on-surface-variant">
                    <span>{rep.total_signals_analyzed.toLocaleString()} signals</span>
                    <span>•</span>
                    <span className="text-primary">{rep.high_conviction_count} Convictions</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => handleExport(e, rep)}
                      className="p-1.5 rounded-lg bg-surface-container text-on-surface-variant hover:text-primary hover:border-primary/30 transition-colors"
                      title="Export JSON"
                    >
                      <span className="material-symbols-outlined text-base">download</span>
                    </button>
                    <span className="text-xs font-label-caps text-primary font-semibold flex items-center gap-1">
                      Read Report →
                    </span>
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
