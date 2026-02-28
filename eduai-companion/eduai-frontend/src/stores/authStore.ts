import { create } from "zustand";
import { authApi, type User } from "../services/api";

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
  token: localStorage.getItem("eduai_token"),
  isLoading: true,
  isAuthenticated: !!localStorage.getItem("eduai_token"),

  login: async (username, password) => {
    const response = await authApi.login({ username, password });
    localStorage.setItem("eduai_token", response.access_token);
    set({ user: response.user, token: response.access_token, isAuthenticated: true });
  },

  register: async (data) => {
    const response = await authApi.register(data);
    localStorage.setItem("eduai_token", response.access_token);
    set({ user: response.user, token: response.access_token, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("eduai_token");
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadUser: async () => {
    const token = localStorage.getItem("eduai_token");
    if (!token) {
      set({ isLoading: false, isAuthenticated: false });
      return;
    }
    try {
      const user = await authApi.me();
      set({ user, isLoading: false, isAuthenticated: true });
    } catch {
      localStorage.removeItem("eduai_token");
      set({ user: null, token: null, isLoading: false, isAuthenticated: false });
    }
  },

  updateUser: async (data) => {
    const user = await authApi.update(data);
    set({ user });
  },
}));
