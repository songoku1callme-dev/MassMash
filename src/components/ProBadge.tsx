import React from "react";
import { View, Text } from "react-native";
import { COLORS } from "../constants/theme";

interface ProBadgeProps {
  small?: boolean;
}

export function ProBadge({ small = false }: ProBadgeProps) {
  return (
    <View
      className="rounded-full items-center justify-center"
      style={{
        backgroundColor: `${COLORS.warningYellow}20`,
        paddingHorizontal: small ? 8 : 12,
        paddingVertical: small ? 2 : 4,
      }}
    >
      <Text
        className="font-poppins-bold"
        style={{
          color: COLORS.warningYellow,
          fontSize: small ? 10 : 12,
        }}
      >
        PRO
      </Text>
    </View>
  );
}
