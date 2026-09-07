import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authService } from "../../services/domainServices";
import { useToast } from "../../context/ToastContext";

export const RegisterPage: React.FC = () => {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const { showToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (!termsAccepted) {
      setError("Please accept the terms and conditions");
      return;
    }

    setLoading(true);
    try {
      const res = await authService.register({
        full_name: fullName,
        email,
        password,
        confirm_password: confirmPassword,
        terms_accepted: termsAccepted,
      });

      if (res.success && res.data) {
        showToast("Account created! Please check your email for the verification code.", "success");
        // Redirect to email verification page (without raw token)
        navigate(`/verify-email?email=${encodeURIComponent(email)}`);
      }
    } catch (err: any) {
      setError(err.message || "Registration failed. Please check your credentials.");
      showToast(err.message || "Registration failed", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="text-center mb-6">
        <h1 className="font-headline-sm text-2xl font-bold text-on-surface">Create Account</h1>
        <p className="text-xs text-on-surface-variant mt-1">
          Start predicting market trends with real-time intelligence.
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
            Full Name
          </label>
          <input
            type="text"
            required
            value={fullName}
            maxLength={100}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Enter full name"
            className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-xs text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-1.5">
            Work Email
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@company.com"
            className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-xs text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-1.5">
            Password
          </label>
          <input
            type="password"
            required
            value={password}
            maxLength={128}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min 8 characters"
            className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-xs text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider mb-1.5">
            Confirm Password
          </label>
          <input
            type="password"
            required
            value={confirmPassword}
            maxLength={128}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Repeat password"
            className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 text-xs text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        <div className="flex items-center gap-2 pt-1">
          <input
            type="checkbox"
            id="terms"
            checked={termsAccepted}
            onChange={(e) => setTermsAccepted(e.target.checked)}
            className="w-4 h-4 rounded bg-surface-container border-outline-variant/40 text-primary focus:ring-0"
          />
          <label htmlFor="terms" className="text-xs text-on-surface-variant cursor-pointer">
            I accept the{" "}
            <span className="text-primary hover:underline">Terms of Service</span> and{" "}
            <span className="text-primary hover:underline">Privacy Policy</span>
          </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-on-primary font-label-caps font-semibold text-xs py-3 rounded-xl hover:bg-primary-container transition-all shadow-[0_0_20px_rgba(255,182,141,0.2)] disabled:opacity-50 flex items-center justify-center gap-2 mt-4"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin" />
              Creating Account...
            </>
          ) : (
            "Create Free Account"
          )}
        </button>
      </form>

      <div className="text-center mt-6 pt-4 border-t border-outline-variant/20">
        <p className="text-xs text-on-surface-variant">
          Already have an account?{" "}
          <Link to="/login" className="text-primary font-semibold hover:underline">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
};
