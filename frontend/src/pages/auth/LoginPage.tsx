import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState("demo@trendpulse.ai");
  const [password, setPassword] = useState("Password123!");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password, rememberMe);
      showToast("Signed in successfully!", "success");
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.message || "Invalid email or password");
      showToast(err.message || "Login failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleFillDemo = () => {
    setEmail("demo@trendpulse.ai");
    setPassword("Password123!");
  };

  return (
    <div>
      <div className="text-center mb-6">
        <h1 className="font-headline-sm text-2xl font-bold text-on-surface">Welcome Back</h1>
        <p className="text-xs text-on-surface-variant mt-1">
          Sign in to access your intelligence feeds and predictive models.
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
            Email Address
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
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-[11px] font-label-caps text-on-surface-variant uppercase tracking-wider">
              Password
            </label>
            <Link
              to="/forgot-password"
              className="text-[11px] text-primary hover:underline font-medium"
            >
              Forgot Password?
            </Link>
          </div>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-3.5 py-2.5 pr-10 text-xs text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary transition-colors"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
            >
              <span className="material-symbols-outlined text-base">
                {showPassword ? "visibility_off" : "visibility"}
              </span>
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between pt-1">
          <label className="flex items-center gap-2 text-xs text-on-surface-variant cursor-pointer">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded bg-surface-container border-outline-variant/40 text-primary focus:ring-0"
            />
            <span>Remember this device</span>
          </label>
          <button
            type="button"
            onClick={handleFillDemo}
            className="text-[11px] text-on-surface-variant hover:text-primary transition-colors underline"
          >
            Fill Demo Credentials
          </button>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-on-primary font-label-caps font-semibold text-xs py-3 rounded-xl hover:bg-primary-container transition-all shadow-[0_0_20px_rgba(255,182,141,0.2)] disabled:opacity-50 flex items-center justify-center gap-2 mt-4"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin" />
              Authenticating...
            </>
          ) : (
            "Sign In to TrendPulse"
          )}
        </button>
      </form>

      <div className="text-center mt-6 pt-4 border-t border-outline-variant/20">
        <p className="text-xs text-on-surface-variant">
          Don't have an account?{" "}
          <Link to="/register" className="text-primary font-semibold hover:underline">
            Create Free Account
          </Link>
        </p>
      </div>
    </div>
  );
};
