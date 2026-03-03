import { useState, useEffect } from "react";
import { Cookie, Settings, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function CookieBanner() {
  const [show, setShow] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [analytics, setAnalytics] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem("cookie_consent");
    if (!consent) setShow(true);
  }, []);

  const accept = (type: "all" | "necessary" | "custom") => {
    const value = type === "all" ? "all" : type === "necessary" ? "necessary" : `custom_analytics_${analytics}`;
    localStorage.setItem("cookie_consent", value);
    localStorage.setItem("cookie_consent_date", new Date().toISOString());
    setShow(false);
  };

  if (!show) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4">
      <div className="max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start gap-3 mb-4">
          <Cookie className="w-6 h-6 text-orange-500 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Cookie-Einstellungen</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Wir verwenden Cookies für die Funktionalität der App. Optionale Cookies helfen uns, die App zu verbessern.
              Mehr Infos in unserer <a href="/datenschutz" className="text-blue-600 underline">Datenschutzerklaerung</a>.
            </p>
          </div>
        </div>

        {showSettings && (
          <div className="mb-4 space-y-3 pl-9">
            <label className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <input type="checkbox" checked disabled className="w-4 h-4 rounded" />
              <div>
                <span className="text-sm font-medium text-gray-900 dark:text-white">Notwendige Cookies</span>
                <p className="text-xs text-gray-500">Session, Authentifizierung (immer aktiv)</p>
              </div>
            </label>
            <label className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700 cursor-pointer">
              <input type="checkbox" checked={analytics} onChange={(e) => setAnalytics(e.target.checked)} className="w-4 h-4 rounded" />
              <div>
                <span className="text-sm font-medium text-gray-900 dark:text-white">Analyse-Cookies</span>
                <p className="text-xs text-gray-500">Hilft uns die App zu verbessern (Dark Mode, Sprache)</p>
              </div>
            </label>
          </div>
        )}

        <div className="flex flex-wrap gap-2 pl-9">
          <Button onClick={() => accept("all")} size="sm" className="bg-blue-600 hover:bg-blue-700">
            <Check className="w-4 h-4 mr-1" /> Alle akzeptieren
          </Button>
          <Button onClick={() => accept("necessary")} variant="outline" size="sm">
            Nur notwendige
          </Button>
          <Button onClick={() => setShowSettings(!showSettings)} variant="ghost" size="sm">
            <Settings className="w-4 h-4 mr-1" /> Einstellungen
          </Button>
          {showSettings && (
            <Button onClick={() => accept("custom")} variant="outline" size="sm">
              Auswahl speichern
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
