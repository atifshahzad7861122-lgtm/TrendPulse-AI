import React, { useState, useEffect } from "react";
import { settingsService } from "../../services/domainServices";
import type { UserSettings } from "../../types";
import { LoadingSpinner, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [activeTab, setActiveTab] = useState<"profile" | "workspace" | "notifications" | "ai" | "display">("profile");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { showToast } = useToast();

  const fetchSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await settingsService.getSettings();
      if (res.success && res.data) {
        setSettings(res.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;

    setSaving(true);
    try {
      const res = await settingsService.updateSettings(settings);
      if (res.success && res.data) {
        setSettings(res.data);
        showToast("Settings saved successfully!", "success");
      }
    } catch (err: any) {
      showToast(err.message || "Failed to save settings", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingSpinner size="lg" label="Loading account & workspace settings..." />;
  }

  if (error || !settings) {
    return <ErrorState message={error || "Settings unavailable"} onRetry={fetchSettings} />;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="border-b border-outline-variant/15 pb-6">
        <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
          SYSTEM PREFERENCES
        </span>
        <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
          Settings & Configuration
        </h1>
        <p className="text-xs text-on-surface-variant mt-1">
          Manage your operator profile, workspace currency defaults, and predictive confidence thresholds.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-outline-variant/15 pb-2">
        {[
          { id: "profile", label: "Profile & Identity", icon: "person" },
          { id: "workspace", label: "Workspace", icon: "domain" },
          { id: "notifications", label: "Notifications", icon: "notifications" },
          { id: "ai", label: "AI Preferences", icon: "psychology" },
          { id: "display", label: "Display & Theme", icon: "palette" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-label-caps uppercase transition-all ${
              activeTab === tab.id
                ? "bg-primary text-on-primary font-bold shadow-[0_0_15px_rgba(255,182,141,0.25)]"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
            }`}
          >
            <span className="material-symbols-outlined text-base">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Form Content */}
      <form onSubmit={handleSave} className="bg-surface-container-low p-8 rounded-3xl border border-outline-variant/20 glass-card space-y-6">
        {/* Profile Tab */}
        {activeTab === "profile" && (
          <div className="space-y-6">
            <div className="flex items-center gap-6 pb-6 border-b border-outline-variant/15">
              <div className="w-16 h-16 rounded-2xl bg-surface-container-high border border-primary/30 flex items-center justify-center overflow-hidden">
                {settings.avatar_url ? (
                  <img src={settings.avatar_url} alt={settings.full_name} className="w-full h-full object-cover" />
                ) : (
                  <span className="text-xl font-bold text-primary">{settings.full_name.charAt(0)}</span>
                )}
              </div>
              <div>
                <h3 className="text-base font-bold text-on-surface">{settings.full_name}</h3>
                <p className="text-xs text-on-surface-variant">{settings.role}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={settings.full_name}
                  onChange={(e) => setSettings({ ...settings, full_name: e.target.value })}
                  className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={settings.email}
                  onChange={(e) => setSettings({ ...settings, email: e.target.value })}
                  className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                  Role Title
                </label>
                <input
                  type="text"
                  value={settings.role}
                  onChange={(e) => setSettings({ ...settings, role: e.target.value })}
                  className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                  Company / Organization
                </label>
                <input
                  type="text"
                  value={settings.company_name}
                  onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
                  className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary"
                />
              </div>
            </div>
          </div>
        )}

        {/* Workspace Tab */}
        {activeTab === "workspace" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                  Operational Currency
                </label>
                <select
                  value={settings.currency}
                  onChange={(e) => setSettings({ ...settings, currency: e.target.value })}
                  className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary"
                >
                  <option value="USD">USD ($) - US Dollar</option>
                  <option value="EUR">EUR (€) - Euro</option>
                  <option value="GBP">GBP (£) - British Pound</option>
                  <option value="PKR">PKR (₨) - Pakistani Rupee</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                  Timezone
                </label>
                <select
                  value={settings.timezone}
                  onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                  className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary"
                >
                  <option value="UTC">UTC - Coordinated Universal Time</option>
                  <option value="America/New_York">EST - Eastern Time</option>
                  <option value="Asia/Karachi">PKT - Pakistan Standard Time</option>
                  <option value="Europe/London">GMT - London</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Notifications Tab */}
        {activeTab === "notifications" && (
          <div className="space-y-4">
            <label className="flex items-center justify-between p-4 rounded-xl bg-surface-container border border-outline-variant/20 cursor-pointer">
              <div>
                <p className="text-xs font-bold text-on-surface">Email Alert Dispatch</p>
                <p className="text-[11px] text-on-surface-variant">Send instant anomaly alarms to account email</p>
              </div>
              <input
                type="checkbox"
                checked={settings.email_notifications}
                onChange={(e) => setSettings({ ...settings, email_notifications: e.target.checked })}
                className="w-4 h-4 rounded bg-surface-container-high border-outline-variant/40 text-primary"
              />
            </label>

            <label className="flex items-center justify-between p-4 rounded-xl bg-surface-container border border-outline-variant/20 cursor-pointer">
              <div>
                <p className="text-xs font-bold text-on-surface">Critical Anomalies Only</p>
                <p className="text-[11px] text-on-surface-variant">Mute standard warnings and only notify on 200%+ velocity surges</p>
              </div>
              <input
                type="checkbox"
                checked={settings.alert_critical_only}
                onChange={(e) => setSettings({ ...settings, alert_critical_only: e.target.checked })}
                className="w-4 h-4 rounded bg-surface-container-high border-outline-variant/40 text-primary"
              />
            </label>

            <label className="flex items-center justify-between p-4 rounded-xl bg-surface-container border border-outline-variant/20 cursor-pointer">
              <div>
                <p className="text-xs font-bold text-on-surface">Weekly Executive Digest</p>
                <p className="text-[11px] text-on-surface-variant">Auto-compile Monday morning market intelligence summary</p>
              </div>
              <input
                type="checkbox"
                checked={settings.weekly_digest}
                onChange={(e) => setSettings({ ...settings, weekly_digest: e.target.checked })}
                className="w-4 h-4 rounded bg-surface-container-high border-outline-variant/40 text-primary"
              />
            </label>
          </div>
        )}

        {/* AI Preferences Tab */}
        {activeTab === "ai" && (
          <div className="space-y-6">
            <div>
              <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
                LLM Synthesis Model (Simulated Contract)
              </label>
              <select
                value={settings.ai_model_preference}
                onChange={(e) => setSettings({ ...settings, ai_model_preference: e.target.value })}
                className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary"
              >
                <option value="Qwen 2.5 Max (Simulated)">Alibaba Cloud Qwen 2.5 Max (Simulated)</option>
                <option value="Qwen 2.5 72B Instruct">Qwen 2.5 72B Instruct</option>
                <option value="DeepSeek R1 Sourcing Model">DeepSeek R1 Sourcing Specialist</option>
              </select>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider">
                  Conviction Threshold ({settings.ai_confidence_threshold}%)
                </label>
                <span className="text-xs font-mono-data text-primary font-bold">
                  {settings.ai_confidence_threshold}% Confidence
                </span>
              </div>
              <input
                type="range"
                min={50}
                max={99}
                value={settings.ai_confidence_threshold}
                onChange={(e) => setSettings({ ...settings, ai_confidence_threshold: Number(e.target.value) })}
                className="w-full accent-primary"
              />
              <p className="text-[11px] text-on-surface-variant mt-1">
                Only products exceeding this score are flagged as high conviction breakout recommendations.
              </p>
            </div>
          </div>
        )}

        {/* Display & Theme Tab */}
        {activeTab === "display" && (
          <div className="space-y-4">
            <label className="flex items-center justify-between p-4 rounded-xl bg-surface-container border border-outline-variant/20 cursor-pointer">
              <div>
                <p className="text-xs font-bold text-on-surface">Top Signal Ticker</p>
                <p className="text-[11px] text-on-surface-variant">Display real-time ticker ribbon on page header</p>
              </div>
              <input
                type="checkbox"
                checked={settings.live_ticker_enabled}
                onChange={(e) => setSettings({ ...settings, live_ticker_enabled: e.target.checked })}
                className="w-4 h-4 rounded bg-surface-container-high border-outline-variant/40 text-primary"
              />
            </label>

            <label className="flex items-center justify-between p-4 rounded-xl bg-surface-container border border-outline-variant/20 cursor-pointer">
              <div>
                <p className="text-xs font-bold text-on-surface">Dark Mode Obsidian Glass</p>
                <p className="text-[11px] text-on-surface-variant">Default high-contrast cinematic copper theme</p>
              </div>
              <input
                type="checkbox"
                checked={settings.dark_mode}
                onChange={(e) => setSettings({ ...settings, dark_mode: e.target.checked })}
                className="w-4 h-4 rounded bg-surface-container-high border-outline-variant/40 text-primary"
              />
            </label>
          </div>
        )}

        {/* Submit */}
        <div className="pt-6 border-t border-outline-variant/20 flex items-center justify-end">
          <button
            type="submit"
            disabled={saving}
            className="bg-primary text-on-primary font-label-caps font-semibold text-xs px-8 py-3 rounded-xl hover:bg-primary-container transition-all shadow-[0_0_20px_rgba(255,182,141,0.25)] flex items-center gap-2 disabled:opacity-50"
          >
            {saving ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin" />
                Saving Changes...
              </>
            ) : (
              "Save Changes"
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
