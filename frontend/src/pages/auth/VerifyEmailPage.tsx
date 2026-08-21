import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { authService } from "../../services/domainServices";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

export const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialToken = searchParams.get("token") || "";
  const emailParam = searchParams.get("email") || "your email";

  const [token, setToken] = useState(initialToken);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);

  const navigate = useNavigate();
  const { setSession } = useAuth();
  const { showToast } = useToast();

  useEffect(() => {
    let timer: any;
    if (cooldown > 0) {
      timer = setInterval(() => setCooldown((c) => c - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [cooldown]);

  const handleVerify = async (tokenToUse?: string) => {
    const t = tokenToUse || token;
    if (!t.trim()) {
      setError("Please provide a verification token");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await authService.verifyEmail(t.trim());
      if (res.success && res.data) {
        showToast("Email verified successfully! Let's set up your workspace.", "success");
        setSession(res.data.access_token, {
          id: res.data.user_id,
          email: emailParam,
          full_name: "Verified User",
          is_verified: true,
          workspace_id: res.data.workspace_id,
          role: "Administrator",
        });
        navigate("/workspace-setup");
      }
    } catch (err: any) {
      setError(err.message || "Verification failed. The token may be invalid or expired.");
      showToast(err.message || "Verification failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = () => {
    if (cooldown > 0) return;
    setCooldown(30);
    showToast(`Verification code resent to ${emailParam}.`, "info");
  };

  return (
    <div className="text-center">
      <div className="w-12 h-12 mx-auto rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-primary mb-4 shadow-[0_0_20px_rgba(255,182,141,0.2)]">
        <span className="material-symbols-outlined text-2xl">mark_email_read</span>
      </div>

      <h1 className="font-headline-sm text-2xl font-bold text-on-surface">Verify Your Email</h1>
      <p className="text-xs text-on-surface-variant max-w-sm mx-auto mt-2 leading-relaxed">
        We sent a verification code to <span className="text-on-surface font-semibold">{emailParam}</span>. Enter the code below to activate your workspace.
      </p>

      {error && (
        <div className="my-4 p-3 rounded-lg bg-error-container/20 border border-error/40 text-on-surface text-xs flex items-center gap-2 text-left">
          <span className="material-symbols-outlined text-error text-base">error</span>
          <span>{error}</span>
        </div>
      )}

      <div className="mt-6 space-y-4 text-left">
        <div>
          <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-1.5">
            Verification Token
          </label>
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste verification token"
            className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-xs text-on-surface font-mono-data focus:outline-none focus:border-primary transition-colors text-center tracking-widest uppercase font-bold"
          />
        </div>

        {initialToken && (
          <div className="p-2.5 rounded-lg bg-primary/10 border border-primary/20 text-xs text-primary flex items-center justify-between">
            <span className="font-mono-data text-[11px]">Token detected from registration</span>
            <button
              type="button"
              onClick={() => handleVerify(initialToken)}
              className="text-[11px] font-semibold underline hover:text-primary-container"
            >
              Auto-Fill & Verify
            </button>
          </div>
        )}

        <button
          type="button"
          onClick={() => handleVerify()}
          disabled={loading || !token.trim()}
          className="w-full bg-primary text-on-primary font-label-caps font-semibold text-xs py-3 rounded-xl hover:bg-primary-container transition-all shadow-[0_0_20px_rgba(255,182,141,0.2)] disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin" />
              Verifying Token...
            </>
          ) : (
            "Verify & Continue"
          )}
        </button>
      </div>

      <div className="mt-6 pt-4 border-t border-outline-variant/20 flex items-center justify-between text-xs text-on-surface-variant">
        <span>Didn't receive the code?</span>
        <button
          onClick={handleResend}
          disabled={cooldown > 0}
          className="text-primary font-semibold hover:underline disabled:opacity-50"
        >
          {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend Token"}
        </button>
      </div>
    </div>
  );
};
