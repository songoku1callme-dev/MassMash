import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  SafeAreaView,
  Pressable,
  RefreshControl,
} from "react-native";
import { COLORS } from "../../src/constants/theme";
import { useAuthStore } from "../../src/stores/authStore";
import { useHabitStore } from "../../src/stores/habitStore";
import { XPBar } from "../../src/components/XPBar";
import { HPBar } from "../../src/components/HPBar";
import { StreakBadge } from "../../src/components/StreakBadge";
import { LifeScoreRing } from "../../src/components/LifeScoreRing";
import { QuestCard } from "../../src/components/QuestCard";
import { AddHabitModal } from "../../src/components/AddHabitModal";
import { XPToast } from "../../src/components/XPToast";
import { getGreeting } from "../../src/utils/date";
import { calculateLevel } from "../../src/utils/xp";

export default function DashboardScreen() {
  const profile = useAuthStore((s) => s.profile);
  const { habits, fetchHabits, fetchTodayLogs, toggleHabit, addHabit, getDailyQuests, getCompletedCount, getTotalCount } =
    useHabitStore();
  const [showAddModal, setShowAddModal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [toastXP, setToastXP] = useState(0);
  const [showToast, setShowToast] = useState(false);

  useEffect(() => {
    fetchHabits();
    fetchTodayLogs();
  }, [fetchHabits, fetchTodayLogs]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([fetchHabits(), fetchTodayLogs()]);
    setRefreshing(false);
  }, [fetchHabits, fetchTodayLogs]);

  const handleToggle = async (habitId: string) => {
    const quest = getDailyQuests().find((q) => q.habit.id === habitId);
    if (quest && !quest.completed) {
      setToastXP(quest.habit.xp_reward);
      setShowToast(true);
    }
    await toggleHabit(habitId);
  };

  const dailyQuests = getDailyQuests();
  const completedCount = getCompletedCount();
  const totalCount = getTotalCount();
  const xp = profile?.xp ?? 0;
  const level = calculateLevel(xp);
  const greeting = getGreeting();

  return (
    <SafeAreaView
      className="flex-1"
      style={{ backgroundColor: COLORS.background }}
    >
      <XPToast
        xp={toastXP}
        visible={showToast}
        onDismiss={() => setShowToast(false)}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={COLORS.purpleAccent}
          />
        }
      >
        {/* Header */}
        <View className="px-6 pt-4 pb-2">
          <View className="flex-row justify-between items-center">
            <View>
              <Text className="text-text-secondary font-inter text-sm">
                {greeting}
              </Text>
              <Text className="text-text-primary font-poppins-bold text-2xl">
                {profile?.display_name ?? "Hero"}
              </Text>
            </View>
            <StreakBadge streak={profile?.streak ?? 0} />
          </View>
        </View>

        {/* XP & HP Bars */}
        <XPBar xp={xp} level={level} />
        <HPBar hp={profile?.hp ?? 100} maxHp={profile?.max_hp ?? 100} />

        {/* Life Score */}
        <View className="items-center py-4">
          <LifeScoreRing score={profile?.life_score ?? 0} size={130} />
        </View>

        {/* Daily Quests Header */}
        <View className="flex-row justify-between items-center px-6 mb-3">
          <View>
            <Text className="text-text-primary font-poppins-bold text-xl">
              Daily Quests
            </Text>
            <Text className="text-text-secondary font-inter text-sm">
              {completedCount}/{totalCount} completed
            </Text>
          </View>
          <Pressable
            onPress={() => setShowAddModal(true)}
            className="rounded-full w-10 h-10 items-center justify-center"
            style={{ backgroundColor: COLORS.purpleAccent }}
          >
            <Text className="text-text-primary font-bold text-xl">+</Text>
          </Pressable>
        </View>

        {/* Quest List */}
        <View className="px-6 pb-8">
          {dailyQuests.length === 0 ? (
            <View
              className="items-center py-12 rounded-2xl"
              style={{ backgroundColor: COLORS.surface }}
            >
              <Text className="text-4xl mb-3">{"\uD83C\uDFAF"}</Text>
              <Text className="text-text-primary font-poppins-semibold text-lg">
                No quests yet
              </Text>
              <Text className="text-text-secondary font-inter text-sm mt-1">
                Tap + to add your first daily quest
              </Text>
            </View>
          ) : (
            dailyQuests.map((quest) => (
              <QuestCard
                key={quest.habit.id}
                quest={quest}
                onToggle={handleToggle}
              />
            ))
          )}
        </View>
      </ScrollView>

      <AddHabitModal
        visible={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={addHabit}
      />
    </SafeAreaView>
  );
}
