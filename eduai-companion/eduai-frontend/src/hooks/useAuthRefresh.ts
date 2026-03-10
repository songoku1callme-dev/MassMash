import { useEffect, useRef } from "react";
import { isTokenExpiringSoon, refreshAccessToken, clearTokens, getAccessToken } from "../services/api";
import { useAuthStore } from "../stores/authStore";

/** How often to check token expiry (ms). Default: every 60 seconds. */
const CHECK_INTERVAL_MS = 60_000;

/**
 * Periodically checks the access token expiry and refreshes it
 * before it expires. On failure, logs the user out.
 *
 * Should be mounted once at the app root when authenticated.
 */
export function useAuthRefresh() {
  const logout = useAuthStore((s) => s.logout);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    async function checkAndRefresh() {
      const token = getAccessToken();
      if (!token) return;

      // Refresh if token expires within 2 minutes
      if (isTokenExpiringSoon(120)) {
        try {
          await refreshAccessToken();
        } catch {
          // Refresh token also expired or invalid — force logout
          clearTokens();
          logout();
        }
      }
    }

    // Run immediately on mount
    checkAndRefresh();

    // Then run periodically
    intervalRef.current = setInterval(checkAndRefresh, CHECK_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [logout]);
}
