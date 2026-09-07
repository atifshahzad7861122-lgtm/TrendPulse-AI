import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { authService } from "../../services/domainServices";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

export const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const emailParam = searchParams.get("email") || "";

  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
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

  const handleVerify = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanCode = code.trim();
    if (!cleanCode) {
      setError("Please enter the verification code sent to your email.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await authService.verifyEmail(cleanCode);
      if (res.success && res.data) {
        showToast("Email verified successfully! Setting up your workspace.", "success");
        setSession(res.data.access_token, {
          id: res.data.user_id,
          email: emailParam || "user@trendpulse.ai",
          full_name: "Verified User",
          is_verified: true,
          workspace_id: res.data.workspace_id,
          role: "Administrator",
        });
        navigate("/workspace-setup");
      }
    } catch (err: any) {
      const msg = err.message || "Verification failed. The code may be invalid or expired.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0 || resending) return;
    if (!emailParam) {
      showToast("Email address is missing. Please register again.", "error");
      return;
    }

    setResending(true);
    setError(null);
    try {
      const res = await authService.resendVerification(emailParam);
      if (res.success) {
        setCooldown(60);
        showToast(res.message || `A new verification code has been sent to ${emailParam}.`, "info");
      }
    } catch (err: any) {
      showToast(err.message || "Failed to resend verification code. Please try again.", "error");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="text-center">
      <div className="w-12 h-12 mx-auto rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-primary mb-4 shadow-[0_0_20px_rgba(255,182,141,0.2)]">
        <span className="material-symbols-outlined text-2xl">mark_email_read</span>
      </div>

      <h1 className="font-headline-sm text-2xl font-bold text-on-surface">Verify Your Email</h1>
      <p className="text-xs text-on-surface-variant max-w-sm mx-auto mt-2 leading-relaxed">
        {emailParam ? (
          <>
            We sent a verification code to <span className="text-on-surface font-semibold">{emailParam}</span>. Enter the code below to activate your workspace.
          </>
        ) : (
          "Enter the verification code sent to your registered email address to activate your workspace."
        )}
      </p>

      {error && (
        <div className="my-4 p-3 rounded-lg bg-error-container/20 border border-error/40 text-on-surface text-xs flex items-center gap-2 text-left">
          <span className="material-symbols-outlined text-error text-base shrink-0">error</span>
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleVerify} className="mt-6 space-y-4 text-left">
        <div>
          <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-1.5">
            Verification Code / OTP
          </label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Enter verification code"
            autoComplete="one-time-code"
            className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-sm text-on-surface font-mono-data focus:outline-none focus:border-primary transition-colors text-center tracking-widest uppercase font-bold placeholder:tracking-normal placeholder:font-normal placeholder:text-xs placeholder:text-on-surface-variant/40"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !code.trim()}
          className="w-full bg-primary text-on-primary font-label-caps font-semibold text-xs py-3 rounded-xl hover:bg-primary-container transition-all shadow-[0_0_20px_rgba(255,182,141,0.2)] disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin" />
              Verifying Code...
            </>
          ) : (
            "Verify & Continue"
          )}
        </button>
      </form>

      <div className="mt-6 pt-4 border-t border-outline-variant/20 flex items-center justify-between text-xs text-on-surface-variant">
        <span>Didn't receive the code?</span>
        <button
          type="button"
          onClick={handleResend}
          disabled={cooldown > 0 || resending}
          className="text-primary font-semibold hover:underline disabled:opacity-50 flex items-center gap-1.5"
        >
          {resending && <div className="w-3 h-3 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />}
          {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend Code"}
        </button>
      </div>
    </div>
  );
};
