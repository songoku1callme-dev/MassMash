import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import LumnosOrb from "../components/LumnosOrb";
import { getAccessToken } from "../services/api";
import { PageLoader, ErrorState } from "../components/PageStates";

const API_URL = import.meta.env.VITE_API_URL || "";

interface KnowledgeUpdate {
 id: number;
 fach: string;
 thema: string;
 quellen_count: number;
 created_at: string;
}

interface PromptVorschlag {
 id: number;
 fach: string;
 probleme: string;
 neuer_prompt: string;
 feedback_count: number;
 status: string;
 created_at: string;
 genehmigt_am: string;
}

interface EvolutionStats {
 qualitätsrate: number;
 positiv_heute: number;
 negativ_heute: number;
 neue_quellen: number;
 ausstehende_vorschlaege: number;
 fach_updates: Record<string, number>;
}

const CRAWL_FÄCHER = ["Mathematik", "Physik", "Geschichte", "Biologie", "Chemie", "Informatik", "Deutsch", "Latein"];

const FACH_EMOJIS: Record<string, string> = {
 Mathematik: "\u{1F4D0}",
 Physik: "\u{269B}",
 Chemie: "\u{1F9EA}",
 Biologie: "\u{1F9EC}",
 Geschichte: "\u{1F3DB}",
 Deutsch: "\u{1F4DA}",
 Englisch: "\u{1F1EC}\u{1F1E7}",
 Informatik: "\u{1F4BB}",
 Latein: "\u{1F3DB}",
 Wirtschaft: "\u{1F4B9}",
};

async function adminFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
 const token = getAccessToken();
 const res = await fetch(`${API_URL}${endpoint}`, {
 ...options,
 headers: {
 "Content-Type": "application/json",
 ...(token ? { Authorization: `Bearer ${token}` } : {}),
 ...((options.headers as Record<string, string>) || {}),
 },
 });
 if (!res.ok) {
 const err = await res.json().catch(() => ({ detail: "Fehler" }));
 throw new Error(err.detail || "Anfrage fehlgeschlagen");
 }
 return res.json();
}

