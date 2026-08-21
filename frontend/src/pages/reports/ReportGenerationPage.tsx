import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { reportService } from "../../services/domainServices";
import { useToast } from "../../context/ToastContext";

export const ReportGenerationPage: React.FC = () => {
  const [title, setTitle] = useState("Q2 Multi-Channel Velocity Intelligence Briefing");
  const [template, setTemplate] = useState("executive");
  const [timeRange, setTimeRange] = useState("30d");
  const [category, setCategory] = useState("All Categories");
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([
    "TikTok",
    "Daraz",
    "Instagram",
    "YouTube",
  ]);

  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStage, setGenerationStage] = useState<string>("");
  const [progressPercent, setProgressPercent] = useState<number>(0);

  const navigate = useNavigate();
  const { showToast } = useToast();

  const togglePlatform = (p: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(p) ? prev.filter((item) => item !== p) : [...prev, p]
    );
  };

  const handleLaunchGeneration = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);

    try {
      // Step 1
      setGenerationStage("Preparing signal ingestion pipeline...");
      setProgressPercent(20);
      await new Promise((r) => setTimeout(r, 600));

      // Step 2
      setGenerationStage("Analyzing cross-channel velocity anomalies...");
      setProgressPercent(50);
      await new Promise((r) => setTimeout(r, 700));

      // Step 3
      setGenerationStage("Synthesizing AI arbitrage takeaways...");
      setProgressPercent(80);
      await new Promise((r) => setTimeout(r, 600));

      // Call API
      const res = await reportService.generate({
        title,
        template,
        time_range: timeRange,
        category,
        platforms: selectedPlatforms,
        sections: ["Executive Summary", "Key Findings", "Platform Distribution", "AI Convictions"],
      });

      // Step 4
      setGenerationStage("Report ready! Finalizing executive dossier...");
      setProgressPercent(100);
      await new Promise((r) => setTimeout(r, 400));

      if (res.success && res.data) {
        showToast("Intelligence report generated successfully!", "success");
        navigate(`/reports/${res.data.id}`);
      }
    } catch (err: any) {
      setIsGenerating(false);
      showToast(err.message || "Failed to generate report", "error");
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="border-b border-outline-variant/15 pb-6">
        <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
          AI INTELLIGENCE SYNTHESIS
        </span>
        <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
          Generate Market Intelligence Report
        </h1>
        <p className="text-xs text-on-surface-variant mt-1">
          Configure multi-source parameters to compile an analytical dossier with predictive sourcing convictions.
        </p>
      </div>

      {isGenerating ? (
        /* Progress Screen */
        <div className="bg-surface-container-low p-12 rounded-3xl border border-primary/30 text-center glass-panel shadow-2xl space-y-6">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center text-primary animate-pulse">
            <span className="material-symbols-outlined text-3xl">auto_awesome</span>
          </div>

          <div className="space-y-2">
            <h3 className="text-xl font-bold text-on-surface font-headline-sm">
              Synthesizing Market Intelligence
            </h3>
            <p className="text-xs font-mono-data text-primary tracking-wide">
              {generationStage}
            </p>
          </div>

          {/* Progress Bar */}
          <div className="max-w-md mx-auto space-y-2">
            <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden border border-outline-variant/20">
              <div
                className="h-full bg-primary transition-all duration-500 rounded-full shadow-[0_0_10px_rgba(255,182,141,0.5)]"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="text-xs font-mono-data text-on-surface-variant">
              {progressPercent}% Complete
            </span>
          </div>
        </div>
      ) : (
        /* Config Form */
        <form
          onSubmit={handleLaunchGeneration}
          className="bg-surface-container-low p-8 md:p-10 rounded-3xl border border-outline-variant/20 glass-card space-y-8"
        >
          {/* Report Title */}
          <div>
            <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
              Report Title
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Q2 Consumer Electronics & Beauty Surge Briefing"
              className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-3 text-xs text-on-surface focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          {/* Template Selection */}
          <div>
            <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-3">
              Intelligence Template
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                {
                  id: "executive",
                  name: "Executive Briefing",
                  desc: "High-level summary of top 10 market velocity shifts and macro signals.",
                  icon: "analytics",
                },
                {
                  id: "velocity_surge",
                  name: "Velocity Surge Deep Dive",
                  desc: "Granular anomaly analysis of 200%+ breakout products and suppliers.",
                  icon: "bolt",
                },
                {
                  id: "platform_distribution",
                  name: "Platform Share Breakdown",
                  desc: "Cross-border channel concentration and consumer conversion paths.",
                  icon: "share",
                },
              ].map((t) => (
                <div
                  key={t.id}
                  onClick={() => setTemplate(t.id)}
                  className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                    template === t.id
                      ? "bg-primary/15 border-primary/50 text-primary shadow-[0_0_15px_rgba(223,115,40,0.15)]"
                      : "bg-surface-container border-outline-variant/20 text-on-surface hover:border-primary/30"
                  }`}
                >
                  <span className="material-symbols-outlined text-2xl mb-2">{t.icon}</span>
                  <h4 className="text-sm font-bold">{t.name}</h4>
                  <p className="text-xs text-on-surface-variant mt-1.5 leading-relaxed">{t.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Time Range & Category */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                Timeframe Horizon
              </label>
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-3 text-xs text-on-surface focus:outline-none focus:border-primary"
              >
                <option value="7d">Last 7 Days (Ultra Fast Velocity)</option>
                <option value="30d">Last 30 Days (Recommended Horizon)</option>
                <option value="90d">Last 90 Days (Macro Trend Trajectory)</option>
                <option value="all">All-Time Historical Dataset</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                Category Scope
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-3 text-xs text-on-surface focus:outline-none focus:border-primary"
              >
                <option value="All Categories">All Monitored Categories</option>
                <option value="Beauty & Personal Care">Beauty & Personal Care</option>
                <option value="Sports & Outdoor">Sports & Outdoor</option>
                <option value="Consumer Electronics">Consumer Electronics</option>
                <option value="Home & Kitchen">Home & Kitchen</option>
                <option value="Fashion & Apparel">Fashion & Apparel</option>
              </select>
            </div>
          </div>

          {/* Platforms to Include */}
          <div>
            <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-3">
              Included Ingestion Sources
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {["TikTok", "Daraz", "Instagram", "YouTube"].map((plat) => {
                const isSelected = selectedPlatforms.includes(plat);
                return (
                  <button
                    type="button"
                    key={plat}
                    onClick={() => togglePlatform(plat)}
                    className={`flex items-center gap-2 p-3 rounded-xl border text-xs font-semibold transition-all ${
                      isSelected
                        ? "bg-primary/15 border-primary/40 text-primary shadow-[0_0_12px_rgba(223,115,40,0.15)]"
                        : "bg-surface-container border-outline-variant/20 text-on-surface-variant"
                    }`}
                  >
                    <span className="material-symbols-outlined text-base">
                      {isSelected ? "check_box" : "check_box_outline_blank"}
                    </span>
                    <span>{plat}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Submit */}
          <div className="pt-4 border-t border-outline-variant/20 flex items-center justify-end gap-4">
            <button
              type="button"
              onClick={() => navigate("/reports")}
              className="text-xs font-label-caps text-on-surface-variant hover:text-on-surface px-4 py-2"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="bg-primary text-on-primary font-label-caps font-semibold text-xs px-8 py-3.5 rounded-xl hover:bg-primary-container transition-all shadow-[0_0_25px_rgba(255,182,141,0.25)] flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">auto_awesome</span>
              Launch AI Synthesis
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
