import { useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Camera, Upload, BookOpen, Brain, Layers, Lock } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import FachSelector from "../components/FachSelector";

const SCAN_STEPS = [
  { icon: "magnifier", label: "Text wird erkannt..." },
  { icon: "brain", label: "Thema wird analysiert..." },
  { icon: "question", label: "Quiz-Fragen werden generiert..." },
];

export default function ScannerPage() {
  const { user } = useAuthStore();
  const tier = user?.subscription_tier || "free";
  const isPro = tier === "pro" || tier === "max";

  const [fach, setFach] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [result, setResult] = useState<{
    thema: string;
    lernziele: string[];
    quiz_count: number;
    karteikarten_count: number;
  } | null>(null);
  const [showUpsell, setShowUpsell] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith("image/")) {
      setFile(droppedFile);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) setFile(selected);
  };

  const handleScan = async () => {
    if (!isPro) {
      setShowUpsell(true);
      return;
    }
    if (!file || !fach) return;

    setScanning(true);
    setScanStep(0);

    // Simulate scanning steps (would call backend OCR endpoint)
    for (let i = 0; i < SCAN_STEPS.length; i++) {
      setScanStep(i);
      await new Promise((r) => setTimeout(r, 1500));
    }

    // Simulated result (real implementation calls /api/schulbuch/scan)
    setResult({
      thema: "Quadratische Funktionen",
      lernziele: [
        "Scheitelpunktform verstehen",
        "p-q-Formel anwenden",
        "Parabeln zeichnen und analysieren",
      ],
      quiz_count: 5,
      karteikarten_count: 8,
    });
    setScanning(false);
  };

  // Free-user upsell modal
  if (showUpsell) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <Card className="max-w-md w-full shadow-xl">
          <CardContent className="p-8 text-center space-y-6">
            <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
              <Lock className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Pro-Feature
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Der Schulbuch-Scanner ist ein exklusives Feature für Pro- und Max-Abonnenten.
              Scanne Schulbuchseiten und erhalte automatisch Quiz-Fragen und Karteikarten!
            </p>
            <div className="bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-xl p-4">
              <p className="text-lg font-bold text-purple-700 dark:text-purple-300">
                Ab 4,99 EUR/Monat
              </p>
              <p className="text-sm text-purple-600 dark:text-purple-400">
                Unbegrenzt scannen + alle Premium-Features
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setShowUpsell(false)} className="flex-1">
                Zurück
              </Button>
              <Button className="flex-1 bg-gradient-to-r from-purple-600 to-indigo-600">
                Upgrade auf Pro
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 md:p-8">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center justify-center gap-3">
            <Camera className="w-8 h-8 text-indigo-600" />
            Schulbuch-Scanner
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-2">
            Fotografiere eine Schulbuchseite und erhalte automatisch Quiz-Fragen
          </p>
        </div>

        {/* Fach Selector */}
        <Card>
          <CardContent className="p-6">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 block">
              Fach waehlen
            </label>
            <FachSelector value={fach} onChange={setFach} />
          </CardContent>
        </Card>

        {/* Upload Area */}
        <Card>
          <CardContent className="p-6">
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                file
                  ? "border-green-400 bg-green-50 dark:bg-green-900/20"
                  : "border-gray-300 dark:border-gray-600 hover:border-indigo-400"
              }`}
            >
              {file ? (
                <div className="space-y-3">
                  <div className="w-12 h-12 mx-auto rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                    <BookOpen className="w-6 h-6 text-green-600" />
                  </div>
                  <p className="font-medium text-gray-900 dark:text-white">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024).toFixed(0)} KB
                  </p>
                  <Button variant="outline" size="sm" onClick={() => setFile(null)}>
                    Anderes Bild waehlen
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="w-16 h-16 mx-auto rounded-full bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center">
                    <Upload className="w-8 h-8 text-indigo-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">
                      Schulbuchseite hochladen
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Drag & Drop oder klicke zum Auswaehlen
                    </p>
                  </div>
                  <div className="flex gap-3 justify-center">
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={handleFileSelect}
                      />
                      <Button variant="outline" size="sm" asChild>
                        <span><Upload className="w-4 h-4 mr-2" />Datei waehlen</span>
                      </Button>
                    </label>
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        accept="image/*"
                        capture="environment"
                        className="hidden"
                        onChange={handleFileSelect}
                      />
                      <Button variant="outline" size="sm" asChild>
                        <span><Camera className="w-4 h-4 mr-2" />Kamera</span>
                      </Button>
                    </label>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Scan Button */}
        <Button
          onClick={handleScan}
          disabled={scanning || (!file && isPro)}
          className="w-full h-12 text-lg bg-gradient-to-r from-indigo-600 to-purple-600"
        >
          {scanning ? "Wird gescannt..." : "Scannen & Quiz generieren"}
        </Button>

        {/* Scanning Animation */}
        {scanning && (
          <Card>
            <CardContent className="p-6 space-y-4">
              {SCAN_STEPS.map((s, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-3 transition-opacity ${
                    i <= scanStep ? "opacity-100" : "opacity-30"
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      i < scanStep
                        ? "bg-green-100 text-green-600"
                        : i === scanStep
                        ? "bg-indigo-100 text-indigo-600 animate-pulse"
                        : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {i < scanStep ? "✓" : i + 1}
                  </div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {s.label}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Result */}
        {result && !scanning && (
          <Card className="border-green-200 dark:border-green-800">
            <CardContent className="p-6 space-y-4">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                Scan-Ergebnis
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-xl p-4">
                  <p className="text-sm text-gray-500">Erkanntes Thema</p>
                  <p className="font-bold text-indigo-700 dark:text-indigo-300">
                    {result.thema}
                  </p>
                </div>
                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-xl p-4">
                  <p className="text-sm text-gray-500">Lernziele</p>
                  <p className="font-bold text-purple-700 dark:text-purple-300">
                    {result.lernziele.length} erkannt
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                {result.lernziele.map((lz, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                    <span className="text-green-500">✓</span> {lz}
                  </div>
                ))}
              </div>
              <div className="flex gap-3">
                <Button className="flex-1 gap-2">
                  <Brain className="w-4 h-4" />
                  Quiz starten ({result.quiz_count} Fragen)
                </Button>
                <Button variant="outline" className="flex-1 gap-2">
                  <Layers className="w-4 h-4" />
                  Karteikarten ({result.karteikarten_count})
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
