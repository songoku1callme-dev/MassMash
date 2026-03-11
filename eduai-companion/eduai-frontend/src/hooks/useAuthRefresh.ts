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
 * NOTE: Clerk tokens (RS256) are managed by the Clerk SDK, not by
 * our refresh endpoint. This hook only handles built-in JWT (HS256).
 */
export function useAuthRefresh() {
  const logout = useAuthStore((s) => s.logout);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    async function checkAndRefresh() {
      const token = getAccessToken();
      if (!token) return;

      // Clerk tokens are refreshed by the Clerk SDK (via registerClerkGetToken).
      // Do NOT try to refresh them via /api/auth/refresh — that endpoint only
      // handles built-in JWT refresh tokens, and calling it with a Clerk token
      // triggers 429 rate limits and a logout loop.
      if (isClerkToken(token)) return;

      // Refresh if token expires within 2 minutes (built-in JWT only)
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
