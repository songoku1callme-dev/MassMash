import { useCallback } from "react";
import { useRouter } from "expo-router";
import { useAuthStore } from "../stores/authStore";

/**
 * Hook that gates Pro-only features.
 * Returns a function that either executes the callback (if Pro)
 * or navigates to the paywall screen.
 */
export function useProGate() {
  const router = useRouter();
  const profile = useAuthStore((s) => s.profile);

  const gateFeature = useCallback(
    (callback: () => void) => {
      if (profile?.is_pro) {
        callback();
      } else {
        router.push("/paywall");
      }
    },
    [profile, router]
  );

  const isPro = profile?.is_pro ?? false;

  return { gateFeature, isPro };
}
