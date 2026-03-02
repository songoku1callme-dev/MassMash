import { create } from "zustand";
import { authApi, type User, setTokens, clearTokens, getAccessToken, isTokenExpiringSoon, refreshAccessToken } from "../services/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
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
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("lumnos_token"),
  isLoading: true,
  isAuthenticated: !!localStorage.getItem("lumnos_token"),

  login: async (username, password) => {
    const response = await authApi.login({ username, password });
    setTokens(response.access_token, response.refresh_token);
    set({ user: response.user, token: response.access_token, isAuthenticated: true });
  },

  register: async (data) => {
    const response = await authApi.register(data);
    setTokens(response.access_token, response.refresh_token);
    set({ user: response.user, token: response.access_token, isAuthenticated: true });
  },

  logout: () => {
    clearTokens();
    set({ user: null, token: null, isAuthenticated: false });
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

  updateUser: async (data) => {
    const user = await authApi.update(data);
    set({ user });
  },
}));
