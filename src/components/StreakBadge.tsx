import React from "react";
import { View, Text } from "react-native";

interface StreakBadgeProps {
  streak: number;
}

export function StreakBadge({ streak }: StreakBadgeProps) {
  return (
    <View className="flex-row items-center bg-surface rounded-full px-4 py-2">
      <Text className="text-2xl mr-2">
        {streak > 0 ? "\uD83D\uDD25" : "\u2744\uFE0F"}
      </Text>
      <View>
        <Text className="text-text-primary font-poppins-bold text-lg">
          {streak}
        </Text>
        <Text className="text-text-secondary font-inter text-xs">
          day streak
        </Text>
      </View>
    </View>
  );
}
