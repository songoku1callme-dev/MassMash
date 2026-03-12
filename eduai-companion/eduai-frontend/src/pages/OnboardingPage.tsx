import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { GraduationCap, Target, Sparkles, ChevronRight, Check } from "lucide-react";

interface OnboardingProps {
 onComplete: () => void;
}

const SCHOOL_TYPES = ["Gymnasium", "Realschule", "Gesamtschule", "Hauptschule", "Berufsschule", "Fachoberschule"];
const GRADES = ["5", "6", "7", "8", "9", "10", "11", "12", "13"];
const BUNDESLAENDER = [
 "Baden-Wuerttemberg", "Bayern", "Berlin", "Brandenburg", "Bremen",
 "Hamburg", "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen",
 "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen",
 "Sachsen-Anhalt", "Schleswig-Holstein", "Thueringen",
];

const SUBJECTS = [
 "Mathematik", "Deutsch", "Englisch", "Physik", "Chemie", "Biologie",
 "Geschichte", "Geographie", "Informatik", "Kunst", "Musik", "Sport",
 "Französisch", "Spanisch", "Latein", "Philosophie",
];

const GOALS = [
 { id: "abitur", label: "Abitur bestehen", icon: <GraduationCap className="w-6 h-6" /> },
 { id: "grades", label: "Noten verbessern", icon: <Target className="w-6 h-6" /> },
 { id: "curious", label: "Aus Neugier lernen", icon: <Sparkles className="w-6 h-6" /> },
];

