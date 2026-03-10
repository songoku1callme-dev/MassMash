import { describe, it, expect, beforeEach } from "vitest";
import { useChatStore } from "../chatStore";

describe("chatStore", () => {
  beforeEach(() => {
    // Reset store state between tests
    useChatStore.setState({
      sessions: [],
      currentSessionId: null,
      messages: [],
      isLoading: false,
      isSending: false,
      currentSubject: "general",
      language: "de",
      detailLevel: "normal",
    });
  });

  it("should have correct initial state", () => {
    const state = useChatStore.getState();
    expect(state.messages).toEqual([]);
    expect(state.currentSubject).toBe("general");
    expect(state.language).toBe("de");
    expect(state.isSending).toBe(false);
    expect(state.isLoading).toBe(false);
    expect(state.detailLevel).toBe("normal");
  });

  it("should add a message via addMessage", () => {
    const store = useChatStore.getState();
    store.addMessage({ role: "user", content: "Hallo Welt" });

    const state = useChatStore.getState();
    expect(state.messages).toHaveLength(1);
    expect(state.messages[0].role).toBe("user");
    expect(state.messages[0].content).toBe("Hallo Welt");
  });

  it("should add multiple messages in order", () => {
    const store = useChatStore.getState();
    store.addMessage({ role: "user", content: "Was ist 2+2?" });
    store.addMessage({ role: "assistant", content: "4", subject: "math" });

    const state = useChatStore.getState();
    expect(state.messages).toHaveLength(2);
    expect(state.messages[0].role).toBe("user");
    expect(state.messages[1].role).toBe("assistant");
    expect(state.messages[1].subject).toBe("math");
  });

  it("should set subject", () => {
    useChatStore.getState().setSubject("math");
    expect(useChatStore.getState().currentSubject).toBe("math");
  });

  it("should set language", () => {
    useChatStore.getState().setLanguage("en");
    expect(useChatStore.getState().language).toBe("en");
  });

  it("should set detail level", () => {
    useChatStore.getState().setDetailLevel("detailed");
    expect(useChatStore.getState().detailLevel).toBe("detailed");
  });

  it("should reset on newChat", () => {
    const store = useChatStore.getState();
    store.addMessage({ role: "user", content: "test" });
    store.setSubject("math");

    store.newChat();
    const state = useChatStore.getState();
    expect(state.messages).toEqual([]);
    expect(state.currentSessionId).toBeNull();
    expect(state.currentSubject).toBe("general");
  });
});
