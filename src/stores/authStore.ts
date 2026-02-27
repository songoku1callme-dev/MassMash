import { create } from "zustand";
import { Session, User } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";
import type { UserProfile, OnboardingData } from "../types";

interface AuthState {
  session: Session | null;
  user: User | null;
  profile: UserProfile | null;
  isLoading: boolean;
  hasCompletedOnboarding: boolean;
  setSession: (session: Session | null) => void;
  setProfile: (profile: UserProfile | null) => void;
  setHasCompletedOnboarding: (value: boolean) => void;
  fetchProfile: () => Promise<void>;
  updateProfile: (data: Partial<UserProfile>) => Promise<void>;
  completeOnboarding: (data: OnboardingData) => Promise<void>;
  signOut: () => Promise<void>;
  deleteAccount: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  session: null,
  user: null,
  profile: null,
  isLoading: true,
  hasCompletedOnboarding: false,

  setSession: (session) => {
    set({
      session,
      user: session?.user ?? null,
      isLoading: false,
    });
  },

  setProfile: (profile) => {
    set({
      profile,
      hasCompletedOnboarding: profile !== null && profile.goals.length > 0,
    });
  },

  setHasCompletedOnboarding: (value) => {
    set({ hasCompletedOnboarding: value });
  },

  fetchProfile: async () => {
    const { user } = get();
    if (!user) return;

    const { data, error } = await supabase
      .from("profiles")
      .select("*")
      .eq("id", user.id)
      .single();

    if (error && error.code !== "PGRST116") {
      console.error("Error fetching profile:", error);
      return;
    }

    if (data) {
      const profile: UserProfile = {
        id: data.id,
        email: data.email ?? user.email ?? "",
        display_name: data.display_name ?? "",
        avatar_url: data.avatar_url,
        xp: data.xp ?? 0,
        hp: data.hp ?? 100,
        max_hp: data.max_hp ?? 100,
        level: data.level ?? 1,
        life_score: data.life_score ?? 0,
        streak: data.streak ?? 0,
        goals: data.goals ?? [],
        sleep_schedule: data.sleep_schedule,
        is_pro: data.is_pro ?? false,
        created_at: data.created_at,
        updated_at: data.updated_at,
      };
      set({
        profile,
        hasCompletedOnboarding: profile.goals.length > 0,
      });
    }
  },

  updateProfile: async (data) => {
    const { user, profile } = get();
    if (!user) return;

    const { error } = await supabase
      .from("profiles")
      .update({ ...data, updated_at: new Date().toISOString() })
      .eq("id", user.id);

    if (error) {
      console.error("Error updating profile:", error);
      return;
    }

    if (profile) {
      set({ profile: { ...profile, ...data } });
    }
  },

  completeOnboarding: async (data) => {
    const { user } = get();
    if (!user) return;

    const profileData = {
      id: user.id,
      email: user.email ?? "",
      display_name: data.display_name,
      goals: data.goals,
      sleep_schedule: data.sleep_schedule,
      xp: 0,
      hp: 100,
      max_hp: 100,
      level: 1,
      life_score: 50,
      streak: 0,
      is_pro: false,
      updated_at: new Date().toISOString(),
    };

    const { error } = await supabase
      .from("profiles")
      .upsert(profileData);

    if (error) {
      console.error("Error saving onboarding:", error);
      return;
    }

    set({
      profile: {
        ...profileData,
        avatar_url: null,
        created_at: new Date().toISOString(),
      },
      hasCompletedOnboarding: true,
    });
  },

  signOut: async () => {
    await supabase.auth.signOut();
    set({
      session: null,
      user: null,
      profile: null,
      hasCompletedOnboarding: false,
    });
  },

  deleteAccount: async () => {
    const { user } = get();
    if (!user) return;

    // Delete user data from all tables
    await supabase.from("chat_messages").delete().eq("user_id", user.id);
    await supabase.from("daily_logs").delete().eq("user_id", user.id);
    await supabase.from("habits").delete().eq("user_id", user.id);
    await supabase.from("profiles").delete().eq("id", user.id);
    await supabase.auth.signOut();

    set({
      session: null,
      user: null,
      profile: null,
      hasCompletedOnboarding: false,
    });
  },
}));
