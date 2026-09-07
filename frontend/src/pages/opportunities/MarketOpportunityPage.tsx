import React, { useState, useEffect, useCallback } from "react";
import {
  TrendingUp,
  Search,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Layers,
  Award,
  Zap,
  ShoppingBag,
  Sliders,
  DollarSign,
  Star,
  Check,
  Globe,
  Compass,
  ShieldAlert,
  Target
} from "lucide-react";
import {
  marketOpportunityService,
  intelligenceService
} from "../../services/domainServices";
import type {
  MarketOpportunityItem,
  MarketOpportunityCandidateItem,
  MarketOpportunitySummaryItem,
  AgentMarketOpportunityStatsItem,
  UnifiedProduct
} from "../../types";

export const MarketOpportunityPage: React.FC = () => {
  // State
  const [activeTab, setActiveTab] = useState<"feed" | "analyzer" | "candidates">("feed");
  const [stats, setStats] = useState<AgentMarketOpportunityStatsItem | null>(null);
  const [opportunities, setOpportunities] = useState<MarketOpportunityItem[]>([]);
  const [candidates, setCandidates] = useState<MarketOpportunityCandidateItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filters
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");
  const [minScore, setMinScore] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Product Analyzer State
  const [catalogProducts, setCatalogProducts] = useState<UnifiedProduct[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [productSummary, setProductSummary] = useState<MarketOpportunitySummaryItem | null>(null);
  const [analyzingProduct, setAnalyzingProduct] = useState<boolean>(false);

  // Load Data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, oppsRes, candsRes, catalogRes] = await Promise.all([
        marketOpportunityService.getStats(),
        marketOpportunityService.list({
          opportunity_type: selectedType !== "all" ? selectedType : undefined,
          category: selectedCategory !== "all" ? selectedCategory : undefined,
          platform: selectedPlatform !== "all" ? selectedPlatform : undefined,
          min_score: minScore > 0 ? minScore : undefined,
          search: searchQuery || undefined,
          limit: 50
        }),
        marketOpportunityService.listCandidates("pending"),
        intelligenceService.listUnifiedProducts({ limit: 50 })
      ]);

      if (statsRes.success && statsRes.data) setStats(statsRes.data);
      if (oppsRes.success && oppsRes.data) setOpportunities(oppsRes.data.items);
      if (candsRes.success && candsRes.data) setCandidates(candsRes.data.items);
      if (catalogRes.success && catalogRes.data) {
        setCatalogProducts(catalogRes.data.items);
        if (!selectedProductId && catalogRes.data.items.length > 0) {
          setSelectedProductId(catalogRes.data.items[0].unified_product_id);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load market opportunity intelligence");
    } finally {
      setLoading(false);
    }
  }, [selectedType, selectedCategory, selectedPlatform, minScore, searchQuery, selectedProductId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Analyze single product
  const handleAnalyzeProduct = async (prodId: string) => {
    if (!prodId) return;
    setAnalyzingProduct(true);
    setError(null);
    try {
      const res = await marketOpportunityService.analyzeProduct(prodId, false);
      if (res.success && res.data) {
        setProductSummary(res.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to generate market opportunities for product");
    } finally {
      setAnalyzingProduct(false);
    }
  };

  useEffect(() => {
    if (selectedProductId && activeTab === "analyzer") {
      handleAnalyzeProduct(selectedProductId);
    }
  }, [selectedProductId, activeTab]);

  // Resolve Candidate
  const handleResolveCandidate = async (candidateId: string, status: "approved" | "dismissed" | "rejected") => {
    try {
      const res = await marketOpportunityService.resolveCandidate(candidateId, { status });
      if (res.success) {
        setActionSuccess(`Candidate ${status === "approved" ? "approved" : "dismissed"} successfully`);
        setTimeout(() => setActionSuccess(null), 3000);
        fetchData();
      }
    } catch (err: any) {
      setError(err.message || "Failed to resolve candidate");
    }
  };

  const getOpportunityTypeBadge = (type: string) => {
    switch (type) {
      case "product_gap":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><ShoppingBag className="w-3.5 h-3.5" /> Product Gap</span>;
      case "cross_platform_gap":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20"><Layers className="w-3.5 h-3.5" /> Cross-Platform Gap</span>;
      case "price_opportunity":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"><DollarSign className="w-3.5 h-3.5" /> Price Opportunity</span>;
      case "competitive_gap":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"><Target className="w-3.5 h-3.5" /> Competitive Gap</span>;
      case "rising_product":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20"><TrendingUp className="w-3.5 h-3.5" /> Rising Product</span>;
      case "product_launch_opportunity":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20"><Zap className="w-3.5 h-3.5" /> Launch Opportunity</span>;
      case "marketplace_expansion":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20"><Globe className="w-3.5 h-3.5" /> Market Expansion</span>;
      case "underserved_category":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20"><Award className="w-3.5 h-3.5" /> Underserved</span>;
      case "quality_gap":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-400 border border-orange-500/20"><Star className="w-3.5 h-3.5" /> Quality Gap</span>;
      default:
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/20">{type.replace(/_/g, " ")}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 lg:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-br from-emerald-500/20 via-cyan-500/20 to-indigo-500/20 border border-emerald-500/30 rounded-xl">
              <Compass className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                Market Opportunity Intelligence
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                AI Agent 07: Evidence-grounded product gaps, cross-platform opportunities & market expansion avenues
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchData()}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg text-sm transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Notifications */}
      {actionSuccess && (
        <div className="p-4 bg-emerald-950/40 border border-emerald-500/30 rounded-xl flex items-center gap-3 text-emerald-300 text-sm">
          <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          {actionSuccess}
        </div>
      )}
      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-300 text-sm">
          <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Opps</span>
            <Compass className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {stats?.active_opportunities_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Live evidence picks</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">High Conf</span>
            <CheckCircle className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 mt-2">
            {stats?.high_confidence_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Confidence ≥ 90%</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">High Score</span>
            <Award className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">
            {stats?.high_score_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Score ≥ 80/100</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Pending Review</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-2">
            {stats?.pending_review_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Human-in-the-loop</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Confirmed</span>
            <Check className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-indigo-400 mt-2">
            {stats?.confirmed_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Operator approved</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Dismissed</span>
            <XCircle className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-400 mt-2">
            {stats?.dismissed_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Filtered candidates</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab("feed")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "feed"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Compass className="w-4 h-4" />
          Opportunities Feed ({opportunities.length})
        </button>

        <button
          onClick={() => setActiveTab("analyzer")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "analyzer"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sliders className="w-4 h-4" />
          Product Opportunity Analyzer
        </button>

        <button
          onClick={() => setActiveTab("candidates")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "candidates"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Candidate Review Queue ({candidates.length})
        </button>
      </div>

      {/* TAB 1: Opportunities Feed */}
      {activeTab === "feed" && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  placeholder="Search opportunities..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 w-64"
                />
              </div>

              {/* Type Filter */}
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="all">All Types</option>
                <option value="product_gap">Product Gap</option>
                <option value="cross_platform_gap">Cross-Platform Gap</option>
                <option value="price_opportunity">Price Opportunity</option>
                <option value="competitive_gap">Competitive Gap</option>
                <option value="rising_product">Rising Product</option>
                <option value="product_launch_opportunity">Launch Opportunity</option>
                <option value="marketplace_expansion">Marketplace Expansion</option>
                <option value="underserved_category">Underserved Category</option>
                <option value="quality_gap">Quality Gap</option>
                <option value="availability_opportunity">Availability</option>
              </select>

              {/* Category Filter */}
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="all">All Categories</option>
                <option value="Audio">Audio</option>
                <option value="Wearables">Wearables</option>
                <option value="Cameras">Cameras</option>
                <option value="Electronics">Electronics</option>
              </select>

              {/* Platform Filter */}
              <select
                value={selectedPlatform}
                onChange={(e) => setSelectedPlatform(e.target.value)}
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="all">All Platforms</option>
                <option value="Daraz">Daraz</option>
                <option value="Shopify">Shopify</option>
              </select>

              {/* Min Score Filter */}
              <select
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value={0}>Min Score: Any</option>
                <option value={60}>Score ≥ 60</option>
                <option value={75}>Score ≥ 75</option>
                <option value={85}>Score ≥ 85</option>
              </select>
            </div>

            <div className="text-xs text-slate-500 font-mono">
              Showing {opportunities.length} opportunities
            </div>
          </div>

          {/* Cards Grid */}
          {loading ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-2xl">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-emerald-400" />
              Loading opportunities...
            </div>
          ) : opportunities.length === 0 ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-2xl">
              <Compass className="w-8 h-8 mx-auto mb-3 text-slate-600" />
              No market opportunities match the current filters.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {opportunities.map((opp) => (
                <div
                  key={opp.id}
                  className="p-5 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-emerald-500/40 rounded-2xl transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex justify-between items-start gap-2 mb-3">
                      {getOpportunityTypeBadge(opp.opportunity_type)}
                      <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 rounded text-xs font-mono font-bold">
                        Score: {opp.score.toFixed(0)}/100
                      </div>
                    </div>

                    <div className="text-sm font-semibold text-white mb-1">
                      {opp.unified_product_id ? `Product: ${opp.unified_product_id}` : `Category: ${opp.category}`}
                    </div>

                    {opp.category && (
                      <div className="text-xs text-slate-400 mb-3">
                        Category: <span className="text-slate-300">{opp.category}</span>
                      </div>
                    )}

                    {/* Reasons */}
                    <div className="space-y-1.5 mb-4">
                      {opp.reasons.slice(0, 3).map((reason, idx) => (
                        <div key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                          <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                          <span>{reason}</span>
                        </div>
                      ))}
                    </div>

                    {/* Platform Presence */}
                    {opp.current_platforms && opp.current_platforms.length > 0 && (
                      <div className="flex items-center gap-2 text-xs text-slate-400 mb-3">
                        <span>Current:</span>
                        {opp.current_platforms.map((p, idx) => (
                          <span key={idx} className="px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded font-mono text-[10px]">
                            {p}
                          </span>
                        ))}
                        {opp.missing_observed_platforms && opp.missing_observed_platforms.length > 0 && (
                          <>
                            <span className="ml-1 text-rose-400">Missing:</span>
                            {opp.missing_observed_platforms.map((p, idx) => (
                              <span key={idx} className="px-1.5 py-0.5 bg-rose-950/40 text-rose-300 border border-rose-500/20 rounded font-mono text-[10px]">
                                {p}
                              </span>
                            ))}
                          </>
                        )}
                      </div>
                    )}

                    {/* Warnings */}
                    {opp.warnings && opp.warnings.length > 0 && (
                      <div className="p-2.5 bg-amber-950/30 border border-amber-500/20 rounded-lg mb-3">
                        {opp.warnings.map((w, idx) => (
                          <div key={idx} className="flex items-center gap-1.5 text-xs text-amber-300">
                            <ShieldAlert className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                            <span>{w}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
                      <span>Conf: {(opp.confidence * 100).toFixed(0)}%</span>
                      <span>•</span>
                      <span className="text-emerald-400 font-medium">{opp.data_freshness}</span>
                    </div>

                    <span className="text-xs text-slate-500 font-mono">
                      {opp.source_agent_ids.length} Sources
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Product Opportunity Analyzer */}
      {activeTab === "analyzer" && (
        <div className="space-y-6">
          {/* Selector */}
          <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-wrap items-center gap-4">
            <label className="text-sm font-semibold text-slate-300">Select Target Product:</label>
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              className="px-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-emerald-500 min-w-[280px]"
            >
              {catalogProducts.map((p) => (
                <option key={p.unified_product_id} value={p.unified_product_id}>
                  {p.canonical_name} ({p.category || "General"})
                </option>
              ))}
            </select>

            <button
              onClick={() => handleAnalyzeProduct(selectedProductId)}
              disabled={analyzingProduct}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-all"
            >
              <Compass className="w-4 h-4" />
              {analyzingProduct ? "Evaluating Opportunities..." : "Analyze Product Opportunities"}
            </button>
          </div>

          {/* Product Summary & 7-Part Score Breakdown */}
          {productSummary && (
            <div className="space-y-6">
              <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl">
                <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-6">
                  <div>
                    <h2 className="text-xl font-bold text-white">{productSummary.name}</h2>
                    <p className="text-sm text-slate-400">
                      Category: <span className="text-slate-300">{productSummary.category}</span> • ID: <span className="font-mono text-xs text-emerald-300">{productSummary.target_id}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-xs text-slate-400">Opportunity Score</div>
                      <div className="text-2xl font-bold text-emerald-400">{productSummary.opportunity_score.toFixed(0)}/100</div>
                    </div>
                  </div>
                </div>

                {/* 7-Part Deterministic Score Breakdown */}
                <h3 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wider">
                  Deterministic Score Breakdown (0 - 100)
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Evidence (25%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.evidence_strength_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Trend (20%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.trend_strength_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Gap (15%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.market_coverage_gap_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Price (15%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.price_opportunity_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Quality (10%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.product_quality_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Cross-Plat (10%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.cross_platform_evidence_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Fresh (5%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.freshness_score.toFixed(1)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Detected Opportunities List */}
              <div className="space-y-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Compass className="w-5 h-5 text-emerald-400" />
                  Detected Opportunities ({productSummary.opportunities.length})
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {productSummary.opportunities.map((opp) => (
                    <div key={opp.id} className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
                      <div className="flex justify-between items-start mb-2">
                        {getOpportunityTypeBadge(opp.opportunity_type)}
                        <span className="text-xs font-mono font-bold text-emerald-300">{opp.score.toFixed(0)}/100</span>
                      </div>
                      <div className="text-sm font-semibold text-white mb-2">Target: {opp.unified_product_id}</div>
                      <div className="space-y-1">
                        {opp.reasons.map((r, i) => (
                          <div key={i} className="text-xs text-slate-300 flex items-center gap-1.5">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                            <span>{r}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Candidate Review Queue */}
      {activeTab === "candidates" && (
        <div className="space-y-6">
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl flex justify-between items-center">
            <div>
              <h2 className="text-base font-bold text-white">Pending Human Review Queue</h2>
              <p className="text-xs text-slate-400">Borderline confidence opportunities requiring operator validation</p>
            </div>
            <span className="text-xs font-mono px-3 py-1 bg-amber-500/10 text-amber-300 border border-amber-500/20 rounded-full font-bold">
              {candidates.length} Pending
            </span>
          </div>

          {candidates.length === 0 ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-2xl">
              <CheckCircle className="w-8 h-8 mx-auto mb-3 text-emerald-500" />
              Candidate review queue is clear! All market opportunities are verified.
            </div>
          ) : (
            <div className="space-y-4">
              {candidates.map((c) => (
                <div key={c.id} className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2.5 py-0.5 bg-amber-500/10 text-amber-300 border border-amber-500/20 rounded text-xs font-bold font-mono">
                        {c.candidate_type}
                      </span>
                      <span className="text-xs font-mono text-slate-400">Score: {c.composite_score.toFixed(0)} • Conf: {(c.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="text-sm font-semibold text-white">{c.unified_product_id ? `Product: ${c.unified_product_id}` : `Category: ${c.category}`}</div>
                    <div className="text-xs text-slate-400 mt-1">
                      {c.reasons.join(" • ")}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleResolveCandidate(c.id, "approved")}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Approve
                    </button>
                    <button
                      onClick={() => handleResolveCandidate(c.id, "dismissed")}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Dismiss
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MarketOpportunityPage;
