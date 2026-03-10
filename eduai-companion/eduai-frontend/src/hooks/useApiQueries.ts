/**
 * React Query hooks for all major API endpoints.
 * Provides automatic caching (5 min staleTime), error handling, and refetching.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  gamificationApi,
  quizApi,
  shopApi,
  challengesApi,
  pomodoroApi,
  tournamentApi,
  researchApi,
  abiturApi,
  memoryApi,
  authApi,
} from "../services/api";

// ============ GAMIFICATION ============
export function useGamificationProfile() {
  return useQuery({
    queryKey: ["gamification", "profile"],
    queryFn: () => gamificationApi.profile(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useLeaderboard() {
  return useQuery({
    queryKey: ["gamification", "leaderboard"],
    queryFn: () => gamificationApi.leaderboard(),
    staleTime: 2 * 60 * 1000,
  });
}

// ============ QUIZ ============
export function useQuizHistory() {
  return useQuery({
    queryKey: ["quiz", "history"],
    queryFn: () => quizApi.history(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useQuizTopics(subject?: string) {
  return useQuery({
    queryKey: ["quiz", "topics", subject],
    queryFn: () => quizApi.topics(subject),
    staleTime: 10 * 60 * 1000,
  });
}

export function useQuizPersonalities() {
  return useQuery({
    queryKey: ["quiz", "personalities"],
    queryFn: () => quizApi.personalities(),
    staleTime: 30 * 60 * 1000,
  });
}

// ============ SHOP ============
export function useShopItems() {
  return useQuery({
    queryKey: ["shop", "items"],
    queryFn: () => shopApi.items(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useBuyItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId: number) => shopApi.buy(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shop"] });
      queryClient.invalidateQueries({ queryKey: ["gamification", "profile"] });
    },
  });
}

// ============ CHALLENGES ============
export function useChallenges() {
  return useQuery({
    queryKey: ["challenges"],
    queryFn: () => challengesApi.list(),
    staleTime: 5 * 60 * 1000,
  });
}

// ============ POMODORO ============
export function usePomodoroStats() {
  return useQuery({
    queryKey: ["pomodoro", "stats"],
    queryFn: () => pomodoroApi.stats(),
    staleTime: 5 * 60 * 1000,
  });
}

// ============ TOURNAMENTS ============
export function useTournaments() {
  return useQuery({
    queryKey: ["tournaments"],
    queryFn: () => tournamentApi.list(),
    staleTime: 2 * 60 * 1000,
  });
}

// ============ RESEARCH ============
export function useResearchHistory() {
  return useQuery({
    queryKey: ["research", "history"],
    queryFn: () => researchApi.history(),
    staleTime: 5 * 60 * 1000,
  });
}

// ============ ABITUR ============
export function useAbiturHistory() {
  return useQuery({
    queryKey: ["abitur", "history"],
    queryFn: () => abiturApi.history(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useAbiturPlans() {
  return useQuery({
    queryKey: ["abitur", "plans"],
    queryFn: () => abiturApi.getPlans(),
    staleTime: 5 * 60 * 1000,
  });
}

// ============ MEMORY ============
export function useMemoryStats() {
  return useQuery({
    queryKey: ["memory", "stats"],
    queryFn: () => memoryApi.stats(),
    staleTime: 5 * 60 * 1000,
  });
}

// ============ USER ============
export function useCurrentUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => authApi.me(),
    staleTime: 10 * 60 * 1000,
  });
}
