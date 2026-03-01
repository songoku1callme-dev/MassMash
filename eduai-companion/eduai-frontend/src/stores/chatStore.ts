import { create } from "zustand";
import { chatApi, type ChatMessage, type ChatSession } from "../services/api";

interface ChatState {
  sessions: ChatSession[];
  currentSessionId: number | null;
  messages: ChatMessage[];
  isLoading: boolean;
  isSending: boolean;
  currentSubject: string;
  language: string;
  detailLevel: string;

  loadSessions: () => Promise<void>;
  loadSession: (id: number) => Promise<void>;
  sendMessage: (message: string, personalityId?: number) => Promise<void>;
  newChat: () => void;
  setSubject: (subject: string) => void;
  setLanguage: (lang: string) => void;
  setDetailLevel: (level: string) => void;
  deleteSession: (id: number) => Promise<void>;
  addMessage: (msg: ChatMessage) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  isLoading: false,
  isSending: false,
  currentSubject: "general",
  language: "de",
  detailLevel: "normal",

  loadSessions: async () => {
    try {
      const sessions = await chatApi.sessions();
      set({ sessions });
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  },

  loadSession: async (id) => {
    set({ isLoading: true });
    try {
      const session = await chatApi.session(id);
      set({
        currentSessionId: id,
        messages: session.messages,
        currentSubject: session.subject,
        language: session.language,
        isLoading: false,
      });
    } catch (err) {
      console.error("Failed to load session:", err);
      set({ isLoading: false });
    }
  },

  sendMessage: async (message, personalityId) => {
    const { currentSessionId, messages, currentSubject, language, detailLevel } = get();

    const userMsg: ChatMessage = {
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    };
    set({ messages: [...messages, userMsg], isSending: true });

    try {
      const response = await chatApi.send({
        message,
        session_id: currentSessionId,
        subject: currentSubject !== "general" ? currentSubject : undefined,
        language,
        detail_level: detailLevel,
        personality_id: personalityId,
      });

      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: response.response,
        subject: response.subject,
        timestamp: new Date().toISOString(),
      };

      set((state) => ({
        messages: [...state.messages, assistantMsg],
        currentSessionId: response.session_id,
        currentSubject: response.subject,
        isSending: false,
      }));

      // Reload sessions list
      get().loadSessions();
    } catch (err) {
      console.error("Failed to send message:", err);
      set({ isSending: false });
    }
  },

  newChat: () => {
    set({ currentSessionId: null, messages: [], currentSubject: "general" });
  },

  setSubject: (subject) => set({ currentSubject: subject }),
  setLanguage: (language) => set({ language }),
  setDetailLevel: (detailLevel) => set({ detailLevel }),

  addMessage: (msg) => {
    set((state) => ({ messages: [...state.messages, msg] }));
  },

  deleteSession: async (id) => {
    try {
      await chatApi.deleteSession(id);
      const { currentSessionId } = get();
      if (currentSessionId === id) {
        set({ currentSessionId: null, messages: [] });
      }
      get().loadSessions();
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  },
}));
