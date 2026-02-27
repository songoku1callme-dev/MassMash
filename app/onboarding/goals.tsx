import React, { useState } from "react";
import { View, Text, Pressable, SafeAreaView } from "react-native";
import { useRouter } from "expo-router";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from "react-native-reanimated";
import { COLORS } from "../../src/constants/theme";
import { useHaptics } from "../../src/hooks/useHaptics";

const GOAL_OPTIONS = [
  { id: "health", label: "Health & Fitness", icon: "\uD83D\uDCAA", description: "Exercise, nutrition, sleep" },
  { id: "wealth", label: "Wealth & Career", icon: "\uD83D\uDCB0", description: "Income, skills, networking" },
  { id: "mindset", label: "Mindset & Growth", icon: "\uD83E\uDDE0", description: "Meditation, learning, journaling" },
  { id: "relationships", label: "Relationships", icon: "\u2764\uFE0F", description: "Family, friends, community" },
  { id: "creativity", label: "Creativity", icon: "\uD83C\uDFA8", description: "Art, music, writing" },
  { id: "productivity", label: "Productivity", icon: "\u26A1", description: "Focus, time management, habits" },
];

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export default function GoalsScreen() {
  const router = useRouter();
  const [selectedGoals, setSelectedGoals] = useState<string[]>([]);
  const { lightTap, successTap } = useHaptics();
  const buttonScale = useSharedValue(1);

  const buttonAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(buttonScale.value) }],
  }));

  const toggleGoal = (id: string) => {
    lightTap();
    setSelectedGoals((prev) => {
      if (prev.includes(id)) {
        return prev.filter((g) => g !== id);
      }
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  };

  const handleContinue = () => {
    if (selectedGoals.length < 1) return;
    successTap();
    router.push({
      pathname: "/onboarding/schedule",
      params: { goals: selectedGoals.join(",") },
    });
  };

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: COLORS.background }}>
      <View className="flex-1 px-6 pt-12">
        {/* Progress indicator */}
        <View className="flex-row mb-8">
          <View className="flex-1 h-1 rounded-full mr-2" style={{ backgroundColor: COLORS.purpleAccent }} />
          <View className="flex-1 h-1 rounded-full mr-2" style={{ backgroundColor: COLORS.surfaceLight }} />
          <View className="flex-1 h-1 rounded-full" style={{ backgroundColor: COLORS.surfaceLight }} />
        </View>

        <Text className="text-text-primary font-poppins-bold text-3xl mb-2">
          Choose your quests
        </Text>
        <Text className="text-text-secondary font-inter text-base mb-8">
          Select up to 3 life areas you want to level up
        </Text>

        {/* Goal Cards */}
        <View className="flex-row flex-wrap justify-between">
          {GOAL_OPTIONS.map((goal) => {
            const isSelected = selectedGoals.includes(goal.id);
            return (
              <Pressable
                key={goal.id}
                onPress={() => toggleGoal(goal.id)}
                className="w-[48%] mb-4 rounded-2xl p-4"
                style={{
                  backgroundColor: isSelected
                    ? `${COLORS.purpleAccent}20`
                    : COLORS.surface,
                  borderWidth: 2,
                  borderColor: isSelected
                    ? COLORS.purpleAccent
                    : "transparent",
                }}
              >
                <Text className="text-3xl mb-2">{goal.icon}</Text>
                <Text className="text-text-primary font-poppins-semibold text-sm">
                  {goal.label}
                </Text>
                <Text className="text-text-muted font-inter text-xs mt-1">
                  {goal.description}
                </Text>
              </Pressable>
            );
          })}
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
            style={{
              backgroundColor:
                selectedGoals.length > 0
                  ? COLORS.purpleAccent
                  : COLORS.textMuted,
            }}
          >
            <Text className="text-text-primary font-poppins-bold text-base">
              Continue ({selectedGoals.length}/3)
            </Text>
          </View>
        </AnimatedPressable>
      </View>
    </SafeAreaView>
  );
}
