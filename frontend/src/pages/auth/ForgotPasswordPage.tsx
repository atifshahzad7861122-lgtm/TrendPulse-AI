import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authService } from "../../services/domainServices";
import { useToast } from "../../context/ToastContext";

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [devResetToken, setDevResetToken] = useState<string | null>(null);

  const { showToast } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setLoading(true);
    try {
      const res = await authService.forgotPassword(email.trim());
      if (res.success && res.data) {
        setSubmitted(true);
        if (res.data.reset_token) {
          setDevResetToken(res.data.reset_token);
        }
        showToast("Password reset instructions sent", "success");
      }
    } catch (err: any) {
      showToast(err.message || "Request failed", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-center">
      <div className="w-12 h-12 mx-auto rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-primary mb-4 shadow-[0_0_20px_rgba(255,182,141,0.2)]">
        <span className="material-symbols-outlined text-2xl">lock_reset</span>
      </div>

      <h1 className="font-headline-sm text-2xl font-bold text-on-surface">Forgot Password?</h1>
      <p className="text-xs text-on-surface-variant max-w-sm mx-auto mt-1 leading-relaxed">
        Enter your work email address and we'll generate a secure token to reset your password.
      </p>

      {!submitted ? (
        <form onSubmit={handleSubmit} className="mt-6 space-y-4 text-left">
          <div>
            <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-1.5">
              Account Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alex@company.com"
              className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-xs text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-on-primary font-label-caps font-semibold text-xs py-3 rounded-xl hover:bg-primary-container transition-all shadow-[0_0_20px_rgba(255,182,141,0.2)] disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin" />
                Sending Link...
              </>
            ) : (
              "Send Reset Link"
            )}
          </button>
        </form>
      ) : (
        <div className="mt-6 space-y-4 text-left">
          <div className="p-4 rounded-xl bg-surface-container-high border border-primary/20 text-xs text-on-surface space-y-2">
            <p className="text-primary font-semibold">Reset request generated!</p>
            <p className="text-on-surface-variant">
              If an account matches <span className="text-on-surface">{email}</span>, the reset link is active.
            </p>
            {devResetToken && (
              <div className="mt-2 pt-2 border-t border-outline-variant/20 flex flex-col gap-2">
                <span className="text-[11px] font-mono-data text-primary">Dev Token: {devResetToken}</span>
                <button
                  type="button"
                  onClick={() => navigate(`/reset-password?token=${devResetToken}`)}
                  className="bg-primary text-on-primary font-label-caps text-xs py-2 px-3 rounded-lg hover:bg-primary-container font-semibold"
                >
                  Proceed to Reset Password
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="mt-6 pt-4 border-t border-outline-variant/20">
        <Link to="/login" className="text-xs text-primary font-semibold hover:underline flex items-center justify-center gap-1">
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          Back to Sign In
        </Link>
      </div>
    </div>
  );
};
