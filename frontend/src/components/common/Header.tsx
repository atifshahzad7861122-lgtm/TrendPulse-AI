import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { notificationService, alertService, signalService } from "../../services/domainServices";
import type { NotificationItem, Alert, LiveSignalItem } from "../../types";
import { CommandSearchModal } from "./CommandSearchModal";
import { DarazProductModal } from "../products/DarazProductModal";

export const Header: React.FC = () => {
  const { user, loading: authLoading, logout } = useAuth();
  const { workspace } = useWorkspace();
  const navigate = useNavigate();

  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [signals, setSignals] = useState<LiveSignalItem[]>([]);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [selectedDarazId, setSelectedDarazId] = useState<string | null>(null);

  const notifRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchBadges = async () => {
      try {
        const [nRes, aRes] = await Promise.all([
          notificationService.list(true),
          alertService.list({ unread_only: true }),
        ]);
        if (nRes.success && nRes.data) setNotifications(nRes.data);
        if (aRes.success && aRes.data) setAlerts(aRes.data);
      } catch (err) {
        console.warn("Could not load header badges", err);
      }
    };
    fetchBadges();
  }, []);

  // Fetch real live market signals with periodic refresh
  useEffect(() => {
    let isMounted = true;

    const fetchLiveSignals = async () => {
      try {
        const res = await signalService.getLiveSignals(20);
        if (isMounted && res.success && res.data && res.data.signals) {
          setSignals(res.data.signals);
        }
      } catch (err) {
        console.warn("Could not load live signals", err);
      }
    };

    fetchLiveSignals();
    const interval = setInterval(fetchLiveSignals, 45000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Close menus on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setIsNotifOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Keyboard shortcut Command/Ctrl + K for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsSearchOpen(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleMarkAllNotifs = async () => {
    try {
      await notificationService.markAllRead();
      setNotifications([]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleSignalClick = (signal: LiveSignalItem) => {
    if (signal.product_id) {
      if (signal.platform === "daraz" || signal.product_id.startsWith("daraz_")) {
        setSelectedDarazId(signal.product_id);
      } else {
        navigate(`/products/${signal.product_id}`);
      }
    }
  };

  const getPlatformBadge = (platform: string) => {
    switch (platform.toLowerCase()) {
      case "daraz":
        return { label: "DARAZ", bg: "bg-[#F85606]/15 text-[#F85606] border-[#F85606]/30" };
      case "youtube":
        return { label: "YOUTUBE", bg: "bg-[#FF0000]/15 text-[#FF0000] border-[#FF0000]/30" };
      case "tiktok":
        return { label: "TIKTOK", bg: "bg-[#00F2FE]/15 text-[#00F2FE] border-[#00F2FE]/30" };
      case "instagram":
        return { label: "INSTAGRAM", bg: "bg-[#E1306C]/15 text-[#E1306C] border-[#E1306C]/30" };
      default:
        return { label: platform.toUpperCase(), bg: "bg-primary/15 text-primary border-primary/30" };
    }
  };

  return (
    <>
      <header className="sticky top-0 z-40 bg-surface/90 backdrop-blur-xl border-b border-outline-variant/15 transition-all">
        {/* Live Signal Ticker Ribbon */}
        <div className="w-full bg-surface-container-lowest/90 border-b border-primary/15 py-1 px-4 overflow-hidden flex items-center">
          <div className="flex items-center gap-2 mr-4 shrink-0">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(223,115,40,0.8)]" />
            <span className="text-[10px] font-label-caps font-bold text-primary tracking-widest uppercase flex items-center gap-1">
              LIVE SIGNALS
            </span>
          </div>

          <div className="overflow-hidden relative w-full group">
            {signals.length === 0 ? (
              <div className="text-[11px] font-mono-data text-on-surface-variant/70 italic flex items-center gap-2">
                <span>Waiting for live market data...</span>
              </div>
            ) : (
              <div className="flex whitespace-nowrap animate-ticker gap-8 text-[11px] font-mono-data text-on-surface-variant items-center group-hover:[animation-play-state:paused]">
                {signals.map((sig, idx) => {
                  const pBadge = getPlatformBadge(sig.platform);
                  return (
                    <React.Fragment key={sig.id || idx}>
                      <button
                        onClick={() => handleSignalClick(sig)}
                        className={`text-on-surface flex items-center gap-2 hover:text-primary transition-colors text-left ${sig.product_id ? "cursor-pointer" : "cursor-default"}`}
                        title={sig.product_id ? "Click to view product details" : undefined}
                      >
                        <span className={`px-1.5 py-0.2 text-[9px] font-bold rounded border ${pBadge.bg}`}>
                          {pBadge.label}
                        </span>
                        <span className="text-primary font-semibold text-[10px] uppercase">
                          {sig.type}:
                        </span>
                        <span className="truncate max-w-[340px] text-on-surface hover:text-primary">
                          {sig.description}
                        </span>
                      </button>
                      <span className="text-outline-variant/50">•</span>
                    </React.Fragment>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Main Navbar */}
        <div className="h-16 px-6 flex items-center justify-between gap-4">
          {/* Brand & Workspace Name */}
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center gap-2 group">
              <div className="w-8 h-8 rounded-lg bg-primary-container/20 border border-primary/40 flex items-center justify-center text-primary group-hover:scale-105 transition-transform shadow-[0_0_15px_rgba(223,115,40,0.2)]">
                <span className="material-symbols-outlined text-xl text-primary">radar</span>
              </div>
              <div className="flex flex-col">
                <span className="font-headline-sm text-base font-bold tracking-tight text-on-surface">
                  TrendPulse <span className="text-primary">AI</span>
                </span>
                <span className="text-[10px] font-label-caps text-on-surface-variant tracking-wider truncate max-w-[140px]">
                  {workspace?.name || "Workspace"}
                </span>
              </div>
            </Link>
          </div>

          {/* Center: Global Search Bar */}
          <div className="flex-1 max-w-md hidden md:block">
            <button
              onClick={() => setIsSearchOpen(true)}
              className="w-full flex items-center justify-between px-3.5 py-2 rounded-xl bg-surface-container-low border border-outline-variant/30 text-on-surface-variant hover:border-primary/40 hover:text-on-surface text-xs transition-all group"
            >
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-base group-hover:text-primary transition-colors">
                  search
                </span>
                <span>Search signals, products, reports...</span>
              </div>
              <kbd className="px-2 py-0.5 text-[10px] font-mono-data bg-surface-container-high rounded border border-outline-variant/30 text-on-surface-variant">
                Ctrl K
              </kbd>
            </button>
          </div>

          {/* Right Action Icons & User Dropdown */}
          <div className="flex items-center gap-3">
            {/* Generate Report Quick Button */}
            <Link
              to="/report-generation"
              className="hidden sm:flex items-center gap-1.5 bg-primary/10 border border-primary/30 text-primary hover:bg-primary hover:text-on-primary font-label-caps text-xs px-3.5 py-2 rounded-lg transition-all"
            >
              <span className="material-symbols-outlined text-sm">auto_awesome</span>
              Generate Report
            </Link>

            {/* Alerts Link */}
            <Link
              to="/alerts"
              className="relative p-2 rounded-lg text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors"
              title="System Alerts"
            >
              <span className="material-symbols-outlined text-xl">warning</span>
              {alerts.length > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-error text-on-error rounded-full text-[9px] font-bold flex items-center justify-center">
                  {alerts.length}
                </span>
              )}
            </Link>

            {/* Notifications Dropdown */}
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setIsNotifOpen(!isNotifOpen)}
                className="relative p-2 rounded-lg text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors"
                title="Notifications"
              >
                <span className="material-symbols-outlined text-xl">notifications</span>
                {notifications.length > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full animate-ping" />
                )}
              </button>

              {isNotifOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-surface-container border border-primary/20 rounded-xl shadow-2xl p-3 glass-panel z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="flex items-center justify-between pb-2 border-b border-outline-variant/20 mb-2">
                    <span className="text-xs font-label-caps uppercase tracking-wider text-on-surface">
                      Notifications
                    </span>
                    {notifications.length > 0 && (
                      <button
                        onClick={handleMarkAllNotifs}
                        className="text-[11px] text-primary hover:underline"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>
                  <div className="max-h-60 overflow-y-auto space-y-2">
                    {notifications.length === 0 ? (
                      <p className="text-center py-4 text-xs text-on-surface-variant">
                        No unread notifications
                      </p>
                    ) : (
                      notifications.map((n) => (
                        <Link
                          key={n.id}
                          to={n.link || "/notifications"}
                          onClick={() => setIsNotifOpen(false)}
                          className="block p-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high transition-colors"
                        >
                          <p className="text-xs font-medium text-on-surface">{n.title}</p>
                          <p className="text-[11px] text-on-surface-variant truncate">{n.message}</p>
                        </Link>
                      ))
                    )}
                  </div>
                  <Link
                    to="/notifications"
                    onClick={() => setIsNotifOpen(false)}
                    className="block text-center mt-2 pt-2 border-t border-outline-variant/20 text-xs text-primary hover:underline"
                  >
                    View all notifications
                  </Link>
                </div>
              )}
            </div>

            {/* User Profile Menu */}
            <div className="relative" ref={userMenuRef}>
              {authLoading ? (
                <div className="flex items-center gap-2 p-1.5 rounded-xl border border-transparent">
                  <div className="w-8 h-8 rounded-lg bg-surface-container-high animate-pulse" />
                  <div className="hidden lg:flex flex-col text-left gap-1.5">
                    <div className="w-20 h-2.5 bg-surface-container-high rounded animate-pulse" />
                    <div className="w-14 h-2 bg-surface-container-high rounded animate-pulse" />
                  </div>
                </div>
              ) : user ? (
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-surface-container border border-transparent hover:border-outline-variant/30 transition-all"
                >
                  <div className="w-8 h-8 rounded-lg bg-surface-container-high border border-primary/30 flex items-center justify-center overflow-hidden">
                    {user.avatar_url ? (
                      <img src={user.avatar_url} alt={user.full_name} className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-xs font-bold text-primary">
                        {user.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
                      </span>
                    )}
                  </div>
                  <div className="hidden lg:flex flex-col text-left">
                    <span className="text-xs font-medium text-on-surface leading-none">{user.full_name}</span>
                    <span className="text-[10px] text-on-surface-variant leading-none mt-1">{user.role}</span>
                  </div>
                  <span className="material-symbols-outlined text-base text-on-surface-variant">
                    expand_more
                  </span>
                </button>
              ) : null}

              {user && isUserMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-surface-container border border-primary/20 rounded-xl shadow-2xl p-2 glass-panel z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="px-3 py-2 border-b border-outline-variant/20 mb-1">
                    <p className="text-xs font-semibold text-on-surface">{user.full_name}</p>
                    <p className="text-[11px] text-on-surface-variant truncate">{user.email}</p>
                  </div>
                  <Link
                    to="/settings"
                    onClick={() => setIsUserMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-on-surface hover:bg-surface-container-high transition-colors"
                  >
                    <span className="material-symbols-outlined text-sm text-primary">settings</span>
                    Account & Workspace Settings
                  </Link>
                  <Link
                    to="/data-sources"
                    onClick={() => setIsUserMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-on-surface hover:bg-surface-container-high transition-colors"
                  >
                    <span className="material-symbols-outlined text-sm text-primary">hub</span>
                    Connected Data Sources
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-error hover:bg-error-container/20 transition-colors mt-1 border-t border-outline-variant/20 pt-2"
                  >
                    <span className="material-symbols-outlined text-sm">logout</span>
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Global Command Search Modal */}
      <CommandSearchModal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />

      {/* Daraz Product Detail Modal for Live Signals */}
      {selectedDarazId && (
        <DarazProductModal
          itemId={selectedDarazId}
          isOpen={true}
          onClose={() => setSelectedDarazId(null)}
        />
      )}
    </>
  );
};
