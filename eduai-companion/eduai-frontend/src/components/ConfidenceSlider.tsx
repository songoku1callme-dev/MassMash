import { motion } from "framer-motion";

/**
 * Block C: Confidence Slider — "Wie sicher warst du?"
 * 1 = Geraten, 5 = Sicher
 * Wird nach jeder Quiz-Antwort angezeigt.
 */
export function ConfidenceSlider({
  onSelect,
}: {
  onSelect: (level: 1 | 2 | 3 | 4 | 5) => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 p-3 rounded-xl"
      style={{
        background: "rgba(99,102,241,0.08)",
        border: "1px solid rgba(99,102,241,0.2)",
      }}
    >
      <p className="text-xs text-slate-400 mb-2">
        Wie sicher warst du? (1 = Geraten · 5 = Sicher)
      </p>
      <div className="flex gap-2">
        {([1, 2, 3, 4, 5] as const).map((n) => (
          <button
            key={n}
            onClick={() => onSelect(n)}
            className="flex-1 py-2 rounded-lg text-sm font-bold transition-all hover:scale-110"
            style={{
              background:
                n <= 2
                  ? "rgba(239,68,68,0.2)"
                  : n === 3
                  ? "rgba(245,158,11,0.2)"
                  : "rgba(34,197,94,0.2)",
              border:
                n <= 2
                  ? "1px solid rgba(239,68,68,0.4)"
                  : n === 3
                  ? "1px solid rgba(245,158,11,0.4)"
                  : "1px solid rgba(34,197,94,0.4)",
              color: n <= 2 ? "#fca5a5" : n === 3 ? "#fcd34d" : "#86efac",
            }}
          >
            {n}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

export default ConfidenceSlider;
