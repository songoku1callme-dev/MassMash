import React from "react";
import { View, Text } from "react-native";
import { COLORS } from "../constants/theme";

interface HPBarProps {
  hp: number;
  maxHp: number;
}

export function HPBar({ hp, maxHp }: HPBarProps) {
  const percentage = Math.max((hp / maxHp) * 100, 0);

  const barColor =
    percentage > 60
      ? COLORS.successGreen
      : percentage > 30
        ? COLORS.warningYellow
        : COLORS.dangerRed;

  return (
    <View className="px-4 py-2">
      <View className="flex-row justify-between items-center mb-1">
        <Text className="text-text-secondary font-inter text-xs">HP</Text>
        <Text className="text-text-secondary font-inter text-xs">
          {hp}/{maxHp}
        </Text>
      </View>
      <View
        className="h-2 rounded-full overflow-hidden"
        style={{ backgroundColor: COLORS.surfaceLight }}
      >
        <View
          className="h-full rounded-full"
          style={{
            width: `${percentage}%`,
            backgroundColor: barColor,
          }}
        />
      </View>
    </View>
  );
}
