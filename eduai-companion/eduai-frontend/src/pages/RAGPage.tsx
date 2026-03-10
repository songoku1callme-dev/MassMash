import { useState, useEffect, useCallback } from "react";
import { ragApi, type RAGDocument, type RAGStats, type RAGQueryResponse } from "../services/api";
import { ErrorState, PageLoader, EmptyState } from "../components/PageStates";
import { Upload, Search, Loader2, FileText, Trash2, Database, Sparkles, BookOpen, HelpCircle } from "lucide-react";

const SUBJECTS = [
 { value: "general", label: "Allgemein" },
 { value: "math", label: "Mathematik" },
 { value: "english", label: "Englisch" },
 { value: "german", label: "Deutsch" },
 { value: "history", label: "Geschichte" },
 { value: "science", label: "Naturwissenschaften" },
];

export default function RAGPage() {
 const [documents, setDocuments] = useState<RAGDocument[]>([]);
 const [stats, setStats] = useState<RAGStats | null>(null);
 const [uploading, setUploading] = useState(false);
 const [uploadProgress, setUploadProgress] = useState(0);
 const [seeding, setSeeding] = useState(false);
 const [error, setError] = useState("");
 const [success, setSuccess] = useState("");
 const [selectedSubject, setSelectedSubject] = useState("general");
 const [dragOver, setDragOver] = useState(false);
 const [loading, setLoading] = useState(true);
 const [loadError, setLoadError] = useState(false);
 const [query, setQuery] = useState("");
 const [queryResult, setQueryResult] = useState<RAGQueryResponse | null>(null);
 const [querying, setQuerying] = useState(false);
 const [autoSuggestion, setAutoSuggestion] = useState<string | null>(null);

 const loadData = useCallback(async () => {
  setLoadError(false);
  try {
   const [docs, s] = await Promise.all([
    ragApi.listDocuments(),
    ragApi.stats(),
   ]);
   setDocuments(docs);
   setStats(s);
  } catch {
   setLoadError(true);
  } finally {
   setLoading(false);
  }
 }, []);

 useEffect(() => {
  loadData();
 }, [loadData]);

 const handleUpload = async (files: FileList | null) => {
  if (!files || files.length === 0) return;
  setUploading(true);
  setUploadProgress(0);
  setError("");
  setSuccess("");
  setAutoSuggestion(null);
  const total = files.length;
  let uploaded = 0;
  for (const file of Array.from(files)) {
   try {
    const result = await ragApi.uploadFile(file, selectedSubject, "de", file.name);
    uploaded++;
    setUploadProgress(Math.round((uploaded / total) * 100));
    setSuccess(`${file.name}: ${result.chunks_created} Chunks indexiert`);
   } catch (err) {
    setError(`${file.name}: ${err instanceof Error ? err.message : "Upload fehlgeschlagen"}`);
   }
  }
  setUploading(false);
  if (uploaded > 0) {
   loadData();
   setAutoSuggestion("Soll ich dir basierend auf diesem Dokument 5 Lernkarten oder ein 2-Minuten-Quiz erstellen?");
  }
 };

 const handleSeed = async () => {
  setSeeding(true);
  setError("");
  setSuccess("");
  try {
   const result = await ragApi.seed();
   setSuccess(result.message);
   loadData();
  } catch (err) {
   setError(err instanceof Error ? err.message : "Seeding fehlgeschlagen");
  }
  setSeeding(false);
 };

 const handleDelete = async (docId: string) => {
  try {
   await ragApi.deleteDocument(docId);
   setSuccess(`Dokument ${docId} gelöscht`);
   loadData();
  } catch (err) {
   setError(err instanceof Error ? err.message : "Löschen fehlgeschlagen");
  }
 };

 const handleQuery = async () => {
  if (!query.trim()) return;
  setQuerying(true);
  setError("");
  try {
   const result = await ragApi.query({ query: query.trim() });
   setQueryResult(result);
  } catch (err) {
   setError(err instanceof Error ? err.message : "Abfrage fehlgeschlagen");
  }
  setQuerying(false);
 };

 if (loading) return <PageLoader text="Wissensdatenbank wird geladen..." />;
 if (loadError) return <ErrorState message="Fehler beim Laden der Wissensdatenbank." onRetry={() => { setLoading(true); loadData(); }} />;

 return (
  <div className="p-6 max-w-4xl mx-auto">
   <h1 className="text-2xl font-bold theme-text mb-2 flex items-center gap-2">
    <Database className="w-7 h-7 text-purple-500" />
    Wissensdatenbank (RAG)
   </h1>
   <p className="theme-text-secondary mb-6">
    Lade Lehrpläne, Arbeitsblätter oder Texte hoch, damit der KI-Tutor darauf zugreifen kann.
   </p>

   {/* Stats */}
   {stats && (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
     <div className="theme-card rounded-lg p-4 shadow-sm flex items-center gap-3">
      <FileText className="w-5 h-5 text-blue-500" />
      <div>
       <p className="text-sm theme-text-secondary">Dokumente</p>
       <p className="text-2xl font-bold text-blue-600">{stats.total_documents}</p>
      </div>
     </div>
     <div className="theme-card rounded-lg p-4 shadow-sm flex items-center gap-3">
      <Database className="w-5 h-5 text-green-500" />
      <div>
       <p className="text-sm theme-text-secondary">Chunks</p>
       <p className="text-2xl font-bold text-green-600">{stats.total_chunks}</p>
      </div>
     </div>
     <div className="theme-card rounded-lg p-4 shadow-sm flex items-center gap-3">
      <Sparkles className="w-5 h-5 text-purple-500" />
      <div>
       <p className="text-sm theme-text-secondary">Embedding-Dim</p>
       <p className="text-2xl font-bold text-purple-600">{stats.embedding_dim}</p>
      </div>
     </div>
     <div className="theme-card rounded-lg p-4 shadow-sm flex items-center gap-3">
      <HelpCircle className="w-5 h-5 text-amber-500" />
      <div>
       <p className="text-sm theme-text-secondary">Modell</p>
       <p className="text-sm font-medium theme-text-secondary truncate" title={stats.embedding_model}>
        {stats.embedding_model.split("/").pop()}
       </p>
      </div>
     </div>
    </div>
   )}

   {/* Alerts */}
   {error && (
    <div className="mb-4 p-3 bg-red-500/10 text-red-500 rounded-lg text-sm">
     {error}
    </div>
   )}
   {success && (
    <div className="mb-4 p-3 bg-green-500/10 text-green-500 rounded-lg text-sm">
     {success}
    </div>
   )}

   {/* Auto-Suggestion after upload */}
   {autoSuggestion && (
    <div className="mb-6 p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-start gap-3">
     <Sparkles className="w-5 h-5 text-purple-500 shrink-0 mt-0.5" />
     <div>
      <p className="text-sm font-semibold text-purple-600 mb-1">KI-Vorschlag</p>
      <p className="text-sm theme-text-secondary">{autoSuggestion}</p>
      <div className="flex gap-2 mt-3">
       <button
        className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 flex items-center gap-1"
        onClick={() => { setAutoSuggestion(null); setQuery("Erstelle 5 Lernkarten basierend auf dem hochgeladenen Dokument"); }}
       >
        <BookOpen className="w-3.5 h-3.5" />
        5 Lernkarten
       </button>
       <button
        className="px-3 py-1.5 bg-amber-600 text-white rounded-lg text-sm hover:bg-amber-700 flex items-center gap-1"
        onClick={() => { setAutoSuggestion(null); setQuery("Erstelle ein 2-Minuten-Quiz basierend auf dem hochgeladenen Dokument"); }}
       >
        <HelpCircle className="w-3.5 h-3.5" />
        2-Min Quiz
       </button>
       <button
        className="px-3 py-1.5 theme-card theme-text rounded-lg text-sm hover:opacity-80"
        onClick={() => setAutoSuggestion(null)}
       >
        Später
       </button>
      </div>
     </div>
    </div>
   )}

   {/* Query section */}
   <div className="theme-card rounded-lg shadow-sm p-6 mb-6">
    <h2 className="text-lg font-semibold theme-text mb-4 flex items-center gap-2">
     <Search className="w-5 h-5 text-blue-500" />
     Wissen abfragen
    </h2>
    <div className="flex gap-2">
     <input
      type="text"
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      onKeyDown={(e) => e.key === "Enter" && handleQuery()}
      placeholder="Stelle eine Frage an deine Wissensdatenbank..."
      className="flex-1 px-4 py-2 border rounded-lg theme-card theme-text text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
     />
     <button
      onClick={handleQuery}
      disabled={querying || !query.trim()}
      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm flex items-center gap-2"
     >
      {querying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
      Suchen
     </button>
    </div>

    {/* Query result */}
    {queryResult && queryResult.results.length > 0 && (
     <div className="mt-4 space-y-3">
      <p className="text-sm font-semibold text-blue-600">Ergebnisse ({queryResult.results.length}):</p>
      {queryResult.results.map((r, i) => (
       <div key={i} className="p-3 bg-blue-500/5 rounded-lg border border-blue-500/20">
        <p className="text-sm theme-text whitespace-pre-wrap">{r.chunk_text}</p>
        <div className="flex items-center gap-2 mt-2">
         <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
          Relevanz: {(r.score * 100).toFixed(0)}%
         </span>
         {r.source && (
          <span className="text-xs theme-text-secondary">Quelle: {r.source}</span>
         )}
        </div>
       </div>
      ))}
     </div>
    )}
    {queryResult && queryResult.results.length === 0 && (
     <p className="mt-4 text-sm theme-text-secondary">Keine Ergebnisse gefunden. Versuche eine andere Frage.</p>
    )}
   </div>

   {/* Upload section */}
   <div className="theme-card rounded-lg shadow-sm p-6 mb-6">
    <h2 className="text-lg font-semibold theme-text mb-4 flex items-center gap-2">
     <Upload className="w-5 h-5 text-green-500" />
     Dokument hochladen
    </h2>

    <div className="flex gap-4 mb-4">
     <div>
      <label className="block text-sm theme-text-secondary mb-1">Fach</label>
      <select
       value={selectedSubject}
       onChange={(e) => setSelectedSubject(e.target.value)}
       className="px-3 py-2 border rounded-lg theme-card theme-text text-sm"
      >
       {SUBJECTS.map((s) => (
        <option key={s.value} value={s.value}>{s.label}</option>
       ))}
      </select>
     </div>
    </div>

    {/* Drop zone */}
    <div
     className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
      dragOver
       ? "border-blue-500 bg-blue-500/10"
       : "border-[var(--border-color)]"
     }`}
     onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
     onDragLeave={() => setDragOver(false)}
     onDrop={(e) => {
      e.preventDefault();
      setDragOver(false);
      handleUpload(e.dataTransfer.files);
     }}
    >
     <input
      type="file"
      id="file-upload"
      className="hidden"
      accept=".txt,.md,.csv,.pdf"
      multiple
      onChange={(e) => handleUpload(e.target.files)}
     />
     <label
      htmlFor="file-upload"
      className="cursor-pointer"
     >
      <Upload className="w-10 h-10 mx-auto mb-2 theme-text-secondary" />
      <p className="theme-text-secondary">
       {uploading
        ? "Wird hochgeladen und indexiert..."
        : "Datei hierher ziehen oder klicken zum Auswählen"}
      </p>
      <p className="text-xs theme-text-secondary mt-1">
       PDF, TXT, MD, CSV
      </p>
     </label>
    </div>

    {/* Upload progress bar */}
    {uploading && (
     <div className="mt-4">
      <div className="flex justify-between text-sm theme-text-secondary mb-1">
       <span>Upload-Fortschritt</span>
       <span>{uploadProgress}%</span>
      </div>
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
       <div
        className="h-full bg-blue-600 rounded-full transition-all duration-300"
        style={{ width: `${uploadProgress}%` }}
       />
      </div>
     </div>
    )}
   </div>

   {/* Seed section */}
   <div className="theme-card rounded-lg shadow-sm p-6 mb-6">
    <h2 className="text-lg font-semibold theme-text mb-2 flex items-center gap-2">
     <Sparkles className="w-5 h-5 text-amber-500" />
     Beispiel-Lehrplan laden
    </h2>
    <p className="text-sm theme-text-secondary mb-4">
     Lade vorgefertigte deutsche Lehrplaninhalte für Mathe, Physik, Chemie, Deutsch, Englisch und Geschichte.
    </p>
    <button
     onClick={handleSeed}
     disabled={seeding}
     className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm flex items-center gap-2"
    >
     {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
     {seeding ? "Wird geladen..." : "Curriculum-Daten indexieren"}
    </button>
   </div>

   {/* Document list */}
   <div className="theme-card rounded-lg shadow-sm p-6">
    <h2 className="text-lg font-semibold theme-text mb-4 flex items-center gap-2">
     <FileText className="w-5 h-5 text-blue-500" />
     Indexierte Dokumente ({documents.length})
    </h2>
    {documents.length === 0 ? (
     <EmptyState
      title="Keine Dokumente"
      description="Noch keine Dokumente indexiert. Lade eine Datei hoch oder klicke Curriculum-Daten indexieren."
      icon={<Database className="w-8 h-8 text-indigo-400" />}
     />
    ) : (
     <div className="space-y-3">
      {documents.map((doc) => (
       <div
        key={doc.doc_id}
        className="flex items-center justify-between p-3 bg-[var(--bg-surface)]/50 rounded-lg"
       >
        <div className="min-w-0 flex-1 flex items-center gap-3">
         <FileText className="w-4 h-4 text-blue-500 shrink-0" />
         <div>
          <p className="font-medium theme-text text-sm truncate">
           {doc.metadata.source || doc.metadata.filename || doc.doc_id}
          </p>
          <div className="flex gap-2 mt-1">
           {doc.metadata.subject && (
            <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
             {doc.metadata.subject}
            </span>
           )}
           {doc.metadata.topic && (
            <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">
             {doc.metadata.topic}
            </span>
           )}
           <span className="text-xs theme-text-secondary">
            {new Date(doc.created_at).toLocaleDateString("de-DE")}
           </span>
          </div>
         </div>
        </div>
        <button
         onClick={() => handleDelete(doc.doc_id)}
         className="ml-2 p-1.5 text-red-500 hover:bg-red-500/10 rounded"
         title="Löschen"
        >
         <Trash2 className="w-4 h-4" />
        </button>
       </div>
      ))}
     </div>
    )}
   </div>
  </div>
 );
}
