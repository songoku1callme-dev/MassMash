import { useState, useEffect, useCallback, useMemo } from "react";
import { tournamentApi } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
 Trophy, Clock, Users, Medal, Loader2, Play, Timer, Award, ShieldCheck
} from "lucide-react";
import { PageLoader, ErrorState } from "../components/PageStates";

// Per-question time limit in seconds
const QUESTION_TIME_LIMIT = 30;

interface TournamentQuestion {
 id: number;
 question: string;
 options: string[];
 topic: string;
}

interface Tournament {
 id: number;
 subject: string;
 date: string;
 status: string;
 num_questions: number;
 time_limit_seconds: number;
 questions: TournamentQuestion[];
 participant_count: number;
}

interface Ranking {
 rank: number;
 username: string;
 score: number;
 correct_answers: number;
 time_taken_seconds: number;
}

interface Winner {
 rank: number;
 username: string;
 score: number;
 correct_answers: number;
 prize: string;
}

export default function TurnierPage() {
 const [tournament, setTournament] = useState<Tournament | null>(null);
 const [rankings, setRankings] = useState<Ranking[]>([]);
 const [winners, setWinners] = useState<Winner[]>([]);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState(false);
 const [joined, setJoined] = useState(false);
 const [submitting, setSubmitting] = useState(false);
 const [answers, setAnswers] = useState<Record<number, string>>({});
 const [submitted, setSubmitted] = useState(false);
 const [result, setResult] = useState<{ score: number; correct_answers: number; total_questions: number } | null>(null);

 // BUG 7: Anti-cheat state
 const [currentQ, setCurrentQ] = useState(0);
 const [questionTimeLeft, setQuestionTimeLeft] = useState(QUESTION_TIME_LIMIT);
 const [locked, setLocked] = useState(false);
 const [startTime, setStartTime] = useState(0);
 const [shuffledQuestions, setShuffledQuestions] = useState<TournamentQuestion[]>([]);

 useEffect(() => {
 loadTournament();
 loadWinners();
 }, []);

 // Shuffle array helper
 const shuffleArray = <T,>(arr: T[]): T[] => {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
   const j = Math.floor(Math.random() * (i + 1));
   [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
 };

 const handleAutoSubmit = useCallback(async () => {
  if (!tournament) return;
  setSubmitting(true);
  try {
   const answerList = Object.entries(answers).map(([qId, answer]) => ({
    question_id: parseInt(qId),
    answer,
   }));
   const elapsed = Math.round((Date.now() - startTime) / 1000);
   const data = await tournamentApi.submit(tournament.id, answerList, elapsed);
   setResult(data);
   setSubmitted(true);
   loadTournament();
  } catch (err) {
   console.error("Submit failed:", err);
  } finally {
   setSubmitting(false);
  }
 // eslint-disable-next-line react-hooks/exhaustive-deps
 }, [tournament, answers, startTime]);

 const advanceToNextQuestion = useCallback(() => {
  if (!shuffledQuestions.length) return;
  const nextQ = currentQ + 1;
  if (nextQ >= shuffledQuestions.length) {
   handleAutoSubmit();
  } else {
   setCurrentQ(nextQ);
   setQuestionTimeLeft(QUESTION_TIME_LIMIT);
   setLocked(false);
  }
 }, [currentQ, shuffledQuestions.length, handleAutoSubmit]);

 // BUG 7: Per-question countdown timer
 useEffect(() => {
  if (!joined || submitted || shuffledQuestions.length === 0) return;
  if (currentQ >= shuffledQuestions.length) return;
  const timer = setInterval(() => {
   setQuestionTimeLeft((t) => {
    if (t <= 1) {
     clearInterval(timer);
     setTimeout(() => advanceToNextQuestion(), 100);
     return 0;
    }
    return t - 1;
   });
  }, 1000);
  return () => clearInterval(timer);
 }, [joined, submitted, currentQ, shuffledQuestions.length, advanceToNextQuestion]);

 // BUG 7: Anti-copy protection
 useEffect(() => {
  if (!joined || submitted) return;
  const preventCopy = (e: ClipboardEvent) => { e.preventDefault(); };
  const preventContextMenu = (e: MouseEvent) => { e.preventDefault(); };
  const preventSelect = (e: Event) => { e.preventDefault(); };
  document.addEventListener("copy", preventCopy);
  document.addEventListener("contextmenu", preventContextMenu);
  document.addEventListener("selectstart", preventSelect);
  return () => {
   document.removeEventListener("copy", preventCopy);
   document.removeEventListener("contextmenu", preventContextMenu);
   document.removeEventListener("selectstart", preventSelect);
  };
 }, [joined, submitted]);

 const loadTournament = async () => {
 setLoading(true);
 setError(false);
 try {
 const data = await tournamentApi.current();
 if (data.tournament) {
 setTournament(data.tournament);
 if (data.tournament.status === "active" && data.tournament.id) {
 const rankData = await tournamentApi.rankings(data.tournament.id);
 setRankings(rankData.rankings || []);
 }
 }
 } catch {
 setError(true);
 } finally {
 setLoading(false);
 }
 };

 const loadWinners = async () => {
 try {
 const data = await tournamentApi.winners();
 setWinners(data.winners || []);
 } catch {
 // No winners yet
 }
 };

 const handleJoin = async () => {
 if (!tournament) return;
 try {
 await tournamentApi.join(tournament.id);
 // BUG 7: Shuffle questions and their answer options
 const shuffledQs = shuffleArray(tournament.questions).map((q) => ({
  ...q,
  options: shuffleArray(q.options),
 }));
 setShuffledQuestions(shuffledQs);
 setJoined(true);
 setCurrentQ(0);
 setQuestionTimeLeft(QUESTION_TIME_LIMIT);
 setLocked(false);
 setStartTime(Date.now());
 } catch (err) {
 console.error("Join failed:", err);
 }
 };

 const handleSelectAnswer = (questionId: number, letter: string) => {
  if (locked) return;
  setAnswers((prev) => ({ ...prev, [questionId]: letter }));
  setLocked(true);
  setTimeout(() => { advanceToNextQuestion(); }, 800);
 };

 // Current question data
 const currentQuestion = useMemo(() => {
  if (!shuffledQuestions.length || currentQ >= shuffledQuestions.length) return null;
  return shuffledQuestions[currentQ];
 }, [shuffledQuestions, currentQ]);

 const progressPercent = useMemo(() => {
  if (!shuffledQuestions.length) return 0;
  return Math.round((currentQ / shuffledQuestions.length) * 100);
 }, [currentQ, shuffledQuestions.length]);

 const timerColor = questionTimeLeft <= 5 ? "text-red-600" : questionTimeLeft <= 10 ? "text-orange-500" : "text-yellow-700";
 const timerBg = questionTimeLeft <= 5 ? "bg-red-50 border-red-300" : questionTimeLeft <= 10 ? "bg-orange-50 border-orange-300" : "bg-yellow-50 border-yellow-200";

 if (loading) return <PageLoader text="Turnier laden..." />;
 if (error) return <ErrorState message="Fehler beim Laden des Turniers." onRetry={loadTournament} />;

 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <Trophy className="w-7 h-7 text-yellow-500" />
 T&auml;gliches Turnier
 </h1>
 <p className="theme-text-secondary mt-1">
 Jeden Tag um 18:00 Uhr - Teste dein Wissen und gewinne Preise!
 </p>
 </div>

 {/* Current Tournament Info */}
 {tournament && !joined && !submitted && (
 <Card className="border-2 border-yellow-400">
 <CardHeader>
 <CardTitle className="flex items-center justify-between">
 <span className="flex items-center gap-2">
 <Trophy className="w-5 h-5 text-yellow-500" />
 {tournament.subject} - {tournament.date}
 </span>
 <span className={`text-sm px-3 py-1 rounded-full ${
 tournament.status === "active"
 ? "bg-emerald-100 text-emerald-700"
 : "bg-[var(--bg-surface)] theme-text-secondary"
 }`}>
 {tournament.status === "active" ? "Aktiv" : "Beendet"}
 </span>
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="flex items-center gap-6 text-sm theme-text-secondary">
 <span className="flex items-center gap-1">
 <Clock className="w-4 h-4" />
 {QUESTION_TIME_LIMIT}s pro Frage
 </span>
 <span className="flex items-center gap-1">
 <Users className="w-4 h-4" />
 {tournament.participant_count} Teilnehmer
 </span>
 <span>{tournament.num_questions} Fragen</span>
 </div>

 <div className="mt-3 p-3 rounded-lg bg-[var(--bg-surface)] text-sm theme-text-secondary">
 <div className="flex items-center gap-2 font-medium theme-text mb-1">
 <ShieldCheck className="w-4 h-4 text-emerald-500" />
 Anti-Cheat Regeln
 </div>
 <ul className="list-disc list-inside space-y-1">
 <li>Eine Frage nach der anderen</li>
 <li>{QUESTION_TIME_LIMIT} Sekunden pro Frage</li>
 <li>Kein Zur&uuml;ck-Button</li>
 <li>Antwort wird sofort gesperrt</li>
 <li>Zuf&auml;llige Reihenfolge</li>
 </ul>
 </div>

 {tournament.status === "active" && (
 <Button onClick={handleJoin} className="mt-4 bg-yellow-500 hover:bg-yellow-600 text-black">
 <Play className="w-4 h-4 mr-2" />
 Jetzt teilnehmen
 </Button>
 )}
 </CardContent>
 </Card>
 )}

 {!tournament && (
 <Card>
 <CardContent className="p-8 text-center">
 <Clock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
 <p className="text-gray-500">Kein aktives Turnier. N&auml;chstes Turnier um 18:00 Uhr!</p>
 </CardContent>
 </Card>
 )}

 {/* BUG 7: One question at a time with per-question timer */}
 {joined && !submitted && currentQuestion && (
 <>
 {/* Progress bar */}
 <div className="space-y-2">
 <div className="flex items-center justify-between text-sm theme-text-secondary">
 <span>Frage {currentQ + 1} von {shuffledQuestions.length}</span>
 <span>{progressPercent}%</span>
 </div>
 <div className="w-full h-2 bg-[var(--bg-surface)] rounded-full overflow-hidden">
 <div className="h-full bg-yellow-500 transition-all duration-300" style={{ width: `${progressPercent}%` }} />
 </div>
 </div>

 {/* Per-question timer */}
 <div className={`flex items-center justify-between p-3 rounded-lg border ${timerBg}`}>
 <span className="flex items-center gap-2 font-bold text-yellow-700">
 <Timer className="w-5 h-5" />
 Frage {currentQ + 1}
 </span>
 <span className={`text-3xl font-mono font-bold ${timerColor} ${questionTimeLeft <= 5 ? "animate-pulse" : ""}`}>
 {questionTimeLeft}s
 </span>
 </div>

 {/* Single question card */}
 <Card className="border-2 border-yellow-200">
 <CardContent className="p-6">
 <p className="text-sm text-yellow-600 font-medium mb-2">{currentQuestion.topic}</p>
 <p className="font-semibold theme-text text-lg mb-6 select-none" style={{ userSelect: "none", WebkitUserSelect: "none" }}>
 {currentQuestion.question}
 </p>
 <div className="grid grid-cols-1 gap-3">
 {currentQuestion.options.map((opt, i) => {
 const letter = String.fromCharCode(65 + i);
 const selected = answers[currentQuestion.id] === letter;
 const isLocked = locked;
 return (
 <button
 key={i}
 onClick={() => handleSelectAnswer(currentQuestion.id, letter)}
 disabled={isLocked}
 className={`p-4 rounded-xl text-left text-base border-2 transition-all min-h-[56px] select-none ${
  selected
  ? "border-yellow-500 bg-yellow-50 text-yellow-800 scale-[1.02] shadow-md"
  : isLocked
  ? "border-[var(--border-color)] opacity-50 cursor-not-allowed"
  : "border-[var(--border-color)] hover:border-yellow-300 hover:bg-yellow-50/50 active:scale-[0.98]"
 }`}
 style={{ userSelect: "none", WebkitUserSelect: "none" }}
 >
 <span className="font-bold mr-3 text-yellow-600">{letter}.</span>
 {opt}
 </button>
 );
 })}
 </div>
 {locked && (
 <p className="text-center text-sm text-yellow-600 mt-4 animate-pulse">
 N&auml;chste Frage...
 </p>
 )}
 </CardContent>
 </Card>
 </>
 )}

 {/* Submitting overlay */}
 {submitting && (
 <Card className="border-2 border-yellow-400">
 <CardContent className="p-8 text-center">
 <Loader2 className="w-10 h-10 text-yellow-500 mx-auto mb-3 animate-spin" />
 <p className="font-medium theme-text">Antworten werden ausgewertet...</p>
 </CardContent>
 </Card>
 )}

 {/* Result */}
 {submitted && result && (
 <Card className="border-2 border-emerald-400">
 <CardContent className="p-6 text-center">
 <Award className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
 <h2 className="text-2xl font-bold theme-text">
 {result.correct_answers} / {result.total_questions} richtig
 </h2>
 <p className="text-lg text-emerald-600 font-semibold mt-1">Score: {result.score}</p>
 <p className="text-sm text-gray-500 mt-2">Schau in die Rangliste um deinen Platz zu sehen!</p>
 </CardContent>
 </Card>
 )}

 {/* Rankings */}
 {rankings.length > 0 && (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Medal className="w-5 h-5 text-yellow-500" />
 Rangliste
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="space-y-2">
 {rankings.map((r) => (
 <div key={r.rank} className="flex items-center justify-between p-2 rounded bg-[var(--bg-surface)]">
 <div className="flex items-center gap-3">
 <span className={`w-8 h-8 flex items-center justify-center rounded-full font-bold text-sm ${
 r.rank === 1 ? "bg-yellow-100 text-yellow-700" :
 r.rank === 2 ? "bg-gray-400/20 theme-text-secondary" :
 r.rank === 3 ? "bg-orange-100 text-orange-700" :
 "bg-[var(--bg-surface)] theme-text-secondary"
 }`}>
 {r.rank}
 </span>
 <span className="font-medium text-sm">{r.username}</span>
 </div>
 <div className="text-sm text-gray-500">
 <span className="font-bold theme-text">{r.score}</span>
 <span className="ml-2">({r.correct_answers} richtig)</span>
 </div>
 </div>
 ))}
 </div>
 </CardContent>
 </Card>
 )}

 {/* Winners */}
 {winners.length > 0 && (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Trophy className="w-5 h-5 text-yellow-500" />
 Letzte Gewinner
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="space-y-2">
 {winners.map((w) => (
 <div key={w.rank} className="flex items-center justify-between p-3 rounded-lg bg-gradient-to-r from-yellow-50 to-amber-50">
 <div className="flex items-center gap-3">
 <span className={`text-lg ${w.rank === 1 ? "text-yellow-500" : w.rank === 2 ? "text-gray-400" : "text-orange-400"}`}>
 {w.rank === 1 ? "🥇" : w.rank === 2 ? "🥈" : "🥉"}
 </span>
 <span className="font-medium">{w.username}</span>
 </div>
 <span className="text-sm font-medium text-emerald-600">{w.prize}</span>
 </div>
 ))}
 </div>
 </CardContent>
 </Card>
 )}

 {/* Prizes Info */}
 <Card>
 <CardHeader>
 <CardTitle className="text-base">Preise</CardTitle>
 </CardHeader>
 <CardContent>
 <div className="space-y-2 text-sm">
 <div className="flex items-center justify-between p-2 rounded bg-yellow-50">
 <span>1. Platz</span>
 <span className="font-bold text-purple-600">1 Monat Max gratis</span>
 </div>
 <div className="flex items-center justify-between p-2 rounded bg-[var(--bg-surface)]">
 <span>2. Platz</span>
 <span className="font-bold text-blue-600">1 Monat Pro gratis</span>
 </div>
 <div className="flex items-center justify-between p-2 rounded bg-orange-50">
 <span>3. Platz</span>
 <span className="font-bold text-blue-500">1 Woche Pro gratis</span>
 </div>
 </div>
 </CardContent>
 </Card>
 </div>
 );
}
