import { useEffect, useRef } from "react";
import { isTokenExpiringSoon, refreshAccessToken, clearTokens, getAccessToken, isClerkToken } from "../services/api";
import { useAuthStore } from "../stores/authStore";

/** How often to check token expiry (ms). Default: every 60 seconds. */
const CHECK_INTERVAL_MS = 60_000;

/**
 * Periodically checks the access token expiry and refreshes it
 * before it expires. On failure, logs the user out.
 *
 * Should be mounted once at the app root when authenticated.
 *
 * IMPORTANT: Clerk tokens are refreshed automatically by the Clerk SDK
 * and must NOT be sent to /api/auth/refresh — doing so causes 429 loops.
 */
export function useAuthRefresh() {
  const logout = useAuthStore((s) => s.logout);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    async function checkAndRefresh() {
      const token = getAccessToken();
      if (!token) return;

      // Clerk tokens auto-refresh via the Clerk SDK.
      // Never call our backend /api/auth/refresh for them — it causes 429 rate-limit loops.
      if (isClerkToken(token)) return;

      // Only refresh built-in JWT tokens via our backend
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
