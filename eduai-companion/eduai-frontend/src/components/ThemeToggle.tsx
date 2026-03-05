import type { CSSProperties } from "react";
import { useThemeStore } from "../stores/themeStore";

interface ThemeToggleProps {
  compact?: boolean;
  className?: string;
}

export default function ThemeToggle({ compact = false, className }: ThemeToggleProps) {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  const baseStyle: CSSProperties = {
    borderRadius: 12,
    border: "1px solid var(--border-color)",
    background: "var(--bg-surface)",
    color: "var(--text-primary)",
  };

  const activeStyle: CSSProperties = {
    borderRadius: 12,
    border: "1px solid var(--accent-border)",
    background: "var(--accent)",
    color: "#ffffff",
    boxShadow: "var(--shadow-glow)",
  };

  const btnClass = compact
    ? "px-2 py-2 text-sm font-semibold flex items-center justify-center"
    : "px-3 py-2 text-sm font-semibold flex items-center justify-center gap-2";

  return (
    <div className={className} style={{ display: "flex", gap: 8 }}>
      <button
        type="button"
        aria-pressed={theme === "dark"}
        onClick={() => setTheme("dark")}
        className={btnClass}
        style={theme === "dark" ? activeStyle : baseStyle}
        title="Dark"
      >
        <span>{"🌙"}</span>
        {!compact && <span>Dark</span>}
      </button>

      <button
        type="button"
        aria-pressed={theme === "system"}
        onClick={() => setTheme("system")}
        className={btnClass}
        style={theme === "system" ? activeStyle : baseStyle}
        title="System"
      >
        <span>{"💻"}</span>
        {!compact && <span>System</span>}
      </button>

      <button
        type="button"
        aria-pressed={theme === "light"}
        onClick={() => setTheme("light")}
        className={btnClass}
        style={theme === "light" ? activeStyle : baseStyle}
        title="Light"
      >
        <span>{"☀️"}</span>
        {!compact && <span>Light</span>}
      </button>
    </div>
  );
}
