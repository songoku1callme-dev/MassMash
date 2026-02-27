import React, { useEffect } from "react";
import { Text } from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withDelay,
  withSequence,
  runOnJS,
} from "react-native-reanimated";
import { COLORS } from "../constants/theme";

interface XPToastProps {
  xp: number;
  visible: boolean;
  onDismiss: () => void;
}

export function XPToast({ xp, visible, onDismiss }: XPToastProps) {
  const translateY = useSharedValue(-100);
  const opacity = useSharedValue(0);

  useEffect(() => {
    if (visible) {
      translateY.value = withSequence(
        withTiming(0, { duration: 300 }),
        withDelay(1500, withTiming(-100, { duration: 300 }))
      );
      opacity.value = withSequence(
        withTiming(1, { duration: 300 }),
        withDelay(1500, withTiming(0, { duration: 300 }, () => {
          runOnJS(onDismiss)();
        }))
      );
    }
  }, [visible, translateY, opacity, onDismiss]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
    opacity: opacity.value,
  }));

  if (!visible) return null;

  return (
    <Animated.View
      style={[
        animatedStyle,
        {
          position: "absolute",
          top: 60,
          alignSelf: "center",
          backgroundColor: COLORS.purpleAccent,
          paddingHorizontal: 24,
          paddingVertical: 12,
          borderRadius: 999,
          zIndex: 100,
        },
      ]}
    >
      <Text
        className="font-poppins-bold text-base"
        style={{ color: COLORS.textPrimary }}
      >
        +{xp} XP Earned! {"\u2728"}
      </Text>
    </Animated.View>
  );
}
