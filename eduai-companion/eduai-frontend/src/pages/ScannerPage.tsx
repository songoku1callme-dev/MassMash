import { useState, useCallback, useEffect, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Camera, Upload, BookOpen, Lock, Loader2, Clipboard, X } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { visionApi } from "../services/api";
import FachSelector from "../components/FachSelector";

export default function ScannerPage() {
 const { user } = useAuthStore();
 const tier = user?.subscription_tier || "free";
 const isPro = tier === "pro" || tier === "max";

 const [fach, setFach] = useState("");
 const [file, setFile] = useState<File | null>(null);
 const [preview, setPreview] = useState<string | null>(null);
 const [frage, setFrage] = useState("");
 const [scanning, setScanning] = useState(false);
 const [streamText, setStreamText] = useState("");
 const [result, setResult] = useState<string | null>(null);
 const [resultModel, setResultModel] = useState("");
 const [error, setError] = useState("");
 const [showUpsell, setShowUpsell] = useState(false);
 const dropRef = useRef<HTMLDivElement>(null);

 // Create preview URL when file changes
 useEffect(() => {
  if (file) {
   const url = URL.createObjectURL(file);
   setPreview(url);
   return () => URL.revokeObjectURL(url);
  }
  setPreview(null);
 }, [file]);

 // Handle paste (Ctrl+V) for images
 useEffect(() => {
  const handlePaste = (e: ClipboardEvent) => {
   const items = e.clipboardData?.items;
   if (!items) return;
   for (const item of items) {
    if (item.type.startsWith("image/")) {
     e.preventDefault();
     const blob = item.getAsFile();
     if (blob) {
      setFile(blob);
      setResult(null);
      setStreamText("");
      setError("");
     }
     break;
    }
   }
  };
  document.addEventListener("paste", handlePaste);
  return () => document.removeEventListener("paste", handlePaste);
 }, []);

 const handleDrop = useCallback((e: React.DragEvent) => {
  e.preventDefault();
  const droppedFile = e.dataTransfer.files[0];
  if (droppedFile && droppedFile.type.startsWith("image/")) {
   setFile(droppedFile);
   setResult(null);
   setStreamText("");
   setError("");
  }
 }, []);

 const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
  const selected = e.target.files?.[0];
  if (selected) {
   setFile(selected);
   setResult(null);
   setStreamText("");
   setError("");
  }
 };

 const handleScan = async () => {
  if (!isPro) {
   setShowUpsell(true);
   return;
  }
  if (!file) return;

  setScanning(true);
  setResult(null);
  setStreamText("");
  setError("");

  try {
   // Try streaming first for live display
   const response = await visionApi.analyseStream(file, frage || undefined, fach || undefined);

   if (!response.body) {
    // Fallback to non-streaming
    const data = await visionApi.analyse(file, frage || undefined, fach || undefined);
    setResult(data.analyse);
    setResultModel(data.model);
    setScanning(false);
    return;
   }

   const reader = response.body.getReader();
   const decoder = new TextDecoder();
   let accumulated = "";
   let model = "";

   while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n");

    for (const line of lines) {
     if (!line.startsWith("data: ")) continue;
     const payload = line.slice(6);
     try {
      const parsed = JSON.parse(payload);
      if (parsed.content) {
       accumulated += parsed.content;
       setStreamText(accumulated);
      }
      if (parsed.model) {
       model = parsed.model;
      }
      if (parsed.error) {
       setError(parsed.error);
      }
     } catch {
      // Skip invalid JSON chunks
     }
    }
   }

   if (accumulated) {
    setResult(accumulated);
    setResultModel(model);
   }
  } catch (err) {
   setError(err instanceof Error ? err.message : "Bild-Analyse fehlgeschlagen");
  } finally {
   setScanning(false);
  }
 };

 // Free-user upsell modal
 if (showUpsell) {
  return (
   <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--lumnos-bg)" }}>
    <Card className="max-w-md w-full shadow-xl">
     <CardContent className="p-8 text-center space-y-6">
      <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
       <Lock className="w-8 h-8 text-white" />
      </div>
      <h2 className="text-2xl font-bold text-white">
       Pro-Feature
      </h2>
      <p className="text-slate-400">
       Der Schulbuch-Scanner mit KI-Vision ist ein exklusives Feature für Pro- und Max-Abonnenten.
       Scanne Aufgaben und erhalte Schritt-für-Schritt Lösungen!
      </p>
      <div className="bg-gradient-to-r from-purple-900/30 to-indigo-900/30 rounded-xl p-4 border border-purple-500/20">
       <p className="text-lg font-bold text-purple-300">
        Ab 4,99 EUR/Monat
       </p>
       <p className="text-sm text-purple-400">
        Unbegrenzt scannen + alle Premium-Features
       </p>
      </div>
      <div className="flex gap-3">
       <Button variant="outline" onClick={() => setShowUpsell(false)} className="flex-1">
        Zurück
       </Button>
       <Button
        className="flex-1 bg-gradient-to-r from-purple-600 to-indigo-600"
        onClick={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "pricing" }))}
       >
        Upgrade auf Pro
       </Button>
      </div>
     </CardContent>
    </Card>
   </div>
  );
 }

 return (
  <div className="min-h-screen p-4 md:p-8" style={{ background: "var(--lumnos-bg)" }}>
   <div className="max-w-2xl mx-auto space-y-6">
    <div className="text-center">
     <h1 className="text-3xl font-bold text-white flex items-center justify-center gap-3">
      <Camera className="w-8 h-8 text-indigo-400" />
      Schulbuch-Scanner
     </h1>
     <p className="text-slate-400 mt-2">
      Fotografiere eine Aufgabe — KI analysiert und löst sie Schritt für Schritt
     </p>
    </div>

    {/* Fach Selector */}
    <Card className="border border-indigo-500/20 bg-[var(--lumnos-surface)]">
     <CardContent className="p-6">
      <label className="text-sm font-medium text-slate-400 mb-3 block">
       Fach wählen (optional)
      </label>
      <FachSelector value={fach} onChange={setFach} />
     </CardContent>
    </Card>

    {/* Upload Area with Drag & Drop + Paste */}
    <Card className="border border-indigo-500/20 bg-[var(--lumnos-surface)]">
     <CardContent className="p-6">
      <div
       ref={dropRef}
       onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add("border-indigo-400"); }}
       onDragLeave={(e) => { e.currentTarget.classList.remove("border-indigo-400"); }}
       onDrop={(e) => { e.currentTarget.classList.remove("border-indigo-400"); handleDrop(e); }}
       className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
        file
         ? "border-green-400 bg-green-500/10"
         : "border-slate-600 hover:border-indigo-400"
       }`}
      >
       {file && preview ? (
        <div className="space-y-3">
         <div className="relative inline-block">
          <img src={preview} alt="Vorschau" className="max-h-48 rounded-lg mx-auto" />
          <button
           onClick={() => { setFile(null); setResult(null); setStreamText(""); }}
           className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
          >
           <X className="w-4 h-4" />
          </button>
         </div>
         <p className="font-medium text-white">{file.name}</p>
         <p className="text-sm text-slate-400">
          {(file.size / 1024).toFixed(0)} KB
         </p>
        </div>
       ) : (
        <div className="space-y-4">
         <div className="w-16 h-16 mx-auto rounded-full bg-indigo-500/10 flex items-center justify-center">
          <Upload className="w-8 h-8 text-indigo-400" />
         </div>
         <div>
          <p className="font-medium text-white">
           Bild hochladen
          </p>
          <p className="text-sm text-slate-400 mt-1">
           Drag & Drop, Einfügen (Strg+V) oder klicken
          </p>
         </div>
         <div className="flex gap-3 justify-center flex-wrap">
          <label className="cursor-pointer">
           <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFileSelect}
           />
           <Button variant="outline" size="sm" asChild>
            <span><Upload className="w-4 h-4 mr-2" />Datei wählen</span>
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
          <Button variant="outline" size="sm" onClick={() => navigator.clipboard.read?.()}>
           <Clipboard className="w-4 h-4 mr-2" />Einfügen
          </Button>
         </div>
        </div>
       )}
      </div>
     </CardContent>
    </Card>

    {/* Optional question input */}
    <Card className="border border-indigo-500/20 bg-[var(--lumnos-surface)]">
     <CardContent className="p-6">
      <label className="text-sm font-medium text-slate-400 mb-2 block">
       Zusätzliche Frage (optional)
      </label>
      <input
       type="text"
       value={frage}
       onChange={(e) => setFrage(e.target.value)}
       placeholder="z.B. Erkläre Aufgabe 3 genauer..."
       className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white placeholder:text-slate-500 focus:border-indigo-400 focus:outline-none"
      />
     </CardContent>
    </Card>

    {/* Scan Button */}
    <Button
     onClick={handleScan}
     disabled={scanning || !file}
     className="w-full h-12 text-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
    >
     {scanning ? (
      <>
       <Loader2 className="w-5 h-5 mr-2 animate-spin" />
       KI analysiert...
      </>
     ) : (
      <>
       <BookOpen className="w-5 h-5 mr-2" />
       Bild analysieren
      </>
     )}
    </Button>

    {error && (
     <div className="p-4 rounded-lg bg-red-900/20 border border-red-500/20 text-red-400 text-center">
      {error}
     </div>
    )}

    {/* Streaming / Result */}
    {(streamText || result) && (
     <Card className="border border-green-500/20 bg-[var(--lumnos-surface)]">
      <CardContent className="p-6 space-y-4">
       <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-white">
         KI-Analyse
        </h3>
        {resultModel && (
         <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">
          {resultModel.split("/").pop()}
         </span>
        )}
       </div>
       <div className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
        {result || streamText}
        {scanning && <span className="animate-pulse ml-1">|</span>}
       </div>
      </CardContent>
     </Card>
    )}
   </div>
  </div>
 );
}
