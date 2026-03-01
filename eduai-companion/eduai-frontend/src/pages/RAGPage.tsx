import { useState, useEffect, useCallback } from "react";
import { ragApi, type RAGDocument, type RAGStats } from "../services/api";

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
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("general");
  const [dragOver, setDragOver] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [docs, s] = await Promise.all([
        ragApi.listDocuments(),
        ragApi.stats(),
      ]);
      setDocuments(docs);
      setStats(s);
    } catch {
      // Stats may fail if no docs indexed yet
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError("");
    setSuccess("");
    let uploaded = 0;
    for (const file of Array.from(files)) {
      try {
        const result = await ragApi.uploadFile(file, selectedSubject, "de", file.name);
        uploaded++;
        setSuccess(`${file.name}: ${result.chunks_created} Chunks indexiert`);
      } catch (err) {
        setError(`${file.name}: ${err instanceof Error ? err.message : "Upload fehlgeschlagen"}`);
      }
    }
    setUploading(false);
    if (uploaded > 0) loadData();
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
      setSuccess(`Dokument ${docId} geloescht`);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Loeschen fehlgeschlagen");
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        Wissensdatenbank (RAG)
      </h1>
      <p className="text-gray-500 dark:text-gray-400 mb-6">
        Lade Lehrplaene, Arbeitsblatter oder Texte hoch, damit der KI-Tutor darauf zugreifen kann.
      </p>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
            <p className="text-sm text-gray-500 dark:text-gray-400">Dokumente</p>
            <p className="text-2xl font-bold text-blue-600">{stats.total_documents}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
            <p className="text-sm text-gray-500 dark:text-gray-400">Chunks</p>
            <p className="text-2xl font-bold text-green-600">{stats.total_chunks}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
            <p className="text-sm text-gray-500 dark:text-gray-400">Embedding-Dim</p>
            <p className="text-2xl font-bold text-purple-600">{stats.embedding_dim}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
            <p className="text-sm text-gray-500 dark:text-gray-400">Modell</p>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate" title={stats.embedding_model}>
              {stats.embedding_model.split("/").pop()}
            </p>
          </div>
        </div>
      )}

      {/* Alerts */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg text-sm">
          {success}
        </div>
      )}

      {/* Upload section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Dokument hochladen
        </h2>

        <div className="flex gap-4 mb-4">
          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Fach</label>
            <select
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 dark:border-gray-600 text-gray-900 dark:text-white text-sm"
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
              ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
              : "border-gray-300 dark:border-gray-600"
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
            <div className="text-4xl mb-2">
              {uploading ? "..." : "📄"}
            </div>
            <p className="text-gray-600 dark:text-gray-400">
              {uploading
                ? "Wird hochgeladen und indexiert..."
                : "Datei hierher ziehen oder klicken zum Auswaehlen"}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              PDF, TXT, MD, CSV
            </p>
          </label>
        </div>
      </div>

      {/* Seed section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Beispiel-Lehrplan laden
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Lade vorgefertigte deutsche Lehrplaninhalte fuer Mathe, Physik, Chemie, Deutsch, Englisch und Geschichte.
        </p>
        <button
          onClick={handleSeed}
          disabled={seeding}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {seeding ? "Wird geladen..." : "Curriculum-Daten indexieren"}
        </button>
      </div>

      {/* Document list */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Indexierte Dokumente ({documents.length})
        </h2>
        {documents.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            Noch keine Dokumente indexiert. Lade eine Datei hoch oder klicke &quot;Curriculum-Daten indexieren&quot;.
          </p>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.doc_id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-gray-900 dark:text-white text-sm truncate">
                    {doc.metadata.source || doc.metadata.filename || doc.doc_id}
                  </p>
                  <div className="flex gap-2 mt-1">
                    {doc.metadata.subject && (
                      <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded">
                        {doc.metadata.subject}
                      </span>
                    )}
                    {doc.metadata.topic && (
                      <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 rounded">
                        {doc.metadata.topic}
                      </span>
                    )}
                    <span className="text-xs text-gray-400">
                      {new Date(doc.created_at).toLocaleDateString("de-DE")}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.doc_id)}
                  className="ml-2 p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded"
                  title="Loeschen"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
