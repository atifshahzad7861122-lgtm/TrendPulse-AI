import React, { useState, useEffect } from 'react';
import {
  TrendingUp, TrendingDown, Zap, AlertTriangle, RefreshCw,
  Search, Filter, XCircle, Layers, Activity, Compass, Flame,
  BarChart3, Check, Info, Clock
} from 'lucide-react';
import { trendDetectionService } from '../../services/domainServices';
import type {
  TrendSignalItem, TrendSignalCandidateItem, ProductTrendSummaryItem,
  AgentTrendDetectionStatsItem, TrendObservationItem,
  TrendDirection, TrendSeverity, TrendState
} from '../../types';

export const TrendDiscoveryPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'signals' | 'candidates' | 'analyzer'>('signals');
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState<AgentTrendDetectionStatsItem | null>(null);

  // Signals Feed State
  const [signals, setSignals] = useState<TrendSignalItem[]>([]);
  const [signalsTotal, setSignalsTotal] = useState(0);
  const [signalTypeFilter, setSignalTypeFilter] = useState<string>('all');
  const [directionFilter, setDirectionFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Candidates State
  const [candidates, setCandidates] = useState<TrendSignalCandidateItem[]>([]);
  const [candidateStatusFilter, setCandidateStatusFilter] = useState<string>('pending_review');
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  // Analyzer State
  const [analyzerProductId, setAnalyzerProductId] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzedSummary, setAnalyzedSummary] = useState<ProductTrendSummaryItem | null>(null);
  const [analyzerObservations, setAnalyzerObservations] = useState<TrendObservationItem[]>([]);

  useEffect(() => {
    loadData();
  }, [signalTypeFilter, directionFilter, severityFilter, candidateStatusFilter, activeTab]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const statsRes = await trendDetectionService.getStats();
      if (statsRes.data) setStats(statsRes.data);

      if (activeTab === 'signals') {
        const signalsRes = await trendDetectionService.listSignals({
          signal_type: signalTypeFilter,
          direction: directionFilter,
          severity: severityFilter,
          page_size: 50
        });
        if (signalsRes.data) {
          setSignals(signalsRes.data.items || []);
          setSignalsTotal(signalsRes.data.total || 0);
        }
      } else if (activeTab === 'candidates') {
        const candRes = await trendDetectionService.listCandidates(candidateStatusFilter);
        if (candRes.data) {
          setCandidates(candRes.data.items || []);
        }
      }
    } catch (err) {
      console.error('Failed to load trend detection data', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResolveCandidate = async (candidateId: string, status: 'confirmed' | 'rejected') => {
    setResolvingId(candidateId);
    try {
      await trendDetectionService.resolveCandidate(candidateId, {
        status,
        notes: `Operator decision applied via Trend Discovery Dashboard`
      });
      // Refresh candidates & stats
      const candRes = await trendDetectionService.listCandidates(candidateStatusFilter);
      if (candRes.data) setCandidates(candRes.data.items || []);
      const statsRes = await trendDetectionService.getStats();
      if (statsRes.data) setStats(statsRes.data);
    } catch (err) {
      console.error('Failed to resolve candidate', err);
    } finally {
      setResolvingId(null);
    }
  };

  const handleRunAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!analyzerProductId.trim()) return;

    setIsAnalyzing(true);
    try {
      const res = await trendDetectionService.analyzeProduct(analyzerProductId.trim(), undefined, true);
      if (res.data) {
        setAnalyzedSummary(res.data);
      }
      const obsRes = await trendDetectionService.getProductObservationsHistory(analyzerProductId.trim(), undefined, undefined, 30);
      if (obsRes.data) {
        setAnalyzerObservations(obsRes.data.items || []);
      }
    } catch (err) {
      console.error('Failed to analyze product trends', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getSeverityBadge = (severity: TrendSeverity) => {
    switch (severity) {
      case 'critical':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">Critical</span>;
      case 'high':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">High</span>;
      case 'medium':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">Medium</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">Low</span>;
    }
  };

  const getDirectionIcon = (direction: TrendDirection) => {
    switch (direction) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-emerald-400" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-rose-400" />;
      case 'volatile':
        return <Zap className="w-4 h-4 text-amber-400" />;
      default:
        return <Activity className="w-4 h-4 text-blue-400" />;
    }
  };

  const getTrendStateBadge = (state: TrendState) => {
    switch (state) {
      case 'breakout':
        return <span className="px-3 py-1 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 flex items-center gap-1.5"><Flame className="w-3.5 h-3.5 text-purple-400" /> BREAKOUT</span>;
      case 'accelerating':
        return <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5"><TrendingUp className="w-3.5 h-3.5 text-emerald-400" /> ACCELERATING</span>;
      case 'emerging':
        return <span className="px-3 py-1 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 flex items-center gap-1.5"><Zap className="w-3.5 h-3.5 text-cyan-400" /> EMERGING</span>;
      case 'insufficient_data':
        return <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-500/20 text-slate-400 border border-slate-500/40 flex items-center gap-1.5"><Info className="w-3.5 h-3.5" /> INSUFFICIENT DATA</span>;
      default:
        return <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-500/20 text-slate-300 border border-slate-500/40 uppercase">{state}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0d14] text-slate-100 p-6 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-400">
                <Compass className="w-6 h-6 text-indigo-400 animate-spin-slow" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold tracking-tight text-white">Trend Detection & Signal Discovery</h1>
                  <span className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    Agent 04 Active
                  </span>
                </div>
                <p className="text-sm text-slate-400 mt-0.5">
                  Autonomous discovery of verified marketplace signals, momentum breakout scoring, and multi-platform velocity.
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              disabled={isLoading}
              className="px-4 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 text-slate-200 text-sm font-medium flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh Signals
            </button>
          </div>
        </div>

        {/* Telemetry Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-xl relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Signals Discovered</span>
              <Activity className="w-4 h-4 text-indigo-400" />
            </div>
            <p className="text-2xl font-bold text-white mt-2">{stats?.total_signals_detected ?? 0}</p>
            <div className="flex items-center gap-1.5 mt-1 text-xs text-indigo-400">
              <span>{stats?.active_signals_count ?? 0} active now</span>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-xl relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Breakouts</span>
              <Flame className="w-4 h-4 text-purple-400" />
            </div>
            <p className="text-2xl font-bold text-white mt-2">{stats?.breakout_candidates_count ?? 0}</p>
            <div className="flex items-center gap-1.5 mt-1 text-xs text-purple-400">
              <span>High-velocity candidates</span>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-xl relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">High Severity</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-2xl font-bold text-white mt-2">{stats?.high_severity_signals ?? 0}</p>
            <div className="flex items-center gap-1.5 mt-1 text-xs text-amber-400">
              <span>Sharp price/stock shifts</span>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-xl relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Cross-Platform</span>
              <Layers className="w-4 h-4 text-cyan-400" />
            </div>
            <p className="text-2xl font-bold text-white mt-2">{stats?.multi_platform_signals ?? 0}</p>
            <div className="flex items-center gap-1.5 mt-1 text-xs text-cyan-400">
              <span>Multi-channel presence</span>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-xl relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Avg Trend Score</span>
              <BarChart3 className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold text-white mt-2">{(stats?.average_trend_score ?? 0).toFixed(1)}/100</p>
            <div className="flex items-center gap-1.5 mt-1 text-xs text-emerald-400">
              <span>Deterministic formula</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800">
          <button
            onClick={() => setActiveTab('signals')}
            className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'signals'
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Zap className="w-4 h-4" />
            Market Signals Feed ({signalsTotal})
          </button>
          <button
            onClick={() => setActiveTab('candidates')}
            className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'candidates'
                ? 'border-purple-500 text-purple-400 bg-purple-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Flame className="w-4 h-4" />
            Breakout Candidates ({candidates.length})
          </button>
          <button
            onClick={() => setActiveTab('analyzer')}
            className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'analyzer'
                ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Compass className="w-4 h-4" />
            Trend Score Analyzer
          </button>
        </div>

        {/* Tab 1: Signals Feed */}
        {activeTab === 'signals' && (
          <div className="space-y-6">
            {/* Filter Bar */}
            <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-semibold text-slate-400 uppercase">Filters:</span>
                </div>

                <select
                  value={signalTypeFilter}
                  onChange={(e) => setSignalTypeFilter(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="all">All Signal Types</option>
                  <option value="demand_surge">Demand Surge</option>
                  <option value="price_drop">Price Drop</option>
                  <option value="price_increase">Price Increase</option>
                  <option value="large_discount">Large Discount</option>
                  <option value="review_momentum">Review Momentum</option>
                  <option value="rating_momentum">Rating Momentum</option>
                  <option value="out_of_stock">Out of Stock</option>
                  <option value="restocked">Restocked</option>
                  <option value="cross_platform_surge">Cross-Platform Surge</option>
                  <option value="breakout_candidate">Breakout Candidate</option>
                </select>

                <select
                  value={directionFilter}
                  onChange={(e) => setDirectionFilter(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="all">All Directions</option>
                  <option value="up">Trending Up</option>
                  <option value="down">Trending Down</option>
                  <option value="stable">Stable</option>
                  <option value="volatile">Volatile</option>
                </select>

                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="all">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search product ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 w-48 md:w-64"
                />
              </div>
            </div>

            {/* Signals Grid */}
            {signals.length === 0 ? (
              <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800/80">
                <Zap className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-slate-300">No signals matching filters</h3>
                <p className="text-xs text-slate-500 mt-1">Try broadening your filter criteria or running a product sync.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {signals
                  .filter((s) => !searchTerm || s.unified_product_id.toLowerCase().includes(searchTerm.toLowerCase()))
                  .map((sig) => (
                    <div
                      key={sig.id}
                      className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all space-y-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <div className="p-2 rounded-lg bg-slate-800 text-slate-300">
                            {getDirectionIcon(sig.direction)}
                          </div>
                          <div>
                            <h4 className="text-sm font-semibold text-white capitalize">
                              {sig.signal_type.replace(/_/g, ' ')}
                            </h4>
                            <span className="text-[11px] text-slate-400 font-mono">
                              {sig.unified_product_id}
                            </span>
                          </div>
                        </div>
                        {getSeverityBadge(sig.severity)}
                      </div>

                      {/* Signal Strength & Confidence */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-400">Signal Strength</span>
                          <span className="font-semibold text-slate-200">{sig.signal_strength.toFixed(0)}/100</span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400 rounded-full"
                            style={{ width: `${Math.min(100, Math.max(5, sig.signal_strength))}%` }}
                          ></div>
                        </div>
                      </div>

                      {/* Evidence Payload */}
                      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60 text-xs space-y-1.5">
                        <div className="flex items-center justify-between text-slate-400">
                          <span>Confidence:</span>
                          <span className="text-emerald-400 font-medium">{(sig.confidence * 100).toFixed(0)}%</span>
                        </div>
                        {sig.platforms && sig.platforms.length > 0 && (
                          <div className="flex items-center justify-between text-slate-400">
                            <span>Platforms:</span>
                            <span className="text-slate-200 capitalize">{sig.platforms.join(', ')}</span>
                          </div>
                        )}
                        {sig.evidence && (
                          <div className="text-[11px] text-slate-400 font-mono pt-1 border-t border-slate-800/80 truncate">
                            {JSON.stringify(sig.evidence)}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800/60">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(sig.detected_at).toLocaleDateString()}
                        </span>
                        <span className="font-mono text-[10px] text-slate-600 truncate max-w-[120px]">
                          fp: {sig.fingerprint.substring(0, 10)}...
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Breakout Candidates */}
        {activeTab === 'candidates' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-400 uppercase">Status:</span>
                {(['pending_review', 'confirmed', 'rejected'] as const).map((st) => (
                  <button
                    key={st}
                    onClick={() => setCandidateStatusFilter(st)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer capitalize ${
                      candidateStatusFilter === st
                        ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                        : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {st.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {candidates.length === 0 ? (
              <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800">
                <Flame className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-slate-300">No {candidateStatusFilter.replace('_', ' ')} candidates</h3>
                <p className="text-xs text-slate-500 mt-1">Breakout candidates are automatically identified when review velocity and demand surge align.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {candidates.map((cand) => (
                  <div
                    key={cand.id}
                    className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-purple-500/40 transition-all space-y-4"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                          {cand.candidate_type.replace(/_/g, ' ')}
                        </span>
                        <h4 className="text-base font-semibold text-white mt-2 font-mono">
                          {cand.unified_product_id}
                        </h4>
                      </div>
                      <div className="text-right">
                        <span className="text-2xl font-bold text-purple-400">{cand.composite_score.toFixed(0)}</span>
                        <span className="text-xs text-slate-500">/100</span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-slate-400 uppercase">Detection Reasons:</span>
                      <ul className="space-y-1">
                        {cand.reasons.map((r, idx) => (
                          <li key={idx} className="text-xs text-slate-300 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {cand.status === 'pending_review' && (
                      <div className="flex items-center gap-3 pt-3 border-t border-slate-800">
                        <button
                          onClick={() => handleResolveCandidate(cand.id, 'confirmed')}
                          disabled={resolvingId === cand.id}
                          className="flex-1 py-2 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                        >
                          <Check className="w-3.5 h-3.5" />
                          Confirm Breakout
                        </button>
                        <button
                          onClick={() => handleResolveCandidate(cand.id, 'rejected')}
                          disabled={resolvingId === cand.id}
                          className="flex-1 py-2 px-4 rounded-xl bg-slate-800 hover:bg-rose-500/20 hover:text-rose-400 text-slate-300 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          Dismiss
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Trend Score Analyzer */}
        {activeTab === 'analyzer' && (
          <div className="space-y-6">
            <form onSubmit={handleRunAnalysis} className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 flex gap-4">
              <div className="flex-1 relative">
                <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Enter Unified Product ID (e.g. unf_...)"
                  value={analyzerProductId}
                  onChange={(e) => setAnalyzerProductId(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <button
                type="submit"
                disabled={isAnalyzing || !analyzerProductId.trim()}
                className="px-6 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
              >
                {isAnalyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Compass className="w-4 h-4" />}
                Analyze Trends
              </button>
            </form>

            {analyzedSummary && (
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
                  <div>
                    <h3 className="text-xl font-bold text-white">{analyzedSummary.canonical_name}</h3>
                    <p className="text-xs text-slate-400 font-mono mt-1">{analyzedSummary.unified_product_id}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {getTrendStateBadge(analyzedSummary.trend_state)}
                    <div className="p-3 rounded-xl bg-slate-800 border border-slate-700 text-right">
                      <span className="text-xs text-slate-400 block">Trend Score</span>
                      <span className="text-2xl font-bold text-cyan-400">{analyzedSummary.trend_score.toFixed(1)}/100</span>
                    </div>
                  </div>
                </div>

                {/* Score Breakdown Meters */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                    <span className="text-xs text-slate-400 font-medium">Demand & Reviews (35%)</span>
                    <p className="text-lg font-bold text-white">
                      {analyzedSummary.score_breakdown.demand_review_score.toFixed(1)}/35
                    </p>
                    <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full"
                        style={{ width: `${(analyzedSummary.score_breakdown.demand_review_score / 35) * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                    <span className="text-xs text-slate-400 font-medium">Price Health (20%)</span>
                    <p className="text-lg font-bold text-white">
                      {analyzedSummary.score_breakdown.price_health_score.toFixed(1)}/20
                    </p>
                    <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-500 rounded-full"
                        style={{ width: `${(analyzedSummary.score_breakdown.price_health_score / 20) * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                    <span className="text-xs text-slate-400 font-medium">Cross-Platform (20%)</span>
                    <p className="text-lg font-bold text-white">
                      {analyzedSummary.score_breakdown.cross_platform_score.toFixed(1)}/20
                    </p>
                    <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: `${(analyzedSummary.score_breakdown.cross_platform_score / 20) * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                    <span className="text-xs text-slate-400 font-medium">Inventory (15%)</span>
                    <p className="text-lg font-bold text-white">
                      {analyzedSummary.score_breakdown.inventory_health_score.toFixed(1)}/15
                    </p>
                    <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${(analyzedSummary.score_breakdown.inventory_health_score / 15) * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                    <span className="text-xs text-slate-400 font-medium">Freshness (10%)</span>
                    <p className="text-lg font-bold text-white">
                      {analyzedSummary.score_breakdown.freshness_confidence_score.toFixed(1)}/10
                    </p>
                    <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-amber-500 rounded-full"
                        style={{ width: `${(analyzedSummary.score_breakdown.freshness_confidence_score / 10) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                {/* Observation History */}
                {analyzerObservations.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-slate-300">Recorded Metric Observations ({analyzerObservations.length})</h4>
                    <div className="overflow-x-auto rounded-xl border border-slate-800">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-800/60 text-slate-400 font-semibold border-b border-slate-800">
                          <tr>
                            <th className="py-2.5 px-4">Platform</th>
                            <th className="py-2.5 px-4">Metric</th>
                            <th className="py-2.5 px-4">Value</th>
                            <th className="py-2.5 px-4">Delta</th>
                            <th className="py-2.5 px-4">Observed At</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {analyzerObservations.map((o) => (
                            <tr key={o.id} className="hover:bg-slate-800/30">
                              <td className="py-2.5 px-4 capitalize text-slate-200">{o.platform}</td>
                              <td className="py-2.5 px-4 text-slate-300 font-medium">{o.metric_type}</td>
                              <td className="py-2.5 px-4 text-white font-mono">{o.metric_value}</td>
                              <td className="py-2.5 px-4">
                                {o.change_percent !== undefined && o.change_percent !== null ? (
                                  <span className={o.change_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                                    {o.change_percent > 0 ? `+${o.change_percent.toFixed(1)}%` : `${o.change_percent.toFixed(1)}%`}
                                  </span>
                                ) : (
                                  <span className="text-slate-500">-</span>
                                )}
                              </td>
                              <td className="py-2.5 px-4 text-slate-400">{new Date(o.observed_at).toLocaleString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TrendDiscoveryPage;
