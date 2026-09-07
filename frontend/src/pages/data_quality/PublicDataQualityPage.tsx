import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  XCircle,
  CheckCircle2,
  RefreshCw,
  Search,
  ExternalLink,
  Layers,
  Database,
  History,
  Info,
  BarChart3,
  Clock,
  Sparkles,
  Tag,
  Store,
  Star,
  X,
  ChevronLeft,
  ChevronRight,
  AlertCircle
} from "lucide-react";


import { publicDataQualityService } from "../../services/domainServices";
import type {
  PublicDataQualityItem,
  PublicDataQualityStatsResponse,
  PublicDataQualityHistoryResponse
} from "../../types";

export const PublicDataQualityPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"rejected" | "feed" | "analytics">("rejected");
  const [stats, setStats] = useState<PublicDataQualityStatsResponse | null>(null);
  const [items, setItems] = useState<PublicDataQualityItem[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPlatform, setSelectedPlatform] = useState("all");
  const [selectedProvider, setSelectedProvider] = useState("all");
  const [selectedClassification, setSelectedClassification] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [rejectionReasonFilter, setRejectionReasonFilter] = useState("all");
  const [scoreBandFilter, setScoreBandFilter] = useState("all");
  const [sortBy, setSortBy] = useState("validated_at_desc");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  // Detail Modal
  const [selectedProduct, setSelectedProduct] = useState<PublicDataQualityItem | null>(null);
  const [productHistory, setProductHistory] = useState<PublicDataQualityHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  // View Mode: Cards vs Table
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");

  const getScoreRange = (band: string): { min_score?: number; max_score?: number } => {
    switch (band) {
      case "high":
        return { min_score: 90, max_score: 100 };
      case "warnings":
        return { min_score: 70, max_score: 89.99 };
      case "review":
        return { min_score: 50, max_score: 69.99 };
      case "rejected":
        return { min_score: 0, max_score: 49.99 };
      default:
        return {};
    }
  };

  const fetchStats = async () => {
    try {
      const res = await publicDataQualityService.getPublicStats();
      setStats(res.data);
    } catch (err) {
      console.error("Failed to fetch public stats:", err);
    }
  };

  const fetchFeed = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const scoreRange = getScoreRange(scoreBandFilter);
      const queryParams = {
        platform: selectedPlatform !== "all" ? selectedPlatform : undefined,
        provider: selectedProvider !== "all" ? selectedProvider : undefined,
        category: categoryFilter.trim() || undefined,
        rejection_reason: rejectionReasonFilter !== "all" ? rejectionReasonFilter : undefined,
        search: searchQuery.trim() || undefined,
        min_score: scoreRange.min_score,
        max_score: scoreRange.max_score,
        sort_by: sortBy,
        page: currentPage,
        page_size: pageSize
      };

      if (activeTab === "rejected") {
        const res = await publicDataQualityService.getRejectedProducts(queryParams);
        setItems(res.data.items);
        setTotalItems(res.data.total);
      } else {
        const res = await publicDataQualityService.getValidationFeed({
          ...queryParams,
          classification: selectedClassification !== "all" ? selectedClassification : undefined
        });
        setItems(res.data.items);
        setTotalItems(res.data.total);
      }
    } catch (err) {
      console.error("Failed to fetch data quality feed:", err);
      setErrorMsg("Unable to load data-quality records.");
      setItems([]);
      setTotalItems(0);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [
    activeTab,
    selectedPlatform,
    selectedProvider,
    selectedClassification,
    categoryFilter,
    rejectionReasonFilter,
    searchQuery,
    scoreBandFilter,
    sortBy,
    currentPage
  ]);

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    fetchFeed();
  }, [fetchFeed]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchStats();
    fetchFeed();
  };

  const handleOpenDetail = async (item: PublicDataQualityItem) => {
    setSelectedProduct(item);
    setProductHistory(null);
    setHistoryLoading(true);
    try {
      const targetId = item.product_id || item.id;
      const res = await publicDataQualityService.getProductHistory(item.platform, targetId);
      setProductHistory(res.data);
    } catch (err) {
      console.error("Failed to load product evaluation history:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedProduct(null);
    setProductHistory(null);
  };

  const getScoreBadge = (score: number) => {
    if (score >= 90) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <ShieldCheck className="w-3 h-3" />
          High Quality ({score}/100)
        </span>
      );
    }
    if (score >= 70) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-3 h-3" />
          Warnings ({score}/100)
        </span>
      );
    }
    if (score >= 50) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
          <Info className="w-3 h-3" />
          Needs Review ({score}/100)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <XCircle className="w-3 h-3" />
        Rejected ({score}/100)
      </span>
    );
  };

  const getStatusBadge = (status: string, classification: string) => {
    const cls = (classification || "").toLowerCase();
    if (cls === "rejected") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-950/60 text-rose-300 border border-rose-600/40">
          <XCircle className="w-3.5 h-3.5 text-rose-400" />
          {status || "Rejected By Data Quality Checks"}
        </span>
      );
    }
    if (cls === "valid_with_warnings") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-950/60 text-amber-300 border border-amber-600/40">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          {status || "Real Data With Warnings"}
        </span>
      );
    }
    if (cls === "needs_review") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-cyan-950/60 text-cyan-300 border border-cyan-600/40">
          <Info className="w-3.5 h-3.5 text-cyan-400" />
          {status || "Needs Review"}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-950/60 text-emerald-300 border border-emerald-600/40">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        {status || "Real Data"}
      </span>
    );
  };

  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header Title & Actions */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  Data Quality Transparency
                </h1>
                <p className="text-sm text-slate-400 mt-0.5">
                  Public audit portal of raw marketplace records processed by TrendPulse AI Agent 1
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 transition-colors disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
              Refresh Feed
            </button>
          </div>
        </div>

        {/* Mandatory Trust Indicator Clarification Banner */}
        <div className="p-4 sm:p-5 rounded-xl border border-rose-900/40 bg-gradient-to-r from-rose-950/30 via-slate-900/60 to-slate-900/40 backdrop-blur-md flex items-start gap-3.5 shadow-lg">
          <ShieldAlert className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <p className="text-sm font-semibold text-rose-200">
              Public Audit &amp; Data Integrity Notice
            </p>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              &ldquo;TrendPulse displays real marketplace records, including records that fail data-quality validation. Rejected records are excluded from trusted intelligence calculations but remain visible for transparency.&rdquo;
            </p>
            <p className="text-xs text-slate-400">
              Raw marketplace listings are evaluated deterministically. Problematic entries are quarantined under{" "}
              <span className="font-semibold text-rose-300">Data Quality Issues</span> while preserving their full audit trail.
            </p>
          </div>
        </div>

        {/* 4 Classification Metrics Bar */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 p-4 sm:p-5 backdrop-blur-md">
            <div className="flex items-center justify-between text-rose-300 mb-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider">Rejected By Checks</span>
              <XCircle className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-rose-400">
              {stats ? stats.total_rejected.toLocaleString() : "--"}
            </div>
            <p className="text-xs text-rose-400/80 mt-1">
              {stats ? `${stats.rejection_rate}% of all raw records` : "Quarantined records"}
            </p>
          </div>

          <div className="rounded-xl border border-amber-900/40 bg-amber-950/20 p-4 sm:p-5 backdrop-blur-md">
            <div className="flex items-center justify-between text-amber-300 mb-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider">Real Data With Warnings</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-amber-400">
              {stats ? stats.total_warnings.toLocaleString() : "--"}
            </div>
            <p className="text-xs text-amber-400/80 mt-1">
              Minor anomalies flagged
            </p>
          </div>

          <div className="rounded-xl border border-cyan-900/40 bg-cyan-950/20 p-4 sm:p-5 backdrop-blur-md">
            <div className="flex items-center justify-between text-cyan-300 mb-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider">Needs Review</span>
              <Info className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-cyan-400">
              {stats ? (stats.total_inspected - stats.total_rejected - stats.total_warnings - stats.total_valid).toLocaleString() : "--"}
            </div>
            <p className="text-xs text-cyan-400/80 mt-1">
              Pending human/LLM verification
            </p>
          </div>

          <div className="rounded-xl border border-emerald-900/40 bg-emerald-950/20 p-4 sm:p-5 backdrop-blur-md">
            <div className="flex items-center justify-between text-emerald-300 mb-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider">Real Data (Clean)</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400">
              {stats ? stats.total_valid.toLocaleString() : "--"}
            </div>
            <p className="text-xs text-emerald-400/80 mt-1">
              {stats ? `${stats.clean_rate}% clean pass rate` : "Admitted to intelligence"}
            </p>
          </div>
        </div>

        {/* Quality Score Bands Explanation Bar */}
        <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs">
          <span className="font-semibold text-slate-300 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            Deterministic Score Tiers:
          </span>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
              <span className="text-slate-300 font-medium">90–100:</span>
              <span className="text-emerald-400 font-semibold">High Quality</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
              <span className="text-slate-300 font-medium">70–89:</span>
              <span className="text-amber-400 font-semibold">Warnings</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
              <span className="text-slate-300 font-medium">50–69:</span>
              <span className="text-cyan-400 font-semibold">Needs Review</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-400"></span>
              <span className="text-slate-300 font-medium">Below 50:</span>
              <span className="text-rose-400 font-semibold">Rejected</span>
            </div>
          </div>
        </div>

        {/* Tab Switcher & View Controls */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2 bg-slate-900/90 p-1 rounded-xl border border-slate-800 shrink-0">
            <button
              onClick={() => {
                setActiveTab("rejected");
                setCurrentPage(1);
              }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "rejected"
                  ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <XCircle className="w-4 h-4 text-rose-400" />
              Rejected Products (Data Quality Issues)
            </button>

            <button
              onClick={() => {
                setActiveTab("feed");
                setCurrentPage(1);
              }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "feed"
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Layers className="w-4 h-4 text-indigo-400" />
              Full Validation Audit Feed
            </button>

            <button
              onClick={() => {
                setActiveTab("analytics");
              }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "analytics"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              Diagnostics &amp; Analytics
            </button>
          </div>

          {activeTab !== "analytics" && (
            <div className="flex items-center gap-2 self-end lg:self-auto">
              <button
                onClick={() => setViewMode("cards")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                  viewMode === "cards"
                    ? "bg-slate-800 text-slate-100 border border-slate-700"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Cards View
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                  viewMode === "table"
                    ? "bg-slate-800 text-slate-100 border border-slate-700"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Table View
              </button>
            </div>
          )}
        </div>

        {/* Interactive Filter & Search Bar */}
        {activeTab !== "analytics" && (
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              {/* Search Bar */}
              <div className="relative flex-1 min-w-[240px]">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search by Product Name, Product ID, Category..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full pl-9 pr-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs placeholder:text-slate-500 focus:outline-none focus:border-rose-500 transition-colors"
                />
              </div>

              {/* Platform Filter */}
              <select
                value={selectedPlatform}
                onChange={(e) => {
                  setSelectedPlatform(e.target.value);
                  setCurrentPage(1);
                }}
                aria-label="Filter by Platform"
                className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:border-rose-500 cursor-pointer"
              >
                <option value="all">All Platforms</option>
                <option value="daraz">Daraz</option>
                <option value="shopify">Shopify</option>
                <option value="amazon">Amazon</option>
                <option value="ebay">eBay</option>
              </select>

              {/* Provider Filter */}
              <select
                value={selectedProvider}
                onChange={(e) => {
                  setSelectedProvider(e.target.value);
                  setCurrentPage(1);
                }}
                aria-label="Filter by Provider"
                className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:border-rose-500 cursor-pointer"
              >
                <option value="all">All Providers</option>
                <option value="direct">Direct Connector</option>
                <option value="daraz_official">Daraz Official API</option>
                <option value="shopify_official">Shopify Store API</option>
                <option value="amazon_partner">Amazon Partner</option>
              </select>

              {/* Category Filter */}
              <input
                type="text"
                placeholder="Filter by Category..."
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs placeholder:text-slate-500 focus:outline-none focus:border-rose-500 w-44"
              />

              {/* Rejection Reason Filter */}
              <select
                value={rejectionReasonFilter}
                onChange={(e) => {
                  setRejectionReasonFilter(e.target.value);
                  setCurrentPage(1);
                }}
                aria-label="Filter by Rejection Reason"
                className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:border-rose-500 cursor-pointer"
              >
                <option value="all">All Rejection Reasons</option>
                <option value="price">Price Violation</option>
                <option value="rating">Rating Violation</option>
                <option value="missing">Missing Required Field</option>
                <option value="spam">Spam / Keyword Stuffing</option>
                <option value="url">Malformed URL</option>
                <option value="title">Title Length / Quality</option>
              </select>


              {/* Status Filter for Feed */}
              {activeTab === "feed" && (
                <select
                  value={selectedClassification}
                  onChange={(e) => {
                    setSelectedClassification(e.target.value);
                    setCurrentPage(1);
                  }}
                  aria-label="Filter by Status"
                  className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:border-rose-500 cursor-pointer"
                >
                  <option value="all">All Statuses</option>
                  <option value="rejected">Rejected Only</option>
                  <option value="valid_with_warnings">Warnings Only</option>
                  <option value="valid">Valid Only</option>
                  <option value="needs_review">Needs Review</option>
                </select>
              )}

              {/* Quality Score Band Filter */}
              <select
                value={scoreBandFilter}
                onChange={(e) => {
                  setScoreBandFilter(e.target.value);
                  setCurrentPage(1);
                }}
                aria-label="Filter by Score Band"
                className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:border-rose-500 cursor-pointer"
              >
                <option value="all">All Quality Scores</option>
                <option value="high">High Quality (90–100)</option>
                <option value="warnings">Warnings (70–89)</option>
                <option value="review">Needs Review (50–69)</option>
                <option value="rejected">Rejected (&lt;50)</option>
              </select>

              {/* Sort By */}
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setCurrentPage(1);
                }}
                aria-label="Sort Order"
                className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:border-rose-500 cursor-pointer"
              >
                <option value="validated_at_desc">Newest Validated</option>
                <option value="validated_at_asc">Oldest Validated</option>
                <option value="score_asc">Score: Low to High</option>
                <option value="score_desc">Score: High to Low</option>
                <option value="price_asc">Price: Low to High</option>
                <option value="price_desc">Price: High to Low</option>
              </select>
            </div>
          </div>
        )}

        {/* Content Section */}
        {activeTab === "analytics" ? (
          /* Analytics & Breakdown Tab */
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Failure Reasons Breakdown */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
                <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-rose-400" />
                  Top Rejection Failure Reasons
                </h3>
                {stats && stats.top_rejection_reasons.length > 0 ? (
                  <div className="space-y-3">
                    {stats.top_rejection_reasons.map((r, i) => (
                      <div key={i} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-300 font-medium truncate max-w-[80%]">{r.reason}</span>
                          <span className="text-rose-400 font-semibold">{r.count} incidents</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-rose-500 rounded-full"
                            style={{
                              width: `${Math.min(100, Math.max(5, (r.count / Math.max(1, stats.total_rejected)) * 100))}%`
                            }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No rejection incidents recorded yet.</p>
                )}
              </div>

              {/* Platform Quality Health */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
                <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
                  <Store className="w-5 h-5 text-indigo-400" />
                  Platform Quality Distribution
                </h3>
                {stats && stats.platform_breakdown.length > 0 ? (
                  <div className="space-y-4">
                    {stats.platform_breakdown.map((p, i) => (
                      <div key={i} className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-lg space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-slate-200 capitalize">{p.platform}</span>
                          <span className="text-slate-400">{p.total} products evaluated</span>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-center text-xs">
                          <div className="p-1.5 bg-emerald-950/40 rounded border border-emerald-900/30">
                            <span className="block text-emerald-400 font-bold">{p.valid}</span>
                            <span className="text-[10px] text-emerald-400/70">Valid</span>
                          </div>
                          <div className="p-1.5 bg-amber-950/40 rounded border border-amber-900/30">
                            <span className="block text-amber-400 font-bold">{p.warnings}</span>
                            <span className="text-[10px] text-amber-400/70">Warnings</span>
                          </div>
                          <div className="p-1.5 bg-rose-950/40 rounded border border-rose-900/30">
                            <span className="block text-rose-400 font-bold">{p.rejected}</span>
                            <span className="text-[10px] text-rose-400/70">Rejected</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No platform breakdown data available.</p>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* Cards or Table Listing */
          <div className="space-y-4">
            {/* Loading State */}
            {loading && (
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((idx) => (
                  <div
                    key={idx}
                    className="p-5 rounded-xl bg-slate-900/40 border border-slate-800 animate-pulse flex flex-col md:flex-row gap-4"
                  >
                    <div className="w-16 h-16 bg-slate-800 rounded-lg shrink-0"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-slate-800 rounded w-1/3"></div>
                      <div className="h-3 bg-slate-800 rounded w-1/4"></div>
                      <div className="h-3 bg-slate-800 rounded w-1/2"></div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Error State */}
            {!loading && errorMsg && (
              <div className="p-8 text-center rounded-xl bg-rose-950/20 border border-rose-900/40 space-y-3">
                <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
                <h3 className="text-base font-semibold text-rose-300">{errorMsg}</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Unable to fetch validation records from the backend API.
                </p>
                <button
                  onClick={handleRefresh}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 rounded-lg text-xs font-semibold text-white transition-colors cursor-pointer"
                >
                  Retry Connection
                </button>
              </div>
            )}

            {/* Empty State */}
            {!loading && !errorMsg && items.length === 0 && (
              <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
                <ShieldCheck className="w-12 h-12 text-slate-600 mx-auto" />
                <h3 className="text-base font-semibold text-slate-300">
                  {activeTab === "rejected"
                    ? "No products have been rejected by the current data-quality checks."
                    : "No validation records match your current filters."}
                </h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  All processed marketplace records in this view adhere to quality thresholds or no records were returned by the backend.
                </p>
              </div>
            )}

            {/* Cards View */}
            {!loading && !errorMsg && items.length > 0 && viewMode === "cards" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-all p-5 flex flex-col justify-between space-y-4 shadow-sm"
                  >
                    <div className="flex items-start gap-4">
                      {/* Product Image */}
                      <div className="w-20 h-20 rounded-lg bg-slate-950 border border-slate-800 overflow-hidden shrink-0 flex items-center justify-center">
                        {item.image ? (
                          <img
                            src={item.image}
                            alt={item.product_name}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                        ) : (
                          <Database className="w-7 h-7 text-slate-600" />
                        )}
                      </div>

                      {/* Product Overview */}
                      <div className="flex-1 min-w-0 space-y-1.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-slate-800 text-slate-200 border border-slate-700">
                            {item.platform}
                          </span>
                          {item.provider && (
                            <span className="text-[11px] text-slate-400 font-mono">
                              via {item.provider}
                            </span>
                          )}
                          {item.data_quality_category && (
                            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-950/60 text-rose-300 border border-rose-800/40">
                              {item.data_quality_category}
                            </span>
                          )}
                        </div>

                        <h4 className="text-sm font-bold text-white truncate" title={item.product_name}>
                          {item.product_name}
                        </h4>

                        {/* Categories */}
                        <div className="text-xs text-slate-400 space-y-0.5">
                          <div>
                            <span className="text-slate-500">Category: </span>
                            <span className="text-slate-300 font-medium">
                              {item.original_category ? `${item.original_category} → ` : ""}
                              {item.normalized_category}
                            </span>
                          </div>
                        </div>

                        {/* Price, Currency, Rating, Reviews */}
                        <div className="flex items-center gap-3 text-xs pt-1">
                          <span className="font-semibold text-slate-200">
                            {item.price !== null && item.price !== undefined
                              ? `${item.currency} ${item.price.toLocaleString()}`
                              : "No Price"}
                          </span>
                          <span className="text-slate-600">|</span>
                          <span className="flex items-center gap-1 text-amber-400">
                            <Star className="w-3 h-3 fill-amber-400" />
                            {item.rating !== null && item.rating !== undefined ? item.rating : "0.0"}
                          </span>
                          <span className="text-slate-500">({item.review_count} reviews)</span>
                        </div>
                      </div>
                    </div>

                    {/* Quality Badges & Rejection Reasons */}
                    <div className="space-y-2 border-t border-slate-800/80 pt-3">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        {getStatusBadge(item.public_status, item.classification)}
                        {getScoreBadge(item.quality_score)}
                      </div>

                      {/* Primary Rejection Reasons */}
                      {item.rejection_reasons && item.rejection_reasons.length > 0 && (
                        <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-900/30 text-xs text-rose-300 space-y-1">
                          <span className="font-semibold block text-rose-200">Failure Diagnostics:</span>
                          <ul className="list-disc list-inside space-y-0.5">
                            {item.rejection_reasons.map((r, i) => (
                              <li key={i} className="truncate">{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Footer Actions */}
                    <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-800/40">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(item.last_validated_time).toLocaleString()}
                      </span>

                      <div className="flex items-center gap-2">
                        {item.product_url && (
                          <a
                            href={item.product_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium"
                          >
                            View Original Product
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                        <button
                          onClick={() => handleOpenDetail(item)}
                          className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-medium transition-colors cursor-pointer"
                        >
                          Inspect Record
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Table View */}
            {!loading && !errorMsg && items.length > 0 && viewMode === "table" && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[11px] font-bold tracking-wider">
                      <tr>
                        <th className="px-4 py-3.5">Product</th>
                        <th className="px-4 py-3.5">Platform &amp; Provider</th>
                        <th className="px-4 py-3.5">Category</th>
                        <th className="px-4 py-3.5">Price &amp; Currency</th>
                        <th className="px-4 py-3.5">Rating &amp; Reviews</th>
                        <th className="px-4 py-3.5">Quality Score</th>
                        <th className="px-4 py-3.5">Status</th>
                        <th className="px-4 py-3.5">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {items.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-900/40 transition-colors">
                          <td className="px-4 py-3 max-w-[220px]">
                            <div className="flex items-center gap-2.5">
                              <div className="w-10 h-10 rounded bg-slate-950 border border-slate-800 overflow-hidden shrink-0 flex items-center justify-center">
                                {item.image ? (
                                  <img src={item.image} alt="" className="w-full h-full object-cover" />
                                ) : (
                                  <Database className="w-4 h-4 text-slate-600" />
                                )}
                              </div>
                              <div className="truncate">
                                <span className="font-bold text-slate-200 block truncate" title={item.product_name}>
                                  {item.product_name}
                                </span>
                                <span className="text-[10px] text-slate-500 font-mono">
                                  ID: {item.product_id || item.id}
                                </span>
                              </div>
                            </div>
                          </td>

                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="font-semibold text-slate-200 capitalize block">{item.platform}</span>
                            <span className="text-[10px] text-slate-500 font-mono">{item.provider}</span>
                          </td>

                          <td className="px-4 py-3 max-w-[180px]">
                            <span className="text-slate-300 block truncate" title={item.normalized_category}>
                              {item.normalized_category}
                            </span>
                            {item.original_category && (
                              <span className="text-[10px] text-slate-500 block truncate" title={item.original_category}>
                                Raw: {item.original_category}
                              </span>
                            )}
                          </td>

                          <td className="px-4 py-3 whitespace-nowrap font-mono font-semibold text-slate-200">
                            {item.price !== null && item.price !== undefined
                              ? `${item.currency} ${item.price.toLocaleString()}`
                              : "--"}
                          </td>

                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="text-amber-400 font-semibold">{item.rating ?? 0.0} ★</span>
                            <span className="text-slate-500 text-[10px] block">{item.review_count} reviews</span>
                          </td>

                          <td className="px-4 py-3 whitespace-nowrap">
                            {getScoreBadge(item.quality_score)}
                          </td>

                          <td className="px-4 py-3 whitespace-nowrap">
                            {getStatusBadge(item.public_status, item.classification)}
                          </td>

                          <td className="px-4 py-3 whitespace-nowrap">
                            <button
                              onClick={() => handleOpenDetail(item)}
                              className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-medium transition-colors cursor-pointer"
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Pagination Controls */}
            {!loading && totalItems > 0 && (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-400">
                <div>
                  Showing <span className="font-semibold text-slate-200">{Math.min(totalItems, (currentPage - 1) * pageSize + 1)}</span> to{" "}
                  <span className="font-semibold text-slate-200">{Math.min(totalItems, currentPage * pageSize)}</span> of{" "}
                  <span className="font-semibold text-slate-200">{totalItems.toLocaleString()}</span> records
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>

                  <span className="px-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-semibold">
                    {currentPage} / {totalPages}
                  </span>

                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage >= totalPages}
                    className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Detailed Product Inspection Modal */}
        {selectedProduct && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
            <div className="relative w-full max-w-3xl bg-slate-950 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
              {/* Modal Header */}
              <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {getStatusBadge(selectedProduct.public_status, selectedProduct.classification)}
                    {getScoreBadge(selectedProduct.quality_score)}
                    <span className="px-2 py-0.5 rounded text-xs font-bold uppercase bg-slate-800 text-slate-300">
                      {selectedProduct.platform}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-1">
                    {selectedProduct.product_name}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Product ID: {selectedProduct.product_id || selectedProduct.id} | Provider: {selectedProduct.provider}
                  </p>
                </div>

                <button
                  onClick={handleCloseDetail}
                  className="p-1.5 rounded-lg bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Product Info Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800/80">
                  <span className="text-[11px] text-slate-400 block font-medium">Price &amp; Currency</span>
                  <span className="text-sm font-bold text-slate-100 font-mono">
                    {selectedProduct.price !== null && selectedProduct.price !== undefined
                      ? `${selectedProduct.currency} ${selectedProduct.price.toLocaleString()}`
                      : "Missing"}
                  </span>
                </div>

                <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800/80">
                  <span className="text-[11px] text-slate-400 block font-medium">Rating &amp; Reviews</span>
                  <span className="text-sm font-bold text-amber-400">
                    {selectedProduct.rating ?? 0.0} ★ ({selectedProduct.review_count})
                  </span>
                </div>

                <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800/80">
                  <span className="text-[11px] text-slate-400 block font-medium">Stock Availability</span>
                  <span className={`text-sm font-bold ${selectedProduct.availability ? "text-emerald-400" : "text-rose-400"}`}>
                    {selectedProduct.availability ? "In Stock" : "Out of Stock"}
                  </span>
                </div>

                <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800/80">
                  <span className="text-[11px] text-slate-400 block font-medium">Last Validated</span>
                  <span className="text-xs font-semibold text-slate-300 block">
                    {new Date(selectedProduct.last_validated_time).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {/* Category Inspection */}
              <div className="p-4 bg-slate-900/40 rounded-xl border border-slate-800 space-y-2 text-xs">
                <h4 className="font-semibold text-slate-200 flex items-center gap-2">
                  <Tag className="w-4 h-4 text-indigo-400" />
                  Category Attribution
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <span className="text-slate-500 block">Raw Marketplace Category:</span>
                    <span className="text-slate-300 font-medium">
                      {selectedProduct.original_category || "(None provided by marketplace)"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Normalized Category:</span>
                    <span className="text-slate-300 font-semibold">
                      {selectedProduct.normalized_category}
                    </span>
                  </div>
                </div>
              </div>

              {/* Diagnostic Issues & Violations */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-rose-300 flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  Rule Violations &amp; Quality Penalties
                </h4>

                {selectedProduct.issues && selectedProduct.issues.length > 0 ? (
                  <div className="space-y-2">
                    {selectedProduct.issues.map((iss, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-lg bg-rose-950/30 border border-rose-900/40 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-rose-300 font-mono">{iss.rule_name}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-900/60 text-rose-200">
                            -{iss.penalty_score} pts ({iss.severity})
                          </span>
                        </div>
                        <p className="text-slate-300">{iss.message}</p>
                        {iss.observed_value !== undefined && iss.observed_value !== null && (
                          <p className="text-[11px] text-slate-500 font-mono">
                            Observed Value: {JSON.stringify(iss.observed_value)}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No critical rule violations recorded.</p>
                )}
              </div>

              {/* Field Classification Diagnostics */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="font-semibold text-rose-300 block mb-1">Missing Fields:</span>
                  {selectedProduct.missing_fields && selectedProduct.missing_fields.length > 0 ? (
                    <ul className="list-disc list-inside space-y-0.5 text-slate-300">
                      {selectedProduct.missing_fields.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500">None</span>
                  )}
                </div>

                <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="font-semibold text-amber-300 block mb-1">Invalid Fields:</span>
                  {selectedProduct.invalid_fields && selectedProduct.invalid_fields.length > 0 ? (
                    <ul className="list-disc list-inside space-y-0.5 text-slate-300">
                      {selectedProduct.invalid_fields.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500">None</span>
                  )}
                </div>

                <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="font-semibold text-cyan-300 block mb-1">Suspicious Fields:</span>
                  {selectedProduct.suspicious_fields && selectedProduct.suspicious_fields.length > 0 ? (
                    <ul className="list-disc list-inside space-y-0.5 text-slate-300">
                      {selectedProduct.suspicious_fields.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500">None</span>
                  )}
                </div>
              </div>

              {/* Evaluation History Lineage */}
              <div className="space-y-2 border-t border-slate-800 pt-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <History className="w-4 h-4 text-indigo-400" />
                  Historical Evaluations Lineage
                </h4>

                {historyLoading ? (
                  <div className="p-4 text-center text-xs text-slate-500">Loading audit history...</div>
                ) : productHistory && productHistory.history.length > 0 ? (
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {productHistory.history.map((hist, i) => (
                      <div
                        key={hist.id || i}
                        className="p-2.5 rounded bg-slate-900/50 border border-slate-800/80 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-slate-400">{new Date(hist.last_validated_time).toLocaleString()}</span>
                          {getStatusBadge(hist.public_status, hist.classification)}
                        </div>
                        <span className="font-bold text-slate-300">{hist.quality_score}/100</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">Single evaluation run recorded for this product.</p>
                )}
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-between border-t border-slate-800 pt-4">
                {selectedProduct.product_url ? (
                  <a
                    href={selectedProduct.product_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors shadow-sm"
                  >
                    View Original Product
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                ) : (
                  <span className="text-xs text-slate-500 italic">No external URL provided by marketplace</span>
                )}

                <button
                  onClick={handleCloseDetail}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors cursor-pointer"
                >
                  Close Inspection
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
