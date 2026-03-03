import { create } from "zustand";
import { chatApi, type ChatMessage, type ChatSession } from "../services/api";

interface ChatState {
  sessions: ChatSession[];
  currentSessionId: number | null;
  messages: ChatMessage[];
  isLoading: boolean;
  isSending: boolean;
  isStreaming: boolean;
  streamStatus: string;
  streamingText: string;
  thinkingText: string;
  isThinking: boolean;
  currentSubject: string;
  language: string;
  detailLevel: string;

  loadSessions: () => Promise<void>;
  loadSession: (id: number) => Promise<void>;
  sendMessage: (message: string, personalityId?: number, tutorModus?: boolean, eli5?: boolean) => Promise<void>;
  sendMessageStream: (message: string, personalityId?: number, tutorModus?: boolean, eli5?: boolean) => Promise<void>;
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
  isStreaming: false,
  streamStatus: "",
  streamingText: "",
  thinkingText: "",
  isThinking: false,
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

  sendMessage: async (message, personalityId, tutorModus, eli5) => {
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
        tutor_modus: tutorModus,
        eli5,
      });

      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: response.response,
        subject: response.subject,
        timestamp: new Date().toISOString(),
        karteikarten: response.karteikarten || [],
        zusammenfassung: response.zusammenfassung || "",
        quellen: response.quellen || [],
        web_quellen: response.web_quellen || [],
        internet_genutzt: response.internet_genutzt || false,
        is_verified: response.is_verified || false,
        confidence: response.confidence || 0,
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

  /**
   * SSE Streaming Chat — Quality Engine v2 Block 1
   * Sends message via SSE stream, updates UI token-by-token.
   */
  sendMessageStream: async (message, personalityId, tutorModus, eli5) => {
    const { currentSessionId, messages, currentSubject, language, detailLevel } = get();

    const userMsg: ChatMessage = {
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    };
    set({
      messages: [...messages, userMsg],
      isSending: true,
      isStreaming: true,
      streamStatus: "Verbinde...",
      streamingText: "",
      thinkingText: "",
      isThinking: false,
    });

    try {
      const response = await chatApi.stream({
        message,
        session_id: currentSessionId,
        subject: currentSubject !== "general" ? currentSubject : undefined,
        language,
        detail_level: detailLevel,
        personality_id: personalityId,
        tutor_modus: tutorModus,
        eli5,
      });

      if (!response.ok || !response.body) {
        // Fallback to non-streaming
        set({ isStreaming: false, streamStatus: "", isSending: false });
        set((state) => ({ messages: state.messages.slice(0, -1) }));
        await get().sendMessage(message, personalityId, tutorModus, eli5);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";
      let metaData: Record<string, unknown> = {};
      let sessionId = currentSessionId;
      let subject = currentSubject;
      let currentEventType = "";

      // Add placeholder assistant message
      const placeholderMsg: ChatMessage = {
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
      };
      set((state) => ({ messages: [...state.messages, placeholderMsg] }));

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEventType = line.slice(7).trim();
            continue;
          }

          if (!line.startsWith("data: ")) continue;
          const dataStr = line.slice(6);

          try {
            const data = JSON.parse(dataStr);

            if (currentEventType === "status") {
              set({ streamStatus: data.text || "" });
            } else if (currentEventType === "token") {
              fullText += data.text || "";
              set((state) => {
                const msgs = [...state.messages];
                const last = msgs[msgs.length - 1];
                if (last && last.role === "assistant") {
                  msgs[msgs.length - 1] = { ...last, content: fullText };
                }
                return { messages: msgs, streamingText: fullText };
              });
            } else if (currentEventType === "thinking_start") {
              set({ isThinking: true, streamStatus: "Lumnos überlegt..." });
            } else if (currentEventType === "thinking_end") {
              set({ isThinking: false, thinkingText: data.text || "", streamStatus: "" });
            } else if (currentEventType === "correction") {
              fullText = "";
              set({ streamStatus: "Korrigiere Antwort..." });
              set((state) => {
                const msgs = [...state.messages];
                const last = msgs[msgs.length - 1];
                if (last && last.role === "assistant") {
                  msgs[msgs.length - 1] = { ...last, content: "" };
                }
                return { messages: msgs, streamingText: "" };
              });
            } else if (currentEventType === "meta") {
              metaData = data;
              if (data.final_text) {
                fullText = data.final_text;
              }
            } else if (currentEventType === "done") {
              sessionId = data.session_id ?? sessionId;
              subject = data.subject || subject;
            }

            currentEventType = "";
          } catch {
            // Not valid JSON, skip
          }
        }
      }

      // Finalize the assistant message
      set((state) => {
        const msgs = [...state.messages];
        const last = msgs[msgs.length - 1];
        if (last && last.role === "assistant") {
          msgs[msgs.length - 1] = {
            ...last,
            content: fullText,
            subject: subject,
            web_quellen: (metaData.web_quellen as ChatMessage["web_quellen"]) || [],
            quellen: (metaData.quellen as string[]) || [],
            internet_genutzt: (metaData.internet_genutzt as boolean) || false,
            is_verified: (metaData.is_verified as boolean) || false,
            confidence: (metaData.confidence as number) || 0,
            thinking: (metaData.thinking as string) || state.thinkingText || "",
            wiki_genutzt: (metaData.wiki_genutzt as boolean) || false,
          };
        }
        return {
          messages: msgs,
          currentSessionId: sessionId,
          currentSubject: subject,
          isSending: false,
          isStreaming: false,
          streamStatus: "",
          streamingText: "",
          isThinking: false,
        };
      });

      get().loadSessions();
    } catch (err) {
      console.error("Streaming failed, falling back:", err);
      set({ isStreaming: false, streamStatus: "", isSending: false, isThinking: false });
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
