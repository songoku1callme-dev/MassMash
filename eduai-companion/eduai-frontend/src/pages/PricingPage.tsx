import { useState } from "react";
import { useAuthStore } from "../stores/authStore";
import { stripeApi } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Star, Check, Zap, Camera, Mic, FileText, BarChart3, Crown, Loader2
} from "lucide-react";

export default function PricingPage() {
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleUpgrade = async () => {
    setLoading(true);
    setError("");
    try {
      const currentUrl = window.location.origin;
      const result = await stripeApi.createCheckout({
        success_url: `${currentUrl}?pro_success=1`,
        cancel_url: currentUrl,
      });
      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Erstellen der Checkout-Session");
    } finally {
      setLoading(false);
    }
  };

  const freePlan = [
    "KI-Tutor Chat (begrenzt)",
    "50 OCR-Anfragen/Monat",
    "50 Spracheingaben/Monat",
    "5 Fächer",
    "Quiz & Lernpfade",
    "RAG Wissensdatenbank",
  ];

  const proPlan = [
    "Unbegrenzt KI-Tutor Chat",
    "Unbegrenzt OCR & Mathe-Fotos",
    "Unbegrenzt Spracheingabe & Vorlesen",
    "Priorisierte KI (schnellere Antworten)",
    "Kreative Übungen & Wochenberichte",
    "PDF-Export von Chats",
    "Alles aus Kostenlos +",
  ];

  return (
    <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Wähle deinen Plan
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-2 text-lg">
          Lerne besser mit EduAI Pro
        </p>
      </div>

      {user?.is_pro && (
        <div className="flex items-center justify-center gap-2 p-4 rounded-xl bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900/20 dark:to-amber-900/20 border border-yellow-200 dark:border-yellow-800">
          <Crown className="w-6 h-6 text-yellow-600" />
          <span className="text-lg font-semibold text-yellow-800 dark:text-yellow-300">
            Du bist Pro-Mitglied!
          </span>
          <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-center">
          {error}
        </div>
      )}

      {/* Pricing Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Free Plan */}
        <Card className="relative">
          <CardHeader>
            <CardTitle className="text-xl">Kostenlos</CardTitle>
            <CardDescription>Perfekt zum Ausprobieren</CardDescription>
            <div className="mt-4">
              <span className="text-4xl font-bold text-gray-900 dark:text-white">0 EUR</span>
              <span className="text-gray-500 dark:text-gray-400 ml-1">/Monat</span>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {freePlan.map((feature, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                  {feature}
                </li>
              ))}
            </ul>
            <Button variant="outline" className="w-full mt-6" disabled>
              Aktueller Plan
            </Button>
          </CardContent>
        </Card>

        {/* Pro Plan */}
        <Card className="relative border-2 border-blue-500 dark:border-blue-400 shadow-lg">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-blue-600 text-white text-xs font-bold rounded-full uppercase tracking-wider">
            Beliebt
          </div>
          <CardHeader>
            <CardTitle className="text-xl flex items-center gap-2">
              Pro
              <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
            </CardTitle>
            <CardDescription>Für ambitionierte Schüler</CardDescription>
            <div className="mt-4">
              <span className="text-4xl font-bold text-gray-900 dark:text-white">4,99 EUR</span>
              <span className="text-gray-500 dark:text-gray-400 ml-1">/Monat</span>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {proPlan.map((feature, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <Zap className="w-4 h-4 text-blue-500 flex-shrink-0" />
                  {feature}
                </li>
              ))}
            </ul>
            {user?.is_pro ? (
              <Button className="w-full mt-6 bg-emerald-600 hover:bg-emerald-700" disabled>
                <Check className="w-4 h-4 mr-2" />
                Aktiv
              </Button>
            ) : (
              <Button
                className="w-full mt-6 bg-blue-600 hover:bg-blue-700"
                onClick={handleUpgrade}
                disabled={loading}
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Star className="w-4 h-4 mr-2" />
                )}
                {loading ? "Wird geladen..." : "Jetzt upgraden"}
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Feature Comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Pro Features im Detail</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
              <Camera className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white text-sm">Unbegrenzt OCR</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Mathe-Fotos ohne Limit</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
              <Mic className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white text-sm">Unbegrenzt Sprache</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Eingabe & Vorlesen ohne Limit</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
              <Zap className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white text-sm">Priorisierte KI</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Schnellere, kreativere Antworten</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
              <FileText className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white text-sm">PDF-Export</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Chats als PDF speichern</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
              <BarChart3 className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white text-sm">Wochenberichte</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Dein Fortschritt auf einen Blick</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
              <Crown className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white text-sm">Exklusive Übungen</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Zusatz-Aufgaben für Pro</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <p className="text-center text-xs text-gray-400 dark:text-gray-600">
        Sichere Zahlung über Stripe. Jederzeit kündbar. DSGVO-konform.
      </p>
    </div>
  );
}
