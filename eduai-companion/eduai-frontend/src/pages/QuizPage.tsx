import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { quizApi, type QuizData, type QuizResult, type QuizHistoryItem, type AnswerCheckResult } from "../services/api";
import ConfidenceSlider from "../components/ConfidenceSlider";
import {
 BrainCircuit, CheckCircle2, XCircle, ArrowRight, RotateCcw, Trophy,
 Calculator, Languages, BookOpenCheck, Clock, FlaskConical, Loader2,
 Atom, Leaf, Globe, Landmark, Brain, Palette, Music, Users, Code, BookOpen,
 AlertTriangle, Lightbulb, Lock, Timer, Zap
} from "lucide-react";
import ErklaerButton from "../components/ui/ErklaerButton";

const SUBJECTS = [
 { id: "math", name: "Mathe", icon: <Calculator className="w-5 h-5" />, color: "from-blue-500 to-blue-600" },
 { id: "german", name: "Deutsch", icon: <BookOpenCheck className="w-5 h-5" />, color: "from-amber-500 to-amber-600" },
 { id: "english", name: "Englisch", icon: <Languages className="w-5 h-5" />, color: "from-emerald-500 to-emerald-600" },
 { id: "physics", name: "Physik", icon: <Atom className="w-5 h-5" />, color: "from-cyan-500 to-cyan-600" },
 { id: "chemistry", name: "Chemie", icon: <FlaskConical className="w-5 h-5" />, color: "from-rose-500 to-rose-600" },
 { id: "biology", name: "Biologie", icon: <Leaf className="w-5 h-5" />, color: "from-green-500 to-green-600" },
 { id: "history", name: "Geschichte", icon: <Clock className="w-5 h-5" />, color: "from-purple-500 to-purple-600" },
 { id: "geography", name: "Geografie", icon: <Globe className="w-5 h-5" />, color: "from-teal-500 to-teal-600" },
 { id: "economics", name: "Wirtschaft", icon: <Landmark className="w-5 h-5" />, color: "from-orange-500 to-orange-600" },
 { id: "ethics", name: "Ethik", icon: <Brain className="w-5 h-5" />, color: "from-indigo-500 to-indigo-600" },
 { id: "computer_science", name: "Informatik", icon: <Code className="w-5 h-5" />, color: "from-gray-500 to-gray-600" },
 { id: "art", name: "Kunst", icon: <Palette className="w-5 h-5" />, color: "from-pink-500 to-pink-600" },
 { id: "music", name: "Musik", icon: <Music className="w-5 h-5" />, color: "from-violet-500 to-violet-600" },
 { id: "social_studies", name: "Sozialkunde", icon: <Users className="w-5 h-5" />, color: "from-sky-500 to-sky-600" },
 { id: "latin", name: "Latein", icon: <BookOpen className="w-5 h-5" />, color: "from-stone-500 to-stone-600" },
 { id: "french", name: "Französisch", icon: <Languages className="w-5 h-5" />, color: "from-red-500 to-red-600" },
];

const DIFFICULTIES = [
 { id: "beginner", name: "Anfänger", desc: "Grundlagen" },
 { id: "intermediate", name: "Mittel", desc: "Fortgeschritten" },
 { id: "advanced", name: "Schwer", desc: "Experte" },
];

const QUIZ_TYPES = [
 { id: "mixed", name: "Gemischt", desc: "Alle Fragetypen" },
 { id: "mcq", name: "Multiple Choice", desc: "A/B/C/D" },
 { id: "true_false", name: "Wahr/Falsch", desc: "Richtig oder Falsch" },
 { id: "fill_blank", name: "Lückentext", desc: "Antwort eingeben" },
 { id: "free_text", name: "Freitext", desc: "Eigene Antwort" },
];

const QUESTION_COUNTS = [5, 10, 20, 50];

type QuizState = "setup" | "playing" | "results";

