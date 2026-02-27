import React, { useState } from "react";
import { View, Text, Pressable, SafeAreaView } from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from "react-native-reanimated";
import { COLORS } from "../../src/constants/theme";
import { useHaptics } from "../../src/hooks/useHaptics";

const BEDTIME_OPTIONS = [
  "9:00 PM",
  "9:30 PM",
  "10:00 PM",
  "10:30 PM",
  "11:00 PM",
  "11:30 PM",
  "12:00 AM",
];

const WAKE_OPTIONS = [
  "5:00 AM",
  "5:30 AM",
  "6:00 AM",
  "6:30 AM",
  "7:00 AM",
  "7:30 AM",
  "8:00 AM",
];

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export default function ScheduleScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ goals: string }>();
  const [bedtime, setBedtime] = useState("10:30 PM");
  const [wakeTime, setWakeTime] = useState("6:30 AM");
  const { lightTap, successTap } = useHaptics();
  const buttonScale = useSharedValue(1);

  const buttonAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(buttonScale.value) }],
  }));

  const handleContinue = () => {
    successTap();
    router.push({
      pathname: "/onboarding/profile",
      params: {
        goals: params.goals ?? "",
        bedtime,
        wakeTime,
      },
    });
  };

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: COLORS.background }}>
      <View className="flex-1 px-6 pt-12">
        {/* Progress indicator */}
        <View className="flex-row mb-8">
          <View className="flex-1 h-1 rounded-full mr-2" style={{ backgroundColor: COLORS.purpleAccent }} />
          <View className="flex-1 h-1 rounded-full mr-2" style={{ backgroundColor: COLORS.purpleAccent }} />
          <View className="flex-1 h-1 rounded-full" style={{ backgroundColor: COLORS.surfaceLight }} />
        </View>

        <Text className="text-text-primary font-poppins-bold text-3xl mb-2">
          Sleep schedule
        </Text>
        <Text className="text-text-secondary font-inter text-base mb-8">
          Good sleep = More HP. Set your ideal schedule.
        </Text>

        {/* Bedtime */}
        <Text className="text-text-primary font-poppins-semibold text-lg mb-3">
          {"\uD83C\uDF19"} Bedtime
        </Text>
        <View className="flex-row flex-wrap mb-6">
          {BEDTIME_OPTIONS.map((time) => (
            <Pressable
              key={time}
              onPress={() => {
                lightTap();
                setBedtime(time);
              }}
              className="rounded-full px-4 py-2 mr-2 mb-2"
              style={{
                backgroundColor:
                  bedtime === time
                    ? COLORS.purpleAccent
                    : COLORS.surface,
              }}
            >
              <Text
                className="font-inter text-sm"
                style={{
                  color:
                    bedtime === time
                      ? COLORS.textPrimary
                      : COLORS.textSecondary,
                }}
              >
                {time}
              </Text>
            </Pressable>
          ))}
        </View>

        {/* Wake Time */}
        <Text className="text-text-primary font-poppins-semibold text-lg mb-3">
          {"\u2600\uFE0F"} Wake Time
        </Text>
        <View className="flex-row flex-wrap mb-6">
          {WAKE_OPTIONS.map((time) => (
            <Pressable
              key={time}
              onPress={() => {
                lightTap();
                setWakeTime(time);
              }}
              className="rounded-full px-4 py-2 mr-2 mb-2"
              style={{
                backgroundColor:
                  wakeTime === time
                    ? COLORS.cyberBlue
                    : COLORS.surface,
              }}
            >
              <Text
                className="font-inter text-sm"
                style={{
                  color:
                    wakeTime === time
                      ? COLORS.background
                      : COLORS.textSecondary,
                }}
              >
                {time}
              </Text>
            </Pressable>
          ))}
        </View>

        <View className="flex-1" />

        {/* Continue Button */}
        <AnimatedPressable
          onPress={handleContinue}
          onPressIn={() => { buttonScale.value = 0.96; }}
          onPressOut={() => { buttonScale.value = 1; }}
          style={[buttonAnimStyle]}
          className="mb-8"
        >
          <View
            className="p-4 rounded-xl items-center"
            style={{ backgroundColor: COLORS.purpleAccent }}
          >
            <Text className="text-text-primary font-poppins-bold text-base">
              Continue
            </Text>
          </View>
        </AnimatedPressable>
      </View>
    </SafeAreaView>
  );
}