export default function OnboardingPage({ onComplete }: OnboardingProps) {
 const [step, setStep] = useState(0);
 const [grade, setGrade] = useState("10");
 const [schoolType, setSchoolType] = useState("Gymnasium");
 const [bundesland, setBundesland] = useState("");
 const [selectedSubjects, setSelectedSubjects] = useState<string[]>([]);
 const [goal, setGoal] = useState("");

 const toggleSubject = (s: string) => {
 setSelectedSubjects((prev) =>
 prev.includes(s) ? prev.filter((x) => x !== s) : prev.length < 3 ? [...prev, s] : prev
 );
 };

 const steps = [
 {
 title: "Welche Klasse besuchst du?",
 subtitle: "Damit wir die Inhalte an dein Niveau anpassen",
 content: (
 <div className="space-y-6">
 <div>
 <label className="text-sm font-medium theme-text-secondary mb-2 block">Klassenstufe</label>
 <div className="flex flex-wrap gap-2">
 {GRADES.map((g) => (
 <button
 key={g}
 onClick={() => setGrade(g)}
 className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all min-h-[44px] ${
 grade === g
 ? "bg-indigo-600 text-white shadow-md"
 : "bg-[var(--bg-surface)] theme-text-secondary hover:bg-[var(--bg-card-hover)]"
 }`}
 >
 {g}. Klasse
 </button>
 ))}
 </div>
 </div>
 <div>
 <label className="text-sm font-medium theme-text-secondary mb-2 block">Schulart</label>
 <div className="flex flex-wrap gap-2">
 {SCHOOL_TYPES.map((t) => (
 <button
 key={t}
 onClick={() => setSchoolType(t)}
 className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all min-h-[44px] ${
 schoolType === t
 ? "bg-indigo-600 text-white shadow-md"
 : "bg-[var(--bg-surface)] theme-text-secondary hover:bg-[var(--bg-card-hover)]"
 }`}
 >
 {t}
 </button>
 ))}
 </div>
 </div>
 </div>
 ),
 },
 {
 title: "In welchem Bundesland bist du?",
 subtitle: "Der Lehrplan unterscheidet sich je nach Bundesland",
 content: (
 <div className="space-y-4">
 <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
 {BUNDESLAENDER.map((bl) => (
 <button
 key={bl}
 onClick={() => setBundesland(bl)}
 className={`px-3 py-2.5 rounded-lg text-sm font-medium transition-all min-h-[44px] ${
 bundesland === bl
 ? "bg-indigo-600 text-white shadow-md"
 : "bg-[var(--bg-surface)] theme-text-secondary hover:bg-[var(--bg-card-hover)]"
 }`}
 >
 {bl}
 </button>
 ))}
 </div>
 </div>
 ),
 },
 {
 title: "Was sind deine Hauptfächer?",
 subtitle: "Wähle bis zu 3 Fächer aus",
 content: (
 <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
 {SUBJECTS.map((s) => (
 <button
 key={s}
 onClick={() => toggleSubject(s)}
 className={`px-3 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2 min-h-[44px] ${
 selectedSubjects.includes(s)
 ? "bg-indigo-600 text-white shadow-md"
 : "bg-[var(--bg-surface)] theme-text-secondary hover:bg-[var(--bg-card-hover)]"
 }`}
 >
 {selectedSubjects.includes(s) && <Check className="w-4 h-4" />}
 {s}
 </button>
 ))}
 </div>
 ),
 },
 {
 title: "Was ist dein Ziel?",
 subtitle: "Wir passen deinen Lernplan entsprechend an",
 content: (
 <div className="space-y-3">
 {GOALS.map((g) => (
 <button
 key={g.id}
 onClick={() => setGoal(g.id)}
 className={`w-full flex items-center gap-4 px-5 py-4 rounded-xl text-left transition-all ${
 goal === g.id
 ? "bg-indigo-600 text-white shadow-lg"
 : "bg-[var(--bg-surface)] theme-text-secondary hover:bg-[var(--bg-card-hover)]"
 }`}
 >
 {g.icon}
 <span className="font-medium text-lg">{g.label}</span>
 </button>
 ))}
 </div>
 ),
 },
 {
 title: "Dein Lernplan ist bereit!",
 subtitle: "Basierend auf deinem Profil haben wir alles vorbereitet",
 content: (
 <div className="text-center space-y-6">
 <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-xl">
 <Sparkles className="w-10 h-10 text-white" />
 </div>
 <div className="space-y-2">
 <p className="theme-text-secondary">
 <strong>{schoolType}</strong>, {grade}. Klasse
 </p>
 <p className="theme-text-secondary">
 Fächer: {selectedSubjects.join(", ") || "Alle"}
 </p>
 <p className="theme-text-secondary">
 Ziel: {GOALS.find((g) => g.id === goal)?.label || "Lernen"}
 </p>
 </div>
 <p className="text-sm theme-text-secondary">
 Du kannst diese Einstellungen jederzeit ändern.
 </p>
 </div>
 ),
 },
 ];

 const currentStep = steps[step];
 const isLast = step === steps.length - 1;

 return (
 <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center p-4">
 <div className="w-full max-w-lg">
 {/* Progress */}
 <div className="flex gap-2 mb-6 sm:mb-8">
 {steps.map((_, i) => (
 <div
 key={i}
 className={`h-2 sm:h-1.5 flex-1 rounded-full transition-all ${
 i <= step ? "bg-indigo-600" : "bg-[var(--progress-bg)]"
 }`}
 />
 ))}
 </div>

 <Card className="shadow-xl border-0">
 <CardContent className="p-5 sm:p-8">
 <div className="mb-6">
 <h2 className="text-2xl font-bold theme-text">{currentStep.title}</h2>
 <p className="theme-text-secondary mt-1">{currentStep.subtitle}</p>
 </div>

 {currentStep.content}

 <div className="flex justify-between mt-6 sm:mt-8">
 {step > 0 ? (
 <Button variant="outline" onClick={() => setStep(step - 1)}>
 Zurück
 </Button>
 ) : (
 <div />
 )}
 <Button
 onClick={() => (isLast ? onComplete() : setStep(step + 1))}
 className="gap-2 min-h-[48px] px-6"
 >
 {isLast ? "Los geht's!" : "Weiter"}
 <ChevronRight className="w-4 h-4" />
 </Button>
 </div>
 </CardContent>
 </Card>
 </div>
 </div>
 );
}
