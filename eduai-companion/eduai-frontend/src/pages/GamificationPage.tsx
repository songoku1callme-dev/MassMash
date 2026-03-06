import { useState, useEffect } from "react";
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
 const [tab, setTab] = useState<"overview" | "achievements" | "leaderboard">("overview");

 useEffect(() => {
 loadData();
 }, []);

 const loadData = async () => {
 setLoading(true);
 try {
 const [profileData, lbData] = await Promise.all([
 gamificationApi.profile(),
 gamificationApi.leaderboard(),
 ]);
 setProfile(profileData);
 setLeaderboard(lbData.leaderboard);
 } catch (err) {
 console.error("Failed to load gamification data:", err);
 } finally {
 setLoading(false);
 }
 };

 if (loading) {
 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto flex items-center justify-center min-h-[400px]">
 <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
 </div>
 );
 }

 if (!profile) {
 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto text-center">
 <p className="theme-text-secondary">Gamification-Daten konnten nicht geladen werden.</p>
 </div>
 );
 }

 const xpProgress = profile.xp_to_next_level > 0
 ? Math.min(100, ((profile.xp % profile.xp_to_next_level) / profile.xp_to_next_level) * 100)
 : 100;

 const earnedAchievementIds = new Set(profile.achievements.map(a => a.id));

 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <Trophy className="w-7 h-7 text-yellow-500" /> Gamification
 </h1>
 <p className="theme-text-secondary mt-1">Dein Fortschritt, Achievements und Rangliste</p>
 </div>

 {/* Stats Cards */}
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
 <Card>
 <CardContent className="p-4 text-center">
 <div className="text-3xl mb-1">{profile.level_emoji}</div>
 <p className="text-2xl font-bold theme-text">Level {profile.level}</p>
 <p className="text-sm theme-text-secondary">{profile.level_name}</p>
 </CardContent>
 </Card>
 <Card>
 <CardContent className="p-4 text-center">
 <Star className="w-8 h-8 text-yellow-500 mx-auto mb-1" />
 <p className="text-2xl font-bold theme-text">{profile.xp}</p>
 <p className="text-sm theme-text-secondary">XP gesamt</p>
 </CardContent>
 </Card>
 <Card>
 <CardContent className="p-4 text-center">
 <Flame className="w-8 h-8 text-orange-500 mx-auto mb-1" />
 <p className="text-2xl font-bold theme-text">{profile.streak_days}</p>
 <p className="text-sm theme-text-secondary">Tage Streak</p>
 </CardContent>
 </Card>
 <Card>
 <CardContent className="p-4 text-center">
 <Target className="w-8 h-8 text-blue-500 mx-auto mb-1" />
 <p className="text-2xl font-bold theme-text">{profile.quizzes_completed}</p>
 <p className="text-sm theme-text-secondary">Quizzes</p>
 </CardContent>
 </Card>
 </div>

 {/* XP Progress Bar */}
 <Card>
 <CardContent className="p-4">
 <div className="flex items-center justify-between mb-2">
 <span className="text-sm font-medium theme-text-secondary">
 {profile.level_emoji} {profile.level_name}
 </span>
 <span className="text-sm theme-text-secondary">
 {profile.xp_to_next_level > 0 ? `${profile.xp_to_next_level} XP bis ${profile.next_level_name}` : "Max Level!"}
 </span>
 </div>
 <div className="w-full bg-[var(--progress-bg)] rounded-full h-3">
 <div className="bg-gradient-to-r from-yellow-400 to-yellow-600 h-3 rounded-full transition-all" style={{ width: `${xpProgress}%` }} />
 </div>
 </CardContent>
 </Card>

 {/* Tabs */}
 <div className="flex gap-2 border-b border-[var(--border-color)]">
 {[
 { id: "overview" as const, label: "Übersicht", icon: <TrendingUp className="w-4 h-4" /> },
 { id: "achievements" as const, label: "Achievements", icon: <Award className="w-4 h-4" /> },
 { id: "leaderboard" as const, label: "Rangliste", icon: <Crown className="w-4 h-4" /> },
 ].map((t) => (
 <button key={t.id} onClick={() => setTab(t.id)}
 className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
 tab === t.id ? "border-blue-500 text-blue-500" : "border-transparent theme-text-secondary hover:theme-text"
 }`}>
 {t.icon} {t.label}
 </button>
 ))}
 </div>

 {/* Tab Content */}
 {tab === "overview" && (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <Card>
 <CardHeader><CardTitle className="text-base flex items-center gap-2"><Zap className="w-5 h-5 text-yellow-500" /> Aktivitäten</CardTitle></CardHeader>
 <CardContent>
 <div className="space-y-3">
 <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-surface)]">
 <span className="text-sm theme-text-secondary">Quizzes abgeschlossen</span>
 <Badge variant="secondary">{profile.quizzes_completed}</Badge>
 </div>
 <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-surface)]">
 <span className="text-sm theme-text-secondary">Chat-Nachrichten</span>
 <Badge variant="secondary">{profile.chats_sent}</Badge>
 </div>
 <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-surface)]">
 <span className="text-sm theme-text-secondary">Abitur-Simulationen</span>
 <Badge variant="secondary">{profile.abitur_completed}</Badge>
 </div>
 </div>
 </CardContent>
 </Card>
 <Card>
 <CardHeader><CardTitle className="text-base flex items-center gap-2"><Medal className="w-5 h-5 text-purple-500" /> Level-System</CardTitle></CardHeader>
 <CardContent>
 <div className="space-y-2">
 {profile.all_levels.map((lvl) => (
 <div key={lvl.level} className={`flex items-center justify-between p-2 rounded-lg text-sm ${
 profile.level >= lvl.level ? "bg-yellow-500/10" : "bg-[var(--bg-surface)] opacity-60"
 }`}>
 <span className="flex items-center gap-2">
 <span>{lvl.emoji}</span>
 <span className="font-medium">{lvl.name}</span>
 </span>
 <span className="theme-text-secondary">{lvl.min_xp} XP</span>
 </div>
 ))}
 </div>
 </CardContent>
 </Card>
 </div>
 )}

 {tab === "achievements" && (
 <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
 {profile.all_achievements.map((ach) => {
 const earned = earnedAchievementIds.has(ach.id);
 return (
 <Card key={ach.id} className={earned ? "border-yellow-300" : "opacity-60"}>
 <CardContent className="p-4 flex items-center gap-4">
 <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl ${
 earned ? "bg-yellow-500/20" : "bg-[var(--bg-surface)]"
 }`}>
 {ach.emoji}
 </div>
 <div className="flex-1">
 <p className="font-medium theme-text flex items-center gap-2">
 {ach.name}
 {earned && <Badge variant="success" className="text-xs">Freigeschaltet</Badge>}
 </p>
 <p className="text-sm theme-text-secondary">{ach.desc}</p>
 <p className="text-xs text-yellow-600 mt-1">+{ach.xp_reward} XP</p>
 </div>
 </CardContent>
 </Card>
 );
 })}
 </div>
 )}

 {tab === "leaderboard" && (
 <Card>
 <CardHeader><CardTitle className="text-base flex items-center gap-2"><Users className="w-5 h-5" /> Top 10 (Wöchentlich)</CardTitle></CardHeader>
 <CardContent>
 {leaderboard.length === 0 ? (
 <p className="text-sm theme-text-secondary text-center py-4">Noch keine Einträge vorhanden.</p>
 ) : (
 <div className="space-y-2">
 {leaderboard.map((entry) => (
 <div key={entry.rank} className={`flex items-center gap-3 p-3 rounded-lg ${
 entry.is_you ? "bg-blue-500/10 border border-blue-500/20" : "bg-[var(--bg-surface)]"
 }`}>
 <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
 entry.rank === 1 ? "bg-yellow-400 text-yellow-900" :
 entry.rank === 2 ? "bg-gray-400 text-gray-900 dark:bg-gray-500 dark:text-white" :
 entry.rank === 3 ? "bg-orange-300 text-orange-800" :
 "bg-[var(--progress-bg)] theme-text-secondary"
 }`}>
 {entry.rank}
 </div>
 <div className="flex-1">
 <p className="text-sm font-medium theme-text flex items-center gap-1">
 {entry.name} {entry.is_you && <Badge variant="secondary" className="text-xs">Du</Badge>}
 </p>
 <p className="text-xs theme-text-secondary">{entry.level_name} - {entry.streak_days} Tage Streak</p>
 </div>
 <div className="text-right">
 <p className="font-bold theme-text">{entry.xp} XP</p>
 <p className="text-xs theme-text-secondary">Level {entry.level}</p>
 </div>
 </div>
 ))}
 </div>
 )}
 </CardContent>
 </Card>
 )}
 </div>
 );
}
