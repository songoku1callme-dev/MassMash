import { useState, useEffect } from "react";
import { X, Download, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/button";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export default function PWAInstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showBanner, setShowBanner] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Check if already dismissed or installed
    const wasDismissed = localStorage.getItem("lumnos_pwa_dismissed");
    if (wasDismissed) {
      setDismissed(true);
      return;
    }

    // Track visit count for showing banner on 3rd visit
    const visits = parseInt(localStorage.getItem("lumnos_visit_count") || "0") + 1;
    localStorage.setItem("lumnos_visit_count", String(visits));

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      // Show on 3rd visit or later
      if (visits >= 3) {
        setShowBanner(true);
      }
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setShowBanner(false);
      localStorage.setItem("lumnos_pwa_dismissed", "true");
    }
    setDeferredPrompt(null);
  };

  const handleDismiss = () => {
    setShowBanner(false);
    setDismissed(true);
    localStorage.setItem("lumnos_pwa_dismissed", "true");
  };

  if (!showBanner || dismissed) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 z-50 animate-in slide-in-from-bottom-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-start gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shrink-0">
            <Smartphone className="w-6 h-6" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-gray-900 dark:text-white text-sm">
              Lumnos installieren
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Installiere die App auf deinem Handy für schnellen Zugriff — auch offline!
            </p>
            <div className="flex gap-2 mt-3">
              <Button onClick={handleInstall} size="sm" className="gap-1.5 text-xs">
                <Download className="w-3.5 h-3.5" />
                Installieren
              </Button>
              <Button onClick={handleDismiss} variant="ghost" size="sm" className="text-xs text-gray-500">
                Spaeter
              </Button>
            </div>
          </div>
          <button onClick={handleDismiss} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
