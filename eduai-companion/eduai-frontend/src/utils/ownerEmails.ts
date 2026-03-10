/**
 * Owner email whitelist — these users get ALL rights:
 * is_admin=true, is_pro=true, is_max=true, no rate limits, no upgrade prompts.
 *
 * This list mirrors the backend ADMIN_EMAILS in auth.py and admin.py.
 */
export const OWNER_EMAILS: string[] = [
  "songoku1callme@gmail.com",
  "ahmadalkhalaf2019@gmail.com",
  "ahmadalkhalaf20024@gmail.com",
  "ahmadalkhalaf1245@gmail.com",
  "261g2g261@gmail.com",
  "261al3nzi261@gmail.com",
];

/**
 * Check if an email belongs to an owner.
 * Owners bypass all feature gates, upgrade prompts, and rate limits.
 */
export function isOwnerEmail(email: string | undefined | null): boolean {
  if (!email) return false;
  return OWNER_EMAILS.some((e) => e.toLowerCase() === email.toLowerCase());
}
