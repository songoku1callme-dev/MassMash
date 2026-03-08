import { useEffect, useState } from "react";
import { getAccessToken } from "../services/api";
import { Trophy, Star, Lock, Gift, Zap, Bot, Palette, Crown, Gem, Flame } from "lucide-react";
import { PageLoader, ErrorState } from "../components/PageStates";

const API_URL = import.meta.env.VITE_API_URL || "";

interface Reward {
 level: number;
 xp_required: number;
 reward: string;
 type: string;
 icon: string;
}

interface BattlePassStatus {
 saison: string;
 current_level: number;
 max_level: number;
 current_xp: number;
 xp_for_next_level: number;
 progress_percent: number;
 current_reward: Reward | null;
 next_reward: Reward | null;
 claimed_rewards: number[];
 all_rewards: Reward[];
}

const ICON_MAP: Record<string, React.ReactNode> = {
 award: <Trophy className="w-5 h-5" />,
 palette: <Palette className="w-5 h-5" />,
 zap: <Zap className="w-5 h-5" />,
 star: <Star className="w-5 h-5" />,
 bot: <Bot className="w-5 h-5" />,
 crown: <Crown className="w-5 h-5" />,
 gem: <Gem className="w-5 h-5" />,
 flame: <Flame className="w-5 h-5" />,
 trophy: <Trophy className="w-5 h-5" />,
};

export default function BattlePassPage() {
 const [status, setStatus] = useState<BattlePassStatus | null>(null);
 const [loading, setLoading] = useState(true);
 const [claimMsg, setClaimMsg] = useState("");

 const fetchStatus = async () => {
 try {
 const token = getAccessToken();
 const res = await fetch(`${API_URL}/api/battle-pass/status`, {
 headers: { Authorization: `Bearer ${token}` },
 });
 if (res.ok) setStatus(await res.json());
 } catch {
 /* ignore */
 } finally {
 setLoading(false);
 }
 };

 useEffect(() => {
 fetchStatus();
 }, []);

 const claimReward = async (level: number) => {
 try {
 const token = getAccessToken();
 const res = await fetch(`${API_URL}/api/battle-pass/claim/${level}`, {
 method: "POST",
 headers: { Authorization: `Bearer ${token}` },
 });
 const data = await res.json();
 if (res.ok) {
 setClaimMsg(data.message);
 fetchStatus();
 setTimeout(() => setClaimMsg(""), 3000);
 }
 } catch {
 /* ignore */
 }
 };

 if (loading) return <PageLoader text="Battle Pass laden..." />;
 if (!status) return <ErrorState message="Battle Pass konnte nicht geladen werden." onRetry={fetchStatus} />;

 return (
 <div className="p-6 max-w-5xl mx-auto">
 {/* Header */}
 <div className="mb-8">
 <h1 className="text-3xl font-bold theme-text flex items-center gap-3">
 <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white shadow-lg">
 <Trophy className="w-6 h-6" />
 </div>
 Battle Pass
 </h1>
 <p className="theme-text-secondary mt-1">
 Saison: {status.saison} - 50 Level mit exklusiven Belohnungen
 </p>
 </div>

 {/* Progress Bar */}
 <div className="theme-card rounded-2xl p-6 shadow-sm border border-[var(--border-color)] mb-8">
 <div className="flex items-center justify-between mb-3">
 <div>
 <span className="text-2xl font-bold text-purple-600">Level {status.current_level}</span>
 <span className="theme-text-secondary text-sm ml-2">/ {status.max_level}</span>
 </div>
 <div className="text-right">
 <span className="text-lg font-semibold theme-text">{status.current_xp} XP</span>
 <span className="theme-text-secondary text-sm ml-1">/ {status.xp_for_next_level}</span>
 </div>
 </div>
 <div className="w-full bg-[var(--progress-bg)] rounded-full h-4 overflow-hidden">
 <div
 className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
 style={{ width: `${status.progress_percent}%` }}
 />
 </div>
 <p className="text-xs theme-text-secondary mt-2">
 {status.progress_percent.toFixed(1)}% zum nächsten Level
 </p>
 </div>

 {/* Claim Message */}
 {claimMsg && (
 <div className="mb-4 p-4 bg-green-500/10 border border-green-500/20 rounded-xl text-green-500 text-sm font-medium">
 {claimMsg}
 </div>
 )}

 {/* XP Sources */}
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
 {[
 { label: "Quiz", xp: "+50 XP", icon: "zap", color: "bg-blue-500" },
 { label: "Turnier", xp: "+100 XP", icon: "trophy", color: "bg-orange-500" },
 { label: "Täglich lernen", xp: "+25 XP", icon: "star", color: "bg-green-500" },
 { label: "Feynman-Test", xp: "+75 XP", icon: "award", color: "bg-purple-500" },
 ].map((src) => (
 <div key={src.label} className="theme-card rounded-xl p-4 border border-[var(--border-color)] text-center">
 <div className={`w-10 h-10 ${src.color} rounded-lg flex items-center justify-center text-white mx-auto mb-2`}>
 {ICON_MAP[src.icon]}
 </div>
 <p className="text-sm font-medium theme-text">{src.label}</p>
 <p className="text-xs theme-text-secondary">{src.xp}</p>
 </div>
 ))}
 </div>

 {/* Rewards Grid */}
 <h2 className="text-xl font-bold theme-text mb-4">Alle Belohnungen</h2>
 <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
 {status.all_rewards.map((reward) => {
 const unlocked = status.current_xp >= reward.xp_required;
 const claimed = status.claimed_rewards.includes(reward.level);
 const canClaim = unlocked && !claimed;

 return (
 <div
 key={reward.level}
 className={`relative rounded-xl p-3 border transition-all ${
 claimed
 ? "bg-purple-500/10 border-purple-500/30"
 : unlocked
 ? "theme-card border-green-300 shadow-sm"
 : "bg-[var(--bg-surface)] border-[var(--border-color)] opacity-60"
 }`}
 >
 <div className="flex items-center justify-between mb-2">
 <span className="text-xs font-bold theme-text-secondary">Lv. {reward.level}</span>
 {claimed && <Gift className="w-4 h-4 text-purple-500" />}
 {!unlocked && <Lock className="w-4 h-4 theme-text-secondary" />}
 </div>
 <div className="text-center mb-2">
 <div className={`w-8 h-8 rounded-lg flex items-center justify-center mx-auto ${
 unlocked ? "bg-purple-500/20 text-purple-400" : "bg-[var(--progress-bg)] theme-text-secondary"
 }`}>
 {ICON_MAP[reward.icon] || <Star className="w-4 h-4" />}
 </div>
 </div>
 <p className="text-xs text-center font-medium theme-text-secondary line-clamp-2">
 {reward.reward}
 </p>
 <p className="text-xs text-center text-gray-400 mt-1">{reward.xp_required} XP</p>
 {canClaim && (
 <button
 onClick={() => claimReward(reward.level)}
 className="mt-2 w-full py-1 text-xs font-medium bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
 >
 Abholen
 </button>
 )}
 </div>
 );
 })}
 </div>
 </div>
 );
}
