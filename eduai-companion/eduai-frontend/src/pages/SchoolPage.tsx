import { useState, useEffect } from "react";
import { GraduationCap, Users, Plus, Copy, CheckCircle, Loader2, Trophy, Flame, School, Building2, Sparkles, Mail, AlertCircle } from "lucide-react";

const API = import.meta.env.VITE_API_URL || "";

interface Student {
  id: number; username: string; full_name: string; grade: string;
  xp: number; level: number; streak: number; quizzes: number;
}
interface ClassInfo {
  id: number; school_name: string; class_code: string; student_count: number;
  max_students: number; is_active: boolean; students: Student[]; created_at: string;
}

type PackageType = "klassen" | "schul" | "enterprise" | null;

export default function SchoolPage() {
  const [view, setView] = useState<"overview" | "create" | "join">("overview");
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [myClass, setMyClass] = useState<{ class_code: string | null; school_name: string | null }>({ class_code: null, school_name: null });
  const [schoolName, setSchoolName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState("");
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [selectedPackage, setSelectedPackage] = useState<PackageType>(null);
  const [contactSent, setContactSent] = useState(false);
  const token = localStorage.getItem("lumnos_token");

  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

  const fetchData = async () => {
    try {
      const [dashRes, myRes] = await Promise.all([
        fetch(`${API}/api/school/dashboard`, { headers }).catch(() => null),
        fetch(`${API}/api/school/my-class`, { headers }).catch(() => null),
      ]);
      if (dashRes && dashRes.ok) { const d = await dashRes.json(); setClasses(d.classes || []); }
      if (myRes && myRes.ok) { const m = await myRes.json(); setMyClass(m); }
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchData(); }, []);

  const createClass = async () => {
    if (!schoolName.trim()) return;
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch(`${API}/api/school/create?school_name=${encodeURIComponent(schoolName)}`, { method: "POST", headers });
      if (res.ok) {
        const d = await res.json();
        setMessage({ text: `Klasse erstellt! Code: ${d.class_code}`, type: "success" });
        setSchoolName("");
        setView("overview");
        fetchData();
      } else {
        const errData = await res.json().catch(() => null);
        setMessage({ text: errData?.detail || "Klasse konnte nicht erstellt werden. Bitte versuche es erneut.", type: "error" });
      }
    } catch {
      setMessage({ text: "Verbindung zum Server fehlgeschlagen. Bitte pruefe deine Internetverbindung.", type: "error" });
    }
    setLoading(false);
  };

  const joinClass = async () => {
    if (!joinCode.trim()) return;
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch(`${API}/api/school/join/${joinCode.trim().toUpperCase()}`, { method: "POST", headers });
      if (res.ok) {
        const d = await res.json();
        setMessage({ text: d.message, type: "success" });
        setJoinCode("");
        setView("overview");
        fetchData();
      } else {
        const errData = await res.json().catch(() => null);
        setMessage({ text: errData?.detail || "Klassen-Code nicht gefunden. Bitte pruefe den Code.", type: "error" });
      }
    } catch {
      setMessage({ text: "Verbindung zum Server fehlgeschlagen. Bitte pruefe deine Internetverbindung.", type: "error" });
    }
    setLoading(false);
  };

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(code);
    setTimeout(() => setCopied(""), 2000);
  };

  const selectPackage = (pkg: PackageType) => {
    setSelectedPackage(pkg);
    if (pkg === "enterprise") {
      setContactSent(false);
    }
  };

  const handleContactEnterprise = () => {
    setContactSent(true);
    setMessage({ text: "Anfrage gesendet! Wir melden uns innerhalb von 24 Stunden.", type: "success" });
  };

  const packages = [
    { id: "klassen" as PackageType, name: "Klassen-Lizenz", price: "49,99", period: "EUR/Monat", students: "Bis zu 30 Schueler", icon: <School className="w-6 h-6" />, popular: false },
    { id: "schul" as PackageType, name: "Schul-Lizenz", price: "299,99", period: "EUR/Monat", students: "Bis zu 300 Schueler", icon: <Building2 className="w-6 h-6" />, popular: true },
    { id: "enterprise" as PackageType, name: "Enterprise", price: "Auf Anfrage", period: "", students: "Unbegrenzt", icon: <Sparkles className="w-6 h-6" />, popular: false },
  ];

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6 overflow-y-auto" style={{ maxHeight: "100vh" }}>
      <div className="text-center">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
          style={{
            background: "linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)",
            boxShadow: "0 4px 20px rgba(99,102,241,0.3)",
          }}
        >
          <GraduationCap className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-white">Schul-Lizenzen</h1>
        <p className="text-slate-400 mt-2">Klassen verwalten und beitreten</p>
      </div>

      {message && (
        <div
          className={`rounded-xl p-4 text-center flex items-center justify-center gap-2 ${
            message.type === "success"
              ? "text-emerald-300"
              : "text-red-300"
          }`}
          style={{
            background: message.type === "success" ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
            border: `1px solid ${message.type === "success" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
          }}
        >
          {message.type === "error" && <AlertCircle className="w-4 h-4 flex-shrink-0" />}
          {message.type === "success" && <CheckCircle className="w-4 h-4 flex-shrink-0" />}
          {message.text}
        </div>
      )}

      {/* Student view - show current class */}
      {myClass.class_code && (
        <div
          className="rounded-xl p-4"
          style={{
            background: "rgba(99,102,241,0.1)",
            border: "1px solid rgba(99,102,241,0.2)",
          }}
        >
          <p className="text-sm text-indigo-300">
            Du bist in der Klasse <strong className="text-white">{myClass.school_name}</strong> (Code: <span className="font-mono">{myClass.class_code}</span>)
          </p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3 justify-center">
        <button
          onClick={() => { setView(view === "create" ? "overview" : "create"); setMessage(null); }}
          className={`flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
            view === "create"
              ? "bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-lg shadow-indigo-500/25"
              : "text-slate-400 hover:text-slate-300 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.08)]"
          }`}
        >
          <Plus className="w-4 h-4" /> Klasse erstellen
        </button>
        <button
          onClick={() => { setView(view === "join" ? "overview" : "join"); setMessage(null); }}
          className={`flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
            view === "join"
              ? "bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-lg shadow-indigo-500/25"
              : "text-slate-400 hover:text-slate-300 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.08)]"
          }`}
        >
          <Users className="w-4 h-4" /> Klasse beitreten
        </button>
      </div>

      {/* Create Class */}
      {view === "create" && (
        <div
          className="rounded-xl p-6 max-w-md mx-auto"
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            backdropFilter: "blur(10px)",
          }}
        >
          <h2 className="text-lg font-semibold text-white mb-4">Neue Klasse erstellen</h2>
          <input
            placeholder="Schulname (z.B. Gymnasium Berlin)"
            value={schoolName}
            onChange={(e) => setSchoolName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createClass()}
            className="w-full mb-4 px-4 py-3 rounded-xl text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          />
          <button
            onClick={createClass}
            disabled={loading || !schoolName.trim()}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
              boxShadow: "0 4px 15px rgba(99,102,241,0.3)",
            }}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Klasse erstellen
          </button>
          <p className="text-xs text-slate-500 mt-3 text-center">Alle Schueler in deiner Klasse erhalten automatisch Max-Zugang.</p>
        </div>
      )}

      {/* Join Class */}
      {view === "join" && (
        <div
          className="rounded-xl p-6 max-w-md mx-auto"
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            backdropFilter: "blur(10px)",
          }}
        >
          <h2 className="text-lg font-semibold text-white mb-4">Klasse beitreten</h2>
          <input
            placeholder="Klassen-Code (z.B. KLASSE-ABCD)"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && joinClass()}
            className="w-full mb-4 px-4 py-3 rounded-xl text-white text-center font-mono tracking-widest placeholder-slate-500 outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          />
          <button
            onClick={joinClass}
            disabled={loading || joinCode.length < 6}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
              boxShadow: "0 4px 15px rgba(99,102,241,0.3)",
            }}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Users className="w-4 h-4" />}
            Beitreten
          </button>
        </div>
      )}

      {/* Teacher Dashboard - Classes */}
      {classes.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-white">Meine Klassen</h2>
          {classes.map((c) => (
            <div
              key={c.id}
              className="rounded-xl p-5"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)",
                backdropFilter: "blur(10px)",
              }}
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-white">{c.school_name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="font-mono text-sm text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">{c.class_code}</span>
                    <button onClick={() => copyCode(c.class_code)} className="text-slate-500 hover:text-indigo-400 transition-colors">
                      {copied === c.class_code ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <span className={`text-xs px-3 py-1 rounded-full font-medium ${c.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-slate-500/10 text-slate-400"}`}>
                  {c.student_count}/{c.max_students} Schueler
                </span>
              </div>

              {c.students.length > 0 && (
                <div className="space-y-2">
                  <div className="grid grid-cols-5 gap-2 text-xs font-semibold text-slate-500 px-2">
                    <span>Schueler</span><span>Level</span><span>XP</span><span>Streak</span><span>Quizze</span>
                  </div>
                  {c.students.map((s) => (
                    <div
                      key={s.id}
                      className="grid grid-cols-5 gap-2 items-center p-2 rounded-lg text-sm"
                      style={{ background: "rgba(255,255,255,0.03)" }}
                    >
                      <span className="font-medium text-white truncate">{s.full_name || s.username}</span>
                      <span className="text-indigo-400 font-mono">Lv.{s.level}</span>
                      <span className="flex items-center gap-1 text-slate-300"><Trophy className="w-3 h-3 text-yellow-500" />{s.xp}</span>
                      <span className="flex items-center gap-1 text-slate-300"><Flame className="w-3 h-3 text-orange-500" />{s.streak}d</span>
                      <span className="text-slate-400">{s.quizzes}</span>
                    </div>
                  ))}
                </div>
              )}
              {c.students.length === 0 && (
                <p className="text-sm text-slate-500 text-center py-4">Noch keine Schueler beigetreten. Teile den Code!</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pricing Packages — selectable */}
      <div
        className="rounded-xl p-6"
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <h2 className="text-lg font-semibold text-white mb-6 text-center">Schul-Pakete</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {packages.map((pkg) => (
            <button
              key={pkg.id}
              onClick={() => selectPackage(pkg.id)}
              className={`relative rounded-xl p-5 text-center transition-all cursor-pointer text-left ${
                selectedPackage === pkg.id
                  ? "ring-2 ring-indigo-500 shadow-lg shadow-indigo-500/20"
                  : "hover:ring-1 hover:ring-white/20"
              }`}
              style={{
                background: selectedPackage === pkg.id ? "rgba(99,102,241,0.1)" : "rgba(255,255,255,0.03)",
                border: `1px solid ${selectedPackage === pkg.id ? "rgba(99,102,241,0.3)" : "rgba(255,255,255,0.08)"}`,
              }}
            >
              {pkg.popular && (
                <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 text-[10px] font-bold uppercase tracking-wider px-3 py-0.5 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 text-white">
                  Beliebt
                </span>
              )}
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center mx-auto mb-3 ${
                selectedPackage === pkg.id ? "text-indigo-400" : "text-slate-400"
              }`} style={{ background: "rgba(255,255,255,0.05)" }}>
                {pkg.icon}
              </div>
              <h3 className="font-semibold text-white text-sm">{pkg.name}</h3>
              <p className="text-2xl font-bold text-indigo-400 my-2">
                {pkg.price}{" "}
                {pkg.period && <span className="text-xs font-normal text-slate-500">{pkg.period}</span>}
              </p>
              <p className="text-xs text-slate-500">{pkg.students}</p>
              {selectedPackage === pkg.id && (
                <div className="mt-3 text-xs text-indigo-300 flex items-center justify-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Ausgewaehlt
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Selected package action */}
        {selectedPackage && (
          <div className="mt-6 text-center">
            {selectedPackage === "enterprise" ? (
              <div className="space-y-3">
                <p className="text-sm text-slate-400">Fuer Enterprise-Loesungen kontaktiere uns direkt:</p>
                <button
                  onClick={handleContactEnterprise}
                  disabled={contactSent}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-white font-semibold transition-all disabled:opacity-50"
                  style={{
                    background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                    boxShadow: "0 4px 15px rgba(99,102,241,0.3)",
                  }}
                >
                  <Mail className="w-4 h-4" />
                  {contactSent ? "Anfrage gesendet!" : "Kontakt aufnehmen"}
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-slate-400">
                  {selectedPackage === "klassen" ? "Perfekt fuer einzelne Klassen mit bis zu 30 Schuelern." : "Ideal fuer ganze Schulen mit bis zu 300 Schuelern."}
                </p>
                <button
                  onClick={() => {
                    setView("create");
                    setMessage({ text: `${selectedPackage === "klassen" ? "Klassen" : "Schul"}-Lizenz ausgewaehlt! Erstelle jetzt deine erste Klasse.`, type: "success" });
                  }}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-white font-semibold transition-all"
                  style={{
                    background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                    boxShadow: "0 4px 15px rgba(99,102,241,0.3)",
                  }}
                >
                  <Plus className="w-4 h-4" />
                  Jetzt starten
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
