import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { learningApi, type Progress } from "../services/api";
import { useAuthStore } from "../stores/authStore";
import BentoTile from "../components/BentoTile";
import LumnosOrb from "../components/LumnosOrb";
import BlindSpotHeatmap from "../components/BlindSpotHeatmap";
import { APPLE_EASE, staggerContainer } from "../lib/animations";

interface DashboardProps {
 onNavigate: (page: string) => void;
}

export default function DashboardPage({ onNavigate }: DashboardProps) {
 const { user } = useAuthStore();
 const [progress, setProgress] = useState<Progress | null>(null);
 const [loading, setLoading] = useState(true);
 const [blindSpots, setBlindSpots] = useState<{ fach: string; blind_spots: number }[]>([]);

 useEffect(() => {
 loadProgress();
 loadBlindSpots();
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

 const loadBlindSpots = async () => {
 try {
 const API = import.meta.env.VITE_API_URL || "";
 const res = await fetch(`${API}/api/quiz/blind-spots`, {
 headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
 });
 if (res.ok) {
 const data = await res.json();
 setBlindSpots(data.blind_spots || []);
 }
 } catch { /* silent */ }
 };

 if (loading) {
 return (
 <div className="flex items-center justify-center h-full min-h-screen" style={{ background: "var(--lumnos-bg)" }}>
 <LumnosOrb size="lg" isTyping />
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
 const userXp = (user as Record<string, unknown>)?.xp as number || 0;
 const userLevel = (user as Record<string, unknown>)?.level as number || 1;

 return (
 <motion.div
 initial={{ opacity: 0, y: 12 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -8 }}
 transition={{ duration: 0.35, ease: "easeOut" }}
 className="min-h-screen p-4 md:p-6"
 style={{
 background: "var(--lumnos-bg)",
 backgroundImage:
 "linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px)," +
 "linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px)",
 backgroundSize: "32px 32px",
 }}>

 {/* Header */}
 <motion.div
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 className="flex items-center justify-between mb-5">
 <div>
 <h1 className="text-2xl font-black text-white">
 Hey {userName}! {"\u2726"}
 </h1>
 <p className="text-slate-400 text-sm">
 {streak > 0
 ? `\uD83D\uDD25 ${streak} Tage Streak`
 : "Bereit zu lernen?"}
 </p>
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
 </motion.div>

 {/* ORB + BENTO GRID */}
 <motion.div
 variants={staggerContainer}
 initial="initial"
 animate="animate"
 className="grid grid-cols-2 md:grid-cols-4 gap-3"
 style={{ perspective: "1000px" }}>

 {/* KI-Tutor Haupt-Kachel mit Orb */}
 <BentoTile col={2} row={2} color="#6366f1"
 onClick={() => onNavigate("chat")} glow delay={0}>
 <div className="h-full flex flex-col items-center
 justify-center gap-4 p-6 min-h-[200px]">
 <LumnosOrb size="lg" />
 <div className="text-center">
 <h2 className="text-xl font-black text-white">
 KI-Tutor
 </h2>
 <p className="text-slate-400 text-sm">
 Frag mich alles
 </p>
 </div>
 <motion.div
 whileHover={{ scale: 1.05 }}
 className="px-5 py-2 rounded-xl font-bold text-sm text-white"
 style={{
 background: "linear-gradient(135deg,#6366f1,#8b5cf6)"
 }}>
 Chat starten {"\u2192"}
 </motion.div>
 </div>
 </BentoTile>

 {/* Streak */}
 <BentoTile color="#f97316" delay={0.1}>
 <div className="p-4 text-center h-full flex flex-col
 items-center justify-center">
 <motion.div
 animate={{ scale: [1, 1.2, 1] }}
 transition={{ duration: 1.5, repeat: Infinity }}
 className="text-3xl">{"\uD83D\uDD25"}</motion.div>
 <div className="text-3xl font-black text-white">
 {streak}
 </div>
 <div className="text-xs text-slate-400">Streak</div>
 </div>
 </BentoTile>

 {/* XP */}
 <BentoTile color="#8b5cf6" delay={0.15}>
 <div className="p-4 text-center h-full flex flex-col
 items-center justify-center">
 <div className="text-3xl">{"\u2B50"}</div>
 <div className="text-2xl font-black text-white">
 Lv.{userLevel}
 </div>
 <div className="text-xs text-slate-400">
 {userXp} XP
 </div>
 <div className="mt-2 h-1.5 rounded-full w-full overflow-hidden relative"
 style={{ background: "rgba(var(--surface-rgb),0.6)" }}>
 <motion.div
 initial={{ width: 0 }}
 animate={{
 width: `${(userXp % 1000) / 10}%`
 }}
 transition={{ duration: 1.2, ease: APPLE_EASE, delay: 0.3 }}
 className="h-full rounded-full relative overflow-hidden"
 style={{
 background: "linear-gradient(90deg, #8b5cf6, #a78bfa)"
 }}>
 {/* Shimmer effect */}
 <div className="absolute inset-0 animate-shimmer" style={{
 background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)",
 width: "50%"
 }} />
 </motion.div>
 </div>
 </div>
 </BentoTile>

 {/* Quiz */}
 <BentoTile col={2} color="#06b6d4"
 onClick={() => onNavigate("quiz")} delay={0.2}>
 <div className="flex items-center gap-4 p-4 h-full">
 <motion.div
 animate={{ rotate: [0, 10, -10, 0] }}
 transition={{ duration: 2, repeat: Infinity }}
 className="text-4xl">{"\u26A1"}</motion.div>
 <div>
 <div className="font-bold text-white">Tages-Quiz</div>
 <div className="text-sm text-slate-400">
 {totalQuizzes} Quizze absolviert
 </div>
 </div>
 <div className="ml-auto text-2xl text-cyan-400">{"\u2192"}</div>
 </div>
 </BentoTile>

 {/* Stats */}
 <BentoTile col={4} color="#1e293b" delay={0.25}>
 <div className="grid grid-cols-4 gap-0 p-4">
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
 transition={{ delay: 0.3 + i * 0.08 }}
 className="text-center">
 <div className="text-xl">{icon}</div>
 <div className="text-lg font-black text-white">
 {wert}
 </div>
 <div className="text-xs text-slate-400">{label}</div>
 </motion.div>
 ))}
 </div>
 </BentoTile>

 {/* Scanner (Pro) */}
 <BentoTile color="#8b5cf6" delay={0.3}
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
 <BentoTile color="#f59e0b" delay={0.35}
 onClick={() => onNavigate("turnier")}>
 <div className="p-4 text-center h-full flex flex-col items-center justify-center">
 <div className="text-2xl">{"\uD83C\uDFC6"}</div>
 <div className="text-xs font-bold text-white mt-1">Turnier</div>
 <div className="text-xs text-cyan-400">Live!</div>
 </div>
 </BentoTile>

 {/* Karteikarten */}
 <BentoTile col={2} color="#6366f1" delay={0.4}
 onClick={() => onNavigate("flashcards")}>
 <div className="flex items-center gap-3 p-4 h-full">
 <div className="text-2xl">{"\uD83D\uDCDA"}</div>
 <div>
 <div className="font-bold text-white text-sm">Karteikarten</div>
 <div className="text-xs text-slate-400">Spaced Repetition lernen</div>
 </div>
 </div>
 </BentoTile>

 {/* Gamification */}
 <BentoTile col={2} color="#06b6d4" delay={0.45}
 onClick={() => onNavigate("gamification")}>
 <div className="flex items-center gap-3 p-4 h-full">
 <div className="text-2xl">{"\uD83C\uDFAE"}</div>
 <div>
 <div className="font-bold text-white text-sm">Gamification</div>
 <div className="text-xs text-slate-400">XP, Badges & Achievements</div>
 </div>
 </div>
 </BentoTile>

 </motion.div>

 {/* Blind-Spot Heatmap */}
 {blindSpots.length > 0 && (
 <div className="mt-4">
 <BlindSpotHeatmap fächer={blindSpots} />
 </div>
 )}

 {/* Upgrade-Banner */}
 {tier === "free" && (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.5 }}
 whileHover={{ scale: 1.01 }}
 className="mt-4 rounded-2xl p-5 flex items-center gap-4 cursor-pointer"
 style={{
 background: "linear-gradient(135deg,rgba(99,102,241,0.2),rgba(139,92,246,0.15))",
 border: "1px solid rgba(99,102,241,0.4)",
 boxShadow: "0 0 25px rgba(99,102,241,0.15)",
 }}
 onClick={() => onNavigate("pricing")}>
 <div className="text-4xl">{"\uD83D\uDE80"}</div>
 <div className="flex-1">
 <div className="font-black text-white">
 Upgrade auf Pro — 4,99€/Monat
 </div>
 <div className="text-slate-400 text-sm">
 Schulbuch-Scanner · alle 32 Fächer · unbegrenzte Chats · Multi-Step KI
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
