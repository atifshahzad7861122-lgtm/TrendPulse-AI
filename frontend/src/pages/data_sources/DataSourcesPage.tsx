import React, { useState, useEffect } from "react";
import { dataSourceService, devService, scraperService } from "../../services/domainServices";
import type { DataSource, DataSourceConfigStatus, ScraperJobProgress, ScraperMarketplaceHealth, StartScraperJobPayload } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const DataSourcesPage: React.FC = () => {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [configStatus, setConfigStatus] = useState<DataSourceConfigStatus | null>(null);
  const [scraperHealth, setScraperHealth] = useState<ScraperMarketplaceHealth[]>([]);
  const [activeJobs, setActiveJobs] = useState<ScraperJobProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [resettingDev, setResettingDev] = useState(false);

  // Scraper Modal State
  const [isScraperModalOpen, setIsScraperModalOpen] = useState(false);
  const [crawlMode, setCrawlMode] = useState<"keyword" | "url">("keyword");
  const [scraperForm, setScraperForm] = useState<StartScraperJobPayload>({
    marketplace: "daraz",
    provider: "daraz_specialized",
    keyword: "wireless earbuds",
    url: "",
    category: "",
    max_products: 10,
    max_workers: 2,
    export_format: "json",
    dry_run: false
  });
  const [isLaunchingJob, setIsLaunchingJob] = useState(false);

  const { showToast } = useToast();

  const fetchSourcesAndConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sourcesRes, configRes, healthRes, jobsRes] = await Promise.all([
        dataSourceService.list().catch(() => ({ success: false, data: [] })),
        dataSourceService.getConfigStatus().catch(() => ({ success: false, data: null })),
        scraperService.getMarketplaceHealth().catch(() => ({ success: false, data: [] })),
        scraperService.listJobs({ limit: 10 }).catch(() => ({ success: false, data: { total: 0, jobs: [] } }))
      ]);

      if (sourcesRes.success && sourcesRes.data) {
        setSources(sourcesRes.data);
      }
      if (configRes.success && configRes.data) {
        setConfigStatus(configRes.data);
      }
      if (healthRes.success && healthRes.data) {
        setScraperHealth(healthRes.data);
      }
      if (jobsRes.success && jobsRes.data?.jobs) {
        setActiveJobs(jobsRes.data.jobs);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load data sources configuration");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSourcesAndConfig();

    const interval = setInterval(async () => {
      try {
        const [healthRes, jobsRes] = await Promise.all([
          scraperService.getMarketplaceHealth(),
          scraperService.listJobs({ limit: 10 })
        ]);
        if (healthRes.success && healthRes.data) setScraperHealth(healthRes.data);
        if (jobsRes.success && jobsRes.data?.jobs) setActiveJobs(jobsRes.data.jobs);
      } catch (e) {
        // Silent poll refresh
      }
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  const handleStartScraperJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLaunchingJob(true);
    try {
      const payload: StartScraperJobPayload = {
        marketplace: scraperForm.marketplace,
        provider: scraperForm.provider || "daraz_specialized",
        keyword: crawlMode === "keyword" ? (scraperForm.keyword || undefined) : undefined,
        keywords: crawlMode === "keyword" && scraperForm.keyword ? [scraperForm.keyword] : undefined,
        url: crawlMode === "url" ? (scraperForm.url || undefined) : undefined,
        urls: crawlMode === "url" && scraperForm.url ? [scraperForm.url] : undefined,
        category: scraperForm.category || undefined,
        max_products: Number(scraperForm.max_products) || 10,
        max_workers: Number(scraperForm.max_workers) || 2,
        export_format: scraperForm.export_format || "json",
        dry_run: Boolean(scraperForm.dry_run)
      };

      const res = await scraperService.startJob(payload);
      if (res.success && res.data) {
        showToast(`Scraper crawl job ${res.data.job_id} launched for ${res.data.marketplace.toUpperCase()} via ${payload.provider}!`, "success");
        setIsScraperModalOpen(false);
        const updatedJobs = await scraperService.listJobs({ limit: 10 });
        if (updatedJobs.success && updatedJobs.data?.jobs) {
          setActiveJobs(updatedJobs.data.jobs);
        }
      }
    } catch (err: any) {
      showToast(err.message || "Failed to launch scraper job", "error");
    } finally {
      setIsLaunchingJob(false);
    }
  };

  const handlePauseJob = async (jobId: string) => {
    try {
      const res = await scraperService.pauseJob(jobId);
      if (res.success) {
        showToast(`Job ${jobId} paused.`, "info");
        const updated = await scraperService.listJobs({ limit: 10 });
        if (updated.success && updated.data?.jobs) setActiveJobs(updated.data.jobs);
      }
    } catch (err: any) {
      showToast(err.message || "Failed to pause job", "error");
    }
  };

  const handleStopJob = async (jobId: string) => {
    try {
      const res = await scraperService.stopJob(jobId);
      if (res.success) {
        showToast(`Job ${jobId} stopped.`, "info");
        const updated = await scraperService.listJobs({ limit: 10 });
        if (updated.success && updated.data?.jobs) setActiveJobs(updated.data.jobs);
      }
    } catch (err: any) {
      showToast(err.message || "Failed to stop job", "error");
    }
  };

  const handleToggleConnect = async (slug: string, currentStatus: string) => {
    setActionLoading(slug);
    try {
      if (currentStatus === "Connected") {
        const res = await dataSourceService.disconnect(slug);
        if (res.success && res.data) {
          setSources((prev) => prev.map((s) => (s.slug === slug ? res.data : s)));
          showToast(`${res.data.name} disconnected`, "info");
        }
      } else {
        const res = await dataSourceService.connect(slug);
        if (res.success && res.data) {
          setSources((prev) => prev.map((s) => (s.slug === slug ? res.data : s)));
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
        const listRes = await dataSourceService.list();
        if (listRes.success && listRes.data) setSources(listRes.data);
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
        showToast(`Ingested ${res.data.total_records} signals across active channels.`, "success");
        const listRes = await dataSourceService.list();
        if (listRes.success && listRes.data) setSources(listRes.data);
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
            MULTI-PLATFORM INGESTION & UNIVERSAL SCRAPER INTEGRATION
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Data Sources & Ingestion Engines
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Manage live marketplace scraping pipelines (Daraz, Amazon, eBay, AliExpress, Shopify), signal deduplication, and challenge telemetry.
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
            onClick={() => setIsScraperModalOpen(true)}
            className="px-4 py-2.5 rounded-xl text-xs font-label-caps font-bold bg-primary text-on-primary hover:bg-primary-container shadow-[0_0_15px_rgba(255,182,141,0.25)] transition-all flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-base">travel_explore</span>
            Launch Universal Scraper
          </button>

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
            {syncingAll ? "Syncing Feeds..." : "Sync All Feeds"}
          </button>
        </div>
      </div>

      {/* Universal Scraper Marketplace Health & Control Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-xl">hub</span>
              Universal Scraper Ecosystem & Marketplace Health
            </h2>
            <p className="text-xs text-on-surface-variant mt-0.5">
              Autonomous multi-channel crawling with challenge detection, rate-limit governance, and persistent checkpoint queues.
            </p>
          </div>
        </div>

        {/* 5 Marketplace Health Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {[
            { key: "daraz", name: "Daraz PK", icon: "shopping_bag", color: "text-amber-400 border-amber-500/20 bg-amber-500/5" },
            { key: "amazon", name: "Amazon", icon: "local_shipping", color: "text-orange-400 border-orange-500/20 bg-orange-500/5" },
            { key: "ebay", name: "eBay", icon: "sell", color: "text-blue-400 border-blue-500/20 bg-blue-500/5" },
            { key: "aliexpress", name: "AliExpress", icon: "public", color: "text-red-400 border-red-500/20 bg-red-500/5" },
            { key: "shopify", name: "Shopify Stores", icon: "storefront", color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5" }
          ].map((m) => {
            const h = scraperHealth.find((item) => item.marketplace.toLowerCase() === m.key);
            const isHealthy = h?.status === "healthy";
            const isChallenged = h?.status === "challenged";
            return (
              <div key={m.key} className={`p-4 rounded-2xl border ${m.color} glass-card space-y-3`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-lg">{m.icon}</span>
                    <span className="text-xs font-bold text-on-surface">{m.name}</span>
                  </div>
                  <span className={`text-[9px] font-label-caps uppercase px-2 py-0.5 rounded border font-semibold flex items-center gap-1 ${
                    isHealthy
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                      : isChallenged
                      ? "bg-red-500/10 text-red-400 border-red-500/30"
                      : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${isHealthy ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
                    {h?.status?.toUpperCase() || "READY"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[10px] font-mono-data text-on-surface-variant pt-1 border-t border-outline-variant/10">
                  <div>
                    <span className="block text-[9px] text-on-surface-variant/60">SUCCESS</span>
                    <span className="text-on-surface font-bold">{h?.successful_requests || 0}</span>
                  </div>
                  <div>
                    <span className="block text-[9px] text-on-surface-variant/60">CHALLENGES</span>
                    <span className={h?.challenge_count ? "text-amber-400 font-bold" : "text-on-surface font-bold"}>
                      {h?.challenge_count || 0}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Active & Recent Crawl Jobs Monitor */}
        {activeJobs.length > 0 && (
          <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/20 glass-card space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-label-caps text-primary uppercase font-bold tracking-wider flex items-center gap-1.5">
                <span className="material-symbols-outlined text-base">monitoring</span>
                Live Crawl Job Queue & Execution Telemetry
              </h3>
              <span className="text-[10px] font-mono-data text-on-surface-variant">
                Auto-refreshing every 5s
              </span>
            </div>

            <div className="space-y-3">
              {activeJobs.slice(0, 3).map((job) => {
                const progressPct = job.target_count > 0 ? Math.min(100, Math.round((job.products_persisted / job.target_count) * 100)) : 0;
                const isRunning = job.status === "running";

                return (
                  <div key={job.job_id} className="p-3.5 rounded-xl bg-surface-container border border-outline-variant/20 space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono-data font-bold text-on-surface">{job.job_id}</span>
                        <span className="text-[10px] font-label-caps uppercase px-2 py-0.5 rounded bg-primary/10 border border-primary/20 text-primary font-bold">
                          {job.marketplace}
                        </span>
                        {job.provider && (
                          <span className="text-[10px] font-mono-data px-2 py-0.5 rounded bg-surface-container-high border border-outline-variant/30 text-on-surface-variant">
                            {job.provider}
                          </span>
                        )}
                        <span className={`text-[10px] font-mono-data uppercase px-2 py-0.5 rounded border font-semibold ${
                          job.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                            : job.status === "running"
                            ? "bg-primary/10 text-primary border-primary/30 animate-pulse"
                            : job.status === "failed"
                            ? "bg-red-500/10 text-red-400 border-red-500/30"
                            : job.status === "stopped" || job.status === "cancelled"
                            ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                            : job.status === "paused"
                            ? "bg-sky-500/10 text-sky-400 border-sky-500/30"
                            : "bg-surface-container text-on-surface-variant border-outline-variant/30"
                        }`}>
                          {job.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {isRunning && (
                          <>
                            <button
                              onClick={() => handlePauseJob(job.job_id)}
                              className="px-2.5 py-1 rounded-lg text-[10px] font-label-caps bg-surface-container-high border border-outline-variant/30 text-on-surface hover:text-amber-400"
                            >
                              Pause
                            </button>
                            <button
                              onClick={() => handleStopJob(job.job_id)}
                              className="px-2.5 py-1 rounded-lg text-[10px] font-label-caps bg-surface-container-high border border-outline-variant/30 text-on-surface hover:text-error"
                            >
                              Stop
                            </button>
                          </>
                        )}
                        <a
                          href={`/products?marketplace=${job.marketplace}`}
                          className="px-2.5 py-1 rounded-lg text-[10px] font-label-caps bg-primary/10 border border-primary/20 text-primary hover:bg-primary/20"
                        >
                          View Products
                        </a>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] font-mono-data text-on-surface-variant">
                        <span>Progress: {job.products_persisted} / {job.target_count} products ({progressPct}%)</span>
                        <span>Throughput: {job.current_throughput} items/s | Duration: {job.duration_seconds}s</span>
                      </div>
                      <div className="h-2 w-full bg-surface-container-highest rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
                            job.status === "failed"
                              ? "bg-red-500"
                              : job.status === "completed"
                              ? "bg-emerald-500"
                              : job.status === "stopped" || job.status === "cancelled"
                              ? "bg-amber-500"
                              : "bg-primary"
                          }`}
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                      {job.error_message && (
                        <p className="text-[11px] font-mono-data text-red-400 pt-0.5 flex items-center gap-1">
                          <span className="material-symbols-outlined text-xs">error</span>
                          {job.error_message}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Standard Integrations List */}
      {loading ? (
        <LoadingSpinner size="lg" label="Checking ingestion connection statuses..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchSourcesAndConfig} />
      ) : (
        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-surface-container-low border border-primary/20 flex items-start gap-3 text-xs glass-card">
            <span className="material-symbols-outlined text-primary text-lg shrink-0 mt-0.5">info</span>
            <div className="space-y-1">
              <p className="font-bold text-on-surface">
                Autonomous Data Governance & Real Provenance
              </p>
              <p className="text-on-surface-variant leading-relaxed">
                Every scraped product record is stored in raw format, validated through <strong>DataQualityAgent</strong> (Agent 1), and cross-referenced with <strong>EntityMatchingAgent</strong> (Agent 3) to form the unified cross-marketplace catalog.
              </p>
            </div>
          </div>

          {sources.map((src) => {
            const isYt = src.slug === "youtube";
            const isShopify = src.slug === "shopify";
            const isDaraz = src.slug === "daraz";
            const isConnected = src.status === "Connected";
            const isToggling = actionLoading === src.slug;
            const isSyncing = actionLoading === `sync_${src.slug}`;

            return (
              <div
                key={src.id}
                className={`p-6 rounded-2xl border transition-all glass-card flex flex-col md:flex-row md:items-center justify-between gap-6 ${
                  isYt || isShopify || isDaraz
                    ? "bg-surface-container-low border-primary/25"
                    : "bg-surface-container-low/60 border-outline-variant/15 opacity-90"
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-2xl border flex items-center justify-center shrink-0 ${
                    isYt
                      ? "bg-primary/10 border-primary/25 text-primary"
                      : isShopify
                      ? "bg-emerald-500/10 border-emerald-500/25 text-emerald-400"
                      : isDaraz
                      ? "bg-amber-500/10 border-amber-500/25 text-amber-400"
                      : "bg-surface-container border-outline-variant/30 text-on-surface-variant"
                  }`}>
                    <span className="material-symbols-outlined text-2xl">{src.icon}</span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-bold text-on-surface">{src.name}</h3>

                      {isYt ? (
                        <>
                          <span
                            className={`text-[10px] font-mono-data uppercase px-2 py-0.5 rounded border ${
                              isConnected
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                : "bg-surface-container text-on-surface-variant border-outline-variant/30"
                            }`}
                          >
                            {src.status}
                          </span>
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
                        </>
                      ) : isShopify ? (
                        <>
                          <span className="text-[10px] font-mono-data uppercase px-2 py-0.5 rounded border bg-emerald-500/10 text-emerald-400 border-emerald-500/30 font-semibold flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            LIVE DATA (5-TIER FAILOVER)
                          </span>
                          <span className="text-[9px] font-label-caps uppercase px-2 py-0.5 rounded border bg-surface-container text-on-surface-variant border-outline-variant/30">
                            AUTO-RECOVERY ACTIVE
                          </span>
                        </>
                      ) : isDaraz ? (
                        <>
                          <span className="text-[10px] font-mono-data uppercase px-2 py-0.5 rounded border bg-amber-500/10 text-amber-400 border-amber-500/30 font-semibold flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                            OFFICIAL OPEN PLATFORM + UNIVERSAL SCRAPER
                          </span>
                          <span className="text-[9px] font-label-caps uppercase px-2 py-0.5 rounded border bg-surface-container text-on-surface-variant border-outline-variant/30">
                            HTTPS TUNNEL READY
                          </span>
                        </>
                      ) : (
                        <span className="text-[10px] font-mono-data uppercase px-2 py-0.5 rounded border bg-amber-500/10 text-amber-400 border-amber-500/30 font-semibold">
                          COMING SOON
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
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end md:self-center shrink-0">
                  {isDaraz ? (
                    <div className="flex items-center gap-2">
                      <a
                        href="/platforms/daraz"
                        className="px-4 py-2.5 rounded-xl text-xs font-label-caps font-semibold bg-primary text-on-primary hover:bg-primary-container shadow-[0_0_15px_rgba(255,182,141,0.2)] transition-all flex items-center gap-1.5"
                      >
                        <span className="material-symbols-outlined text-sm">visibility</span>
                        View Daraz Catalog
                      </a>
                    </div>
                  ) : isShopify ? (
                    <div className="flex items-center gap-2">
                      <a
                        href="/platforms/shopify"
                        className="px-4 py-2.5 rounded-xl text-xs font-label-caps font-semibold bg-primary text-on-primary hover:bg-primary-container shadow-[0_0_15px_rgba(255,182,141,0.2)] transition-all flex items-center gap-1.5"
                      >
                        <span className="material-symbols-outlined text-sm">visibility</span>
                        View Shopify Catalog
                      </a>
                    </div>
                  ) : isYt ? (
                    <>
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
                    </>
                  ) : (
                    <div className="flex items-center gap-2">
                      <button
                        disabled
                        title="Live synchronization not available. Connector scheduled for future release."
                        className="px-4 py-2.5 rounded-xl text-xs font-label-caps font-medium bg-surface-container/50 border border-outline-variant/15 text-on-surface-variant/40 cursor-not-allowed flex items-center gap-1.5"
                      >
                        <span className="material-symbols-outlined text-sm">lock</span>
                        Sync Disabled
                      </button>

                      <span className="px-3 py-2 rounded-xl text-[11px] font-label-caps text-on-surface-variant/60 bg-surface-container border border-outline-variant/20">
                        Integration Planned
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Universal Scraper Launch Modal */}
      {isScraperModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-surface-container-low border border-primary/30 rounded-3xl max-w-lg w-full p-6 shadow-2xl space-y-5 glass-card animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-outline-variant/15 pb-4">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-2xl">travel_explore</span>
                <h3 className="text-lg font-bold text-on-surface">Launch Real Scraper Crawl Job</h3>
              </div>
              <button
                onClick={() => setIsScraperModalOpen(false)}
                className="p-1 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
              >
                <span className="material-symbols-outlined text-xl">close</span>
              </button>
            </div>

            <form onSubmit={handleStartScraperJob} className="space-y-4">
              {/* Marketplace Select */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-label-caps text-on-surface-variant">Marketplace</label>
                  <select
                    value={scraperForm.marketplace}
                    onChange={(e) => setScraperForm({ ...scraperForm, marketplace: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface text-sm focus:outline-none focus:border-primary"
                  >
                    <option value="daraz">Daraz PK</option>
                    <option value="amazon">Amazon</option>
                    <option value="ebay">eBay</option>
                    <option value="aliexpress">AliExpress</option>
                    <option value="shopify">Shopify Stores</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-label-caps text-on-surface-variant">Scraper Engine / Provider</label>
                  <select
                    value={scraperForm.provider}
                    onChange={(e) => setScraperForm({ ...scraperForm, provider: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface text-sm focus:outline-none focus:border-primary"
                  >
                    {scraperForm.marketplace === "daraz" ? (
                      <>
                        <option value="daraz_specialized">Specialized Daraz Engine (Deep Reviews & Variations)</option>
                        <option value="universal">Universal Orchestrator</option>
                        <option value="scrapegraphai">ScrapeGraphAI (AI Graph Extraction)</option>
                      </>
                    ) : (
                      <>
                        <option value="universal">Universal Multi-Marketplace Engine</option>
                        <option value="scrapegraphai">ScrapeGraphAI (AI Graph Extraction)</option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              {/* Mode Toggle: Search Keyword vs Direct Product URL */}
              <div className="space-y-1.5">
                <label className="text-xs font-label-caps text-on-surface-variant">Crawl Target Mode</label>
                <div className="flex rounded-xl bg-surface-container p-1 border border-outline-variant/30">
                  <button
                    type="button"
                    onClick={() => setCrawlMode("keyword")}
                    className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                      crawlMode === "keyword"
                        ? "bg-primary text-on-primary shadow-sm"
                        : "text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    Keyword Search Catalog
                  </button>
                  <button
                    type="button"
                    onClick={() => setCrawlMode("url")}
                    className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                      crawlMode === "url"
                        ? "bg-primary text-on-primary shadow-sm"
                        : "text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    Direct Product URL
                  </button>
                </div>
              </div>

              {crawlMode === "keyword" ? (
                <div className="space-y-1.5">
                  <label className="text-xs font-label-caps text-on-surface-variant">Search Keywords</label>
                  <input
                    type="text"
                    value={scraperForm.keyword}
                    onChange={(e) => setScraperForm({ ...scraperForm, keyword: e.target.value })}
                    placeholder="e.g. wireless earbuds, mechanical keyboard, smartwatch"
                    required
                    className="w-full px-3.5 py-2.5 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface text-sm focus:outline-none focus:border-primary"
                  />
                </div>
              ) : (
                <div className="space-y-1.5">
                  <label className="text-xs font-label-caps text-on-surface-variant">Product Direct URL</label>
                  <input
                    type="url"
                    value={scraperForm.url}
                    onChange={(e) => setScraperForm({ ...scraperForm, url: e.target.value })}
                    placeholder="https://www.daraz.pk/products/..."
                    required
                    className="w-full px-3.5 py-2.5 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface text-sm focus:outline-none focus:border-primary"
                  />
                </div>
              )}

              {/* Category (Optional) */}
              <div className="space-y-1.5">
                <label className="text-xs font-label-caps text-on-surface-variant">Category Filter (Optional)</label>
                <input
                  type="text"
                  value={scraperForm.category}
                  onChange={(e) => setScraperForm({ ...scraperForm, category: e.target.value })}
                  placeholder="e.g. Audio, Electronics, Wearables"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface text-sm focus:outline-none focus:border-primary"
                />
              </div>

              {/* Concurrency & Target Count */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-label-caps text-on-surface-variant">Target Products</label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={scraperForm.max_products}
                    onChange={(e) => setScraperForm({ ...scraperForm, max_products: parseInt(e.target.value) || 10 })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface text-sm focus:outline-none focus:border-primary"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-label-caps text-on-surface-variant">Worker Concurrency</label>
                  <input
                    type="number"
                    min={1}
                    max={8}
                    value={scraperForm.max_workers}
                    onChange={(e) => setScraperForm({ ...scraperForm, max_workers: parseInt(e.target.value) || 2 })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface text-sm focus:outline-none focus:border-primary"
                  />
                </div>
              </div>

              {/* Dry Run Checkbox */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="dryRunCheck"
                  checked={scraperForm.dry_run}
                  onChange={(e) => setScraperForm({ ...scraperForm, dry_run: e.target.checked })}
                  className="rounded bg-surface-container border-outline-variant text-primary focus:ring-primary"
                />
                <label htmlFor="dryRunCheck" className="text-xs text-on-surface-variant cursor-pointer">
                  Dry Run Mode (Plan task execution without sending network requests)
                </label>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-outline-variant/15">
                <button
                  type="button"
                  onClick={() => setIsScraperModalOpen(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-label-caps font-semibold bg-surface-container border border-outline-variant/30 text-on-surface hover:bg-surface-container-high"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLaunchingJob}
                  className="px-5 py-2.5 rounded-xl text-xs font-label-caps font-bold bg-primary text-on-primary hover:bg-primary-container shadow-md flex items-center gap-2"
                >
                  {isLaunchingJob ? (
                    <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <span className="material-symbols-outlined text-base">bolt</span>
                  )}
                  {isLaunchingJob ? "Scheduling..." : "Start Scraping Job"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
