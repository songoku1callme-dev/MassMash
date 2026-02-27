import React from "react";
import { View, Text } from "react-native";
import Animated, {
  useAnimatedStyle,
  withSpring,
} from "react-native-reanimated";
import { levelProgress, formatXP, getLevelTitle } from "../utils/xp";
import { COLORS } from "../constants/theme";

interface XPBarProps {
  xp: number;
  level: number;
}

export function XPBar({ xp, level }: XPBarProps) {
  const progress = levelProgress(xp);
  const title = getLevelTitle(level);

  const animatedWidth = useAnimatedStyle(() => ({
    width: withSpring(`${Math.max(progress * 100, 2)}%` as unknown as number, {
      damping: 15,
      stiffness: 100,
    }),
  }));

  return (
    <View className="px-4 py-3">
      <View className="flex-row justify-between items-center mb-2">
        <View className="flex-row items-center">
          <Text className="text-purple-accent font-poppins-bold text-lg">
            Lv. {level}
          </Text>
          <Text className="text-text-secondary font-inter ml-2 text-sm">
            {title}
          </Text>
        </View>
        <Text className="text-text-secondary font-inter text-sm">
          {formatXP(xp)}
        </Text>
      </View>
      <View
        className="h-3 bg-surface-light rounded-full overflow-hidden"
        style={{ backgroundColor: COLORS.surfaceLight }}
      >
        <Animated.View
          className="h-full rounded-full"
          style={[
            {
              backgroundColor: COLORS.purpleAccent,
            },
            animatedWidth,
          ]}
        />
      </View>
    </View>
  );
}
