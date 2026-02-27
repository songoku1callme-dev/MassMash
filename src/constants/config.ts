/**
 * App configuration constants.
 * All sensitive values (API keys) must come from environment variables.
 * These placeholders are used for structure; real keys should be in .env
 */

export const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL ?? "";
export const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? "";
export const REVENUECAT_API_KEY_IOS = process.env.EXPO_PUBLIC_REVENUECAT_IOS ?? "";
export const REVENUECAT_API_KEY_ANDROID = process.env.EXPO_PUBLIC_REVENUECAT_ANDROID ?? "";

/** RevenueCat product identifiers */
export const RC_ENTITLEMENT_ID = "pro";
export const RC_MONTHLY_PRODUCT = "evolveai_pro_monthly";
export const RC_YEARLY_PRODUCT = "evolveai_pro_yearly";

/** Free-tier limits */
export const FREE_AI_INTERACTIONS_PER_DAY = 1;

/** Subscription pricing (display only) */
export const PRICING = {
  monthly: "$9.99/month",
  yearly: "$59.99/year",
  yearlyPerMonth: "$4.99/month",
} as const;
