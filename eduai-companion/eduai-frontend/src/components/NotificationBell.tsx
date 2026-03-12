import { useState, useEffect, useRef, useCallback } from "react";
import { Bell } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "";

interface Notification {
  id: number;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

export default function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchBell = useCallback(async () => {
    try {
      const token = localStorage.getItem("lumnos_access_token");
      if (!token) return;
      const resp = await fetch(`${API_URL}/api/notifications/bell`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setUnread(data.unread_count || 0);
        setNotifications(data.notifications || []);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const markAllRead = async () => {
    try {
      const token = localStorage.getItem("lumnos_access_token");
      if (!token) return;
      await fetch(`${API_URL}/api/notifications/mark-all-read`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      setUnread(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      /* ignore */
    }
  };

  // Perfect School 4.1: WebSocket with ticket system + fallback to polling
  useEffect(() => {
    fetchBell();

    const token = localStorage.getItem("lumnos_token") || localStorage.getItem("lumnos_access_token");
    if (!token) {
      const interval = setInterval(fetchBell, 30000);
      return () => clearInterval(interval);
    }

    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let fallbackInterval: ReturnType<typeof setInterval> | null = null;

    const connectWS = async () => {
      try {
        // Get a short-lived ticket from the backend (Block 1.3)
        const ticketResp = await fetch(`${API_URL}/api/ws/ticket`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!ticketResp.ok) {
          if (!fallbackInterval) fallbackInterval = setInterval(fetchBell, 30000);
          return;
        }
        const { ticket, user_id } = await ticketResp.json();

        const wsBase = API_URL.replace(/^http/, "ws");
        const wsUrl = `${wsBase}/api/notifications/ws/notifications/${user_id}?ticket=${ticket}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (fallbackInterval) { clearInterval(fallbackInterval); fallbackInterval = null; }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "init") setUnread(data.unread_count || 0);
            else if (data.type === "new_notification") { setUnread((p) => p + 1); fetchBell(); }
          } catch { /* ignore */ }
        };

        ws.onclose = () => {
          wsRef.current = null;
          if (!fallbackInterval) fallbackInterval = setInterval(fetchBell, 30000);
          reconnectTimer = setTimeout(connectWS, 5000);
        };

        ws.onerror = () => ws.close();

        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        }, 25000);
        ws.addEventListener("close", () => clearInterval(pingInterval));
      } catch {
        if (!fallbackInterval) fallbackInterval = setInterval(fetchBell, 30000);
      }
    };

    connectWS();

    return () => {
      if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (fallbackInterval) clearInterval(fallbackInterval);
    };
  }, [fetchBell]);

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const typeColor: Record<string, string> = {
    tip: "bg-blue-100 text-blue-700",
    reminder: "bg-yellow-100 text-yellow-700",
    achievement: "bg-green-100 text-green-700",
    warning: "bg-red-100 text-red-700",
    info: "bg-gray-100 text-gray-700",
  };

  const timeAgo = (dateStr: string) => {
    if (!dateStr) return "";
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `vor ${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `vor ${hours}h`;
    return `vor ${Math.floor(hours / 24)}d`;
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => { setOpen(!open); if (!open && unread > 0) markAllRead(); }}
        className="relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        title="Benachrichtigungen"
      >
        <Bell className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center animate-pulse">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 z-50 max-h-96 overflow-y-auto">
          <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h3 className="font-semibold text-sm text-gray-900 dark:text-white">Benachrichtigungen</h3>
            {notifications.length > 0 && (
              <button onClick={markAllRead} className="text-xs text-blue-600 hover:underline">
                Alle gelesen
              </button>
            )}
          </div>
          {notifications.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">
              Keine Benachrichtigungen
            </div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                className={`p-3 border-b border-gray-100 dark:border-gray-700 last:border-0 ${
                  !n.is_read ? "bg-blue-50/50 dark:bg-blue-900/10" : ""
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${typeColor[n.type] || typeColor.info}`}>
                    {n.type}
                  </span>
                  <span className="text-xs text-gray-400 ml-auto">{timeAgo(n.created_at)}</span>
                </div>
                <p className="text-sm font-medium text-gray-900 dark:text-white mt-1">{n.title}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{n.message}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
