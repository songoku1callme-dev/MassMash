import { useState, useEffect } from "react";
import { questsApi } from "../services/api";
import { Target, CheckCircle, Circle, Flame, Swords, BookOpen, Loader2, Sparkles } from "lucide-react";

const QUEST_ICONS: Record<string, React.ReactNode> = {
  target: <Target className="w-5 h-5" />,
  flame: <Flame className="w-5 h-5" />,
  swords: <Swords className="w-5 h-5" />,
  book: <BookOpen className="w-5 h-5" />,
};

export default function QuestsPage() {
  /* eslint-disable @typescript-eslint/no-explicit-any */
  const [quests, setQuests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [date, setDate] = useState("");

  useEffect(() => {
    loadQuests();
  }, []);

  const loadQuests = async () => {
    try {
      const data = await questsApi.today();
      setQuests(data.quests);
      setDate(data.date);
    } catch {
      // No quests yet
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (questId: string) => {
    try {
      const result = await questsApi.updateProgress(questId);
      if (result.completed) {
        setQuests((prev) =>
          prev.map((q) =>
            q.quest_id === questId ? { ...q, progress: result.progress, completed: true } : q
          )
        );
      }
    } catch {
      // Error handling
    }
  };

  const completedCount = quests.filter((q) => q.completed).length;
  const totalXP = quests.reduce((sum, q) => sum + (q.completed ? q.xp_reward : 0), 0);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-yellow-600" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Target className="w-7 h-7 text-yellow-600" />
          Taegliche Quests
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Erledige taegliche Aufgaben und verdiene Bonus-XP! Quests werden jeden Tag neu generiert.
        </p>
      </div>

      {/* Progress Summary */}
      <div className="mb-6 p-4 bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 rounded-xl border border-yellow-200 dark:border-yellow-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-yellow-700 dark:text-yellow-300">{date}</p>
            <p className="text-lg font-bold text-gray-900 dark:text-white">
              {completedCount}/{quests.length} Quests erledigt
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-yellow-600">{totalXP} XP</p>
            <p className="text-xs text-gray-500">verdient</p>
          </div>
        </div>
        {/* Progress bar */}
        <div className="mt-3 w-full bg-yellow-200 dark:bg-yellow-800 rounded-full h-2">
          <div
            className="bg-yellow-500 h-2 rounded-full transition-all"
            style={{ width: `${quests.length > 0 ? (completedCount / quests.length) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* All Complete Celebration */}
      {completedCount === quests.length && quests.length > 0 && (
        <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-xl border border-green-200 dark:border-green-800 text-center">
          <Sparkles className="w-8 h-8 text-green-600 mx-auto mb-2" />
          <p className="text-lg font-bold text-green-700 dark:text-green-300">Alle Quests erledigt!</p>
          <p className="text-sm text-green-600 dark:text-green-400">Komm morgen wieder für neue Quests.</p>
        </div>
      )}

      {/* Quest Cards */}
      <div className="space-y-4">
        {quests.map((quest: any) => (
          <div
            key={quest.quest_id}
            className={`p-5 rounded-xl border transition-all ${
              quest.completed
                ? "bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800"
                : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:shadow-md"
            }`}
          >
            <div className="flex items-start gap-4">
              <div className={`p-2 rounded-lg ${quest.completed ? "bg-green-100 dark:bg-green-900/30 text-green-600" : "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600"}`}>
                {quest.completed ? <CheckCircle className="w-5 h-5" /> : (QUEST_ICONS[quest.icon] || <Circle className="w-5 h-5" />)}
              </div>
              <div className="flex-1">
                <h3 className={`font-semibold ${quest.completed ? "text-green-700 dark:text-green-300 line-through" : "text-gray-900 dark:text-white"}`}>
                  {quest.title}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{quest.description}</p>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-xs font-medium text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 px-2 py-0.5 rounded-full">
                    +{quest.xp_reward} XP
                  </span>
                  <span className="text-xs text-gray-400">
                    {quest.progress}/{quest.target}
                  </span>
                </div>
              </div>
              {!quest.completed && (
                <button
                  onClick={() => handleComplete(quest.quest_id)}
                  className="px-4 py-2 bg-yellow-500 text-white rounded-lg text-sm font-medium hover:bg-yellow-600 transition-colors"
                >
                  Erledigt
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
  /* eslint-enable @typescript-eslint/no-explicit-any */
}
