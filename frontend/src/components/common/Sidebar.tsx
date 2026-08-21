import React from "react";
import { NavLink } from "react-router-dom";

interface NavItem {
  path: string;
  label: string;
  icon: string;
  badge?: string;
}

const navItems: NavItem[] = [
  { path: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { path: "/products", label: "Product Intelligence", icon: "inventory_2" },
  { path: "/product-comparison", label: "Compare Signals", icon: "compare_arrows" },
  { path: "/categories", label: "Categories", icon: "category" },
  { path: "/platforms", label: "Platform Pulse", icon: "share" },
  { path: "/watchlist", label: "Watchlist", icon: "bookmark" },
  { path: "/reports", label: "Intelligence Reports", icon: "analytics" },
  { path: "/report-generation", label: "Generate Report", icon: "auto_awesome" },
  { path: "/data-sources", label: "Data Sources", icon: "hub" },
  { path: "/alerts", label: "Alerts Center", icon: "warning" },
  { path: "/search", label: "Global Search", icon: "search" },
  { path: "/settings", label: "Settings", icon: "settings" },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 shrink-0 hidden md:flex flex-col bg-surface-container-lowest border-r border-outline-variant/15 p-4 min-h-[calc(100vh-6.5rem)] sticky top-[6.5rem] self-start">
      <div className="text-[10px] font-label-caps uppercase tracking-wider text-on-surface-variant/70 px-3 mb-2">
        Core Intelligence
      </div>
      <nav className="space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all group ${
                isActive
                  ? "bg-primary/15 text-primary border border-primary/30 shadow-[0_0_15px_rgba(223,115,40,0.15)]"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
              }`
            }
          >
            <div className="flex items-center gap-3">
              <span
                className="material-symbols-outlined text-lg group-hover:text-primary transition-colors"
              >
                {item.icon}
              </span>
              <span>{item.label}</span>
            </div>
            {item.badge && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary-container text-on-primary-container font-mono-data">
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* System Operational Status Widget at bottom of sidebar */}
      <div className="mt-auto pt-6">
        <div className="p-3.5 rounded-xl bg-surface-container border border-outline-variant/20 glass-card">
          <div className="flex items-center gap-2 mb-1.5">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span className="text-[11px] font-semibold text-on-surface">Data Ingestion Active</span>
          </div>
          <p className="text-[10px] text-on-surface-variant leading-relaxed">
            Real-time multi-platform signal scrapers synced across 4 channels.
          </p>
        </div>
      </div>
    </aside>
  );
};
