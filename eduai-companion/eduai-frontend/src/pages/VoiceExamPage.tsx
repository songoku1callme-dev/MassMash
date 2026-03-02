import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "../stores/authStore";
import { api } from "../services/api";
import LumnosOrb from "../components/LumnosOrb";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Typen & Konstanten
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

type ExamState = "idle" | "starting" | "asking" | "listening" | "evaluating" | "feedback" | "finished";

const MAX_FRAGEN = 6;

const ORBS_ZUSTAND: Record<ExamState, { color: string; label: string }> = {
  idle:       { color: "default",     label: "Bereit" },
  starting:   { color: "Informatik",  label: "Startet..." },
  asking:     { color: "Geschichte",  label: "Frage..." },
  listening:  { color: "Biologie",    label: "Höre zu..." },
  evaluating: { color: "Latein",      label: "Denke..." },
  feedback:   { color: "Deutsch",     label: "Feedback" },
  finished:   { color: "default",     label: "Fertig!" },
};

const FÄCHER = [
  "Mathematik", "Physik", "Chemie", "Biologie", "Deutsch",
  "Geschichte", "Englisch", "Informatik", "Latein", "Geografie",
];

interface VerlaufItem {
  frage: string;
  antwort: string;
  bewertung: string;
  score: number;
  feedback: string;
  feedback_gesprochen: string;
}

