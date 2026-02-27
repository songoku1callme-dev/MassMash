import React from "react";
import { View, Text, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { COLORS } from "../constants/theme";
import { ProBadge } from "./ProBadge";

interface BlurredProSectionProps {
  title: string;
  height?: number;
}

/**
 * Overlay that blurs/hides Pro-only content with a CTA to upgrade.
 */
export function BlurredProSection({
  title,
  height = 200,
}: BlurredProSectionProps) {
  const router = useRouter();

  return (
    <Pressable onPress={() => router.push("/paywall")}>
      <View
        className="rounded-2xl items-center justify-center overflow-hidden"
        style={{
          height,
          backgroundColor: `${COLORS.surface}CC`,
          borderWidth: 1,
          borderColor: COLORS.surfaceLight,
        }}
      >
        <ProBadge />
        <Text className="text-text-primary font-poppins-semibold text-lg mt-3">
          {title}
        </Text>
        <Text className="text-text-secondary font-inter text-sm mt-1">
          Upgrade to Pro to unlock
        </Text>
        <View
          className="rounded-full px-6 py-2 mt-4"
          style={{ backgroundColor: COLORS.purpleAccent }}
        >
          <Text className="text-text-primary font-poppins-bold text-sm">
            Unlock Now
          </Text>
        </View>
      </View>
    </Pressable>
  );
}
