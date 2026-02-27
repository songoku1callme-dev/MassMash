import React from "react";
import { View, Text } from "react-native";
import Svg, { Circle } from "react-native-svg";
import { COLORS } from "../constants/theme";

interface LifeScoreRingProps {
  score: number;
  size?: number;
}

export function LifeScoreRing({ score, size = 120 }: LifeScoreRingProps) {
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const scoreColor =
    score >= 70
      ? COLORS.successGreen
      : score >= 40
        ? COLORS.warningYellow
        : COLORS.dangerRed;

  return (
    <View className="items-center justify-center">
      <Svg width={size} height={size}>
        {/* Background circle */}
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={COLORS.surfaceLight}
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        {/* Progress circle */}
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={scoreColor}
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          rotation="-90"
          origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <View className="absolute items-center">
        <Text
          className="font-poppins-bold text-3xl"
          style={{ color: scoreColor }}
        >
          {score}
        </Text>
        <Text className="text-text-secondary font-inter text-xs">
          Life Score
        </Text>
      </View>
    </View>
  );
}
