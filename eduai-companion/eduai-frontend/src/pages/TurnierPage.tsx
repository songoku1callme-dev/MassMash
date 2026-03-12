import { useState, useEffect } from "react";
import { tournamentApi } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
 Trophy, Clock, Users, Medal, Loader2, Play, Send, Timer, Award
} from "lucide-react";
import { PageLoader, ErrorState } from "../components/PageStates";

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
 const [timeLeft, setTimeLeft] = useState(0);
 const [submitted, setSubmitted] = useState(false);
 const [result, setResult] = useState<{ score: number; correct_answers: number; total_questions: number } | null>(null);

 useEffect(() => {
 loadTournament();
 loadWinners();
 }, []);

 useEffect(() => {
 if (timeLeft <= 0 || !joined || submitted) return;
 const timer = setInterval(() => {
 setTimeLeft((t) => {
 if (t <= 1) {
 clearInterval(timer);
 return 0;
 }
 return t - 1;
 });
 }, 1000);
 return () => clearInterval(timer);
 }, [timeLeft, joined, submitted]);

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
 setJoined(true);
 setTimeLeft(tournament.time_limit_seconds);
 } catch (err) {
 console.error("Join failed:", err);
 }
 };

 const handleSubmit = async () => {
 if (!tournament) return;
 setSubmitting(true);
 try {
 const answerList = Object.entries(answers).map(([qId, answer]) => ({
 question_id: parseInt(qId),
 answer,
 }));
 const elapsed = tournament.time_limit_seconds - timeLeft;
 const data = await tournamentApi.submit(tournament.id, answerList, elapsed);
 setResult(data);
 setSubmitted(true);
 loadTournament();
 } catch (err) {
 console.error("Submit failed:", err);
 } finally {
 setSubmitting(false);
 }
 };

 const formatTime = (seconds: number) => {
 const m = Math.floor(seconds / 60);
 const s = seconds % 60;
 return `${m}:${s.toString().padStart(2, "0")}`;
 };

 if (loading) return <PageLoader text="Turnier laden..." />;
 if (error) return <ErrorState message="Fehler beim Laden des Turniers." onRetry={loadTournament} />;

 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <Trophy className="w-7 h-7 text-yellow-500" />
 Tägliches Turnier
 </h1>
 <p className="theme-text-secondary mt-1">
 Jeden Tag um 18:00 Uhr - Teste dein Wissen und gewinne Preise!
 </p>
 </div>

 {/* Current Tournament Info */}
 {tournament && (
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
 {Math.floor(tournament.time_limit_seconds / 60)} Min
 </span>
 <span className="flex items-center gap-1">
 <Users className="w-4 h-4" />
 {tournament.participant_count} Teilnehmer
 </span>
 <span>{tournament.num_questions} Fragen</span>
 </div>

 {!joined && !submitted && tournament.status === "active" && (
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
 <p className="text-gray-500">Kein aktives Turnier. Nächstes Turnier um 18:00 Uhr!</p>
 </CardContent>
 </Card>
 )}

 {/* Timer + Questions */}
 {joined && !submitted && tournament && (
 <>
 <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg border border-yellow-200">
 <span className="flex items-center gap-2 font-bold text-yellow-700">
 <Timer className="w-5 h-5" />
 Verbleibende Zeit
 </span>
 <span className={`text-2xl font-mono font-bold ${timeLeft < 60 ? "text-red-600" : "text-yellow-700"}`}>
 {formatTime(timeLeft)}
 </span>
 </div>

 <div className="space-y-4">
 {tournament.questions.map((q, idx) => (
 <Card key={q.id}>
 <CardContent className="p-4">
 <p className="font-medium theme-text mb-3">
 {idx + 1}. {q.question}
 </p>
 <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
 {q.options.map((opt, i) => {
 const letter = String.fromCharCode(65 + i);
 const selected = answers[q.id] === letter;
 return (
 <button
 key={i}
 onClick={() => setAnswers((prev) => ({ ...prev, [q.id]: letter }))}
 className={`p-3 rounded-lg text-left text-sm border transition-colors ${
 selected
 ? "border-yellow-500 bg-yellow-50 text-yellow-800"
 : "border-[var(--border-color)] hover:border-yellow-300"
 }`}
 >
 <span className="font-bold mr-2">{letter}.</span>
 {opt}
 </button>
 );
 })}
 </div>
 </CardContent>
 </Card>
 ))}
 </div>

 <Button onClick={handleSubmit} disabled={submitting} className="w-full bg-emerald-600 hover:bg-emerald-700">
 {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
 Antworten abgeben
 </Button>
 </>
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
