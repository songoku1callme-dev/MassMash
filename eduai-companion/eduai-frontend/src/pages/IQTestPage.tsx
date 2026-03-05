import { useState, useEffect, useCallback, useRef } from "react";
import { iqApi, IQTestQuestion, IQTestResult } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
 Brain, Clock, ChevronRight, Trophy, BarChart3, Target,
 Loader2, AlertCircle, CheckCircle2, Lightbulb, Puzzle,
 Calculator, BookOpen, Box, MemoryStick
} from "lucide-react";

type Step = "intro" | "test" | "results";

const KATEGORIE_LABELS: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
 logik: { label: "Logik", icon: <Puzzle className="w-5 h-5" />, color: "text-blue-500" },
 verbal: { label: "Verbal", icon: <BookOpen className="w-5 h-5" />, color: "text-green-500" },
 mathe: { label: "Mathe", icon: <Calculator className="w-5 h-5" />, color: "text-orange-500" },
 raum: { label: "Räumlich", icon: <Box className="w-5 h-5" />, color: "text-purple-500" },
 gedaechtnis: { label: "Gedächtnis", icon: <MemoryStick className="w-5 h-5" />, color: "text-pink-500" },
};

export default function IQTestPage() {
 const [step, setStep] = useState<Step>("intro");
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState("");

 // Test state
 const [testId, setTestId] = useState<number | null>(null);
 const [questions, setQuestions] = useState<IQTestQuestion[]>([]);
 const [currentIndex, setCurrentIndex] = useState(0);
 const [answers, setAnswers] = useState<Map<number, { answer: number; time_seconds: number }>>(new Map());
 const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
 const [questionStartTime, setQuestionStartTime] = useState(Date.now());

 // Timer state
 const [timeRemaining, setTimeRemaining] = useState(2700); // 45 minutes
 const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

 // Results state
 const [result, setResult] = useState<IQTestResult | null>(null);

 // Cooldown state
 const [canTakeTest, setCanTakeTest] = useState(true);
 const [daysRemaining, setDaysRemaining] = useState(0);
 const [previousResult, setPreviousResult] = useState<IQTestResult | null>(null);

 // Check cooldown + previous result on mount
 useEffect(() => {
 const checkStatus = async () => {
 try {
 const [cooldown, prevResult] = await Promise.all([
 iqApi.cooldown(),
 iqApi.result(),
 ]);
 setCanTakeTest(cooldown.can_take_test);
 setDaysRemaining(cooldown.days_remaining);
 if (prevResult.has_result) {
 setPreviousResult(prevResult);
 }
 } catch {
 // No previous result
 }
 };
 checkStatus();
 }, []);

 // Timer countdown
 useEffect(() => {
 if (step === "test" && timeRemaining > 0) {
 timerRef.current = setInterval(() => {
 setTimeRemaining((prev) => {
 if (prev <= 1) {
 // Time's up — auto-submit
 handleSubmitTest();
 return 0;
 }
 return prev - 1;
 });
 }, 1000);
 }
 return () => {
 if (timerRef.current) clearInterval(timerRef.current);
 };
 }, [step]);

 const formatTime = (seconds: number) => {
 const m = Math.floor(seconds / 60);
 const s = seconds % 60;
 return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
 };

 const startTest = async () => {
 setLoading(true);
 setError("");
 try {
 const data = await iqApi.generate();
 setTestId(data.test_id);
 setQuestions(data.questions);
 setTimeRemaining(data.time_limit_seconds);
 setCurrentIndex(0);
 setAnswers(new Map());
 setQuestionStartTime(Date.now());
 setStep("test");
 } catch (err) {
 setError(err instanceof Error ? err.message : "Fehler beim Generieren des Tests");
 } finally {
 setLoading(false);
 }
 };

 const selectAnswer = (optionIndex: number) => {
 setSelectedAnswer(optionIndex);
 };

 const confirmAnswer = useCallback(() => {
 if (selectedAnswer === null || !questions[currentIndex]) return;

 const timeTaken = (Date.now() - questionStartTime) / 1000;
 const newAnswers = new Map(answers);
 newAnswers.set(questions[currentIndex].id, {
 answer: selectedAnswer,
 time_seconds: timeTaken,
 });
 setAnswers(newAnswers);
 setSelectedAnswer(null);

 if (currentIndex < questions.length - 1) {
 setCurrentIndex(currentIndex + 1);
 setQuestionStartTime(Date.now());
 } else {
 // Last question — submit
 submitTest(newAnswers);
 }
 }, [selectedAnswer, currentIndex, questions, answers, questionStartTime]);

 const submitTest = async (finalAnswers: Map<number, { answer: number; time_seconds: number }>) => {
 if (!testId) return;
 if (timerRef.current) clearInterval(timerRef.current);

 setLoading(true);
 try {
 const answersArray = Array.from(finalAnswers.entries()).map(([questionId, data]) => ({
 question_id: questionId,
 answer: data.answer,
 time_seconds: data.time_seconds,
 }));

 const res = await iqApi.submit({ test_id: testId, answers: answersArray });
 setResult(res);
 setStep("results");
 } catch (err) {
 setError(err instanceof Error ? err.message : "Fehler beim Berechnen");
 } finally {
 setLoading(false);
 }
 };

 const handleSubmitTest = () => {
 submitTest(answers);
 };

 const currentQuestion = questions[currentIndex];
 const progress = questions.length > 0 ? ((currentIndex + (selectedAnswer !== null ? 0 : 0)) / questions.length) * 100 : 0;
 const answeredCount = answers.size;

 // ---- INTRO ----
 if (step === "intro") {
 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
 <div className="text-center space-y-3">
 <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
 <Brain className="w-8 h-8 text-white" />
 </div>
 <h1 className="text-3xl font-bold theme-text">IQ-Test</h1>
 <p className="theme-text-secondary text-lg max-w-2xl mx-auto">
 Wissenschaftlich inspirierter Intelligenztest mit 40 Fragen in 5 Kategorien.
 Dein IQ wird anhand der Normalverteilung (Durchschnitt 100, Standardabweichung 15) berechnet.
 </p>
 </div>

 {/* Categories */}
 <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
 {Object.entries(KATEGORIE_LABELS).map(([key, { label, icon, color }]) => (
 <Card key={key} className="text-center">
 <CardContent className="pt-4 pb-3">
 <div className={`${color} flex justify-center mb-2`}>{icon}</div>
 <p className="font-medium text-sm theme-text">{label}</p>
 <p className="text-xs theme-text-secondary">8 Fragen</p>
 </CardContent>
 </Card>
 ))}
 </div>

 {/* Info Cards */}
 <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
 <Card>
 <CardContent className="pt-4 flex items-start gap-3">
 <Clock className="w-5 h-5 text-blue-500 mt-0.5" />
 <div>
 <p className="font-medium theme-text text-sm">45 Minuten</p>
 <p className="text-xs theme-text-secondary">Zeitlimit für alle Fragen</p>
 </div>
 </CardContent>
 </Card>
 <Card>
 <CardContent className="pt-4 flex items-start gap-3">
 <Target className="w-5 h-5 text-green-500 mt-0.5" />
 <div>
 <p className="font-medium theme-text text-sm">40 Fragen</p>
 <p className="text-xs theme-text-secondary">8 pro Kategorie, kein Zurück</p>
 </div>
 </CardContent>
 </Card>
 <Card>
 <CardContent className="pt-4 flex items-start gap-3">
 <BarChart3 className="w-5 h-5 text-purple-500 mt-0.5" />
 <div>
 <p className="font-medium theme-text text-sm">IQ-Auswertung</p>
 <p className="text-xs theme-text-secondary">Normalverteilung + Kategorien</p>
 </div>
 </CardContent>
 </Card>
 </div>

 {/* Previous Result */}
 {previousResult && (
 <Card className="border-indigo-200 bg-indigo-50/50">
 <CardContent className="pt-4">
 <div className="flex items-center justify-between">
 <div>
 <p className="font-medium text-indigo-900">Dein letztes Ergebnis</p>
 <p className="text-sm text-indigo-600">
 IQ: {previousResult.iq} ({previousResult.klassifikation})
 </p>
 </div>
 <div className="text-3xl font-bold text-indigo-600">
 {previousResult.iq}
 </div>
 </div>
 </CardContent>
 </Card>
 )}

 {error && (
 <div className="p-4 rounded-lg bg-red-50 text-red-600 flex items-center gap-2">
 <AlertCircle className="w-5 h-5 flex-shrink-0" />
 {error}
 </div>
 )}

 <div className="text-center">
 {canTakeTest ? (
 <Button
 size="lg"
 onClick={startTest}
 disabled={loading}
 className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-lg px-8"
 >
 {loading ? (
 <>
 <Loader2 className="w-5 h-5 mr-2 animate-spin" />
 Test wird generiert...
 </>
 ) : (
 <>
 <Brain className="w-5 h-5 mr-2" />
 Test starten
 </>
 )}
 </Button>
 ) : (
 <div className="space-y-2">
 <Button size="lg" disabled className="text-lg px-8">
 <Clock className="w-5 h-5 mr-2" />
 Noch {daysRemaining} Tage Wartezeit
 </Button>
 <p className="text-sm theme-text-secondary">
 Der IQ-Test kann nur alle 30 Tage wiederholt werden.
 </p>
 </div>
 )}
 </div>

 <p className="text-center text-xs text-gray-400">
 Hinweis: Dies ist ein Unterhaltungstest und ersetzt keinen klinisch validierten IQ-Test.
 Die Ergebnisse dienen der Selbsteinschätzung.
 </p>
 </div>
 );
 }

 // ---- TEST ----
 if (step === "test" && currentQuestion) {
 const katInfo = KATEGORIE_LABELS[currentQuestion.kategorie] || KATEGORIE_LABELS.logik;

 return (
 <div className="p-4 lg:p-6 max-w-3xl mx-auto space-y-4">
 {/* Header: Timer + Progress */}
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2">
 <div className={`${katInfo.color}`}>{katInfo.icon}</div>
 <span className="text-sm font-medium theme-text-secondary">{katInfo.label}</span>
 </div>
 <div className={`flex items-center gap-2 font-mono text-lg font-bold ${timeRemaining < 300 ? "text-red-500" : "theme-text"}`}>
 <Clock className="w-5 h-5" />
 {formatTime(timeRemaining)}
 </div>
 </div>

 {/* Progress bar */}
 <div className="space-y-1">
 <div className="flex justify-between text-xs theme-text-secondary">
 <span>Frage {currentIndex + 1} von {questions.length}</span>
 <span>{answeredCount} beantwortet</span>
 </div>
 <div className="w-full h-2 bg-[var(--progress-bg)] rounded-full overflow-hidden">
 <div
 className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-300"
 style={{ width: `${progress}%` }}
 />
 </div>
 </div>

 {/* Question Card */}
 <Card className="border-2 border-indigo-100">
 <CardHeader>
 <CardDescription className="text-xs uppercase tracking-wider">
 {katInfo.label} - Schwierigkeit: {"★".repeat(Math.round(currentQuestion.schwierigkeit * 5))}{"☆".repeat(5 - Math.round(currentQuestion.schwierigkeit * 5))}
 </CardDescription>
 <CardTitle className="text-lg leading-relaxed">
 {currentQuestion.frage}
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-3">
 {currentQuestion.optionen.map((option, index) => (
 <button
 key={index}
 onClick={() => selectAnswer(index)}
 className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
 selectedAnswer === index
 ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-200"
 : "border-[var(--border-color)] hover:border-gray-300 hover:bg-gray-50"
 }`}
 >
 <div className="flex items-center gap-3">
 <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
 selectedAnswer === index
 ? "bg-indigo-500 text-white"
 : "bg-[var(--bg-surface)] theme-text-secondary"
 }`}>
 {String.fromCharCode(65 + index)}
 </span>
 <span className={`text-sm ${
 selectedAnswer === index
 ? "text-indigo-900 font-medium"
 : "theme-text-secondary"
 }`}>
 {option}
 </span>
 </div>
 </button>
 ))}
 </CardContent>
 </Card>

 {/* Confirm Button */}
 <div className="flex justify-between items-center">
 <p className="text-xs theme-text-secondary">
 Kein Zurück möglich
 </p>
 <Button
 onClick={confirmAnswer}
 disabled={selectedAnswer === null || loading}
 className="bg-indigo-600 hover:bg-indigo-700"
 >
 {currentIndex === questions.length - 1 ? "Abgeben" : "Weiter"}
 <ChevronRight className="w-4 h-4 ml-1" />
 </Button>
 </div>

 {loading && (
 <div className="flex items-center justify-center gap-2 text-indigo-600">
 <Loader2 className="w-5 h-5 animate-spin" />
 <span className="text-sm">Wird ausgewertet...</span>
 </div>
 )}
 </div>
 );
 }

 // ---- RESULTS ----
 if (step === "results" && result) {
 const iqColor = result.iq >= 120 ? "text-emerald-500" : result.iq >= 100 ? "text-blue-500" : result.iq >= 85 ? "text-yellow-500" : "text-red-500";
 const iqBg = result.iq >= 120 ? "from-emerald-500 to-teal-600" : result.iq >= 100 ? "from-blue-500 to-indigo-600" : result.iq >= 85 ? "from-yellow-500 to-orange-600" : "from-red-500 to-pink-600";

 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
 {/* IQ Score Hero */}
 <div className="text-center space-y-4">
 <div className={`w-32 h-32 mx-auto rounded-full bg-gradient-to-br ${iqBg} flex items-center justify-center shadow-xl`}>
 <div className="text-center">
 <p className="text-4xl font-bold text-white">{result.iq}</p>
 <p className="text-xs text-white/80">IQ</p>
 </div>
 </div>
 <div>
 <h1 className="text-2xl font-bold theme-text">{result.klassifikation}</h1>
 <p className="theme-text-secondary mt-1">{result.vergleich}</p>
 <p className="text-sm theme-text-secondary mt-1">IQ-Bereich: {result.iq_range}</p>
 </div>
 </div>

 {/* Stats Grid */}
 <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
 <Card>
 <CardContent className="pt-4 text-center">
 <p className={`text-2xl font-bold ${iqColor}`}>{result.iq}</p>
 <p className="text-xs theme-text-secondary">IQ-Wert</p>
 </CardContent>
 </Card>
 <Card>
 <CardContent className="pt-4 text-center">
 <p className="text-2xl font-bold text-indigo-500">{result.percentile}%</p>
 <p className="text-xs theme-text-secondary">Perzentil</p>
 </CardContent>
 </Card>
 <Card>
 <CardContent className="pt-4 text-center">
 <p className="text-2xl font-bold text-emerald-500">{result.raw_score}</p>
 <p className="text-xs theme-text-secondary">Punkte</p>
 </CardContent>
 </Card>
 <Card>
 <CardContent className="pt-4 text-center">
 <p className="text-2xl font-bold text-gray-500">{result.max_score}</p>
 <p className="text-xs theme-text-secondary">Max. Punkte</p>
 </CardContent>
 </Card>
 </div>

 {/* Category Scores */}
 <Card>
 <CardHeader>
 <CardTitle className="text-lg flex items-center gap-2">
 <BarChart3 className="w-5 h-5 text-indigo-500" />
 Ergebnisse nach Kategorie
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-4">
 {Object.entries(result.kategorien).map(([kat, pct]) => {
 const info = KATEGORIE_LABELS[kat] || { label: kat, icon: null, color: "text-gray-500" };
 const barColor = pct >= 75 ? "bg-emerald-500" : pct >= 50 ? "bg-blue-500" : pct >= 25 ? "bg-yellow-500" : "bg-red-500";
 return (
 <div key={kat} className="space-y-1">
 <div className="flex items-center justify-between text-sm">
 <div className="flex items-center gap-2">
 <span className={info.color}>{info.icon}</span>
 <span className="font-medium theme-text">{info.label}</span>
 </div>
 <span className="font-bold theme-text">{pct}%</span>
 </div>
 <div className="w-full h-3 bg-[var(--progress-bg)] rounded-full overflow-hidden">
 <div className={`h-full ${barColor} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
 </div>
 </div>
 );
 })}
 </CardContent>
 </Card>

 {/* Strengths & Weaknesses */}
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {result.staerken.length > 0 && (
 <Card className="border-emerald-200">
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2 text-emerald-700">
 <CheckCircle2 className="w-5 h-5" />
 Stärken
 </CardTitle>
 </CardHeader>
 <CardContent>
 <ul className="space-y-2">
 {result.staerken.map((s) => (
 <li key={s} className="flex items-center gap-2 text-sm theme-text-secondary">
 <Trophy className="w-4 h-4 text-emerald-500" />
 {KATEGORIE_LABELS[s]?.label || s}
 </li>
 ))}
 </ul>
 </CardContent>
 </Card>
 )}
 {result.schwaechen.length > 0 && (
 <Card className="border-orange-200">
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2 text-orange-700">
 <Lightbulb className="w-5 h-5" />
 Verbesserungspotenzial
 </CardTitle>
 </CardHeader>
 <CardContent>
 <ul className="space-y-2">
 {result.schwaechen.map((s) => (
 <li key={s} className="flex items-center gap-2 text-sm theme-text-secondary">
 <Target className="w-4 h-4 text-orange-500" />
 {KATEGORIE_LABELS[s]?.label || s}
 </li>
 ))}
 </ul>
 </CardContent>
 </Card>
 )}
 </div>

 {/* Training Recommendations */}
 {result.training && result.training.length > 0 && (
 <Card className="border-indigo-200">
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2 text-indigo-700">
 <Target className="w-5 h-5" />
 Trainings-Empfehlungen
 </CardTitle>
 </CardHeader>
 <CardContent>
 <ul className="space-y-2">
 {result.training.map((t, i) => (
 <li key={i} className="flex items-start gap-2 text-sm theme-text-secondary">
 <ChevronRight className="w-4 h-4 text-indigo-500 mt-0.5 shrink-0" />
 {t}
 </li>
 ))}
 </ul>
 </CardContent>
 </Card>
 )}

 {/* IQ Classification Table */}
 {result.iq_table && result.iq_table.length > 0 && (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Brain className="w-5 h-5 text-indigo-500" />
 IQ-Einordnung
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="overflow-x-auto">
 <table className="w-full text-sm">
 <thead>
 <tr className="border-b border-[var(--border-color)]">
 <th className="text-left py-2 px-3 font-medium theme-text-secondary">IQ-Bereich</th>
 <th className="text-left py-2 px-3 font-medium theme-text-secondary">Klassifikation</th>
 <th className="text-left py-2 px-3 font-medium theme-text-secondary">Bevölkerung</th>
 </tr>
 </thead>
 <tbody>
 {result.iq_table.map((row, i) => {
 const isCurrentRange =
 (row.range === "130+" && result.iq >= 130) ||
 (row.range.includes("-") && (() => {
 const [lo, hi] = row.range.split("-").map(Number);
 return result.iq >= lo && result.iq <= hi;
 })());
 return (
 <tr
 key={i}
 className={`border-b border-[var(--border-color)] ${isCurrentRange ? "bg-indigo-50 font-medium" : ""}`}
 >
 <td className="py-2 px-3 theme-text">{row.range}</td>
 <td className="py-2 px-3 theme-text-secondary">{row.label}</td>
 <td className="py-2 px-3 theme-text-secondary">{row.percent}</td>
 </tr>
 );
 })}
 </tbody>
 </table>
 </div>
 </CardContent>
 </Card>
 )}

 {/* IQ Distribution Visual */}
 <Card>
 <CardHeader>
 <CardTitle className="text-base">IQ-Verteilung (Normalverteilung)</CardTitle>
 <CardDescription>Wo dein Ergebnis auf der Glockenkurve liegt</CardDescription>
 </CardHeader>
 <CardContent>
 <div className="relative h-24">
 {/* Bell curve approximation with gradient */}
 <div className="absolute inset-0 flex items-end">
 {Array.from({ length: 40 }, (_, i) => {
 const iq = 55 + (i / 39) * 90; // IQ range 55-145
 const z = (iq - 100) / 15;
 const height = Math.exp(-0.5 * z * z) * 100;
 const isUserRange = Math.abs(iq - result.iq) < 5;
 return (
 <div
 key={i}
 className={`flex-1 rounded-t-sm ${isUserRange ? "bg-indigo-500" : "bg-[var(--progress-bg)]"}`}
 style={{ height: `${height}%` }}
 />
 );
 })}
 </div>
 {/* User marker */}
 <div
 className="absolute top-0 flex flex-col items-center"
 style={{ left: `${((result.iq - 55) / 90) * 100}%`, transform: "translateX(-50%)" }}
 >
 <div className="text-xs font-bold text-indigo-600 theme-card px-1 rounded">
 Du: {result.iq}
 </div>
 </div>
 </div>
 <div className="flex justify-between text-xs theme-text-secondary mt-2">
 <span>55</span>
 <span>70</span>
 <span>85</span>
 <span>100</span>
 <span>115</span>
 <span>130</span>
 <span>145</span>
 </div>
 </CardContent>
 </Card>

 <div className="text-center">
 <Button
 onClick={() => {
 setStep("intro");
 setResult(null);
 setCanTakeTest(false);
 setDaysRemaining(30);
 setPreviousResult(result);
 }}
 variant="outline"
 >
 Zurück zur Übersicht
 </Button>
 </div>

 <p className="text-center text-xs text-gray-400">
 Nächster Test möglich in 30 Tagen. Dies ist ein Unterhaltungstest.
 </p>
 </div>
 );
 }

 // Fallback loading state
 return (
 <div className="p-6 flex items-center justify-center">
 <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
 </div>
 );
}
