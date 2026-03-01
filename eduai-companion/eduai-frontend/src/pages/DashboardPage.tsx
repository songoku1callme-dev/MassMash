import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { learningApi, type Progress } from "../services/api";
import { useAuthStore } from "../stores/authStore";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from "recharts";
import {
  Calculator, Languages, BookOpenCheck, Clock, FlaskConical,
  TrendingUp, MessageCircle, BrainCircuit, Flame, Target
} from "lucide-react";

const SUBJECT_ICONS: Record<string, React.ReactNode> = {
  math: <Calculator className="w-5 h-5" />,
  english: <Languages className="w-5 h-5" />,
  german: <BookOpenCheck className="w-5 h-5" />,
  history: <Clock className="w-5 h-5" />,
  science: <FlaskConical className="w-5 h-5" />,
};

const SUBJECT_COLORS: Record<string, string> = {
  math: "from-blue-500 to-blue-600",
  english: "from-emerald-500 to-emerald-600",
  german: "from-amber-500 to-amber-600",
  history: "from-purple-500 to-purple-600",
  science: "from-rose-500 to-rose-600",
};

const SUBJECT_NAMES: Record<string, string> = {
  math: "Mathe",
  english: "Englisch",
  german: "Deutsch",
  history: "Geschichte",
  science: "Natur-Wiss.",
};

const LEVEL_BADGES: Record<string, { variant: "default" | "success" | "warning"; label: string }> = {
  beginner: { variant: "warning", label: "Anfänger" },
  intermediate: { variant: "default", label: "Mittel" },
  advanced: { variant: "success", label: "Fortgeschritten" },
};

interface DashboardProps {
  onNavigate: (page: string) => void;
}

export default function DashboardPage({ onNavigate }: DashboardProps) {
  const { user } = useAuthStore();
  const [progress, setProgress] = useState<Progress | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProgress();
  }, []);

  const loadProgress = async () => {
    try {
      const data = await learningApi.progress();
      setProgress(data);
    } catch (err) {
      console.error("Failed to load progress:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const profiles = progress?.profiles || [];
  const barData = profiles.map((p) => ({
    name: SUBJECT_NAMES[p.subject] || p.subject,
    mastery: p.mastery_score,
    accuracy: p.accuracy,
  }));

  const radarData = profiles.map((p) => ({
    subject: SUBJECT_NAMES[p.subject] || p.subject,
    score: p.mastery_score || 0,
    fullMark: 100,
  }));

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Guten Morgen";
    if (hour < 18) return "Guten Tag";
    return "Guten Abend";
  };

  return (
    <div className="p-4 lg:p-6 space-y-6 max-w-7xl mx-auto">
      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white">
            {greeting()}, {user?.full_name?.split(" ")[0] || user?.username}!
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Bereit zu lernen? Wähle ein Fach oder stelle eine Frage.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-orange-50 dark:bg-orange-900/20">
            <Flame className="w-4 h-4 text-orange-500" />
            <span className="text-sm font-medium text-orange-700 dark:text-orange-300">
              {progress?.streak_days || 0} Tage Streak
            </span>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
              <MessageCircle className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{progress?.total_sessions || 0}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Chat-Sitzungen</p>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
              <BrainCircuit className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{progress?.total_quizzes || 0}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Quizzes</p>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-50 dark:bg-purple-900/20 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {profiles.reduce((sum, p) => sum + p.total_questions_answered, 0)}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Fragen beantwortet</p>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center">
              <Target className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {profiles.reduce((sum, p) => sum + p.correct_answers, 0)}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Richtig beantwortet</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Subject Cards */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Fächer</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {profiles.map((p) => {
            const badge = LEVEL_BADGES[p.proficiency_level] || LEVEL_BADGES.beginner;
            return (
              <Card
                key={p.subject}
                className="hover:shadow-lg transition-all cursor-pointer group"
                onClick={() => onNavigate("chat")}
              >
                <CardContent className="p-4 text-center">
                  <div className={`w-12 h-12 mx-auto rounded-xl bg-gradient-to-br ${SUBJECT_COLORS[p.subject] || "from-gray-500 to-gray-600"} flex items-center justify-center text-white shadow-md group-hover:scale-110 transition-transform mb-3`}>
                    {SUBJECT_ICONS[p.subject]}
                  </div>
                  <h3 className="font-medium text-gray-900 dark:text-white text-sm">
                    {SUBJECT_NAMES[p.subject] || p.subject}
                  </h3>
                  <Badge variant={badge.variant} className="mt-2 text-xs">
                    {badge.label}
                  </Badge>
                  <div className="mt-2 w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full bg-gradient-to-r ${SUBJECT_COLORS[p.subject] || "from-gray-500 to-gray-600"}`}
                      style={{ width: `${Math.max(p.mastery_score, 5)}%` }}
                    />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Mastery Bar Chart */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Fortschritt nach Fach</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} />
                <Tooltip />
                <Bar dataKey="mastery" fill="#3B82F6" radius={[4, 4, 0, 0]} name="Meisterung %" />
                <Bar dataKey="accuracy" fill="#10B981" radius={[4, 4, 0, 0]} name="Genauigkeit %" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Radar Chart */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Kompetenzprofil</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Radar
                  name="Score"
                  dataKey="score"
                  stroke="#3B82F6"
                  fill="#3B82F6"
                  fillOpacity={0.3}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Letzte Aktivitäten</CardTitle>
          </CardHeader>
          <CardContent>
            {progress?.recent_activity && progress.recent_activity.length > 0 ? (
              <div className="space-y-3">
                {progress.recent_activity.slice(0, 5).map((a, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs ${
                      a.activity_type === "chat" ? "bg-blue-500" :
                      a.activity_type === "quiz" ? "bg-emerald-500" : "bg-gray-500"
                    }`}>
                      {a.activity_type === "chat" ? <MessageCircle className="w-4 h-4" /> :
                       a.activity_type === "quiz" ? <BrainCircuit className="w-4 h-4" /> :
                       <Target className="w-4 h-4" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-700 dark:text-gray-300 truncate">{a.description}</p>
                      <p className="text-xs text-gray-400">{new Date(a.created_at).toLocaleString("de-DE")}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                Noch keine Aktivitäten. Starte deinen ersten Chat!
              </p>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Schnellstart</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              variant="outline"
              className="w-full justify-start gap-3 h-auto py-3"
              onClick={() => onNavigate("chat")}
            >
              <MessageCircle className="w-5 h-5 text-blue-500" />
              <div className="text-left">
                <p className="font-medium">Frage stellen</p>
                <p className="text-xs text-gray-500">Starte einen Chat mit dem KI-Tutor</p>
              </div>
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start gap-3 h-auto py-3"
              onClick={() => onNavigate("quiz")}
            >
              <BrainCircuit className="w-5 h-5 text-emerald-500" />
              <div className="text-left">
                <p className="font-medium">Quiz starten</p>
                <p className="text-xs text-gray-500">Teste dein Wissen mit einem Quiz</p>
              </div>
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start gap-3 h-auto py-3"
              onClick={() => onNavigate("learning")}
            >
              <BookOpenCheck className="w-5 h-5 text-purple-500" />
              <div className="text-left">
                <p className="font-medium">Lernpfad ansehen</p>
                <p className="text-xs text-gray-500">Deine empfohlenen nächsten Schritte</p>
              </div>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
