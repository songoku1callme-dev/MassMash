import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { learningApi, type LearningPath, type LearningProfile } from "../services/api";
import {
 BookOpen, CheckCircle2, Circle, Star, ArrowRight, Loader2,
 Calculator, Languages, BookOpenCheck, Clock, FlaskConical, Target
} from "lucide-react";
import ErklaerButton from "../components/ui/ErklaerButton";

const SUBJECTS = [
 { id: "math", name: "Mathe", icon: <Calculator className="w-5 h-5" />, color: "from-blue-500 to-blue-600" },
 { id: "english", name: "Englisch", icon: <Languages className="w-5 h-5" />, color: "from-emerald-500 to-emerald-600" },
 { id: "german", name: "Deutsch", icon: <BookOpenCheck className="w-5 h-5" />, color: "from-amber-500 to-amber-600" },
 { id: "history", name: "Geschichte", icon: <Clock className="w-5 h-5" />, color: "from-purple-500 to-purple-600" },
 { id: "science", name: "Naturwiss.", icon: <FlaskConical className="w-5 h-5" />, color: "from-rose-500 to-rose-600" },
];

interface LearningPathPageProps {
 onNavigate: (page: string) => void;
}

export default function LearningPathPage({ onNavigate }: LearningPathPageProps) {
 const [selectedSubject, setSelectedSubject] = useState("math");
 const [learningPath, setLearningPath] = useState<LearningPath | null>(null);
 const [profiles, setProfiles] = useState<LearningProfile[]>([]);
 const [loading, setLoading] = useState(false);

 useEffect(() => {
 loadProfiles();
 }, []);

 useEffect(() => {
 loadPath(selectedSubject);
 }, [selectedSubject]);

 const loadProfiles = async () => {
 try {
 const data = await learningApi.profile();
 setProfiles(data);
 } catch (err) {
 console.error("Failed to load profiles:", err);
 }
 };

 const loadPath = async (subject: string) => {
 setLoading(true);
 try {
 const data = await learningApi.learningPath(subject);
 setLearningPath(data);
 } catch (err) {
 console.error("Failed to load learning path:", err);
 } finally {
 setLoading(false);
 }
 };

 const currentProfile = profiles.find(p => p.subject === selectedSubject);
 const subjectInfo = SUBJECTS.find(s => s.id === selectedSubject);

 return (
 <div className="p-4 lg:p-6 max-w-5xl mx-auto space-y-6">
 {/* Header */}
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <BookOpen className="w-7 h-7 text-blue-600" />
 Lernpfad
 </h1>
 <p className="theme-text-secondary mt-1">
 Dein personalisierter Weg zum Lernerfolg
 </p>
 </div>

 {/* Subject Tabs */}
 <div className="flex gap-2 overflow-x-auto pb-2">
 {SUBJECTS.map((s) => (
 <button
 key={s.id}
 onClick={() => setSelectedSubject(s.id)}
 className={`flex items-center gap-2 px-4 py-2.5 rounded-xl whitespace-nowrap transition-all ${
 selectedSubject === s.id
 ? "bg-blue-600 text-white shadow-md"
 : "bg-[var(--bg-surface)] theme-text-secondary hover:opacity-80"
 }`}
 >
 {s.icon}
 <span className="text-sm font-medium">{s.name}</span>
 </button>
 ))}
 </div>

 {/* Current Level Card */}
 {currentProfile && subjectInfo && (
 <Card className={`bg-gradient-to-r ${subjectInfo.color} text-white border-0`}>
 <CardContent className="p-6">
 <div className="flex items-center justify-between">
 <div>
 <p className="text-white/80 text-sm">Aktuelles Level</p>
 <p className="text-2xl font-bold capitalize mt-1">{currentProfile.proficiency_level}</p>
 <p className="text-white/80 text-sm mt-1">
 Meisterung: {currentProfile.mastery_score}% | Genauigkeit: {currentProfile.accuracy}%
 </p>
 </div>
 <div className="w-16 h-16 rounded-2xl bg-white/20 flex items-center justify-center">
 {subjectInfo.icon}
 </div>
 </div>
 {learningPath && (
 <div className="mt-4 pt-4 border-t border-white/20">
 <div className="flex items-center gap-2">
 <Target className="w-4 h-4" />
 <span className="text-sm">Nächstes Ziel: {learningPath.next_milestone}</span>
 </div>
 </div>
 )}
 </CardContent>
 </Card>
 )}

 {/* Learning Path Topics */}
 {loading ? (
 <div className="flex items-center justify-center py-12">
 <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
 </div>
 ) : learningPath ? (
 <div className="space-y-4">
 <h2 className="text-lg font-semibold theme-text">Empfohlene Themen</h2>

 <div className="relative">
 {/* Timeline line */}
 <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-[var(--progress-bg)]" />

 <div className="space-y-4">
 {learningPath.recommended_topics.map((topic, idx) => (
 <div key={idx} className="relative flex items-start gap-4">
 {/* Timeline dot */}
 <div className={`relative z-10 w-12 h-12 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
 topic.mastered
 ? "bg-emerald-100"
 : topic.recommended
 ? "bg-blue-100"
 : "bg-[var(--bg-surface)]"
 }`}>
 {topic.mastered ? (
 <CheckCircle2 className="w-6 h-6 text-emerald-600" />
 ) : topic.recommended ? (
 <Star className="w-6 h-6 text-blue-600" />
 ) : (
 <Circle className="w-6 h-6 theme-text-secondary" />
 )}
 </div>

 {/* Topic card */}
 <Card className={`flex-1 ${topic.recommended ? "ring-2 ring-blue-500/30 shadow-md" : ""}`}>
 <CardContent className="p-4">
 <div className="flex items-start justify-between gap-2">
 <div className="flex-1">
 <div className="flex items-center gap-2">
 <h3 className="font-medium theme-text">{topic.topic}</h3>
 {topic.recommended && (
 <Badge variant="default" className="text-xs">Empfohlen</Badge>
 )}
 {topic.mastered && (
 <Badge variant="success" className="text-xs">Gemeistert</Badge>
 )}
 </div>
 <p className="text-sm theme-text-secondary mt-1">{topic.description}</p>
 <div className="flex items-center gap-3 mt-2">
 <Badge variant="secondary" className="text-xs capitalize">{topic.difficulty}</Badge>
 </div>
 </div>
 <div className="flex items-center gap-2 shrink-0">
 <ErklaerButton
 thema={topic.topic}
 fach={SUBJECTS.find(s => s.id === selectedSubject)?.name || "Allgemein"}
 variant="minimal"
 />
 {topic.recommended && !topic.mastered && (
 <Button
 size="sm"
 className="shrink-0 gap-1"
 onClick={() => onNavigate("chat")}
 >
 Lernen <ArrowRight className="w-3 h-3" />
 </Button>
 )}
 </div>
 </div>
 </CardContent>
 </Card>
 </div>
 ))}
 </div>
 </div>
 </div>
 ) : null}

 {/* Summary Card */}
 {profiles.length > 0 && (
 <Card>
 <CardHeader>
 <CardTitle className="text-base">Gesamtübersicht</CardTitle>
 </CardHeader>
 <CardContent>
 <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
 {profiles.map((p) => {
 const s = SUBJECTS.find(sub => sub.id === p.subject);
 return (
 <div
 key={p.subject}
 className="text-center cursor-pointer"
 onClick={() => setSelectedSubject(p.subject)}
 >
 <div className={`w-10 h-10 mx-auto rounded-lg bg-gradient-to-br ${s?.color || "from-gray-500 to-gray-600"} flex items-center justify-center text-white shadow-sm mb-2`}>
 {s?.icon}
 </div>
 <p className="text-xs font-medium theme-text">{s?.name}</p>
 <p className="text-xs theme-text-secondary capitalize">{p.proficiency_level}</p>
 <div className="mt-1 w-full bg-[var(--bg-surface)] rounded-full h-1">
 <div
 className={`h-1 rounded-full bg-gradient-to-r ${s?.color || "from-gray-500 to-gray-600"}`}
 style={{ width: `${Math.max(p.mastery_score, 5)}%` }}
 />
 </div>
 </div>
 );
 })}
 </div>
 </CardContent>
 </Card>
 )}
 </div>
 );
}
