import { useState, useEffect } from "react";
import { Shield, FileText, Lock, Trash2, Cookie, Mail, Scale, Eye } from "lucide-react";

const API = import.meta.env.VITE_API_URL || "";

interface Section { title: string; content: string; }

/* Static fallback content — works even without backend */
const STATIC_SECTIONS: Section[] = [
 { title: "1. Verantwortlicher", content: "Lumnos Companion ist ein Bildungstechnologie-Projekt. Kontakt: support@lumnos-companion.de" },
 { title: "2. Welche Daten wir erheben", content: "Wir erheben: E-Mail-Adresse, Benutzername, Schulklasse, Schultyp, Lernfortschritt, Quiz-Ergebnisse, Chat-Verlaeufe. Alle Daten dienen ausschliesslich der Lernunterstuetzung." },
 { title: "3. Zweck der Verarbeitung", content: "Personalisiertes Lernen, KI-gestütztes Tutoring, Fortschrittsverfolgung, Gamification. Keine Daten werden an Dritte verkauft." },
 { title: "4. KI-Verarbeitung (Groq)", content: "Chat-Nachrichten werden an die Groq API gesendet für KI-Antworten. Es werden keine personenbezogenen Daten (Name, E-Mail) an Groq übermittelt. Nur der Fragetext und minimaler Kontext." },
 { title: "5. Zahlungsdaten (Stripe)", content: "Zahlungen werden über Stripe abgewickelt. Wir speichern keine Kreditkartendaten. Stripe ist PCI-DSS zertifiziert." },
 { title: "6. Cookies", content: "Wir verwenden: Notwendige Cookies (Session, Auth-Token), Optionale Cookies (Dark Mode Praeferenz, Sprache). Keine Tracking-Cookies ohne Einwilligung." },
 { title: "7. Deine Rechte (DSGVO Art. 15-22)", content: "Du hast das Recht auf: Auskunft, Berichtigung, Loeschung, Einschraenkung, Datenportabilitaet, Widerspruch. Kontaktiere uns jederzeit." },
 { title: "8. Account loeschen", content: "Du kannst deinen Account jederzeit in den Einstellungen loeschen. Alle deine Daten werden unwiderruflich entfernt." },
 { title: "9. Speicherdauer", content: "Deine Daten werden gespeichert solange dein Account aktiv ist. Nach Loeschung werden alle Daten innerhalb von 30 Tagen entfernt." },
];

const STATIC_IMPRESSUM: Record<string, string> = {
 name: "Lumnos Companion",
 description: "KI-gestütztes Lernen für deutsche Schüler",
 email: "support@lumnos-companion.de",
 haftungsausschluss: "Die Inhalte dieser App wurden mit größter Sorgfalt erstellt. Für die Richtigkeit, Vollständigkeit und Aktualität der Inhalte können wir jedoch keine Gewähr übernehmen. Die KI-generierten Antworten ersetzen keinen professionellen Unterricht.",
 urheberrecht: "Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen dem deutschen Urheberrecht.",
};

function getSectionIcon(title: string) {
 if (title.includes("Cookie")) return <Cookie className="w-5 h-5 text-orange-400" />;
 if (title.includes("loeschen") || title.includes("Loeschung")) return <Trash2 className="w-5 h-5 text-red-400" />;
 if (title.includes("Rechte") || title.includes("DSGVO")) return <Scale className="w-5 h-5 text-blue-400" />;
 if (title.includes("Verantwortlicher")) return <Mail className="w-5 h-5 text-indigo-400" />;
 if (title.includes("Daten") && title.includes("erheben")) return <Eye className="w-5 h-5 text-purple-400" />;
 if (title.includes("Zahlungs")) return <Shield className="w-5 h-5 text-emerald-400" />;
 return <Lock className="w-5 h-5 text-green-400" />;
}

