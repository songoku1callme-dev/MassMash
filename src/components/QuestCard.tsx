import React from "react";
import { View, Text, Pressable } from "react-native";
import Animated, {
  useAnimatedStyle,
  withSpring,
  useSharedValue,
} from "react-native-reanimated";
import { COLORS } from "../constants/theme";
import { useHaptics } from "../hooks/useHaptics";
import type { DailyQuest } from "../types";

interface QuestCardProps {
  quest: DailyQuest;
  onToggle: (habitId: string) => void;
}

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export function QuestCard({ quest, onToggle }: QuestCardProps) {
  const { successTap, selectionTap } = useHaptics();
  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(scale.value) }],
  }));

  const handlePressIn = () => {
    scale.value = 0.96;
  };

  const handlePressOut = () => {
    scale.value = 1;
  };

  const handlePress = () => {
    if (quest.completed) {
      selectionTap();
    } else {
      successTap();
    }
    onToggle(quest.habit.id);
  };

  return (
    <AnimatedPressable
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      onPress={handlePress}
      style={[animatedStyle]}
      className="mb-3"
    >
      <View
        className="flex-row items-center p-4 rounded-2xl"
        style={{
          backgroundColor: quest.completed
            ? `${COLORS.successGreen}15`
            : COLORS.surface,
          borderWidth: 1,
          borderColor: quest.completed
            ? `${COLORS.successGreen}40`
            : COLORS.surfaceLight,
        }}
      >
        {/* Checkbox */}
        <View
          className="w-7 h-7 rounded-full items-center justify-center mr-4"
          style={{
            backgroundColor: quest.completed
              ? COLORS.successGreen
              : "transparent",
            borderWidth: quest.completed ? 0 : 2,
            borderColor: COLORS.textMuted,
          }}
        >
          {quest.completed && (
            <Text className="text-background text-sm font-bold">
              {"\u2713"}
            </Text>
          )}
        </View>

        {/* Icon */}
        <Text className="text-2xl mr-3">{quest.habit.icon}</Text>

        {/* Info */}
        <View className="flex-1">
          <Text
            className="font-poppins-semibold text-base"
            style={{
              color: quest.completed
                ? COLORS.textSecondary
                : COLORS.textPrimary,
              textDecorationLine: quest.completed ? "line-through" : "none",
            }}
          >
            {quest.habit.title}
          </Text>
          {quest.habit.description ? (
            <Text className="text-text-secondary font-inter text-xs mt-0.5">
              {quest.habit.description}
            </Text>
          ) : null}
        </View>

        {/* XP Badge */}
        <View
          className="rounded-full px-3 py-1"
          style={{ backgroundColor: `${COLORS.purpleAccent}30` }}
        >
          <Text
            className="font-inter-bold text-xs"
            style={{ color: COLORS.purpleAccent }}
          >
            +{quest.habit.xp_reward} XP
          </Text>
        </View>
      </View>
    </AnimatedPressable>
  );
}
