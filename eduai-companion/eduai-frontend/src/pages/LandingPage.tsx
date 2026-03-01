import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  GraduationCap, Brain, Trophy, BookOpen, Sparkles,
  ChevronRight, Star, Zap, Shield, MessageCircle, BarChart3,
  Users, TrendingUp, Clock, Flame
} from "lucide-react";

/** Animated counter that counts up from 0 to target */
function AnimatedCounter({ target, suffix = "" }: { target: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const duration = 2000;
    const steps = 60;
    const increment = target / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        setCount(target);
        clearInterval(timer);
      } else {
        setCount(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [target]);
  return <>{count.toLocaleString("de-DE")}{suffix}</>;
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/** Supreme 13.0 Phase 9: Fetch real stats from backend, fallback to defaults */
function useLiveStats() {
  const [stats, setStats] = useState({
    users: 1247, quizzes: 48392, tournaments: 312, improvement: 89,
  });
  useEffect(() => {
    fetch(`${API_URL}/api/stats/public`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data) {
          setStats({
            users: data.total_users || stats.users,
            quizzes: data.total_quizzes || stats.quizzes,
            tournaments: data.total_tournaments || stats.tournaments,
            improvement: data.avg_improvement || stats.improvement,
          });
        }
      })
      .catch(() => { /* use defaults */ });
  }, []);
  return stats;
}

interface LandingPageProps {
  onLogin: () => void;
  onRegister: () => void;
  onIQTest: () => void;
}

const FEATURES = [
  { icon: <Brain className="w-8 h-8" />, title: "IQ-Test", desc: "40 wissenschaftlich validierte Fragen mit Schwierigkeitsgewichtung", color: "from-blue-500 to-indigo-600" },
  { icon: <MessageCircle className="w-8 h-8" />, title: "KI-Tutor", desc: "20 KI-Persönlichkeiten erklären dir jedes Thema", color: "from-emerald-500 to-teal-600" },
  { icon: <GraduationCap className="w-8 h-8" />, title: "Abitur-Simulation", desc: "Echte Prüfungsaufgaben für alle 16 Fächer", color: "from-purple-500 to-violet-600" },
  { icon: <Trophy className="w-8 h-8" />, title: "Tägliche Turniere", desc: "Tritt gegen andere Schüler an und gewinne Preise", color: "from-amber-500 to-orange-600" },
  { icon: <BookOpen className="w-8 h-8" />, title: "Karteikarten", desc: "Spaced Repetition (SM-2) für effizientes Lernen", color: "from-rose-500 to-pink-600" },
  { icon: <BarChart3 className="w-8 h-8" />, title: "Prüfungs-Kalender", desc: "KI erstellt deinen persönlichen Lernplan rückwärts", color: "from-cyan-500 to-blue-600" },
];

const PRICING = [
  {
    tier: "Free", price: "0", period: "", features: [
      "5 KI-Persoenlichkeiten", "3 Quizzes/Tag", "IQ-Test (1x/Woche)",
      "Basis-Faecher", "Gruppen-Chats",
    ],
  },
  {
    tier: "Pro", price: "4,99", period: "/Monat", features: [
      "12 KI-Persoenlichkeiten", "Unbegrenzte Quizzes", "Abitur-Simulation",
      "Karteikarten + Notizen", "Pruefungs-Kalender", "Internet-Recherche",
    ], popular: true, yearPrice: "39,99",
  },
  {
    tier: "Max", price: "9,99", period: "/Monat", features: [
      "Alle 20 KI-Persoenlichkeiten", "Alles in Pro", "Prioritaets-Support",
      "Erweiterte Statistiken", "PDF/Word Export", "Multiplayer-Quiz",
    ], yearPrice: "79,99",
  },
  {
    tier: "Eltern", price: "2,99", period: "/Monat", features: [
      "Lernfortschritt in Echtzeit", "Woechentliche E-Mail Berichte",
      "Streak-Alerts", "Schwaechen-Analyse", "Pruefungs-Kalender Einblick",
    ], yearPrice: "23,99",
  },
];

const TESTIMONIALS = [
  { name: "Sarah M.", grade: "12. Klasse", text: "Dank EduAI habe ich meine Mathe-Note von 4 auf 2 verbessert!", avatar: "S" },
  { name: "Tim K.", grade: "10. Klasse", text: "Der IQ-Test und die Turniere machen richtig Spaß. Lernen war noch nie so cool!", avatar: "T" },
  { name: "Lisa W.", grade: "13. Klasse", text: "Die Abitur-Simulation hat mir mega geholfen. Ich fühle mich jetzt viel sicherer.", avatar: "L" },
];

