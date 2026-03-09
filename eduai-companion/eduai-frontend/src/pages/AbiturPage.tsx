import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { abiturApi, type AbiturSimulation, type AbiturResult, type AbiturHistoryItem, type StudyPlanListItem } from "../services/api";
import { Input } from "@/components/ui/input";
import {
 GraduationCap, Play, Pause, Send, Clock, Trophy, Calendar,
 Loader2, Lock, CheckCircle2, XCircle, BarChart3,
 Calculator, Languages, BookOpenCheck, FlaskConical, Atom, Leaf, Lightbulb, MessageCircle
} from "lucide-react";
import ErklaerButton from "../components/ui/ErklaerButton";
import { PageLoader, ErrorState } from "../components/PageStates";

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
 const [customTopic, setCustomTopic] = useState("");
 const [duration, setDuration] = useState(180);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState("");
 const [initLoading, setInitLoading] = useState(true);
 const [simulation, setSimulation] = useState<AbiturSimulation | null>(null);
 const [answers, setAnswers] = useState<Record<number, string>>({});
 const [currentQ, setCurrentQ] = useState(0);
 const [result, setResult] = useState<AbiturResult | null>(null);
 const [history, setHistory] = useState<AbiturHistoryItem[]>([]);
 const [plans, setPlans] = useState<StudyPlanListItem[]>([]);
 const [isPaused, setIsPaused] = useState(false);
 const [elapsedSeconds, setElapsedSeconds] = useState(0);
 const [proTipp, setProTipp] = useState<string | null>(null);
 const [tippLoading, setTippLoading] = useState(false);
 const lastAnswerTimeRef = useRef<number>(Date.now());
 const tippTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
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
 // Echtzeit-Prüfer: Proaktive Tipps wenn der Nutzer zu lange zögert
 tippTimerRef.current = setInterval(() => {
 const secondsSinceLastAnswer = (Date.now() - lastAnswerTimeRef.current) / 1000;
 if (secondsSinceLastAnswer >= 30 && !tippLoading && !proTipp && simulation) {
 generateProTipp();
 }
 }, 5000);
 }
 return () => {
 if (timerRef.current) clearInterval(timerRef.current);
 if (tippTimerRef.current) clearInterval(tippTimerRef.current);
 };
 }, [state, isPaused, simulation, tippLoading, proTipp]);

 // Reset Tipp-Timer wenn Antwort geändert wird
 useEffect(() => {
 lastAnswerTimeRef.current = Date.now();
 setProTipp(null);
 }, [currentQ, answers]);

 const generateProTipp = async () => {
 if (!simulation || tippLoading) return;
 const question = simulation.questions[currentQ];
 if (!question) return;
 setTippLoading(true);
 try {
 // Verwende den Erklärungs-Endpunkt für einen kontextbezogenen Tipp
 const subjectName = SUBJECTS.find(s => s.id === subject)?.name || "Allgemein";
 const response = await fetch(
 `${import.meta.env.VITE_API_URL || ""}/api/erklaerung/schnell`,
 {
 method: "POST",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({
 thema: question.question,
 fach: subjectName,
 kontext: "Gib einen kurzen, hilfreichen Tipp f\u00fcr diese Abitur-Aufgabe. Kein L\u00f6sungsweg, nur ein Denkansatz in 1-2 S\u00e4tzen."
 }),
 }
 );
 if (response.ok) {
 const data = await response.json();
 setProTipp(data.erklaerung || "Lies die Frage nochmal genau durch und überlege, welche Konzepte hier relevant sind.");
 } else {
 setProTipp("Lies die Frage nochmal genau durch und überlege, welche Konzepte hier relevant sind.");
 }
 } catch {
 setProTipp("Lies die Frage nochmal genau durch und überlege, welche Konzepte hier relevant sind.");
 } finally {
 setTippLoading(false);
 }
 };

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
 } finally {
 setInitLoading(false);
 }
 };

 const startExam = async () => {
 setLoading(true);
 setError("");
 try {
 const sim = await abiturApi.start({ subject, duration_minutes: duration, num_questions: 20, thema_custom: customTopic.trim() || undefined });
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

 if (initLoading) return <PageLoader text="Abitur-Simulation lädt..." />;

 // Setup screen
 if (state === "setup") {
 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <GraduationCap className="w-7 h-7 text-purple-600" />
 Abitur-Simulation
 </h1>
 <p className="theme-text-secondary mt-1">
 Echte Prüfungsbedingungen mit Timer und Notenpunkten (Max)
 </p>
 </div>

 {error && (
 <div className="p-4 rounded-lg bg-red-500/10 text-red-500 flex items-center gap-2">
 <Lock className="w-5 h-5" />
 {error}
 </div>
 )}

 {/* Subject Selection */}
 <Card>
 <CardHeader><CardTitle className="text-base">Fach wählen</CardTitle></CardHeader>
 <CardContent>
 <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
 {SUBJECTS.map((s) => (
 <button
 key={s.id}
 onClick={() => setSubject(s.id)}
 className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
 subject === s.id
 ? "border-purple-500 bg-purple-500/10"
 : "border-[var(--border-color)] hover:border-gray-300"
 }`}
 >
 {s.icon}
 <span className="text-sm font-medium">{s.name}</span>
 </button>
 ))}
 </div>
 </CardContent>
 </Card>

 {/* Free Topic Input */}
 <Card>
 <CardHeader><CardTitle className="text-base">Thema (optional)</CardTitle></CardHeader>
 <CardContent>
 <div className="space-y-2">
 <Input value={customTopic} onChange={(e) => setCustomTopic(e.target.value)}
 placeholder="z.B. Analysis, Expressionismus, Genetik..." className="p-3" />
 <p className="text-xs text-gray-500 flex items-center gap-1"><Lightbulb className="w-3 h-3" /> Gib ein Thema ein für gezielte Abitur-Aufgaben. Tavily sucht echte Prüfungsaufgaben 2024-2026.</p>
 </div>
 </CardContent>
 </Card>

 {/* Duration Selection */}
 <Card>
 <CardHeader><CardTitle className="text-base">Prüfungsdauer</CardTitle></CardHeader>
 <CardContent>
 <div className="grid grid-cols-3 gap-3">
 {[180, 210, 240].map((d) => (
 <button
 key={d}
 onClick={() => setDuration(d)}
 className={`p-4 rounded-xl border-2 text-center transition-all ${
 duration === d
 ? "border-purple-500 bg-purple-500/10"
 : "border-[var(--border-color)] hover:border-gray-300"
 }`}
 >
 <p className="font-bold text-lg">{d} min</p>
 <p className="text-xs theme-text-secondary">{d / 60} Stunden</p>
 </button>
 ))}
 </div>
 </CardContent>
 </Card>

 <div className="flex gap-3">
 <Button onClick={startExam} size="lg" className="flex-1 gap-2 bg-purple-600 hover:bg-purple-700" disabled={loading}>
 {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
 Prüfung starten
 </Button>
 <Button onClick={createPlan} variant="outline" size="lg" className="flex-1 gap-2" disabled={loading}>
 <Calendar className="w-5 h-5" />
 Wochen-Coach Plan
 </Button>
 </div>

 {/* Plans */}
 {plans.length > 0 && (
 <Card>
 <CardHeader><CardTitle className="text-base flex items-center gap-2"><BarChart3 className="w-5 h-5" /> Lernpläne</CardTitle></CardHeader>
 <CardContent>
 <div className="space-y-2">
 {plans.map((p) => (
 <div key={p.id} className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-surface)]">
 <div>
 <p className="text-sm font-medium">{p.subject} - {p.week_count} Wochen</p>
 <p className="text-xs theme-text-secondary">Woche {p.current_week} / {p.week_count} - {p.status}</p>
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
 <CardHeader><CardTitle className="text-base flex items-center gap-2"><Trophy className="w-5 h-5" /> Prüfungshistorie</CardTitle></CardHeader>
 <CardContent>
 <div className="space-y-2">
 {history.slice(0, 5).map((h) => (
 <div key={h.id} className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-surface)]">
 <div>
 <p className="text-sm font-medium">{h.subject} ({h.duration_minutes}min)</p>
 <p className="text-xs theme-text-secondary">{new Date(h.created_at).toLocaleDateString("de-DE")}</p>
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
 <div className="w-full bg-[var(--progress-bg)] rounded-full h-2">
 <div
 className={`h-2 rounded-full transition-all ${remainingSeconds < 300 ? "bg-red-500" : "bg-purple-600"}`}
 style={{ width: `${progressPercent}%` }}
 />
 </div>

 {isPaused && (
 <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-center">
 <Pause className="w-8 h-8 text-yellow-600 mx-auto mb-2" />
 <p className="font-medium text-yellow-800">Prüfung pausiert</p>
 <Button onClick={togglePause} className="mt-2" size="sm"><Play className="w-4 h-4 mr-1" /> Fortsetzen</Button>
 </div>
 )}

 {/* Echtzeit-Prüfer Tipp */}
 {(proTipp || tippLoading) && !isPaused && (
 <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
 <MessageCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
 <div>
 <p className="text-sm font-semibold text-amber-600 mb-1">Echtzeit-Prüfer — Tipp</p>
 {tippLoading ? (
 <div className="flex items-center gap-2 text-sm text-amber-500">
 <Loader2 className="w-4 h-4 animate-spin" />
 Generiere Tipp...
 </div>
 ) : (
 <p className="text-sm theme-text-secondary">{proTipp}</p>
 )}
 </div>
 </div>
 )}

 {!isPaused && question && (
 <Card className="shadow-lg">
 <CardContent className="p-6">
 <div className="flex items-start justify-between gap-3 mb-6">
 <p className="text-lg font-medium theme-text">{question.question}</p>
 <ErklaerButton
 thema={question.question}
 fach={SUBJECTS.find(s => s.id === subject)?.name || "Allgemein"}
 kontext="Abitur-Niveau"
 variant="inline"
 className="shrink-0 mt-1"
 />
 </div>
 {question.options && question.options.length > 0 ? (
 <div className="space-y-3">
 {question.options.map((opt, idx) => (
 <button
 key={idx}
 onClick={() => setAnswers({ ...answers, [question.id]: opt })}
 className={`w-full text-left p-4 rounded-xl border-2 transition-all flex items-center gap-3 ${
 answers[question.id] === opt
 ? "border-purple-500 bg-purple-500/10"
 : "border-[var(--border-color)] hover:border-gray-300"
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
 className="w-full p-3 rounded-xl border-2 border-[var(--border-color)] bg-transparent"
 />
 )}
 </CardContent>
 </Card>
 )}

 <div className="flex gap-3">
 {currentQ > 0 && (
 <Button variant="outline" onClick={() => setCurrentQ(currentQ - 1)}>Zurück</Button>
 )}
 {currentQ < simulation.questions.length - 1 ? (
 <Button className="flex-1" onClick={() => setCurrentQ(currentQ + 1)}>
 Nächste Frage
 </Button>
 ) : (
 <Button className="flex-1 bg-purple-600 hover:bg-purple-700 gap-2" onClick={submitExam} disabled={loading}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
 Prüfung abgeben
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
 <h2 className="text-2xl font-bold theme-text mb-2">Prüfung abgeschlossen!</h2>
 <p className={`text-5xl font-bold ${scoreColor} mb-2`}>{result.note_punkte}/15</p>
 <p className="text-lg font-medium theme-text-secondary mb-2">{result.note}</p>
 <p className="theme-text-secondary">
 {result.correct_answers} von {result.total_questions} richtig ({result.score_percent}%)
 </p>

 {/* Graded answers */}
 <div className="mt-6 text-left space-y-2 max-h-60 overflow-y-auto">
 {result.graded_answers.map((ga, idx) => (
 <div key={idx} className={`flex items-center gap-2 p-2 rounded-lg text-sm ${
 ga.is_correct ? "bg-emerald-500/10" : "bg-red-500/10"
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
 Zurück
 </Button>
 </div>
 </div>
 );
 }

 return null;
}
