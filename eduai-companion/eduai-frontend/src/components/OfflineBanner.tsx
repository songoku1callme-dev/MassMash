import { useEffect, useState } from "react";
import { WifiOff, Wifi } from "lucide-react";
import { useNetworkStatus } from "../hooks/useCapacitor";

export default function OfflineBanner() {
  const { isOnline } = useNetworkStatus();
  const [isOffline, setIsOffline] = useState(!isOnline);
  const [showReconnect, setShowReconnect] = useState(false);

  useEffect(() => {
    if (isOnline && isOffline) {
      // Was offline, now back online
      setIsOffline(false);
      setShowReconnect(true);
      setTimeout(() => setShowReconnect(false), 3000);
    } else if (!isOnline) {
      setIsOffline(true);
    }
  }, [isOnline]);

  if (!isOffline && !showReconnect) return null;

  if (showReconnect) {
    return (
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 bg-green-600 text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-2 text-sm font-medium animate-fade-in">
        <Wifi className="w-4 h-4" />
        Wieder online - Daten werden synchronisiert
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 bg-orange-600 text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-2 text-sm font-medium">
      <WifiOff className="w-4 h-4" />
      Offline - Karteikarten und Notizen verfügbar
    </div>
  );
}
