import { useState, useEffect, useCallback } from "react";
import { notificationBellApi } from "../services/api";
import { Bell, Check, CheckCheck, Loader2, Inbox } from "lucide-react";
import { PageLoader, ErrorState, EmptyState } from "../components/PageStates";

interface Notification {
  id: number;
  title: string;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);
  const [markingId, setMarkingId] = useState<number | null>(null);

  const loadNotifications = useCallback(async () => {
    setError(false);
    try {
      const data = await notificationBellApi.bell();
      setNotifications(data.notifications || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const handleMarkRead = async (id: number) => {
    setMarkingId(id);
    try {
      await notificationBellApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    } catch {
      // Stille Fehlerbehandlung
    } finally {
      setMarkingId(null);
    }
  };

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await notificationBellApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch {
      // Stille Fehlerbehandlung
    } finally {
      setMarkingAll(false);
    }
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "achievement": return "\u{1F3C6}";
      case "streak": return "\u{1F525}";
      case "quiz": return "\u{1F4DD}";
      case "level_up": return "\u{2B50}";
      case "reminder": return "\u{23F0}";
      default: return "\u{1F514}";
    }
  };

  if (loading) return <PageLoader text="Benachrichtigungen laden..." />;
  if (error) return <ErrorState message="Fehler beim Laden der Benachrichtigungen." onRetry={() => { setLoading(true); loadNotifications(); }} />;

  return (
    <div className="p-4 lg:p-6 max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
            <Bell className="w-7 h-7" style={{ color: "var(--icon-color)" }} />
            Benachrichtigungen
          </h1>
          <p className="theme-text-secondary mt-1">
            {unreadCount > 0
              ? `${unreadCount} ungelesene Nachricht${unreadCount > 1 ? "en" : ""}`
              : "Alle Benachrichtigungen gelesen"}
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            disabled={markingAll}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all hover:scale-105"
            style={{
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "white",
              boxShadow: "0 0 20px rgba(99,102,241,0.3)",
            }}
          >
            {markingAll ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCheck className="w-4 h-4" />
            )}
            Alle gelesen
          </button>
        )}
      </div>

      {/* Notifications List */}
      {notifications.length === 0 ? (
        <EmptyState
          title="Keine Benachrichtigungen"
          description="Du hast noch keine Benachrichtigungen erhalten. Lerne weiter, um Belohnungen zu verdienen!"
          icon={<Inbox className="w-8 h-8 text-indigo-400" />}
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`p-4 rounded-xl border transition-all ${
                n.read
                  ? "border-[var(--border-color)] opacity-70"
                  : "border-indigo-500/30 bg-indigo-500/5"
              }`}
              style={{
                background: n.read ? "var(--bg-surface)" : undefined,
              }}
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl shrink-0">{getTypeIcon(n.type)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className={`text-sm font-semibold ${n.read ? "theme-text-secondary" : "theme-text"}`}>
                      {n.title}
                    </p>
                    {!n.read && (
                      <span className="w-2 h-2 rounded-full bg-indigo-500 shrink-0" />
                    )}
                  </div>
                  <p className="text-sm theme-text-secondary">{n.message}</p>
                  <p className="text-xs theme-text-secondary mt-2">
                    {new Date(n.created_at).toLocaleDateString("de-DE", {
                      day: "2-digit",
                      month: "long",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
                {!n.read && (
                  <button
                    onClick={() => handleMarkRead(n.id)}
                    disabled={markingId === n.id}
                    className="shrink-0 p-2 rounded-lg hover:bg-indigo-500/10 transition-colors"
                    title="Als gelesen markieren"
                  >
                    {markingId === n.id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                    ) : (
                      <Check className="w-4 h-4 text-indigo-400" />
                    )}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