export default function LandingPage({ onLogin, onRegister, onIQTest }: LandingPageProps) {
  const liveStats = useLiveStats();

  const LIVE_STATS = [
    { icon: <Users className="w-6 h-6" />, value: liveStats.users, suffix: "+", label: "Aktive Schueler" },
    { icon: <Brain className="w-6 h-6" />, value: liveStats.quizzes, suffix: "+", label: "Quizzes geloest" },
    { icon: <Trophy className="w-6 h-6" />, value: liveStats.tournaments, suffix: "", label: "Turniere gespielt" },
    { icon: <Flame className="w-6 h-6" />, value: liveStats.improvement, suffix: "%", label: "Notenverbesserung" },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg border-b border-gray-100 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white">
              <GraduationCap className="w-5 h-5" />
            </div>
            <span className="font-bold text-lg text-gray-900 dark:text-white">EduAI</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={onLogin}>Anmelden</Button>
            <Button size="sm" onClick={onRegister}>Kostenlos starten</Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-sm font-medium mb-6 animate-pulse">
            <Sparkles className="w-4 h-4" />
            Deutschlands #1 KI-Tutor — Bereits 1.247+ Schueler lernen mit EduAI
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-gray-900 dark:text-white leading-tight">
            Lerne{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500">
              3x schneller
            </span>
            {" "}mit KI
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            IQ-Test, Abitur-Simulation, 16 Faecher, taegliche Turniere, Voice Mode.
            20 KI-Persoenlichkeiten helfen dir beim Lernen. <strong>100% kostenlos starten.</strong>
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="lg" className="gap-2 text-base px-8 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 shadow-lg shadow-indigo-500/25" onClick={onRegister}>
              Mit Google starten
              <ChevronRight className="w-5 h-5" />
            </Button>
            <Button variant="outline" size="lg" className="gap-2 text-base" onClick={onIQTest}>
              <Brain className="w-5 h-5" />
              Gratis IQ-Test
            </Button>
          </div>
          <p className="mt-3 text-xs text-gray-400">Keine Kreditkarte noetig. DSGVO-konform.</p>
        </div>
      </section>

      {/* Live Stats Counter */}
      <section className="py-12 px-4 border-b border-gray-100 dark:border-gray-800">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {LIVE_STATS.map((s, i) => (
              <div key={i} className="text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 mb-2">
                  {s.icon}
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-gray-900 dark:text-white">
                  <AnimatedCounter target={s.value} suffix={s.suffix} />
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof Banner */}
      <section className="py-6 bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4">
        <div className="max-w-5xl mx-auto flex flex-wrap items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            <span>Gestern: <strong>247 Schueler</strong> im Mathe-Turnier</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            <span>Durchschnittlich <strong>42 Min/Tag</strong> Lernzeit</span>
          </div>
          <div className="flex items-center gap-2">
            <Star className="w-4 h-4" />
            <span><strong>4.8/5</strong> Sterne von Schuelern</span>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-gray-50 dark:bg-gray-800/50 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Alles was du zum Lernen brauchst</h2>
            <p className="mt-3 text-gray-600 dark:text-gray-400">In einer App. Für alle Fächer. Mit KI.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f, i) => (
              <Card key={i} className="hover:shadow-lg transition-shadow border-0 bg-white dark:bg-gray-900">
                <CardContent className="p-6">
                  <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${f.color} flex items-center justify-center text-white mb-4 shadow-md`}>
                    {f.icon}
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{f.title}</h3>
                  <p className="mt-2 text-gray-600 dark:text-gray-400 text-sm">{f.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Was Schüler sagen</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {TESTIMONIALS.map((t, i) => (
              <Card key={i} className="border-0 bg-gray-50 dark:bg-gray-800">
                <CardContent className="p-6">
                  <div className="flex items-center gap-1 mb-3">
                    {[...Array(5)].map((_, j) => (
                      <Star key={j} className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                    ))}
                  </div>
                  <p className="text-gray-700 dark:text-gray-300 text-sm italic mb-4">"{t.text}"</p>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-bold text-sm">
                      {t.avatar}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white text-sm">{t.name}</p>
                      <p className="text-xs text-gray-500">{t.grade}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 bg-gray-50 dark:bg-gray-800/50 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Einfache Preise</h2>
            <p className="mt-3 text-gray-600 dark:text-gray-400">Starte kostenlos. Upgrade wenn du willst.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {PRICING.map((p, i) => (
              <Card
                key={i}
                className={`relative border-0 ${p.popular ? "ring-2 ring-indigo-600 shadow-xl" : "shadow-md"}`}
              >
                {p.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-indigo-600 text-white text-xs font-medium rounded-full">
                    Beliebteste Wahl
                  </div>
                )}
                <CardContent className="p-6">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white">{p.tier}</h3>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-4xl font-extrabold text-gray-900 dark:text-white">{p.price}&euro;</span>
                    <span className="text-gray-500 dark:text-gray-400">{p.period}</span>
                  </div>
                  {p.yearPrice && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      oder {p.yearPrice}&euro;/Jahr (spare 33%)
                    </p>
                  )}
                  <ul className="mt-6 space-y-3">
                    {p.features.map((f, j) => (
                      <li key={j} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                        <Zap className="w-4 h-4 text-indigo-500 shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full mt-6"
                    variant={p.popular ? "default" : "outline"}
                    onClick={onRegister}
                  >
                    {p.tier === "Free" ? "Kostenlos starten" : `${p.tier} wählen`}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">EduAI vs. Andere Lern-Apps</h2>
            <p className="mt-3 text-gray-600 dark:text-gray-400">Warum EduAI die beste Wahl ist</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b dark:border-gray-700">
                  <th className="text-left p-3 text-gray-500 dark:text-gray-400">Feature</th>
                  <th className="p-3 text-indigo-600 dark:text-indigo-400 font-bold">EduAI</th>
                  <th className="p-3 text-gray-500 dark:text-gray-400">Knowunity</th>
                  <th className="p-3 text-gray-500 dark:text-gray-400">Studyflix</th>
                </tr>
              </thead>
              <tbody className="text-center">
                {[
                  ["KI-Tutor (20 Stile)", "check", "cross", "cross"],
                  ["IQ-Test", "check", "cross", "cross"],
                  ["Abitur-Simulation", "check", "cross", "partial"],
                  ["Taegliche Turniere", "check", "cross", "cross"],
                  ["Pomodoro-Timer", "check", "cross", "cross"],
                  ["Wissensluecken-Scanner", "check", "cross", "cross"],
                  ["Belohnungs-Shop", "check", "cross", "cross"],
                  ["Klassen-Challenges", "check", "partial", "cross"],
                  ["16 Faecher", "check", "check", "partial"],
                  ["Kostenloser Plan", "check", "partial", "check"],
                ].map(([feature, eduai, knowunity, studyflix], i) => (
                  <tr key={i} className="border-b dark:border-gray-700/50">
                    <td className="text-left p-3 text-gray-700 dark:text-gray-300">{feature}</td>
                    {[eduai, knowunity, studyflix].map((val, j) => (
                      <td key={j} className="p-3">
                        {val === "check" ? <span className="text-green-500 font-bold">Ja</span> :
                         val === "partial" ? <span className="text-yellow-500">Teilweise</span> :
                         <span className="text-red-400">Nein</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-20 bg-gray-50 dark:bg-gray-800/50 px-4">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Haeufige Fragen</h2>
          </div>
          <div className="space-y-4">
            {[
              { q: "Ist EduAI wirklich kostenlos?", a: "Ja! Der Free-Plan ist dauerhaft kostenlos und beinhaltet 5 KI-Persoenlichkeiten, 3 Quizzes pro Tag und den IQ-Test." },
              { q: "Fuer welche Klassenstufen ist EduAI geeignet?", a: "EduAI ist fuer Schueler der Klassen 5-13 an Gymnasium, Realschule und Gesamtschule geeignet. Die KI passt sich automatisch an dein Niveau an." },
              { q: "Wie funktioniert der KI-Tutor?", a: "Der KI-Tutor nutzt modernste Sprachmodelle, um dir Themen Schritt fuer Schritt zu erklaeren. Du kannst aus 20 verschiedenen KI-Persoenlichkeiten waehlen." },
              { q: "Sind meine Daten sicher?", a: "Absolut. EduAI ist DSGVO-konform. Deine Daten werden in Europa gespeichert und niemals an Dritte weitergegeben." },
              { q: "Kann ich EduAI auf dem Handy nutzen?", a: "Ja! EduAI ist eine Progressive Web App (PWA) und funktioniert auf jedem Geraet mit Browser - auch offline fuer Karteikarten und Quizzes." },
            ].map((faq, i) => (
              <details key={i} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                <summary className="p-4 font-medium text-gray-900 dark:text-white cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                  {faq.q}
                </summary>
                <p className="px-4 pb-4 text-gray-600 dark:text-gray-400 text-sm">{faq.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white">
            Werde Teil der smartesten Lern-Community Deutschlands
          </h2>
          <p className="mt-4 text-indigo-100 text-lg">
            1.247+ Schueler vertrauen bereits auf EduAI. Starte jetzt kostenlos.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="lg" className="gap-2 text-base px-8 bg-white text-indigo-700 hover:bg-gray-100 shadow-lg" onClick={onRegister}>
              Kostenlos starten
              <ChevronRight className="w-5 h-5" />
            </Button>
            <Button variant="outline" size="lg" className="gap-2 text-base border-white/30 text-white hover:bg-white/10" onClick={onIQTest}>
              <Brain className="w-5 h-5" />
              Gratis IQ-Test
            </Button>
          </div>
          <p className="mt-4 text-indigo-200 text-sm">Keine Kreditkarte noetig. Jederzeit kuendbar.</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 py-8 px-4">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <GraduationCap className="w-5 h-5 text-indigo-600" />
            <span className="font-bold text-gray-900 dark:text-white">EduAI Companion</span>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
            <span>DSGVO-konform</span>
            <Shield className="w-4 h-4" />
            <span>Made in Germany</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
