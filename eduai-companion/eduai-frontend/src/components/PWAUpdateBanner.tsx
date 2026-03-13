import { useState, useEffect, useCallback } from "react";
import { RefreshCw, X } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * PWA Auto-Updater Banner
 * - Checks for new service worker versions every 5 minutes and on window focus
 * - Shows "Update available" banner when a new version is detected
 * - User clicks "Reload" to activate the new service worker and refresh
 */
export default function PWAUpdateBanner() {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const checkForUpdate = useCallback(() => {
    if (!("serviceWorker" in navigator)) return;

    navigator.serviceWorker.getRegistration().then((registration) => {
      if (registration) {
        registration.update().catch(() => {
          // Silent fail — network might be offline
        });
      }
    });
  }, []);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    // Listen for new service worker waiting
    const handleControllerChange = () => {
      // New SW activated — reload
      window.location.reload();
    };

    const listenForWaiting = (registration: ServiceWorkerRegistration) => {
      // If there's already a waiting worker
      if (registration.waiting) {
        setUpdateAvailable(true);
        setWaitingWorker(registration.waiting);
        return;
      }

      // Listen for new installing worker
      registration.addEventListener("updatefound", () => {
        const newWorker = registration.installing;
        if (!newWorker) return;

        newWorker.addEventListener("statechange", () => {
          if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
            // New version installed but waiting to activate
            setUpdateAvailable(true);
            setWaitingWorker(newWorker);
          }
        });
      });
    };

    navigator.serviceWorker.ready.then(listenForWaiting);
    navigator.serviceWorker.addEventListener("controllerchange", handleControllerChange);

    // Check for updates every 5 minutes
    const interval = setInterval(checkForUpdate, 5 * 60 * 1000);

    // Check on window focus (user returns to tab)
    const handleFocus = () => checkForUpdate();
    window.addEventListener("focus", handleFocus);

    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", handleFocus);
      navigator.serviceWorker.removeEventListener("controllerchange", handleControllerChange);
    };
  }, [checkForUpdate]);

  const handleUpdate = () => {
    if (waitingWorker) {
      // Tell the waiting SW to skip waiting and become active
      waitingWorker.postMessage({ type: "SKIP_WAITING" });
    }
    // Fallback: force reload after a short delay
    setTimeout(() => window.location.reload(), 1000);
  };

  const handleDismiss = () => {
    setDismissed(true);
    // Show again after 30 minutes if still not updated
    setTimeout(() => setDismissed(false), 30 * 60 * 1000);
  };

  if (!updateAvailable || dismissed) return null;

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[9999] animate-in slide-in-from-top-4">
      <div
        className="flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl border"
        style={{
          background: "linear-gradient(135deg, rgba(99,102,241,0.95) 0%, rgba(139,92,246,0.95) 100%)",
          borderColor: "rgba(255,255,255,0.15)",
          backdropFilter: "blur(10px)",
        }}
      >
        <RefreshCw className="w-5 h-5 text-white animate-spin" style={{ animationDuration: "3s" }} />
        <span className="text-white text-sm font-medium">
          Neue Version verfügbar!
        </span>
        <Button
          onClick={handleUpdate}
          size="sm"
          className="bg-white text-indigo-700 hover:bg-white/90 text-xs font-bold px-3"
        >
          Jetzt aktualisieren
        </Button>
        <button
          onClick={handleDismiss}
          className="text-white/60 hover:text-white transition-colors ml-1"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
