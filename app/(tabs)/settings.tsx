import React from "react";
import {
  View,
  Text,
  Pressable,
  SafeAreaView,
  ScrollView,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import { COLORS } from "../../src/constants/theme";
import { useAuthStore } from "../../src/stores/authStore";
import { useSubscriptionStore } from "../../src/stores/subscriptionStore";
import { ProBadge } from "../../src/components/ProBadge";
import { useHaptics } from "../../src/hooks/useHaptics";

interface SettingsRowProps {
  icon: string;
  title: string;
  subtitle?: string;
  onPress: () => void;
  danger?: boolean;
  trailing?: React.ReactNode;
}

function SettingsRow({
  icon,
  title,
  subtitle,
  onPress,
  danger = false,
  trailing,
}: SettingsRowProps) {
  return (
    <Pressable
      onPress={onPress}
      className="flex-row items-center p-4 mb-1 rounded-xl"
      style={{ backgroundColor: COLORS.surface }}
    >
      <Text className="text-xl mr-4">{icon}</Text>
      <View className="flex-1">
        <Text
          className="font-poppins-semibold text-sm"
          style={{ color: danger ? COLORS.dangerRed : COLORS.textPrimary }}
        >
          {title}
        </Text>
        {subtitle ? (
          <Text className="text-text-muted font-inter text-xs mt-0.5">
            {subtitle}
          </Text>
        ) : null}
      </View>
      {trailing}
      <Text className="text-text-muted text-lg ml-2">{"\u203A"}</Text>
    </Pressable>
  );
}

export default function SettingsScreen() {
  const router = useRouter();
  const profile = useAuthStore((s) => s.profile);
  const signOut = useAuthStore((s) => s.signOut);
  const deleteAccount = useAuthStore((s) => s.deleteAccount);
  const subscription = useSubscriptionStore((s) => s.subscription);
  const { lightTap, errorTap } = useHaptics();

  const handleSignOut = () => {
    lightTap();
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          await signOut();
          router.replace("/(auth)/login");
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    errorTap();
    Alert.alert(
      "Delete Account",
      "This will permanently delete your account and all data. This action cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete Everything",
          style: "destructive",
          onPress: async () => {
            await deleteAccount();
            router.replace("/(auth)/login");
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView
      className="flex-1"
      style={{ backgroundColor: COLORS.background }}
    >
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View className="px-6 pt-6 pb-4">
          <Text className="text-text-primary font-poppins-bold text-2xl">
            Settings
          </Text>
        </View>

        {/* Profile Card */}
        <View className="px-6 mb-6">
          <View
            className="rounded-2xl p-5 flex-row items-center"
            style={{ backgroundColor: COLORS.surface }}
          >
            <View
              className="w-14 h-14 rounded-full items-center justify-center mr-4"
              style={{ backgroundColor: `${COLORS.purpleAccent}30` }}
            >
              <Text className="text-2xl">{"\uD83E\uDDD1\u200D\uD83D\uDE80"}</Text>
            </View>
            <View className="flex-1">
              <View className="flex-row items-center">
                <Text className="text-text-primary font-poppins-bold text-lg mr-2">
                  {profile?.display_name ?? "Hero"}
                </Text>
                {subscription.tier === "pro" && <ProBadge small />}
              </View>
              <Text className="text-text-secondary font-inter text-sm">
                {profile?.email ?? ""}
              </Text>
              <Text className="text-text-muted font-inter text-xs mt-1">
                Level {profile?.level ?? 1} {"\u2022"}{" "}
                {(profile?.xp ?? 0).toLocaleString()} XP
              </Text>
            </View>
          </View>
        </View>

        {/* Subscription */}
        <View className="px-6 mb-6">
          <Text className="text-text-secondary font-inter-semibold text-xs mb-2 uppercase tracking-wider">
            Subscription
          </Text>
          {subscription.tier === "pro" ? (
            <View
              className="rounded-2xl p-4"
              style={{
                backgroundColor: `${COLORS.purpleAccent}15`,
                borderWidth: 1,
                borderColor: `${COLORS.purpleAccent}40`,
              }}
            >
              <View className="flex-row items-center">
                <ProBadge />
                <Text className="text-text-primary font-poppins-semibold text-sm ml-3">
                  EvolveAI Pro Active
                </Text>
              </View>
            </View>
          ) : (
            <Pressable
              onPress={() => {
                lightTap();
                router.push("/paywall");
              }}
            >
              <View
                className="rounded-2xl p-4"
                style={{ backgroundColor: COLORS.surface }}
              >
                <Text className="text-text-primary font-poppins-semibold text-sm">
                  {"\uD83D\uDE80"} Upgrade to Pro
                </Text>
                <Text className="text-text-secondary font-inter text-xs mt-1">
                  Unlock unlimited AI coaching and more
                </Text>
              </View>
            </Pressable>
          )}
        </View>

        {/* Settings Rows */}
        <View className="px-6 mb-6">
          <Text className="text-text-secondary font-inter-semibold text-xs mb-2 uppercase tracking-wider">
            Account
          </Text>
          <SettingsRow
            icon={"\uD83D\uDD14"}
            title="Notifications"
            subtitle="Manage reminders"
            onPress={() => lightTap()}
          />
          <SettingsRow
            icon={"\uD83C\uDFA8"}
            title="Appearance"
            subtitle="Theme & display"
            onPress={() => lightTap()}
          />
          <SettingsRow
            icon={"\uD83D\uDCE4"}
            title="Export Data"
            subtitle="Download your progress"
            onPress={() => {
              lightTap();
              if (!profile?.is_pro) {
                router.push("/paywall");
              }
            }}
            trailing={!profile?.is_pro ? <ProBadge small /> : undefined}
          />
        </View>

        <View className="px-6 mb-6">
          <Text className="text-text-secondary font-inter-semibold text-xs mb-2 uppercase tracking-wider">
            Support
          </Text>
          <SettingsRow
            icon={"\u2753"}
            title="Help & FAQ"
            onPress={() => lightTap()}
          />
          <SettingsRow
            icon={"\u2B50"}
            title="Rate EvolveAI"
            onPress={() => lightTap()}
          />
          <SettingsRow
            icon={"\uD83D\uDCE7"}
            title="Contact Us"
            onPress={() => lightTap()}
          />
        </View>

        <View className="px-6 mb-8">
          <Text className="text-text-secondary font-inter-semibold text-xs mb-2 uppercase tracking-wider">
            Danger Zone
          </Text>
          <SettingsRow
            icon={"\uD83D\uDEAA"}
            title="Sign Out"
            onPress={handleSignOut}
          />
          <SettingsRow
            icon={"\uD83D\uDDD1\uFE0F"}
            title="Delete Account & Data"
            subtitle="GDPR - Permanently delete everything"
            onPress={handleDeleteAccount}
            danger
          />
        </View>

        <Text className="text-text-muted font-inter text-xs text-center mb-8">
          EvolveAI v1.0.0
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}
