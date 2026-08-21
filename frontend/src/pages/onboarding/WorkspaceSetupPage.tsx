import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { workspaceService } from "../../services/domainServices";
import { useWorkspace } from "../../context/WorkspaceContext";
import { useToast } from "../../context/ToastContext";

export const WorkspaceSetupPage: React.FC = () => {
  const [name, setName] = useState("Apex Intelligence Labs");
  const [industry, setIndustry] = useState("E-commerce & Consumer Tech");
  const [useCase, setUseCase] = useState("Trend Prediction & Arbitrage");
  const [currency, setCurrency] = useState("USD");
  const [selectedSources, setSelectedSources] = useState<string[]>(["tiktok", "daraz", "instagram"]);
  const [loading, setLoading] = useState(false);

  const { updateLocalWorkspace } = useWorkspace();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const toggleSource = (src: string) => {
    setSelectedSources((prev) =>
      prev.includes(src) ? prev.filter((s) => s !== src) : [...prev, src]
    );
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);

    try {
      const res = await workspaceService.setupWorkspace({
        name,
        industry,
        use_case: useCase,
        currency,
        default_dashboard: "signals",
        data_sources: selectedSources,
      });

      if (res.success && res.data) {
        updateLocalWorkspace(res.data);
        showToast("Workspace initialized! Welcome to TrendPulse AI.", "success");
        navigate("/dashboard");
      }
    } catch (err: any) {
      showToast(err.message || "Failed to setup workspace", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-on-surface flex flex-col justify-between relative overflow-hidden p-6 md:p-12">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-primary/10 rounded-full blur-[140px] pointer-events-none" />

      {/* Header */}
      <div className="relative z-10 max-w-3xl mx-auto w-full flex items-center justify-between border-b border-outline-variant/20 pb-6 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-xl">domain</span>
          </div>
          <span className="font-headline-sm text-lg font-bold text-on-surface">
            TrendPulse Workspace Setup
          </span>
        </div>
        <button
          type="button"
          onClick={() => handleSubmit()}
          className="text-xs font-label-caps text-on-surface-variant hover:text-primary transition-colors"
        >
          Skip for Now →
        </button>
      </div>

      {/* Content Form */}
      <div className="relative z-10 max-w-3xl mx-auto w-full bg-surface-container/90 border border-primary/20 rounded-3xl p-8 md:p-12 glass-panel shadow-2xl">
        <div className="mb-8">
          <span className="text-xs font-label-caps text-primary uppercase tracking-wider">
            STEP 1 OF 1 • ONBOARDING
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Configure Your Intelligence Workspace
          </h1>
          <p className="text-xs md:text-sm text-on-surface-variant mt-2 leading-relaxed">
            Customize your data channels, currency thresholds, and default category focus.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                Workspace Name
              </label>
              <input
                type="text"
                required
                value={name}
                maxLength={100}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Apex Intelligence"
                className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-4 py-3 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
              />
            </div>

            <div>
              <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                Primary Industry Focus
              </label>
              <select
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-4 py-3 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
              >
                <option value="E-commerce & Consumer Tech">E-commerce & Consumer Tech</option>
                <option value="Beauty & Personal Care">Beauty & Personal Care</option>
                <option value="Fashion & Apparel">Fashion & Apparel</option>
                <option value="Sports & Outdoor">Sports & Outdoor</option>
                <option value="Home & Living">Home & Living</option>
                <option value="Multi-Category Enterprise">Multi-Category Enterprise</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                Primary Intelligence Objective
              </label>
              <select
                value={useCase}
                onChange={(e) => setUseCase(e.target.value)}
                className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-4 py-3 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
              >
                <option value="Trend Prediction & Arbitrage">Trend Prediction & Product Arbitrage</option>
                <option value="Competitor Monitoring">Competitor Sourcing & Stock Tracking</option>
                <option value="Market Research & Analytics">Macro Sourcing Research & Forecasting</option>
                <option value="Direct Supplier Sourcing">Direct Manufacturer Alignment</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                Preferred Currency
              </label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-4 py-3 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
              >
                <option value="USD">USD ($) - US Dollar</option>
                <option value="EUR">EUR (€) - Euro</option>
                <option value="GBP">GBP (£) - British Pound</option>
                <option value="PKR">PKR (₨) - Pakistani Rupee</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-3">
              Initial Data Channels (Simulated Ingestion)
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                { id: "tiktok", label: "TikTok Viral Feed", icon: "tiktok" },
                { id: "daraz", label: "Daraz Marketplace", icon: "shopping_bag" },
                { id: "instagram", label: "Instagram Reels", icon: "photo_camera" },
                { id: "youtube", label: "YouTube Reviews", icon: "smart_display" },
                { id: "facebook", label: "Facebook Commerce", icon: "group" },
              ].map((src) => {
                const isSelected = selectedSources.includes(src.id);
                return (
                  <button
                    type="button"
                    key={src.id}
                    onClick={() => toggleSource(src.id)}
                    className={`flex items-center gap-2.5 p-3 rounded-xl border text-left transition-all ${
                      isSelected
                        ? "bg-primary/15 border-primary/40 text-primary shadow-[0_0_15px_rgba(223,115,40,0.15)]"
                        : "bg-surface-container-low border-outline-variant/20 text-on-surface-variant hover:border-primary/20"
                    }`}
                  >
                    <span className="material-symbols-outlined text-lg">{src.icon}</span>
                    <span className="text-xs font-semibold">{src.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="pt-4 flex items-center justify-end gap-4 border-t border-outline-variant/20">
            <button
              type="button"
              onClick={() => handleSubmit()}
              className="text-xs font-label-caps text-on-surface-variant hover:text-on-surface px-4 py-2"
            >
              Skip
            </button>
            <button
              type="submit"
              disabled={loading}
              className="bg-primary text-on-primary font-label-caps font-semibold text-xs px-8 py-3.5 rounded-xl hover:bg-primary-container transition-all shadow-[0_0_25px_rgba(255,182,141,0.25)] flex items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin" />
                  Finalizing Workspace...
                </>
              ) : (
                <>
                  Launch Workspace Dashboard
                  <span className="material-symbols-outlined text-sm">arrow_forward</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      <div className="relative z-10 text-center text-xs text-on-surface-variant/60 font-mono-data">
        TrendPulse AI v1.0 • Ready for Market Sourcing
      </div>
    </div>
  );
};
