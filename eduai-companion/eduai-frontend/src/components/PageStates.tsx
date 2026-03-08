import { motion } from "framer-motion";
import { AlertTriangle, RefreshCw, Inbox, Loader2 } from "lucide-react";

/** Skeleton loading placeholder with shimmer animation */
export function LoadingSkeleton({ lines = 4, className = "" }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-4 p-6 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0.3 }}
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.1 }}
          className="rounded-xl"
          style={{
            height: i === 0 ? "32px" : "20px",
            width: i === 0 ? "60%" : `${80 - i * 10}%`,
            background: "rgba(var(--surface-rgb), 0.5)",
          }}
        />
      ))}
    </div>
  );
}

/** Card-style skeleton for grid layouts */
export function CardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0.3 }}
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.15 }}
          className="rounded-2xl p-6 space-y-3"
          style={{
            background: "rgba(var(--surface-rgb), 0.3)",
            border: "1px solid rgba(var(--border-rgb, 99,102,241), 0.1)",
          }}
        >
          <div className="h-6 w-1/2 rounded-lg" style={{ background: "rgba(var(--surface-rgb), 0.5)" }} />
          <div className="h-4 w-3/4 rounded" style={{ background: "rgba(var(--surface-rgb), 0.4)" }} />
          <div className="h-4 w-2/3 rounded" style={{ background: "rgba(var(--surface-rgb), 0.3)" }} />
          <div className="h-10 w-full rounded-xl mt-4" style={{ background: "rgba(var(--surface-rgb), 0.4)" }} />
        </motion.div>
      ))}
    </div>
  );
}

/** Full-page loading spinner */
export function PageLoader({ text = "Laden..." }: { text?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center min-h-[400px] gap-4"
    >
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
      >
        <Loader2 className="w-8 h-8 text-indigo-400" />
      </motion.div>
      <p className="text-sm text-slate-400">{text}</p>
    </motion.div>
  );
}

/** Error state with retry button */
export function ErrorState({
  message = "Fehler beim Laden der Daten.",
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center min-h-[300px] gap-4 p-6 text-center"
    >
      <div
        className="w-16 h-16 rounded-full flex items-center justify-center"
        style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)" }}
      >
        <AlertTriangle className="w-8 h-8 text-red-400" />
      </div>
      <p className="text-slate-300 text-sm max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-indigo-300 hover:text-indigo-200 transition-colors"
          style={{
            background: "rgba(99,102,241,0.1)",
            border: "1px solid rgba(99,102,241,0.3)",
          }}
        >
          <RefreshCw className="w-4 h-4" />
          Erneut versuchen
        </button>
      )}
    </motion.div>
  );
}

/** Empty state when no data is available */
export function EmptyState({
  title = "Noch keine Daten",
  description = "Hier gibt es noch nichts zu sehen.",
  icon,
  action,
}: {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center min-h-[300px] gap-4 p-6 text-center"
    >
      <div
        className="w-16 h-16 rounded-full flex items-center justify-center"
        style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)" }}
      >
        {icon || <Inbox className="w-8 h-8 text-indigo-400" />}
      </div>
      <div>
        <p className="text-slate-200 font-medium">{title}</p>
        <p className="text-slate-400 text-sm mt-1">{description}</p>
      </div>
      {action && (
        <button
          onClick={action.onClick}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white transition-all hover:scale-105"
          style={{
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            boxShadow: "0 0 20px rgba(99,102,241,0.3)",
          }}
        >
          {action.label}
        </button>
      )}
    </motion.div>
  );
}