export default function QuizPage() {
 const [state, setState] = useState<QuizState>("setup");
 const [subject, setSubject] = useState("math");
 const [difficulty, setDifficulty] = useState("beginner");
 const [quizType, setQuizType] = useState("mixed");
 const [numQuestions, setNumQuestions] = useState(5);
 const [customTopic, setCustomTopic] = useState("");
 const [selectedPresetTopic, setSelectedPresetTopic] = useState("");
 const [quiz, setQuiz] = useState<QuizData | null>(null);
 const [currentQ, setCurrentQ] = useState(0);
 const [answers, setAnswers] = useState<Record<number, string>>({});
 const [showAnswer, setShowAnswer] = useState(false);
 const [answerResult, setAnswerResult] = useState<AnswerCheckResult | null>(null);
 const [result, setResult] = useState<QuizResult | null>(null);
 const [loading, setLoading] = useState(false);
 const [history, setHistory] = useState<QuizHistoryItem[]>([]);
 const [fillAnswer, setFillAnswer] = useState("");
 const [presetTopics, setPresetTopics] = useState<{ id: number; name: string; tier: string }[]>([]);
 const [confidenceGiven, setConfidenceGiven] = useState(false);
 const [timer, setTimer] = useState(30);
 const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

 // Timer: 30s countdown per question
 const startTimer = useCallback(() => {
 setTimer(30);
 if (timerRef.current) clearInterval(timerRef.current);
 timerRef.current = setInterval(() => {
 setTimer((prev) => {
 if (prev <= 1) {
 if (timerRef.current) clearInterval(timerRef.current);
 return 0;
 }
 return prev - 1;
 });
 }, 1000);
 }, []);

 const stopTimer = useCallback(() => {
 if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
 }, []);

 // Auto-submit when timer hits 0
 useEffect(() => {
 if (timer === 0 && state === "playing" && !showAnswer && quiz) {
 const q = quiz.questions[currentQ];
 selectAnswer(q.id, "__timeout__");
 }
 }, [timer, state, showAnswer]);

 // Start timer when question changes
 useEffect(() => {
 if (state === "playing" && !showAnswer) startTimer();
 return () => stopTimer();
 }, [currentQ, state, showAnswer, startTimer, stopTimer]);

 useEffect(() => { loadHistory(); }, []);
 useEffect(() => { loadTopics(); }, [subject]);

 const loadHistory = async () => {
 try { const data = await quizApi.history(); setHistory(data); } catch { /* ignore */ }
 };

 const loadTopics = async () => {
 try {
 const data = await quizApi.topics(subject);
 if (data.topics) setPresetTopics(data.topics);
 } catch { setPresetTopics([]); }
 };

 const startQuiz = async () => {
 setLoading(true);
 try {
 const data = await quizApi.generate({
 subject, difficulty, num_questions: numQuestions, quiz_type: quizType, language: "de",
 topic: selectedPresetTopic || undefined,
 thema_custom: customTopic.trim() || undefined,
 });
 setQuiz(data); setCurrentQ(0); setAnswers({}); setShowAnswer(false);
 setResult(null); setFillAnswer(""); setState("playing");
 } catch (err) { console.error("Failed to generate quiz:", err); }
 finally { setLoading(false); }
 };

 const selectAnswer = async (questionId: number, answer: string) => {
 if (showAnswer || !quiz) return;
 stopTimer();
 setAnswers({ ...answers, [questionId]: answer });
 setShowAnswer(true);
 // Check answer against server
 try {
 const checkResult = await quizApi.checkAnswer({
 quiz_id: quiz.quiz_id,
 question_id: questionId,
 user_answer: answer,
 });
 setAnswerResult(checkResult);
 } catch (err) {
 console.error("Failed to check answer:", err);
 setAnswerResult(null);
 }
 };

 const submitFillAnswer = () => {
 if (!quiz || !fillAnswer.trim()) return;
 const q = quiz.questions[currentQ];
 selectAnswer(q.id, fillAnswer.trim());
 setFillAnswer("");
 };

 const handleConfidence = async (level: 1 | 2 | 3 | 4 | 5) => {
 if (!quiz) return;
 setConfidenceGiven(true);
 const question = quiz.questions[currentQ];
 const warRichtig = answerResult?.correct ? 1 : 0;
 try {
 const API = import.meta.env.VITE_API_URL || "";
 await fetch(`${API}/api/quiz/confidence`, {
 method: "POST",
 headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("token")}` },
 body: JSON.stringify({ quiz_id: quiz.quiz_id, fach: subject, thema: question.question.slice(0, 60), confidence: level, war_richtig: warRichtig }),
 });
 } catch { /* silent */ }
 };

 const nextQuestion = () => {
 if (!quiz) return;
 setConfidenceGiven(false);
 if (currentQ < quiz.questions.length - 1) {
 setCurrentQ(currentQ + 1);
 setShowAnswer(false);
 setAnswerResult(null);
 } else {
 submitQuiz();
 }
 };

 const submitQuiz = async () => {
 if (!quiz) return;
 setLoading(true);
 try {
 const answersList = quiz.questions.map((q) => ({
 question_id: q.id,
 user_answer: answers[q.id] || "",
 }));
 const res = await quizApi.submit({
 quiz_id: quiz.quiz_id,
 subject: quiz.subject,
 answers: answersList,
 difficulty: quiz.difficulty,
 });
 setResult(res);
 setState("results");
 loadHistory();
 } catch (err) {
 console.error("Failed to submit quiz:", err);
 } finally {
 setLoading(false);
 }
 };

 const resetQuiz = () => {
 setState("setup"); setQuiz(null); setResult(null); setAnswers({});
 setCurrentQ(0); setShowAnswer(false); setAnswerResult(null);
 setCustomTopic(""); setSelectedPresetTopic("");
 };

 // Setup screen
 if (state === "setup") {
 return (
 <div className="p-4 lg:p-6 max-w-5xl mx-auto space-y-6">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <BrainCircuit className="w-7 h-7 text-blue-600" /> Quiz 3.0
 </h1>
 <p className="theme-text-secondary mt-1">Teste dein Wissen mit eigenen Themen oder vordefinierten Fragen!</p>
 </div>

 {/* Subject Selection */}
 <Card>
 <CardHeader><CardTitle className="text-base">Fach wählen</CardTitle></CardHeader>
 <CardContent>
 <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
 {SUBJECTS.map((s) => (
 <button key={s.id} onClick={() => { setSubject(s.id); setSelectedPresetTopic(""); }}
 className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${subject === s.id ? "border-blue-500 bg-blue-500/10" : "border-[var(--border-color)] hover:border-[var(--border-color)]"}`}>
 <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${s.color} flex items-center justify-center text-white`}>{s.icon}</div>
 <span className="text-sm font-medium theme-text-secondary">{s.name}</span>
 </button>
 ))}
 </div>
 </CardContent>
 </Card>

 {/* Topic Selection: 2-Column Layout */}
 <Card>
 <CardHeader><CardTitle className="text-base">Thema wählen</CardTitle></CardHeader>
 <CardContent>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div>
 <label className="block text-sm font-medium theme-text-secondary mb-2">Vordefinierte Themen</label>
 <select value={selectedPresetTopic}
 onChange={(e) => { setSelectedPresetTopic(e.target.value); if (e.target.value) setCustomTopic(""); }}
 className="w-full p-3 rounded-xl border-2 border-[var(--border-color)] theme-card theme-text">
 <option value="">-- Thema wählen --</option>
 {presetTopics.map((t) => (<option key={t.id} value={t.name}>{t.name}</option>))}
 </select>
 <p className="text-xs theme-text-secondary mt-1">{presetTopics.length} Themen verfügbar</p>
 </div>
 <div>
 <label className="block text-sm font-medium theme-text-secondary mb-2 flex items-center gap-1">
 Eigenes Thema eingeben <Badge variant="secondary" className="text-xs ml-1">Pro+</Badge>
 </label>
 <Input value={customTopic}
 onChange={(e) => { setCustomTopic(e.target.value); if (e.target.value) setSelectedPresetTopic(""); }}
 placeholder="z.B. Integralrechnung, Sturm und Drang, Napoleonische Kriege..." className="p-3" />
 <p className="text-xs theme-text-secondary mt-1 flex items-center gap-1"><Lock className="w-3 h-3" /> Eigenes Thema hat Priorität (Pro/Max)</p>
 </div>
 </div>
 </CardContent>
 </Card>

 {/* Quiz Type & Question Count */}
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <Card>
 <CardHeader><CardTitle className="text-base">Fragetyp</CardTitle></CardHeader>
 <CardContent>
 <div className="grid grid-cols-1 gap-2">
 {QUIZ_TYPES.map((t) => (
 <button key={t.id} onClick={() => setQuizType(t.id)}
 className={`flex items-center justify-between p-3 rounded-lg border-2 transition-all text-left ${quizType === t.id ? "border-blue-500 bg-blue-500/10" : "border-[var(--border-color)] hover:border-[var(--border-color)]"}`}>
 <span className="font-medium text-sm theme-text">{t.name}</span>
 <span className="text-xs theme-text-secondary">{t.desc}</span>
 </button>
 ))}
 </div>
 </CardContent>
 </Card>
 <div className="space-y-4">
 <Card>
 <CardHeader><CardTitle className="text-base">Schwierigkeitsgrad</CardTitle></CardHeader>
 <CardContent>
 <div className="grid grid-cols-3 gap-2">
 {DIFFICULTIES.map((d) => (
 <button key={d.id} onClick={() => setDifficulty(d.id)}
 className={`p-3 rounded-lg border-2 text-center transition-all ${difficulty === d.id ? "border-blue-500 bg-blue-500/10" : "border-[var(--border-color)] hover:border-[var(--border-color)]"}`}>
 <p className="font-medium text-sm theme-text">{d.name}</p>
 <p className="text-xs theme-text-secondary mt-0.5">{d.desc}</p>
 </button>
 ))}
 </div>
 </CardContent>
 </Card>
 <Card>
 <CardHeader><CardTitle className="text-base">Anzahl Fragen</CardTitle></CardHeader>
 <CardContent>
 <div className="grid grid-cols-4 gap-2">
 {QUESTION_COUNTS.map((n) => (
 <button key={n} onClick={() => setNumQuestions(n)}
 className={`p-3 rounded-lg border-2 text-center transition-all ${numQuestions === n ? "border-blue-500 bg-blue-500/10" : "border-[var(--border-color)] hover:border-[var(--border-color)]"}`}>
 <p className="font-bold text-lg theme-text">{n}</p>
 </button>
 ))}
 </div>
 </CardContent>
 </Card>
 </div>
 </div>

 <Button onClick={startQuiz} size="lg" className="w-full gap-2" disabled={loading}>
 {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <BrainCircuit className="w-5 h-5" />}
 {loading ? "Quiz wird erstellt..." : `Quiz starten (${numQuestions} Fragen)`}
 </Button>

 {/* Quiz History */}
 {history.length > 0 && (
 <Card>
 <CardHeader><CardTitle className="text-base">Letzte Quizzes</CardTitle></CardHeader>
 <CardContent>
 <div className="space-y-2">
 {history.slice(0, 5).map((h, i) => (
 <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-surface)]">
 <div className="flex items-center gap-3">
 <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${SUBJECTS.find(s => s.id === h.subject)?.color || "from-gray-500 to-gray-600"} flex items-center justify-center text-white text-xs`}>
 {SUBJECTS.find(s => s.id === h.subject)?.icon}
 </div>
 <div>
 <p className="text-sm font-medium theme-text">{SUBJECTS.find(s => s.id === h.subject)?.name || h.subject}</p>
 <p className="text-xs theme-text-secondary">{new Date(h.completed_at).toLocaleDateString(undefined)} - {h.difficulty}</p>
 </div>
 </div>
 <Badge variant={h.score >= 80 ? "success" : h.score >= 50 ? "warning" : "destructive"}>
 {h.correct_answers}/{h.total_questions} ({h.score}%)
 </Badge>
 </div>
 ))}
 </div>
 </CardContent>
 </Card>
 )}
 </div>
 );
 }

 // Playing screen
 if (state === "playing" && quiz) {
 const question = quiz.questions[currentQ];
 const isAnswered = showAnswer;
 const userAnswer = answers[question.id];
 const isCorrect = answerResult?.correct ?? false;
 const hasOptions = question.options && question.options.length > 0;
 const timerColor = timer > 15 ? "#22c55e" : timer > 5 ? "#f59e0b" : "#ef4444";
 const timerPercent = (timer / 30) * 100;

 return (
 <div className="p-4 lg:p-6 max-w-2xl mx-auto space-y-6">
 {/* Progress + Timer */}
 <div className="flex items-center justify-between">
 <Badge variant="secondary" className="text-sm">
 Frage {currentQ + 1} von {quiz.questions.length}
 </Badge>
 {!isAnswered && (
 <motion.div
 initial={{ scale: 0.8, opacity: 0 }}
 animate={{ scale: 1, opacity: 1 }}
 className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-bold"
 style={{
 background: `rgba(${timer > 15 ? "34,197,94" : timer > 5 ? "245,158,11" : "239,68,68"},0.15)`,
 border: `1px solid ${timerColor}40`,
 color: timerColor,
 }}
 >
 <Timer className="w-4 h-4" />
 <motion.span
 key={timer}
 initial={{ scale: 1.3, opacity: 0 }}
 animate={{ scale: 1, opacity: 1 }}
 transition={{ duration: 0.2 }}
 >
 {timer}s
 </motion.span>
 </motion.div>
 )}
 <Badge variant="default">
 {SUBJECTS.find(s => s.id === quiz.subject)?.name} - {difficulty}
 </Badge>
 </div>
 {/* Timer bar */}
 <div className="w-full rounded-full h-2 overflow-hidden" style={{ background: "rgba(var(--surface-rgb),0.5)" }}>
 <motion.div
 className="h-2 rounded-full"
 style={{ background: timerColor }}
 animate={{ width: `${isAnswered ? ((currentQ + 1) / quiz.questions.length) * 100 : timerPercent}%` }}
 transition={{ duration: 0.3 }}
 />
 </div>

 {/* Question */}
 <Card className="shadow-lg">
 <CardContent className="p-6">
 <div className="flex items-start justify-between gap-3 mb-6">
 <p className="text-lg font-medium theme-text">
 {question.question}
 </p>
 <ErklaerButton
 thema={question.question}
 fach={SUBJECTS.find(s => s.id === quiz.subject)?.name || "Allgemein"}
 variant="inline"
 className="shrink-0 mt-1"
 />
 </div>

 {/* MCQ Options — Animated */}
 {hasOptions ? (
 <div className="space-y-3">
 <AnimatePresence mode="wait">
 {question.options!.map((opt, idx) => {
 const isSelected = userAnswer === opt;
 const isRight = answerResult ? opt === answerResult.correct_answer : false;
 let optionBg = "transparent";
 let optionBorder = "var(--border-color)";
 if (isAnswered) {
 if (isRight) { optionBg = "rgba(34,197,94,0.1)"; optionBorder = "#22c55e"; }
 else if (isSelected && !isRight) { optionBg = "rgba(239,68,68,0.1)"; optionBorder = "#ef4444"; }
 else { optionBorder = "var(--border-color)"; }
 } else if (isSelected) {
 optionBg = "rgba(99,102,241,0.1)"; optionBorder = "#6366f1";
 }

 return (
 <motion.button
 key={`${currentQ}-${idx}`}
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: isAnswered && !isRight && !isSelected ? 0.5 : 1, x: 0 }}
 transition={{ delay: idx * 0.05, duration: 0.3 }}
 whileHover={!isAnswered ? { scale: 1.01, x: 4 } : {}}
 whileTap={!isAnswered ? { scale: 0.98 } : {}}
 onClick={() => selectAnswer(question.id, opt)}
 disabled={isAnswered}
 className="w-full text-left p-4 rounded-xl border-2 transition-colors flex items-center gap-3"
 style={{ background: optionBg, borderColor: optionBorder }}
 >
 <span className="w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm font-medium shrink-0">
 {String.fromCharCode(65 + idx)}
 </span>
 <span className="theme-text flex-1">{opt}</span>
 {isAnswered && isRight && (
 <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300 }}>
 <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
 </motion.div>
 )}
 {isAnswered && isSelected && !isRight && (
 <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300 }}>
 <XCircle className="w-5 h-5 text-red-500 shrink-0" />
 </motion.div>
 )}
 </motion.button>
 );
 })}
 </AnimatePresence>
 </div>
 ) : (
 /* Fill-in-blank */
 <div className="space-y-3">
 {!isAnswered ? (
 <div className="flex gap-2">
 <Input
 value={fillAnswer}
 onChange={(e) => setFillAnswer(e.target.value)}
 onKeyDown={(e) => e.key === "Enter" && submitFillAnswer()}
 placeholder="Deine Antwort eingeben..."
 className="flex-1"
 />
 <Button onClick={submitFillAnswer} disabled={!fillAnswer.trim()}>
 Prüfen
 </Button>
 </div>
 ) : (
 <div className={`p-4 rounded-xl border-2 ${isCorrect ? "border-emerald-500 bg-emerald-50" : "border-red-500 bg-red-50"}`}>
 <div className="flex items-center gap-2 mb-1">
 {isCorrect ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <XCircle className="w-5 h-5 text-red-500" />}
 <span className="font-medium">{isCorrect ? "Richtig!" : "Falsch"}</span>
 </div>
 <p className="text-sm theme-text-secondary">
 Deine Antwort: <strong>{userAnswer}</strong>
 </p>
 {!isCorrect && answerResult && (
 <p className="text-sm theme-text-secondary">
 Richtige Antwort: <strong>{answerResult.correct_answer}</strong>
 </p>
 )}
 </div>
 )}
 </div>
 )}

 {/* Explanation */}
 {isAnswered && answerResult?.explanation && (
 <div className="mt-4 p-4 rounded-xl bg-blue-50 border border-blue-200">
 <p className="text-sm font-medium text-blue-800 mb-1 flex items-center gap-1"><Lightbulb className="w-4 h-4" /> KI-Erklärung:</p>
 <p className="text-sm text-blue-700">{answerResult.explanation}</p>
 </div>
 )}
 </CardContent>
 </Card>

 {/* Confidence Slider */}
 {isAnswered && !confidenceGiven && (
 <ConfidenceSlider onSelect={handleConfidence} />
 )}

 {/* Navigation */}
 {isAnswered && confidenceGiven && (
 <Button onClick={nextQuestion} size="lg" className="w-full gap-2">
 {currentQ < quiz.questions.length - 1 ? (
 <>Nächste Frage <ArrowRight className="w-4 h-4" /></>
 ) : (
 <>Quiz beenden <Trophy className="w-4 h-4" /></>
 )}
 </Button>
 )}
 </div>
 );
 }

 // Results screen — with Framer Motion animations + XP display
 if (state === "results" && result) {
 const scoreColor = result.score >= 80 ? "text-emerald-500" : result.score >= 50 ? "text-amber-500" : "text-red-500";
 const scoreBg = result.score >= 80 ? "from-emerald-500 to-emerald-600" : result.score >= 50 ? "from-amber-500 to-amber-600" : "from-red-500 to-red-600";
 const xpEarned = result.score >= 80 ? 25 : result.score >= 50 ? 15 : 10;
 const showConfetti = result.score >= 80;

 const confettiColors = ["#22c55e", "#6366f1", "#a78bfa", "#f59e0b", "#06b6d4", "#f472b6"];
 const confettiPieces = Array.from({ length: 26 }, (_, i) => {
  const left = (i * 17) % 100;
  const size = 6 + (i % 3) * 3;
  const delay = i * 0.03;
  return {
   key: i,
   left,
   size,
   delay,
   color: confettiColors[i % confettiColors.length],
   rotate: (i * 57) % 360,
  };
 });

 return (
 <motion.div
 initial={{ opacity: 0, scale: 0.95 }}
 animate={{ opacity: 1, scale: 1 }}
 transition={{ duration: 0.5, ease: "easeOut" }}
 className="p-4 lg:p-6 max-w-2xl mx-auto space-y-6"
 >
 <Card className="shadow-xl text-center overflow-hidden" style={{ border: "1px solid rgba(99,102,241,0.3)" }}>
 <CardContent className="p-8 relative">
 {/* Confetti (score >= 80%) */}
 {showConfetti && (
  <div className="pointer-events-none absolute inset-0 overflow-hidden">
   {confettiPieces.map((p) => (
    <motion.div
     key={p.key}
     initial={{ y: -20, opacity: 0, rotate: p.rotate }}
     animate={{ y: 420, opacity: [0, 1, 1, 0], rotate: p.rotate + 360 }}
     transition={{ duration: 2.4, delay: p.delay, ease: "easeOut" }}
     className="absolute rounded-sm"
     style={{
      left: `${p.left}%`,
      top: -20,
      width: p.size,
      height: p.size * 0.55,
      background: p.color,
      boxShadow: `0 0 12px ${p.color}55`,
     }}
    />
   ))}
  </div>
 )}

 {/* Animated trophy */}
 <motion.div
 initial={{ scale: 0, rotate: -20 }}
 animate={{ scale: 1, rotate: 0 }}
 transition={{ type: "spring", stiffness: 200, damping: 12, delay: 0.2 }}
 className={`w-24 h-24 mx-auto rounded-full bg-gradient-to-br ${scoreBg} flex items-center justify-center text-white shadow-lg mb-6`}
 style={{ boxShadow: `0 0 40px ${result.score >= 80 ? "rgba(34,197,94,0.4)" : result.score >= 50 ? "rgba(245,158,11,0.4)" : "rgba(239,68,68,0.4)"}` }}
 >
 <Trophy className="w-12 h-12" />
 </motion.div>
 <motion.h2
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.3 }}
 className="text-2xl font-bold theme-text mb-2"
 >Quiz abgeschlossen!</motion.h2>
 <motion.p
 initial={{ opacity: 0, scale: 0.5 }}
 animate={{ opacity: 1, scale: 1 }}
 transition={{ delay: 0.5, type: "spring", stiffness: 200 }}
 className={`text-5xl font-bold ${scoreColor} mb-2`}
 >{result.score}%</motion.p>
 <p className="theme-text-secondary mb-4">
 {result.correct_answers} von {result.total_questions} richtig
 </p>
 <Badge variant={result.score >= 80 ? "success" : result.score >= 50 ? "warning" : "destructive"} className="text-sm px-4 py-1">
 Neues Level: {result.new_proficiency}
 </Badge>
 <p className="text-sm theme-text-secondary mt-4 max-w-md mx-auto">
 {result.feedback}
 </p>

 {result.weak_topic_detected && (
 <motion.div
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.7 }}
 className="mt-4 p-4 rounded-xl text-left"
 style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)" }}
 >
 <div className="flex items-center gap-2 mb-1">
 <AlertTriangle className="w-5 h-5 text-amber-500" />
 <span className="font-medium text-amber-400">Schwaches Thema erkannt</span>
 </div>
 <p className="text-sm text-amber-300/80">{result.weak_topic_suggestion}</p>
 </motion.div>
 )}

 {/* XP Animation */}
 <motion.div
 initial={{ opacity: 0, y: 20, scale: 0.8 }}
 animate={{ opacity: 1, y: 0, scale: 1 }}
 transition={{ delay: 0.8, type: "spring", stiffness: 200 }}
 className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-bold"
 style={{
 background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.2))",
 border: "1px solid rgba(99,102,241,0.4)",
 color: "#a78bfa",
 boxShadow: "0 0 20px rgba(99,102,241,0.3)",
 }}
 >
 <Zap className="w-4 h-4" />
 +{xpEarned} XP verdient!
 </motion.div>
 </CardContent>
 </Card>

 <div className="flex flex-col sm:flex-row gap-3">
 <Button onClick={startQuiz} className="flex-1 gap-2" disabled={loading}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
 Nochmal spielen
 </Button>
 <Button onClick={resetQuiz} variant="outline" className="flex-1">
 Anderes Fach
 </Button>
 <Button
  onClick={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "dashboard" }))}
  variant="outline"
  className="flex-1"
 >
  Zum Dashboard
 </Button>
 </div>
 </motion.div>
 );
 }

 return null;
}
