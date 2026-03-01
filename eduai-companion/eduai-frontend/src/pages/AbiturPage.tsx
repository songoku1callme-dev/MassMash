import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { abiturApi, type AbiturSimulation, type AbiturResult, type AbiturHistoryItem, type StudyPlanListItem } from "../services/api";
import {
  GraduationCap, Play, Pause, Send, Clock, Trophy, Calendar,
  Loader2, Lock, CheckCircle2, XCircle, BarChart3,
  Calculator, Languages, BookOpenCheck, FlaskConical, Atom, Leaf
} from "lucide-react";

const SUBJECTS = [
  { id: "math", name: "Mathe", icon: <Calculator className="w-5 h-5" /> },
  { id: "german", name: "Deutsch", icon: <BookOpenCheck className="w-5 h-5" /> },
  { id: "english", name: "Englisch", icon: <Languages className="w-5 h-5" /> },
  { id: "physics", name: "Physik", icon: <Atom className="w-5 h-5" /> },
  { id: "chemistry", name: "Chemie", icon: <FlaskConical className="w-5 h-5" /> },
  { id: "biology", name: "Biologie", icon: <Leaf className="w-5 h-5" /> },
];

type AbiturState = "setup" | "exam" | "results";

export default function AbiturPage() {
  const [state, setState] = useState<AbiturState>("setup");
  const [subject, setSubject] = useState("math");
  const [duration, setDuration] = useState(180);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [simulation, setSimulation] = useState<AbiturSimulation | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [currentQ, setCurrentQ] = useState(0);
  const [result, setResult] = useState<AbiturResult | null>(null);
  const [history, setHistory] = useState<AbiturHistoryItem[]>([]);
  const [plans, setPlans] = useState<StudyPlanListItem[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadHistory();
    loadPlans();
  }, []);

  useEffect(() => {
    if (state === "exam" && !isPaused) {
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [state, isPaused]);

  const loadHistory = async () => {
    try {
      const data = await abiturApi.history();
      setHistory(data.simulations);
    } catch {
      // Ignore - user might not be Max tier
    }
  };

  const loadPlans = async () => {
    try {
      const data = await abiturApi.getPlans();
      setPlans(data.plans);
    } catch {
      // Ignore
    }
  };

  const startExam = async () => {
    setLoading(true);
    setError("");
    try {
      const sim = await abiturApi.start({ subject, duration_minutes: duration, num_questions: 20 });
      setSimulation(sim);
      setAnswers({});
      setCurrentQ(0);
      setElapsedSeconds(0);
      setIsPaused(false);
      setState("exam");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Fehler beim Starten";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const togglePause = async () => {
    if (!simulation) return;
    try {
      if (isPaused) {
        await abiturApi.resume(simulation.simulation_id);
        setIsPaused(false);
      } else {
        await abiturApi.pause({ simulation_id: simulation.simulation_id, elapsed_seconds: elapsedSeconds });
        setIsPaused(true);
      }
    } catch (err: unknown) {
      console.error("Pause/Resume error:", err);
    }
  };

  const submitExam = async () => {
    if (!simulation) return;
    setLoading(true);
    try {
      const answersList = simulation.questions.map((q) => ({
        question_id: q.id,
        user_answer: answers[q.id] || "",
      }));
      const res = await abiturApi.submit({ simulation_id: simulation.simulation_id, answers: answersList });
      setResult(res);
      setState("results");
      loadHistory();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Fehler beim Absenden";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const createPlan = async () => {
    setLoading(true);
    setError("");
    try {
      await abiturApi.createPlan({ subject, weeks: 8 });
      loadPlans();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Fehler beim Erstellen";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  const remainingSeconds = duration * 60 - elapsedSeconds;
  const progressPercent = Math.min(100, (elapsedSeconds / (duration * 60)) * 100);

  // Setup screen
  if (state === "setup") {
    return (
      <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <GraduationCap className="w-7 h-7 text-purple-600" />
            Abitur-Simulation
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Echte Pr&uuml;fungsbedingungen mit Timer und Notenpunkten (Max)
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 flex items-center gap-2">
            <Lock className="w-5 h-5" />
            {error}
          </div>
        )}

        {/* Subject Selection */}
        <Card>
          <CardHeader><CardTitle className="text-base">Fach w&auml;hlen</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {SUBJECTS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSubject(s.id)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    subject === s.id
                      ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                      : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                  }`}
                >
                  {s.icon}
                  <span className="text-sm font-medium">{s.name}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Duration Selection */}
        <Card>
          <CardHeader><CardTitle className="text-base">Pr&uuml;fungsdauer</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {[180, 210, 240].map((d) => (
                <button
                  key={d}
                  onClick={() => setDuration(d)}
                  className={`p-4 rounded-xl border-2 text-center transition-all ${
                    duration === d
                      ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                      : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                  }`}
                >
                  <p className="font-bold text-lg">{d} min</p>
                  <p className="text-xs text-gray-500">{d / 60} Stunden</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-3">
          <Button onClick={startExam} size="lg" className="flex-1 gap-2 bg-purple-600 hover:bg-purple-700" disabled={loading}>
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
            Pr&uuml;fung starten
          </Button>
          <Button onClick={createPlan} variant="outline" size="lg" className="flex-1 gap-2" disabled={loading}>
            <Calendar className="w-5 h-5" />
            Wochen-Coach Plan
          </Button>
        </div>

        {/* Plans */}
        {plans.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-base flex items-center gap-2"><BarChart3 className="w-5 h-5" /> Lernpl&auml;ne</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2">
                {plans.map((p) => (
                  <div key={p.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                    <div>
                      <p className="text-sm font-medium">{p.subject} - {p.week_count} Wochen</p>
                      <p className="text-xs text-gray-500">Woche {p.current_week} / {p.week_count} - {p.status}</p>
                    </div>
                    <Badge variant={p.status === "completed" ? "success" : "secondary"}>
                      {p.status === "completed" ? "Fertig" : `Woche ${p.current_week}`}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* History */}
        {history.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-base flex items-center gap-2"><Trophy className="w-5 h-5" /> Pr&uuml;fungshistorie</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2">
                {history.slice(0, 5).map((h) => (
                  <div key={h.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                    <div>
                      <p className="text-sm font-medium">{h.subject} ({h.duration_minutes}min)</p>
                      <p className="text-xs text-gray-500">{new Date(h.created_at).toLocaleDateString("de-DE")}</p>
                    </div>
                    <div className="text-right">
                      <Badge variant={h.note_punkte >= 10 ? "success" : h.note_punkte >= 5 ? "warning" : "destructive"}>
                        {h.note_punkte} Punkte
                      </Badge>
                      <p className="text-xs text-gray-500 mt-1">{h.note}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  // Exam screen
  if (state === "exam" && simulation) {
    const question = simulation.questions[currentQ];
    return (
      <div className="p-4 lg:p-6 max-w-2xl mx-auto space-y-6">
        {/* Timer Bar */}
        <div className="flex items-center justify-between">
          <Badge variant="secondary" className="text-sm">
            Frage {currentQ + 1} von {simulation.questions.length}
          </Badge>
          <div className="flex items-center gap-2">
            <Clock className={`w-4 h-4 ${remainingSeconds < 300 ? "text-red-500" : "text-purple-500"}`} />
            <span className={`font-mono text-lg font-bold ${remainingSeconds < 300 ? "text-red-500" : ""}`}>
              {formatTime(Math.max(0, remainingSeconds))}
            </span>
            <Button size="sm" variant="outline" onClick={togglePause}>
              {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${remainingSeconds < 300 ? "bg-red-500" : "bg-purple-600"}`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {isPaused && (
          <div className="p-4 rounded-xl bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 text-center">
            <Pause className="w-8 h-8 text-yellow-600 mx-auto mb-2" />
            <p className="font-medium text-yellow-800 dark:text-yellow-300">Pr&uuml;fung pausiert</p>
            <Button onClick={togglePause} className="mt-2" size="sm"><Play className="w-4 h-4 mr-1" /> Fortsetzen</Button>
          </div>
        )}

        {!isPaused && question && (
          <Card className="shadow-lg">
            <CardContent className="p-6">
              <p className="text-lg font-medium text-gray-900 dark:text-white mb-6">{question.question}</p>
              {question.options && question.options.length > 0 ? (
                <div className="space-y-3">
                  {question.options.map((opt, idx) => (
                    <button
                      key={idx}
                      onClick={() => setAnswers({ ...answers, [question.id]: opt })}
                      className={`w-full text-left p-4 rounded-xl border-2 transition-all flex items-center gap-3 ${
                        answers[question.id] === opt
                          ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                          : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                      }`}
                    >
                      <span className="w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm font-medium shrink-0">
                        {String.fromCharCode(65 + idx)}
                      </span>
                      <span>{opt}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <input
                  type="text"
                  value={answers[question.id] || ""}
                  onChange={(e) => setAnswers({ ...answers, [question.id]: e.target.value })}
                  placeholder="Deine Antwort..."
                  className="w-full p-3 rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-transparent"
                />
              )}
            </CardContent>
          </Card>
        )}

        <div className="flex gap-3">
          {currentQ > 0 && (
            <Button variant="outline" onClick={() => setCurrentQ(currentQ - 1)}>Zur&uuml;ck</Button>
          )}
          {currentQ < simulation.questions.length - 1 ? (
            <Button className="flex-1" onClick={() => setCurrentQ(currentQ + 1)}>
              N&auml;chste Frage
            </Button>
          ) : (
            <Button className="flex-1 bg-purple-600 hover:bg-purple-700 gap-2" onClick={submitExam} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Pr&uuml;fung abgeben
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Results screen
  if (state === "results" && result) {
    const scoreColor = result.note_punkte >= 10 ? "text-emerald-600" : result.note_punkte >= 5 ? "text-amber-600" : "text-red-600";
    return (
      <div className="p-4 lg:p-6 max-w-2xl mx-auto space-y-6">
        <Card className="shadow-xl text-center">
          <CardContent className="p-8">
            <div className="w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center text-white shadow-lg mb-6">
              <Trophy className="w-12 h-12" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Pr&uuml;fung abgeschlossen!</h2>
            <p className={`text-5xl font-bold ${scoreColor} mb-2`}>{result.note_punkte}/15</p>
            <p className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">{result.note}</p>
            <p className="text-gray-500">
              {result.correct_answers} von {result.total_questions} richtig ({result.score_percent}%)
            </p>

            {/* Graded answers */}
            <div className="mt-6 text-left space-y-2 max-h-60 overflow-y-auto">
              {result.graded_answers.map((ga, idx) => (
                <div key={idx} className={`flex items-center gap-2 p-2 rounded-lg text-sm ${
                  ga.is_correct ? "bg-emerald-50 dark:bg-emerald-900/20" : "bg-red-50 dark:bg-red-900/20"
                }`}>
                  {ga.is_correct ? <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" /> : <XCircle className="w-4 h-4 text-red-500 shrink-0" />}
                  <span className="truncate">Frage {idx + 1}: {ga.user_answer || "(leer)"}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-3">
          <Button onClick={startExam} className="flex-1 bg-purple-600 hover:bg-purple-700 gap-2" disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GraduationCap className="w-4 h-4" />}
            Nochmal
          </Button>
          <Button onClick={() => { setState("setup"); setSimulation(null); setResult(null); }} variant="outline" className="flex-1">
            Zur&uuml;ck
          </Button>
        </div>
      </div>
    );
  }

  return null;
}
