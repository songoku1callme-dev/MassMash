import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  SafeAreaView,
  Dimensions,
} from "react-native";
import { LineChart } from "react-native-chart-kit";
import { COLORS } from "../../src/constants/theme";
import { useAuthStore } from "../../src/stores/authStore";
import { useHabitStore } from "../../src/stores/habitStore";
import { useProGate } from "../../src/hooks/useProGate";
import { BlurredProSection } from "../../src/components/BlurredProSection";
import { getLastNDays, getShortDayName } from "../../src/utils/date";
import { supabase } from "../../src/lib/supabase";
import type { DailyLog } from "../../src/types";

const screenWidth = Dimensions.get("window").width;

export default function AnalyticsScreen() {
  const profile = useAuthStore((s) => s.profile);
  const habits = useHabitStore((s) => s.habits);
  const { isPro } = useProGate();
  const [weeklyData, setWeeklyData] = useState<number[]>([0, 0, 0, 0, 0, 0, 0]);
  const last7Days = getLastNDays(7);

  useEffect(() => {
    fetchWeeklyData();
  }, []);

  const fetchWeeklyData = async () => {
    if (!profile) return;

    const { data, error } = await supabase
      .from("daily_logs")
      .select("*")
      .eq("user_id", profile.id)
      .eq("completed", true)
      .gte("date", last7Days[0])
      .lte("date", last7Days[6]);

    if (error) {
      console.error("Error fetching weekly data:", error);
      return;
    }

    const logs = (data ?? []) as DailyLog[];
    const dailyCounts = last7Days.map(
      (date) => logs.filter((log) => log.date === date).length
    );
    setWeeklyData(dailyCounts);
  };

  const chartConfig = {
    backgroundGradientFrom: COLORS.surface,
    backgroundGradientTo: COLORS.surface,
    color: (opacity = 1) => `rgba(138, 43, 226, ${opacity})`,
    labelColor: () => COLORS.textSecondary,
    strokeWidth: 2,
    barPercentage: 0.5,
    propsForDots: {
      r: "5",
      strokeWidth: "2",
      stroke: COLORS.purpleAccent,
    },
    propsForBackgroundLines: {
      strokeDasharray: "",
      stroke: COLORS.surfaceLight,
    },
  };

  const totalCompleted = weeklyData.reduce((sum, val) => sum + val, 0);
  const totalPossible = habits.length * 7;
  const completionRate =
    totalPossible > 0 ? Math.round((totalCompleted / totalPossible) * 100) : 0;

  return (
    <SafeAreaView
      className="flex-1"
      style={{ backgroundColor: COLORS.background }}
    >
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View className="px-6 pt-6 pb-4">
          <Text className="text-text-primary font-poppins-bold text-2xl">
            Progress
          </Text>
          <Text className="text-text-secondary font-inter text-sm">
            Track your evolution
          </Text>
        </View>

        {/* Stats Row */}
        <View className="flex-row px-6 mb-6">
          <View
            className="flex-1 rounded-2xl p-4 mr-3"
            style={{ backgroundColor: COLORS.surface }}
          >
            <Text className="text-text-secondary font-inter text-xs">
              This Week
            </Text>
            <Text className="text-text-primary font-poppins-bold text-2xl">
              {totalCompleted}
            </Text>
            <Text className="text-text-secondary font-inter text-xs">
              habits done
            </Text>
          </View>
          <View
            className="flex-1 rounded-2xl p-4 mr-3"
            style={{ backgroundColor: COLORS.surface }}
          >
            <Text className="text-text-secondary font-inter text-xs">
              Completion
            </Text>
            <Text
              className="font-poppins-bold text-2xl"
              style={{
                color:
                  completionRate >= 70
                    ? COLORS.successGreen
                    : completionRate >= 40
                      ? COLORS.warningYellow
                      : COLORS.dangerRed,
              }}
            >
              {completionRate}%
            </Text>
            <Text className="text-text-secondary font-inter text-xs">rate</Text>
          </View>
          <View
            className="flex-1 rounded-2xl p-4"
            style={{ backgroundColor: COLORS.surface }}
          >
            <Text className="text-text-secondary font-inter text-xs">
              Level
            </Text>
            <Text
              className="font-poppins-bold text-2xl"
              style={{ color: COLORS.purpleAccent }}
            >
              {profile?.level ?? 1}
            </Text>
            <Text className="text-text-secondary font-inter text-xs">
              current
            </Text>
          </View>
        </View>

        {/* Weekly Chart */}
        <View className="px-6 mb-6">
          <Text className="text-text-primary font-poppins-semibold text-lg mb-3">
            Weekly Activity
          </Text>
          <View className="rounded-2xl overflow-hidden">
            <LineChart
              data={{
                labels: last7Days.map(getShortDayName),
                datasets: [{ data: weeklyData.map((v) => Math.max(v, 0)) }],
              }}
              width={screenWidth - 48}
              height={200}
              chartConfig={chartConfig}
              bezier
              style={{ borderRadius: 16 }}
              withInnerLines={false}
              withOuterLines={false}
            />
          </View>
        </View>

        {/* Heatmap - Weekly (Pro section) */}
        <View className="px-6 mb-6">
          <Text className="text-text-primary font-poppins-semibold text-lg mb-3">
            Habit Heatmap
          </Text>
          {isPro ? (
            <View
              className="rounded-2xl p-4"
              style={{ backgroundColor: COLORS.surface }}
            >
              <View className="flex-row justify-between">
                {last7Days.map((date, i) => {
                  const count = weeklyData[i];
                  const maxCount = Math.max(...weeklyData, 1);
                  const intensity = count / maxCount;
                  return (
                    <View key={date} className="items-center">
                      <View
                        className="w-10 h-10 rounded-lg mb-1"
                        style={{
                          backgroundColor:
                            count === 0
                              ? COLORS.surfaceLight
                              : `rgba(138, 43, 226, ${0.3 + intensity * 0.7})`,
                        }}
                      />
                      <Text className="text-text-muted font-inter text-xs">
                        {getShortDayName(date)}
                      </Text>
                    </View>
                  );
                })}
              </View>
            </View>
          ) : (
            <BlurredProSection title="Habit Heatmap" height={120} />
          )}
        </View>

        {/* Monthly Trends (Pro section) */}
        <View className="px-6 mb-8">
          <Text className="text-text-primary font-poppins-semibold text-lg mb-3">
            Monthly Trends
          </Text>
          {isPro ? (
            <View
              className="rounded-2xl p-4"
              style={{ backgroundColor: COLORS.surface }}
            >
              <Text className="text-text-secondary font-inter text-sm">
                Monthly trend analysis coming soon!
              </Text>
            </View>
          ) : (
            <BlurredProSection title="Monthly Trends" height={160} />
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
