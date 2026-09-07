import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Flame,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  Eye,
  Activity,
  Layers,
  Sparkles,
  Zap,
  Globe,
  SlidersHorizontal,
  ShieldCheck
} from 'lucide-react';
import { anomalyDetectionService } from '../../services/domainServices';
import type {
  AnomalyDetectionItem,
  AnomalyCandidateItem,
  ProductAnomalySummaryItem,
  AgentAnomalyDetectionStatsItem,
  AnomalyObservationItem
} from '../../types';

export const AnomalyDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'signals' | 'candidates' | 'analyzer'>('signals');
  const [stats, setStats] = useState<AgentAnomalyDetectionStatsItem | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyDetectionItem[]>([]);
  const [candidates, setCandidates] = useState<AnomalyCandidateItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [totalAnomalies, setTotalAnomalies] = useState(0);

  // Filters
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [platformFilter, setPlatformFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('active');
  const [candidateStatusFilter, setCandidateStatusFilter] = useState<string>('pending_review');

  // Analyzer State
  const [analyzerProductId, setAnalyzerProductId] = useState<string>('');
  const [productSummary, setProductSummary] = useState<ProductAnomalySummaryItem | null>(null);
  const [obsHistory, setObsHistory] = useState<AnomalyObservationItem[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
    loadData();
  }, [activeTab, typeFilter, severityFilter, platformFilter, statusFilter, candidateStatusFilter]);

  const loadStats = async () => {
    try {
      const res = await anomalyDetectionService.getStats();
      if (res.data) setStats(res.data);
    } catch (err) {
      console.error('Failed to load anomaly detection stats', err);
    }
  };

  const loadData = async () => {
    setIsLoading(true);
    try {
      if (activeTab === 'signals') {
        const res = await anomalyDetectionService.listAnomalies({
          anomaly_type: typeFilter,
          severity: severityFilter,
          platform: platformFilter,
          status: statusFilter,
          page_size: 50
        });
        if (res.data) {
          setAnomalies(res.data.items || []);
          setTotalAnomalies(res.data.total || 0);
        }
      } else if (activeTab === 'candidates') {
        const res = await anomalyDetectionService.listCandidates(candidateStatusFilter);
        if (res.data) {
          setCandidates(res.data.items || []);
        }
      }
    } catch (err) {
      console.error('Failed to load anomaly data', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResolveCandidate = async (candidateId: string, status: 'confirmed' | 'dismissed' | 'false_positive' | 'resolved') => {
    setResolvingId(candidateId);
    try {
      await anomalyDetectionService.resolveCandidate(candidateId, {
        status,
        notes: `Operator resolution applied via Anomaly Dashboard`
      });
      const candRes = await anomalyDetectionService.listCandidates(candidateStatusFilter);
      if (candRes.data) setCandidates(candRes.data.items || []);
      const statsRes = await anomalyDetectionService.getStats();
      if (statsRes.data) setStats(statsRes.data);
    } catch (err) {
      console.error('Failed to resolve candidate', err);
    } finally {
      setResolvingId(null);
    }
  };

  const handleAnalyzeProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!analyzerProductId.trim()) return;
    setIsAnalyzing(true);
    try {
      const summaryRes = await anomalyDetectionService.getProductSummary(analyzerProductId.trim());
      if (summaryRes.data) setProductSummary(summaryRes.data);
      const histRes = await anomalyDetectionService.getProductObservationsHistory(analyzerProductId.trim(), undefined, undefined, 30);
      if (histRes.data) setObsHistory(histRes.data.items || []);
    } catch (err) {
      console.error('Failed to analyze product anomaly', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center gap-1"><Flame className="w-3.5 h-3.5" /> Critical</span>;
      case 'high':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> High</span>;
      case 'medium':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">Medium</span>;
      default:
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-400 border border-slate-500/30">Low</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-amber-500/20 to-rose-500/20 border border-amber-500/30 text-amber-400">
              <AlertTriangle className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-amber-400 via-rose-400 to-indigo-400 bg-clip-text text-transparent">
                  Anomaly Detection Agent
                </h1>
                <span className="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  Agent 05
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                Statistical outlier detection, price spikes/crashes, rating shifts, and provider integrity monitoring.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={() => { loadStats(); loadData(); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition-all text-sm font-medium shadow-sm hover:shadow-indigo-500/10 self-start md:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-amber-400' : ''}`} />
          Refresh Feed
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <div className="text-xs text-slate-400 font-medium">Total Anomalies</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">{stats?.total_anomalies_detected || totalAnomalies}</div>
          <div className="text-[11px] text-amber-400/90 mt-1 flex items-center gap-1">
            <Zap className="w-3 h-3" /> Discovered
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <div className="text-xs text-slate-400 font-medium">Critical Severity</div>
          <div className="text-2xl font-bold text-rose-400 mt-1">{stats?.critical_anomalies_count || 0}</div>
          <div className="text-[11px] text-rose-400/90 mt-1 flex items-center gap-1">
            <Flame className="w-3 h-3" /> Immediate Alert
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <div className="text-xs text-slate-400 font-medium">High Severity</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{stats?.high_severity_count || 0}</div>
          <div className="text-[11px] text-amber-400/90 mt-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Significant Outlier
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <div className="text-xs text-slate-400 font-medium">Pending Review</div>
          <div className="text-2xl font-bold text-indigo-400 mt-1">{stats?.candidates_pending_review || candidates.length}</div>
          <div className="text-[11px] text-indigo-400/90 mt-1 flex items-center gap-1">
            <Eye className="w-3 h-3" /> Human-in-the-loop
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <div className="text-xs text-slate-400 font-medium">False Positives</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{stats?.false_positives_count || 0}</div>
          <div className="text-[11px] text-emerald-400/90 mt-1 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" /> Learned Suppression
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <div className="text-xs text-slate-400 font-medium">Analyzed Products</div>
          <div className="text-2xl font-bold text-cyan-400 mt-1">{stats?.total_analyzed_products || 0}</div>
          <div className="text-[11px] text-cyan-400/90 mt-1 flex items-center gap-1">
            <Layers className="w-3 h-3" /> Baseline Tracking
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 mb-6">
        <button
          onClick={() => setActiveTab('signals')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeTab === 'signals'
              ? 'border-amber-500 text-amber-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Zap className="w-4 h-4" />
          Live Anomaly Feed ({anomalies.length})
        </button>
        <button
          onClick={() => setActiveTab('candidates')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeTab === 'candidates'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Eye className="w-4 h-4" />
          Candidate Review Queue
        </button>
        <button
          onClick={() => setActiveTab('analyzer')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeTab === 'analyzer'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          Product Anomaly Analyzer
        </button>
      </div>

      {/* TAB 1: Live Anomaly Feed */}
      {activeTab === 'signals' && (
        <div>
          {/* Filter Bar */}
          <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80 mb-6 flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
              <SlidersHorizontal className="w-4 h-4 text-slate-500" />
              Filter By:
            </div>

            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
            >
              <option value="all">All Anomaly Types</option>
              <option value="price_spike">Price Spike</option>
              <option value="price_crash">Price Crash</option>
              <option value="unusual_discount">Unusual Discount</option>
              <option value="rating_jump">Rating Jump</option>
              <option value="rating_drop">Rating Drop</option>
              <option value="review_velocity_spike">Review Velocity Spike</option>
              <option value="availability_change">Availability Flip-Flop</option>
              <option value="cross_platform_price_anomaly">Cross-Platform Price Anomaly</option>
              <option value="platform_presence_anomaly">Platform Presence Disappearance</option>
              <option value="provider_data_anomaly">Provider Data Anomaly</option>
            </select>

            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
            >
              <option value="all">All Platforms</option>
              <option value="daraz">Daraz</option>
              <option value="shopify">Shopify</option>
              <option value="amazon">Amazon</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
            >
              <option value="active">Active Only</option>
              <option value="resolved">Resolved</option>
              <option value="false_positive">False Positives</option>
              <option value="all">All Statuses</option>
            </select>
          </div>

          {/* Anomalies List */}
          {isLoading ? (
            <div className="flex flex-col items-center justify-center p-16 text-slate-500">
              <RefreshCw className="w-8 h-8 animate-spin text-amber-500 mb-3" />
              <p className="text-sm">Evaluating statistical baselines & anomalies...</p>
            </div>
          ) : anomalies.length === 0 ? (
            <div className="p-12 rounded-2xl bg-slate-900/20 border border-dashed border-slate-800 text-center text-slate-400">
              <CheckCircle2 className="w-12 h-12 text-emerald-500/60 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-200">No Anomalies Found</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                No active anomalies match your filters. Products are currently tracking within normal statistical baseline parameters.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {anomalies.map((anom) => (
                <div
                  key={anom.id}
                  className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all shadow-sm"
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                          {anom.anomaly_type.replace(/_/g, ' ')}
                        </span>
                        {getSeverityBadge(anom.severity)}
                      </div>
                      <div className="text-xs text-slate-400 mt-1">Product ID: {anom.unified_product_id}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-extrabold bg-gradient-to-r from-amber-400 to-rose-400 bg-clip-text text-transparent">
                        Score {anom.score}
                      </div>
                      <div className="text-[11px] text-slate-400">Conf: {Math.round(anom.confidence * 100)}%</div>
                    </div>
                  </div>

                  {/* Metrics Row */}
                  <div className="grid grid-cols-3 gap-2 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 mb-3 text-center">
                    <div>
                      <div className="text-[11px] text-slate-400">Baseline</div>
                      <div className="text-xs font-semibold text-slate-200 mt-0.5">
                        {anom.baseline !== undefined ? anom.baseline : 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[11px] text-slate-400">Observed</div>
                      <div className="text-xs font-semibold text-amber-400 mt-0.5">
                        {anom.observed_value !== undefined ? anom.observed_value : 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[11px] text-slate-400">Deviation</div>
                      <div className={`text-xs font-semibold mt-0.5 ${
                        (anom.deviation_percent || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'
                      }`}>
                        {anom.deviation_percent !== undefined ? `${anom.deviation_percent > 0 ? '+' : ''}${anom.deviation_percent}%` : 'N/A'}
                      </div>
                    </div>
                  </div>

                  {/* Platforms & Evidence */}
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 pt-2 border-t border-slate-800/60">
                    <div className="flex items-center gap-1.5">
                      <Globe className="w-3.5 h-3.5 text-slate-500" />
                      <span>Platforms: {anom.platforms.join(', ') || 'N/A'}</span>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Method: <span className="text-slate-300 font-mono">{anom.baseline_method}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Candidate Review Queue */}
      {activeTab === 'candidates' && (
        <div>
          <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80 mb-6 flex items-center justify-between">
            <div className="text-sm font-medium text-slate-300">
              Human-in-the-Loop Review Queue
            </div>
            <select
              value={candidateStatusFilter}
              onChange={(e) => setCandidateStatusFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="pending_review">Pending Review</option>
              <option value="confirmed">Confirmed</option>
              <option value="dismissed">Dismissed</option>
              <option value="false_positive">False Positives</option>
              <option value="all">All Candidates</option>
            </select>
          </div>

          {candidates.length === 0 ? (
            <div className="p-12 rounded-2xl bg-slate-900/20 border border-dashed border-slate-800 text-center text-slate-400">
              <CheckCircle2 className="w-12 h-12 text-emerald-500/60 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-200">Review Queue Empty</h3>
              <p className="text-xs text-slate-500 mt-1">No anomaly candidates currently require human review.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {candidates.map((c) => (
                <div key={c.id} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <span className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                        {c.candidate_type.replace(/_/g, ' ')}
                      </span>
                      <div className="text-xs text-slate-400 mt-0.5">Product ID: {c.unified_product_id}</div>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                      Score {c.composite_score}
                    </span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 mb-4">
                    <div className="text-xs font-semibold text-slate-300 mb-1">Trigger Reasons:</div>
                    <ul className="text-xs text-slate-400 list-disc list-inside space-y-0.5">
                      {c.reasons.map((r, idx) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </div>

                  {c.status === 'pending_review' && (
                    <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                      <button
                        disabled={resolvingId === c.id}
                        onClick={() => handleResolveCandidate(c.id, 'confirmed')}
                        className="flex-1 py-2 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Confirm
                      </button>
                      <button
                        disabled={resolvingId === c.id}
                        onClick={() => handleResolveCandidate(c.id, 'false_positive')}
                        className="flex-1 py-2 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-500/30 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                      >
                        <ShieldCheck className="w-3.5 h-3.5" /> False Positive
                      </button>
                      <button
                        disabled={resolvingId === c.id}
                        onClick={() => handleResolveCandidate(c.id, 'dismissed')}
                        className="flex-1 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                      >
                        <XCircle className="w-3.5 h-3.5" /> Dismiss
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Product Anomaly Analyzer */}
      {activeTab === 'analyzer' && (
        <div className="space-y-6">
          <form onSubmit={handleAnalyzeProduct} className="flex gap-3 max-w-2xl">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Enter Canonical Unified Product ID (e.g. prod_...)"
                value={analyzerProductId}
                onChange={(e) => setAnalyzerProductId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <button
              type="submit"
              disabled={isAnalyzing || !analyzerProductId.trim()}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-sm font-semibold shadow-md disabled:opacity-50 flex items-center gap-2"
            >
              {isAnalyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              Analyze
            </button>
          </form>

          {productSummary && (
            <div className="space-y-6">
              {/* Product Header Card */}
              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-slate-100">{productSummary.canonical_name}</h2>
                    <div className="text-xs text-slate-400 mt-1 flex items-center gap-3">
                      <span>Brand: <strong className="text-slate-300">{productSummary.brand || 'Unbranded'}</strong></span>
                      <span>Category: <strong className="text-slate-300">{productSummary.category}</strong></span>
                      <span>Freshness: <strong className="text-cyan-400">{productSummary.freshness_status}</strong></span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-extrabold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                      {productSummary.anomaly_score} / 100
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">Status: <span className="font-semibold text-slate-200">{productSummary.status}</span></div>
                  </div>
                </div>

                {/* Score Breakdown Meters */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-6 pt-6 border-t border-slate-800/80">
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[11px] text-slate-400">Deviation Mag (35%)</div>
                    <div className="text-sm font-bold text-slate-200 mt-1">{productSummary.score_breakdown.deviation_magnitude_score}</div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[11px] text-slate-400">Historical Cons (25%)</div>
                    <div className="text-sm font-bold text-slate-200 mt-1">{productSummary.score_breakdown.historical_consistency_score}</div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[11px] text-slate-400">Data Freshness (15%)</div>
                    <div className="text-sm font-bold text-slate-200 mt-1">{productSummary.score_breakdown.data_freshness_score}</div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[11px] text-slate-400">Baseline Quality (15%)</div>
                    <div className="text-sm font-bold text-slate-200 mt-1">{productSummary.score_breakdown.baseline_quality_score}</div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[11px] text-slate-400">Cross-Platform (10%)</div>
                    <div className="text-sm font-bold text-slate-200 mt-1">{productSummary.score_breakdown.cross_platform_score}</div>
                  </div>
                </div>
              </div>

              {/* Historical Observations Timeline */}
              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
                <h3 className="text-base font-bold text-slate-200 mb-4 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Chronological Metric Observations ({obsHistory.length})
                </h3>

                {obsHistory.length === 0 ? (
                  <p className="text-xs text-slate-500">No raw observation records available for this product.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="pb-2">Metric Type</th>
                          <th className="pb-2">Platform</th>
                          <th className="pb-2">Observed Value</th>
                          <th className="pb-2">Previous</th>
                          <th className="pb-2">Delta</th>
                          <th className="pb-2">Observed At</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50 text-slate-300">
                        {obsHistory.map((o) => (
                          <tr key={o.id} className="hover:bg-slate-800/30">
                            <td className="py-2.5 font-semibold text-slate-200 capitalize">{o.metric_type}</td>
                            <td className="py-2.5 uppercase text-slate-400 font-mono text-[11px]">{o.platform}</td>
                            <td className="py-2.5 font-bold text-cyan-400">{o.metric_value}</td>
                            <td className="py-2.5 text-slate-400">{o.previous_value !== undefined ? o.previous_value : '—'}</td>
                            <td className="py-2.5">
                              {o.change_percent !== undefined ? (
                                <span className={o.change_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                                  {o.change_percent > 0 ? '+' : ''}{o.change_percent}%
                                </span>
                              ) : (
                                '—'
                              )}
                            </td>
                            <td className="py-2.5 text-slate-400">{new Date(o.observed_at).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnomalyDashboardPage;
