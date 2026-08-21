import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { reportService } from "../../services/domainServices";
import type { Report } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const ReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchReport = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await reportService.getById(id);
      if (res.success && res.data) {
        setReport(res.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load report dossier");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [id]);

  const handleExportJson = () => {
    if (!report) return;
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(report, null, 2)
    )}`;
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonString);
    downloadAnchor.setAttribute("download", `report_${report.id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast("Report exported to JSON", "success");
  };

  const handleExportCsv = () => {
    if (!report) return;
    const csvContent = `data:text/csv;charset=utf-8,ID,Title,Template,TimeRange,TotalSignals,Convictions\n${report.id},"${report.title}",${report.template},${report.time_range},${report.total_signals_analyzed},${report.high_conviction_count}\n`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `report_${report.id}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    showToast("Report exported to CSV", "success");
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return <LoadingSpinner size="lg" label="Retrieving synthesized report..." />;
  }

  if (error || !report) {
    return <ErrorState message={error || "Report not found"} onRetry={fetchReport} />;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Top Header & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/reports")}
            className="p-2 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface-variant hover:text-on-surface hover:border-primary/40 transition-all"
            title="Back to reports list"
          >
            <span className="material-symbols-outlined text-lg">arrow_back</span>
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono-data uppercase font-bold text-primary px-2.5 py-0.5 rounded-full bg-primary/10 border border-primary/20">
                {report.template.replace("_", " ")}
              </span>
              <span className="text-xs text-on-surface-variant font-mono-data">
                {new Date(report.created_at).toLocaleDateString()}
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
              {report.title}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface-container border border-outline-variant/30 text-xs font-label-caps text-on-surface hover:text-primary transition-colors"
          >
            <span className="material-symbols-outlined text-sm">table_chart</span>
            Export CSV
          </button>
          <button
            onClick={handleExportJson}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface-container border border-outline-variant/30 text-xs font-label-caps text-on-surface hover:text-primary transition-colors"
          >
            <span className="material-symbols-outlined text-sm">code</span>
            JSON
          </button>
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-on-primary text-xs font-label-caps font-semibold hover:bg-primary-container transition-all"
          >
            <span className="material-symbols-outlined text-sm">print</span>
            Print View
          </button>
        </div>
      </div>

      {/* Report Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-surface-container-low p-4 rounded-xl border border-outline-variant/20">
          <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
            Total Signals
          </span>
          <p className="text-xl font-mono-data font-bold text-primary mt-1">
            {report.total_signals_analyzed.toLocaleString()}
          </p>
        </div>
        <div className="bg-surface-container-low p-4 rounded-xl border border-outline-variant/20">
          <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
            High Conviction
          </span>
          <p className="text-xl font-mono-data font-bold text-on-surface mt-1">
            {report.high_conviction_count} Targets
          </p>
        </div>
        <div className="bg-surface-container-low p-4 rounded-xl border border-outline-variant/20">
          <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
            Time Horizon
          </span>
          <p className="text-xl font-mono-data font-bold text-on-surface mt-1">
            {report.time_range.toUpperCase()}
          </p>
        </div>
        <div className="bg-surface-container-low p-4 rounded-xl border border-outline-variant/20">
          <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
            Author
          </span>
          <p className="text-sm font-semibold text-on-surface mt-1 truncate">
            {report.created_by}
          </p>
        </div>
      </div>

      {/* AI Synthesis Statement */}
      <div className="bg-surface-container-low p-8 rounded-3xl border border-primary/30 relative overflow-hidden glass-panel space-y-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <span className="text-xs font-label-caps text-primary uppercase tracking-wider font-semibold">
            Executive Synthesis & Conviction Assessment
          </span>
        </div>
        <p className="font-editorial-italic text-lg md:text-xl text-on-surface leading-relaxed italic">
          "{report.ai_takeaways}"
        </p>
      </div>

      {/* Key Strategic Findings */}
      <div className="bg-surface-container-low p-6 md:p-8 rounded-2xl border border-outline-variant/20 glass-card space-y-4">
        <h3 className="text-base font-bold text-on-surface">Key Signal Findings & Anomalies</h3>
        <div className="space-y-3">
          {report.key_findings.map((item, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-container border border-outline-variant/15"
            >
              <div className="w-5 h-5 rounded-full bg-primary/20 text-primary font-mono-data text-xs flex items-center justify-center font-bold shrink-0 mt-0.5">
                {idx + 1}
              </div>
              <p className="text-xs md:text-sm text-on-surface leading-relaxed">{item}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Included Channels */}
      <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card flex flex-wrap items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-bold text-on-surface">Ingestion Sources Analyzed</h4>
          <p className="text-xs text-on-surface-variant">
            Cross-referenced telemetry across validated channels
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {report.platforms.map((plat) => (
            <span
              key={plat}
              className="text-xs font-mono-data px-3 py-1 rounded-lg bg-surface-container border border-outline-variant/20 text-primary font-semibold"
            >
              {plat}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
