import React, { useState, useEffect, useCallback } from "react";
import {
  Sparkles,
  Search,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  TrendingUp,
  Layers,
  Award,
  Zap,
  ShoppingBag,
  Sliders,
  DollarSign,
  Star,
  Check,
  Eye,
  Bookmark,
  Activity
} from "lucide-react";
import {
  recommendationService,
  intelligenceService
} from "../../services/domainServices";
import type {
  ProductRecommendationItem,
  RecommendationCandidateItem,
  ProductRecommendationSummaryItem,
  AgentRecommendationStatsItem,
  UnifiedProduct
} from "../../types";

export const RecommendationIntelligencePage: React.FC = () => {
  // State
  const [activeTab, setActiveTab] = useState<"feed" | "analyzer" | "candidates">("feed");
  const [stats, setStats] = useState<AgentRecommendationStatsItem | null>(null);
  const [recommendations, setRecommendations] = useState<ProductRecommendationItem[]>([]);
  const [candidates, setCandidates] = useState<RecommendationCandidateItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filters
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [minScore, setMinScore] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Product Analyzer State
  const [catalogProducts, setCatalogProducts] = useState<UnifiedProduct[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [productSummary, setProductSummary] = useState<ProductRecommendationSummaryItem | null>(null);
  const [analyzingProduct, setAnalyzingProduct] = useState<boolean>(false);

  // Load Data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, recsRes, candsRes, catalogRes] = await Promise.all([
        recommendationService.getStats(),
        recommendationService.list({
          recommendation_type: selectedType !== "all" ? selectedType : undefined,
          category: selectedCategory !== "all" ? selectedCategory : undefined,
          min_score: minScore > 0 ? minScore : undefined,
          search: searchQuery || undefined,
          limit: 50
        }),
        recommendationService.listCandidates("pending"),
        intelligenceService.listUnifiedProducts({ limit: 50 })
      ]);

      if (statsRes.success && statsRes.data) setStats(statsRes.data);
      if (recsRes.success && recsRes.data) setRecommendations(recsRes.data.items);
      if (candsRes.success && candsRes.data) setCandidates(candsRes.data.items);
      if (catalogRes.success && catalogRes.data) {
        setCatalogProducts(catalogRes.data.items);
        if (!selectedProductId && catalogRes.data.items.length > 0) {
          setSelectedProductId(catalogRes.data.items[0].unified_product_id);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load recommendation intelligence");
    } finally {
      setLoading(false);
    }
  }, [selectedType, selectedCategory, minScore, searchQuery, selectedProductId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Analyze single product
  const handleAnalyzeProduct = async (prodId: string) => {
    if (!prodId) return;
    setAnalyzingProduct(true);
    setError(null);
    try {
      const res = await recommendationService.generateForProduct(prodId, {
        include_similar: true,
        include_alternatives: true,
        include_better_price: true,
        include_cross_platform: true,
        include_best_value: true
      });
      if (res.success && res.data) {
        setProductSummary(res.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to generate recommendations for product");
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
      const res = await recommendationService.resolveCandidate(candidateId, { status });
      if (res.success) {
        setActionSuccess(`Candidate ${status === "approved" ? "approved" : "dismissed"} successfully`);
        setTimeout(() => setActionSuccess(null), 3000);
        fetchData();
      }
    } catch (err: any) {
      setError(err.message || "Failed to resolve candidate");
    }
  };

  // Log interaction
  const handleLogInteraction = async (rec: ProductRecommendationItem, type: 'view' | 'click' | 'save' | 'compare') => {
    try {
      await recommendationService.logInteraction({
        recommendation_id: rec.id,
        product_id: rec.unified_product_id,
        interaction_type: type,
        metadata: { category: rec.category, brand: rec.brand, type: rec.recommendation_type }
      });
      setActionSuccess(`Interaction logged: ${type}`);
      setTimeout(() => setActionSuccess(null), 2000);
    } catch {
      // Non-blocking interaction log
    }
  };

  const getRecommendationTypeBadge = (type: string) => {
    switch (type) {
      case "best_value":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><Award className="w-3.5 h-3.5" /> Best Value</span>;
      case "trending_product":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"><TrendingUp className="w-3.5 h-3.5" /> Trending</span>;
      case "better_price":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"><DollarSign className="w-3.5 h-3.5" /> Better Price</span>;
      case "high_quality":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20"><Star className="w-3.5 h-3.5" /> High Quality</span>;
      case "cross_platform":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20"><Layers className="w-3.5 h-3.5" /> Cross-Platform</span>;
      case "similar_product":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20"><ShoppingBag className="w-3.5 h-3.5" /> Similar</span>;
      case "opportunity":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20"><Zap className="w-3.5 h-3.5" /> Opportunity</span>;
      default:
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/20">{type.replace("_", " ")}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 lg:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 rounded-xl">
              <Sparkles className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                Recommendation & Product Intelligence
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                AI Agent 06: Evidence-grounded multi-platform product ranking & discovery
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Recs</span>
            <Sparkles className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {stats?.active_recommendations_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Live evidence-grounded picks</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Best Value</span>
            <Award className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">
            {stats?.best_value_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Price & rating optimized</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Trending</span>
            <TrendingUp className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 mt-2">
            {stats?.trending_recommendations_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Agent 4 momentum signals</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Cross-Platform</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-purple-400 mt-2">
            {stats?.cross_platform_count ?? 0}
          </div>
          <span className="text-xs text-slate-500">Multi-marketplace sync</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Interactions</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-2">
            {stats?.total_interactions_logged ?? 0}
          </div>
          <span className="text-xs text-slate-500">Real clicks & saves</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab("feed")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "feed"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          Recommendations Feed ({recommendations.length})
        </button>

        <button
          onClick={() => setActiveTab("analyzer")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "analyzer"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sliders className="w-4 h-4" />
          Product Intelligence Analyzer
        </button>

        <button
          onClick={() => setActiveTab("candidates")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "candidates"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Candidate Review Queue ({candidates.length})
        </button>
      </div>

      {/* TAB 1: Recommendations Feed */}
      {activeTab === "feed" && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  placeholder="Search recommendations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-64"
                />
              </div>

              {/* Type Filter */}
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All Types</option>
                <option value="best_value">Best Value</option>
                <option value="trending_product">Trending</option>
                <option value="better_price">Better Price</option>
                <option value="high_quality">High Quality</option>
                <option value="cross_platform">Cross-Platform</option>
                <option value="similar_product">Similar</option>
                <option value="alternative_product">Alternative</option>
                <option value="opportunity">Opportunity</option>
              </select>

              {/* Category Filter */}
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All Categories</option>
                <option value="Audio">Audio</option>
                <option value="Wearables">Wearables</option>
                <option value="Cameras">Cameras</option>
                <option value="Electronics">Electronics</option>
              </select>

              {/* Min Score Filter */}
              <select
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value={0}>Min Score: Any</option>
                <option value={60}>Score ≥ 60</option>
                <option value={75}>Score ≥ 75</option>
                <option value={85}>Score ≥ 85</option>
              </select>
            </div>

            <div className="text-xs text-slate-500 font-mono">
              Showing {recommendations.length} recommendations
            </div>
          </div>

          {/* Cards Grid */}
          {loading ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-2xl">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-400" />
              Loading recommendations...
            </div>
          ) : recommendations.length === 0 ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-2xl">
              <Sparkles className="w-8 h-8 mx-auto mb-3 text-slate-600" />
              No recommendations match the current filters.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {recommendations.map((rec) => (
                <div
                  key={rec.id}
                  className="p-5 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/40 rounded-2xl transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex justify-between items-start gap-2 mb-3">
                      {getRecommendationTypeBadge(rec.recommendation_type)}
                      <div className="flex items-center gap-1.5 px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 rounded text-xs font-mono font-bold">
                        Score: {rec.score.toFixed(0)}/100
                      </div>
                    </div>

                    <div className="text-sm font-semibold text-white mb-1">
                      Product: {rec.unified_product_id}
                    </div>

                    {rec.category && (
                      <div className="text-xs text-slate-400 mb-3">
                        Category: <span className="text-slate-300">{rec.category}</span>
                      </div>
                    )}

                    {/* Reasons */}
                    <div className="space-y-1.5 mb-4">
                      {rec.reasons.slice(0, 3).map((reason, idx) => (
                        <div key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                          <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                          <span>{reason}</span>
                        </div>
                      ))}
                    </div>

                    {/* Warnings */}
                    {rec.warnings && rec.warnings.length > 0 && (
                      <div className="p-2.5 bg-amber-950/30 border border-amber-500/20 rounded-lg mb-3">
                        {rec.warnings.map((w, idx) => (
                          <div key={idx} className="flex items-center gap-1.5 text-xs text-amber-300">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                            <span>{w}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
                      <span>Conf: {(rec.confidence * 100).toFixed(0)}%</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleLogInteraction(rec, 'view')}
                        title="Log View"
                        className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleLogInteraction(rec, 'save')}
                        title="Save Pick"
                        className="p-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded-lg text-xs transition-colors"
                      >
                        <Bookmark className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Product Intelligence Analyzer */}
      {activeTab === "analyzer" && (
        <div className="space-y-6">
          {/* Selector */}
          <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-wrap items-center gap-4">
            <label className="text-sm font-semibold text-slate-300">Select Target Product:</label>
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              className="px-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500 min-w-[280px]"
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
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all"
            >
              <Sparkles className="w-4 h-4" />
              {analyzingProduct ? "Computing Scores..." : "Generate Product Intelligence"}
            </button>
          </div>

          {/* Product Summary & 8-Part Score Breakdown */}
          {productSummary && (
            <div className="space-y-6">
              <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl">
                <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-6">
                  <div>
                    <h2 className="text-xl font-bold text-white">{productSummary.canonical_name}</h2>
                    <p className="text-sm text-slate-400">
                      Category: <span className="text-slate-300">{productSummary.category}</span> • ID: <span className="font-mono text-xs text-indigo-300">{productSummary.unified_product_id}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-xs text-slate-400">Overall Score</div>
                      <div className="text-2xl font-bold text-indigo-400">{productSummary.recommendation_score.toFixed(0)}/100</div>
                    </div>
                  </div>
                </div>

                {/* 8-Part Deterministic Score Breakdown */}
                <h3 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wider">
                  Deterministic Score Breakdown (0 - 100)
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Data Quality (15%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.data_quality_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Similarity (20%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.product_similarity_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Price Value (20%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.price_value_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Rating Quality (15%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.rating_quality_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Trend Strength (15%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.trend_strength_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Availability (5%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.availability_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Cross-Platform (5%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.cross_platform_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                    <div className="text-xs text-slate-400">Freshness (5%)</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {productSummary.score_breakdown.freshness_score.toFixed(1)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Recommended Items */}
              <div className="space-y-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-400" />
                  Generated Recommendations ({productSummary.recommendations.length})
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {productSummary.recommendations.map((rec) => (
                    <div key={rec.id} className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
                      <div className="flex justify-between items-start mb-2">
                        {getRecommendationTypeBadge(rec.recommendation_type)}
                        <span className="text-xs font-mono font-bold text-indigo-300">{rec.score.toFixed(0)}/100</span>
                      </div>
                      <div className="text-sm font-semibold text-white mb-2">Item: {rec.unified_product_id}</div>
                      <div className="space-y-1">
                        {rec.reasons.map((r, i) => (
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
              <p className="text-xs text-slate-400">Borderline confidence recommendations requiring operator confirmation</p>
            </div>
            <span className="text-xs font-mono px-3 py-1 bg-amber-500/10 text-amber-300 border border-amber-500/20 rounded-full font-bold">
              {candidates.length} Pending
            </span>
          </div>

          {candidates.length === 0 ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-2xl">
              <CheckCircle className="w-8 h-8 mx-auto mb-3 text-emerald-500" />
              Candidate review queue is clear! All recommendations are qualified.
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
                    <div className="text-sm font-semibold text-white">Product: {c.unified_product_id}</div>
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

export default RecommendationIntelligencePage;
