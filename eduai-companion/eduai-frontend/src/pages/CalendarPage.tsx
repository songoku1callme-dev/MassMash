import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
 CalendarDays, Plus, Trash2, Sparkles, Loader2, BookOpen, Clock
} from "lucide-react";
import { getAccessToken } from "../services/api";
import { LoadingSkeleton, ErrorState } from "../components/PageStates";

const API = import.meta.env.VITE_API_URL || "";

interface Exam {
 id: number;
 title: string;
 subject: string;
 exam_date: string;
 topics: string;
 study_plan: string;
}

interface StudyDay {
 tag: number;
 datum: string;
 aufgabe: string;
 dauer_minuten: number;
}

async function apiFetch(path: string, opts: RequestInit = {}) {
 const token = getAccessToken();
 const res = await fetch(`${API}${path}`, {
 ...opts,
 headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...opts.headers },
 });
 return res.json();
}

export default function CalendarPage() {
 const [exams, setExams] = useState<Exam[]>([]);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState(false);
 const [showAdd, setShowAdd] = useState(false);
 const [title, setTitle] = useState("");
 const [subject, setSubject] = useState("");
 const [examDate, setExamDate] = useState("");
 const [topics, setTopics] = useState("");
 const [planLoading, setPlanLoading] = useState<number | null>(null);
 const [activePlan, setActivePlan] = useState<{ examId: number; days: StudyDay[] } | null>(null);

 useEffect(() => {
 loadExams();
 }, []);

 const loadExams = async () => {
 setError(false);
 try {
 const data = await apiFetch("/api/calendar/exams");
 setExams(data.exams || []);
 } catch {
 setError(true);
 } finally {
 setLoading(false);
 }
 };

 const addExam = async () => {
 if (!title || !subject || !examDate) return;
 await apiFetch("/api/calendar/exams", {
 method: "POST",
 body: JSON.stringify({ title, subject, exam_date: examDate, topics }),
 });
 setTitle("");
 setSubject("");
 setExamDate("");
 setTopics("");
 setShowAdd(false);
 loadExams();
 };

 const deleteExam = async (id: number) => {
 await apiFetch(`/api/calendar/exams/${id}`, { method: "DELETE" });
 if (activePlan?.examId === id) setActivePlan(null);
 loadExams();
 };

 const generatePlan = async (examId: number) => {
 setPlanLoading(examId);
 try {
 const data = await apiFetch(`/api/calendar/exams/${examId}/study-plan`, { method: "POST" });
 setActivePlan({ examId, days: data.study_plan || [] });
 } catch {
 /* ignore */
 } finally {
 setPlanLoading(null);
 }
 };

 const daysUntil = (dateStr: string) => {
 const diff = new Date(dateStr).getTime() - Date.now();
 return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
 };

 if (loading) return <LoadingSkeleton lines={6} />;
 if (error) return <ErrorState message="Fehler beim Laden des Kalenders." onRetry={loadExams} />;

  return (
  <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <CalendarDays className="w-7 h-7 text-indigo-600" />
 Prüfungs-Kalender
 </h1>
 <p className="theme-text-secondary mt-1">Plane deine Klausuren und lass dir einen KI-Lernplan erstellen</p>
 </div>
 <Button onClick={() => setShowAdd(true)} className="gap-1 w-full sm:w-auto">
 <Plus className="w-4 h-4" /> Klausur eintragen
 </Button>
 </div>

 {showAdd && (
 <Card className="border-indigo-200">
  <CardContent className="p-4 space-y-3">
  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
 <Input placeholder="Klausur-Titel" value={title} onChange={(e) => setTitle(e.target.value)} />
 <Input placeholder="Fach" value={subject} onChange={(e) => setSubject(e.target.value)} />
  </div>
  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
 <Input type="date" value={examDate} onChange={(e) => setExamDate(e.target.value)} />
 <Input placeholder="Themen (optional)" value={topics} onChange={(e) => setTopics(e.target.value)} />
  </div>
  <div className="flex flex-col sm:flex-row gap-2">
  <Button onClick={addExam} className="w-full sm:w-auto">Speichern</Button>
  <Button variant="ghost" onClick={() => setShowAdd(false)} className="w-full sm:w-auto">Abbrechen</Button>
  </div>
 </CardContent>
 </Card>
 )}

 {exams.length === 0 ? (
 <Card>
 <CardContent className="p-12 text-center">
 <CalendarDays className="w-12 h-12 theme-text-secondary mx-auto mb-3" />
 <p className="theme-text-secondary">Keine Klausuren eingetragen.</p>
 <p className="text-sm theme-text-secondary mt-1">Trage deine nächste Klausur ein und lass dir einen Lernplan erstellen!</p>
 </CardContent>
 </Card>
 ) : (
 <div className="space-y-4">
 {exams.map((exam) => {
 const days = daysUntil(exam.exam_date);
 const urgent = days <= 3;
 return (
 <Card key={exam.id} className={urgent ? "border-red-200" : ""}>
  <CardContent className="p-4">
  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
 <div>
 <h3 className="font-medium theme-text">{exam.title}</h3>
 <div className="flex items-center gap-3 mt-1 text-sm theme-text-secondary">
 <span className="flex items-center gap-1">
 <BookOpen className="w-4 h-4" /> {exam.subject}
 </span>
 <span className="flex items-center gap-1">
 <Clock className="w-4 h-4" />
 {new Date(exam.exam_date).toLocaleDateString("de-DE")}
 </span>
 <span className={`font-medium ${urgent ? "text-red-500" : "text-indigo-600"}`}>
 {days === 0 ? "Heute!" : `noch ${days} Tage`}
 </span>
 </div>
 {exam.topics && (
 <p className="text-xs theme-text-secondary mt-1">Themen: {exam.topics}</p>
 )}
  </div>
  <div className="flex flex-col sm:flex-row gap-2">
  <Button
  variant="outline"
  size="sm"
 onClick={() => generatePlan(exam.id)}
 disabled={planLoading === exam.id}
 className="gap-1"
 >
 {planLoading === exam.id ? (
 <Loader2 className="w-4 h-4 animate-spin" />
 ) : (
 <Sparkles className="w-4 h-4" />
 )}
 Lernplan
 </Button>
 <Button
 variant="ghost"
 size="sm"
 onClick={() => deleteExam(exam.id)}
 className="theme-text-secondary hover:text-red-500"
 >
 <Trash2 className="w-4 h-4" />
 </Button>
 </div>
 </div>

 {activePlan?.examId === exam.id && activePlan.days.length > 0 && (
 <div className="mt-4 border-t pt-4">
 <h4 className="text-sm font-medium theme-text-secondary mb-3">
 KI-Lernplan ({activePlan.days.length} Tage)
 </h4>
 <div className="space-y-2">
 {activePlan.days.map((day, i) => (
 <div key={i} className="flex items-center gap-3 text-sm">
 <span className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 font-medium text-xs shrink-0">
 {day.tag}
 </span>
 <span className="theme-text-secondary w-20 shrink-0">
 {day.datum ? new Date(day.datum).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "short" }) : `Tag ${day.tag}`}
 </span>
 <span className="theme-text flex-1">{day.aufgabe}</span>
 <span className="theme-text-secondary text-xs shrink-0">{day.dauer_minuten} Min.</span>
 </div>
 ))}
 </div>
 </div>
 )}
 </CardContent>
 </Card>
 );
 })}
 </div>
 )}
 </div>
 );
}
