import { useEffect, useState } from "react";
import { learningApi, type Progress } from "../services/api";
import { useAuthStore } from "../stores/authStore";

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
      <div className="flex items-center justify-center h-full min-h-screen bg-[#0a0f1e]">
        <div className="animate-pulse rounded-full h-12 w-12 flex items-center justify-center text-white text-lg font-bold"
             style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.5)" }}>
          {"\u2726"}
        </div>
      </div>
    );
  }

  const userName = user?.full_name?.split(" ")[0] || user?.username || "Lernender";
  const streak = progress?.streak_days || 0;
  const totalQuizzes = progress?.total_quizzes || 0;
  const totalSessions = progress?.total_sessions || 0;
  const profiles = progress?.profiles || [];
  const totalCorrect = profiles.reduce((sum, p) => sum + p.correct_answers, 0);
  const correctPercent = totalQuizzes > 0 ? Math.round((totalCorrect / Math.max(totalQuizzes, 1)) * 100) : 0;
  const tier = user?.subscription_tier || "free";

  return (
    <div className="min-h-screen bg-[#0a0f1e] p-4 md:p-6"
         style={{
           backgroundImage: "linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px)",
           backgroundSize: "32px 32px"
         }}>

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Hey {userName}! {"\u2726"}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {streak > 0
              ? `\uD83D\uDD25 ${streak} Tage Streak — weiter so!`
              : "Bereit zu lernen? Los geht's!"}
          </p>
        </div>

        {/* UPGRADE BUTTON — immer sichtbar für Free-User */}
        {tier === "free" && (
          <button
            onClick={() => onNavigate("pricing")}
            className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm text-white"
            style={{
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              boxShadow: "0 0 20px rgba(99,102,241,0.5)",
              animation: "pulse 2s infinite"
            }}>
            {"\u26A1"} Pro upgraden
          </button>
        )}
      </div>

      {/* BENTO GRID */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">

        {/* KI-Tutor — Groß (2x2) */}
        <button
          onClick={() => onNavigate("chat")}
          className="col-span-2 row-span-2 rounded-2xl p-5 text-left transition-all duration-300 hover:-translate-y-1"
          style={{
            background: "rgba(99,102,241,0.1)",
            border: "1px solid rgba(99,102,241,0.3)",
            backdropFilter: "blur(12px)",
            boxShadow: "inset 0 0 20px rgba(99,102,241,0.05)"
          }}
          onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 0 30px rgba(99,102,241,0.4)"; }}
          onMouseLeave={e => { e.currentTarget.style.boxShadow = "inset 0 0 20px rgba(99,102,241,0.05)"; }}>
          <div className="text-4xl mb-3">{"\uD83E\uDD16"}</div>
          <h2 className="text-xl font-bold text-white mb-1">KI-Tutor</h2>
          <p className="text-slate-400 text-sm">
            Frag mich alles — ich erkläre es Schritt für Schritt!
          </p>
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold text-white"
               style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
            Chat starten {"\u2192"}
          </div>
        </button>

        {/* Streak */}
        <div className="rounded-2xl p-4 text-center"
             style={{ background: "rgba(249,115,22,0.1)", border: "1px solid rgba(249,115,22,0.3)" }}>
          <div className="text-3xl">{"\uD83D\uDD25"}</div>
          <div className="text-2xl font-black text-white mt-1">{streak}</div>
          <div className="text-xs text-slate-400">Tage Streak</div>
        </div>

        {/* Level */}
        <div className="rounded-2xl p-4 text-center"
             style={{ background: "rgba(139,92,246,0.1)", border: "1px solid rgba(139,92,246,0.3)" }}>
          <div className="text-3xl">{"\u2B50"}</div>
          <div className="text-2xl font-black text-white mt-1">{totalCorrect}</div>
          <div className="text-xs text-slate-400">Richtige Antworten</div>
        </div>

        {/* Tages-Quiz */}
        <button
          onClick={() => onNavigate("quiz")}
          className="col-span-2 rounded-2xl p-4 flex items-center gap-4 transition-all hover:-translate-y-0.5"
          style={{ background: "rgba(6,182,212,0.1)", border: "1px solid rgba(6,182,212,0.3)" }}>
          <div className="text-3xl">{"\u26A1"}</div>
          <div>
            <div className="font-bold text-white">Tages-Quiz</div>
            <div className="text-sm text-slate-400">
              {totalQuizzes} Quizzes absolviert
            </div>
          </div>
          <div className="ml-auto text-cyan-400 text-xl">{"\u2192"}</div>
        </button>

        {/* Statistiken */}
        <div className="col-span-2 grid grid-cols-4 gap-2 rounded-2xl p-4"
             style={{ background: "rgba(30,41,59,0.6)", border: "1px solid rgba(99,102,241,0.2)" }}>
          {[
            { icon: "\uD83D\uDCAC", zahl: totalSessions, label: "Chats" },
            { icon: "\uD83C\uDFAF", zahl: totalQuizzes, label: "Quizze" },
            { icon: "\u2705", zahl: `${correctPercent}%`, label: "Richtig" },
            { icon: "\uD83D\uDD25", zahl: streak, label: "Streak" },
          ].map(({ icon, zahl, label }) => (
            <div key={label} className="text-center">
              <div className="text-xl">{icon}</div>
              <div className="text-lg font-bold text-white">{zahl}</div>
              <div className="text-xs text-slate-400">{label}</div>
            </div>
          ))}
        </div>

        {/* Scanner (Pro) */}
        <button
          onClick={() => tier === "free" ? onNavigate("pricing") : onNavigate("scanner")}
          className="rounded-2xl p-4 text-center transition-all hover:-translate-y-0.5 relative"
          style={{ background: "rgba(139,92,246,0.1)", border: "1px solid rgba(139,92,246,0.3)" }}>
          {tier === "free" && (
            <div className="absolute top-2 right-2 text-xs px-1.5 py-0.5 rounded-md font-bold"
                 style={{ background: "rgba(139,92,246,0.3)", color: "#a78bfa" }}>PRO</div>
          )}
          <div className="text-2xl">{"\uD83D\uDCF7"}</div>
          <div className="text-xs font-bold text-white mt-1">Scanner</div>
        </button>

        {/* Turnier */}
        <button
          onClick={() => onNavigate("turnier")}
          className="rounded-2xl p-4 text-center transition-all hover:-translate-y-0.5"
          style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)" }}>
          <div className="text-2xl">{"\uD83C\uDFC6"}</div>
          <div className="text-xs font-bold text-white mt-1">Turnier</div>
          <div className="text-xs text-cyan-400">Live!</div>
        </button>

        {/* Karteikarten */}
        <button
          onClick={() => onNavigate("flashcards")}
          className="col-span-2 rounded-2xl p-4 flex items-center gap-3 transition-all hover:-translate-y-0.5"
          style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)" }}>
          <div className="text-2xl">{"\uD83D\uDCDA"}</div>
          <div>
            <div className="font-bold text-white text-sm">Karteikarten</div>
            <div className="text-xs text-slate-400">Spaced Repetition lernen</div>
          </div>
        </button>

        {/* Gamification */}
        <button
          onClick={() => onNavigate("gamification")}
          className="col-span-2 rounded-2xl p-4 flex items-center gap-3 transition-all hover:-translate-y-0.5"
          style={{ background: "rgba(6,182,212,0.08)", border: "1px solid rgba(6,182,212,0.2)" }}>
          <div className="text-2xl">{"\uD83C\uDFAE"}</div>
          <div>
            <div className="font-bold text-white text-sm">Gamification</div>
            <div className="text-xs text-slate-400">XP, Badges & Achievements</div>
          </div>
        </button>

      </div>

      {/* PRO UPGRADE BANNER (nur für Free-User) */}
      {tier === "free" && (
        <div className="mt-4 rounded-2xl p-4 flex items-center gap-4 cursor-pointer"
             style={{
               background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))",
               border: "1px solid rgba(99,102,241,0.4)",
               boxShadow: "0 0 20px rgba(99,102,241,0.1)"
             }}
             onClick={() => onNavigate("pricing")}>
          <div className="text-3xl">{"\uD83D\uDE80"}</div>
          <div className="flex-1">
            <div className="font-bold text-white">Upgrade auf Pro — 4,99€/Monat</div>
            <div className="text-sm text-slate-400">
              Schulbuch-Scanner, Multi-Step KI, alle 32 Fächer + unbegrenzte Quizze
            </div>
          </div>
          <div className="px-4 py-2 rounded-xl font-bold text-sm text-white shrink-0"
               style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
            Jetzt upgraden {"\u2192"}
          </div>
        </div>
      )}

    </div>
  );
}
