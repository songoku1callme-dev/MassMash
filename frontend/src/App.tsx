import { useState, useEffect, useRef, useCallback } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatMessageItem } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { ModeSelector } from "@/components/ModeSelector";
import { SettingsDialog } from "@/components/SettingsDialog";
import { LoadingDots } from "@/components/LoadingDots";
import { sendChat } from "@/services/api";
import type { ChatMessage, ChatMode, Conversation } from "@/types";
import { Bot } from "lucide-react";

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function createConversation(mode: ChatMode = "normal"): Conversation {
  return {
    id: generateId(),
    title: "Neuer Chat",
    messages: [],
    mode,
    createdAt: Date.now(),
  };
}

// Load conversations from localStorage
function loadConversations(): Conversation[] {
  try {
    const data = localStorage.getItem("massmash_conversations");
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

function saveConversations(convs: Conversation[]) {
  localStorage.setItem("massmash_conversations", JSON.stringify(convs));
}

function App() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [mode, setMode] = useState<ChatMode>("normal");
  const [loading, setLoading] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeConv = conversations.find((c) => c.id === activeId) || null;

  // Save conversations whenever they change
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConv?.messages.length, loading]);

  const handleNewChat = useCallback(() => {
    const conv = createConversation(mode);
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
  }, [mode]);

  const handleSelectConv = useCallback((id: string) => {
    setActiveId(id);
    const conv = conversations.find((c) => c.id === id);
    if (conv) setMode(conv.mode);
  }, [conversations]);

  const handleDeleteConv = useCallback((id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  }, [activeId]);

  const handleModeChange = useCallback((newMode: ChatMode) => {
    setMode(newMode);
    if (activeId) {
      setConversations((prev) =>
        prev.map((c) => (c.id === activeId ? { ...c, mode: newMode } : c))
      );
    }
  }, [activeId]);

  const handleSend = useCallback(
    async (message: string, fileContext?: string) => {
      let convId = activeId;

      // Auto-create conversation if none active
      if (!convId) {
        const conv = createConversation(mode);
        setConversations((prev) => [conv, ...prev]);
        setActiveId(conv.id);
        convId = conv.id;
      }

      const userMessage: ChatMessage = { role: "user", content: message };

      // Add user message to conversation
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== convId) return c;
          const updated = {
            ...c,
            messages: [...c.messages, userMessage],
            fileContext: fileContext || c.fileContext,
          };
          // Set title from first message
          if (c.messages.length === 0) {
            updated.title = message.slice(0, 40) + (message.length > 40 ? "..." : "");
          }
          return updated;
        })
      );

      setLoading(true);

      try {
        // Get current messages for the conversation
        const currentConv = conversations.find((c) => c.id === convId);
        const allMessages = [...(currentConv?.messages || []), userMessage];

        const response = await sendChat({
          messages: allMessages,
          mode: mode,
          file_context: fileContext || currentConv?.fileContext,
        });

        // Append assistant response
        setConversations((prev) =>
          prev.map((c) =>
            c.id === convId
              ? { ...c, messages: [...c.messages, response.message] }
              : c
          )
        );
      } catch (err) {
        const errorMsg: ChatMessage = {
          role: "assistant",
          content: `Fehler: ${err instanceof Error ? err.message : "Verbindung zum Server fehlgeschlagen. Ist das Backend gestartet?"}`,
        };
        setConversations((prev) =>
          prev.map((c) =>
            c.id === convId ? { ...c, messages: [...c.messages, errorMsg] } : c
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [activeId, conversations, mode]
  );

  return (
    <div className="flex h-screen bg-zinc-950">
      {/* Sidebar */}
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelectConv}
        onNew={handleNewChat}
        onDelete={handleDeleteConv}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800 bg-zinc-900/50">
          <ModeSelector mode={mode} onChange={handleModeChange} />
          <div className="text-xs text-zinc-600">
            {activeConv
              ? `${activeConv.messages.length} Nachrichten`
              : "Neuen Chat starten"}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {!activeConv || activeConv.messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-zinc-600">
              <Bot size={48} className="mb-4 text-zinc-700" />
              <h2 className="text-xl font-semibold text-zinc-400 mb-2">
                MassMash AI
              </h2>
              <p className="text-sm text-center max-w-md">
                Starte einen neuen Chat oder wähle eine Unterhaltung aus der
                Seitenleiste. Du kannst auch Dateien hochladen und verschiedene
                Modi wählen.
              </p>
            </div>
          ) : (
            <>
              {activeConv.messages.map((msg, i) => (
                <ChatMessageItem key={i} message={msg} />
              ))}
              {loading && <LoadingDots />}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={loading} />
      </div>

      {/* Settings Dialog */}
      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

export default App;
