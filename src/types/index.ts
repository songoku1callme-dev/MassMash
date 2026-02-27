export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  xp: number;
  hp: number;
  max_hp: number;
  level: number;
  life_score: number;
  streak: number;
  goals: string[];
  sleep_schedule: SleepSchedule | null;
  is_pro: boolean;
  created_at: string;
  updated_at: string;
}

export interface SleepSchedule {
  bedtime: string;
  wake_time: string;
}

export interface Habit {
  id: string;
  user_id: string;
  title: string;
  description: string;
  icon: string;
  xp_reward: number;
  frequency: HabitFrequency;
  is_active: boolean;
  created_at: string;
}

export type HabitFrequency = "daily" | "weekly" | "custom";

export interface DailyLog {
  id: string;
  user_id: string;
  habit_id: string;
  completed: boolean;
  completed_at: string | null;
  date: string;
  xp_earned: number;
}

export interface ChatMessage {
  id: string;
  user_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface OnboardingData {
  goals: string[];
  sleep_schedule: SleepSchedule;
  display_name: string;
}

export interface DailyQuest {
  habit: Habit;
  log: DailyLog | null;
  completed: boolean;
}

export interface WeeklyStats {
  date: string;
  completed: number;
  total: number;
  percentage: number;
}

export type SubscriptionTier = "free" | "pro";

export interface SubscriptionInfo {
  tier: SubscriptionTier;
  expiry_date: string | null;
  is_trial: boolean;
}
