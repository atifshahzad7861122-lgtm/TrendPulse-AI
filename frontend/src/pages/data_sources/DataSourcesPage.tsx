import React, { useState, useEffect } from "react";
import { dataSourceService, devService } from "../../services/domainServices";
import type { DataSource, DataSourceConfigStatus } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const DataSourcesPage: React.FC = () => {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [configStatus, setConfigStatus] = useState<DataSourceConfigStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [resettingDev, setResettingDev] = useState(false);

  const { showToast } = useToast();

  const fetchSourcesAndConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sourcesRes, configRes] = await Promise.all([
        dataSourceService.list(),
        dataSourceService.getConfigStatus().catch(() => null)
      ]);

      if (sourcesRes.success && sourcesRes.data) {
        setSources(sourcesRes.data);
      }
      if (configRes && configRes.success && configRes.data) {
        setConfigStatus(configRes.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load data sources");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSourcesAndConfig();
  }, []);

  const handleToggleConnect = async (slug: string, currentStatus: string) => {
    setActionLoading(slug);
    try {
      if (currentStatus === "Connected") {
        const res = await dataSourceService.disconnect(slug);
        if (res.success && res.data) {
          setSources((prev) =>
            prev.map((s) => (s.slug === slug ? res.data : s))
          );
          showToast(`${res.data.name} disconnected`, "info");
        }
      } else {
        const res = await dataSourceService.connect(slug);
        if (res.success && res.data) {
          setSources((prev) =>
            prev.map((s) => (s.slug === slug ? res.data : s))
          );
          showToast(`${res.data.name} connected successfully`, "success");
        }
      }
    } catch (err: any) {
      showToast(err.message || "Action failed", "error");
    } finally {
      setActionLoading(null);
    }
  };

  const handleSyncSource = async (slug: string) => {
    setActionLoading(`sync_${slug}`);
    try {
      const res = await dataSourceService.sync(slug);
      if (res.success && res.data) {
        const d = res.data;
        const modeTag = d.is_live ? "LIVE" : "MOCK";
        showToast(
          `[${modeTag}] ${d.records_normalized} signals normalized, ${d.records_matched} matched, ${d.records_updated} products updated in ${d.duration_seconds}s.`,
          "success"
        );
        // Refresh sources
        const listRes = await dataSourceService.list();
        if (listRes.success && listRes.data) {
          setSources(listRes.data);
        }
      }
    } catch (err: any) {
      showToast(err.message || `Failed to sync ${slug}`, "error");
    } finally {
      setActionLoading(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    try {
      const res = await dataSourceService.syncAll();
      if (res.success && res.data) {
        showToast(
          `Ingested ${res.data.total_records} signals across active channels.`,
          "success"
        );
        const listRes = await dataSourceService.list();
        if (listRes.success && listRes.data) {
          setSources(listRes.data);
        }
      }
    } catch (err: any) {
      showToast(err.message || "Bulk sync failed", "error");
    } finally {
      setSyncingAll(false);
    }
  };

  const handleResetDevData = async () => {
    if (!window.confirm("Reset in-memory repositories to initial baseline seed state?")) return;
    setResettingDev(true);
    try {
      const res = await devService.resetData();
      if (res.success) {
        showToast("In-memory development data reset successfully", "info");
        await fetchSourcesAndConfig();
      }
    } catch (err: any) {
      showToast(err.message || "Reset failed", "error");
    } finally {
      setResettingDev(false);
    }
  };

  const isYouTubeLive = configStatus?.youtube.mode === "LIVE";

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            MULTI-PLATFORM INGESTION & INTELLIGENCE AGENTS
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Data Sources & Integrations
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Manage live scraping pipelines, signal deduplication, and entity resolution telemetry.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto">
          {configStatus?.environment === "development" && (
            <button
              onClick={handleResetDevData}
              disabled={resettingDev || loading}
              title="Reset in-memory repositories to baseline seed state"
              className="px-3 py-2.5 rounded-xl text-xs font-label-caps font-medium bg-surface-container border border-outline-variant/30 text-on-surface-variant hover:text-error hover:border-error/40 transition-all flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-sm">restart_alt</span>
              {resettingDev ? "Resetting..." : "Dev Reset"}
            </button>
          )}

          <button
            onClick={handleSyncAll}
            disabled={syncingAll || loading}
            className="px-4 py-2.5 rounded-xl text-xs font-label-caps font-semibold bg-surface-container border border-primary/30 text-primary hover:bg-primary/10 transition-all flex items-center gap-2 shadow-sm"
          >
            {syncingAll ? (
              <div className="w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            ) : (
              <span className="material-symbols-outlined text-base">sync</span>
            )}
            {syncingAll ? "Syncing Feeds..." : "Sync All Sources"}
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Checking ingestion connection statuses..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchSourcesAndConfig} />
      ) : (
        <div className="space-y-4">
          {sources.map((src) => {
            const isConnected = src.status === "Connected";
            const isToggling = actionLoading === src.slug;
            const isSyncing = actionLoading === `sync_${src.slug}`;
            const isYt = src.slug === "youtube";

            return (
              <div
                key={src.id}
                className={`p-6 rounded-2xl border transition-all glass-card flex flex-col md:flex-row md:items-center justify-between gap-6 ${
                  isConnected
                    ? "bg-surface-container-low border-primary/25"
                    : "bg-surface-container-low/60 border-outline-variant/15 opacity-80"
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-primary/10 border border-primary/25 flex items-center justify-center text-primary shrink-0">
                    <span className="material-symbols-outlined text-2xl">{src.icon}</span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <h3 className="text-base font-bold text-on-surface">{src.name}</h3>
                      <span
                        className={`text-[10px] font-mono-data uppercase px-2 py-0.5 rounded border ${
                          isConnected
                            ? "bg-primary/10 text-primary border-primary/30"
                            : "bg-surface-container text-on-surface-variant border-outline-variant/30"
                        }`}
                      >
                        {src.status}
                      </span>
                      {isYt && (
                        <span
                          className={`text-[9px] font-label-caps uppercase px-2 py-0.5 rounded border font-semibold flex items-center gap-1 ${
                            isYouTubeLive
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                              : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${isYouTubeLive ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
                          {isYouTubeLive ? "LIVE DATA API V3" : "OFFLINE FALLBACK"}
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-on-surface-variant max-w-xl leading-relaxed">
                      {src.description}
                    </p>

                    <div className="flex flex-wrap items-center gap-4 text-xs font-mono-data text-on-surface-variant pt-2">
                      <span>Sync: {src.sync_frequency}</span>
                      <span>•</span>
                      <span>Records: {src.records_synced.toLocaleString()}</span>
                      <span>•</span>
                      <span className={src.health_score > 80 ? "text-primary" : "text-on-surface-variant"}>
                        Health: {src.health_score}%
                      </span>
                      {isYt && configStatus && (
                        <>
                          <span>•</span>
                          <span>Region: {configStatus.youtube.region_code}</span>
                          <span>•</span>
                          <span>Batch: {configStatus.youtube.max_results}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end md:self-center shrink-0">
                  {isConnected && (
                    <button
                      onClick={() => handleSyncSource(src.slug)}
                      disabled={isSyncing || isToggling}
                      className="px-4 py-2.5 rounded-xl text-xs font-label-caps font-semibold bg-surface-container border border-outline-variant/30 text-on-surface hover:border-primary/40 hover:text-primary transition-all flex items-center gap-2"
                    >
                      {isSyncing ? (
                        <div className="w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <span className="material-symbols-outlined text-sm">refresh</span>
                      )}
                      {isSyncing ? "Ingesting..." : "Sync Now"}
                    </button>
                  )}

                  <button
                    onClick={() => handleToggleConnect(src.slug, src.status)}
                    disabled={isToggling || isSyncing}
                    className={`px-5 py-2.5 rounded-xl text-xs font-label-caps font-semibold transition-all flex items-center gap-2 ${
                      isConnected
                        ? "bg-surface-container border border-error/40 text-error hover:bg-error-container/20"
                        : "bg-primary text-on-primary hover:bg-primary-container shadow-[0_0_15px_rgba(255,182,141,0.2)]"
                    }`}
                  >
                    {isToggling ? (
                      <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    ) : isConnected ? (
                      "Disconnect"
                    ) : (
                      "Connect Source"
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