export default function ForschungsSeite() {
 const [updates, setUpdates] = useState<KnowledgeUpdate[]>([]);
 const [vorschläge, setVorschläge] = useState<PromptVorschlag[]>([]);
 const [stats, setStats] = useState<EvolutionStats | null>(null);
 const [crawling, setCrawling] = useState<string | null>(null);
 const [loading, setLoading] = useState(true);
 const [loadError, setLoadError] = useState(false);

 const loadData = async () => {
 setLoadError(false);
 try {
 const [updatesData, vorschlägData, statsData] = await Promise.all([
 adminFetch<{ updates: KnowledgeUpdate[] }>("/api/admin/knowledge-updates"),
 adminFetch<{ vorschlaege: PromptVorschlag[] }>("/api/admin/prompt-vorschlaege"),
 adminFetch<EvolutionStats>("/api/admin/evolution-stats"),
 ]);
 setUpdates(updatesData.updates);
 setVorschläge(vorschlägData.vorschlaege);
 setStats(statsData);
 } catch (e) {
 console.error("Forschungs-Daten laden fehlgeschlagen:", e);
 setLoadError(true);
 } finally {
 setLoading(false);
 }
 };

 useEffect(() => {
 loadData();
 const interval = setInterval(loadData, 30000);
 return () => clearInterval(interval);
 }, []);

 const handleCrawl = async (fach: string) => {
 setCrawling(fach);
 try {
 await adminFetch("/api/admin/trigger-crawl", {
 method: "POST",
 body: JSON.stringify({ fach, thema: `Aktuelle Themen ${fach} 2026` }),
 });
 await loadData();
 } catch (e) {
 console.error("Crawl fehlgeschlagen:", e);
 } finally {
 setCrawling(null);
 }
 };

 const handleGenehmigen = async (id: number) => {
 try {
 await adminFetch(`/api/admin/prompts/${id}/genehmigen`, { method: "POST" });
 await loadData();
 } catch (e) {
 console.error("Genehmigung fehlgeschlagen:", e);
 }
 };

 if (loading) return <PageLoader text="Forschungs-Zentrum lädt..." />;
 if (loadError) return <ErrorState message="Fehler beim Laden des Forschungs-Zentrums." onRetry={loadData} />;

 if (false) {
 }

 return (
 <div className="min-h-screen cyber-bg p-6 space-y-6">
 {/* Header */}
 <div className="flex items-center gap-4">
 <LumnosOrb
 isTyping={crawling !== null}
 isLearning={crawling !== null}
 size="md"
 />
 <div>
 <h1 className="text-2xl font-bold text-white flex items-center gap-2">
 {"\u{1F9E0}"} Forschungs-Zentrum
 </h1>
 <p className="text-lumnos-muted text-sm">
 LUMNOS Self-Evolution — Autonomes Lernen aus dem Internet
 </p>
 </div>
 </div>

 {/* Stats Row */}
 {stats && (
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
 <StatCard
 label="Qualitätsrate"
 value={`${stats.qualitätsrate}%`}
 color="#10b981"
 icon={"\u2728"}
 />
 <StatCard
 label="Positiv heute"
 value={String(stats.positiv_heute)}
 color="#22c55e"
 icon={"\u{1F44D}"}
 />
 <StatCard
 label="Negativ heute"
 value={String(stats.negativ_heute)}
 color="#ef4444"
 icon={"\u{1F44E}"}
 />
 <StatCard
 label="Neue Quellen"
 value={String(stats.neue_quellen)}
 color="#6366f1"
 icon={"\u{1F4E1}"}
 />
 </div>
 )}

 {/* Main Content Grid */}
 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
 {/* Left: Heute gelernt */}
 <div className="glass rounded-2xl p-6 border border-lumnos-border">
 <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
 {"\u{1F4E1}"} Heute gelernt
 </h2>

 {/* Manual Crawl Buttons */}
 <div className="flex flex-wrap gap-2 mb-4">
 {CRAWL_FÄCHER.map((fach) => (
 <button
 key={fach}
 onClick={() => handleCrawl(fach)}
 disabled={crawling !== null}
 className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
 style={{
 background: crawling === fach
 ? "rgba(245,158,11,0.3)"
 : "rgba(99,102,241,0.15)",
 border: `1px solid ${crawling === fach ? "rgba(245,158,11,0.5)" : "rgba(99,102,241,0.3)"}`,
 color: crawling === fach ? "#f59e0b" : "#a5b4fc",
 }}
 >
 {crawling === fach ? "\u23F3" : (FACH_EMOJIS[fach] || "\u{1F4DA}")} {fach}
 </button>
 ))}
 </div>

 {/* Knowledge Updates List */}
 <div className="space-y-3 max-h-[400px] overflow-y-auto">
 <AnimatePresence>
 {updates.length === 0 ? (
 <p className="text-lumnos-muted text-sm text-center py-8">
 Noch keine Updates heute — Nightly Crawl läuft um 03:00 Uhr
 </p>
 ) : (
 updates.map((update) => (
 <motion.div
 key={update.id}
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: 20 }}
 className="p-3 rounded-xl"
 style={{
 background: "rgba(99,102,241,0.08)",
 border: "1px solid rgba(99,102,241,0.2)",
 }}
 >
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2">
 <span className="text-lg">{FACH_EMOJIS[update.fach] || "\u{1F4DA}"}</span>
 <div>
 <p className="text-white text-sm font-medium">{update.thema}</p>
 <p className="text-lumnos-muted text-xs">{update.fach}</p>
 </div>
 </div>
 <div className="text-right">
 <span className="text-xs font-bold px-2 py-1 rounded-full"
 style={{
 background: "rgba(99,102,241,0.2)",
 color: "#a5b4fc",
 }}>
 {update.quellen_count} Quellen
 </span>
 <p className="text-lumnos-muted text-[10px] mt-1">
 {new Date(update.created_at).toLocaleTimeString("de-DE", {
 hour: "2-digit", minute: "2-digit"
 })}
 </p>
 </div>
 </div>
 </motion.div>
 ))
 )}
 </AnimatePresence>
 </div>
 </div>

 {/* Right: Prompt-Verbesserungen */}
 <div className="glass rounded-2xl p-6 border border-lumnos-border">
 <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
 {"\u{1F527}"} Prompt-Verbesserungen
 {stats && stats.ausstehende_vorschlaege > 0 && (
 <span className="text-xs font-bold px-2 py-0.5 rounded-full"
 style={{ background: "rgba(245,158,11,0.2)", color: "#f59e0b" }}>
 {stats.ausstehende_vorschlaege} ausstehend
 </span>
 )}
 </h2>

 <div className="space-y-4 max-h-[500px] overflow-y-auto">
 {vorschläge.length === 0 ? (
 <p className="text-lumnos-muted text-sm text-center py-8">
 Keine Vorschläge — Wöchentliche Analyse läuft Montag 04:00
 </p>
 ) : (
 vorschläge.map((v) => (
 <motion.div
 key={v.id}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 className="p-4 rounded-xl"
 style={{
 background: v.status === "ausstehend"
 ? "rgba(245,158,11,0.08)"
 : "rgba(34,197,94,0.08)",
 border: `1px solid ${v.status === "ausstehend"
 ? "rgba(245,158,11,0.25)"
 : "rgba(34,197,94,0.25)"}`,
 }}
 >
 <div className="flex items-start justify-between mb-2">
 <div>
 <span className="text-xs font-bold px-2 py-0.5 rounded"
 style={{
 background: v.status === "ausstehend"
 ? "rgba(245,158,11,0.2)" : "rgba(34,197,94,0.2)",
 color: v.status === "ausstehend" ? "#f59e0b" : "#22c55e",
 }}>
 {v.fach}
 </span>
 <span className="text-lumnos-muted text-xs ml-2">
 {v.feedback_count} Feedbacks analysiert
 </span>
 </div>
 <span className="text-[10px] text-lumnos-muted">
 {new Date(v.created_at).toLocaleDateString("de-DE")}
 </span>
 </div>

 {/* Probleme */}
 <div className="mb-2">
 <p className="text-xs font-semibold text-red-400 mb-1">Erkannte Probleme:</p>
 <p className="text-xs text-lumnos-muted leading-relaxed">
 {v.probleme.slice(0, 200)}{v.probleme.length > 200 ? "..." : ""}
 </p>
 </div>

 {/* Neuer Prompt Preview */}
 <div className="mb-3">
 <p className="text-xs font-semibold text-indigo-400 mb-1">Verbesserter Prompt:</p>
 <p className="text-xs text-slate-400 leading-relaxed bg-black/20 rounded-lg p-2">
 {v.neuer_prompt.slice(0, 150)}{v.neuer_prompt.length > 150 ? "..." : ""}
 </p>
 </div>

 {/* Actions */}
 {v.status === "ausstehend" && (
 <div className="flex gap-2">
 <button
 onClick={() => handleGenehmigen(v.id)}
 className="px-4 py-1.5 rounded-lg text-xs font-bold text-white transition-all hover:brightness-110"
 style={{
 background: "linear-gradient(135deg, #22c55e, #16a34a)",
 }}
 >
 Genehmigen
 </button>
 <button
 className="px-4 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition-all"
 style={{
 background: "rgba(239,68,68,0.1)",
 border: "1px solid rgba(239,68,68,0.3)",
 }}
 >
 Ablehnen
 </button>
 </div>
 )}

 {v.status === "genehmigt" && (
 <p className="text-xs text-green-400 font-medium">
 Genehmigt am {new Date(v.genehmigt_am).toLocaleDateString("de-DE")}
 </p>
 )}
 </motion.div>
 ))
 )}
 </div>
 </div>
 </div>

 {/* Bottom: Orbs der Evolution */}
 <div className="glass rounded-2xl p-6 border border-lumnos-border">
 <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
 {"\u2726"} Orbs der Evolution
 </h2>
 <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-4">
 {CRAWL_FÄCHER.map((fach) => {
 const count = stats?.fach_updates?.[fach] || 0;
 return (
 <div key={fach} className="flex flex-col items-center gap-2">
 <LumnosOrb
 fach={fach}
 isLearning={count > 0}
 size="sm"
 />
 <p className="text-xs text-lumnos-muted text-center">{fach}</p>
 <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
 style={{
 background: count > 0 ? "rgba(245,158,11,0.2)" : "rgba(100,116,139,0.2)",
 color: count > 0 ? "#f59e0b" : "#64748b",
 }}>
 {count} Updates
 </span>
 </div>
 );
 })}
 </div>
 </div>
 </div>
 );
}

function StatCard({ label, value, color, icon }: {
 label: string; value: string; color: string; icon: string;
}) {
 return (
 <motion.div
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 className="p-4 rounded-xl"
 style={{
 background: `${color}10`,
 border: `1px solid ${color}30`,
 }}
 >
 <div className="flex items-center gap-2 mb-1">
 <span className="text-lg">{icon}</span>
 <span className="text-xs text-lumnos-muted">{label}</span>
 </div>
 <p className="text-2xl font-bold" style={{ color }}>{value}</p>
 </motion.div>
 );
}
