import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  CheckCircle2,
  RefreshCw,
  Cpu,
  BrainCircuit,
  History,
  Layers,
  Sparkles,
  Sliders,
  Send,
  HelpCircle,
  Database
} from "lucide-react";
import { dataQualityService } from "../../services/domainServices";

import type {
  DataQualityStatusResponse,
  DataQualityValidationResponse,
  DataQualityMemoryItem,
  AIAgentRunItem
} from "../../types";

export const DataQualityAgentPage: React.FC = () => {
  const [statusData, setStatusData] = useState<DataQualityStatusResponse | null>(null);
  const [results, setResults] = useState<DataQualityValidationResponse[]>([]);
  const [runs, setRuns] = useState<AIAgentRunItem[]>([]);
  const [memories, setMemories] = useState<DataQualityMemoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "sandbox" | "history" | "memory">("overview");

  // Sandbox state
  const [sandboxPlatform, setSandboxPlatform] = useState("Daraz");
  const [sandboxProvider, setSandboxProvider] = useState("daraz_official");
  const [sandboxAllowLLM, setSandboxAllowLLM] = useState(true);
  const [sandboxPayload, setSandboxPayload] = useState<string>(
    JSON.stringify(
      {
        product_id: "DARAZ_SAMPLE_101",
        title: "Anker Soundcore Life P2 True Wireless Earbuds Bluetooth 5.0",
        brand: "Anker",
        price: 6499.0,
        currency: "PKR",
        original_price: 7999.0,
        rating: 4.8,
        review_count: 312,
        available: true,
        category: "Audio & Headphones",
        product_url: "https://www.daraz.pk/products/anker-p2-i101.html",
        image_url: "https://img.daraz.pk/images/anker-p2.jpg"
      },
      null,
      2
    )
  );
  const [sandboxLoading, setSandboxLoading] = useState(false);
  const [sandboxResult, setSandboxResult] = useState<DataQualityValidationResponse | null>(null);
  const [sandboxError, setSandboxError] = useState<string | null>(null);

  // Filter state
  const [filterPlatform, setFilterPlatform] = useState<string>("");
  const [filterClassification, setFilterClassification] = useState<string>("");

  const loadData = async (isRefresh: boolean = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const [statusRes, resultsRes, runsRes, memRes] = await Promise.all([
        dataQualityService.getStatus().catch(() => null),
        dataQualityService.getResults({
          platform: filterPlatform || undefined,
          classification: filterClassification || undefined,
          page_size: 25
        }).catch(() => null),
        dataQualityService.getRunHistory(20).catch(() => null),
        dataQualityService.getMemoryItems().catch(() => null)
      ]);

      if (statusRes?.data) setStatusData(statusRes.data);
      if (resultsRes?.data?.items) setResults(resultsRes.data.items);
      if (runsRes?.data?.runs) setRuns(runsRes.data.runs);
      if (memRes?.data?.items) setMemories(memRes.data.items);
    } catch (err) {
      console.error("Failed to load Data Quality agent data", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filterPlatform, filterClassification]);

  const handleTestSandbox = async () => {
    setSandboxLoading(true);
    setSandboxError(null);
    setSandboxResult(null);
    try {
      const parsed = JSON.parse(sandboxPayload);
      const res = await dataQualityService.validateSingle(
        parsed,
        sandboxPlatform,
        sandboxProvider,
        sandboxAllowLLM
      );
      if (res?.data) {
        setSandboxResult(res.data);
        // Refresh history & metrics in background
        loadData(true);
      }
    } catch (err: any) {
      setSandboxError(err?.message || "Invalid JSON payload or evaluation error.");
    } finally {
      setSandboxLoading(false);
    }
  };

  const getClassificationBadge = (classification: string, score: number) => {
    switch (classification) {
      case "valid":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> Valid ({score})
          </span>
        );
      case "valid_with_warnings":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" /> Warnings ({score})
          </span>
        );
      case "needs_review":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <HelpCircle className="w-3.5 h-3.5" /> Needs Review ({score})
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" /> Rejected ({score})
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            {classification} ({score})
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
        <div className="text-sm font-medium text-slate-400">Loading Data Quality & Validation Agent...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">

      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-850 to-indigo-950/40 border border-slate-800 p-6 shadow-xl">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <ShieldCheck className="w-64 h-64 text-indigo-400" />
        </div>

        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold text-white tracking-tight">
                    Data Quality & Validation Agent
                  </h1>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    ACTIVE (Agent 1/15)
                  </span>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-800 text-slate-400 border border-slate-700">
                    v1.0.0
                  </span>
                </div>
                <p className="text-sm text-slate-400 mt-1">
                  Deterministic marketplace gate & anomaly detection engine with selective Gemini LLM resolution.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mt-4">
              {[
                "Deterministic Validation Gate",
                "Impossible Value Sanity",
                "Freshness Enforcement",
                "Spam Detection",
                "Selective Gemini LLM",
                "Persistent Memory Learning"
              ].map((cap, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800/80 text-slate-300 border border-slate-750"
                >
                  {cap}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3 self-end md:self-auto">
            <button
              onClick={() => loadData(true)}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-750 rounded-xl border border-slate-700 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin text-indigo-400" : ""}`} />
              Refresh Agent
            </button>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        {[
          { id: "overview", label: "Agent Overview & Metrics", icon: Layers },
          { id: "sandbox", label: "Validation Sandbox", icon: Sliders },
          { id: "history", label: "Evaluation Stream", icon: History },
          { id: "memory", label: "Learned Provider Memory", icon: BrainCircuit }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition ${
                isActive
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-850"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW & METRICS */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Key Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <span>Average Quality Score</span>
                <Sparkles className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">
                  {statusData?.overall_average_score ?? 100.0}
                </span>
                <span className="text-sm font-medium text-slate-400">/ 100</span>
              </div>
              <div className="mt-2 text-xs text-emerald-400 font-medium">
                Deterministic Scoring Model
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <span>Total Validated</span>
                <Database className="w-4 h-4 text-blue-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">
                  {statusData?.total_products_validated ?? results.length}
                </span>
                <span className="text-xs text-slate-400 font-normal">marketplace items</span>
              </div>
              <div className="mt-2 text-xs text-slate-400">
                {statusData?.total_runs ?? runs.length} total agent execution runs
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <span>Validation Breakdown</span>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="mt-3 flex items-center justify-between gap-2">
                <div className="text-center">
                  <div className="text-sm font-bold text-emerald-400">{statusData?.valid_count ?? 0}</div>
                  <div className="text-[10px] text-slate-400 uppercase">Valid</div>
                </div>
                <div className="text-center">
                  <div className="text-sm font-bold text-amber-400">{statusData?.warning_count ?? 0}</div>
                  <div className="text-[10px] text-slate-400 uppercase">Warnings</div>
                </div>
                <div className="text-center">
                  <div className="text-sm font-bold text-blue-400">{statusData?.needs_review_count ?? 0}</div>
                  <div className="text-[10px] text-slate-400 uppercase">Review</div>
                </div>
                <div className="text-center">
                  <div className="text-sm font-bold text-rose-400">{statusData?.rejected_count ?? 0}</div>
                  <div className="text-[10px] text-slate-400 uppercase">Rejected</div>
                </div>
              </div>
              <div className="mt-2 w-full bg-slate-800 h-1.5 rounded-full overflow-hidden flex">
                <div
                  className="bg-emerald-500 h-full"
                  style={{
                    width: `${
                      statusData?.total_products_validated
                        ? ((statusData.valid_count / statusData.total_products_validated) * 100)
                        : 100
                    }%`
                  }}
                ></div>
                <div
                  className="bg-amber-500 h-full"
                  style={{
                    width: `${
                      statusData?.total_products_validated
                        ? ((statusData.warning_count / statusData.total_products_validated) * 100)
                        : 0
                    }%`
                  }}
                ></div>
                <div
                  className="bg-rose-500 h-full"
                  style={{
                    width: `${
                      statusData?.total_products_validated
                        ? ((statusData.rejected_count / statusData.total_products_validated) * 100)
                        : 0
                    }%`
                  }}
                ></div>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <span>Learned Memory</span>
                <BrainCircuit className="w-4 h-4 text-purple-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">
                  {statusData?.total_memory_items ?? memories.length}
                </span>
                <span className="text-xs text-slate-400 font-normal">active patterns</span>
              </div>
              <div className="mt-2 text-xs text-purple-400">
                Persistent provider reliability & defect models
              </div>
            </div>
          </div>

          {/* Provider Reliability Profile Cards */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">Provider Reliability Index</h3>
                <p className="text-xs text-slate-400">
                  Continuous performance evaluation across scraping connectors & direct APIs.
                </p>
              </div>
            </div>

            {statusData?.provider_reliabilities && statusData.provider_reliabilities.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {statusData.provider_reliabilities.map((prov, i) => (
                  <div
                    key={i}
                    className="p-4 rounded-xl bg-slate-850 border border-slate-750 hover:border-slate-700 transition space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-white text-sm">{prov.provider}</div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
                        {prov.platform}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center py-1 bg-slate-900/60 rounded-lg">
                      <div>
                        <div className="text-xs text-slate-400">Evaluated</div>
                        <div className="text-sm font-bold text-white">{prov.total_evaluated}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-400">Pass Rate</div>
                        <div className="text-sm font-bold text-emerald-400">
                          {Math.round(prov.valid_rate * 100)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-400">Avg Score</div>
                        <div className="text-sm font-bold text-indigo-400">{prov.avg_score}</div>
                      </div>
                    </div>

                    {prov.top_issues && prov.top_issues.length > 0 && (
                      <div className="text-xs text-slate-400">
                        <span className="text-slate-500">Top Anomaly:</span>{" "}
                        <span className="text-amber-400 font-mono">{prov.top_issues[0]}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 text-sm bg-slate-850/50 rounded-xl border border-slate-800 border-dashed">
                Provider reliability profiles will populate as marketplace listings are ingested.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: VALIDATION SANDBOX */}
      {activeTab === "sandbox" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Interactive Input */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Sliders className="w-5 h-5 text-indigo-400" /> Validation Input Sandbox
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Test raw or normalized product payloads against deterministic rules & Gemini LLM resolver.
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Platform</label>
                <select
                  value={sandboxPlatform}
                  onChange={(e) => setSandboxPlatform(e.target.value)}
                  className="w-full bg-slate-850 border border-slate-750 text-white rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="Daraz">Daraz</option>
                  <option value="Shopify">Shopify</option>
                  <option value="Amazon">Amazon</option>
                  <option value="AliExpress">AliExpress</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Source Provider</label>
                <select
                  value={sandboxProvider}
                  onChange={(e) => setSandboxProvider(e.target.value)}
                  className="w-full bg-slate-850 border border-slate-750 text-white rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="daraz_official">daraz_official</option>
                  <option value="shopify_scout">shopify_scout</option>
                  <option value="shopscraper">shopscraper</option>
                  <option value="direct">direct</option>
                </select>
              </div>

              <div className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  id="allowLLM"
                  checked={sandboxAllowLLM}
                  onChange={(e) => setSandboxAllowLLM(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 bg-slate-800 border-slate-700 focus:ring-0"
                />
                <label htmlFor="allowLLM" className="text-xs font-medium text-slate-300 cursor-pointer">
                  Allow Gemini LLM
                </label>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-400">Product JSON Payload</label>
                <div className="flex gap-2">
                  <button
                    onClick={() =>
                      setSandboxPayload(
                        JSON.stringify(
                          {
                            product_id: "DARAZ_BAD_99",
                            title: "Cheap Earphones Cheap Best Cheap Buy Cheap Deals !!!!!!",
                            price: -50.0,
                            currency: "PKR",
                            rating: 7.2,
                            review_count: -3,
                            product_url: "invalid-url-format"
                          },
                          null,
                          2
                        )
                      )
                    }
                    className="text-[11px] text-rose-400 hover:underline"
                  >
                    Load Malformed Sample
                  </button>
                  <button
                    onClick={() =>
                      setSandboxPayload(
                        JSON.stringify(
                          {
                            product_id: "SHOP_AMB_01",
                            title: "Taez Premium Ultra-Fast Type-C Charging Cable 65W Braided",
                            price: 18.99,
                            currency: "USD",
                            brand: null,
                            category: "9042",
                            product_url: "https://shop.myshopify.com/products/cable",
                            image_url: "https://shop.myshopify.com/cable.jpg"
                          },
                          null,
                          2
                        )
                      )
                    }
                    className="text-[11px] text-indigo-400 hover:underline"
                  >
                    Load Ambiguous Sample (LLM)
                  </button>
                </div>
              </div>
              <textarea
                value={sandboxPayload}
                onChange={(e) => setSandboxPayload(e.target.value)}
                rows={12}
                className="w-full bg-slate-950 font-mono text-xs text-slate-200 border border-slate-800 rounded-xl p-3 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {sandboxError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{sandboxError}</span>
              </div>
            )}

            <button
              onClick={handleTestSandbox}
              disabled={sandboxLoading}
              className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/25 transition disabled:opacity-50"
            >
              {sandboxLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Evaluating Rules & LLM...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" /> Run Quality Validation
                </>
              )}
            </button>
          </div>

          {/* Right Column: Live Validation Results */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Cpu className="w-5 h-5 text-indigo-400" /> Evaluation Audit Result
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Real-time validation score, classification, rule violations, and LLM resolution.
              </p>
            </div>

            {sandboxResult ? (
              <div className="space-y-4">
                {/* Result Top Summary */}
                <div className="p-4 rounded-xl bg-slate-850 border border-slate-750 flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-400 uppercase tracking-wider">Classification</div>
                    <div className="mt-1">
                      {getClassificationBadge(sandboxResult.classification, sandboxResult.overall_score)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-400 uppercase tracking-wider">Quality Score</div>
                    <div className="text-2xl font-bold text-white mt-1">
                      {sandboxResult.overall_score} <span className="text-sm font-normal text-slate-400">/ 100</span>
                    </div>
                  </div>
                </div>

                {/* Field Scores Breakdown */}
                <div className="p-4 rounded-xl bg-slate-850 border border-slate-750 space-y-2">
                  <div className="text-xs font-semibold text-slate-300">Field Quality Breakdown</div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {Object.entries(sandboxResult.field_scores || {}).map(([f, val]) => (
                      <div key={f} className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                        <div className="text-slate-400 capitalize">{f.replace("_", " ")}</div>
                        <div
                          className={`font-mono font-bold ${
                            val >= 0.9
                              ? "text-emerald-400"
                              : val >= 0.7
                              ? "text-amber-400"
                              : "text-rose-400"
                          }`}
                        >
                          {Math.round(val * 100)}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Critical Issues */}
                {sandboxResult.issues && sandboxResult.issues.length > 0 && (
                  <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 space-y-2">
                    <div className="text-xs font-bold text-rose-400 flex items-center gap-1.5">
                      <XCircle className="w-4 h-4" /> Critical Rule Violations ({sandboxResult.issues.length})
                    </div>
                    <ul className="space-y-1.5 text-xs text-rose-300">
                      {sandboxResult.issues.map((iss, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-rose-900/40 border border-rose-800/60 text-rose-300">
                            -{iss.penalty_score}
                          </span>
                          <span>
                            <strong>{iss.field}:</strong> {iss.message}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Warnings */}
                {sandboxResult.warnings && sandboxResult.warnings.length > 0 && (
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-2">
                    <div className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4" /> Non-Critical Warnings ({sandboxResult.warnings.length})
                    </div>
                    <ul className="space-y-1.5 text-xs text-amber-300">
                      {sandboxResult.warnings.map((warn, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-amber-900/40 border border-amber-800/60 text-amber-300">
                            -{warn.penalty_score}
                          </span>
                          <span>
                            <strong>{warn.field}:</strong> {warn.message}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Gemini LLM Resolution Card */}
                {sandboxResult.used_llm && sandboxResult.llm_resolution && (
                  <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 space-y-2">
                    <div className="text-xs font-bold text-purple-400 flex items-center gap-1.5">
                      <Sparkles className="w-4 h-4" /> Gemini Ambiguity Resolution
                    </div>
                    <div className="text-xs text-slate-300 space-y-1">
                      {sandboxResult.llm_resolution.extracted_brand && (
                        <div>
                          <span className="text-slate-400">Extracted Brand:</span>{" "}
                          <span className="font-semibold text-purple-300">
                            {sandboxResult.llm_resolution.extracted_brand}
                          </span>
                        </div>
                      )}
                      {sandboxResult.llm_resolution.mapped_category && (
                        <div>
                          <span className="text-slate-400">Mapped Category:</span>{" "}
                          <span className="font-semibold text-purple-300">
                            {sandboxResult.llm_resolution.mapped_category}
                          </span>
                        </div>
                      )}
                      <div>
                        <span className="text-slate-400">Assessment:</span>{" "}
                        <span>{sandboxResult.llm_resolution.quality_assessment}</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Confidence: {Math.round((sandboxResult.llm_resolution.confidence || 0.9) * 100)}% | Model:{" "}
                        {sandboxResult.llm_resolution.model || "gemini-3.5-flash"}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-12 text-center text-slate-500 text-sm bg-slate-850/50 rounded-xl border border-slate-800 border-dashed">
                Enter a product payload and click "Run Quality Validation" to inspect the audit result.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: EVALUATION STREAM */}
      {activeTab === "history" && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-white">Marketplace Validation Stream</h3>
              <p className="text-xs text-slate-400">Audit log of all products validated by the agent.</p>
            </div>

            <div className="flex items-center gap-3">
              <select
                value={filterPlatform}
                onChange={(e) => setFilterPlatform(e.target.value)}
                className="bg-slate-850 border border-slate-750 text-white rounded-xl px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Platforms</option>
                <option value="Daraz">Daraz</option>
                <option value="Shopify">Shopify</option>
              </select>

              <select
                value={filterClassification}
                onChange={(e) => setFilterClassification(e.target.value)}
                className="bg-slate-850 border border-slate-750 text-white rounded-xl px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Statuses</option>
                <option value="valid">Valid</option>
                <option value="valid_with_warnings">Warnings</option>
                <option value="needs_review">Needs Review</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-850 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="p-3">Product Title</th>
                  <th className="p-3">Platform / Provider</th>
                  <th className="p-3">Score & Status</th>
                  <th className="p-3">Issues / Warnings</th>
                  <th className="p-3">LLM</th>
                  <th className="p-3">Validated At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {results.length > 0 ? (
                  results.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-850/50 transition">
                      <td className="p-3 font-medium text-white max-w-xs truncate">
                        {r.product_title}
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          ID: {r.platform_product_id}
                        </div>
                      </td>
                      <td className="p-3">
                        <span className="font-semibold text-slate-200">{r.platform}</span>
                        <div className="text-[10px] text-slate-500">{r.source_provider}</div>
                      </td>
                      <td className="p-3">{getClassificationBadge(r.classification, r.overall_score)}</td>
                      <td className="p-3">
                        {r.issues?.length > 0 ? (
                          <span className="text-rose-400 font-medium">
                            {r.issues.length} critical issues
                          </span>
                        ) : r.warnings?.length > 0 ? (
                          <span className="text-amber-400 font-medium">
                            {r.warnings.length} warnings
                          </span>
                        ) : (
                          <span className="text-emerald-400">Clean payload</span>
                        )}
                      </td>
                      <td className="p-3">
                        {r.used_llm ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                            Gemini
                          </span>
                        ) : (
                          <span className="text-slate-500 text-[11px]">Deterministic</span>
                        )}
                      </td>
                      <td className="p-3 text-slate-400 text-[11px]">
                        {new Date(r.validated_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit"
                        })}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      No validation records found for current filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: LEARNED MEMORY */}
      {activeTab === "memory" && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-purple-400" /> Persistent Agent Memory
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Learned defect patterns, missing field tendencies, and reliability metrics across data providers.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {memories.length > 0 ? (
              memories.map((m) => (
                <div
                  key={m.id}
                  className="p-4 rounded-xl bg-slate-850 border border-slate-750 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] font-semibold uppercase bg-purple-500/10 text-purple-400 border border-purple-500/20">
                      {m.memory_type}
                    </span>
                    <span className="text-slate-500 text-[10px]">
                      Observed {m.occurrence_count} times
                    </span>
                  </div>

                  <div className="font-semibold text-white text-sm">{m.memory_key}</div>

                  <pre className="p-2.5 rounded-lg bg-slate-950 font-mono text-[11px] text-slate-300 overflow-x-auto border border-slate-800">
                    {JSON.stringify(m.memory_value, null, 2)}
                  </pre>

                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                    <span>Confidence: {Math.round(m.confidence_score * 100)}%</span>
                    <span>Last Updated: {new Date(m.last_observed_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-2 p-12 text-center text-slate-500 text-sm bg-slate-850/50 rounded-xl border border-slate-800 border-dashed">
                No persistent memory patterns logged yet. The agent learns automatically during marketplace ingestion.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
