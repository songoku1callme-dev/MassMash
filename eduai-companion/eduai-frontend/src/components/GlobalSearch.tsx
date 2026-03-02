import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * Infra 5: Global Search — Cmd/Ctrl+K zum Suchen
 * Alle Fächer + Themen durchsuchbar.
 */

const ALLE_THEMEN = [
  // Mathematik
  { label: "Pythagoras", fach: "Mathematik", page: "chat" },
  { label: "Ableitungsregeln", fach: "Mathematik", page: "chat" },
  { label: "Kurvendiskussion", fach: "Mathematik", page: "chat" },
  { label: "Lineare Gleichungen", fach: "Mathematik", page: "quiz" },
  { label: "Quadratische Funktionen", fach: "Mathematik", page: "chat" },
  { label: "Integralrechnung", fach: "Mathematik", page: "chat" },
  // Physik
  { label: "Newtonsche Gesetze", fach: "Physik", page: "chat" },
  { label: "Elektromagnetismus", fach: "Physik", page: "chat" },
  { label: "Thermodynamik", fach: "Physik", page: "chat" },
  // Chemie
  { label: "Periodensystem", fach: "Chemie", page: "chat" },
  { label: "Organische Chemie", fach: "Chemie", page: "chat" },
  { label: "Reaktionsgleichungen", fach: "Chemie", page: "chat" },
  // Biologie
  { label: "Zellbiologie", fach: "Biologie", page: "chat" },
  { label: "Genetik", fach: "Biologie", page: "chat" },
  { label: "Evolution", fach: "Biologie", page: "chat" },
  // Deutsch
  { label: "Gedichtanalyse", fach: "Deutsch", page: "chat" },
  { label: "Erörterung", fach: "Deutsch", page: "chat" },
  { label: "Konjunktiv", fach: "Deutsch", page: "chat" },
  // Geschichte
  { label: "Weimarer Republik", fach: "Geschichte", page: "chat" },
  { label: "Nationalsozialismus", fach: "Geschichte", page: "chat" },
  { label: "Kalter Krieg", fach: "Geschichte", page: "chat" },
  // Seiten
  ...["Mathematik", "Physik", "Chemie", "Biologie", "Deutsch",
      "Geschichte", "Englisch", "Informatik", "Latein", "Philosophie",
      "Wirtschaft", "Politik", "Musik", "Kunst", "Sport", "Religion",
      "Ethik", "Geografie", "Psychologie", "Sozialkunde"]
    .map(f => ({ label: f, fach: f, page: "chat" })),
  // Navigation
  { label: "Dashboard", fach: "Navigation", page: "dashboard" },
  { label: "Quiz", fach: "Navigation", page: "quiz" },
  { label: "Karteikarten", fach: "Navigation", page: "flashcards" },
  { label: "Mündliche Prüfung", fach: "Navigation", page: "voice-exam" },
  { label: "Abitur-Simulation", fach: "Navigation", page: "abitur" },
  { label: "Lernpfad", fach: "Navigation", page: "learning" },
  { label: "Turniere", fach: "Navigation", page: "turnier" },
  { label: "Einstellungen", fach: "Navigation", page: "settings" },
  { label: "Statistiken", fach: "Navigation", page: "meine-stats" },
];

interface GlobalSearchProps {
  onNavigate: (page: string) => void;
}

export function GlobalSearch({ onNavigate }: GlobalSearchProps) {
  const [offen, setOffen] = useState(false);
  const [q, setQ] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Cmd/Ctrl + K zum Öffnen
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOffen(o => !o);
        setTimeout(() => inputRef.current?.focus(), 50);
      }
      if (e.key === "Escape") setOffen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const treffer = q.length > 1
    ? ALLE_THEMEN.filter(t =>
        t.label.toLowerCase().includes(q.toLowerCase()) ||
        t.fach.toLowerCase().includes(q.toLowerCase())
      ).slice(0, 8)
    : [];

  return (
    <>
      {/* Search-Trigger */}
      <button
        onClick={() => { setOffen(true); setTimeout(() => inputRef.current?.focus(), 50); }}
        className="flex items-center gap-2 px-3 py-2 rounded-xl
                   text-sm text-slate-400 transition-all w-full
                   hover:text-slate-200"
        style={{
          background: "rgba(30,41,59,0.5)",
          border: "1px solid rgba(99,102,241,0.2)",
        }}
      >
        <span>🔍</span>
        <span className="flex-1 text-left">Suchen...</span>
        <span
          className="text-xs px-1.5 py-0.5 rounded"
          style={{ background: "rgba(99,102,241,0.2)", color: "#a5b4fc" }}
        >
          ⌘K
        </span>
      </button>

      {/* Overlay */}
      <AnimatePresence>
        {offen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4"
            style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)" }}
            onClick={() => setOffen(false)}
          >
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10 }}
              className="w-full max-w-md rounded-2xl overflow-hidden"
              style={{
                background: "rgba(15,23,42,0.98)",
                border: "1px solid rgba(99,102,241,0.35)",
                boxShadow: "0 0 50px rgba(99,102,241,0.3)",
              }}
              onClick={e => e.stopPropagation()}
            >
              <div
                className="flex items-center gap-3 p-4"
                style={{ borderBottom: "1px solid rgba(99,102,241,0.15)" }}
              >
                <span className="text-slate-400">🔍</span>
                <input
                  ref={inputRef}
                  value={q}
                  onChange={e => setQ(e.target.value)}
                  placeholder="Fach oder Thema suchen..."
                  className="flex-1 bg-transparent text-white placeholder:text-slate-500 outline-none"
                />
                <kbd className="text-xs text-slate-500">ESC</kbd>
              </div>

              {treffer.length > 0 && (
                <div className="p-2">
                  {treffer.map((t, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        onNavigate(t.page);
                        setOffen(false);
                        setQ("");
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2.5
                                 rounded-xl text-sm transition-all text-left
                                 hover:bg-indigo-500/10"
                    >
                      <span className="text-slate-400">
                        {t.page === "chat" ? "🤖" : t.page === "quiz" ? "⚡" : "📄"}
                      </span>
                      <span className="text-white flex-1">{t.label}</span>
                      <span className="text-xs text-slate-500">{t.fach}</span>
                    </button>
                  ))}
                </div>
              )}

              {q.length > 1 && treffer.length === 0 && (
                <div className="p-8 text-center text-slate-500 text-sm">
                  Keine Ergebnisse für &quot;{q}&quot;
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default GlobalSearch;
