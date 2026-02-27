import { useEffect } from "react";
import { useRouter } from "expo-router";
import { useAuthStore } from "../src/stores/authStore";
import { LoadingScreen } from "../src/components/LoadingScreen";

/**
 * Root index: redirects based on auth/onboarding state.
 */
export default function Index() {
  const router = useRouter();
  const session = useAuthStore((s) => s.session);
  const isLoading = useAuthStore((s) => s.isLoading);
  const hasCompletedOnboarding = useAuthStore((s) => s.hasCompletedOnboarding);

  useEffect(() => {
    if (isLoading) return;

    if (!session) {
      router.replace("/(auth)/login");
    } else if (!hasCompletedOnboarding) {
      router.replace("/onboarding/goals");
    } else {
      router.replace("/(tabs)/dashboard");
    }
  }, [session, isLoading, hasCompletedOnboarding, router]);

  return <LoadingScreen />;
}
