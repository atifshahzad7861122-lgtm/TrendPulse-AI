import React, { useState, useEffect } from "react";
import { platformService } from "../../services/domainServices";
import type { PlatformMetrics } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";

export const PlatformsPage: React.FC = () => {
  const [platforms, setPlatforms] = useState<PlatformMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlatforms = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await platformService.list();
      if (res.success && res.data) {
        setPlatforms(res.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load platform metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlatforms();
  }, []);

  const getProvenanceLabel = (p: PlatformMetrics) => {
    if (p.status === "Connected" || p.status === "Live") {
      if (p.slug === "youtube") {
        return `${p.total_signals.toLocaleString()} Live Ingested Signals (API v3)`;
      }
      if (p.slug === "daraz") {
        return `${p.total_signals.toLocaleString()} Persisted Scraped Listings (Marketplace)`;
      }
      return `${p.total_signals.toLocaleString()} Active Verified Signals`;
    }
    if (p.status === "Insufficient Data") {
      return "0 Persisted Observations (Data Insufficient)";
    }
    return "Connector in Development (No Live Stream)";
  };

  const isLiveOrConnected = (status: string) => status === "Connected" || status === "Live";

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            CHANNEL PULSE & PROVENANCE
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Platform Intelligence
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Verified social velocity, marketplace search volumes, and catalog spikes across connected data pipelines.
          </p>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Ingesting verified channel signals..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchPlatforms} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {platforms.map((p) => {
            const isConnected = isLiveOrConnected(p.status);
            const isInsufficient = p.status === "Insufficient Data";

            return (
              <div
                key={p.id}
                className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card space-y-6 flex flex-col justify-between"
              >
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-2xl">{p.icon}</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-on-surface">{p.name}</h3>
                        <span className="text-xs text-on-surface-variant font-mono-data">
                          {getProvenanceLabel(p)}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {isConnected ? (
                        <span className="text-xs font-label-caps uppercase px-3 py-1 rounded-full border bg-emerald-500/10 text-emerald-400 border-emerald-500/30 font-semibold flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          CONNECTED
                        </span>
                      ) : isInsufficient ? (
                        <span className="text-xs font-label-caps uppercase px-3 py-1 rounded-full border bg-amber-500/10 text-amber-400 border-amber-500/30 font-semibold">
                          INSUFFICIENT DATA
                        </span>
                      ) : (
                        <span className="text-xs font-label-caps uppercase px-3 py-1 rounded-full border bg-surface-container-high text-on-surface-variant border-outline-variant/40 font-semibold">
                          COMING SOON
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Stats Bar */}
                  <div className="grid grid-cols-3 gap-3 p-4 rounded-xl bg-surface-container border border-outline-variant/15 text-center">
                    <div>
                      <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                        Active Trends
                      </span>
                      <p className="text-base font-mono-data font-bold text-on-surface mt-1">
                        {isConnected ? p.active_trends : "—"}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                        WoW Growth
                      </span>
                      <p className={`text-base font-mono-data font-bold mt-1 ${isConnected ? "text-primary" : "text-on-surface-variant"}`}>
                        {isConnected ? (p.velocity_growth > 0 ? `+${p.velocity_growth}%` : `${p.velocity_growth}%`) : "—"}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] font-label-caps text-on-surface-variant uppercase">
                        Market Share
                      </span>
                      <p className="text-base font-mono-data font-bold text-on-surface mt-1">
                        {isConnected ? `${p.market_share}%` : "—"}
                      </p>
                    </div>
                  </div>

                  {/* Signals & Spikes List */}
                  <div>
                    <span className="text-xs font-label-caps text-on-surface-variant uppercase tracking-wider block mb-2">
                      {p.slug === "daraz"
                        ? "Top Persisted Marketplace Products"
                        : "Recent High-Velocity Hashtags & Keywords"}
                    </span>
                    {isConnected && p.recent_spikes.length > 0 ? (
                      <div className="space-y-2">
                        {p.recent_spikes.map((sp, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-2.5 rounded-lg bg-surface-container border border-outline-variant/10 text-xs font-mono-data"
                          >
                            <span className="text-on-surface font-semibold truncate max-w-[200px]" title={sp.hashtag}>
                              {sp.hashtag}
                            </span>
                            <div className="flex items-center gap-3">
                              <span className="text-on-surface-variant">{sp.signals}</span>
                              <span className="text-primary font-bold">{sp.growth}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : isInsufficient ? (
                      <div className="p-3 rounded-lg bg-surface-container border border-outline-variant/10 text-xs text-on-surface-variant flex items-center gap-2">
                        <span className="material-symbols-outlined text-base text-amber-400">hourglass_empty</span>
                        <span>No scrape observations recorded yet. Run a scraper job from Data Sources.</span>
                      </div>
                    ) : (
                      <div className="p-3 rounded-lg bg-surface-container border border-outline-variant/10 text-xs text-on-surface-variant flex items-center gap-2">
                        <span className="material-symbols-outlined text-base text-primary/70">lock_clock</span>
                        <span>No live data available — Direct integration planned for future release.</span>
                      </div>
                    )}
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
