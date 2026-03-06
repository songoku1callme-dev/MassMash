import { useState, useEffect } from "react";
import { parentsApi } from "../services/api";
import { Users, Link, Unlink, TrendingUp, BookOpen, Flame, Trophy, Loader2 } from "lucide-react";

export default function ParentsPage() {
 const [childEmail, setChildEmail] = useState("");
 /* eslint-disable @typescript-eslint/no-explicit-any */
 const [children, setChildren] = useState<any[]>([]);
 const [loading, setLoading] = useState(true);
 const [linking, setLinking] = useState(false);
 const [error, setError] = useState("");
 const [success, setSuccess] = useState("");

 useEffect(() => {
 loadChildren();
 }, []);

 const loadChildren = async () => {
 try {
 const data = await parentsApi.children();
 setChildren(data.children);
 } catch {
 // No linked children yet
 } finally {
 setLoading(false);
 }
 };

 const handleLinkChild = async () => {
 if (!childEmail.trim()) return;
 setLinking(true);
 setError("");
 setSuccess("");
 try {
 const result = await parentsApi.linkChild(childEmail);
 setSuccess(result.message);
 setChildEmail("");
 loadChildren();
 } catch (err) {
 setError(err instanceof Error ? err.message : "Fehler beim Verknuepfen");
 } finally {
 setLinking(false);
 }
 };

 const handleUnlink = async (childId: number) => {
 try {
 await parentsApi.unlinkChild(childId);
 loadChildren();
 } catch {
 setError("Fehler beim Entfernen der Verknuepfung");
 }
 };

 return (
 <div className="p-6 max-w-4xl mx-auto">
 <div className="mb-8">
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <Users className="w-7 h-7 text-purple-600" />
 Eltern-Dashboard
 </h1>
 <p className="theme-text-secondary mt-1">
 Verknuepfe dein Kind und verfolge seinen Lernfortschritt.
 </p>
 </div>

 {/* Link Child Form */}
 <div className="mb-8 p-6 theme-card rounded-xl border border-[var(--border-color)] shadow-sm">
 <h2 className="text-lg font-semibold theme-text mb-4 flex items-center gap-2">
 <Link className="w-5 h-5 text-purple-600" />
 Kind verknuepfen
 </h2>
 <div className="flex gap-3">
 <input
 type="email"
 value={childEmail}
 onChange={(e) => setChildEmail(e.target.value)}
 placeholder="Email-Adresse deines Kindes"
 className="flex-1 px-4 py-2 border border-[var(--border-color)] rounded-lg theme-card theme-text text-sm"
 />
 <button
 onClick={handleLinkChild}
 disabled={linking || !childEmail.trim()}
 className="px-6 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
 >
 {linking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link className="w-4 h-4" />}
 Verknuepfen
 </button>
 </div>

 {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
 {success && <p className="mt-3 text-sm text-green-600">{success}</p>}
 </div>

 {/* Children List */}
 {loading ? (
 <div className="flex justify-center py-12">
 <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
 </div>
 ) : children.length === 0 ? (
 <div className="text-center py-12 theme-text-secondary">
 <Users className="w-16 h-16 mx-auto mb-4 opacity-30" />
 <p className="text-lg">Noch keine Kinder verknuepft</p>
 <p className="text-sm mt-1">Gib die Email-Adresse deines Kindes ein, um seine Fortschritte zu sehen.</p>
 </div>
 ) : (
 <div className="space-y-6">
 {children.map((child: any) => (
 <div key={child.id} className="theme-card rounded-xl border border-[var(--border-color)] shadow-sm overflow-hidden">
 {/* Child Header */}
 <div className="p-6 border-b border-[var(--border-color)] flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center text-white font-bold text-lg">
 {child.username?.[0]?.toUpperCase() || "?"}
 </div>
 <div>
 <h3 className="font-semibold theme-text">{child.username}</h3>
 <p className="text-sm theme-text-secondary">
 {child.school_type} {child.school_grade}. Klasse
 </p>
 </div>
 </div>
 <button
 onClick={() => handleUnlink(child.id)}
 className="text-red-500 hover:text-red-700 text-sm flex items-center gap-1"
 >
 <Unlink className="w-4 h-4" />
 Entfernen
 </button>
 </div>

 {/* Stats Grid */}
 <div className="p-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
 <div className="text-center p-3 bg-blue-500/10 rounded-lg">
 <Trophy className="w-5 h-5 text-blue-600 mx-auto mb-1" />
 <p className="text-lg font-bold theme-text">{child.stats?.xp || 0}</p>
 <p className="text-xs theme-text-secondary">XP</p>
 </div>
 <div className="text-center p-3 bg-orange-500/10 rounded-lg">
 <Flame className="w-5 h-5 text-orange-600 mx-auto mb-1" />
 <p className="text-lg font-bold theme-text">{child.stats?.streak_days || 0}</p>
 <p className="text-xs theme-text-secondary">Streak Tage</p>
 </div>
 <div className="text-center p-3 bg-green-500/10 rounded-lg">
 <BookOpen className="w-5 h-5 text-green-600 mx-auto mb-1" />
 <p className="text-lg font-bold theme-text">{child.stats?.quizzes_completed || 0}</p>
 <p className="text-xs theme-text-secondary">Quizze</p>
 </div>
 <div className="text-center p-3 bg-purple-500/10 rounded-lg">
 <TrendingUp className="w-5 h-5 text-purple-600 mx-auto mb-1" />
 <p className="text-lg font-bold theme-text">{child.stats?.avg_quiz_score || 0}%</p>
 <p className="text-xs theme-text-secondary">Durchschnitt</p>
 </div>
 </div>

 {/* Weak Subjects */}
 {child.stats?.weak_subjects?.length > 0 && (
 <div className="px-6 pb-4">
 <p className="text-sm font-medium theme-text-secondary mb-2">Schwache Fächer:</p>
 <div className="flex flex-wrap gap-2">
 {child.stats.weak_subjects.map((s: string) => (
 <span key={s} className="px-3 py-1 bg-red-500/10 text-red-500 text-xs rounded-full">
 {s}
 </span>
 ))}
 </div>
 </div>
 )}

 {/* Week Activity */}
 <div className="px-6 pb-6">
 <p className="text-sm theme-text-secondary">
 Diese Woche: {child.stats?.week_activities || 0} Aktivitaeten,{" "}
 {child.stats?.week_learning_minutes || 0} Min Lernzeit
 </p>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 );
 /* eslint-enable @typescript-eslint/no-explicit-any */
}
