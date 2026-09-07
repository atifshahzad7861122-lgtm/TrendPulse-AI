import React, { useState, useEffect } from "react";
import { intelligenceService, llmService, taxonomyService, categorizationAgentService, entityMatchingService } from "../../services/domainServices";
import type {
  UnifiedProduct,
  UnifiedProductDetailResponse,
  UnifiedProductHistoryResponse,
  AIProductAnalysisResponse,
  AIProductSummaryResponse,
  AIMarketComparisonResponse,
  AITrendAnalysisResponse,
  TaxonomyTreeNode,
  TaxonomyCategoryItem,
  ProductTaxonomyAssignmentResponse,
  ProductTaxonomyCandidateItem,
  ProductMatchCandidateItem,
  ProductMatchDecisionItem,
  EntityMatchingStatsItem
} from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const ProductIntelligencePage: React.FC = () => {
  const [products, setProducts] = useState<UnifiedProduct[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState<number>(0);

  // View Mode: 'grid' | 'taxonomy' | 'candidates' | 'matching_queue'
  const [viewMode, setViewMode] = useState<"grid" | "taxonomy" | "candidates" | "matching_queue">("grid");

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("synced");

  // Taxonomy Explorer States
  const [taxonomyTree, setTaxonomyTree] = useState<TaxonomyTreeNode[]>([]);
  const [categoriesList, setCategoriesList] = useState<TaxonomyCategoryItem[]>([]);
  const [taxonomyLoading, setTaxonomyLoading] = useState<boolean>(false);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});
  const [taxonomySearchQuery, setTaxonomySearchQuery] = useState<string>("");
  const [taxonomySearchResults, setTaxonomySearchResults] = useState<any[]>([]);

  // Taxonomy Candidates Review States
  const [candidates, setCandidates] = useState<ProductTaxonomyCandidateItem[]>([]);
  const [candidatesLoading, setCandidatesLoading] = useState<boolean>(false);

  // Agent 3 Entity Matching States
  const [matchingCandidates, setMatchingCandidates] = useState<ProductMatchCandidateItem[]>([]);
  const [matchingStats, setMatchingStats] = useState<EntityMatchingStatsItem | null>(null);
  const [matchingLoading, setMatchingLoading] = useState<boolean>(false);
  const [matchingDecisions, setMatchingDecisions] = useState<ProductMatchDecisionItem[]>([]);
  const [resolvingCandidateId, setResolvingCandidateId] = useState<string | null>(null);

  // Selected Unified Product for Detail Modal
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [detailData, setDetailData] = useState<UnifiedProductDetailResponse | null>(null);
  const [historyData, setHistoryData] = useState<UnifiedProductHistoryResponse | null>(null);
  const [taxonomyAssignment, setTaxonomyAssignment] = useState<ProductTaxonomyAssignmentResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [reclassifying, setReclassifying] = useState<boolean>(false);

  // Modal Sub-Tabs: 'overview' | 'taxonomy' | 'matching' | 'ai_analysis' | 'ai_summary' | 'ai_comparison' | 'ai_trend'
  const [activeModalTab, setActiveModalTab] = useState<string>("overview");


  // AI Intelligence States
  const [aiAnalysis, setAiAnalysis] = useState<AIProductAnalysisResponse | null>(null);
  const [aiSummary, setAiSummary] = useState<AIProductSummaryResponse | null>(null);
  const [aiComparison, setAiComparison] = useState<AIMarketComparisonResponse | null>(null);
  const [aiTrend, setAiTrend] = useState<AITrendAnalysisResponse | null>(null);
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const { showToast } = useToast();

  const fetchUnifiedProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await intelligenceService.listUnifiedProducts({
        search: searchQuery || undefined,
        platform: selectedPlatform !== "all" ? selectedPlatform : undefined,
        category: selectedCategory !== "all" ? selectedCategory : undefined,
        sort_by: sortBy,
        limit: 50
      });
      if (res.success && res.data) {
        setProducts(res.data.items);
        setTotalCount(res.data.total);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load Product Intelligence catalog");
    } finally {
      setLoading(false);
    }
  };

  const fetchTaxonomyTree = async () => {
    setTaxonomyLoading(true);
    try {
      const [treeRes, catsRes] = await Promise.all([
        taxonomyService.getTree(),
        taxonomyService.getCategories({ level: 1 })
      ]);
      if (treeRes.success && treeRes.data) {
        setTaxonomyTree(treeRes.data.categories);
        // Default expand top 3
        const initExpanded: Record<string, boolean> = {};
        treeRes.data.categories.slice(0, 4).forEach((c) => {
          initExpanded[c.id] = true;
        });
        setExpandedNodes(initExpanded);
      }
      if (catsRes.success && catsRes.data) {
        setCategoriesList(catsRes.data.items);
      }
    } catch (err: any) {
      console.error("Failed to load taxonomy tree:", err);
    } finally {
      setTaxonomyLoading(false);
    }
  };

  const fetchCandidates = async () => {
    setCandidatesLoading(true);
    try {
      const res = await categorizationAgentService.getCandidates(50, 0);
      if (res.success && res.data) {
        setCandidates(res.data);
      }
    } catch (err: any) {
      console.error("Failed to load taxonomy candidates:", err);
    } finally {
      setCandidatesLoading(false);
    }
  };

  const fetchMatchingCandidates = async () => {
    setMatchingLoading(true);
    try {
      const [candRes, statsRes] = await Promise.all([
        entityMatchingService.listCandidates("needs_review", 50, 0),
        entityMatchingService.getStats()
      ]);
      if (candRes.success && candRes.data) {
        setMatchingCandidates(candRes.data);
      }
      if (statsRes.success && statsRes.data) {
        setMatchingStats(statsRes.data);
      }
    } catch (err: any) {
      console.error("Failed to load entity matching candidates:", err);
    } finally {
      setMatchingLoading(false);
    }
  };

  const handleResolveMatchCandidate = async (
    candidateId: string,
    action: "confirm_match" | "confirm_variant" | "reject_match"
  ) => {
    setResolvingCandidateId(candidateId);
    try {
      const res = await entityMatchingService.resolveCandidate(candidateId, { action });
      if (res.success) {
        const actionLabels = {
          confirm_match: "Match confirmed & reinforced in memory!",
          confirm_variant: "Variant confirmed & recorded!",
          reject_match: "Marked as false-positive & remembered!"
        };
        showToast(actionLabels[action], "success");
        // Refresh candidates
        fetchMatchingCandidates();
      }
    } catch (err: any) {
      showToast(err.message || "Failed to resolve candidate", "error");
    } finally {
      setResolvingCandidateId(null);
    }
  };

  useEffect(() => {
    fetchUnifiedProducts();
  }, [selectedPlatform, selectedCategory, sortBy]);

  useEffect(() => {
    fetchTaxonomyTree();
    fetchMatchingCandidates();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchUnifiedProducts();
  };

  const handleTaxonomySearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taxonomySearchQuery.trim()) {
      setTaxonomySearchResults([]);
      return;
    }
    try {
      const res = await taxonomyService.search(taxonomySearchQuery.trim());
      if (res.success && res.data) {
        setTaxonomySearchResults(res.data.results);
      }
    } catch (err: any) {
      showToast("Taxonomy search failed", "error");
    }
  };

  const handleOpenDetail = async (prodId: string) => {
    setSelectedProductId(prodId);
    setDetailLoading(true);
    setDetailData(null);
    setHistoryData(null);
    setTaxonomyAssignment(null);
    setMatchingDecisions([]);
    setActiveModalTab("overview");
    setAiAnalysis(null);
    setAiSummary(null);
    setAiComparison(null);
    setAiTrend(null);
    setAiError(null);

    try {
      const [detailRes, histRes, taxRes, matchRes] = await Promise.all([
        intelligenceService.getUnifiedProductDetail(prodId),
        intelligenceService.getUnifiedProductHistory(prodId).catch(() => null),
        categorizationAgentService.getAssignment(prodId).catch(() => null),
        entityMatchingService.getProductMatches(prodId).catch(() => null)
      ]);
      if (detailRes.success && detailRes.data) {
        setDetailData(detailRes.data);
      }
      if (histRes && histRes.success && histRes.data) {
        setHistoryData(histRes.data);
      }
      if (taxRes && taxRes.success && taxRes.data) {
        setTaxonomyAssignment(taxRes.data);
      }
      if (matchRes && matchRes.success && matchRes.data) {
        setMatchingDecisions(matchRes.data);
      }

    } catch (err: any) {
      showToast(err.message || "Failed to load product details", "error");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleReclassifyProduct = async () => {
    if (!selectedProductId) return;
    setReclassifying(true);
    try {
      const res = await categorizationAgentService.classify(selectedProductId, {
        allow_llm: true,
        force_reclassify: true
      });
      if (res.success && res.data) {
        setTaxonomyAssignment(res.data);
        showToast("Agent 2 successfully reclassified product!", "success");
        // Refresh catalog and detail
        fetchUnifiedProducts();
        const detailRes = await intelligenceService.getUnifiedProductDetail(selectedProductId);
        if (detailRes.success && detailRes.data) {
          setDetailData(detailRes.data);
        }
      }
    } catch (err: any) {
      showToast(err.message || "Reclassification failed", "error");
    } finally {
      setReclassifying(false);
    }
  };

  // AI Triggers
  const handleFetchAiAnalysis = async (forceRefresh: boolean = false) => {
    if (!selectedProductId) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await llmService.analyzeProduct(selectedProductId, forceRefresh);
      if (res.success && res.data) {
        setAiAnalysis(res.data);
      }
    } catch (err: any) {
      setAiError(err.message || "AI Analysis failed");
      showToast(err.message || "AI Analysis failed", "error");
    } finally {
      setAiLoading(false);
    }
  };

  const handleFetchAiSummary = async (forceRefresh: boolean = false) => {
    if (!selectedProductId) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await llmService.summarizeProduct(selectedProductId, forceRefresh);
      if (res.success && res.data) {
        setAiSummary(res.data);
      }
    } catch (err: any) {
      setAiError(err.message || "AI Summary generation failed");
      showToast(err.message || "AI Summary generation failed", "error");
    } finally {
      setAiLoading(false);
    }
  };

  const handleFetchAiComparison = async (forceRefresh: boolean = false) => {
    if (!selectedProductId) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await llmService.compareMarket(selectedProductId, forceRefresh);
      if (res.success && res.data) {
        setAiComparison(res.data);
      }
    } catch (err: any) {
      setAiError(err.message || "Market Comparison failed");
      showToast(err.message || "Market Comparison failed", "error");
    } finally {
      setAiLoading(false);
    }
  };

  const handleFetchAiTrend = async (forceRefresh: boolean = false) => {
    if (!selectedProductId) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await llmService.analyzeTrend(selectedProductId, forceRefresh);
      if (res.success && res.data) {
        setAiTrend(res.data);
      }
    } catch (err: any) {
      setAiError(err.message || "Trend Analysis failed");
      showToast(err.message || "Trend Analysis failed", "error");
    } finally {
      setAiLoading(false);
    }
  };

  const handleTabSelect = (tab: string) => {
    setActiveModalTab(tab);
    if (tab === "ai_analysis" && !aiAnalysis) {
      handleFetchAiAnalysis(false);
    } else if (tab === "ai_summary" && !aiSummary) {
      handleFetchAiSummary(false);
    } else if (tab === "ai_comparison" && !aiComparison) {
      handleFetchAiComparison(false);
    } else if (tab === "ai_trend" && !aiTrend) {
      handleFetchAiTrend(false);
    }
  };

  const toggleNodeExpand = (nodeId: string) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [nodeId]: !prev[nodeId]
    }));
  };

  const getMethodBadgeClass = (method?: string) => {
    switch (method) {
      case "exact_marketplace_map":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "brand_rule":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "keyword_rule":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/30";
      case "memory":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "llm":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      default:
        return "bg-gray-500/10 text-gray-400 border-gray-500/30";
    }
  };

  const getConfidenceBadge = (confidence: number, needsReview?: boolean) => {
    if (needsReview || confidence < 0.50) {
      return (
        <span className="px-2 py-0.5 rounded text-[9px] font-mono-data font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1">
          <span className="material-symbols-outlined text-[10px]">warning</span>
          NEEDS REVIEW ({Math.round(confidence * 100)}%)
        </span>
      );
    }
    if (confidence >= 0.90) {
      return (
        <span className="px-2 py-0.5 rounded text-[9px] font-mono-data font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
          HIGH ({Math.round(confidence * 100)}%)
        </span>
      );
    }
    if (confidence >= 0.75) {
      return (
        <span className="px-2 py-0.5 rounded text-[9px] font-mono-data font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
          MED ({Math.round(confidence * 100)}%)
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[9px] font-mono-data font-bold bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
        LOW ({Math.round(confidence * 100)}%)
      </span>
    );
  };

  return (
    <div className="space-y-8 animate-fade-in p-2 md:p-6">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-outline-variant/20 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-primary/10 border border-primary/20 text-primary">
              <span className="material-symbols-outlined text-2xl">account_tree</span>
            </div>
            <div>
              <h1 className="text-2xl font-headline font-bold text-on-surface flex items-center gap-3">
                Product Intelligence & Deduplication
                <span className="text-xs px-2.5 py-0.5 rounded-full font-mono-data border bg-primary/10 text-primary border-primary/30">
                  AGENT 02 + 03 ENRICHED
                </span>
              </h1>
              <p className="text-xs text-on-surface-variant font-mono-data mt-0.5">
                Centralized TrendPulse taxonomy hierarchy, cross-platform entity matching & Agent 3 deduplication
              </p>
            </div>
          </div>
        </div>

        {/* View Mode & Stats Strip */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center p-1 rounded-xl bg-surface-container-low border border-outline-variant/20">
            <button
              onClick={() => setViewMode("grid")}
              className={`px-3 py-1.5 rounded-lg text-xs font-headline font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === "grid"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <span className="material-symbols-outlined text-sm">grid_view</span>
              Catalog View
            </button>
            <button
              onClick={() => {
                setViewMode("taxonomy");
                if (taxonomyTree.length === 0) fetchTaxonomyTree();
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-headline font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === "taxonomy"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <span className="material-symbols-outlined text-sm">account_tree</span>
              Taxonomy Explorer
            </button>
            <button
              onClick={() => {
                setViewMode("candidates");
                fetchCandidates();
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-headline font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === "candidates"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <span className="material-symbols-outlined text-sm">pending_actions</span>
              Taxonomy Review
            </button>
            <button
              onClick={() => {
                setViewMode("matching_queue");
                fetchMatchingCandidates();
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-headline font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === "matching_queue"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <span className="material-symbols-outlined text-sm">hub</span>
              Match Review Queue
              {matchingCandidates.length > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[9px] bg-amber-500 text-black font-bold font-mono-data">
                  {matchingCandidates.length}
                </span>
              )}
            </button>
          </div>

          <div className="px-4 py-2 rounded-xl bg-surface-container-low border border-outline-variant/20 flex items-center gap-2.5">
            <span className="material-symbols-outlined text-primary text-base">inventory_2</span>
            <div>
              <div className="text-[10px] font-label-caps text-on-surface-variant uppercase">Unified Products</div>
              <div className="text-sm font-headline font-bold text-on-surface font-mono-data">{totalCount}</div>
            </div>
          </div>
        </div>
      </div>

      {/* VIEW 1: CATALOG GRID VIEW */}
      {viewMode === "grid" && (
        <div className="space-y-6">
          {/* Filter and Search Bar */}
          <div className="bg-surface-container-low border border-outline-variant/20 rounded-2xl p-4 space-y-4">
            <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row items-center gap-3">
              <div className="relative flex-1 w-full">
                <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant/60 text-lg">
                  search
                </span>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search canonical titles, brands, SKUs or keywords..."
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-surface-container-high border border-outline-variant/30 text-xs font-mono-data text-on-surface focus:outline-none focus:border-primary transition-all"
                />
              </div>

              <button
                type="submit"
                className="px-5 py-2.5 bg-primary text-on-primary rounded-xl font-headline text-xs font-semibold hover:bg-primary/90 transition-all shrink-0 flex items-center gap-1.5 shadow-sm"
              >
                <span className="material-symbols-outlined text-sm">filter_list</span>
                <span>Filter Catalog</span>
              </button>
            </form>

            {/* Filter Controls */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-outline-variant/10">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-label-caps text-on-surface-variant uppercase font-semibold">
                  Platform:
                </span>
                {["all", "daraz", "shopify"].map((p) => (
                  <button
                    key={p}
                    onClick={() => setSelectedPlatform(p)}
                    className={`px-3 py-1 rounded-lg text-xs font-mono-data uppercase transition-all ${
                      selectedPlatform === p
                        ? "bg-primary text-on-primary font-bold shadow-sm"
                        : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-label-caps text-on-surface-variant uppercase font-semibold">
                    Category:
                  </span>
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-surface-container-high border border-outline-variant/30 text-xs font-mono-data text-on-surface focus:outline-none focus:border-primary"
                  >
                    <option value="all">All Categories</option>
                    {categoriesList.map((c) => (
                      <option key={c.id} value={c.name}>
                        {c.name} ({c.product_count})
                      </option>
                    ))}
                    {categoriesList.length === 0 && (
                      <>
                        <option value="Electronics">Electronics</option>
                        <option value="Fashion">Fashion</option>
                        <option value="Beauty & Personal Care">Beauty & Personal Care</option>
                        <option value="Home & Living">Home & Living</option>
                        <option value="Sports & Fitness">Sports & Fitness</option>
                      </>
                    )}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-label-caps text-on-surface-variant uppercase font-semibold">
                    Sort By:
                  </span>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-surface-container-high border border-outline-variant/30 text-xs font-mono-data text-on-surface focus:outline-none focus:border-primary"
                  >
                    <option value="synced">Recently Synced</option>
                    <option value="quality">Data Quality Score</option>
                    <option value="listings">Most Multi-Platform Listings</option>
                    <option value="name">Product Name (A-Z)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Catalog Grid */}
          {loading ? (
            <LoadingSpinner label="Querying unified product intelligence..." />
          ) : error ? (
            <ErrorState message={error} onRetry={fetchUnifiedProducts} />
          ) : products.length === 0 ? (
            <div className="p-12 text-center border border-dashed border-outline-variant/30 rounded-3xl space-y-3 bg-surface-container-low">
              <span className="material-symbols-outlined text-4xl text-on-surface-variant/40">search_off</span>
              <h3 className="text-base font-headline font-bold text-on-surface">No Unified Products Found</h3>
              <p className="text-xs text-on-surface-variant max-w-md mx-auto">
                Try adjusting your search query or sync products from Daraz or Shopify to populate the canonical catalog.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {products.map((p) => (
                <div
                  key={p.unified_product_id}
                  onClick={() => handleOpenDetail(p.unified_product_id)}
                  className="bg-surface-container-low border border-outline-variant/20 rounded-2xl overflow-hidden hover:border-primary/40 transition-all flex flex-col justify-between group shadow-sm hover:shadow-md cursor-pointer"
                >
                  {/* Product Photo */}
                  <div className="relative aspect-square bg-surface-container-high overflow-hidden">
                    {p.primary_image ? (
                      <img
                        src={p.primary_image}
                        alt={p.canonical_name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-on-surface-variant/30">
                        <span className="material-symbols-outlined text-4xl">category</span>
                      </div>
                    )}

                    {/* Platforms Badges */}
                    <div className="absolute top-2 left-2 flex flex-wrap gap-1">
                      {p.platforms.map((pl) => (
                        <span
                          key={pl}
                          className={`px-2 py-0.5 text-[9px] font-mono-data font-bold rounded shadow-sm ${
                            pl.toLowerCase() === "daraz"
                              ? "bg-amber-500 text-black"
                              : pl.toLowerCase() === "shopify"
                              ? "bg-emerald-500 text-white"
                              : "bg-primary text-on-primary"
                          }`}
                        >
                          {pl.toUpperCase()}
                        </span>
                      ))}
                    </div>

                    {/* Quality Score Badge */}
                    <span className="absolute bottom-2 right-2 px-2 py-0.5 bg-surface-container-highest/90 backdrop-blur text-on-surface text-[9px] font-mono-data rounded border border-outline-variant/30">
                      Quality: {Math.round(p.completeness_score * 100)}%
                    </span>
                  </div>

                  {/* Product Details */}
                  <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                    <div>
                      {/* Taxonomy Path Breadcrumbs */}
                      <div className="text-[10px] font-mono-data text-primary flex items-center gap-1 truncate font-semibold">
                        <span className="material-symbols-outlined text-xs">folder</span>
                        <span>
                          {p.taxonomy_path && p.taxonomy_path.length > 0
                            ? p.taxonomy_path.join(" > ")
                            : p.category || "Unclassified"}
                        </span>
                      </div>

                      <h4 className="text-sm font-headline font-semibold text-on-surface line-clamp-2 mt-1 group-hover:text-primary transition-colors">
                        {p.canonical_name}
                      </h4>

                      {/* Brand & Confidence */}
                      <div className="flex flex-wrap items-center gap-1.5 mt-2">
                        {p.brand && (
                          <span className="px-2 py-0.5 bg-surface-container-high rounded text-[10px] font-mono-data text-on-surface-variant">
                            {p.brand}
                          </span>
                        )}
                        {getConfidenceBadge(p.category_confidence || 1.0, p.needs_review)}
                        {p.classification_method && (
                          <span className={`px-1.5 py-0.5 text-[9px] font-mono-data rounded border ${getMethodBadgeClass(p.classification_method)}`}>
                            {p.classification_method}
                          </span>
                        )}
                      </div>

                      {/* Extracted Attributes Pills */}
                      {p.attributes && Object.keys(p.attributes).length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {Object.entries(p.attributes).slice(0, 3).map(([k, v]) => (
                            <span key={k} className="px-1.5 py-0.5 bg-surface-container-highest/50 text-on-surface-variant text-[9px] font-mono-data rounded">
                              {k}: {String(v)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="pt-3 border-t border-outline-variant/15 flex items-center justify-between">
                      <div>
                        <div className="text-xs font-mono-data text-on-surface-variant">Price Range</div>
                        <div className="text-sm font-headline font-bold text-on-surface truncate max-w-[150px]">
                          {p.price_range_formatted || `$${p.lowest_price.toFixed(2)}`}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="flex items-center gap-1 text-xs text-amber-400 font-bold justify-end">
                          <span className="material-symbols-outlined text-sm">star</span>
                          <span>{p.avg_rating.toFixed(1)}</span>
                        </div>
                        <div className="text-[10px] font-mono-data text-on-surface-variant">
                          {p.listings_count} listing{p.listings_count > 1 ? "s" : ""}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* VIEW 2: TAXONOMY EXPLORER VIEW */}
      {viewMode === "taxonomy" && (
        <div className="space-y-6">
          <div className="bg-surface-container-low border border-outline-variant/20 rounded-3xl p-6 space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/20 pb-4">
              <div>
                <h2 className="text-lg font-headline font-bold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-xl">account_tree</span>
                  TrendPulse Centralized Taxonomy Hierarchy
                </h2>
                <p className="text-xs text-on-surface-variant font-mono-data mt-0.5">
                  Extensible tree: Category (L1) &gt; Subcategory (L2) &gt; Product Type (L4) with real database product counts
                </p>
              </div>

              {/* Taxonomy Fast Search */}
              <form onSubmit={handleTaxonomySearch} className="flex items-center gap-2">
                <input
                  type="text"
                  value={taxonomySearchQuery}
                  onChange={(e) => setTaxonomySearchQuery(e.target.value)}
                  placeholder="Search taxonomy nodes..."
                  className="px-3 py-1.5 rounded-xl bg-surface-container-high border border-outline-variant/30 text-xs font-mono-data text-on-surface focus:outline-none focus:border-primary"
                />
                <button
                  type="submit"
                  className="px-3 py-1.5 bg-primary text-on-primary rounded-xl text-xs font-headline font-semibold hover:bg-primary/90 transition-all"
                >
                  Search
                </button>
              </form>
            </div>

            {/* Search Results if any */}
            {taxonomySearchResults.length > 0 && (
              <div className="p-4 rounded-2xl bg-surface-container border border-outline-variant/30 space-y-2">
                <div className="text-xs font-label-caps text-primary uppercase font-bold">Search Matches:</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                  {taxonomySearchResults.map((sr) => (
                    <div
                      key={sr.id}
                      onClick={() => {
                        setSelectedCategory(sr.path[0]);
                        setViewMode("grid");
                      }}
                      className="p-2.5 rounded-xl bg-surface-container-high border border-outline-variant/20 hover:border-primary/40 cursor-pointer transition-all"
                    >
                      <div className="text-xs font-bold text-on-surface">{sr.name}</div>
                      <div className="text-[10px] font-mono-data text-on-surface-variant truncate">
                        {sr.path.join(" > ")}
                      </div>
                      <div className="text-[10px] text-primary font-mono-data mt-1">
                        {sr.product_count} products
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Taxonomy Tree Explorer */}
            {taxonomyLoading ? (
              <LoadingSpinner label="Loading taxonomy tree..." />
            ) : taxonomyTree.length === 0 ? (
              <div className="p-8 text-center text-on-surface-variant font-mono-data text-xs">
                No taxonomy categories initialized.
              </div>
            ) : (
              <div className="space-y-4">
                {taxonomyTree.map((cat) => (
                  <div
                    key={cat.id}
                    className="border border-outline-variant/20 rounded-2xl bg-surface-container overflow-hidden"
                  >
                    {/* Level 1 Header */}
                    <div
                      onClick={() => toggleNodeExpand(cat.id)}
                      className="p-4 flex items-center justify-between cursor-pointer hover:bg-surface-container-high/60 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary text-xl">
                          {expandedNodes[cat.id] ? "folder_open" : "folder"}
                        </span>
                        <div>
                          <div className="text-sm font-headline font-bold text-on-surface flex items-center gap-2">
                            {cat.name}
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono-data bg-primary/10 text-primary border border-primary/20">
                              {cat.product_count} products
                            </span>
                          </div>
                          {cat.description && (
                            <div className="text-xs text-on-surface-variant font-mono-data">{cat.description}</div>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedCategory(cat.name);
                            setViewMode("grid");
                          }}
                          className="px-3 py-1 bg-surface-container-highest hover:bg-primary hover:text-on-primary rounded-lg text-xs font-mono-data transition-all"
                        >
                          View Products
                        </button>
                        <span className="material-symbols-outlined text-on-surface-variant text-lg">
                          {expandedNodes[cat.id] ? "expand_less" : "expand_more"}
                        </span>
                      </div>
                    </div>

                    {/* Level 2 Subcategories */}
                    {expandedNodes[cat.id] && cat.children && cat.children.length > 0 && (
                      <div className="p-4 pt-0 space-y-3 border-t border-outline-variant/10 bg-surface-container-low/40">
                        {cat.children.map((sub) => (
                          <div key={sub.id} className="pl-6 border-l-2 border-primary/20 space-y-2 mt-3">
                            <div
                              onClick={() => toggleNodeExpand(sub.id)}
                              className="flex items-center justify-between cursor-pointer hover:text-primary transition-colors"
                            >
                              <div className="flex items-center gap-2">
                                <span className="material-symbols-outlined text-sm text-primary">subdirectory_arrow_right</span>
                                <span className="text-xs font-headline font-semibold text-on-surface">{sub.name}</span>
                                <span className="text-[10px] font-mono-data text-on-surface-variant">
                                  ({sub.product_count} products)
                                </span>
                              </div>

                              <span className="material-symbols-outlined text-xs text-on-surface-variant">
                                {expandedNodes[sub.id] ? "expand_less" : "expand_more"}
                              </span>
                            </div>

                            {/* Level 4 Product Types */}
                            {expandedNodes[sub.id] && sub.children && sub.children.length > 0 && (
                              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pl-4 pt-1">
                                {sub.children.map((pt) => (
                                  <div
                                    key={pt.id}
                                    onClick={() => {
                                      setSearchQuery(pt.name);
                                      setViewMode("grid");
                                    }}
                                    className="p-2 rounded-xl bg-surface-container-high/60 border border-outline-variant/20 hover:border-primary/40 cursor-pointer flex items-center justify-between text-xs font-mono-data text-on-surface transition-all"
                                  >
                                    <span className="truncate">{pt.name}</span>
                                    <span className="text-[10px] text-primary shrink-0 font-bold ml-2">
                                      {pt.product_count}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW 3: CANDIDATES FOR REVIEW */}
      {viewMode === "candidates" && (
        <div className="space-y-6">
          <div className="bg-surface-container-low border border-outline-variant/20 rounded-3xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-outline-variant/20 pb-4">
              <div>
                <h2 className="text-lg font-headline font-bold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-amber-400 text-xl">pending_actions</span>
                  Taxonomy Review Candidates
                </h2>
                <p className="text-xs text-on-surface-variant font-mono-data mt-0.5">
                  Products with classification confidence &lt; 0.50 or insufficient marketplace data flagged by Agent 2
                </p>
              </div>
              <button
                onClick={fetchCandidates}
                disabled={candidatesLoading}
                className="px-3 py-1.5 bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-xl text-xs font-mono-data flex items-center gap-1.5 transition-all"
              >
                <span className="material-symbols-outlined text-xs">refresh</span>
                Refresh
              </button>
            </div>

            {candidatesLoading ? (
              <LoadingSpinner label="Querying review candidates..." />
            ) : candidates.length === 0 ? (
              <div className="p-12 text-center border border-dashed border-outline-variant/30 rounded-2xl text-on-surface-variant text-xs font-mono-data">
                No taxonomy review candidates currently queued. All products classified confidently!
              </div>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-outline-variant/20 bg-surface-container">
                <table className="w-full text-left text-xs">
                  <thead className="bg-surface-container-high text-on-surface-variant font-label-caps uppercase text-[10px] border-b border-outline-variant/20">
                    <tr>
                      <th className="p-3">Product ID</th>
                      <th className="p-3">Candidate Category</th>
                      <th className="p-3">Subcategory</th>
                      <th className="p-3">Product Type</th>
                      <th className="p-3">Confidence</th>
                      <th className="p-3">Reason</th>
                      <th className="p-3">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/10 font-mono-data text-on-surface">
                    {candidates.map((c) => (
                      <tr key={c.id} className="hover:bg-surface-container-high/40 transition-colors">
                        <td className="p-3 font-bold text-primary">{c.product_id}</td>
                        <td className="p-3">{c.candidate_category}</td>
                        <td className="p-3">{c.candidate_subcategory}</td>
                        <td className="p-3">{c.candidate_product_type}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
                            {Math.round(c.confidence * 100)}%
                          </span>
                        </td>
                        <td className="p-3 text-[11px] text-on-surface-variant max-w-xs truncate">{c.reason}</td>
                        <td className="p-3 text-[11px] text-on-surface-variant">
                          {new Date(c.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW 4: MATCH REVIEW QUEUE (AGENT 03) */}
      {viewMode === "matching_queue" && (
        <div className="space-y-6 animate-fade-in">
          {/* Agent 3 Stats Banner */}
          {matchingStats && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20">
                <div className="text-[10px] font-label-caps text-on-surface-variant uppercase">Total Evaluations</div>
                <div className="text-xl font-bold font-mono-data text-on-surface mt-1">{matchingStats.total_evaluations}</div>
              </div>
              <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20">
                <div className="text-[10px] font-label-caps text-emerald-400 uppercase">Exact Matches</div>
                <div className="text-xl font-bold font-mono-data text-emerald-400 mt-1">{matchingStats.exact_matches}</div>
              </div>
              <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20">
                <div className="text-[10px] font-label-caps text-blue-400 uppercase">High Confidence</div>
                <div className="text-xl font-bold font-mono-data text-blue-400 mt-1">{matchingStats.high_confidence_matches}</div>
              </div>
              <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20">
                <div className="text-[10px] font-label-caps text-purple-400 uppercase">Variants Detected</div>
                <div className="text-xl font-bold font-mono-data text-purple-400 mt-1">{matchingStats.variants_detected}</div>
              </div>
              <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20">
                <div className="text-[10px] font-label-caps text-amber-400 uppercase">Needs Review</div>
                <div className="text-xl font-bold font-mono-data text-amber-400 mt-1">{matchingCandidates.length}</div>
              </div>
              <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20">
                <div className="text-[10px] font-label-caps text-cyan-400 uppercase">Memory Hits</div>
                <div className="text-xl font-bold font-mono-data text-cyan-400 mt-1">{matchingStats.memory_hit_count}</div>
              </div>
            </div>
          )}

          <div className="bg-surface-container-low border border-outline-variant/20 rounded-3xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-outline-variant/20 pb-4">
              <div>
                <h2 className="text-lg font-headline font-bold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-amber-400 text-xl">hub</span>
                  Entity Matching Review Queue
                </h2>
                <p className="text-xs text-on-surface-variant font-mono-data mt-0.5">
                  Ambiguous product pairs (confidence 0.75–0.84) held in review queue to prevent false-positive merges. Confirming or rejecting trains Agent 3 memory.
                </p>
              </div>
              <button
                onClick={fetchMatchingCandidates}
                disabled={matchingLoading}
                className="px-3 py-1.5 bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-xl text-xs font-mono-data flex items-center gap-1.5 transition-all"
              >
                <span className="material-symbols-outlined text-xs">refresh</span>
                Refresh
              </button>
            </div>

            {matchingLoading ? (
              <LoadingSpinner label="Querying matching review queue..." />
            ) : matchingCandidates.length === 0 ? (
              <div className="p-12 text-center border border-dashed border-outline-variant/30 rounded-2xl text-on-surface-variant text-xs font-mono-data">
                No matching candidates currently in review queue. All listings merged or kept distinct with high confidence!
              </div>
            ) : (
              <div className="space-y-4">
                {matchingCandidates.map((c) => (
                  <div
                    key={c.id}
                    className="p-4 rounded-2xl bg-surface-container border border-outline-variant/20 hover:border-outline-variant/40 transition-all space-y-3"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-outline-variant/15 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded text-[10px] font-mono-data font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                          {c.method.toUpperCase()} ({Math.round(c.confidence_score * 100)}%)
                        </span>
                        <span className="text-xs font-mono-data text-on-surface-variant">
                          Platform: <strong className="text-on-surface">{c.platform}</strong> ({c.platform_product_id})
                        </span>
                      </div>
                      <div className="text-[11px] font-mono-data text-on-surface-variant">
                        Queued: {new Date(c.created_at).toLocaleString()}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono-data">
                      <div className="p-3 rounded-xl bg-surface-container-high border border-outline-variant/20 space-y-1">
                        <div className="text-[10px] text-primary uppercase font-bold">Incoming Listing</div>
                        <div className="text-xs font-semibold text-on-surface">{c.product_a_title || c.platform_product_id}</div>
                        <div className="text-[10px] text-on-surface-variant">ID: {c.platform_product_id}</div>
                      </div>

                      <div className="p-3 rounded-xl bg-surface-container-high border border-outline-variant/20 space-y-1">
                        <div className="text-[10px] text-purple-400 uppercase font-bold">Candidate Target Product</div>
                        <div className="text-xs font-semibold text-on-surface">{c.product_b_title || c.candidate_unified_id}</div>
                        <div className="text-[10px] text-on-surface-variant">Unified ID: {c.candidate_unified_id}</div>
                      </div>
                    </div>

                    {c.reasons && c.reasons.length > 0 && (
                      <div className="text-xs font-mono-data text-on-surface-variant space-y-1">
                        <span className="font-bold text-[10px] uppercase text-on-surface">Matching Signals:</span>
                        <div className="flex flex-wrap gap-1">
                          {c.reasons.map((r, i) => (
                            <span key={i} className="px-2 py-0.5 rounded bg-surface-container-high text-emerald-400 text-[10px]">
                              + {r}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {c.conflicts && c.conflicts.length > 0 && (
                      <div className="text-xs font-mono-data text-on-surface-variant space-y-1">
                        <span className="font-bold text-[10px] uppercase text-amber-400">Potential Conflicts:</span>
                        <div className="flex flex-wrap gap-1">
                          {c.conflicts.map((conf, i) => (
                            <span key={i} className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-[10px]">
                              ! {conf}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="pt-2 border-t border-outline-variant/15 flex flex-wrap items-center justify-end gap-2">
                      <button
                        onClick={() => handleResolveMatchCandidate(c.id, "confirm_match")}
                        disabled={resolvingCandidateId === c.id}
                        className="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl text-xs font-mono-data font-bold flex items-center gap-1 transition-all disabled:opacity-50"
                      >
                        <span className="material-symbols-outlined text-xs">check_circle</span>
                        Confirm Match
                      </button>
                      <button
                        onClick={() => handleResolveMatchCandidate(c.id, "confirm_variant")}
                        disabled={resolvingCandidateId === c.id}
                        className="px-3 py-1.5 bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded-xl text-xs font-mono-data font-bold flex items-center gap-1 transition-all disabled:opacity-50"
                      >
                        <span className="material-symbols-outlined text-xs">tune</span>
                        Confirm Variant
                      </button>
                      <button
                        onClick={() => handleResolveMatchCandidate(c.id, "reject_match")}
                        disabled={resolvingCandidateId === c.id}
                        className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-xl text-xs font-mono-data font-bold flex items-center gap-1 transition-all disabled:opacity-50"
                      >
                        <span className="material-symbols-outlined text-xs">cancel</span>
                        Reject Match
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Multi-Platform & AI Intelligence Product Modal */}
      {selectedProductId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div
            className="bg-surface-container border border-outline-variant/30 rounded-3xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 md:p-8 space-y-6 animate-scale-up"
            onClick={(e) => e.stopPropagation()}
          >
            {detailLoading ? (
              <LoadingSpinner label="Querying multi-platform intelligence..." />
            ) : detailData ? (
              <>
                {/* Modal Header */}
                <div className="flex items-start justify-between gap-4 border-b border-outline-variant/20 pb-4">
                  <div className="flex items-start gap-4">
                    {detailData.unified_product.primary_image && (
                      <img
                        src={detailData.unified_product.primary_image}
                        alt={detailData.unified_product.canonical_name}
                        className="w-16 h-16 md:w-20 md:h-20 rounded-2xl object-cover border border-outline-variant/30 shrink-0"
                      />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-label-caps font-bold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                          {detailData.unified_product.brand || "Canonical Entity"}
                        </span>
                        <span className="text-xs font-mono-data text-on-surface-variant">
                          ID: {detailData.unified_product.unified_product_id}
                        </span>
                        {getConfidenceBadge(
                          detailData.unified_product.category_confidence || 1.0,
                          detailData.unified_product.needs_review
                        )}
                      </div>
                      <h2 className="text-xl font-headline font-bold text-on-surface mt-1">
                        {detailData.unified_product.canonical_name}
                      </h2>
                      {/* Breadcrumbs */}
                      <div className="text-xs font-mono-data text-primary mt-1 flex items-center gap-1">
                        <span className="material-symbols-outlined text-xs">folder</span>
                        {detailData.unified_product.taxonomy_path && detailData.unified_product.taxonomy_path.length > 0
                          ? detailData.unified_product.taxonomy_path.join(" > ")
                          : detailData.unified_product.category}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => setSelectedProductId(null)}
                    className="p-2 rounded-xl text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-all"
                  >
                    <span className="material-symbols-outlined text-xl">close</span>
                  </button>
                </div>

                {/* Sub-Navigation Tabs */}
                <div className="flex flex-wrap gap-2 border-b border-outline-variant/20 pb-2">
                  <button
                    onClick={() => handleTabSelect("overview")}
                    className={`px-3 py-1.5 rounded-xl text-xs font-headline font-semibold transition-all flex items-center gap-1.5 ${
                      activeModalTab === "overview"
                        ? "bg-primary text-on-primary shadow-sm"
                        : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">compare_arrows</span>
                    Marketplace Listings
                  </button>
                  <button
                    onClick={() => handleTabSelect("taxonomy")}
                    className={`px-3 py-1.5 rounded-xl text-xs font-headline font-semibold transition-all flex items-center gap-1.5 ${
                      activeModalTab === "taxonomy"
                        ? "bg-primary text-on-primary shadow-sm"
                        : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">category</span>
                    Taxonomy & Categorization
                  </button>
                  <button
                    onClick={() => handleTabSelect("matching")}
                    className={`px-3 py-1.5 rounded-xl text-xs font-headline font-semibold transition-all flex items-center gap-1.5 ${
                      activeModalTab === "matching"
                        ? "bg-primary text-on-primary shadow-sm"
                        : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">hub</span>
                    Match Intelligence
                  </button>
                  <button
                    onClick={() => handleTabSelect("ai_analysis")}
                    className={`px-3 py-1.5 rounded-xl text-xs font-headline font-semibold transition-all flex items-center gap-1.5 ${
                      activeModalTab === "ai_analysis"
                        ? "bg-primary text-on-primary shadow-sm"
                        : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">psychology</span>
                    AI Analysis
                  </button>
                  <button
                    onClick={() => handleTabSelect("ai_summary")}
                    className={`px-3 py-1.5 rounded-xl text-xs font-headline font-semibold transition-all flex items-center gap-1.5 ${
                      activeModalTab === "ai_summary"
                        ? "bg-primary text-on-primary shadow-sm"
                        : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">summarize</span>
                    AI Executive Summary
                  </button>
                  <button
                    onClick={() => handleTabSelect("ai_comparison")}
                    className={`px-3 py-1.5 rounded-xl text-xs font-headline font-semibold transition-all flex items-center gap-1.5 ${
                      activeModalTab === "ai_comparison"
                        ? "bg-primary text-on-primary shadow-sm"
                        : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">store</span>
                    Market Comparison
                  </button>
                  <button
                    onClick={() => handleTabSelect("ai_trend")}
                    className={`px-3 py-1.5 rounded-xl text-xs font-headline font-semibold transition-all flex items-center gap-1.5 ${
                      activeModalTab === "ai_trend"
                        ? "bg-primary text-on-primary shadow-sm"
                        : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">trending_up</span>
                    Predictive Trend
                  </button>
                </div>


                {/* 1. OVERVIEW TAB */}
                {activeModalTab === "overview" && (
                  <div className="space-y-6">
                    {/* Platform Comparison Table */}
                    <div className="space-y-3">
                      <h3 className="text-sm font-headline font-bold text-on-surface flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary text-base">compare_arrows</span>
                        Cross-Platform Marketplace Comparison
                      </h3>

                      <div className="overflow-x-auto rounded-2xl border border-outline-variant/20 bg-surface-container-low">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-surface-container-high/60 text-on-surface-variant font-label-caps uppercase text-[10px] border-b border-outline-variant/20">
                            <tr>
                              <th className="p-3">Platform</th>
                              <th className="p-3">Seller / Vendor</th>
                              <th className="p-3">Live Price</th>
                              <th className="p-3">Rating</th>
                              <th className="p-3">Status</th>
                              <th className="p-3 text-right">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-outline-variant/10 font-mono-data">
                            {detailData.platform_listings.map((item) => (
                              <tr key={item.id} className="hover:bg-surface-container-high/40 transition-colors">
                                <td className="p-3 font-bold text-on-surface flex items-center gap-2">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                                      item.platform.toLowerCase() === "daraz"
                                        ? "bg-amber-500 text-black"
                                        : "bg-emerald-500 text-white"
                                    }`}
                                  >
                                    {item.platform}
                                  </span>
                                  {item.store_domain && (
                                    <span className="text-[10px] text-on-surface-variant">{item.store_domain}</span>
                                  )}
                                </td>
                                <td className="p-3 text-on-surface-variant">{item.vendor || item.seller_name || "N/A"}</td>
                                <td className="p-3 font-bold text-on-surface">{item.price_formatted}</td>
                                <td className="p-3 text-amber-400 font-bold flex items-center gap-1">
                                  <span className="material-symbols-outlined text-xs">star</span>
                                  <span>{item.rating.toFixed(1)}</span>
                                </td>
                                <td className="p-3">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[9px] font-mono-data ${
                                      item.available
                                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                        : "bg-red-500/10 text-red-400 border border-red-500/20"
                                    }`}
                                  >
                                    {item.available ? "IN STOCK" : "OUT OF STOCK"}
                                  </span>
                                </td>
                                <td className="p-3 text-right">
                                  <a
                                    href={item.product_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-3 py-1 bg-surface-container-high hover:bg-primary hover:text-on-primary rounded-lg text-xs font-mono-data inline-flex items-center gap-1 transition-all"
                                  >
                                    <span>View Listing</span>
                                    <span className="material-symbols-outlined text-xs">open_in_new</span>
                                  </a>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. TAXONOMY TAB */}
                {activeModalTab === "taxonomy" && (
                  <div className="space-y-6 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-sm font-headline font-bold text-on-surface flex items-center gap-2">
                          <span className="material-symbols-outlined text-primary text-base">category</span>
                          Agent 2 Taxonomy Assignment & Extraction
                        </h3>
                        <p className="text-xs text-on-surface-variant font-mono-data mt-0.5">
                          Classification and attribute extraction performed by Agent 2
                        </p>
                      </div>

                      <button
                        onClick={handleReclassifyProduct}
                        disabled={reclassifying}
                        className="px-3 py-1.5 bg-primary text-on-primary rounded-xl text-xs font-headline font-semibold hover:bg-primary/90 transition-all flex items-center gap-1.5 disabled:opacity-50"
                      >
                        <span className="material-symbols-outlined text-xs">auto_fix_high</span>
                        {reclassifying ? "Classifying..." : "Re-Classify with Agent 2"}
                      </button>
                    </div>

                    {/* Taxonomy Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20">
                        <div className="text-[10px] font-label-caps text-on-surface-variant uppercase font-bold">Primary Category</div>
                        <div className="text-sm font-bold text-primary mt-1">
                          {taxonomyAssignment?.category || detailData.unified_product.category || "Unknown"}
                        </div>
                      </div>
                      <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20">
                        <div className="text-[10px] font-label-caps text-on-surface-variant uppercase font-bold">Subcategory</div>
                        <div className="text-sm font-bold text-on-surface mt-1">
                          {taxonomyAssignment?.subcategory || detailData.unified_product.subcategory || "Unknown"}
                        </div>
                      </div>
                      <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20">
                        <div className="text-[10px] font-label-caps text-on-surface-variant uppercase font-bold">Product Type</div>
                        <div className="text-sm font-bold text-on-surface mt-1">
                          {taxonomyAssignment?.product_type || detailData.unified_product.product_type || "Unknown"}
                        </div>
                      </div>
                    </div>

                    {/* Taxonomy Path */}
                    <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-2">
                      <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                        Full Canonical Taxonomy Path
                      </span>
                      <div className="flex flex-wrap items-center gap-2 font-mono-data text-xs">
                        {(taxonomyAssignment?.taxonomy_path || detailData.unified_product.taxonomy_path || []).map((step, idx, arr) => (
                          <React.Fragment key={idx}>
                            <span className="px-2.5 py-1 bg-surface-container-high rounded-lg text-on-surface font-semibold">
                              {step}
                            </span>
                            {idx < arr.length - 1 && (
                              <span className="material-symbols-outlined text-xs text-on-surface-variant">
                                chevron_right
                              </span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>

                    {/* Extracted Attributes & Specifications */}
                    <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-3">
                      <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                        Extracted Product Specifications & Attributes
                      </span>
                      {Object.keys(taxonomyAssignment?.attributes || detailData.unified_product.attributes || {}).length === 0 ? (
                        <div className="text-xs text-on-surface-variant font-mono-data">
                          No structured attributes extracted.
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 font-mono-data text-xs">
                          {Object.entries(taxonomyAssignment?.attributes || detailData.unified_product.attributes || {}).map(([k, v]) => (
                            <div key={k} className="p-2.5 rounded-xl bg-surface-container-high border border-outline-variant/20">
                              <div className="text-[10px] text-on-surface-variant uppercase font-bold">{k}</div>
                              <div className="text-xs font-bold text-on-surface mt-0.5">{String(v)}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* MATCH INTELLIGENCE TAB (AGENT 03) */}
                {activeModalTab === "matching" && (
                  <div className="space-y-6 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono-data font-bold bg-primary/20 text-primary border border-primary/30">
                          AGENT 03 DEDUPLICATION
                        </span>
                        <span className="text-xs text-on-surface-variant">
                          Cross-platform entity resolution & variant isolation
                        </span>
                      </div>
                    </div>

                    {/* Listing Match Cards */}
                    <div className="space-y-3">
                      <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                        Linked Marketplace Listings ({detailData.platform_listings.length})
                      </span>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {detailData.platform_listings.map((l) => (
                          <div key={l.id} className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-3">
                            <div className="flex items-center justify-between border-b border-outline-variant/15 pb-2">
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono-data font-bold uppercase bg-primary/10 text-primary">
                                {l.platform}
                              </span>
                              <span className="text-xs font-mono-data font-bold text-on-surface">
                                {l.currency} {l.price.toLocaleString()}
                              </span>
                            </div>

                            <div className="space-y-1 text-xs font-mono-data">
                              <div className="text-on-surface font-medium line-clamp-2">{l.raw_title || l.title}</div>
                              <div className="text-on-surface-variant text-[11px]">ID: {l.platform_product_id}</div>
                              {l.store_domain && (
                                <div className="text-on-surface-variant text-[11px]">Store: {l.store_domain}</div>
                              )}
                            </div>

                            <div className="pt-2 border-t border-outline-variant/15 flex items-center justify-between text-[11px] font-mono-data">
                              <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                                l.match_status === "matched" ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"
                              }`}>
                                {l.match_status ? l.match_status.toUpperCase() : "MATCHED"} ({Math.round((l.match_confidence || 1.0) * 100)}%)
                              </span>
                              <span className="text-on-surface-variant text-[10px]">
                                Method: {l.match_method || "canonical_entity"}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {historyData && historyData.snapshots && historyData.snapshots.length > 0 && (
                      <div className="text-[11px] font-mono-data text-on-surface-variant">
                        Tracked Historical Snapshots: <strong className="text-on-surface">{historyData.snapshots.length}</strong>
                      </div>
                    )}


                    {/* Match Decisions History */}
                    {matchingDecisions.length > 0 && (
                      <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-3">
                        <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                          Agent 3 Match Decisions & Audit Trail ({matchingDecisions.length})
                        </span>
                        <div className="space-y-2">
                          {matchingDecisions.map((dec) => (
                            <div key={dec.id} className="p-3 rounded-xl bg-surface-container-high/60 border border-outline-variant/20 text-xs font-mono-data space-y-1.5">
                              <div className="flex items-center justify-between">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  dec.decision === "EXACT_MATCH" ? "bg-emerald-500/20 text-emerald-400" :
                                  dec.decision === "HIGH_CONFIDENCE_MATCH" ? "bg-blue-500/20 text-blue-400" :
                                  dec.decision === "VARIANT" ? "bg-purple-500/20 text-purple-400" :
                                  dec.decision === "NEEDS_REVIEW" ? "bg-amber-500/20 text-amber-400" : "bg-gray-500/20 text-gray-400"
                                }`}>
                                  {dec.decision} ({Math.round(dec.confidence * 100)}%)
                                </span>
                                <span className="text-[10px] text-on-surface-variant">
                                  {new Date(dec.created_at).toLocaleString()}
                                </span>
                              </div>
                              <div className="text-on-surface text-[11px]">
                                Method: <strong>{dec.match_method}</strong> | LLM: {dec.llm_used ? "Yes (Selective)" : "No (Deterministic)"}
                              </div>
                              {dec.reasons && dec.reasons.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {dec.reasons.map((r, i) => (
                                    <span key={i} className="px-1.5 py-0.2 rounded bg-surface-container-highest text-emerald-400 text-[9px]">
                                      + {r}
                                    </span>
                                  ))}
                                </div>
                              )}
                              {dec.variant_attributes && Object.keys(dec.variant_attributes).length > 0 && (
                                <div className="text-[10px] text-purple-400">
                                  Variant Diffs: {JSON.stringify(dec.variant_attributes)}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 3. AI ANALYSIS TAB */}
                {activeModalTab === "ai_analysis" && (

                  <div className="space-y-5 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono-data font-bold bg-primary/20 text-primary border border-primary/30">
                          GROUNDED LLM
                        </span>
                        <span className="text-xs text-on-surface-variant">
                          Synthesized across all marketplace listings
                        </span>
                      </div>
                      <button
                        onClick={() => handleFetchAiAnalysis(true)}
                        disabled={aiLoading}
                        className="px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-lg text-xs font-mono-data flex items-center gap-1 transition-all disabled:opacity-50"
                      >
                        <span className="material-symbols-outlined text-xs">refresh</span>
                        Re-Analyze
                      </button>
                    </div>

                    {aiLoading ? (
                      <LoadingSpinner label="Generating grounded product intelligence..." />
                    ) : aiError ? (
                      <ErrorState message={aiError} onRetry={() => handleFetchAiAnalysis(true)} />
                    ) : aiAnalysis ? (
                      <div className="space-y-4">
                        <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-2">
                          <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                            Strategic Synthesis
                          </span>
                          <p className="text-xs text-on-surface leading-relaxed">{aiAnalysis.summary}</p>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-2">
                            <span className="text-xs font-label-caps text-emerald-400 uppercase font-bold flex items-center gap-1">
                              <span className="material-symbols-outlined text-sm">trending_up</span>
                              Market Opportunities
                            </span>
                            <ul className="text-xs space-y-1.5 text-on-surface">
                              {aiAnalysis.opportunities.map((item, idx) => (
                                <li key={idx} className="flex items-start gap-1.5">
                                  <span className="text-emerald-400">•</span>
                                  <span>{item}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-2">
                            <span className="text-xs font-label-caps text-amber-400 uppercase font-bold flex items-center gap-1">
                              <span className="material-symbols-outlined text-sm">warning</span>
                              Risks & Constraints
                            </span>
                            <ul className="text-xs space-y-1.5 text-on-surface">
                              {aiAnalysis.risks.map((item, idx) => (
                                <li key={idx} className="flex items-start gap-1.5">
                                  <span className="text-amber-400">•</span>
                                  <span>{item}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}

                {/* 4. AI SUMMARY TAB */}
                {activeModalTab === "ai_summary" && (
                  <div className="space-y-5 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono-data font-bold bg-primary/20 text-primary border border-primary/30">
                          EXECUTIVE REPORT
                        </span>
                        <span className="text-xs text-on-surface-variant">High-level briefing & positioning</span>
                      </div>
                      <button
                        onClick={() => handleFetchAiSummary(true)}
                        disabled={aiLoading}
                        className="px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-lg text-xs font-mono-data flex items-center gap-1 transition-all disabled:opacity-50"
                      >
                        <span className="material-symbols-outlined text-xs">refresh</span>
                        Re-Summarize
                      </button>
                    </div>

                    {aiLoading ? (
                      <LoadingSpinner label="Distilling executive takeaways..." />
                    ) : aiError ? (
                      <ErrorState message={aiError} onRetry={() => handleFetchAiSummary(true)} />
                    ) : aiSummary ? (
                      <div className="space-y-4">
                        <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-2">
                          <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                            Executive Overview
                          </span>
                          <p className="text-xs text-on-surface leading-relaxed">
                            {aiSummary.executive_summary}
                          </p>
                        </div>

                        <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-2">
                          <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                            Key Strategic Takeaways
                          </span>
                          <ul className="text-xs space-y-1.5 text-on-surface">
                            {aiSummary.key_takeaways.map((item, idx) => (
                              <li key={idx} className="flex items-start gap-2">
                                <span className="text-primary font-bold">{idx + 1}.</span>
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}

                {/* 5. AI COMPARISON TAB */}
                {activeModalTab === "ai_comparison" && (
                  <div className="space-y-5 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono-data font-bold bg-primary/20 text-primary border border-primary/30">
                          MARKET DYNAMICS
                        </span>
                        <span className="text-xs text-on-surface-variant">
                          Multi-platform arbitrage & seller variance
                        </span>
                      </div>
                      <button
                        onClick={() => handleFetchAiComparison(true)}
                        disabled={aiLoading}
                        className="px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-lg text-xs font-mono-data flex items-center gap-1 transition-all disabled:opacity-50"
                      >
                        <span className="material-symbols-outlined text-xs">refresh</span>
                        Re-Compare
                      </button>
                    </div>

                    {aiLoading ? (
                      <LoadingSpinner label="Evaluating cross-platform marketplace dynamics..." />
                    ) : aiError ? (
                      <ErrorState message={aiError} onRetry={() => handleFetchAiComparison(true)} />
                    ) : aiComparison ? (
                      <div className="space-y-4">
                        <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-2">
                          <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                            Distribution Landscape
                          </span>
                          <p className="text-xs text-on-surface leading-relaxed">
                            {aiComparison.cross_platform_overview}
                          </p>
                        </div>

                        <div className="p-4 rounded-2xl bg-primary/5 border border-primary/20 space-y-2">
                          <span className="text-xs font-label-caps text-primary uppercase font-bold">
                            Price Arbitrage & Margin Analysis
                          </span>
                          <p className="text-xs text-on-surface leading-relaxed">
                            {aiComparison.price_arbitrage_analysis}
                          </p>
                        </div>

                        {aiComparison.platform_comparison_breakdown.length > 0 && (
                          <div className="space-y-2">
                            <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                              Platform Strengths & Risks
                            </span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                              {aiComparison.platform_comparison_breakdown.map((item, idx) => (
                                <div key={idx} className="p-3 rounded-xl bg-surface-container-low border border-outline-variant/20 space-y-1">
                                  <div className="text-xs font-bold text-on-surface">{item.platform}</div>
                                  <div className="text-[11px] text-emerald-400"><strong>Strength:</strong> {item.competitive_strength}</div>
                                  <div className="text-[11px] text-amber-400"><strong>Risk:</strong> {item.risk_factor}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : null}
                  </div>
                )}

                {/* 6. AI PREDICTIVE TREND TAB */}
                {activeModalTab === "ai_trend" && (
                  <div className="space-y-5 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono-data font-bold bg-primary/20 text-primary border border-primary/30">
                          PREDICTIVE VELOCITY
                        </span>
                        <span className="text-xs text-on-surface-variant">
                          Historical snapshot price action & 30-day outlook
                        </span>
                      </div>
                      <button
                        onClick={() => handleFetchAiTrend(true)}
                        disabled={aiLoading}
                        className="px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-lg text-xs font-mono-data flex items-center gap-1 transition-all disabled:opacity-50"
                      >
                        <span className="material-symbols-outlined text-xs">refresh</span>
                        Re-Analyze Trend
                      </button>
                    </div>

                    {aiLoading ? (
                      <LoadingSpinner label="Calculating price trajectory & momentum..." />
                    ) : aiError ? (
                      <ErrorState message={aiError} onRetry={() => handleFetchAiTrend(true)} />
                    ) : aiTrend ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div className="p-3 rounded-xl bg-surface-container-low border border-outline-variant/20">
                            <div className="text-[10px] font-label-caps text-on-surface-variant uppercase">Trajectory</div>
                            <div className="text-sm font-bold text-primary mt-0.5">{aiTrend.trend_trajectory}</div>
                          </div>
                          <div className="p-3 rounded-xl bg-surface-container-low border border-outline-variant/20">
                            <div className="text-[10px] font-label-caps text-on-surface-variant uppercase">Volatility Risk</div>
                            <div className="text-sm font-bold text-amber-400 mt-0.5">{aiTrend.volatility_risk}</div>
                          </div>
                          <div className="p-3 rounded-xl bg-surface-container-low border border-outline-variant/20">
                            <div className="text-[10px] font-label-caps text-on-surface-variant uppercase">Velocity</div>
                            <div className="text-xs font-mono-data text-on-surface mt-0.5 truncate">{aiTrend.velocity_assessment}</div>
                          </div>
                        </div>

                        <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-2">
                          <span className="text-xs font-label-caps text-on-surface-variant uppercase font-bold">
                            Historical Price Action
                          </span>
                          <p className="text-xs text-on-surface leading-relaxed">
                            {aiTrend.historical_price_action}
                          </p>
                        </div>

                        <div className="p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 space-y-2">
                          <span className="text-xs font-label-caps text-emerald-400 uppercase font-bold flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-sm">insights</span>
                            30-Day Predictive Trajectory
                          </span>
                          <p className="text-xs text-on-surface leading-relaxed">
                            {aiTrend.predictive_outlook_30d}
                          </p>
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};
