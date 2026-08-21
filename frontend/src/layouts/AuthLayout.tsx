import React from "react";
import { Link, Outlet } from "react-router-dom";

export const AuthLayout: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-background text-on-surface flex flex-col justify-between relative overflow-hidden">
      {/* Background Radial Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-primary/10 rounded-full blur-[140px] pointer-events-none" />

      {/* Top Navbar */}
      <header className="relative z-10 h-20 max-w-[1440px] w-full mx-auto px-6 md:px-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary-container/20 border border-primary/40 flex items-center justify-center text-primary shadow-[0_0_15px_rgba(223,115,40,0.2)]">
            <span className="material-symbols-outlined text-xl">radar</span>
          </div>
          <span className="font-headline-sm text-lg font-bold text-on-surface">
            TrendPulse <span className="text-primary">AI</span>
          </span>
        </Link>
        <Link
          to="/"
          className="text-xs font-label-caps text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1"
        >
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          Back to Overview
        </Link>
      </header>

      {/* Auth Form Box */}
      <main className="relative z-10 flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-surface-container/80 border border-primary/20 rounded-2xl p-8 glass-panel shadow-2xl animate-in fade-in zoom-in-95 duration-200">
          {children || <Outlet />}
        </div>
      </main>

      {/* Simple Footer */}
      <footer className="relative z-10 py-6 text-center text-xs text-on-surface-variant/60 font-mono-data">
        © 2026 TrendPulse AI Platform • All Signals Verified
      </footer>
    </div>
  );
};
