import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

interface NavItem {
  path: string;
  label: string;
  icon: string;
  badge?: string;
}

const navItems: NavItem[] = [
  { path: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { path: "/market-intelligence", label: "Market Intelligence", icon: "psychology", badge: "PHASE 3" },
  { path: "/agents/data-quality", label: "Data Quality Agent", icon: "verified_user", badge: "AI 1" },
  { path: "/rejected-products", label: "Public DQ Audit", icon: "policy", badge: "AUDIT" },
  { path: "/products/intelligence", label: "Unified Intelligence", icon: "hub", badge: "MULTI" },
  { path: "/trends", label: "Trend Discovery", icon: "trending_up", badge: "AI 4" },
  { path: "/anomalies", label: "Anomaly Sentinel", icon: "security_update_warning", badge: "AI 5" },
  { path: "/recommendations", label: "Recommendations", icon: "auto_awesome", badge: "AI 6" },
  { path: "/opportunities", label: "Market Opportunities", icon: "explore", badge: "AI 7" },
  { path: "/products", label: "Product Catalog", icon: "inventory_2" },
  { path: "/platforms/shopify", label: "Shopify Intelligence", icon: "shopping_cart" },
  { path: "/product-comparison", label: "Compare Signals", icon: "compare_arrows" },
  { path: "/categories", label: "Categories", icon: "category" },
  { path: "/platforms", label: "Platform Pulse", icon: "share" },
  { path: "/watchlist", label: "Watchlist", icon: "bookmark" },
  { path: "/reports", label: "Intelligence Reports", icon: "analytics" },
  { path: "/report-generation", label: "Generate Report", icon: "auto_awesome" },
  { path: "/data-sources", label: "Data Sources", icon: "cloud_sync" },
  { path: "/alerts", label: "Alerts Center", icon: "warning" },
  { path: "/search", label: "Global Search", icon: "search" },
  { path: "/settings", label: "Settings", icon: "settings" },
];

export const Sidebar: React.FC = () => {
  const { user, loading: authLoading } = useAuth();

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

      {/* Authenticated Operator Live Summary */}
      {authLoading ? (
        <div className="mt-auto pt-4 border-t border-outline-variant/15">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-surface-container/60 border border-outline-variant/10 animate-pulse">
            <div className="w-7 h-7 rounded-lg bg-surface-container-high shrink-0" />
            <div className="flex flex-col gap-1 min-w-0 flex-1">
              <div className="w-20 h-2.5 bg-surface-container-high rounded" />
              <div className="w-12 h-2 bg-surface-container-high rounded" />
            </div>
          </div>
        </div>
      ) : user ? (
        <div className="mt-auto pt-4 border-t border-outline-variant/15">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-surface-container/60 border border-outline-variant/10">
            <div className="w-7 h-7 rounded-lg bg-surface-container-high border border-primary/30 flex items-center justify-center overflow-hidden shrink-0">
              {user.avatar_url ? (
                <img src={user.avatar_url} alt={user.full_name} className="w-full h-full object-cover" />
              ) : (
                <span className="text-xs font-bold text-primary">
                  {user.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
                </span>
              )}
            </div>
            <div className="flex flex-col min-w-0 flex-1">
              <span className="text-xs font-medium text-on-surface truncate">{user.full_name}</span>
              <span className="text-[10px] text-on-surface-variant truncate">{user.role || "Operator"}</span>
            </div>
          </div>
        </div>
      ) : null}

      {/* System Operational Status Widget at bottom of sidebar */}
      <div className={user || authLoading ? "pt-3" : "mt-auto pt-6"}>
        <div className="p-3 rounded-xl bg-surface-container border border-outline-variant/20 glass-card">
          <div className="flex items-center gap-2 mb-1">
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
