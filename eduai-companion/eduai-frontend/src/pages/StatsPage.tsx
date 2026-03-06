import { useState, useEffect } from "react";
import { BarChart3, Brain, Flame, Trophy, Target, Sparkles, TrendingUp, BookOpen, ArrowUp, ArrowDown, Minus, Download } from "lucide-react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts";

const API_URL = import.meta.env.VITE_API_URL || "";

interface StatsOverview {
 total_learning_minutes: number;
 total_quizzes: number;
 quiz_success_rate: number;
 current_streak: number;
 longest_streak: number;
 total_xp: number;
 level: number;
 iq_score: number | null;
}

interface SubjectStat {
 subject: string;
 total_quizzes: number;
 avg_score: number;
 best_score: number;
}

interface NotenPrognose {
 fach: string;
 aktuelle_note: number;
 prognose_note: number;
 trend: string;
 confidence: number;
 avg_score: number;
 total_quizzes: number;
}

export default function StatsPage() {
 const [overview, setOverview] = useState<StatsOverview | null>(null);
 const [subjects, setSubjects] = useState<SubjectStat[]>([]);
 const [strongest, setStrongest] = useState<SubjectStat[]>([]);
 const [weakest, setWeakest] = useState<SubjectStat[]>([]);
 const [analysis, setAnalysis] = useState("");
 const [analysisLoading, setAnalysisLoading] = useState(false);
 const [loading, setLoading] = useState(true);
 const [prognosen, setPrognosen] = useState<NotenPrognose[]>([]);
 const [prognoseLoading, setPrognoseLoading] = useState(false);
 const [prognoseEmpfehlung, setPrognoseEmpfehlung] = useState("");
 const [prognoseTrend, setPrognoseTrend] = useState("");

 const token = localStorage.getItem("lumnos_access_token");
 const headers = { Authorization: `Bearer ${token}` };

 useEffect(() => {
 const load = async () => {
 try {
 const [ovRes, subjRes] = await Promise.all([
 fetch(`${API_URL}/api/stats/overview`, { headers }),
 fetch(`${API_URL}/api/stats/per-subject`, { headers }),
 ]);
 if (ovRes.ok) setOverview(await ovRes.json());
 if (subjRes.ok) {
 const data = await subjRes.json();
 setSubjects(data.subjects || []);
 setStrongest(data.strongest || []);
 setWeakest(data.weakest || []);
 }
 } catch { /* ignore */ }
 setLoading(false);
 };
 load();
 }, []);

 const runNotenPrognose = async () => {
 setPrognoseLoading(true);
 try {
 const resp = await fetch(`${API_URL}/api/stats/noten-prognose`, {
 method: "POST",
 headers,
 });
 if (resp.ok) {
 const data = await resp.json();
 setPrognosen(data.prognosen || []);
 setPrognoseEmpfehlung(data.empfehlung || "");
 setPrognoseTrend(data.gesamt_trend || "");
 }
 } catch { /* ignore */ }
 setPrognoseLoading(false);
 };

 const runKIAnalyse = async () => {
 setAnalysisLoading(true);
 try {
 const resp = await fetch(`${API_URL}/api/stats/ki-analyse`, {
 method: "POST",
 headers,
 });
 if (resp.ok) {
 const data = await resp.json();
 setAnalysis(data.analysis || "");
 }
 } catch { /* ignore */ }
 setAnalysisLoading(false);
 };

 if (loading) {
 return (
 <div className="p-8 flex items-center justify-center min-h-screen">
 <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
 </div>
 );
 }

 const ov = overview || {
 total_learning_minutes: 0, total_quizzes: 0, quiz_success_rate: 0,
 current_streak: 0, longest_streak: 0, total_xp: 0, level: 1, iq_score: null,
 };

 return (
 <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-6">
 <div className="flex items-center justify-between">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <BarChart3 className="w-7 h-7 text-indigo-600" />
 Meine Statistiken
 </h1>
 <p className="theme-text-secondary text-sm mt-1">
 Dein persönliches Analyse-Dashboard
 </p>
 </div>
 <div className="flex items-center gap-2">
 <a
 href={`${API_URL}/api/stats/export/csv`}
 className="px-3 py-2 bg-[var(--bg-surface)] theme-text-secondary rounded-lg text-sm font-medium hover:bg-[var(--bg-surface)] transition-colors flex items-center gap-1.5"
 onClick={(e) => {
 e.preventDefault();
 const t = localStorage.getItem("lumnos_token") || localStorage.getItem("lumnos_access_token");
 if (t) window.open(`${API_URL}/api/stats/export/csv?token=${t}`, "_blank");
 }}
 >
 <Download className="w-4 h-4" />
 CSV
 </a>
 <button
 onClick={runKIAnalyse}
 disabled={analysisLoading}
 className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
 >
 <Sparkles className="w-4 h-4" />
 {analysisLoading ? "Analysiere..." : "KI-Analyse"}
 </button>
 </div>
 </div>

 {/* Overview Cards */}
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
 <StatCard icon={<BookOpen className="w-5 h-5 text-blue-600" />} label="Lernzeit" value={`${ov.total_learning_minutes} min`} bg="bg-blue-50" />
 <StatCard icon={<Target className="w-5 h-5 text-green-600" />} label="Quiz-Erfolg" value={`${ov.quiz_success_rate}%`} bg="bg-green-50" />
 <StatCard icon={<Flame className="w-5 h-5 text-orange-600" />} label="Streak" value={`${ov.current_streak} Tage`} sub={`Laengster: ${ov.longest_streak}`} bg="bg-orange-50" />
 <StatCard icon={<Trophy className="w-5 h-5 text-purple-600" />} label="XP / Level" value={`${ov.total_xp} XP`} sub={`Level ${ov.level}`} bg="bg-purple-50" />
 </div>

 {/* IQ Score */}
 {ov.iq_score !== null && (
 <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white text-center">
 <Brain className="w-8 h-8 mx-auto mb-2" />
 <p className="text-sm opacity-80">Dein IQ-Score</p>
 <p className="text-4xl font-bold">{ov.iq_score}</p>
 </div>
 )}

 {/* Supreme 13.0 Phase 10: Noten-Prognose */}
 <div className="theme-card rounded-xl p-5 border border-[var(--border-color)]">
 <div className="flex items-center justify-between mb-4">
 <h3 className="font-semibold theme-text flex items-center gap-2">
 <TrendingUp className="w-5 h-5 text-indigo-600" />
 Noten-Prognose
 </h3>
 <button
 onClick={runNotenPrognose}
 disabled={prognoseLoading}
 className="px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-lg text-xs font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
 >
 {prognoseLoading ? "Berechne..." : "Prognose erstellen"}
 </button>
 </div>

 {prognosen.length === 0 ? (
 <p className="theme-text-secondary text-sm">Klicke auf &quot;Prognose erstellen&quot; für deine Noten-Vorhersage</p>
 ) : (
 <>
 {prognoseTrend && (
 <div className={`mb-3 px-3 py-2 rounded-lg text-sm font-medium ${
 prognoseTrend === "steigend" ? "bg-green-50 text-green-700" :
 prognoseTrend === "fallend" ? "bg-red-50 text-red-700" :
 "bg-[var(--bg-surface)] theme-text-secondary"
 }`}>
 Gesamt-Trend: {prognoseTrend === "steigend" ? "Aufwaerts" : prognoseTrend === "fallend" ? "Abwaerts" : "Stabil"}
 </div>
 )}
 <div className="space-y-2">
 {prognosen.map((p) => (
 <div key={p.fach} className="flex items-center gap-3 p-2 rounded-lg bg-[var(--bg-surface)]/50">
 <div className="flex-1">
 <span className="text-sm font-medium theme-text">{p.fach}</span>
 <span className="text-xs text-gray-400 ml-2">({p.total_quizzes} Quizze)</span>
 </div>
 <div className="text-center">
 <span className="text-xs theme-text-secondary">Aktuell</span>
 <p className="text-lg font-bold theme-text">{p.aktuelle_note}</p>
 </div>
 <div className="flex items-center">
 {p.trend === "steigend" ? <ArrowUp className="w-4 h-4 text-green-500" /> :
 p.trend === "fallend" ? <ArrowDown className="w-4 h-4 text-red-500" /> :
 <Minus className="w-4 h-4 theme-text-secondary" />}
 </div>
 <div className="text-center">
 <span className="text-xs theme-text-secondary">Prognose</span>
 <p className={`text-lg font-bold ${
 p.prognose_note < p.aktuelle_note ? "text-green-600" :
 p.prognose_note > p.aktuelle_note ? "text-red-600" :
 "theme-text"
 }`}>{p.prognose_note}</p>
 </div>
 <div className="w-12 text-right">
 <span className="text-xs theme-text-secondary">{Math.round(p.confidence * 100)}%</span>
 </div>
 </div>
 ))}
 </div>
 {prognoseEmpfehlung && (
 <div className="mt-3 p-3 bg-indigo-50 rounded-lg text-sm theme-text-secondary whitespace-pre-wrap">
 {prognoseEmpfehlung}
 </div>
 )}
 </>
 )}
 </div>

 {/* KI Analysis */}
 {analysis && (
 <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-200">
 <h3 className="font-semibold theme-text flex items-center gap-2 mb-3">
 <Sparkles className="w-5 h-5 text-indigo-600" />
 KI-Analyse
 </h3>
 <div className="theme-text-secondary text-sm whitespace-pre-wrap leading-relaxed">
 {analysis}
 </div>
 </div>
 )}

 {/* Perfect School 4.1 Block 3.1: Fach-Radar */}
 {subjects.length > 0 && (
 <div className="theme-card rounded-xl p-5 border border-[var(--border-color)]">
 <h3 className="font-semibold theme-text flex items-center gap-2 mb-3">
 <Target className="w-5 h-5 text-indigo-600" />
 Fach-Radar
 </h3>
 <ResponsiveContainer width="100%" height={300}>
 <RadarChart data={subjects.map(s => ({ subject: s.subject, score: s.avg_score, fullMark: 100 }))}>
 <PolarGrid />
 <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
 <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
 <Radar name="Score" dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
 </RadarChart>
 </ResponsiveContainer>
 </div>
 )}

 {/* Strongest & Weakest */}
 <div className="grid md:grid-cols-2 gap-4">
 <div className="theme-card rounded-xl p-5 border border-[var(--border-color)]">
 <h3 className="font-semibold theme-text flex items-center gap-2 mb-3">
 <TrendingUp className="w-5 h-5 text-green-600" />
 Stärkste Fächer
 </h3>
 {strongest.length === 0 ? (
 <p className="theme-text-secondary text-sm">Noch keine Daten</p>
 ) : (
 strongest.map((s) => (
 <SubjectBar key={s.subject} subject={s.subject} score={s.avg_score} color="bg-green-500" />
 ))
 )}
 </div>
 <div className="theme-card rounded-xl p-5 border border-[var(--border-color)]">
 <h3 className="font-semibold theme-text flex items-center gap-2 mb-3">
 <Target className="w-5 h-5 text-red-600" />
 Zum Ueben
 </h3>
 {weakest.length === 0 ? (
 <p className="theme-text-secondary text-sm">Keine Schwächen erkannt</p>
 ) : (
 weakest.map((s) => (
 <SubjectBar key={s.subject} subject={s.subject} score={s.avg_score} color="bg-red-500" />
 ))
 )}
 </div>
 </div>

 {/* All Subjects Table */}
 {subjects.length > 0 && (
 <div className="theme-card rounded-xl p-5 border border-[var(--border-color)]">
 <h3 className="font-semibold theme-text mb-3">Alle Fächer</h3>
 <div className="overflow-x-auto">
 <table className="w-full text-sm">
 <thead>
 <tr className="text-left theme-text-secondary border-b border-[var(--border-color)]">
 <th className="pb-2 font-medium">Fach</th>
 <th className="pb-2 font-medium text-center">Quizze</th>
 <th className="pb-2 font-medium text-center">Durchschnitt</th>
 <th className="pb-2 font-medium text-center">Bestes</th>
 </tr>
 </thead>
 <tbody>
 {subjects.map((s) => (
 <tr key={s.subject} className="border-b border-[var(--border-color)] last:border-0">
 <td className="py-2 theme-text font-medium">{s.subject}</td>
 <td className="py-2 text-center theme-text-secondary">{s.total_quizzes}</td>
 <td className="py-2 text-center">
 <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
 s.avg_score >= 80 ? "bg-green-100 text-green-700" :
 s.avg_score >= 60 ? "bg-yellow-100 text-yellow-700" :
 "bg-red-100 text-red-700"
 }`}>
 {s.avg_score}%
 </span>
 </td>
 <td className="py-2 text-center theme-text-secondary">{s.best_score}%</td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </div>
 )}
 </div>
 );
}

function StatCard({ icon, label, value, sub, bg }: {
 icon: React.ReactNode; label: string; value: string; sub?: string; bg: string;
}) {
 return (
 <div className={`${bg} rounded-xl p-4 border border-gray-200/50/50`}>
 <div className="flex items-center gap-2 mb-2">{icon}<span className="text-xs theme-text-secondary">{label}</span></div>
 <p className="text-xl font-bold theme-text">{value}</p>
 {sub && <p className="text-xs theme-text-secondary mt-1">{sub}</p>}
 </div>
 );
}

function SubjectBar({ subject, score, color }: { subject: string; score: number; color: string }) {
 return (
 <div className="mb-3 last:mb-0">
 <div className="flex justify-between text-sm mb-1">
 <span className="theme-text-secondary">{subject}</span>
 <span className="theme-text-secondary">{score}%</span>
 </div>
 <div className="h-2 bg-[var(--progress-bg)] rounded-full overflow-hidden">
 <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${Math.min(score, 100)}%` }} />
 </div>
 </div>
 );
}
