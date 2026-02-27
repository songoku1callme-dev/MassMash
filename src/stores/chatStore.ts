import { create } from "zustand";
import { supabase } from "../lib/supabase";
import type { ChatMessage } from "../types";
import { useAuthStore } from "./authStore";
import { useHabitStore } from "./habitStore";
import { v4 as uuidv4 } from "uuid";
import { FREE_AI_INTERACTIONS_PER_DAY } from "../constants/config";
import { getTodayDate } from "../utils/date";

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  todayInteractionCount: number;
  fetchMessages: () => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  canSendMessage: () => boolean;
  countTodayInteractions: () => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  todayInteractionCount: 0,

  fetchMessages: async () => {
    const user = useAuthStore.getState().user;
    if (!user) return;

    const { data, error } = await supabase
      .from("chat_messages")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: true })
      .limit(100);

    if (error) {
      console.error("Error fetching messages:", error);
      return;
    }

    set({ messages: data ?? [] });
  },

  countTodayInteractions: async () => {
    const user = useAuthStore.getState().user;
    if (!user) return;

    const today = getTodayDate();
    const { count, error } = await supabase
      .from("chat_messages")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id)
      .eq("role", "user")
      .gte("created_at", `${today}T00:00:00`);

    if (error) {
      console.error("Error counting interactions:", error);
      return;
    }

    set({ todayInteractionCount: count ?? 0 });
  },

  canSendMessage: () => {
    const profile = useAuthStore.getState().profile;
    if (profile?.is_pro) return true;
    return get().todayInteractionCount < FREE_AI_INTERACTIONS_PER_DAY;
  },

  sendMessage: async (content) => {
    const user = useAuthStore.getState().user;
    const profile = useAuthStore.getState().profile;
    if (!user || !profile) return;

    if (!get().canSendMessage()) return;

    set({ isLoading: true });

    // Save user message locally and to DB
    const userMessage: ChatMessage = {
      id: uuidv4(),
      user_id: user.id,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      todayInteractionCount: state.todayInteractionCount + 1,
    }));

    await supabase.from("chat_messages").insert(userMessage);

    try {
      // Build context for the AI
      const habits = useHabitStore.getState().habits;
      const todayLogs = useHabitStore.getState().todayLogs;
      const completedCount = todayLogs.filter((l) => l.completed).length;
      const missedHabits = habits.filter(
        (h) => !todayLogs.find((l) => l.habit_id === h.id && l.completed)
      );

      // Call Supabase Edge Function for AI response
      const { data, error } = await supabase.functions.invoke("ai-coach", {
        body: {
          message: content,
          context: {
            display_name: profile.display_name,
            life_score: profile.life_score,
            level: profile.level,
            xp: profile.xp,
            streak: profile.streak,
            goals: profile.goals,
            habits_completed_today: completedCount,
            total_habits: habits.length,
            missed_habits: missedHabits.map((h) => h.title),
          },
        },
      });

      if (error) throw error;

      const aiResponse: ChatMessage = {
        id: uuidv4(),
        user_id: user.id,
        role: "assistant",
        content: data?.reply ?? "Sorry, I couldn't process that. Try again!",
        created_at: new Date().toISOString(),
      };

      set((state) => ({
        messages: [...state.messages, aiResponse],
      }));

      await supabase.from("chat_messages").insert(aiResponse);
    } catch (error) {
      console.error("Error calling AI:", error);

      const errorMessage: ChatMessage = {
        id: uuidv4(),
        user_id: user.id,
        role: "assistant",
        content:
          "I'm having trouble connecting right now. Please try again in a moment.",
        created_at: new Date().toISOString(),
      };

      set((state) => ({
        messages: [...state.messages, errorMessage],
      }));
    } finally {
      set({ isLoading: false });
    }
  },
}));
