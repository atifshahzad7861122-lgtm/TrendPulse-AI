import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { alertService } from "../../services/domainServices";
import type { Alert } from "../../types";
import { LoadingSpinner, EmptyState, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [unreadOnly, setUnreadOnly] = useState<boolean>(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { showToast } = useToast();

  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await alertService.list({
        severity: severityFilter,
        unread_only: unreadOnly,
      });
      if (res.success && res.data) {
        setAlerts(res.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load anomaly alerts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [severityFilter, unreadOnly]);

  const handleMarkRead = async (id: string) => {
    try {
      await alertService.markRead(id);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, is_read: true } : a))
      );
      showToast("Alert marked as read", "info");
    } catch (err: any) {
      showToast(err.message || "Failed to update alert", "error");
    }
  };

  const handleResolve = async (id: string) => {
    try {
      await alertService.resolve(id);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, is_resolved: true, is_read: true } : a))
      );
      showToast("Alert resolved successfully", "success");
    } catch (err: any) {
      showToast(err.message || "Failed to resolve alert", "error");
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            REAL-TIME ANOMALY DETECTIONS
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Alerts Center
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Automated notifications triggered by exponential velocity, volume surges, or inventory depletion.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-2 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
          >
            <option value="all">All Severities</option>
            <option value="Critical">Critical Only</option>
            <option value="Warning">Warnings Only</option>
            <option value="Info">Info Only</option>
          </select>

          <button
            onClick={() => setUnreadOnly(!unreadOnly)}
            className={`px-3 py-2 rounded-xl text-xs font-label-caps border transition-all ${
              unreadOnly
                ? "bg-primary/15 text-primary border-primary/40"
                : "bg-surface-container text-on-surface-variant border-outline-variant/30 hover:text-on-surface"
            }`}
          >
            {unreadOnly ? "Showing Unread" : "Show All"}
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Scanning anomaly detection logs..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchAlerts} />
      ) : alerts.length === 0 ? (
        <EmptyState
          title="No Alerts Found"
          description="All systems are operating normally with no active velocity anomalies matching your criteria."
          icon="check_circle"
        />
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-6 rounded-2xl border transition-all glass-card ${
                !alert.is_read
                  ? "bg-surface-container border-primary/30 shadow-[0_0_15px_rgba(223,115,40,0.1)]"
                  : "bg-surface-container-low border-outline-variant/15 opacity-80"
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                      alert.severity === "Critical"
                        ? "bg-error-container text-error"
                        : alert.severity === "Warning"
                        ? "bg-secondary-container text-secondary"
                        : "bg-surface-container-high text-primary"
                    }`}
                  >
                    <span className="material-symbols-outlined text-xl">
                      {alert.severity === "Critical"
                        ? "error"
                        : alert.severity === "Warning"
                        ? "warning"
                        : "info"}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`text-[10px] font-mono-data font-bold uppercase px-2 py-0.5 rounded border ${
                          alert.severity === "Critical"
                            ? "bg-error/10 text-error border-error/30"
                            : alert.severity === "Warning"
                            ? "bg-secondary/10 text-secondary border-secondary/30"
                            : "bg-primary/10 text-primary border-primary/30"
                        }`}
                      >
                        {alert.severity}
                      </span>
                      <span className="text-xs text-on-surface-variant font-mono-data">
                        {alert.category}
                      </span>
                      {alert.platform && (
                        <span className="text-xs text-on-surface-variant font-mono-data">
                          • {alert.platform}
                        </span>
                      )}
                      {alert.is_resolved && (
                        <span className="text-[10px] font-mono-data text-primary px-2 py-0.5 rounded bg-primary/15">
                          RESOLVED
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-on-surface">{alert.title}</h3>
                    <p className="text-xs text-on-surface-variant leading-relaxed">
                      {alert.description}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 self-end md:self-start shrink-0">
                  {alert.product_id && (
                    <Link
                      to={`/products/${alert.product_id}`}
                      className="px-3 py-1.5 rounded-lg bg-surface-container-high text-xs text-primary hover:bg-primary hover:text-on-primary font-semibold transition-colors flex items-center gap-1"
                    >
                      Inspect Product
                      <span className="material-symbols-outlined text-sm">open_in_new</span>
                    </Link>
                  )}

                  {!alert.is_read && (
                    <button
                      onClick={() => handleMarkRead(alert.id)}
                      className="px-3 py-1.5 rounded-lg bg-surface-container border border-outline-variant/30 text-xs text-on-surface-variant hover:text-on-surface transition-colors"
                    >
                      Mark Read
                    </button>
                  )}

                  {!alert.is_resolved && (
                    <button
                      onClick={() => handleResolve(alert.id)}
                      className="px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/30 text-xs text-primary hover:bg-primary hover:text-on-primary transition-colors font-semibold"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
