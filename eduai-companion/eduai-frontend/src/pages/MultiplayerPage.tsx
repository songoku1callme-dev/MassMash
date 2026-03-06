import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Swords, Users, Trophy, Clock, CheckCircle, XCircle, Copy, Loader2 } from "lucide-react";

const API = import.meta.env.VITE_API_URL || "";

interface Player { user_id: number; username: string; score: number; }
interface Question { frage: string; optionen: string[]; }

export default function MultiplayerPage() {
 const [roomCode, setRoomCode] = useState("");
 const [joinCode, setJoinCode] = useState("");
 const [players, setPlayers] = useState<Player[]>([]);
 const [questions, setQuestions] = useState<Question[]>([]);
 const [currentQ, setCurrentQ] = useState(0);
 const [gameStatus, setGameStatus] = useState<"idle" | "waiting" | "playing" | "finished">("idle");
 const [isHost, setIsHost] = useState(false);
 const [subject, setSubject] = useState("math");
 const [loading, setLoading] = useState(false);
 const [result, setResult] = useState<{ correct: boolean; points: number; erklaerung: string } | null>(null);
 const [scores, setScores] = useState<{ username: string; score: number }[]>([]);
 const [copied, setCopied] = useState(false);
 const [error, setError] = useState("");
 const wsRef = useRef<WebSocket | null>(null);
 const timerRef = useRef(0);
 const token = localStorage.getItem("lumnos_token");

 const apiCall = async (url: string, method = "POST") => {
 const res = await fetch(`${API}${url}`, {
 method,
 headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
 });
 return res.json();
 };

 const connectWS = (code: string) => {
 const wsUrl = API.replace("http", "ws") + `/api/multiplayer/ws/${code}`;
 const ws = new WebSocket(wsUrl);
 ws.onmessage = (event) => {
 const data = JSON.parse(event.data);
 if (data.type === "player_joined") setPlayers(data.players);
 if (data.type === "quiz_start") { setQuestions(data.questions); setGameStatus("playing"); setCurrentQ(0); }
 if (data.type === "score_update") setScores(data.scores);
 };
 wsRef.current = ws;
 };

 // Fix 8: Timeout + Fehlerbehandlung für Raum-Erstellung
 const createRoom = async () => {
 setLoading(true);
 setError("");
 const timeout = setTimeout(() => {
 setLoading(false);
 setError("Server antwortet nicht. Ist das Backend gestartet?");
 }, 5000);
 try {
 const data = await apiCall(`/api/multiplayer/create-room?subject=${subject}&num_questions=10`);
 clearTimeout(timeout);
 if (data.room_code) {
 setRoomCode(data.room_code); setPlayers(data.players || []); setIsHost(true); setGameStatus("waiting");
 connectWS(data.room_code);
 } else {
 setError(data.detail || "Raum konnte nicht erstellt werden.");
 }
 } catch {
 clearTimeout(timeout);
 setError("Verbindung fehlgeschlagen. Bitte versuche es erneut.");
 } finally {
 setLoading(false);
 }
 };

 const joinRoom = async () => {
 if (!joinCode.trim()) return;
 setLoading(true);
 setError("");
 try {
 const data = await apiCall(`/api/multiplayer/join/${joinCode.trim().toUpperCase()}`);
 if (data.room_code) { setRoomCode(data.room_code); setPlayers(data.players || []); setGameStatus("waiting"); connectWS(data.room_code); }
 else { setError(data.detail || "Raum nicht gefunden."); }
 } catch {
 setError("Verbindung fehlgeschlagen. Bitte versuche es erneut.");
 } finally {
 setLoading(false);
 }
 };

 const startQuiz = async () => { await apiCall(`/api/multiplayer/start/${roomCode}`); };

 const submitAnswer = async (answerIdx: number) => {
 const elapsed = Date.now() / 1000 - timerRef.current;
 const data = await apiCall(`/api/multiplayer/answer/${roomCode}?question_index=${currentQ}&answer_index=${answerIdx}&time_seconds=${Math.min(elapsed, 30)}`);
 setResult(data);
 setTimeout(() => {
 setResult(null);
 if (currentQ + 1 < questions.length) { setCurrentQ(currentQ + 1); timerRef.current = Date.now() / 1000; }
 else { setGameStatus("finished"); }
 }, 2000);
 };

 useEffect(() => { if (gameStatus === "playing") timerRef.current = Date.now() / 1000; }, [gameStatus, currentQ]);
 useEffect(() => { return () => { wsRef.current?.close(); }; }, []);

 const copyCode = () => { navigator.clipboard.writeText(roomCode); setCopied(true); setTimeout(() => setCopied(false), 2000); };

 if (gameStatus === "idle") {
 return (
 <div className="max-w-2xl mx-auto p-6 space-y-8">
 <div className="text-center">
 <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center mx-auto mb-4">
 <Swords className="w-8 h-8 text-white" />
 </div>
 <h1 className="text-3xl font-bold theme-text">Multiplayer-Quiz</h1>
 <p className="theme-text-secondary mt-2">Fordere deine Freunde heraus!</p>
 </div>
 <div className="grid md:grid-cols-2 gap-6">
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h2 className="text-lg font-semibold theme-text mb-4">Raum erstellen</h2>
 <select value={subject} onChange={(e) => setSubject(e.target.value)} className="w-full p-2 rounded-lg border border-[var(--border-color)] theme-card text-sm mb-4">
 <option value="math">Mathe</option>
 <option value="german">Deutsch</option>
 <option value="english">Englisch</option>
 <option value="physics">Physik</option>
 <option value="history">Geschichte</option>
 <option value="biology">Biologie</option>
 </select>
 <Button onClick={createRoom} disabled={loading} className="w-full">
 {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Swords className="w-4 h-4 mr-2" />} Raum erstellen
 </Button>
 {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
 </div>
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h2 className="text-lg font-semibold theme-text mb-4">Raum beitreten</h2>
 <Input placeholder="Raum-Code (z.B. ABC123)" value={joinCode} onChange={(e) => setJoinCode(e.target.value.toUpperCase())} className="mb-4 text-center text-lg font-mono tracking-widest" maxLength={6} />
 <Button onClick={joinRoom} disabled={loading || joinCode.length < 4} className="w-full" variant="outline">
 {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Users className="w-4 h-4 mr-2" />} Beitreten
 </Button>
 </div>
 </div>
 </div>
 );
 }

 if (gameStatus === "waiting") {
 return (
 <div className="max-w-lg mx-auto p-6 space-y-6">
 <div className="text-center">
 <h2 className="text-2xl font-bold theme-text">Warteraum</h2>
 <div className="mt-4 flex items-center justify-center gap-2">
 <span className="text-4xl font-mono font-bold tracking-[0.3em] text-purple-600">{roomCode}</span>
 <button onClick={copyCode} className="theme-text-secondary hover:text-purple-500">
 {copied ? <CheckCircle className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5" />}
 </button>
 </div>
 <p className="text-sm theme-text-secondary mt-2">Teile diesen Code mit deinen Freunden</p>
 </div>
 <div className="theme-card rounded-xl p-4 shadow-sm border border-[var(--border-color)]">
 <h3 className="font-semibold theme-text mb-3">Spieler ({players.length}/8)</h3>
 <div className="space-y-2">
 {players.map((p, i) => (
 <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-[var(--bg-surface)]">
 <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center text-white text-sm font-bold">{p.username[0]}</div>
 <span className="text-sm font-medium theme-text">{p.username}</span>
 {i === 0 && <Badge variant="secondary" className="ml-auto text-xs">Host</Badge>}
 </div>
 ))}
 </div>
 </div>
 {isHost ? (
 <Button onClick={startQuiz} className="w-full" size="lg"><Swords className="w-5 h-5 mr-2" /> Quiz starten ({players.length} Spieler)</Button>
 ) : (
 <p className="text-center text-gray-500 text-sm">Warte bis der Host das Quiz startet...</p>
 )}
 </div>
 );
 }

 if (gameStatus === "playing" && questions.length > 0) {
 const q = questions[currentQ];
 return (
 <div className="max-w-2xl mx-auto p-6 space-y-6">
 <div className="flex items-center justify-between">
 <Badge variant="outline">Frage {currentQ + 1}/{questions.length}</Badge>
 <div className="flex items-center gap-1 theme-text-secondary"><Clock className="w-4 h-4" /><span className="text-sm">Schneller = mehr Punkte!</span></div>
 </div>
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h2 className="text-xl font-semibold theme-text mb-6">{q.frage}</h2>
 <div className="grid grid-cols-1 gap-3">
 {q.optionen.map((opt, idx) => (
 <button key={idx} onClick={() => submitAnswer(idx)} disabled={!!result}
 className={`p-4 rounded-xl text-left font-medium transition-all border-2 ${result ? "border-[var(--border-color)]" : "border-[var(--border-color)] hover:border-purple-500 hover:bg-purple-500/10"}`}>
 <span className="theme-text">{opt}</span>
 </button>
 ))}
 </div>
 </div>
 {result && (
 <div className={`p-4 rounded-xl ${result.correct ? "bg-green-500/10 border border-green-500/20" : "bg-red-500/10 border border-red-500/20"}`}>
 <div className="flex items-center gap-2">
 {result.correct ? <CheckCircle className="w-5 h-5 text-green-600" /> : <XCircle className="w-5 h-5 text-red-600" />}
 <span className="font-semibold">{result.correct ? `Richtig! +${result.points} Punkte` : "Falsch!"}</span>
 </div>
 {result.erklaerung && <p className="text-sm theme-text-secondary mt-2">{result.erklaerung}</p>}
 </div>
 )}
 {scores.length > 0 && (
 <div className="theme-card rounded-xl p-4 shadow-sm border border-[var(--border-color)]">
 <h3 className="font-semibold text-sm theme-text-secondary mb-2">Live-Rangliste</h3>
 {[...scores].sort((a, b) => b.score - a.score).map((s, i) => (
 <div key={i} className="flex items-center justify-between py-1">
 <span className="text-sm">{i + 1}. {s.username}</span>
 <span className="font-mono text-sm font-bold text-purple-600">{s.score}</span>
 </div>
 ))}
 </div>
 )}
 </div>
 );
 }

 return (
 <div className="max-w-lg mx-auto p-6 space-y-6 text-center">
 <Trophy className="w-16 h-16 text-yellow-500 mx-auto" />
 <h1 className="text-3xl font-bold theme-text">Quiz beendet!</h1>
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h3 className="font-semibold theme-text mb-4">Endstand</h3>
 {[...(scores.length > 0 ? scores : players)].sort((a, b) => b.score - a.score).map((s, i) => (
 <div key={i} className="flex items-center justify-between py-2 border-b border-[var(--border-color)] last:border-0">
 <span className="text-lg">{i + 1}. {s.username}</span>
 <span className="font-mono text-lg font-bold text-purple-600">{s.score}</span>
 </div>
 ))}
 </div>
 <Button onClick={() => { setGameStatus("idle"); setRoomCode(""); setPlayers([]); setQuestions([]); setScores([]); }} className="w-full">Neues Spiel</Button>
 </div>
 );
}
