import { create } from "zustand";
import { supabase } from "../lib/supabase";
import type { Habit, DailyLog, DailyQuest } from "../types";
import { getTodayDate } from "../utils/date";
import { DEFAULT_XP_REWARD, HP_MISS_PENALTY } from "../constants/theme";
import { useAuthStore } from "./authStore";
import { v4 as uuidv4 } from "uuid";

interface HabitState {
  habits: Habit[];
  todayLogs: DailyLog[];
  isLoading: boolean;
  fetchHabits: () => Promise<void>;
  fetchTodayLogs: () => Promise<void>;
  addHabit: (title: string, description: string, icon: string) => Promise<void>;
  toggleHabit: (habitId: string) => Promise<void>;
  deleteHabit: (habitId: string) => Promise<void>;
  getDailyQuests: () => DailyQuest[];
  getCompletedCount: () => number;
  getTotalCount: () => number;
}

export const useHabitStore = create<HabitState>((set, get) => ({
  habits: [],
  todayLogs: [],
  isLoading: false,

  fetchHabits: async () => {
    const user = useAuthStore.getState().user;
    if (!user) return;

    set({ isLoading: true });
    const { data, error } = await supabase
      .from("habits")
      .select("*")
      .eq("user_id", user.id)
      .eq("is_active", true)
      .order("created_at", { ascending: true });

    if (error) {
      console.error("Error fetching habits:", error);
      set({ isLoading: false });
      return;
    }

    set({ habits: data ?? [], isLoading: false });
  },

  fetchTodayLogs: async () => {
    const user = useAuthStore.getState().user;
    if (!user) return;

    const today = getTodayDate();
    const { data, error } = await supabase
      .from("daily_logs")
      .select("*")
      .eq("user_id", user.id)
      .eq("date", today);

    if (error) {
      console.error("Error fetching today logs:", error);
      return;
    }

    set({ todayLogs: data ?? [] });
  },

  addHabit: async (title, description, icon) => {
    const user = useAuthStore.getState().user;
    if (!user) return;

    const newHabit: Omit<Habit, "created_at"> & { created_at?: string } = {
      id: uuidv4(),
      user_id: user.id,
      title,
      description,
      icon,
      xp_reward: DEFAULT_XP_REWARD,
      frequency: "daily",
      is_active: true,
    };

    const { error } = await supabase.from("habits").insert(newHabit);
    if (error) {
      console.error("Error adding habit:", error);
      return;
    }

    await get().fetchHabits();
  },

  toggleHabit: async (habitId) => {
    const user = useAuthStore.getState().user;
    if (!user) return;

    const today = getTodayDate();
    const { todayLogs, habits } = get();
    const existingLog = todayLogs.find((log) => log.habit_id === habitId);
    const habit = habits.find((h) => h.id === habitId);
    if (!habit) return;

    if (existingLog?.completed) {
      // Uncomplete the habit
      const { error } = await supabase
        .from("daily_logs")
        .update({
          completed: false,
          completed_at: null,
          xp_earned: 0,
        })
        .eq("id", existingLog.id);

      if (error) {
        console.error("Error uncompleting habit:", error);
        return;
      }

      // Subtract XP from profile
      const profile = useAuthStore.getState().profile;
      if (profile) {
        await useAuthStore
          .getState()
          .updateProfile({ xp: Math.max(0, profile.xp - habit.xp_reward) });
      }
    } else {
      // Complete the habit
      const logData = {
        id: existingLog?.id ?? uuidv4(),
        user_id: user.id,
        habit_id: habitId,
        completed: true,
        completed_at: new Date().toISOString(),
        date: today,
        xp_earned: habit.xp_reward,
      };

      const { error } = await supabase
        .from("daily_logs")
        .upsert(logData);

      if (error) {
        console.error("Error completing habit:", error);
        return;
      }

      // Add XP to profile
      const profile = useAuthStore.getState().profile;
      if (profile) {
        await useAuthStore
          .getState()
          .updateProfile({ xp: profile.xp + habit.xp_reward });
      }
    }

    await get().fetchTodayLogs();
  },

  deleteHabit: async (habitId) => {
    const { error } = await supabase
      .from("habits")
      .update({ is_active: false })
      .eq("id", habitId);

    if (error) {
      console.error("Error deleting habit:", error);
      return;
    }

    await get().fetchHabits();
  },

  getDailyQuests: () => {
    const { habits, todayLogs } = get();
    return habits.map((habit) => {
      const log = todayLogs.find((l) => l.habit_id === habit.id) ?? null;
      return {
        habit,
        log,
        completed: log?.completed ?? false,
      };
    });
  },

  getCompletedCount: () => {
    const { todayLogs } = get();
    return todayLogs.filter((log) => log.completed).length;
  },

  getTotalCount: () => {
    const { habits } = get();
    return habits.length;
  },
}));
