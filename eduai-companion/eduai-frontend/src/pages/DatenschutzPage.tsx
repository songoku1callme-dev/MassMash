import { useState, useEffect } from "react";
import { Shield, FileText, Lock, Trash2, Cookie } from "lucide-react";
import { Button } from "@/components/ui/button";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface Section { title: string; content: string; }

export default function DatenschutzPage() {
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"datenschutz" | "impressum">("datenschutz");
  const [impressum, setImpressum] = useState<Record<string, string>>({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dsRes, impRes] = await Promise.all([
          fetch(`${API}/api/legal/datenschutz`),
          fetch(`${API}/api/legal/impressum`),
        ]);
        if (dsRes.ok) {
          const ds = await dsRes.json();
          setSections(ds.sections || []);
        }
        if (impRes.ok) {
          const imp = await impRes.json();
          setImpressum(imp.content || {});
        }
      } catch {
        setSections([{ title: "Fehler", content: "Datenschutzerklaerung konnte nicht geladen werden." }]);
      }
      setLoading(false);
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center mx-auto mb-4">
          <Shield className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Rechtliches</h1>
      </div>

      {/* Tab Toggle */}
      <div className="flex gap-2 justify-center">
        <Button variant={view === "datenschutz" ? "default" : "outline"} onClick={() => setView("datenschutz")} size="sm">
          <Lock className="w-4 h-4 mr-1" /> Datenschutz
        </Button>
        <Button variant={view === "impressum" ? "default" : "outline"} onClick={() => setView("impressum")} size="sm">
          <FileText className="w-4 h-4 mr-1" /> Impressum
        </Button>
      </div>

      {view === "datenschutz" && (
        <div className="space-y-4">
          {sections.map((s, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                {s.title.includes("Cookie") ? <Cookie className="w-5 h-5 text-orange-500" /> :
                 s.title.includes("loeschen") || s.title.includes("Loeschung") ? <Trash2 className="w-5 h-5 text-red-500" /> :
                 <Lock className="w-5 h-5 text-green-500" />}
                {s.title}
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">{s.content}</p>
            </div>
          ))}
        </div>
      )}

      {view === "impressum" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{impressum.name || "Lumnos Companion"}</h2>
          <p className="text-gray-600 dark:text-gray-400">{impressum.description}</p>
          <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <p><strong>E-Mail:</strong> {impressum.email}</p>
            <p><strong>Haftungsausschluss:</strong> {impressum.haftungsausschluss}</p>
            <p><strong>Urheberrecht:</strong> {impressum.urheberrecht}</p>
          </div>
        </div>
      )}
    </div>
  );
}
