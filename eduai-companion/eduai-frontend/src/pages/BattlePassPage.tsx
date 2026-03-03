import { useEffect, useState } from "react";
import { getAccessToken } from "../services/api";
import { Trophy, Star, Lock, Gift, Zap, Bot, Palette, Crown, Gem, Flame } from "lucide-react";

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

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
      </div>
    );
  }

  if (!status) {
    return (
      <div className="p-6">
        <p className="text-gray-500 dark:text-gray-400">Battle Pass konnte nicht geladen werden.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white shadow-lg">
            <Trophy className="w-6 h-6" />
          </div>
          Battle Pass
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Saison: {status.saison} - 50 Level mit exklusiven Belohnungen
        </p>
      </div>

      {/* Progress Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 mb-8">
        <div className="flex items-center justify-between mb-3">
          <div>
            <span className="text-2xl font-bold text-purple-600 dark:text-purple-400">Level {status.current_level}</span>
            <span className="text-gray-500 dark:text-gray-400 text-sm ml-2">/ {status.max_level}</span>
          </div>
          <div className="text-right">
            <span className="text-lg font-semibold text-gray-900 dark:text-white">{status.current_xp} XP</span>
            <span className="text-gray-500 dark:text-gray-400 text-sm ml-1">/ {status.xp_for_next_level}</span>
          </div>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
            style={{ width: `${status.progress_percent}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          {status.progress_percent.toFixed(1)}% zum nächsten Level
        </p>
      </div>

      {/* Claim Message */}
      {claimMsg && (
        <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-xl text-green-700 dark:text-green-300 text-sm font-medium">
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
          <div key={src.label} className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 text-center">
            <div className={`w-10 h-10 ${src.color} rounded-lg flex items-center justify-center text-white mx-auto mb-2`}>
              {ICON_MAP[src.icon]}
            </div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{src.label}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{src.xp}</p>
          </div>
        ))}
      </div>

      {/* Rewards Grid */}
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Alle Belohnungen</h2>
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
                  ? "bg-purple-50 dark:bg-purple-900/20 border-purple-300 dark:border-purple-700"
                  : unlocked
                    ? "bg-white dark:bg-gray-800 border-green-300 dark:border-green-700 shadow-sm"
                    : "bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 opacity-60"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-gray-500 dark:text-gray-400">Lv. {reward.level}</span>
                {claimed && <Gift className="w-4 h-4 text-purple-500" />}
                {!unlocked && <Lock className="w-4 h-4 text-gray-400" />}
              </div>
              <div className="text-center mb-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center mx-auto ${
                  unlocked ? "bg-purple-100 dark:bg-purple-900/40 text-purple-600" : "bg-gray-200 dark:bg-gray-700 text-gray-400"
                }`}>
                  {ICON_MAP[reward.icon] || <Star className="w-4 h-4" />}
                </div>
              </div>
              <p className="text-xs text-center font-medium text-gray-700 dark:text-gray-300 line-clamp-2">
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
