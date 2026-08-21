import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { notificationService } from "../../services/domainServices";
import type { NotificationItem } from "../../types";
import { LoadingSpinner, EmptyState, ErrorState } from "../../components/common/StateComponents";
import { useToast } from "../../context/ToastContext";

export const NotificationsPage: React.FC = () => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { showToast } = useToast();

  const fetchNotifications = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await notificationService.list(false);
      if (res.success && res.data) {
        setNotifications(res.data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleMarkAll = async () => {
    try {
      await notificationService.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      showToast("All notifications marked as read", "success");
    } catch (err: any) {
      showToast(err.message || "Action failed", "error");
    }
  };

  const handleMarkOne = async (id: string) => {
    try {
      await notificationService.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err: any) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/15 pb-6">
        <div>
          <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
            ACTIVITY & UPDATES
          </span>
          <h1 className="text-2xl md:text-3xl font-headline-md font-bold text-on-surface mt-1">
            Notifications
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Real-time feed of background report generation, system status, and signal alarms.
          </p>
        </div>

        {notifications.some((n) => !n.is_read) && (
          <button
            onClick={handleMarkAll}
            className="px-4 py-2 rounded-xl bg-surface-container border border-outline-variant/30 text-xs font-label-caps text-primary hover:border-primary/40 transition-all font-semibold"
          >
            Mark All as Read
          </button>
        )}
      </div>

      {loading ? (
        <LoadingSpinner size="lg" label="Loading notification history..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchNotifications} />
      ) : notifications.length === 0 ? (
        <EmptyState
          title="No Notifications"
          description="You're completely caught up! New system updates and report notifications will appear here."
          icon="notifications_none"
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((item) => (
            <div
              key={item.id}
              className={`p-4 rounded-2xl border transition-all flex items-center justify-between gap-4 glass-card ${
                !item.is_read
                  ? "bg-surface-container border-primary/30"
                  : "bg-surface-container-low border-outline-variant/15 opacity-80"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary shrink-0">
                  <span className="material-symbols-outlined text-lg">
                    {item.type === "alert"
                      ? "warning"
                      : item.type === "report"
                      ? "description"
                      : "notifications"}
                  </span>
                </div>
                <div>
                  <h4 className="text-xs font-bold text-on-surface">{item.title}</h4>
                  <p className="text-xs text-on-surface-variant">{item.message}</p>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                {item.link && (
                  <Link
                    to={item.link}
                    onClick={() => handleMarkOne(item.id)}
                    className="text-xs text-primary font-semibold hover:underline"
                  >
                    Open Link →
                  </Link>
                )}
                {!item.is_read && (
                  <button
                    onClick={() => handleMarkOne(item.id)}
                    className="p-1 text-on-surface-variant hover:text-on-surface"
                    title="Mark read"
                  >
                    <span className="material-symbols-outlined text-base">check</span>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
