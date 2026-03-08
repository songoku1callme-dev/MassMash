import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { useAuthStore } from "../stores/authStore";
import NotificationBell from "./NotificationBell";
import ThemeToggle from "./ThemeToggle";
import { Flame, Zap, Coins } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "";

interface HeaderStats {
  xp: number;
  level: number;
  level_name: string;
  streak_days: number;
  coins: number;
}

export default function GlobalHeader() {
  const { user } = useAuthStore();
  const [stats, setStats] = useState<HeaderStats | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const token = localStorage.getItem("lumnos_access_token") || localStorage.getItem("lumnos_token");
      if (!token) return;
      const resp = await fetch(`${API_URL}/api/gamification/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setStats({
          xp: data.total_xp || 0,
          level: data.level || 1,
          level_name: data.level_name || "Neuling",
          streak_days: data.streak_days || 0,
          coins: data.coins || data.total_xp || 0,
        });
      }
    } catch {
      /* silently fail */
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5 * 60 * 1000); // refresh every 5 min
    return () => clearInterval(interval);
  }, [fetchStats]);

  const displayName = user?.full_name || user?.username || "Lernender";
  const avatarLetter = displayName[0]?.toUpperCase() || "?";
  const avatarUrl = user?.avatar_url;

  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-between px-4 py-2.5 shrink-0"
      style={{
        borderBottom: "1px solid var(--border-color)",
        background: "rgba(var(--surface-rgb), 0.5)",
        backdropFilter: "blur(12px)",
      }}
    >
      {/* Left: Avatar + Name */}
      <div className="flex items-center gap-3">
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt={displayName}
            className="w-8 h-8 rounded-full object-cover border-2 border-indigo-500/30"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-lumnos-gradient flex items-center justify-center text-white text-sm font-bold shadow-glow-sm">
            {avatarLetter}
          </div>
        )}
        <div className="hidden sm:block">
          <p className="text-sm font-semibold text-foreground leading-tight">{displayName}</p>
          {stats && (
            <p className="text-xs text-muted-foreground">
              Level {stats.level} &middot; {stats.level_name}
            </p>
          )}
        </div>
      </div>

      {/* Center: Stats pills */}
      <div className="flex items-center gap-2">
        {stats && (
          <>
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold"
              style={{
                background: "rgba(245,158,11,0.12)",
                border: "1px solid rgba(245,158,11,0.25)",
                color: "#f59e0b",
              }}
            >
              <Coins className="w-3.5 h-3.5" />
              {stats.coins.toLocaleString()}
            </motion.div>
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold"
              style={{
                background: "rgba(99,102,241,0.12)",
                border: "1px solid rgba(99,102,241,0.25)",
                color: "#6366f1",
              }}
            >
              <Zap className="w-3.5 h-3.5" />
              {stats.xp.toLocaleString()} XP
            </motion.div>
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold"
              style={{
                background: stats.streak_days > 0 ? "rgba(239,68,68,0.12)" : "rgba(var(--surface-rgb),0.5)",
                border: `1px solid ${stats.streak_days > 0 ? "rgba(239,68,68,0.25)" : "rgba(var(--surface-rgb),0.8)"}`,
                color: stats.streak_days > 0 ? "#ef4444" : "var(--muted-foreground)",
              }}
            >
              <Flame className="w-3.5 h-3.5" />
              {stats.streak_days}
            </motion.div>
          </>
        )}
      </div>

      {/* Right: Notification + Theme Toggle */}
      <div className="flex items-center gap-1">
        <NotificationBell />
        <ThemeToggle compact />
      </div>
    </motion.header>
  );
}