interface ExamResult {
  note: number;
  avg_score: number;
  total_score: number;
  total_questions: number;
  stärken: string[];
  schwächen: string[];
  karteikarten_erstellt: number;
  feedback: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Hauptkomponente
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export default function VoiceExamPage() {
  const { user } = useAuthStore();
  const [state, setState] = useState<ExamState>("idle");
  const [fach, setFach] = useState("Mathematik");
  const [frageNr, setFrageNr] = useState(0);
  const [aktuelleFrage, setAktuelleFrage] = useState("");
  const [transcript, setTranscript] = useState("");
  const [verlauf, setVerlauf] = useState<VerlaufItem[]>([]);
  const [currentFeedback, setCurrentFeedback] = useState<VerlaufItem | null>(null);
  const [result, setResult] = useState<ExamResult | null>(null);
  const [error, setError] = useState("");

  const synthRef = useRef<SpeechSynthesisUtterance | null>(null);
  const recognRef = useRef<SpeechRecognition | null>(null);
  const transcriptRef = useRef("");

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      window.speechSynthesis.cancel();
      if (recognRef.current) {
        try { recognRef.current.abort(); } catch { /* noop */ }
      }
    };
  }, []);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // TTS: Text vorlesen
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const speak = useCallback((text: string, onEnd?: () => void) => {
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.lang = "de-DE";
    utt.rate = 1.0;
    utt.pitch = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const deVoice = voices.find(v => v.lang.startsWith("de"));
    if (deVoice) utt.voice = deVoice;
    if (onEnd) utt.onend = onEnd;
    synthRef.current = utt;
    window.speechSynthesis.speak(utt);
  }, []);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // STT: Zuhören
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const startListening = useCallback(() => {
    const SR = (window as unknown as Record<string, unknown>).SpeechRecognition ||
               (window as unknown as Record<string, unknown>).webkitSpeechRecognition;
    if (!SR) {
      setError("Spracherkennung nicht unterstützt. Bitte Chrome verwenden.");
      return;
    }
    const recog = new (SR as new () => SpeechRecognition)();
    recog.lang = "de-DE";
    recog.continuous = false;
    recog.interimResults = true;

    setState("listening");
    setTranscript("");
    transcriptRef.current = "";

    recog.onresult = (e: SpeechRecognitionEvent) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) {
        text += e.results[i][0].transcript;
      }
      setTranscript(text);
      transcriptRef.current = text;
    };

    recog.onend = () => {
      const finalText = transcriptRef.current;
      if (finalText.trim().length < 3) {
        speak("Ich habe dich nicht verstanden. Bitte versuche es nochmal.", () => {
          startListening();
        });
        return;
      }
      evaluateAnswer(finalText);
    };

    recog.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (e.error !== "no-speech") {
        setError(`Spracherkennungsfehler: ${e.error}`);
      }
    };

    recognRef.current = recog;
    recog.start();
  }, [speak]);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Antwort bewerten
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const evaluateAnswer = async (antwort: string) => {
    setState("evaluating");
    try {
      const resp = await api.post("/api/exam/evaluate", {
        fach,
        frage: aktuelleFrage,
        antwort,
      });

      const fb: VerlaufItem = {
        frage: aktuelleFrage,
        antwort,
        bewertung: resp.data.bewertung || "teilweise",
        score: resp.data.score || 5,
        feedback: resp.data.feedback || "",
        feedback_gesprochen: resp.data.feedback_gesprochen || "Weiter so!",
      };

      setCurrentFeedback(fb);
      setVerlauf(prev => [...prev, fb]);
      setState("feedback");

      // Feedback vorlesen
      speak(fb.feedback_gesprochen, () => {
        if (frageNr >= MAX_FRAGEN) {
          finishExam([...verlauf, fb]);
        } else {
          nextQuestion([...verlauf, fb]);
        }
      });
    } catch {
      setError("Bewertung fehlgeschlagen. Bitte versuche es erneut.");
      setState("asking");
    }
  };

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Prüfung starten
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const startExam = async () => {
    setError("");
    setVerlauf([]);
    setResult(null);
    setCurrentFeedback(null);
    setState("starting");

    try {
      const resp = await api.post("/api/exam/start", {
        fach,
        klasse: user?.school_grade || "10",
        bundesland: user?.bundesland || "Bayern",
      });

      const greeting = resp.data.greeting || `Willkommen zur Prüfung in ${fach}!`;
      const frage = resp.data.frage || "Was ist die Definition von Energie?";

      speak(greeting, () => {
        setAktuelleFrage(frage);
        setFrageNr(1);
        setState("asking");
        speak(frage, () => {
          startListening();
        });
      });
    } catch {
      setError("Prüfung konnte nicht gestartet werden.");
      setState("idle");
    }
  };

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Nächste Frage
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const nextQuestion = async (currentVerlauf: VerlaufItem[]) => {
    const nextNr = frageNr + 1;
    setFrageNr(nextNr);
    setState("asking");

    try {
      const resp = await api.post("/api/exam/next", {
        fach,
        verlauf: currentVerlauf.map(v => ({ frage: v.frage, score: v.score })),
        frage_nr: nextNr,
        klasse: user?.school_grade || "10",
        bundesland: user?.bundesland || "Bayern",
      });

      const frage = resp.data.frage || "Erkläre den Unterschied zwischen...";
      setAktuelleFrage(frage);
      speak(frage, () => {
        startListening();
      });
    } catch {
      setError("Nächste Frage konnte nicht geladen werden.");
    }
  };

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Prüfung beenden
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const finishExam = async (finalVerlauf: VerlaufItem[]) => {
    setState("finished");

    try {
      const resp = await api.post("/api/exam/finish", {
        fach,
        verlauf: finalVerlauf.map(v => ({
          frage: v.frage,
          antwort: v.antwort,
          bewertung: v.bewertung,
          score: v.score,
        })),
      });
      setResult(resp.data);
      speak(resp.data.feedback || "Prüfung beendet!");
    } catch {
      setError("Ergebnis konnte nicht berechnet werden.");
    }
  };

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Render
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const orbState = ORBS_ZUSTAND[state];

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-white mb-1">
          Mündliche Prüfung
        </h1>
        <p className="text-sm text-slate-400">
          6 Fragen · KI-Bewertung · Automatische Karteikarten
        </p>
      </div>

      {/* Orb */}
      <div className="flex flex-col items-center gap-3">
        <LumnosOrb
          fach={orbState.color}
          isTyping={state === "evaluating" || state === "starting"}
          isListening={state === "listening"}
          size="lg"
          onClick={state === "idle" ? startExam : undefined}
        />
        <motion.div
          key={state}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-sm font-medium"
          style={{ color: "rgba(99,102,241,0.8)" }}
        >
          {orbState.label}
        </motion.div>
      </div>

      {/* Fortschrittsbalken */}
      {state !== "idle" && state !== "finished" && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-slate-400">
            <span>Frage {frageNr} von {MAX_FRAGEN}</span>
            <span>{Math.round((frageNr / MAX_FRAGEN) * 100)}%</span>
          </div>
          <div className="h-2 rounded-full" style={{ background: "rgba(30,41,59,0.8)" }}>
            <motion.div
              className="h-full rounded-full"
              style={{ background: "linear-gradient(90deg, #6366f1, #8b5cf6)" }}
              animate={{ width: `${(frageNr / MAX_FRAGEN) * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>
      )}

      {/* Fehler */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="p-3 rounded-xl text-sm text-red-300"
            style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)" }}
          >
            {error}
            <button onClick={() => setError("")} className="ml-2 underline">Schließen</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Idle: Fach-Auswahl */}
      {state === "idle" && !result && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* User Info */}
          <div className="flex gap-3 text-xs text-slate-400">
            <span className="px-2 py-1 rounded-lg" style={{ background: "rgba(99,102,241,0.1)" }}>
              Klasse {user?.school_grade || "10"}
            </span>
            <span className="px-2 py-1 rounded-lg" style={{ background: "rgba(99,102,241,0.1)" }}>
              {user?.bundesland || "Bayern"}
            </span>
            <span className="px-2 py-1 rounded-lg" style={{ background: "rgba(99,102,241,0.1)" }}>
              {user?.school_type || "Gymnasium"}
            </span>
          </div>

          {/* Fach Selector */}
          <div>
            <label className="text-xs text-slate-400 mb-2 block">Prüfungsfach wählen:</label>
            <div className="grid grid-cols-2 gap-2">
              {FÄCHER.map(f => (
                <button
                  key={f}
                  onClick={() => setFach(f)}
                  className="py-2.5 px-3 rounded-xl text-sm font-medium transition-all"
                  style={{
                    background: fach === f
                      ? "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(139,92,246,0.2))"
                      : "rgba(30,41,59,0.5)",
                    border: fach === f
                      ? "1px solid rgba(99,102,241,0.5)"
                      : "1px solid rgba(99,102,241,0.15)",
                    color: fach === f ? "#a5b4fc" : "#94a3b8",
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Start Button */}
          <button
            onClick={startExam}
            className="w-full py-3 rounded-xl font-bold text-white transition-all hover:scale-[1.02]"
            style={{
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              boxShadow: "0 0 20px rgba(99,102,241,0.4)",
            }}
          >
            Prüfung starten
          </button>
        </motion.div>
      )}

      {/* Aktive Prüfung: Frage + Transkript */}
      {(state === "asking" || state === "listening" || state === "evaluating") && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-4"
        >
          {/* Aktuelle Frage */}
          <div className="p-4 rounded-2xl" style={{
            background: "rgba(30,41,59,0.6)",
            border: "1px solid rgba(99,102,241,0.2)",
          }}>
            <p className="text-xs text-indigo-400 mb-1 font-medium">Frage {frageNr}:</p>
            <p className="text-white">{aktuelleFrage}</p>
          </div>

          {/* Transkript */}
          {(state === "listening" || transcript) && (
            <div className="p-3 rounded-xl" style={{
              background: "rgba(34,197,94,0.08)",
              border: "1px solid rgba(34,197,94,0.2)",
            }}>
              <p className="text-xs text-green-400 mb-1">Deine Antwort:</p>
              <p className="text-slate-300 text-sm">
                {transcript || (
                  <span className="animate-pulse text-slate-500">Höre zu...</span>
                )}
              </p>
            </div>
          )}

          {state === "evaluating" && (
            <div className="text-center text-sm text-slate-400 animate-pulse">
              Bewertung läuft...
            </div>
          )}
        </motion.div>
      )}

      {/* Feedback */}
      {state === "feedback" && currentFeedback && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-2xl space-y-2"
          style={{
            background: currentFeedback.score >= 7
              ? "rgba(34,197,94,0.1)"
              : currentFeedback.score >= 4
              ? "rgba(245,158,11,0.1)"
              : "rgba(239,68,68,0.1)",
            border: `1px solid ${
              currentFeedback.score >= 7 ? "rgba(34,197,94,0.3)"
              : currentFeedback.score >= 4 ? "rgba(245,158,11,0.3)"
              : "rgba(239,68,68,0.3)"
            }`,
          }}
        >
          <div className="flex items-center gap-2">
            <span className="text-lg">
              {currentFeedback.score >= 7 ? "✓" : currentFeedback.score >= 4 ? "~" : "✗"}
            </span>
            <span className="font-bold text-white">
              {currentFeedback.score}/10 Punkte
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{
              background: currentFeedback.bewertung === "richtig"
                ? "rgba(34,197,94,0.2)" : currentFeedback.bewertung === "teilweise"
                ? "rgba(245,158,11,0.2)" : "rgba(239,68,68,0.2)",
              color: currentFeedback.bewertung === "richtig"
                ? "#86efac" : currentFeedback.bewertung === "teilweise"
                ? "#fcd34d" : "#fca5a5",
            }}>
              {currentFeedback.bewertung}
            </span>
          </div>
          <p className="text-sm text-slate-300">{currentFeedback.feedback}</p>
        </motion.div>
      )}

      {/* Ergebnis */}
      {state === "finished" && result && (
        <ExamResults result={result} verlauf={verlauf} onRestart={() => {
          setState("idle");
          setResult(null);
          setVerlauf([]);
          setFrageNr(0);
          setCurrentFeedback(null);
        }} />
      )}

      {/* Verlauf */}
      {verlauf.length > 0 && state !== "finished" && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500 font-medium">Bisheriger Verlauf:</p>
          {verlauf.map((v, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-slate-400">
              <span className={
                v.score >= 7 ? "text-green-400" : v.score >= 4 ? "text-yellow-400" : "text-red-400"
              }>
                {v.score}/10
              </span>
              <span className="truncate">{v.frage}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Ergebnis-Komponente
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function ExamResults({
  result,
  verlauf,
  onRestart,
}: {
  result: ExamResult;
  verlauf: VerlaufItem[];
  onRestart: () => void;
}) {
  const noteColors: Record<number, string> = {
    1: "#22c55e", 2: "#86efac", 3: "#fcd34d",
    4: "#f59e0b", 5: "#f87171", 6: "#ef4444",
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="space-y-4"
    >
      {/* Note */}
      <div className="text-center p-6 rounded-2xl" style={{
        background: "rgba(30,41,59,0.6)",
        border: "1px solid rgba(99,102,241,0.2)",
      }}>
        <div className="text-6xl font-black mb-2" style={{ color: noteColors[result.note] || "#fff" }}>
          {result.note}
        </div>
        <p className="text-slate-400 text-sm">
          {result.avg_score}/10 Punkte Durchschnitt
        </p>
        <p className="text-white font-medium mt-2">{result.feedback}</p>
      </div>

      {/* Stärken / Schwächen */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-xl" style={{
          background: "rgba(34,197,94,0.08)",
          border: "1px solid rgba(34,197,94,0.2)",
        }}>
          <p className="text-xs text-green-400 font-bold mb-1">Stärken</p>
          {result.stärken.length > 0 ? result.stärken.map((s, i) => (
            <p key={i} className="text-xs text-slate-300 truncate">{s}</p>
          )) : <p className="text-xs text-slate-500">—</p>}
        </div>
        <div className="p-3 rounded-xl" style={{
          background: "rgba(239,68,68,0.08)",
          border: "1px solid rgba(239,68,68,0.2)",
        }}>
          <p className="text-xs text-red-400 font-bold mb-1">Schwächen</p>
          {result.schwächen.length > 0 ? result.schwächen.map((s, i) => (
            <p key={i} className="text-xs text-slate-300 truncate">{s}</p>
          )) : <p className="text-xs text-slate-500">—</p>}
        </div>
      </div>

      {/* Karteikarten Info */}
      {result.karteikarten_erstellt > 0 && (
        <div className="p-3 rounded-xl text-center" style={{
          background: "rgba(99,102,241,0.08)",
          border: "1px solid rgba(99,102,241,0.2)",
        }}>
          <p className="text-sm text-indigo-300">
            {result.karteikarten_erstellt} Karteikarten aus deinen Fehlern erstellt
          </p>
        </div>
      )}

      {/* Detaillierter Verlauf */}
      <div className="space-y-2">
        <p className="text-xs text-slate-500 font-medium">Detaillierter Verlauf:</p>
        {verlauf.map((v, i) => (
          <div key={i} className="p-3 rounded-xl text-sm" style={{
            background: "rgba(30,41,59,0.4)",
            border: "1px solid rgba(99,102,241,0.1)",
          }}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-indigo-400 text-xs font-medium">Frage {i + 1}</span>
              <span className={`text-xs font-bold ${
                v.score >= 7 ? "text-green-400" : v.score >= 4 ? "text-yellow-400" : "text-red-400"
              }`}>
                {v.score}/10
              </span>
            </div>
            <p className="text-slate-300 text-xs mb-1">{v.frage}</p>
            <p className="text-slate-500 text-xs">Deine Antwort: {v.antwort}</p>
          </div>
        ))}
      </div>

      {/* Nochmal Button */}
      <button
        onClick={onRestart}
        className="w-full py-3 rounded-xl font-bold text-white transition-all hover:scale-[1.02]"
        style={{
          background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
          boxShadow: "0 0 20px rgba(99,102,241,0.4)",
        }}
      >
        Neue Prüfung starten
      </button>
    </motion.div>
  );
}
