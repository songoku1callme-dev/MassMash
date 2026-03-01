import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  GraduationCap, Brain, Trophy, BookOpen, Sparkles,
  ChevronRight, Star, Zap, Shield, MessageCircle, BarChart3
} from "lucide-react";

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
      "5 KI-Persönlichkeiten", "3 Quizzes/Tag", "IQ-Test (1x/Woche)",
      "Basis-Fächer", "Gruppen-Chats",
    ],
  },
  {
    tier: "Pro", price: "4,99", period: "/Monat", features: [
      "12 KI-Persönlichkeiten", "Unbegrenzte Quizzes", "Abitur-Simulation",
      "Karteikarten + Notizen", "Prüfungs-Kalender", "Internet-Recherche",
    ], popular: true, yearPrice: "39,99",
  },
  {
    tier: "Max", price: "9,99", period: "/Monat", features: [
      "Alle 20 KI-Persönlichkeiten", "Alles in Pro", "Prioritäts-Support",
      "Erweiterte Statistiken", "PDF/Word Export", "Multiplayer-Quiz",
    ], yearPrice: "79,99",
  },
];

const TESTIMONIALS = [
  { name: "Sarah M.", grade: "12. Klasse", text: "Dank EduAI habe ich meine Mathe-Note von 4 auf 2 verbessert!", avatar: "S" },
  { name: "Tim K.", grade: "10. Klasse", text: "Der IQ-Test und die Turniere machen richtig Spaß. Lernen war noch nie so cool!", avatar: "T" },
  { name: "Lisa W.", grade: "13. Klasse", text: "Die Abitur-Simulation hat mir mega geholfen. Ich fühle mich jetzt viel sicherer.", avatar: "L" },
];

export default function LandingPage({ onLogin, onRegister, onIQTest }: LandingPageProps) {
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
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            Bereits 1.000+ Schüler lernen mit EduAI
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-gray-900 dark:text-white leading-tight">
            Deutschlands schlaueste{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">
              Lern-App
            </span>
            {" "}&ndash; powered by KI
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            IQ-Test, Abitur-Simulation, 16 Fächer, tägliche Turniere.
            20 KI-Persönlichkeiten helfen dir beim Lernen. Kostenlos starten.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="lg" className="gap-2 text-base px-8" onClick={onRegister}>
              Jetzt kostenlos starten
              <ChevronRight className="w-5 h-5" />
            </Button>
            <Button variant="outline" size="lg" className="gap-2 text-base" onClick={onIQTest}>
              <Brain className="w-5 h-5" />
              IQ testen
            </Button>
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

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            Bereit, schlauer zu werden?
          </h2>
          <p className="mt-4 text-gray-600 dark:text-gray-400">
            Starte jetzt kostenlos und entdecke, wie KI dein Lernen revolutioniert.
          </p>
          <Button size="lg" className="mt-8 gap-2 text-base px-8" onClick={onRegister}>
            Jetzt kostenlos starten
            <ChevronRight className="w-5 h-5" />
          </Button>
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
