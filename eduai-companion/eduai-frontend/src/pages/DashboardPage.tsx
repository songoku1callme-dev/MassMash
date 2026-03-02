import { useEffect, useState } from "react";
import { learningApi, type Progress } from "../services/api";
import { useAuthStore } from "../stores/authStore";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer
} from "recharts";
import {
  MessageCircle, BrainCircuit, Flame, Target, Trophy, Camera
} from "lucide-react";

const SUBJECT_NAMES: Record<string, string> = {
  math: "Mathe",
  english: "Englisch",
  german: "Deutsch",
  history: "Geschichte",
  science: "Natur-Wiss.",
};

interface DashboardProps {
  onNavigate: (page: string) => void;
}

/** Reusable Bento card with glassmorphism and glow effect */
function BentoCard({
  children, span = "", glow = "indigo", onClick, pro = false
}: {
  children: React.ReactNode;
  span?: string;
  glow?: string;
  onClick?: () => void;
  pro?: boolean;
}) {
  const glowColors: Record<string, string> = {
    indigo: "hover:border-indigo-500/50 hover:shadow-glow-md",
    cyan:   "hover:border-cyan-500/50 hover:shadow-glow-cyan",
    violet: "hover:border-violet-500/50",
    orange: "hover:border-orange-500/50",
    green:  "hover:border-green-500/50",
    red:    "hover:border-red-500/50",
    purple: "hover:border-purple-500/50",
    yellow: "hover:border-yellow-500/50",
  };
  return (
    <div
      onClick={onClick}
      className={`glass-card relative overflow-hidden transition-all duration-300
                 ${span} ${glowColors[glow] || ""}
                 ${onClick ? "cursor-pointer" : ""}`}
    >
      {pro && (
        <div className="absolute top-2 right-2 text-xs bg-violet-500/20
                       text-violet-400 px-1.5 py-0.5 rounded-md font-bold">
          PRO
        </div>
      )}
      {children}
    </div>
  );
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
      <div className="flex items-center justify-center h-full cyber-bg">
        <div className="animate-pulse-glow rounded-full h-12 w-12 bg-lumnos-gradient flex items-center justify-center text-white text-lg font-bold">{"\u2726"}</div>
      </div>
    );
  }

  const profiles = progress?.profiles || [];
  const radarData = profiles.map((p) => ({
    subject: SUBJECT_NAMES[p.subject] || p.subject,
    score: p.mastery_score || 0,
    fullMark: 100,
  }));

  const getMotivatingGreeting = (streak: number) => {
    if (streak >= 30) return "Unaufhaltsam! Weiter so!";
    if (streak >= 7) return "Starke Woche! Bleib dran!";
    if (streak >= 3) return "Guter Lauf! Mach weiter!";
    return "Bereit zu lernen? Los geht's!";
  };

  const userName = user?.full_name?.split(" ")[0] || user?.username || "Lerner";
  const streak = progress?.streak_days || 0;
  const totalQuizzes = progress?.total_quizzes || 0;
  const totalSessions = progress?.total_sessions || 0;
  const totalCorrect = profiles.reduce((sum, p) => sum + p.correct_answers, 0);

  return (
    <div className="cyber-bg min-h-screen p-4 md:p-6 animate-fade-in">
      {/* Willkommens-Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-lumnos-text">
          Hey {userName}! {"\u2726"}
        </h1>
        <p className="text-lumnos-muted text-sm">
          {getMotivatingGreeting(streak)}
        </p>
      </div>

      {/* BENTO GRID */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 auto-rows-auto">

        {/* Hero-Kachel: KI-Chat (gross) */}
        <BentoCard span="col-span-2 row-span-2" glow="indigo"
                   onClick={() => onNavigate("chat")}>
          <div className="h-full flex flex-col justify-between p-4">
            <div>
              <div className="text-3xl mb-2">{"\uD83E\uDD16"}</div>
              <h2 className="text-xl font-bold text-white">KI-Tutor</h2>
              <p className="text-lumnos-muted text-sm mt-1">
                Frag mich alles — ich erklaere es!
              </p>
            </div>
            <div className="lumnos-btn-primary text-center text-sm rounded-xl py-2 mt-4">
              Chat starten {"\u2192"}
            </div>
          </div>
        </BentoCard>

        {/* Streak */}
        <BentoCard span="col-span-1" glow="orange">
          <div className="text-center p-3">
            <div className="text-3xl">{"\uD83D\uDD25"}</div>
            <div className="text-2xl font-black text-white">{streak}</div>
            <div className="text-xs text-lumnos-muted">Tage Streak</div>
          </div>
        </BentoCard>

        {/* Level/XP */}
        <BentoCard span="col-span-1" glow="violet">
          <div className="text-center p-3">
            <div className="text-3xl">{"\u2B50"}</div>
            <div className="text-2xl font-black text-white">{totalCorrect}</div>
            <div className="text-xs text-lumnos-muted">Richtige Antworten</div>
          </div>
        </BentoCard>

        {/* Tages-Quiz */}
        <BentoCard span="col-span-2" glow="cyan"
                   onClick={() => onNavigate("quiz")}>
          <div className="flex items-center gap-4 p-4">
            <div className="text-4xl">{"\u26A1"}</div>
            <div>
              <h3 className="font-bold text-white">Tages-Quiz</h3>
              <p className="text-sm text-lumnos-muted">{totalQuizzes} Quizzes absolviert</p>
              <p className="text-xs text-cyan-400 mt-1">Jetzt starten {"\u2192"}</p>
            </div>
          </div>
        </BentoCard>

        {/* Fach-Radar (klein) */}
        <BentoCard span="col-span-2" glow="green">
          <div className="p-2">
            <p className="text-xs font-bold text-lumnos-muted mb-1 px-2">Kompetenzprofil</p>
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="#334155" />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 9, fill: "#94a3b8" }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} />
                  <Radar
                    name="Score"
                    dataKey="score"
                    stroke="#6366f1"
                    fill="#6366f1"
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-40 flex items-center justify-center text-lumnos-muted text-xs">
                Starte ein Quiz um dein Profil aufzubauen
              </div>
            )}
          </div>
        </BentoCard>

        {/* Schulbuch-Scanner */}
        <BentoCard span="col-span-1" glow="purple"
                   onClick={() => onNavigate("scanner")} pro>
          <div className="text-center p-3">
            <div className="text-2xl"><Camera className="w-6 h-6 mx-auto text-purple-400" /></div>
            <div className="text-xs font-bold text-white mt-1">Scanner</div>
            <div className="text-xs text-lumnos-muted">Pro</div>
          </div>
        </BentoCard>

        {/* Turniere */}
        <BentoCard span="col-span-1" glow="yellow"
                   onClick={() => onNavigate("turnier")}>
          <div className="text-center p-3">
            <div className="text-2xl"><Trophy className="w-6 h-6 mx-auto text-yellow-400" /></div>
            <div className="text-xs font-bold text-white mt-1">Turnier</div>
            <div className="text-xs text-cyan-400">Live!</div>
          </div>
        </BentoCard>

        {/* Quick Actions Row */}
        <BentoCard span="col-span-2" glow="indigo"
                   onClick={() => onNavigate("flashcards")}>
          <div className="flex items-center gap-3 p-3">
            <div className="text-2xl">{"\uD83D\uDCDA"}</div>
            <div>
              <h3 className="font-bold text-white text-sm">Karteikarten</h3>
              <p className="text-xs text-lumnos-muted">Spaced Repetition lernen</p>
            </div>
          </div>
        </BentoCard>

        <BentoCard span="col-span-2" glow="cyan"
                   onClick={() => onNavigate("gamification")}>
          <div className="flex items-center gap-3 p-3">
            <div className="text-2xl">{"\uD83C\uDFAE"}</div>
            <div>
              <h3 className="font-bold text-white text-sm">Gamification</h3>
              <p className="text-xs text-lumnos-muted">XP, Badges & Achievements</p>
            </div>
          </div>
        </BentoCard>

        {/* Stats Overview */}
        <BentoCard span="col-span-4" glow="indigo">
          <div className="p-4">
            <p className="text-xs font-bold text-lumnos-muted mb-3">Deine Statistiken</p>
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <MessageCircle className="w-5 h-5 mx-auto text-blue-400 mb-1" />
                <p className="text-lg font-bold text-white">{totalSessions}</p>
                <p className="text-xs text-lumnos-muted">Chats</p>
              </div>
              <div className="text-center">
                <BrainCircuit className="w-5 h-5 mx-auto text-emerald-400 mb-1" />
                <p className="text-lg font-bold text-white">{totalQuizzes}</p>
                <p className="text-xs text-lumnos-muted">Quizzes</p>
              </div>
              <div className="text-center">
                <Target className="w-5 h-5 mx-auto text-amber-400 mb-1" />
                <p className="text-lg font-bold text-white">{totalCorrect}</p>
                <p className="text-xs text-lumnos-muted">Richtig</p>
              </div>
              <div className="text-center">
                <Flame className="w-5 h-5 mx-auto text-orange-400 mb-1" />
                <p className="text-lg font-bold text-white">{streak}</p>
                <p className="text-xs text-lumnos-muted">Streak</p>
              </div>
            </div>
          </div>
        </BentoCard>
      </div>
    </div>
  );
}
