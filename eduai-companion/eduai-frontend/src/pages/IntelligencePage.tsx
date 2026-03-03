import { useState } from "react";
import { intelligenceApi } from "../services/api";
import { Button } from "@/components/ui/button";
import { Brain, BookOpen, HelpCircle, Search, Calendar, Loader2 } from "lucide-react";

type Tab = "lernstil" | "feynman" | "sokrates" | "wissensscan" | "wochenplan";

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

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "lernstil", label: "Lernstil", icon: <Brain className="w-4 h-4" /> },
    { id: "feynman", label: "Feynman", icon: <BookOpen className="w-4 h-4" /> },
    { id: "sokrates", label: "Sokrates", icon: <HelpCircle className="w-4 h-4" /> },
    { id: "wissensscan", label: "Wissens-Scan", icon: <Search className="w-4 h-4" /> },
    { id: "wochenplan", label: "Wochenplan", icon: <Calendar className="w-4 h-4" /> },
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">KI-Intelligenz</h1>
      <p className="text-gray-500 dark:text-gray-400 mb-6">Smarte Lern-Tools für personalisiertes Lernen</p>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              tab === t.id
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Lernstil */}
      {tab === "lernstil" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold mb-4 dark:text-white">Lernstil-Erkennung</h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Basierend auf deinen Chat-Nachrichten erkennt die KI deinen Lernstil (Visuell, Auditiv, Kinesthetisch, Lesen).
          </p>
          <Button onClick={detectLernstil} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Brain className="w-4 h-4 mr-2" />}
            Lernstil erkennen
          </Button>
          {lernstilResult && (
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <p className="text-lg font-bold text-blue-700 dark:text-blue-300 mb-2">
                Dein Lernstil: {lernstilResult.lernstil.toUpperCase()}
              </p>
              <p className="text-gray-600 dark:text-gray-300 mb-3">{lernstilResult.beschreibung}</p>
              <p className="font-medium text-gray-700 dark:text-gray-200 mb-1">Tipps:</p>
              <ul className="list-disc list-inside space-y-1 text-gray-600 dark:text-gray-300">
                {lernstilResult.tipps.map((t, i) => <li key={i}>{t}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Feynman */}
      {tab === "feynman" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold mb-2 dark:text-white">Feynman-Technik</h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Erkläre ein Thema in eigenen Worten. Die KI bewertet dein Verständnis (1-10) und zeigt Lücken auf.
          </p>
          <input
            value={feynmanThema}
            onChange={(e) => setFeynmanThema(e.target.value)}
            placeholder="Thema (z.B. Photosynthese, Quadratische Gleichungen)"
            className="w-full mb-3 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
          <textarea
            value={feynmanErklärung}
            onChange={(e) => setFeynmanErklärung(e.target.value)}
            placeholder="Erkläre das Thema in deinen eigenen Worten..."
            rows={6}
            className="w-full mb-3 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
          <Button onClick={submitFeynman} disabled={loading || !feynmanThema || !feynmanErklärung}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <BookOpen className="w-4 h-4 mr-2" />}
            Bewertung anfordern
          </Button>
          {feynmanResult && (
            <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <p className="whitespace-pre-wrap text-gray-700 dark:text-gray-200">{feynmanResult}</p>
            </div>
          )}
        </div>
      )}

      {/* Sokrates */}
      {tab === "sokrates" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold mb-2 dark:text-white">Sokrates-Methode</h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Stelle eine Frage und die KI fuehrt dich durch gezielte Gegenfragen zur Antwort.
          </p>
          <input
            value={sokratesFrage}
            onChange={(e) => setSokratesFrage(e.target.value)}
            placeholder="Deine Frage (z.B. Warum ist der Himmel blau?)"
            className="w-full mb-3 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
          <Button onClick={submitSokrates} disabled={loading || !sokratesFrage}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <HelpCircle className="w-4 h-4 mr-2" />}
            Sokratisch fragen
          </Button>
          {sokratesResult && (
            <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <p className="whitespace-pre-wrap text-gray-700 dark:text-gray-200">{sokratesResult}</p>
            </div>
          )}
        </div>
      )}

      {/* Wissensscan */}
      {tab === "wissensscan" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold mb-2 dark:text-white">Wissensluecken-Scanner</h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            10 Diagnose-Fragen um deine Stärken und Schwächen in einem Fach zu erkennen.
          </p>
          {scanQuestions.length === 0 && !scanResult && (
            <div>
              <select
                value={scanSubject}
                onChange={(e) => setScanSubject(e.target.value)}
                className="mb-3 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
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
                <div key={qi} className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <p className="font-medium dark:text-white mb-2">{qi + 1}. {q.frage}</p>
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
                            : "bg-white dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-gray-500"
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
                <p className="text-4xl font-bold text-blue-600 dark:text-blue-400">{scanResult.score}%</p>
                <p className="text-gray-500 dark:text-gray-400">{scanResult.correct}/{scanResult.total} richtig</p>
              </div>
              {scanResult.gaps.length > 0 && (
                <div className="mb-3">
                  <p className="font-medium text-red-600 dark:text-red-400 mb-1">Lücken:</p>
                  <div className="flex flex-wrap gap-2">
                    {scanResult.gaps.map((g: string, i: number) => (
                      <span key={i} className="px-3 py-1 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 rounded-full text-sm">{g}</span>
                    ))}
                  </div>
                </div>
              )}
              {scanResult.strengths.length > 0 && (
                <div className="mb-3">
                  <p className="font-medium text-green-600 dark:text-green-400 mb-1">Stärken:</p>
                  <div className="flex flex-wrap gap-2">
                    {scanResult.strengths.map((s: string, i: number) => (
                      <span key={i} className="px-3 py-1 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 rounded-full text-sm">{s}</span>
                    ))}
                  </div>
                </div>
              )}
              <p className="text-gray-600 dark:text-gray-300 mt-3">{scanResult.recommendation}</p>
              <Button className="mt-3" onClick={() => { setScanQuestions([]); setScanResult(null); }}>
                Neuen Scan starten
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Wochenplan */}
      {tab === "wochenplan" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold mb-2 dark:text-white">Personalisierter Wochenplan</h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Basierend auf deinen Schwächen und kommenden Klausuren erstellt die KI deinen optimalen Wochenplan.
          </p>
          <Button onClick={loadWeeklyPlan} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Calendar className="w-4 h-4 mr-2" />}
            Wochenplan erstellen
          </Button>
          {weeklyPlan && (
            <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
              <p className="whitespace-pre-wrap text-gray-700 dark:text-gray-200">{weeklyPlan}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
