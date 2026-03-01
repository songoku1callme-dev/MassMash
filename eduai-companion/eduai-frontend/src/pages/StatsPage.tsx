import { useState, useEffect } from "react";
import { BarChart3, Brain, Flame, Trophy, Target, Sparkles, TrendingUp, BookOpen } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

export default function StatsPage() {
  const [overview, setOverview] = useState<StatsOverview | null>(null);
  const [subjects, setSubjects] = useState<SubjectStat[]>([]);
  const [strongest, setStrongest] = useState<SubjectStat[]>([]);
  const [weakest, setWeakest] = useState<SubjectStat[]>([]);
  const [analysis, setAnalysis] = useState("");
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem("eduai_access_token");
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-indigo-600" />
            Meine Statistiken
          </h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            Dein persoenliches Analyse-Dashboard
          </p>
        </div>
        <button
          onClick={runKIAnalyse}
          disabled={analysisLoading}
          className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          {analysisLoading ? "Analysiere..." : "KI-Analyse"}
        </button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<BookOpen className="w-5 h-5 text-blue-600" />} label="Lernzeit" value={`${ov.total_learning_minutes} min`} bg="bg-blue-50 dark:bg-blue-900/20" />
        <StatCard icon={<Target className="w-5 h-5 text-green-600" />} label="Quiz-Erfolg" value={`${ov.quiz_success_rate}%`} bg="bg-green-50 dark:bg-green-900/20" />
        <StatCard icon={<Flame className="w-5 h-5 text-orange-600" />} label="Streak" value={`${ov.current_streak} Tage`} sub={`Laengster: ${ov.longest_streak}`} bg="bg-orange-50 dark:bg-orange-900/20" />
        <StatCard icon={<Trophy className="w-5 h-5 text-purple-600" />} label="XP / Level" value={`${ov.total_xp} XP`} sub={`Level ${ov.level}`} bg="bg-purple-50 dark:bg-purple-900/20" />
      </div>

      {/* IQ Score */}
      {ov.iq_score !== null && (
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white text-center">
          <Brain className="w-8 h-8 mx-auto mb-2" />
          <p className="text-sm opacity-80">Dein IQ-Score</p>
          <p className="text-4xl font-bold">{ov.iq_score}</p>
        </div>
      )}

      {/* KI Analysis */}
      {analysis && (
        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-xl p-6 border border-indigo-200 dark:border-indigo-800">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-indigo-600" />
            KI-Analyse
          </h3>
          <div className="text-gray-700 dark:text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">
            {analysis}
          </div>
        </div>
      )}

      {/* Strongest & Weakest */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-3">
            <TrendingUp className="w-5 h-5 text-green-600" />
            Staerkste Faecher
          </h3>
          {strongest.length === 0 ? (
            <p className="text-gray-400 text-sm">Noch keine Daten</p>
          ) : (
            strongest.map((s) => (
              <SubjectBar key={s.subject} subject={s.subject} score={s.avg_score} color="bg-green-500" />
            ))
          )}
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-3">
            <Target className="w-5 h-5 text-red-600" />
            Zum Ueben
          </h3>
          {weakest.length === 0 ? (
            <p className="text-gray-400 text-sm">Keine Schwaechen erkannt</p>
          ) : (
            weakest.map((s) => (
              <SubjectBar key={s.subject} subject={s.subject} score={s.avg_score} color="bg-red-500" />
            ))
          )}
        </div>
      </div>

      {/* All Subjects Table */}
      {subjects.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Alle Faecher</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                  <th className="pb-2 font-medium">Fach</th>
                  <th className="pb-2 font-medium text-center">Quizze</th>
                  <th className="pb-2 font-medium text-center">Durchschnitt</th>
                  <th className="pb-2 font-medium text-center">Bestes</th>
                </tr>
              </thead>
              <tbody>
                {subjects.map((s) => (
                  <tr key={s.subject} className="border-b border-gray-100 dark:border-gray-700 last:border-0">
                    <td className="py-2 text-gray-900 dark:text-white font-medium">{s.subject}</td>
                    <td className="py-2 text-center text-gray-600 dark:text-gray-400">{s.total_quizzes}</td>
                    <td className="py-2 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        s.avg_score >= 80 ? "bg-green-100 text-green-700" :
                        s.avg_score >= 60 ? "bg-yellow-100 text-yellow-700" :
                        "bg-red-100 text-red-700"
                      }`}>
                        {s.avg_score}%
                      </span>
                    </td>
                    <td className="py-2 text-center text-gray-600 dark:text-gray-400">{s.best_score}%</td>
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
    <div className={`${bg} rounded-xl p-4 border border-gray-200/50 dark:border-gray-700/50`}>
      <div className="flex items-center gap-2 mb-2">{icon}<span className="text-xs text-gray-500 dark:text-gray-400">{label}</span></div>
      <p className="text-xl font-bold text-gray-900 dark:text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function SubjectBar({ subject, score, color }: { subject: string; score: number; color: string }) {
  return (
    <div className="mb-3 last:mb-0">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-700 dark:text-gray-300">{subject}</span>
        <span className="text-gray-500 dark:text-gray-400">{score}%</span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
    </div>
  );
}
