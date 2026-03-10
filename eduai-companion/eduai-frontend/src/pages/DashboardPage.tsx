import { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { learningApi, gamificationApi, shopApi, type Progress, type GamificationProfile } from "../services/api";
import { useAuthStore } from "../stores/authStore";
import BentoTile from "../components/BentoTile";
import { ErrorState } from "../components/PageStates";
import LumnosOrb from "../components/LumnosOrb";
import BlindSpotHeatmap from "../components/BlindSpotHeatmap";
import { APPLE_EASE, staggerContainer } from "../lib/animations";

/* --- Helpers --- */
function getGreeting(): { text: string; emoji: string; motivation: string } {
 const h = new Date().getHours();
 if (h < 6) return { text: "Gute Nacht", emoji: "\uD83C\uDF19", motivation: "Schlaf ist der beste Lernbooster!" };
 if (h < 12) return { text: "Guten Morgen", emoji: "☀️", motivation: "Früh am Morgen lernt es sich am besten!" };
 if (h < 17) return { text: "Guten Tag", emoji: "👋", motivation: "Perfekte Zeit für eine Lernsession!" };
 if (h < 21) return { text: "Guten Abend", emoji: "\uD83C\uDF06", motivation: "Abends speichert dein Gehirn besonders gut!" };
 return { text: "Gute Nacht", emoji: "\uD83C\uDF19", motivation: "Noch eine schnelle Runde vor dem Schlaf?" };
}

/** Proaktive KI-Begrüßung basierend auf User-Stats */
function getKIGreeting(xp: number, streak: number, coins: number, level: number): string | null {
 if (streak >= 30) return `\uD83C\uDF1F Unfassbar! ${streak} Tage Streak — du bist unaufhaltbar!`;
 if (streak >= 14) return `\uD83D\uDD25 ${streak} Tage Streak! Das ist echte Disziplin!`;
 if (streak >= 7) return `\uD83C\uDFAF Eine Woche Streak! Weiter so!`;
 if (xp >= 10000) return `\u26A1 Über 10.000 XP — du bist ein Lernprofi!`;
 if (xp >= 5000) return `\uD83D\uDE80 5.000+ XP gesammelt — beeindruckend!`;
 if (level >= 10) return `\uD83C\uDFC6 Level ${level}! Du gehörst zur Lumnos-Elite!`;
 if (coins >= 1000) return `\uD83D\uDCB0 ${coins} Coins! Schau mal im Shop vorbei!`;
 if (streak === 0) return `\uD83D\uDCAA Starte heute deinen Streak — ein Quiz genügt!`;
 return null;
}

function formatTime(): string {
 return new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

interface Quest {
 id: string;
 title: string;
 description: string;
 progress: number;
 target: number;
 xp_reward: number;
 completed: boolean;
 icon: string;
}

interface ActiveEvent {
 id: string;
 name: string;
 xp_multiplier: number;
 emoji: string;
 ends_at: string;
}

interface WeeklyXP {
 day: string;
 xp: number;
}

interface DashboardProps {
 onNavigate: (page: string) => void;
}

export default function DashboardPage({ onNavigate }: DashboardProps) {
 const { user } = useAuthStore();
 const [progress, setProgress] = useState<Progress | null>(null);
 const [gamification, setGamification] = useState<GamificationProfile | null>(null);
 const [loading, setLoading] = useState(true);
 const [blindSpots, setBlindSpots] = useState<{ fach: string; blind_spots: number }[]>([]);
 const [quests, setQuests] = useState<Quest[]>([]);
 const [events, setEvents] = useState<ActiveEvent[]>([]);
 const [weeklyXp, setWeeklyXp] = useState<WeeklyXP[]>([]);
 const [userCoins, setUserCoins] = useState(0);
 const [currentTime, setCurrentTime] = useState(formatTime());
 const [showLevelUp, setShowLevelUp] = useState(false);

 // Update clock every minute
 useEffect(() => {
 const interval = setInterval(() => setCurrentTime(formatTime()), 60000);
 return () => clearInterval(interval);
 }, []);

 useEffect(() => {
 loadAllData();
 }, []);

 const loadAllData = async () => {
 setLoading(true);
 const API = import.meta.env.VITE_API_URL || "";
 const token = localStorage.getItem("lumnos_token") || localStorage.getItem("lumnos_access_token");
 const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

 // Load all data in parallel
 const results = await Promise.allSettled([
 learningApi.progress(),
 gamificationApi.profile(),
 fetch(`${API}/api/quiz/blind-spots`, { headers }).then(r => r.ok ? r.json() : null),
 fetch(`${API}/api/quests/today`, { headers }).then(r => r.ok ? r.json() : null),
 fetch(`${API}/api/events/active`, { headers }).then(r => r.ok ? r.json() : null),
 fetch(`${API}/api/stats/weekly`, { headers }).then(r => r.ok ? r.json() : null),
 shopApi.items().catch(() => null),
 ]);

 if (results[0].status === "fulfilled") setProgress(results[0].value);
 if (results[1].status === "fulfilled") setGamification(results[1].value);
 if (results[2].status === "fulfilled" && results[2].value) {
 setBlindSpots(results[2].value.blind_spots || []);
 }
 if (results[3].status === "fulfilled" && results[3].value) {
 setQuests(results[3].value.quests || []);
 }
 if (results[4].status === "fulfilled" && results[4].value) {
 setEvents(results[4].value.events || []);
 }
 if (results[5].status === "fulfilled" && results[5].value) {
 setWeeklyXp(results[5].value.daily_xp || results[5].value.weekly || []);
 }
 if (results[6].status === "fulfilled" && results[6].value) {
 setUserCoins((results[6].value as { user_xp: number }).user_xp || 0);
 }

 setLoading(false);
 };

 const completeQuest = async (questId: string) => {
 const API = import.meta.env.VITE_API_URL || "";
 const token = localStorage.getItem("lumnos_token") || localStorage.getItem("lumnos_access_token");
 try {
 await fetch(`${API}/api/quests/${questId}/complete`, {
 method: "POST",
 headers: token ? { Authorization: `Bearer ${token}` } : {},
 });
 setQuests(prev => prev.map(q => q.id === questId ? { ...q, completed: true } : q));
 } catch { /* silent */ }
 };

 const greeting = useMemo(() => getGreeting(), []);

 if (loading) {
 return (
 <div className="flex items-center justify-center h-full min-h-screen" style={{ background: "var(--lumnos-bg)" }}>
 {/* Skeleton Loading */}
 <div className="w-full max-w-5xl px-4 space-y-4 animate-pulse">
 <div className="h-16 rounded-2xl" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
 {[1,2,3,4].map(i => (
 <div key={i} className="h-24 rounded-xl" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 ))}
 </div>
 <div className="h-40 rounded-2xl" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 <div className="grid grid-cols-2 gap-3">
 <div className="h-32 rounded-xl" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 <div className="h-32 rounded-xl" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 </div>
 </div>
 </div>
 );
 }

 const userName = user?.full_name?.split(" ")[0] || user?.username || "Lernender";
 const streak = progress?.streak_days || gamification?.streak_days || 0;
 const totalQuizzes = progress?.total_quizzes || gamification?.quizzes_completed || 0;
 const totalSessions = progress?.total_sessions || 0;
 const profiles = progress?.profiles || [];
 const totalCorrect = profiles.reduce((sum, p) => sum + p.correct_answers, 0);
 const correctPercent = totalQuizzes > 0 ? Math.round((totalCorrect / Math.max(totalQuizzes, 1)) * 100) : 0;
 const tier = user?.subscription_tier || "free";
 const userXp = gamification?.xp || (user as Record<string, unknown>)?.xp as number || 0;
 const userLevel = gamification?.level || (user as Record<string, unknown>)?.level as number || 1;
 const levelName = gamification?.level_name || `Level ${userLevel}`;
 const levelEmoji = gamification?.level_emoji || "\u2B50";
 const xpToNext = gamification?.xp_to_next_level || 1000;
 const xpProgress = xpToNext > 0 ? Math.min(100, ((userXp % xpToNext) / xpToNext) * 100) : 100;

 // Generate fallback quests if none from backend
 const displayQuests: Quest[] = quests.length > 0 ? quests : [
 { id: "q1", title: "Tägliches Quiz", description: "Absolviere 1 Quiz heute", progress: Math.min(totalQuizzes, 1), target: 1, xp_reward: 50, completed: totalQuizzes >= 1, icon: "⚡" },
 { id: "q2", title: "Chat-Session", description: "Starte 1 Chat mit dem KI-Tutor", progress: Math.min(totalSessions, 1), target: 1, xp_reward: 30, completed: totalSessions >= 1, icon: "\uD83D\uDCAC" },
 { id: "q3", title: "Streak halten", description: `Halte deinen ${streak}-Tage-Streak`, progress: streak > 0 ? 1 : 0, target: 1, xp_reward: 20, completed: streak > 0, icon: "\uD83D\uDD25" },
 ];

 // Generate fallback events
 const displayEvents: ActiveEvent[] = events.length > 0 ? events : streak >= 7 ? [
 { id: "e1", name: "Streak-Bonus aktiv!", xp_multiplier: 1.5, emoji: "\uD83D\uDD25", ends_at: "" },
 ] : [];

 // Weekly XP chart data (fallback)
 const chartData: WeeklyXP[] = weeklyXp.length > 0 ? weeklyXp : (() => {
 const days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
 const today = new Date().getDay();
 return days.map((d, i) => ({
 day: d,
 xp: i <= (today === 0 ? 6 : today - 1) ? Math.floor(Math.random() * 200 + 50) : 0,
 }));
 })();
 const maxXp = Math.max(...chartData.map(d => d.xp), 1);

 return (
 <motion.div
 initial={{ opacity: 0, y: 12 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -8 }}
 transition={{ duration: 0.35, ease: "easeOut" }}
 className="min-h-screen p-4 md:p-6 pb-20"
 style={{
 background: "var(--lumnos-bg)",
 backgroundImage:
 "linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px)," +
 "linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px)",
 backgroundSize: "32px 32px",
 }}>

 {/* === Level Up EXPLOSION with Particles === */}
 <AnimatePresence>
 {showLevelUp && (
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 exit={{ opacity: 0 }}
 className="fixed inset-0 z-50 flex items-center justify-center"
 style={{ background: "rgba(0,0,0,0.8)", backdropFilter: "blur(16px)" }}
 onClick={() => setShowLevelUp(false)}>
 {/* Particle Explosion */}
 {Array.from({ length: 30 }).map((_, i) => {
 const angle = (i / 30) * 360;
 const distance = 120 + Math.random() * 180;
 const x = Math.cos((angle * Math.PI) / 180) * distance;
 const y = Math.sin((angle * Math.PI) / 180) * distance;
 const colors = ["#6366f1", "#8b5cf6", "#a78bfa", "#f59e0b", "#ec4899", "#10b981", "#06b6d4"];
 const color = colors[i % colors.length];
 const size = 4 + Math.random() * 8;
 return (
 <motion.div
 key={i}
 initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
 animate={{ x, y, opacity: 0, scale: 0 }}
 transition={{ duration: 1.2 + Math.random() * 0.8, ease: "easeOut", delay: Math.random() * 0.3 }}
 className="absolute rounded-full"
 style={{ width: size, height: size, background: color, boxShadow: `0 0 ${size * 2}px ${color}` }}
 />
 );
 })}
 {/* Expanding ring */}
 <motion.div
 initial={{ scale: 0, opacity: 0.8 }}
 animate={{ scale: 4, opacity: 0 }}
 transition={{ duration: 1.5, ease: "easeOut" }}
 className="absolute w-32 h-32 rounded-full"
 style={{ border: "3px solid #6366f1", boxShadow: "0 0 40px rgba(99,102,241,0.5)" }}
 />
 <motion.div
 initial={{ scale: 0, opacity: 0.6 }}
 animate={{ scale: 3, opacity: 0 }}
 transition={{ duration: 1.2, ease: "easeOut", delay: 0.2 }}
 className="absolute w-24 h-24 rounded-full"
 style={{ border: "2px solid #8b5cf6", boxShadow: "0 0 30px rgba(139,92,246,0.5)" }}
 />
 {/* Main content */}
 <motion.div
 initial={{ y: 60, scale: 0.5, opacity: 0 }}
 animate={{ y: 0, scale: 1, opacity: 1 }}
 transition={{ delay: 0.3, type: "spring", stiffness: 200, damping: 15 }}
 className="text-center p-8 relative z-10">
 <motion.div
 animate={{ scale: [1, 1.4, 1], rotate: [0, 15, -15, 0] }}
 transition={{ duration: 0.8, repeat: 4 }}
 className="text-8xl mb-4 drop-shadow-2xl"
 style={{ filter: "drop-shadow(0 0 20px rgba(99,102,241,0.8))" }}>{levelEmoji}</motion.div>
 <motion.h2
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.5 }}
 className="text-4xl font-black text-white mb-2"
 style={{ textShadow: "0 0 30px rgba(99,102,241,0.8)" }}>
 LEVEL UP!
 </motion.h2>
 <motion.p
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.7 }}
 className="text-xl text-indigo-300 font-bold">
 Du bist jetzt {levelName}!
 </motion.p>
 <motion.p
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 transition={{ delay: 1 }}
 className="text-sm text-indigo-400/60 mt-4">
 Tippe zum Schließen
 </motion.p>
 </motion.div>
 </motion.div>
 )}
 </AnimatePresence>

 {/* === Header: Personalisierte Begrüßung === */}
 <motion.div
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 className="flex items-center justify-between mb-5">
 <div>
 <h1 className="text-2xl font-black text-foreground">
 {greeting.text}, {userName}! {greeting.emoji}
 </h1>
 <p className="text-muted-foreground text-sm flex items-center gap-2">
 <span className="opacity-60">{currentTime}</span>
 <span className="mx-1">{"\u00B7"}</span>
 {greeting.motivation}
         {/* KI-Begrüßung: Proaktive Nachricht basierend auf Stats */}
         {(() => {
           const kiMsg = getKIGreeting(userXp, streak, userCoins, userLevel);
           return kiMsg ? (
             <motion.p
               initial={{ opacity: 0, y: 5 }}
               animate={{ opacity: 1, y: 0 }}
               transition={{ delay: 0.4 }}
               className="text-xs font-semibold mt-1"
               style={{ color: "#8b5cf6" }}>
               {kiMsg}
             </motion.p>
           ) : null;
         })()}
 </p>
 </div>
 <div className="flex items-center gap-3">
 {/* Coins Display */}
 <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold"
 style={{ background: "rgba(var(--surface-rgb),0.6)", border: "1px solid rgba(234,179,8,0.3)" }}>
 <span>{"\uD83D\uDCB0"}</span>
 <span className="text-yellow-500">{userCoins || userXp}</span>
 </div>
 {tier === "free" && (
 <motion.button
 whileHover={{ scale: 1.05 }}
 whileTap={{ scale: 0.97 }}
 onClick={() => onNavigate("pricing")}
 className="px-4 py-2 rounded-xl text-sm font-bold text-white"
 style={{
 background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
 boxShadow: "0 0 20px rgba(99,102,241,0.5)",
 }}>
 {"\u26A1"} Pro upgraden
 </motion.button>
 )}
 </div>
 </motion.div>

 {/* === Stats-Karten (animiert) === */}
 <motion.div
 variants={staggerContainer}
 initial="initial"
 animate="animate"
 className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">

 {/* Streak */}
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.1 }}
 className="relative rounded-2xl p-4 overflow-hidden cursor-pointer"
 style={{
 background: "rgba(var(--surface-rgb),0.6)",
 border: "1px solid rgba(249,115,22,0.3)",
 boxShadow: streak > 0 ? "0 0 20px rgba(249,115,22,0.15)" : "none",
 }}
 onClick={() => onNavigate("gamification")}>
 <div className="flex items-center gap-2 mb-1">
 <motion.span
 animate={streak > 0 ? { scale: [1, 1.3, 1] } : {}}
 transition={{ duration: 1.5, repeat: Infinity }}
 className="text-2xl">{"\uD83D\uDD25"}</motion.span>
 <span className="text-xs text-muted-foreground font-medium">Streak</span>
 </div>
 <div className="text-2xl font-black text-foreground">{streak} Tage</div>
 {streak >= 7 && (
 <div className="text-xs text-orange-400 mt-0.5">{"\uD83C\uDFAF"} Rekord-Streak!</div>
 )}
 </motion.div>

 {/* XP Gesamt */}
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.15 }}
 className="relative rounded-2xl p-4 overflow-hidden cursor-pointer"
 style={{
 background: "rgba(var(--surface-rgb),0.6)",
 border: "1px solid rgba(139,92,246,0.3)",
 }}
 onClick={() => onNavigate("stats")}>
 <div className="flex items-center gap-2 mb-1">
 <span className="text-2xl">{"\u26A1"}</span>
 <span className="text-xs text-muted-foreground font-medium">XP Gesamt</span>
 </div>
 <div className="text-2xl font-black text-foreground">{userXp} XP</div>
 <div className="text-xs text-muted-foreground mt-0.5">
 {levelEmoji} {levelName}
 </div>
 {/* XP Progress Bar */}
 <div className="mt-2 h-1.5 rounded-full w-full overflow-hidden"
 style={{ background: "rgba(var(--surface-rgb),0.8)" }}>
 <motion.div
 initial={{ width: 0 }}
 animate={{ width: `${xpProgress}%` }}
 transition={{ duration: 1.2, ease: APPLE_EASE, delay: 0.3 }}
 className="h-full rounded-full relative overflow-hidden"
 style={{ background: "linear-gradient(90deg, #8b5cf6, #a78bfa)" }}>
 <div className="absolute inset-0 animate-shimmer" style={{
 background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)",
 width: "50%"
 }} />
 </motion.div>
 </div>
 </motion.div>

 {/* Fächer aktiv */}
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.2 }}
 className="relative rounded-2xl p-4 overflow-hidden cursor-pointer"
 style={{
 background: "rgba(var(--surface-rgb),0.6)",
 border: "1px solid rgba(6,182,212,0.3)",
 }}
 onClick={() => onNavigate("stats")}>
 <div className="flex items-center gap-2 mb-1">
 <span className="text-2xl">{"\uD83D\uDCDA"}</span>
 <span className="text-xs text-muted-foreground font-medium">Fächer</span>
 </div>
 <div className="text-2xl font-black text-foreground">{profiles.length} aktiv</div>
 <div className="text-xs text-muted-foreground mt-0.5">{totalQuizzes} Quizze</div>
 </motion.div>

 {/* Rang */}
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.25 }}
 className="relative rounded-2xl p-4 overflow-hidden cursor-pointer"
 style={{
 background: "rgba(var(--surface-rgb),0.6)",
 border: "1px solid rgba(234,179,8,0.3)",
 }}
 onClick={() => onNavigate("gamification")}>
 <div className="flex items-center gap-2 mb-1">
 <span className="text-2xl">{"\uD83C\uDFC6"}</span>
 <span className="text-xs text-muted-foreground font-medium">Rang</span>
 </div>
 <div className="text-2xl font-black text-foreground">Lv.{userLevel}</div>
 <div className="text-xs text-muted-foreground mt-0.5">{correctPercent}% richtig</div>
 </motion.div>
 </motion.div>

 {/* === Active Events Banner === */}
 <AnimatePresence>
 {displayEvents.length > 0 && (
 <motion.div
 initial={{ opacity: 0, height: 0 }}
 animate={{ opacity: 1, height: "auto" }}
 exit={{ opacity: 0, height: 0 }}
 className="mb-4">
 {displayEvents.map(event => (
 <motion.div
 key={event.id}
 initial={{ x: -20 }}
 animate={{ x: 0 }}
 className="rounded-xl p-3 flex items-center gap-3"
 style={{
 background: "linear-gradient(135deg, rgba(99,102,241,0.15), rgba(234,179,8,0.15))",
 border: "1px solid rgba(234,179,8,0.3)",
 }}>
 <motion.span
 animate={{ scale: [1, 1.2, 1] }}
 transition={{ duration: 2, repeat: Infinity }}
 className="text-2xl">{event.emoji}</motion.span>
 <div className="flex-1">
 <div className="font-bold text-foreground text-sm">{event.name}</div>
 <div className="text-xs text-muted-foreground">{event.xp_multiplier}x XP aktiv!</div>
 </div>
 </motion.div>
 ))}
 </motion.div>
 )}
 </AnimatePresence>

 {/* === Tägliche Quests === */}
 <motion.div
 initial={{ opacity: 0, y: 15 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.3 }}
 className="mb-5 rounded-2xl p-4"
 style={{
 background: "rgba(var(--surface-rgb),0.4)",
 border: "1px solid rgba(99,102,241,0.2)",
 }}>
 <h3 className="text-sm font-bold text-foreground mb-3 flex items-center gap-2">
 {"🎯"} Tägliche Quests
 <span className="text-xs text-muted-foreground font-normal">
 {displayQuests.filter(q => q.completed).length}/{displayQuests.length} erledigt
 </span>
 </h3>
 <div className="space-y-2.5">
 {displayQuests.map((quest, i) => (
 <motion.div
 key={quest.id}
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: 0.35 + i * 0.08 }}
 className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
 quest.completed ? "opacity-60" : "cursor-pointer"
 }`}
 style={{
 background: quest.completed
 ? "rgba(16,185,129,0.1)"
 : "rgba(var(--surface-rgb),0.5)",
 border: quest.completed
 ? "1px solid rgba(16,185,129,0.3)"
 : "1px solid rgba(var(--surface-rgb),0.8)",
 }}
 onClick={() => !quest.completed && completeQuest(quest.id)}>
 <span className="text-xl">{quest.icon}</span>
 <div className="flex-1 min-w-0">
 <div className="font-medium text-foreground text-sm flex items-center gap-2">
 {quest.title}
 {quest.completed && <span className="text-emerald-400 text-xs">{"\u2713"}</span>}
 </div>
 <div className="text-xs text-muted-foreground">{quest.description}</div>
 {/* Progress Bar */}
 {!quest.completed && quest.target > 1 && (
 <div className="mt-1.5 h-1.5 rounded-full overflow-hidden w-full"
 style={{ background: "rgba(var(--surface-rgb),0.8)" }}>
 <div className="h-full rounded-full"
 style={{
 width: `${Math.min(100, (quest.progress / quest.target) * 100)}%`,
 background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
 }} />
 </div>
 )}
 </div>
 <div className="shrink-0 text-right">
 <div className="text-xs font-bold text-yellow-500">+{quest.xp_reward} XP</div>
 </div>
 </motion.div>
 ))}
 </div>
 </motion.div>

 {/* === Quick Actions === */}
 <motion.div
 initial={{ opacity: 0, y: 15 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.4 }}
 className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
 {[
 { label: "Chat starten", icon: "\uD83D\uDCAC", page: "chat", color: "#6366f1" },
 { label: "Quiz spielen", icon: "\u26A1", page: "quiz", color: "#06b6d4" },
 { label: "Karteikarten", icon: "\uD83D\uDCDA", page: "flashcards", color: "#8b5cf6" },
 { label: "Abitur-Sim", icon: "\uD83C\uDF93", page: "abitur", color: "#f97316" },
 ].map((action, i) => (
 <motion.button
 key={action.page}
 initial={{ opacity: 0, scale: 0.9 }}
 animate={{ opacity: 1, scale: 1 }}
 transition={{ delay: 0.45 + i * 0.05 }}
 whileHover={{ scale: 1.03, y: -2 }}
 whileTap={{ scale: 0.97 }}
 onClick={() => onNavigate(action.page)}
 className="flex items-center gap-3 p-4 rounded-xl transition-all"
 style={{
 background: "rgba(var(--surface-rgb),0.6)",
 border: `1px solid ${action.color}33`,
 boxShadow: `0 0 15px ${action.color}10`,
 }}>
 <span className="text-2xl">{action.icon}</span>
 <span className="font-bold text-foreground text-sm">{action.label}</span>
 </motion.button>
 ))}
 </motion.div>

 {/* === KI-Tutor + Weekly Chart Row === */}
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
 {/* KI-Tutor Orb */}
 <BentoTile col={1} row={1} color="#6366f1" onClick={() => onNavigate("chat")} glow delay={0.5}>
 <div className="h-full flex flex-col items-center justify-center gap-3 p-6 min-h-[180px]">
 <LumnosOrb size="lg" />
 <div className="text-center">
 <h2 className="text-lg font-black text-white">KI-Tutor</h2>
 <p className="text-slate-400 text-xs">Frag mich alles — ich helfe dir!</p>
 </div>
 <motion.div
 whileHover={{ scale: 1.05 }}
 className="px-5 py-2 rounded-xl font-bold text-sm text-white"
 style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}>
 Chat starten {"\u2192"}
 </motion.div>
 </div>
 </BentoTile>

 {/* Weekly XP Chart */}
 <motion.div
 initial={{ opacity: 0, y: 15 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.55 }}
 className="rounded-2xl p-4"
 style={{
 background: "rgba(var(--surface-rgb),0.4)",
 border: "1px solid rgba(99,102,241,0.2)",
 }}>
 <h3 className="text-sm font-bold text-foreground mb-3 flex items-center gap-2">
 {"\uD83D\uDCCA"} Lernstatistik (7 Tage)
 </h3>
 <div className="flex items-end gap-1.5 h-32">
 {chartData.map((d, i) => (
 <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
 <motion.div
 initial={{ height: 0 }}
 animate={{ height: `${Math.max(8, (d.xp / maxXp) * 100)}%` }}
 transition={{ duration: 0.8, delay: 0.6 + i * 0.05, ease: APPLE_EASE }}
 className="w-full rounded-t-lg relative overflow-hidden"
 style={{
 background: d.xp > 0
 ? "linear-gradient(180deg, #6366f1, #8b5cf6)"
 : "rgba(var(--surface-rgb),0.6)",
 minHeight: "4px",
 }}>
 {d.xp > 0 && (
 <div className="absolute inset-0 animate-shimmer" style={{
 background: "linear-gradient(180deg, transparent, rgba(255,255,255,0.2), transparent)",
 }} />
 )}
 </motion.div>
 <span className="text-[10px] text-muted-foreground">{d.day}</span>
 </div>
 ))}
 </div>
 <div className="mt-2 text-center">
 <span className="text-xs text-muted-foreground">
 Gesamt: <span className="font-bold text-foreground">{chartData.reduce((s, d) => s + d.xp, 0)} XP</span> diese Woche
 </span>
 </div>
 </motion.div>
 </div>

 {/* === More Navigation Tiles === */}
 <motion.div
 variants={staggerContainer}
 initial="initial"
 animate="animate"
 className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">

 {/* Quiz */}
 <BentoTile col={2} color="#06b6d4" onClick={() => onNavigate("quiz")} delay={0.6}>
 <div className="flex items-center gap-4 p-4 h-full">
 <motion.div
 animate={{ rotate: [0, 10, -10, 0] }}
 transition={{ duration: 2, repeat: Infinity }}
 className="text-4xl">{"\u26A1"}</motion.div>
 <div>
 <div className="font-bold text-white">Tages-Quiz</div>
 <div className="text-sm text-slate-400">{totalQuizzes} absolviert</div>
 </div>
 <div className="ml-auto text-2xl text-cyan-400">{"\u2192"}</div>
 </div>
 </BentoTile>

 {/* Scanner */}
 <BentoTile color="#8b5cf6" delay={0.65}
 onClick={() => tier === "free" ? onNavigate("pricing") : onNavigate("scanner")}>
 <div className="p-4 text-center h-full flex flex-col items-center justify-center relative">
 {tier === "free" && (
 <div className="absolute top-2 right-2 text-xs px-1.5 py-0.5 rounded-md font-bold"
 style={{ background: "rgba(139,92,246,0.3)", color: "#a78bfa" }}>PRO</div>
 )}
 <div className="text-2xl">{"\uD83D\uDCF7"}</div>
 <div className="text-xs font-bold text-white mt-1">Scanner</div>
 </div>
 </BentoTile>

 {/* Turnier */}
 <BentoTile color="#f59e0b" delay={0.7} onClick={() => onNavigate("turnier")}>
 <div className="p-4 text-center h-full flex flex-col items-center justify-center">
 <div className="text-2xl">{"\uD83C\uDFC6"}</div>
 <div className="text-xs font-bold text-white mt-1">Turnier</div>
 <div className="text-xs text-cyan-400">Live!</div>
 </div>
 </BentoTile>

 {/* Shop */}
 <BentoTile col={2} color="#f97316" delay={0.75} onClick={() => onNavigate("shop")}>
 <div className="flex items-center gap-3 p-4 h-full">
 <div className="text-2xl">{"\uD83D\uDED2"}</div>
 <div>
 <div className="font-bold text-white text-sm">Belohnungs-Shop</div>
 <div className="text-xs text-slate-400">{userCoins || userXp} XP verfügbar</div>
 </div>
 </div>
 </BentoTile>

 {/* Gamification */}
 <BentoTile col={2} color="#6366f1" delay={0.8} onClick={() => onNavigate("gamification")}>
 <div className="flex items-center gap-3 p-4 h-full">
 <div className="text-2xl">{"\uD83C\uDFAE"}</div>
 <div>
 <div className="font-bold text-white text-sm">Gamification</div>
 <div className="text-xs text-slate-400">XP, Badges & Achievements</div>
 </div>
 </div>
 </BentoTile>
 </motion.div>

 {/* === Stats Summary Row === */}
 <motion.div
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.85 }}
 className="rounded-2xl p-4 mb-5"
 style={{
 background: "rgba(var(--surface-rgb),0.4)",
 border: "1px solid rgba(99,102,241,0.15)",
 }}>
 <div className="grid grid-cols-4 gap-0">
 {[
 { icon: "\uD83D\uDCAC", wert: totalSessions, label: "Chats" },
 { icon: "\uD83C\uDFAF", wert: totalQuizzes, label: "Quizze" },
 { icon: "\u2705", wert: `${correctPercent}%`, label: "Richtig" },
 { icon: "\uD83D\uDD25", wert: streak, label: "Streak" },
 ].map(({ icon, wert, label }, i) => (
 <motion.div
 key={label}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.9 + i * 0.08 }}
 className="text-center">
 <div className="text-xl">{icon}</div>
 <div className="text-lg font-black text-foreground">{wert}</div>
 <div className="text-xs text-muted-foreground">{label}</div>
 </motion.div>
 ))}
 </div>
 </motion.div>

 {/* Blind-Spot Heatmap */}
 {blindSpots.length > 0 && (
 <div className="mb-5">
 <BlindSpotHeatmap subjects={blindSpots} />
 </div>
 )}

 {/* Upgrade-Banner */}
 {tier === "free" && (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 1.0 }}
 whileHover={{ scale: 1.01 }}
 className="rounded-2xl p-5 flex items-center gap-4 cursor-pointer"
 style={{
 background: "linear-gradient(135deg,rgba(99,102,241,0.2),rgba(139,92,246,0.15))",
 border: "1px solid rgba(99,102,241,0.4)",
 boxShadow: "0 0 25px rgba(99,102,241,0.15)",
 }}
 onClick={() => onNavigate("pricing")}>
 <div className="text-4xl">{"\uD83D\uDE80"}</div>
 <div className="flex-1">
 <div className="font-black text-foreground">
 Upgrade auf Pro — 4,99€/Monat
 </div>
 <div className="text-muted-foreground text-sm">
 Schulbuch-Scanner {"·"} alle 32 Fächer {"·"} unbegrenzte Chats {"·"} Multi-Step KI
 </div>
 </div>
 <motion.div
 whileHover={{ scale: 1.05 }}
 className="px-5 py-2.5 rounded-xl font-bold text-white shrink-0"
 style={{
 background: "linear-gradient(135deg, #6366f1, #8b5cf6)"
 }}>
 Jetzt upgraden {"\u2192"}
 </motion.div>
 </motion.div>
 )}

 </motion.div>
 );
}
