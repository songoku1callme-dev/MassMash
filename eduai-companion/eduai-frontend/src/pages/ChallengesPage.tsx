import { useState, useEffect } from "react";
import { challengesApi, Challenge } from "../services/api";
import { Button } from "@/components/ui/button";
import { Trophy, Plus, Users, Target, Loader2, Check } from "lucide-react";

export default function ChallengesPage() {
 const [challenges, setChallenges] = useState<Challenge[]>([]);
 const [loading, setLoading] = useState(true);
 const [showCreate, setShowCreate] = useState(false);
 const [joining, setJoining] = useState<string | null>(null);
 const [message, setMessage] = useState<string | null>(null);

 // Create form
 const [title, setTitle] = useState("");
 const [description, setDescription] = useState("");
 const [subject, setSubject] = useState("math");
 const [targetScore, setTargetScore] = useState(80);
 const [xpReward, setXpReward] = useState(100);
 const [deadlineDays, setDeadlineDays] = useState(7);
 const [creating, setCreating] = useState(false);

 useEffect(() => {
 loadChallenges();
 }, []);

 const loadChallenges = async () => {
 setLoading(true);
 try {
 const data = await challengesApi.list();
 setChallenges(data.challenges);
 } catch (e) {
 console.error(e);
 }
 setLoading(false);
 };

 const createChallenge = async () => {
 if (!title || !description) return;
 setCreating(true);
 try {
 await challengesApi.create({ title, description, subject, target_score: targetScore, xp_reward: xpReward, deadline_days: deadlineDays });
 setMessage("Challenge erstellt!");
 setShowCreate(false);
 setTitle("");
 setDescription("");
 await loadChallenges();
 } catch (e: unknown) {
 const err = e as Error;
 setMessage(err.message || "Fehler");
 }
 setCreating(false);
 };

 const joinChallenge = async (challengeId: string) => {
 setJoining(challengeId);
 try {
 const data = await challengesApi.join(challengeId);
 setMessage(data.message);
 await loadChallenges();
 } catch (e: unknown) {
 const err = e as Error;
 setMessage(err.message || "Fehler");
 }
 setJoining(null);
 };

 const SUBJECT_LABELS: Record<string, string> = {
 math: "Mathematik", german: "Deutsch", english: "Englisch", physics: "Physik",
 chemistry: "Chemie", biology: "Biologie", history: "Geschichte",
 };

 const SUBJECT_COLORS: Record<string, string> = {
 math: "from-blue-500 to-indigo-500", german: "from-red-500 to-pink-500",
 english: "from-yellow-500 to-orange-500", physics: "from-purple-500 to-violet-500",
 chemistry: "from-green-500 to-emerald-500", biology: "from-teal-500 to-cyan-500",
 history: "from-amber-500 to-yellow-500",
 };

 return (
 <div className="p-6 max-w-4xl mx-auto">
 <div className="flex items-center justify-between mb-6">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <Trophy className="w-6 h-6 text-yellow-500" />
 Klassen-Challenges
 </h1>
 <p className="theme-text-secondary">Erstelle Challenges und lerne gemeinsam mit anderen</p>
 </div>
 <Button onClick={() => setShowCreate(!showCreate)} className="gap-2">
 <Plus className="w-4 h-4" />
 Challenge erstellen
 </Button>
 </div>

 {message && (
 <div className="mb-4 p-3 bg-green-500/10 text-green-500 rounded-lg text-sm">
 {message}
 <button onClick={() => setMessage(null)} className="ml-2 text-green-500 hover:text-green-700">&times;</button>
 </div>
 )}

 {/* Create Form */}
 {showCreate && (
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)] mb-6">
 <h2 className="text-lg font-semibold mb-4">Neue Challenge</h2>
 <div className="space-y-3">
 <input
 value={title}
 onChange={(e) => setTitle(e.target.value)}
 placeholder="Challenge-Titel"
 className="w-full p-3 border rounded-lg"
 />
 <textarea
 value={description}
 onChange={(e) => setDescription(e.target.value)}
 placeholder="Beschreibung (z.B. 'Lerne alle quadratischen Gleichungen')"
 rows={3}
 className="w-full p-3 border rounded-lg"
 />
 <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
 <div>
 <label className="text-xs theme-text-secondary">Fach</label>
 <select
 value={subject}
 onChange={(e) => setSubject(e.target.value)}
 className="w-full p-2 border rounded-lg text-sm"
 >
 <option value="math">Mathematik</option>
 <option value="german">Deutsch</option>
 <option value="english">Englisch</option>
 <option value="physics">Physik</option>
 <option value="chemistry">Chemie</option>
 <option value="biology">Biologie</option>
 <option value="history">Geschichte</option>
 </select>
 </div>
 <div>
 <label className="text-xs theme-text-secondary">Ziel-Score</label>
 <input
 type="number"
 value={targetScore}
 onChange={(e) => setTargetScore(Number(e.target.value))}
 className="w-full p-2 border rounded-lg text-sm"
 />
 </div>
 <div>
 <label className="text-xs theme-text-secondary">XP Belohnung</label>
 <input
 type="number"
 value={xpReward}
 onChange={(e) => setXpReward(Number(e.target.value))}
 className="w-full p-2 border rounded-lg text-sm"
 />
 </div>
 <div>
 <label className="text-xs theme-text-secondary">Deadline (Tage)</label>
 <input
 type="number"
 value={deadlineDays}
 onChange={(e) => setDeadlineDays(Number(e.target.value))}
 className="w-full p-2 border rounded-lg text-sm"
 />
 </div>
 </div>
 <Button onClick={createChallenge} disabled={creating || !title || !description}>
 {creating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
 Challenge erstellen
 </Button>
 </div>
 </div>
 )}

 {/* Challenges List */}
 {loading ? (
 <div className="flex items-center justify-center py-12">
 <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
 </div>
 ) : challenges.length === 0 ? (
 <div className="text-center py-12">
 <Trophy className="w-12 h-12 mx-auto theme-text-secondary mb-3" />
 <p className="theme-text-secondary">Noch keine Challenges vorhanden.</p>
 <p className="text-sm theme-text-secondary">Erstelle die erste Challenge!</p>
 </div>
 ) : (
 <div className="grid gap-4">
 {challenges.map((c) => (
 <div
 key={c.challenge_id}
 className="theme-card rounded-xl overflow-hidden border border-[var(--border-color)]"
 >
 <div className={`h-1.5 bg-gradient-to-r ${SUBJECT_COLORS[c.subject] || "from-gray-400 to-gray-500"}`} />
 <div className="p-5">
 <div className="flex items-start justify-between mb-3">
 <div>
 <h3 className="font-semibold theme-text text-lg">{c.title}</h3>
 <p className="text-sm theme-text-secondary mt-1">{c.description}</p>
 </div>
 <span className={`px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r ${SUBJECT_COLORS[c.subject] || "from-gray-400 to-gray-500"} text-white`}>
 {SUBJECT_LABELS[c.subject] || c.subject}
 </span>
 </div>

 <div className="flex items-center gap-6 text-sm theme-text-secondary mb-4">
 <span className="flex items-center gap-1">
 <Target className="w-4 h-4" />
 Ziel: {c.target_score}%
 </span>
 <span className="flex items-center gap-1">
 <Users className="w-4 h-4" />
 {c.participants} Teilnehmer
 </span>
 <span className="flex items-center gap-1">
 <Check className="w-4 h-4" />
 {c.completions} geschafft
 </span>
 <span className="font-bold text-yellow-600">+{c.xp_reward} XP</span>
 </div>

 <div className="flex gap-2">
 <Button
 size="sm"
 onClick={() => joinChallenge(c.challenge_id)}
 disabled={joining === c.challenge_id}
 >
 {joining === c.challenge_id ? (
 <Loader2 className="w-4 h-4 animate-spin mr-1" />
 ) : (
 <Users className="w-4 h-4 mr-1" />
 )}
 Beitreten
 </Button>
 </div>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 );
}
