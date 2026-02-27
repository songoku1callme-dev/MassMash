import { useCallback } from "react";
import * as Haptics from "expo-haptics";

/**
 * Hook providing haptic feedback functions for various interactions.
 */
export function useHaptics() {
  const lightTap = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
  }, []);

  const mediumTap = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
  }, []);

  const heavyTap = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
  }, []);

  const successTap = useCallback(() => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  }, []);

  const errorTap = useCallback(() => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
  }, []);

  const selectionTap = useCallback(() => {
    Haptics.selectionAsync();
  }, []);

  return {
    lightTap,
    mediumTap,
    heavyTap,
    successTap,
    errorTap,
    selectionTap,
  };
}