export default function DatenschutzPage() {
 const [sections, setSections] = useState<Section[]>(STATIC_SECTIONS);
 const [loading, setLoading] = useState(true);
 const [view, setView] = useState<"datenschutz" | "impressum">("datenschutz");
 const [impressum, setImpressum] = useState<Record<string, string>>(STATIC_IMPRESSUM);

 useEffect(() => {
 const fetchData = async () => {
 try {
 const [dsRes, impRes] = await Promise.all([
 fetch(`${API}/api/legal/datenschutz`).catch(() => null),
 fetch(`${API}/api/legal/impressum`).catch(() => null),
 ]);
 if (dsRes && dsRes.ok) {
 const ds = await dsRes.json();
 if (ds.sections && ds.sections.length > 0) setSections(ds.sections);
 }
 if (impRes && impRes.ok) {
 const imp = await impRes.json();
 if (imp.content) setImpressum(imp.content);
 }
 } catch {
 // Static fallback already set as default
 }
 setLoading(false);
 };
 fetchData();
 }, []);

 if (loading) {
 return (
 <div className="flex items-center justify-center h-64">
 <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
 </div>
 );
 }

 return (
 <div className="max-w-3xl mx-auto p-6 space-y-6">
 <div className="text-center">
 <div
 className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
 style={{
 background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
 boxShadow: "0 4px 20px rgba(16,185,129,0.3)",
 }}
 >
 <Shield className="w-8 h-8 text-white" />
 </div>
 <h1 className="text-3xl font-bold text-white">Rechtliches</h1>
 </div>

 {/* Tab Toggle */}
 <div className="flex gap-2 justify-center">
 <button
 onClick={() => setView("datenschutz")}
 className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
 view === "datenschutz"
 ? "bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-lg shadow-indigo-500/25"
 : "text-slate-400 hover:text-slate-300 bg-[var(--input-bg)] border border-[var(--border-color)]"
 }`}
 >
 <Lock className="w-4 h-4" /> Datenschutz
 </button>
 <button
 onClick={() => setView("impressum")}
 className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
 view === "impressum"
 ? "bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-lg shadow-indigo-500/25"
 : "text-slate-400 hover:text-slate-300 bg-[var(--input-bg)] border border-[var(--border-color)]"
 }`}
 >
 <FileText className="w-4 h-4" /> Impressum
 </button>
 </div>

 {view === "datenschutz" && (
 <div className="space-y-4">
 {sections.map((s, i) => (
 <div
 key={i}
 className="rounded-xl p-5"
 style={{
 background: "var(--bg-card)",
 border: "1px solid var(--border-color)",
 backdropFilter: "blur(10px)",
 }}
 >
 <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
 {getSectionIcon(s.title)}
 {s.title}
 </h2>
 <p className="text-slate-400 text-sm leading-relaxed">{s.content}</p>
 </div>
 ))}
 </div>
 )}

 {view === "impressum" && (
 <div
 className="rounded-xl p-6 space-y-4"
 style={{
 background: "var(--bg-card)",
 border: "1px solid var(--border-color)",
 backdropFilter: "blur(10px)",
 }}
 >
 <h2 className="text-xl font-semibold text-white">{impressum.name || "Lumnos Companion"}</h2>
 <p className="text-slate-400">{impressum.description}</p>
 <div className="space-y-3 text-sm text-slate-400">
 <p className="flex items-center gap-2">
 <Mail className="w-4 h-4 text-indigo-400" />
 <strong className="text-slate-300">E-Mail:</strong> {impressum.email}
 </p>
 <div>
 <p className="text-slate-300 font-medium mb-1">Haftungsausschluss:</p>
 <p>{impressum.haftungsausschluss}</p>
 </div>
 <div>
 <p className="text-slate-300 font-medium mb-1">Urheberrecht:</p>
 <p>{impressum.urheberrecht}</p>
 </div>
 </div>
 </div>
 )}
 </div>
 );
}
