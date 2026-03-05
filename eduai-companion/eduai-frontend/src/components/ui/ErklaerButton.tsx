import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { erklaerungApi } from "../../services/api";
import { useNavigate } from "react-router-dom";

interface ErklaerButtonProps {
  thema: string;
  fach?: string;
  kontext?: string;
  variant?: "inline" | "floating" | "minimal";
  className?: string;
}

export default function ErklaerButton({
  thema,
  fach = "Allgemein",
  kontext = "",
  variant = "inline",
  className = "",
}: ErklaerButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [erklaerung, setErklaerung] = useState("");
  const [error, setError] = useState("");
  const popupRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Close popup on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popupRef.current && !popupRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleClick = async () => {
    if (isOpen) {
      setIsOpen(false);
      return;
    }
    setIsOpen(true);
    setLoading(true);
    setError("");
    setErklaerung("");

    try {
      const result = await erklaerungApi.schnell({ thema, fach, kontext });
      setErklaerung(result.erklaerung);
    } catch (err) {
      setError("Erklärung konnte nicht geladen werden. Versuche es nochmal.");
      console.error("ErklaerButton error:", err);
    } finally {
      setLoading(false);
    }
  };

  const goToChat = () => {
    setIsOpen(false);
    navigate(`/chat?topic=${encodeURIComponent(thema)}`);
  };

  const buttonStyles = {
    inline:
      "px-3 py-1.5 text-xs rounded-lg bg-gradient-to-r from-cyan-500/20 to-purple-500/20 border border-cyan-500/30 text-cyan-300 hover:from-cyan-500/30 hover:to-purple-500/30 hover:border-cyan-400/50 transition-all",
    floating:
      "w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-110 transition-all flex items-center justify-center text-lg",
    minimal:
      "text-cyan-400/70 hover:text-cyan-300 text-xs underline underline-offset-2 transition-colors",
  };

  return (
    <div className={`relative inline-block ${className}`}>
      <motion.button
        onClick={handleClick}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className={buttonStyles[variant]}
        title={`Erkläre: ${thema}`}
      >
        {variant === "floating" ? "💡" : variant === "minimal" ? "Erklärung" : "💡 Erklär mir das"}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            ref={popupRef}
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="absolute z-50 mt-2 w-80 max-w-[90vw] rounded-xl border border-white/10 bg-slate-900/95 backdrop-blur-xl shadow-2xl shadow-black/40"
            style={{ left: "50%", transform: "translateX(-50%)" }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="text-lg">💡</span>
                <span className="text-sm font-medium text-white/90">Erklärung</span>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-white/40 hover:text-white/70 transition-colors text-lg leading-none"
              >
                &times;
              </button>
            </div>

            {/* Content */}
            <div className="px-4 py-3 min-h-[60px]">
              {loading ? (
                <div className="flex items-center gap-1 text-cyan-400">
                  <span className="text-sm">Denke nach</span>
                  <span className="flex gap-0.5">
                    <motion.span
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
                      className="text-lg"
                    >
                      .
                    </motion.span>
                    <motion.span
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
                      className="text-lg"
                    >
                      .
                    </motion.span>
                    <motion.span
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
                      className="text-lg"
                    >
                      .
                    </motion.span>
                  </span>
                </div>
              ) : error ? (
                <p className="text-sm text-red-400">{error}</p>
              ) : (
                <p className="text-sm text-white/80 leading-relaxed">{erklaerung}</p>
              )}
            </div>

            {/* Footer */}
            {!loading && erklaerung && (
              <div className="px-4 py-2.5 border-t border-white/10">
                <button
                  onClick={goToChat}
                  className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1"
                >
                  <span>💬</span>
                  <span>Mehr Details im Chat</span>
                  <span className="ml-auto">&rarr;</span>
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
