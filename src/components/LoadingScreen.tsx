import React from "react";
import { View, Text, ActivityIndicator } from "react-native";
import { COLORS } from "../constants/theme";

export function LoadingScreen() {
  return (
    <View
      className="flex-1 items-center justify-center"
      style={{ backgroundColor: COLORS.background }}
    >
      <Text className="text-purple-accent font-poppins-bold text-3xl mb-4">
        EvolveAI
      </Text>
      <ActivityIndicator size="large" color={COLORS.purpleAccent} />
    </View>
  );
}
