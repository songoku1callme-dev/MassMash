import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from "react-native-reanimated";
import { COLORS } from "../../src/constants/theme";
import { useHaptics } from "../../src/hooks/useHaptics";
import { useAuthStore } from "../../src/stores/authStore";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export default function ProfileScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    goals: string;
    bedtime: string;
    wakeTime: string;
  }>();
  const [displayName, setDisplayName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  const { successTap } = useHaptics();
  const buttonScale = useSharedValue(1);

  const buttonAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(buttonScale.value) }],
  }));

  const handleComplete = async () => {
    if (!displayName.trim()) return;
    successTap();
    setIsLoading(true);

    await completeOnboarding({
      display_name: displayName.trim(),
      goals: (params.goals ?? "").split(","),
      sleep_schedule: {
        bedtime: params.bedtime ?? "10:30 PM",
        wake_time: params.wakeTime ?? "6:30 AM",
      },
    });

    setIsLoading(false);
    router.replace("/paywall");
  };

  return (
    <SafeAreaView
      className="flex-1"
      style={{ backgroundColor: COLORS.background }}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        className="flex-1"
      >
        <View className="flex-1 px-6 pt-12">
          {/* Progress indicator */}
          <View className="flex-row mb-8">
            <View
              className="flex-1 h-1 rounded-full mr-2"
              style={{ backgroundColor: COLORS.purpleAccent }}
            />
            <View
              className="flex-1 h-1 rounded-full mr-2"
              style={{ backgroundColor: COLORS.purpleAccent }}
            />
            <View
              className="flex-1 h-1 rounded-full"
              style={{ backgroundColor: COLORS.purpleAccent }}
            />
          </View>

          <Text className="text-text-primary font-poppins-bold text-3xl mb-2">
            What should we call you?
          </Text>
          <Text className="text-text-secondary font-inter text-base mb-8">
            Every hero needs a name for their journey.
          </Text>

          {/* Avatar placeholder */}
          <View className="items-center mb-8">
            <View
              className="w-24 h-24 rounded-full items-center justify-center"
              style={{ backgroundColor: `${COLORS.purpleAccent}30` }}
            >
              <Text className="text-4xl">{"\uD83E\uDDD1\u200D\uD83D\uDE80"}</Text>
            </View>
          </View>

          {/* Name Input */}
          <TextInput
            placeholder="Enter your name"
            placeholderTextColor={COLORS.textMuted}
            value={displayName}
            onChangeText={setDisplayName}
            autoCapitalize="words"
            className="text-text-primary font-inter text-lg p-4 rounded-xl text-center mb-4"
            style={{ backgroundColor: COLORS.surface }}
          />

          <View className="flex-1" />

          {/* Complete Button */}
          <AnimatedPressable
            onPress={handleComplete}
            disabled={isLoading || !displayName.trim()}
            onPressIn={() => {
              buttonScale.value = 0.96;
            }}
            onPressOut={() => {
              buttonScale.value = 1;
            }}
            style={[buttonAnimStyle]}
            className="mb-8"
          >
            <View
              className="p-4 rounded-xl items-center"
              style={{
                backgroundColor:
                  displayName.trim() && !isLoading
                    ? COLORS.purpleAccent
                    : COLORS.textMuted,
              }}
            >
              <Text className="text-text-primary font-poppins-bold text-base">
                {isLoading ? "Setting up..." : "Begin Your Journey"}
              </Text>
            </View>
          </AnimatedPressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
