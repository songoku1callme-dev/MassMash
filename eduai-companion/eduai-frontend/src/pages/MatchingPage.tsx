import { useState, useEffect } from "react";
import { matchingApi } from "../services/api";
import { Users, Star, Flame, Trophy, Loader2, RefreshCw, MessageCircle } from "lucide-react";

export default function MatchingPage() {
  /* eslint-disable @typescript-eslint/no-explicit-any */
  const [partners, setPartners] = useState<any[]>([]);
  const [myWeakSubjects, setMyWeakSubjects] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    findPartners();
  }, []);

  const findPartners = async () => {
    setLoading(true);
    try {
      const data = await matchingApi.findPartners();
      setPartners(data.partners);
      setMyWeakSubjects(data.my_weak_subjects || []);
      if (data.partners.length === 0) {
        setMessage("Keine passenden Lernpartner gefunden. Mache mehr Quizze, damit die KI deine Schwaechen erkennt!");
      }
    } catch {
      setMessage("Fehler beim Laden der Lernpartner");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Users className="w-7 h-7 text-cyan-600" />
          Lernpartner finden
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Die KI findet Schueler mit aehnlichen Schwaechen — gemeinsam lernt ihr besser!
        </p>
      </div>

      {/* My Weak Subjects */}
      {myWeakSubjects.length > 0 && (
        <div className="mb-6 p-4 bg-cyan-50 dark:bg-cyan-900/20 rounded-xl border border-cyan-200 dark:border-cyan-800">
          <p className="text-sm font-medium text-cyan-700 dark:text-cyan-300 mb-2">Deine schwachen Faecher:</p>
          <div className="flex flex-wrap gap-2">
            {myWeakSubjects.map((s) => (
              <span key={s} className="px-3 py-1 bg-cyan-100 dark:bg-cyan-800/50 text-cyan-700 dark:text-cyan-300 text-sm rounded-full">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Refresh Button */}
      <div className="mb-6 flex justify-end">
        <button
          onClick={findPartners}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm text-cyan-700 bg-cyan-50 dark:bg-cyan-900/20 dark:text-cyan-300 rounded-lg hover:bg-cyan-100 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Neu suchen
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-600" />
        </div>
      ) : partners.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <Users className="w-16 h-16 mx-auto mb-4 opacity-30" />
          <p className="text-lg">{message || "Keine Lernpartner gefunden"}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {partners.map((partner: any) => (
            <div key={partner.user_id} className="p-5 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center text-white font-bold text-lg">
                  {partner.username?.[0]?.toUpperCase() || "?"}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900 dark:text-white">{partner.username}</h3>
                    <span className="text-sm font-medium text-cyan-600 bg-cyan-50 dark:bg-cyan-900/30 px-3 py-1 rounded-full">
                      {partner.match_prozent || partner.match_score}% Match
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                    {partner.school_grade}. Klasse
                  </p>

                  {/* Common Subjects */}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {partner.common_subjects?.map((s: string) => (
                      <span key={s} className="px-2 py-0.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 text-xs rounded-full">
                        {s}
                      </span>
                    ))}
                  </div>

                  {/* Stats */}
                  <div className="mt-3 flex items-center gap-4 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <Trophy className="w-3 h-3" /> {partner.stats?.xp || 0} XP
                    </span>
                    <span className="flex items-center gap-1">
                      <Star className="w-3 h-3" /> Level {partner.stats?.level || 1}
                    </span>
                    <span className="flex items-center gap-1">
                      <Flame className="w-3 h-3" /> {partner.stats?.streak_days || 0} Tage Streak
                    </span>
                  </div>

                  {/* Gemeinsam lernen Button */}
                  <button
                    className="mt-3 flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors"
                    onClick={() => alert(`Lerngruppe mit ${partner.username} wird erstellt! (Coming soon)`)}
                  >
                    <MessageCircle className="w-4 h-4" />
                    Gemeinsam lernen
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
  /* eslint-enable @typescript-eslint/no-explicit-any */
}
