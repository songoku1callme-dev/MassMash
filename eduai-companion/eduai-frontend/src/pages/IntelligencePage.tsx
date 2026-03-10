import { useState } from "react";
import { intelligenceApi, erklaerungApi } from "../services/api";
import { Button } from "@/components/ui/button";
import { Brain, BookOpen, HelpCircle, Search, Calendar, Loader2, GraduationCap } from "lucide-react";
import { ErrorState } from "../components/PageStates";

type Tab = "lernstil" | "feynman" | "sokrates" | "wissensscan" | "wochenplan" | "erklaerer";

export default function IntelligencePage() {
 const [tab, setTab] = useState<Tab>("lernstil");
 const [loading, setLoading] = useState(false);

 // Lernstil
 const [lernstilResult, setLernstilResult] = useState<{ lernstil: string; beschreibung: string; tipps: string[] } | null>(null);

 // Feynman
 const [feynmanThema, setFeynmanThema] = useState("");
 const [feynmanErklärung, setFeynmanErklärung] = useState("");
 const [feynmanResult, setFeynmanResult] = useState<string | null>(null);

 // Sokrates
 const [sokratesFrage, setSokratesFrage] = useState("");
 const [sokratesResult, setSokratesResult] = useState<string | null>(null);

 // Wissensscan
 const [scanSubject, setScanSubject] = useState("math");
 /* eslint-disable @typescript-eslint/no-explicit-any */
 const [scanQuestions, setScanQuestions] = useState<any[]>([]);
 const [scanAnswers, setScanAnswers] = useState<number[]>([]);
 const [scanResult, setScanResult] = useState<any>(null);
 /* eslint-enable @typescript-eslint/no-explicit-any */

 // Wochenplan
 const [weeklyPlan, setWeeklyPlan] = useState<string | null>(null);

 // Erklärer
 const [erklaererThema, setErklaererThema] = useState("");
 const [erklaererFach, setErklaererFach] = useState("Allgemein");
 const [erklaererStufe, setErklaererStufe] = useState<"einfach" | "normal" | "profi">("normal");
 const [erklaererResult, setErklaererResult] = useState<{ einfach: string; normal: string; profi: string } | null>(null);

 const detectLernstil = async () => {
 setLoading(true);
 try {
 const data = await intelligenceApi.lernstil();
 setLernstilResult(data);
 } catch (e) {
 console.error(e);
 }
 setLoading(false);
 };

 const submitFeynman = async () => {
 if (!feynmanThema || !feynmanErklärung) return;
 setLoading(true);
 try {
 const data = await intelligenceApi.feynman(feynmanThema, feynmanErklärung);
 setFeynmanResult(data.bewertung);
 } catch (e) {
 console.error(e);
 }
 setLoading(false);
 };

 const submitSokrates = async () => {
 if (!sokratesFrage) return;
 setLoading(true);
 try {
 const data = await intelligenceApi.sokrates(sokratesFrage);
 setSokratesResult(data.antwort);
 } catch (e) {
 console.error(e);
 }
 setLoading(false);
 };

 const startWissensscan = async () => {
 setLoading(true);
 setScanResult(null);
 try {
 const data = await intelligenceApi.wissensscanStart(scanSubject);
 setScanQuestions(data.questions);
 setScanAnswers(new Array(data.questions.length).fill(-1));
 } catch (e) {
 console.error(e);
 }
 setLoading(false);
 };

 const submitWissensscan = async () => {
 setLoading(true);
 try {
 const data = await intelligenceApi.wissensscanResult(scanSubject, scanAnswers);
 setScanResult(data);
 } catch (e) {
 console.error(e);
 }
 setLoading(false);
 };

 const loadWeeklyPlan = async () => {
 setLoading(true);
 try {
 const data = await intelligenceApi.weeklyPlan();
 setWeeklyPlan(data.plan);
 } catch (e) {
 console.error(e);
 }
 setLoading(false);
 };

 const submitErklaerer = async () => {
 if (!erklaererThema.trim()) return;
 setLoading(true);
 setErklaererResult(null);
 try {
 const data = await erklaerungApi.stufenweise({ thema: erklaererThema, fach: erklaererFach });
 setErklaererResult(data.stufen);
 } catch (e) {
 console.error(e);
 }
 setLoading(false);
 };

 const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
 { id: "lernstil", label: "Lernstil", icon: <Brain className="w-4 h-4" /> },
 { id: "feynman", label: "Feynman", icon: <BookOpen className="w-4 h-4" /> },
 { id: "sokrates", label: "Sokrates", icon: <HelpCircle className="w-4 h-4" /> },
 { id: "wissensscan", label: "Wissens-Scan", icon: <Search className="w-4 h-4" /> },
 { id: "wochenplan", label: "Wochenplan", icon: <Calendar className="w-4 h-4" /> },
 { id: "erklaerer", label: "Erklärer", icon: <GraduationCap className="w-4 h-4" /> },
 ];

 return (
 <div className="p-6 max-w-4xl mx-auto">
 <h1 className="text-2xl font-bold theme-text mb-2">KI-Intelligenz</h1>
 <p className="theme-text-secondary mb-6">Smarte Lern-Tools für personalisiertes Lernen</p>

 {/* Tabs */}
 <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
 {tabs.map((t) => (
 <button
 key={t.id}
 onClick={() => setTab(t.id)}
 className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
 tab === t.id
 ? "bg-blue-600 text-white"
 : "bg-[var(--bg-surface)] theme-text-secondary hover:opacity-80"
 }`}
 >
 {t.icon}
 {t.label}
 </button>
 ))}
 </div>

 {/* Lernstil */}
 {tab === "lernstil" && (
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h2 className="text-lg font-semibold mb-4">Lernstil-Erkennung</h2>
 <p className="theme-text-secondary mb-4">
 Basierend auf deinen Chat-Nachrichten erkennt die KI deinen Lernstil (Visuell, Auditiv, Kinesthetisch, Lesen).
 </p>
 <Button onClick={detectLernstil} disabled={loading}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Brain className="w-4 h-4 mr-2" />}
 Lernstil erkennen
 </Button>
 {lernstilResult && (
 <div className="mt-4 p-4 bg-blue-500/10 rounded-lg">
 <p className="text-lg font-bold text-blue-600 mb-2">
 Dein Lernstil: {lernstilResult.lernstil.toUpperCase()}
 </p>
 <p className="theme-text-secondary mb-3">{lernstilResult.beschreibung}</p>
 <p className="font-medium theme-text mb-1">Tipps:</p>
 <ul className="list-disc list-inside space-y-1 theme-text-secondary">
 {lernstilResult.tipps.map((t, i) => <li key={i}>{t}</li>)}
 </ul>
 </div>
 )}
 </div>
 )}

 {/* Feynman */}
 {tab === "feynman" && (
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h2 className="text-lg font-semibold mb-2">Feynman-Technik</h2>
 <p className="theme-text-secondary mb-4">
 Erkläre ein Thema in eigenen Worten. Die KI bewertet dein Verständnis (1-10) und zeigt Lücken auf.
 </p>
 <input
 value={feynmanThema}
 onChange={(e) => setFeynmanThema(e.target.value)}
 placeholder="Thema (z.B. Photosynthese, Quadratische Gleichungen)"
 className="w-full mb-3 p-3 border border-[var(--border-color)] bg-[var(--lumnos-surface)] theme-text rounded-lg"
 />
 <textarea
 value={feynmanErklärung}
 onChange={(e) => setFeynmanErklärung(e.target.value)}
 placeholder="Erkläre das Thema in deinen eigenen Worten..."
 rows={6}
 className="w-full mb-3 p-3 border border-[var(--border-color)] bg-[var(--lumnos-surface)] theme-text rounded-lg"
 />
 <Button onClick={submitFeynman} disabled={loading || !feynmanThema || !feynmanErklärung}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <BookOpen className="w-4 h-4 mr-2" />}
 Bewertung anfordern
 </Button>
 {feynmanResult && (
 <div className="mt-4 p-4 bg-green-500/10 rounded-lg">
 <p className="whitespace-pre-wrap theme-text-secondary">{feynmanResult}</p>
 </div>
 )}
 </div>
 )}

 {/* Sokrates */}
 {tab === "sokrates" && (
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h2 className="text-lg font-semibold mb-2">Sokrates-Methode</h2>
 <p className="theme-text-secondary mb-4">
 Stelle eine Frage und die KI fuehrt dich durch gezielte Gegenfragen zur Antwort.
 </p>
 <input
 value={sokratesFrage}
 onChange={(e) => setSokratesFrage(e.target.value)}
 placeholder="Deine Frage (z.B. Warum ist der Himmel blau?)"
 className="w-full mb-3 p-3 border border-[var(--border-color)] bg-[var(--lumnos-surface)] theme-text rounded-lg"
 />
 <Button onClick={submitSokrates} disabled={loading || !sokratesFrage}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <HelpCircle className="w-4 h-4 mr-2" />}
 Sokratisch fragen
 </Button>
 {sokratesResult && (
 <div className="mt-4 p-4 bg-purple-500/10 rounded-lg">
 <p className="whitespace-pre-wrap theme-text-secondary">{sokratesResult}</p>
 </div>
 )}
 </div>
 )}

 {/* Wissensscan */}
 {tab === "wissensscan" && (
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h2 className="text-lg font-semibold mb-2">Wissensluecken-Scanner</h2>
 <p className="theme-text-secondary mb-4">
 10 Diagnose-Fragen um deine Stärken und Schwächen in einem Fach zu erkennen.
 </p>
 {scanQuestions.length === 0 && !scanResult && (
 <div>
 <select
 value={scanSubject}
 onChange={(e) => setScanSubject(e.target.value)}
 className="mb-3 p-3 border border-[var(--border-color)] bg-[var(--lumnos-surface)] theme-text rounded-lg"
 >
 <option value="math">Mathematik</option>
 <option value="german">Deutsch</option>
 <option value="english">Englisch</option>
 <option value="physics">Physik</option>
 <option value="chemistry">Chemie</option>
 <option value="biology">Biologie</option>
 <option value="history">Geschichte</option>
 </select>
 <br />
 <Button onClick={startWissensscan} disabled={loading}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
 Scan starten
 </Button>
 </div>
 )}
 {scanQuestions.length > 0 && !scanResult && (
 <div className="space-y-4">
 {scanQuestions.map((q, qi) => (
 <div key={qi} className="p-4 bg-[var(--bg-surface)] rounded-lg">
 <p className="font-medium mb-2">{qi + 1}. {q.frage}</p>
 <div className="grid grid-cols-2 gap-2">
 {(q.optionen || []).map((opt: string, oi: number) => (
 <button
 key={oi}
 onClick={() => {
 const newAnswers = [...scanAnswers];
 newAnswers[qi] = oi;
 setScanAnswers(newAnswers);
 }}
 className={`p-2 rounded-lg text-sm text-left transition-colors ${
 scanAnswers[qi] === oi
 ? "bg-blue-600 text-white"
 : "bg-[var(--lumnos-surface)] theme-text-secondary hover:opacity-80"
 }`}
 >
 {opt}
 </button>
 ))}
 </div>
 </div>
 ))}
 <Button onClick={submitWissensscan} disabled={loading || scanAnswers.some(a => a === -1)}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
 Ergebnis anzeigen
 </Button>
 </div>
 )}
 {scanResult && (
 <div className="mt-4">
 <div className="text-center mb-4">
 <p className="text-4xl font-bold text-blue-600">{scanResult.score}%</p>
 <p className="theme-text-secondary">{scanResult.correct}/{scanResult.total} richtig</p>
 </div>
 {scanResult.gaps.length > 0 && (
 <div className="mb-3">
 <p className="font-medium text-red-600 mb-1">Lücken:</p>
 <div className="flex flex-wrap gap-2">
 {scanResult.gaps.map((g: string, i: number) => (
 <span key={i} className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm">{g}</span>
 ))}
 </div>
 </div>
 )}
 {scanResult.strengths.length > 0 && (
 <div className="mb-3">
 <p className="font-medium text-green-600 mb-1">Stärken:</p>
 <div className="flex flex-wrap gap-2">
 {scanResult.strengths.map((s: string, i: number) => (
 <span key={i} className="px-3 py-1 bg-green-100 text-green-600 rounded-full text-sm">{s}</span>
 ))}
 </div>
 </div>
 )}
 <p className="theme-text-secondary mt-3">{scanResult.recommendation}</p>
 <Button className="mt-3" onClick={() => { setScanQuestions([]); setScanResult(null); }}>
 Neuen Scan starten
 </Button>
 </div>
 )}
 </div>
 )}

 {/* Wochenplan */}
 {tab === "wochenplan" && (
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h2 className="text-lg font-semibold mb-2">Personalisierter Wochenplan</h2>
 <p className="theme-text-secondary mb-4">
 Basierend auf deinen Schwächen und kommenden Klausuren erstellt die KI deinen optimalen Wochenplan.
 </p>
 <Button onClick={loadWeeklyPlan} disabled={loading}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Calendar className="w-4 h-4 mr-2" />}
 Wochenplan erstellen
 </Button>
 {weeklyPlan && (
 <div className="mt-4 p-4 bg-yellow-500/10 rounded-lg">
 <p className="whitespace-pre-wrap theme-text-secondary">{weeklyPlan}</p>
 </div>
 )}
 </div>
 )}

 {/* Erklärer */}
 {tab === "erklaerer" && (
 <div className="theme-card rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
 <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
 <GraduationCap className="w-5 h-5" /> Erklärer
 </h2>
 <p className="theme-text-secondary mb-4">
 Gib ein Thema ein und erhalte Erklärungen auf drei Schwierigkeitsstufen.
 </p>
 <div className="flex gap-3 mb-4">
 <input
 value={erklaererThema}
 onChange={(e) => setErklaererThema(e.target.value)}
 placeholder="Thema eingeben (z.B. Fotosynthese, Pythagoras, Gedichtanalyse)"
 className="flex-1 p-3 border border-[var(--border-color)] bg-[var(--lumnos-surface)] theme-text rounded-lg"
 onKeyDown={(e) => e.key === "Enter" && submitErklaerer()}
 />
 <select
 value={erklaererFach}
 onChange={(e) => setErklaererFach(e.target.value)}
 className="p-3 border border-[var(--border-color)] bg-[var(--lumnos-surface)] theme-text rounded-lg"
 >
 <option value="Allgemein">Allgemein</option>
 <option value="Mathematik">Mathematik</option>
 <option value="Deutsch">Deutsch</option>
 <option value="Englisch">Englisch</option>
 <option value="Physik">Physik</option>
 <option value="Chemie">Chemie</option>
 <option value="Biologie">Biologie</option>
 <option value="Geschichte">Geschichte</option>
 <option value="Informatik">Informatik</option>
 </select>
 </div>
 <Button onClick={submitErklaerer} disabled={loading || !erklaererThema.trim()}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <GraduationCap className="w-4 h-4 mr-2" />}
 Erklärung generieren
 </Button>

 {erklaererResult && (
 <div className="mt-6">
 {/* Level Buttons */}
 <div className="flex gap-2 mb-4">
 {([
 { key: "einfach" as const, label: "Einfach", emoji: "\uD83E\uDDD2" },
 { key: "normal" as const, label: "Normal", emoji: "\uD83D\uDCDA" },
 { key: "profi" as const, label: "Profi", emoji: "\uD83D\uDD2C" },
 ]).map((s) => (
 <button
 key={s.key}
 onClick={() => setErklaererStufe(s.key)}
 className={`flex-1 py-3 px-4 rounded-lg font-medium text-sm transition-all ${
 erklaererStufe === s.key
 ? "bg-blue-600 text-white shadow-md"
 : "bg-[var(--bg-surface)] theme-text-secondary hover:opacity-80"
 }`}
 >
 <span className="text-lg mr-1">{s.emoji}</span> {s.label}
 </button>
 ))}
 </div>

 {/* Explanation Display */}
 <div className={`p-5 rounded-xl border-2 transition-all ${
 erklaererStufe === "einfach" ? "bg-green-500/10 border-green-500/30" :
 erklaererStufe === "normal" ? "bg-blue-500/10 border-blue-500/30" :
 "bg-purple-500/10 border-purple-500/30"
 }`}>
 <p className={`text-sm font-bold mb-2 ${
 erklaererStufe === "einfach" ? "text-green-600" :
 erklaererStufe === "normal" ? "text-blue-600" :
 "text-purple-600"
 }`}>
 {erklaererStufe === "einfach" ? "\uD83E\uDDD2 Einfach erklärt" :
 erklaererStufe === "normal" ? "\uD83D\uDCDA Normal" :
 "\uD83D\uDD2C Profi-Level"}
 </p>
 <p className="theme-text-secondary whitespace-pre-wrap leading-relaxed">
 {erklaererResult[erklaererStufe]}
 </p>
 </div>
 </div>
 )}
 </div>
 )}
 </div>
 );
}
