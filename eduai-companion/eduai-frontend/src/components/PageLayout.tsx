import type { ReactNode } from "react";

interface PageLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}

/**
 * PageLayout — Wrapper fuer ALLE Nicht-Chat-Seiten.
 * Stellt sicher, dass jede Seite in sich selbst scrollt
 * und der App-Shell (Sidebar + Main) nicht beeinflusst wird.
 */
export default function PageLayout({ children, title, subtitle }: PageLayoutProps) {
  return (
    <div
      className="scrollable"
      style={{
        height: "100%",
        overflowY: "auto",
        overflowX: "hidden",
        padding: "32px",
      }}
    >
      {title && (
        <div style={{ marginBottom: "28px" }}>
          <h1
            style={{
              color: "white",
              fontSize: "26px",
              fontWeight: 700,
              marginBottom: "6px",
            }}
          >
            {title}
          </h1>
          {subtitle && (
            <p style={{ color: "#94a3b8", fontSize: "14px" }}>{subtitle}</p>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
