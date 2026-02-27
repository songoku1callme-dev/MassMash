import React from "react";
import { Tabs } from "expo-router";
import { Text, View } from "react-native";
import { COLORS } from "../../src/constants/theme";

interface TabIconProps {
  icon: string;
  label: string;
  focused: boolean;
}

function TabIcon({ icon, label, focused }: TabIconProps) {
  return (
    <View className="items-center justify-center pt-2">
      <Text style={{ fontSize: 22 }}>{icon}</Text>
      <Text
        className="font-inter text-xs mt-1"
        style={{
          color: focused ? COLORS.purpleAccent : COLORS.textMuted,
        }}
      >
        {label}
      </Text>
    </View>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: COLORS.surface,
          borderTopColor: COLORS.surfaceLight,
          borderTopWidth: 1,
          height: 85,
          paddingBottom: 20,
        },
        tabBarShowLabel: false,
        tabBarActiveTintColor: COLORS.purpleAccent,
        tabBarInactiveTintColor: COLORS.textMuted,
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon={"\u2694\uFE0F"} label="Quests" focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="coach"
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon={"\uD83E\uDD16"} label="AI Coach" focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="analytics"
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon={"\uD83D\uDCCA"} label="Progress" focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon={"\u2699\uFE0F"} label="Settings" focused={focused} />
          ),
        }}
      />
    </Tabs>
  );
}
