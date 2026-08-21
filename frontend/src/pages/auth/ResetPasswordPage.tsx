import React, { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { authService } from "../../services/domainServices";
import { useToast } from "../../context/ToastContext";

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const tokenParam = searchParams.get("token") || "";

  const [token, setToken] = useState(tokenParam);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { showToast } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!token.trim()) {
      setError("Please provide a valid reset token");
      return;
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      const res = await authService.resetPassword({
        token: token.trim(),
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      if (res.success) {
        showToast("Password reset successfully! Please sign in.", "success");
        navigate("/login");
      }
    } catch (err: any) {
      setError(err.message || "Failed to reset password. The token may be expired.");
      showToast(err.message || "Reset failed", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="text-center mb-6">
        <h1 className="font-headline-sm text-2xl font-bold text-on-surface">Set New Password</h1>
        <p className="text-xs text-on-surface-variant mt-1">
          Create a strong password to secure your intelligence feeds.
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-error-container/20 border border-error/40 text-on-surface text-xs flex items-center gap-2">
          <span className="material-symbols-outlined text-error text-base">error</span>
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-1.5">
            Reset Token
          </label>
          <input
            type="text"
            required
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste reset token"
            className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-xs text-on-surface font-mono-data focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-1.5">
            New Password
          </label>
          <input
            type="password"
            required
            value={newPassword}
            maxLength={128}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Min 8 characters"
            className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-xs text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-1.5">
            Confirm New Password
          </label>
          <input
            type="password"
            required
            value={confirmPassword}
            maxLength={128}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Repeat new password"
            className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-xs text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-on-primary font-label-caps font-semibold text-xs py-3 rounded-xl hover:bg-primary-container transition-all shadow-[0_0_20px_rgba(255,182,141,0.2)] disabled:opacity-50 flex items-center justify-center gap-2 mt-4"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin" />
              Updating Password...
            </>
          ) : (
            "Reset Password & Sign In"
          )}
        </button>
      </form>

      <div className="text-center mt-6 pt-4 border-t border-outline-variant/20">
        <Link to="/login" className="text-xs text-primary font-semibold hover:underline">
          Cancel & Back to Sign In
        </Link>
      </div>
    </div>
  );
};
