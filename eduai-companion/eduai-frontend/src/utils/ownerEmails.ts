/**
 * Owner-Email Whitelist + Hook
 * Owners bekommen volle Rechte: Admin-Panel, Forschungs-Zentrum,
 * gruener Stern, "Owner"-Label, keine Upgrade-CTAs.
 *
 * Emails werden aus VITE_OWNER_EMAILS geladen (komma-separiert).
 * Muss in .env / Vercel gesetzt werden.
 */
import { useUser } from "@clerk/clerk-react";
import { useAuthStore } from "../stores/authStore";

/** Parse owner emails from env var (comma-separated, trimmed, lowercased) */
function loadOwnerEmails(): string[] {
  const raw = import.meta.env.VITE_OWNER_EMAILS || "";
  if (!raw) return [];
  return raw
    .split(",")
    .map((e: string) => e.trim().toLowerCase())
    .filter(Boolean);
}

export const OWNER_EMAILS: string[] = loadOwnerEmails();

/** Pure utility — prueft ob eine Email in der Owner-Liste ist */
export function isOwnerEmail(email?: string | null): boolean {
  if (!email) return false;
  return OWNER_EMAILS.includes(email.toLowerCase());
}

/**
 * React Hook — prueft ob der aktuelle User ein Owner ist.
 * Prueft zuerst die Clerk-Email (primaere Quelle), dann Fallback auf AuthStore.
 */
export function useIsOwner(): boolean {
  // Clerk-Email (primaere Quelle bei echtem Login)
  const { user: clerkUser } = useUser();
  const clerkEmail =
    clerkUser?.primaryEmailAddress?.emailAddress
    ?? clerkUser?.emailAddresses?.[0]?.emailAddress
    ?? "";

  // AuthStore-Email (Fallback, z.B. bei dev-token)
  const authEmail = useAuthStore((s) => s.user?.email);

  return isOwnerEmail(clerkEmail) || isOwnerEmail(authEmail);
}
