import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { GraduationCap, Users, Plus, Copy, CheckCircle, Loader2, Trophy, Flame } from "lucide-react";

const API = import.meta.env.VITE_API_URL || "";

interface Student {
  id: number; username: string; full_name: string; grade: string;
  xp: number; level: number; streak: number; quizzes: number;
}
interface ClassInfo {
  id: number; school_name: string; class_code: string; student_count: number;
  max_students: number; is_active: boolean; students: Student[]; created_at: string;
}

export default function SchoolPage() {
  const [view, setView] = useState<"overview" | "create" | "join">("overview");
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [myClass, setMyClass] = useState<{ class_code: string | null; school_name: string | null }>({ class_code: null, school_name: null });
  const [schoolName, setSchoolName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState("");
  const [message, setMessage] = useState("");
  const token = localStorage.getItem("lumnos_token");

  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

  const fetchData = async () => {
    try {
      const [dashRes, myRes] = await Promise.all([
        fetch(`${API}/api/school/dashboard`, { headers }),
        fetch(`${API}/api/school/my-class`, { headers }),
      ]);
      if (dashRes.ok) { const d = await dashRes.json(); setClasses(d.classes || []); }
      if (myRes.ok) { const m = await myRes.json(); setMyClass(m); }
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchData(); }, []);

  const createClass = async () => {
    if (!schoolName.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/school/create?school_name=${encodeURIComponent(schoolName)}`, { method: "POST", headers });
      if (res.ok) {
        const d = await res.json();
        setMessage(`Klasse erstellt! Code: ${d.class_code}`);
        setView("overview");
        fetchData();
      }
    } catch { setMessage("Fehler beim Erstellen"); }
    setLoading(false);
  };

  const joinClass = async () => {
    if (!joinCode.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/school/join/${joinCode.trim().toUpperCase()}`, { method: "POST", headers });
      if (res.ok) {
        const d = await res.json();
        setMessage(d.message);
        setView("overview");
        fetchData();
      }
    } catch { setMessage("Code nicht gefunden"); }
    setLoading(false);
  };

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(code);
    setTimeout(() => setCopied(""), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mx-auto mb-4">
          <GraduationCap className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Schul-Lizenzen</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-2">Klassen verwalten und beitreten</p>
      </div>

      {message && (
        <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-xl p-4 text-center text-green-700 dark:text-green-300">
          {message}
        </div>
      )}

      {/* Student view - show current class */}
      {myClass.class_code && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Du bist in der Klasse <strong>{myClass.school_name}</strong> (Code: {myClass.class_code})
          </p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3 justify-center">
        <Button onClick={() => setView("create")} variant={view === "create" ? "default" : "outline"}>
          <Plus className="w-4 h-4 mr-1" /> Klasse erstellen
        </Button>
        <Button onClick={() => setView("join")} variant={view === "join" ? "default" : "outline"}>
          <Users className="w-4 h-4 mr-1" /> Klasse beitreten
        </Button>
      </div>

      {/* Create Class */}
      {view === "create" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 max-w-md mx-auto">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Neue Klasse erstellen</h2>
          <Input placeholder="Schulname (z.B. Gymnasium Berlin)" value={schoolName} onChange={(e) => setSchoolName(e.target.value)} className="mb-4" />
          <Button onClick={createClass} disabled={loading || !schoolName.trim()} className="w-full">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
            Klasse erstellen
          </Button>
          <p className="text-xs text-gray-500 mt-3">Alle Schüler in deiner Klasse erhalten automatisch Max-Zugang.</p>
        </div>
      )}

      {/* Join Class */}
      {view === "join" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 max-w-md mx-auto">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Klasse beitreten</h2>
          <Input placeholder="Klassen-Code (z.B. KLASSE-ABCD)" value={joinCode} onChange={(e) => setJoinCode(e.target.value.toUpperCase())} className="mb-4 text-center font-mono tracking-widest" />
          <Button onClick={joinClass} disabled={loading || joinCode.length < 6} className="w-full">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Users className="w-4 h-4 mr-2" />}
            Beitreten
          </Button>
        </div>
      )}

      {/* Teacher Dashboard - Classes */}
      {classes.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Meine Klassen</h2>
          {classes.map((c) => (
            <div key={c.id} className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">{c.school_name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="font-mono text-sm text-purple-600 bg-purple-50 dark:bg-purple-900/30 px-2 py-0.5 rounded">{c.class_code}</span>
                    <button onClick={() => copyCode(c.class_code)} className="text-gray-400 hover:text-purple-500">
                      {copied === c.class_code ? <CheckCircle className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <Badge variant={c.is_active ? "default" : "secondary"}>
                  {c.student_count}/{c.max_students} Schüler
                </Badge>
              </div>

              {c.students.length > 0 && (
                <div className="space-y-2">
                  <div className="grid grid-cols-5 gap-2 text-xs font-semibold text-gray-500 px-2">
                    <span>Schüler</span><span>Level</span><span>XP</span><span>Streak</span><span>Quizze</span>
                  </div>
                  {c.students.map((s) => (
                    <div key={s.id} className="grid grid-cols-5 gap-2 items-center p-2 rounded-lg bg-gray-50 dark:bg-gray-700 text-sm">
                      <span className="font-medium text-gray-900 dark:text-white truncate">{s.full_name || s.username}</span>
                      <span className="text-purple-600 font-mono">Lv.{s.level}</span>
                      <span className="flex items-center gap-1"><Trophy className="w-3 h-3 text-yellow-500" />{s.xp}</span>
                      <span className="flex items-center gap-1"><Flame className="w-3 h-3 text-orange-500" />{s.streak}d</span>
                      <span className="text-gray-600 dark:text-gray-400">{s.quizzes}</span>
                    </div>
                  ))}
                </div>
              )}
              {c.students.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-4">Noch keine Schüler beigetreten. Teile den Code!</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pricing Info */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-800">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 text-center">Schul-Pakete</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center border border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold">Klassen-Lizenz</h3>
            <p className="text-2xl font-bold text-blue-600 my-2">49,99 EUR/Monat</p>
            <p className="text-xs text-gray-500">Bis zu 30 Schüler</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center border-2 border-blue-500">
            <h3 className="font-semibold">Schul-Lizenz</h3>
            <p className="text-2xl font-bold text-blue-600 my-2">299,99 EUR/Monat</p>
            <p className="text-xs text-gray-500">Bis zu 300 Schüler</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center border border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold">Enterprise</h3>
            <p className="text-2xl font-bold text-blue-600 my-2">Auf Anfrage</p>
            <p className="text-xs text-gray-500">Unbegrenzt</p>
          </div>
        </div>
      </div>
    </div>
  );
}
