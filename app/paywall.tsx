import React from "react";
import { View, Text, Pressable, SafeAreaView, ScrollView } from "react-native";
import { useRouter } from "expo-router";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from "react-native-reanimated";
import { COLORS } from "../src/constants/theme";
import { PRICING } from "../src/constants/config";
import { useSubscriptionStore } from "../src/stores/subscriptionStore";
import { useHaptics } from "../src/hooks/useHaptics";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

const PRO_FEATURES = [
  { icon: "\uD83E\uDD16", title: "Unlimited AI Coaching", description: "Get personalized advice anytime" },
  { icon: "\uD83D\uDCCA", title: "Advanced Analytics", description: "Deep insights into your habits" },
  { icon: "\uD83C\uDFA8", title: "Custom Themes & Avatars", description: "Personalize your experience" },
  { icon: "\uD83D\uDCE4", title: "Export Your Data", description: "Download your progress data" },
  { icon: "\uD83D\uDD14", title: "Smart Reminders", description: "AI-optimized notification timing" },
  { icon: "\uD83C\uDFC6", title: "Exclusive Achievements", description: "Unlock special badges" },
];

export default function PaywallScreen() {
  const router = useRouter();
  const { purchaseMonthly, purchaseYearly, restorePurchases, isPurchasing } =
    useSubscriptionStore();
  const { lightTap, successTap } = useHaptics();
  const yearlyScale = useSharedValue(1);
  const monthlyScale = useSharedValue(1);

  const yearlyAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(yearlyScale.value) }],
  }));
  const monthlyAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(monthlyScale.value) }],
  }));

  const handleYearly = async () => {
    successTap();
    const success = await purchaseYearly();
    if (success) {
      router.replace("/(tabs)/dashboard");
    }
  };

  const handleMonthly = async () => {
    lightTap();
    const success = await purchaseMonthly();
    if (success) {
      router.replace("/(tabs)/dashboard");
    }
  };

  const handleRestore = async () => {
    lightTap();
    await restorePurchases();
  };

  const handleSkip = () => {
    lightTap();
    router.replace("/(tabs)/dashboard");
  };

  return (
    <SafeAreaView
      className="flex-1"
      style={{ backgroundColor: COLORS.background }}
    >
      <ScrollView
        contentContainerStyle={{ paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >
        {/* Close / Skip */}
        <View className="flex-row justify-end px-6 pt-4">
          <Pressable onPress={handleSkip} className="p-2">
            <Text className="text-text-muted font-inter text-sm">Skip</Text>
          </Pressable>
        </View>

        {/* Header */}
        <View className="items-center px-6 pt-4 pb-8">
          <Text className="text-5xl mb-4">{"\uD83D\uDE80"}</Text>
          <Text
            className="font-poppins-bold text-3xl mb-2 text-center"
            style={{ color: COLORS.purpleAccent }}
          >
            Unlock EvolveAI Pro
          </Text>
          <Text className="text-text-secondary font-inter text-base text-center">
            Start your 7-day free trial today
          </Text>
        </View>

        {/* Features */}
        <View className="px-6 mb-8">
          {PRO_FEATURES.map((feature) => (
            <View
              key={feature.title}
              className="flex-row items-center mb-4 p-3 rounded-xl"
              style={{ backgroundColor: COLORS.surface }}
            >
              <Text className="text-2xl mr-4">{feature.icon}</Text>
              <View className="flex-1">
                <Text className="text-text-primary font-poppins-semibold text-sm">
                  {feature.title}
                </Text>
                <Text className="text-text-secondary font-inter text-xs">
                  {feature.description}
                </Text>
              </View>
            </View>
          ))}
        </View>

        {/* Pricing Options */}
        <View className="px-6">
          {/* Yearly - Best Value */}
          <AnimatedPressable
            onPress={handleYearly}
            disabled={isPurchasing}
            onPressIn={() => {
              yearlyScale.value = 0.96;
            }}
            onPressOut={() => {
              yearlyScale.value = 1;
            }}
            style={[yearlyAnimStyle]}
            className="mb-3"
          >
            <View
              className="p-5 rounded-2xl"
              style={{
                backgroundColor: `${COLORS.purpleAccent}20`,
                borderWidth: 2,
                borderColor: COLORS.purpleAccent,
              }}
            >
              <View className="flex-row justify-between items-center">
                <View>
                  <View className="flex-row items-center mb-1">
                    <Text className="text-text-primary font-poppins-bold text-lg">
                      Yearly
                    </Text>
                    <View
                      className="ml-2 rounded-full px-2 py-0.5"
                      style={{ backgroundColor: COLORS.successGreen }}
                    >
                      <Text
                        className="font-inter-bold text-xs"
                        style={{ color: COLORS.background }}
                      >
                        SAVE 50%
                      </Text>
                    </View>
                  </View>
                  <Text className="text-text-secondary font-inter text-sm">
                    {PRICING.yearlyPerMonth} billed annually
                  </Text>
                </View>
                <Text className="text-text-primary font-poppins-bold text-xl">
                  {PRICING.yearly}
                </Text>
              </View>
            </View>
          </AnimatedPressable>

          {/* Monthly */}
          <AnimatedPressable
            onPress={handleMonthly}
            disabled={isPurchasing}
            onPressIn={() => {
              monthlyScale.value = 0.96;
            }}
            onPressOut={() => {
              monthlyScale.value = 1;
            }}
            style={[monthlyAnimStyle]}
            className="mb-6"
          >
            <View
              className="p-5 rounded-2xl"
              style={{
                backgroundColor: COLORS.surface,
                borderWidth: 1,
                borderColor: COLORS.surfaceLight,
              }}
            >
              <View className="flex-row justify-between items-center">
                <Text className="text-text-primary font-poppins-semibold text-lg">
                  Monthly
                </Text>
                <Text className="text-text-primary font-poppins-bold text-xl">
                  {PRICING.monthly}
                </Text>
              </View>
            </View>
          </AnimatedPressable>

          {/* Restore */}
          <Pressable onPress={handleRestore} className="items-center mb-4">
            <Text className="text-text-muted font-inter text-sm underline">
              Restore Purchases
            </Text>
          </Pressable>

          {/* Legal */}
          <Text className="text-text-muted font-inter text-xs text-center">
            Free 7-day trial, then auto-renews. Cancel anytime.{"\n"}
            Terms of Service | Privacy Policy
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
