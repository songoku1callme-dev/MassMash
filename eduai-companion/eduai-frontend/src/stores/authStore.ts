import { create } from "zustand";
import { authApi, type User, setTokens, clearTokens, getAccessToken, isTokenExpiringSoon, refreshAccessToken } from "../services/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isGuest: boolean;
  guestSessionId: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    username: string;
    password: string;
    full_name: string;
    school_grade: string;
    school_type: string;
    preferred_language: string;
  }) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  updateUser: (data: { full_name?: string; school_grade?: string; school_type?: string; preferred_language?: string }) => Promise<void>;
  enterGuestMode: () => void;
  exitGuestMode: () => void;
}

function getOrCreateGuestId(): string {
  const existing = localStorage.getItem("lumnos_guest_session_id");
  if (existing) return existing;
  const id = "guest_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
  localStorage.setItem("lumnos_guest_session_id", id);
  return id;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("lumnos_token"),
  isLoading: true,
  isAuthenticated: !!localStorage.getItem("lumnos_token"),
  isGuest: false,
  guestSessionId: localStorage.getItem("lumnos_guest_session_id"),

  login: async (username, password) => {
    const response = await authApi.login({ username, password });
    setTokens(response.access_token, response.refresh_token);
    localStorage.removeItem("lumnos_guest_session_id");
    set({ user: response.user, token: response.access_token, isAuthenticated: true, isGuest: false, guestSessionId: null });
  },

  register: async (data) => {
    const response = await authApi.register(data);
    setTokens(response.access_token, response.refresh_token);
    localStorage.removeItem("lumnos_guest_session_id");
    set({ user: response.user, token: response.access_token, isAuthenticated: true, isGuest: false, guestSessionId: null });
  },

  logout: () => {
    clearTokens();
    localStorage.removeItem("lumnos_guest_session_id");
    set({ user: null, token: null, isAuthenticated: false, isGuest: false, guestSessionId: null });
  },

  loadUser: async () => {
    const token = getAccessToken();
    if (!token) {
      set({ isLoading: false, isAuthenticated: false });
      return;
    }
    try {
      // Proactively refresh if token is close to expiry
      if (isTokenExpiringSoon(120)) {
        try {
          const newToken = await refreshAccessToken();
          set({ token: newToken });
        } catch {
          // Refresh failed — clear and redirect to login
          clearTokens();
          set({ user: null, token: null, isLoading: false, isAuthenticated: false });
          return;
        }
      }
      const user = await authApi.me();
      set({ user, isLoading: false, isAuthenticated: true });
    } catch {
      clearTokens();
      set({ user: null, token: null, isLoading: false, isAuthenticated: false });
    }
  },

  enterGuestMode: () => {
    const guestSessionId = getOrCreateGuestId();
    set({ isGuest: true, guestSessionId, isLoading: false });
  },

  exitGuestMode: () => {
    localStorage.removeItem("lumnos_guest_session_id");
    set({ isGuest: false, guestSessionId: null });
  },

  updateUser: async (data) => {
    const user = await authApi.update(data);
    set({ user });
  },
}));
