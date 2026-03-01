import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  FileText, Plus, Trash2, Save, Sparkles, Loader2, ArrowLeft
} from "lucide-react";
import { getAccessToken } from "../services/api";

const API = import.meta.env.VITE_API_URL || "";

interface Note {
  id: number;
  title: string;
  content?: string;
  subject: string;
  word_count: number;
  updated_at: string;
}

async function apiFetch(path: string, opts: RequestInit = {}) {
  const token = getAccessToken();
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...opts.headers },
  });
  return res.json();
}

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [aiResult, setAiResult] = useState("");
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    loadNotes();
  }, []);

  const loadNotes = async () => {
    try {
      const data = await apiFetch("/api/notes/");
      setNotes(data.notes || []);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  const openNote = async (id: number) => {
    const data = await apiFetch(`/api/notes/${id}`);
    setSelectedNote(data);
    setEditTitle(data.title);
    setEditContent(data.content || "");
    setAiResult("");
  };

  const createNote = async () => {
    const data = await apiFetch("/api/notes/", {
      method: "POST",
      body: JSON.stringify({ title: "Neue Notiz", content: "", subject: "general" }),
    });
    if (data.id) {
      await loadNotes();
      openNote(data.id);
    }
  };

  const saveNote = async () => {
    if (!selectedNote) return;
    setSaving(true);
    await apiFetch(`/api/notes/${selectedNote.id}`, {
      method: "PUT",
      body: JSON.stringify({ title: editTitle, content: editContent }),
    });
    setSaving(false);
    loadNotes();
  };

  const deleteNote = async (id: number) => {
    await apiFetch(`/api/notes/${id}`, { method: "DELETE" });
    if (selectedNote?.id === id) {
      setSelectedNote(null);
    }
    loadNotes();
  };

  const aiEnhance = async (action: string) => {
    if (!selectedNote) return;
    setAiLoading(true);
    try {
      const data = await apiFetch("/api/notes/ai-enhance", {
        method: "POST",
        body: JSON.stringify({ note_id: selectedNote.id, action }),
      });
      setAiResult(data.result || "Keine Ergebnisse");
    } catch {
      setAiResult("Fehler bei KI-Verarbeitung");
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  // Note editor
  if (selectedNote) {
    return (
      <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-4">
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => setSelectedNote(null)}>
            <ArrowLeft className="w-4 h-4 mr-1" /> Zurück
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => aiEnhance("improve")} disabled={aiLoading} className="gap-1">
              <Sparkles className="w-4 h-4" /> Verbessern
            </Button>
            <Button variant="outline" size="sm" onClick={() => aiEnhance("summarize")} disabled={aiLoading}>
              Zusammenfassen
            </Button>
            <Button variant="outline" size="sm" onClick={() => aiEnhance("quiz")} disabled={aiLoading}>
              Quiz erstellen
            </Button>
            <Button onClick={saveNote} disabled={saving} className="gap-1" size="sm">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Speichern
            </Button>
          </div>
        </div>

        <Input
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          className="text-xl font-bold border-0 border-b rounded-none px-0 focus-visible:ring-0"
          placeholder="Titel..."
        />

        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="w-full min-h-[400px] p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white resize-y focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
          placeholder="Schreibe deine Notizen hier... (Markdown wird unterstützt)"
        />

        {aiLoading && (
          <div className="flex items-center gap-2 text-indigo-600">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">KI verarbeitet...</span>
          </div>
        )}

        {aiResult && (
          <Card className="border-indigo-200 dark:border-indigo-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-indigo-700 dark:text-indigo-300">
                <Sparkles className="w-4 h-4" /> KI-Ergebnis
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">{aiResult}</pre>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <FileText className="w-7 h-7 text-indigo-600" />
            Notizen
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Schreibe und verbessere deine Notizen mit KI</p>
        </div>
        <Button onClick={createNote} className="gap-1">
          <Plus className="w-4 h-4" /> Neue Notiz
        </Button>
      </div>

      {notes.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">Noch keine Notizen vorhanden.</p>
            <p className="text-sm text-gray-400 mt-1">Erstelle deine erste Notiz!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {notes.map((note) => (
            <Card
              key={note.id}
              className="hover:shadow-lg transition-shadow cursor-pointer group"
              onClick={() => openNote(note.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <h3 className="font-medium text-gray-900 dark:text-white truncate">{note.title}</h3>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteNote(note.id); }}
                    className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {note.word_count} Wörter &middot; {new Date(note.updated_at).toLocaleDateString("de-DE")}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
