import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { gamificationApi, type GamificationProfile, type LeaderboardEntry } from "../services/api";
import {
 Trophy, Flame, Star, Medal, Target, Zap, Crown, Users,
 Loader2, TrendingUp, Award
} from "lucide-react";

export default function GamificationPage() {
 const [profile, setProfile] = useState<GamificationProfile | null>(null);
 const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState(false);
 const [tab, setTab] = useState<"overview" | "achievements" | "leaderboard">("overview");

 useEffect(() => {
 loadData();
 }, []);

 const loadData = async () => {
 setLoading(true);
 setError(false);
 try {
 const [profileData, lbData] = await Promise.all([
 gamificationApi.profile(),
 gamificationApi.leaderboard(),
 ]);
 setProfile(profileData);
 setLeaderboard(lbData.leaderboard);
 } catch (err) {
 console.error("Failed to load gamification data:", err);
 setError(true);
 } finally {
 setLoading(false);
 }
 };

 if (loading) {
 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-4">
 <div className="animate-pulse space-y-4">
 <div className="h-10 rounded-xl w-64" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
 {[1,2,3,4].map(i => (
 <div key={i} className="h-24 rounded-xl" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 ))}
 </div>
 <div className="h-16 rounded-xl" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 <div className="h-64 rounded-xl" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 </div>
 </div>
 );
 }

 if (error || !profile) {
 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto text-center py-20">
 <div className="text-4xl mb-4">😔</div>
 <p className="text-foreground font-bold text-lg mb-2">Fehler beim Laden</p>
 <p className="text-muted-foreground mb-4">Gamification-Daten konnten nicht geladen werden.</p>
 <button onClick={loadData} className="px-4 py-2 rounded-xl text-sm font-bold text-white" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
 Erneut versuchen
 </button>
 </div>
 );
 }

 const xpProgress = profile.xp_to_next_level > 0
 ? Math.min(100, ((profile.xp % profile.xp_to_next_level) / profile.xp_to_next_level) * 100)
 : 100;

 const earnedAchievementIds = new Set(profile.achievements.map(a => a.id));

 return (
 <motion.div
 initial={{ opacity: 0, y: 12 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ duration: 0.35 }}
 className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6 pb-20">
 <div>
 <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
 <Trophy className="w-7 h-7 text-yellow-500" /> Gamification
 </h1>
 <p className="text-muted-foreground mt-1">Dein Fortschritt, Achievements und Rangliste</p>
 </div>

 {/* Stats Cards */}
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
 {[
 { icon: <span className="text-3xl">{profile.level_emoji}</span>, value: `Level ${profile.level}`, label: profile.level_name, color: "rgba(234,179,8,0.15)", border: "rgba(234,179,8,0.3)" },
 { icon: <Star className="w-8 h-8 text-yellow-500" />, value: String(profile.xp), label: "XP gesamt", color: "rgba(139,92,246,0.15)", border: "rgba(139,92,246,0.3)" },
 { icon: <Flame className="w-8 h-8 text-orange-500" />, value: String(profile.streak_days), label: "Tage Streak", color: "rgba(249,115,22,0.15)", border: "rgba(249,115,22,0.3)" },
 { icon: <Target className="w-8 h-8 text-cyan-500" />, value: String(profile.quizzes_completed), label: "Quizzes", color: "rgba(6,182,212,0.15)", border: "rgba(6,182,212,0.3)" },
 ].map((card, i) => (
 <motion.div
 key={card.label}
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.1 + i * 0.05 }}
 className="rounded-2xl p-4 text-center"
 style={{ background: card.color, border: `1px solid ${card.border}` }}>
 <div className="mb-1 flex justify-center">{card.icon}</div>
 <p className="text-2xl font-bold text-foreground">{card.value}</p>
 <p className="text-sm text-muted-foreground">{card.label}</p>
 </motion.div>
 ))}
 </div>

 {/* XP Progress Bar */}
 <motion.div
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.3 }}
 className="rounded-2xl p-4"
 style={{ background: "rgba(var(--surface-rgb),0.4)", border: "1px solid rgba(99,102,241,0.2)" }}>
 <div className="flex items-center justify-between mb-2">
 <span className="text-sm font-medium text-muted-foreground">
 {profile.level_emoji} {profile.level_name}
 </span>
 <span className="text-sm text-muted-foreground">
 {profile.xp_to_next_level > 0 ? `${profile.xp_to_next_level} XP bis ${profile.next_level_name}` : "Max Level!"}
 </span>
 </div>
 <div className="w-full rounded-full h-3 overflow-hidden" style={{ background: "rgba(var(--surface-rgb),0.6)" }}>
 <motion.div
 initial={{ width: 0 }}
 animate={{ width: `${xpProgress}%` }}
 transition={{ duration: 1.2, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.5 }}
 className="h-3 rounded-full relative overflow-hidden"
 style={{ background: "linear-gradient(90deg, #eab308, #f59e0b)" }}>
 <div className="absolute inset-0 animate-shimmer" style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)", width: "50%" }} />
 </motion.div>
 </div>
 </motion.div>

 {/* Tabs */}
 <div className="flex gap-2 border-b" style={{ borderColor: "rgba(var(--surface-rgb),0.8)" }}>
 {[
 { id: "overview" as const, label: "Übersicht", icon: <TrendingUp className="w-4 h-4" /> },
 { id: "achievements" as const, label: "Achievements", icon: <Award className="w-4 h-4" /> },
 { id: "leaderboard" as const, label: "Rangliste", icon: <Crown className="w-4 h-4" /> },
 ].map((t) => (
 <button key={t.id} onClick={() => setTab(t.id)}
 className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
 tab === t.id ? "border-indigo-500 text-indigo-400" : "border-transparent text-muted-foreground hover:text-foreground"
 }`}>
 {t.icon} {t.label}
 </button>
 ))}
 </div>

 {/* Tab Content */}
 <AnimatePresence mode="wait">
 {tab === "overview" && (
 <motion.div
 key="overview"
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: 10 }}
 className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div className="rounded-2xl p-4" style={{ background: "rgba(var(--surface-rgb),0.4)", border: "1px solid rgba(99,102,241,0.15)" }}>
 <h3 className="text-base font-bold text-foreground flex items-center gap-2 mb-3"><Zap className="w-5 h-5 text-yellow-500" /> Aktivitäten</h3>
 <div className="space-y-3">
 {[
 { label: "Quizzes abgeschlossen", value: profile.quizzes_completed },
 { label: "Chat-Nachrichten", value: profile.chats_sent },
 { label: "Abitur-Simulationen", value: profile.abitur_completed },
 ].map((item) => (
 <div key={item.label} className="flex items-center justify-between p-3 rounded-lg" style={{ background: "rgba(var(--surface-rgb),0.5)" }}>
 <span className="text-sm text-muted-foreground">{item.label}</span>
 <span className="text-sm font-bold text-foreground">{item.value}</span>
 </div>
 ))}
 </div>
 </div>
 <div className="rounded-2xl p-4" style={{ background: "rgba(var(--surface-rgb),0.4)", border: "1px solid rgba(99,102,241,0.15)" }}>
 <h3 className="text-base font-bold text-foreground flex items-center gap-2 mb-3"><Medal className="w-5 h-5 text-purple-500" /> Level-System</h3>
 <div className="space-y-2">
 {profile.all_levels.map((lvl) => (
 <div key={lvl.level} className={`flex items-center justify-between p-2 rounded-lg text-sm ${
 profile.level >= lvl.level ? "" : "opacity-50"
 }`} style={{
 background: profile.level >= lvl.level ? "rgba(234,179,8,0.1)" : "rgba(var(--surface-rgb),0.4)",
 border: profile.level === lvl.level ? "1px solid rgba(234,179,8,0.4)" : "1px solid transparent",
 }}>
 <span className="flex items-center gap-2">
 <span>{lvl.emoji}</span>
 <span className="font-medium text-foreground">{lvl.name}</span>
 </span>
 <span className="text-muted-foreground">{lvl.min_xp} XP</span>
 </div>
 ))}
 </div>
 </div>
 </motion.div>
 )}

 {tab === "achievements" && (
 <motion.div
 key="achievements"
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: 10 }}
 className="grid grid-cols-1 sm:grid-cols-2 gap-3">
 {profile.all_achievements.map((ach, i) => {
 const earned = earnedAchievementIds.has(ach.id);
 return (
 <motion.div
 key={ach.id}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: i * 0.03 }}
 className={`rounded-2xl p-4 flex items-center gap-4 ${earned ? "" : "opacity-50"}`}
 style={{
 background: earned ? "rgba(234,179,8,0.08)" : "rgba(var(--surface-rgb),0.4)",
 border: earned ? "1px solid rgba(234,179,8,0.3)" : "1px solid rgba(var(--surface-rgb),0.8)",
 }}>
 <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl ${
 earned ? "" : ""
 }`} style={{ background: earned ? "rgba(234,179,8,0.2)" : "rgba(var(--surface-rgb),0.6)" }}>
 {ach.emoji}
 </div>
 <div className="flex-1">
 <p className="font-medium text-foreground flex items-center gap-2">
 {ach.name}
 {earned && <span className="text-xs px-2 py-0.5 rounded-full font-bold" style={{ background: "rgba(16,185,129,0.15)", color: "#10b981" }}>Freigeschaltet</span>}
 </p>
 <p className="text-sm text-muted-foreground">{ach.desc}</p>
 <p className="text-xs text-yellow-500 mt-1 font-bold">+{ach.xp_reward} XP</p>
 </div>
 </motion.div>
 );
 })}
 </motion.div>
 )}

 {tab === "leaderboard" && (
 <motion.div
 key="leaderboard"
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: 10 }}
 className="rounded-2xl p-4"
 style={{ background: "rgba(var(--surface-rgb),0.4)", border: "1px solid rgba(99,102,241,0.15)" }}>
 <h3 className="text-base font-bold text-foreground flex items-center gap-2 mb-4"><Users className="w-5 h-5" /> Top 10 (Wöchentlich)</h3>
 {leaderboard.length === 0 ? (
 <div className="text-center py-8">
 <div className="text-3xl mb-2">🏆</div>
 <p className="text-sm text-muted-foreground">Noch keine Einträge vorhanden.</p>
 </div>
 ) : (
 <div className="space-y-2">
 {leaderboard.map((entry, i) => (
 <motion.div
 key={entry.rank}
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: i * 0.05 }}
 className={`flex items-center gap-3 p-3 rounded-xl`}
 style={{
 background: entry.is_you ? "rgba(99,102,241,0.15)" : "rgba(var(--surface-rgb),0.5)",
 border: entry.is_you ? "1px solid rgba(99,102,241,0.3)" : "1px solid transparent",
 }}>
 <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
 entry.rank === 1 ? "bg-yellow-400 text-yellow-900" :
 entry.rank === 2 ? "bg-gray-400/60 text-white" :
 entry.rank === 3 ? "bg-orange-300 text-orange-800" :
 "text-muted-foreground"
 }`} style={entry.rank > 3 ? { background: "rgba(var(--surface-rgb),0.6)" } : {}}>
 {entry.rank <= 3 ? ["🥇","🥈","🥉"][entry.rank-1] : entry.rank}
 </div>
 <div className="flex-1">
 <p className="text-sm font-medium text-foreground flex items-center gap-1">
 {entry.name} {entry.is_you && <span className="text-xs px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(99,102,241,0.2)", color: "#818cf8" }}>Du</span>}
 </p>
 <p className="text-xs text-muted-foreground">{entry.level_name} - {entry.streak_days} Tage Streak</p>
 </div>
 <div className="text-right">
 <p className="font-bold text-foreground">{entry.xp} XP</p>
 <p className="text-xs text-muted-foreground">Level {entry.level}</p>
 </div>
 </motion.div>
 ))}
 </div>
 )}
 </motion.div>
 )}
 </AnimatePresence>
 </motion.div>
 );
}
