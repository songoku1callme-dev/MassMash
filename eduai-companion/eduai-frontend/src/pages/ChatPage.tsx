import { useState, useRef, useEffect } from "react";
import { useChatStore } from "../stores/chatStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import ReactMarkdown from "react-markdown";
import {
  Send, Loader2, Copy, Check, ChevronDown, ChevronUp,
  Calculator, Languages, BookOpenCheck, Clock, FlaskConical, Sparkles
} from "lucide-react";

const SUBJECTS = [
  { id: "general", name: "Alle Faecher", icon: <Sparkles className="w-4 h-4" /> },
  { id: "math", name: "Mathe", icon: <Calculator className="w-4 h-4" /> },
  { id: "english", name: "Englisch", icon: <Languages className="w-4 h-4" /> },
  { id: "german", name: "Deutsch", icon: <BookOpenCheck className="w-4 h-4" /> },
  { id: "history", name: "Geschichte", icon: <Clock className="w-4 h-4" /> },
  { id: "science", name: "Naturwiss.", icon: <FlaskConical className="w-4 h-4" /> },
];

export default function ChatPage() {
  const {
    messages, isSending, currentSubject, language,
    sendMessage, setSubject, setLanguage, setDetailLevel
  } = useChatStore();
  const [input, setInput] = useState("");
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = () => {
    if (!input.trim() || isSending) return;
    sendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleDetailRequest = (level: string) => {
    if (messages.length === 0) return;
    const lastUserMsg = [...messages].reverse().find(m => m.role === "user");
    if (lastUserMsg) {
      setDetailLevel(level);
      sendMessage(lastUserMsg.content);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3 lg:p-4">
        <div className="flex flex-wrap items-center gap-2">
          {/* Subject Selector */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1">
            {SUBJECTS.map((s) => (
              <button
                key={s.id}
                onClick={() => setSubject(s.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                  currentSubject === s.id
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
                }`}
              >
                {s.icon}
                {s.name}
              </button>
            ))}
          </div>

          {/* Language Toggle */}
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setLanguage(language === "de" ? "en" : "de")}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-gray-100 dark:bg-gray-800 text-xs font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              {language === "de" ? "DE" : "EN"}
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4 lg:p-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-xl mb-6">
              <Sparkles className="w-10 h-10" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              {language === "de" ? "Hallo! Wie kann ich dir helfen?" : "Hello! How can I help you?"}
            </h2>
            <p className="text-gray-500 dark:text-gray-400 max-w-md mb-8">
              {language === "de"
                ? "Stelle mir eine Frage zu Mathe, Englisch, Deutsch, Geschichte oder Naturwissenschaften!"
                : "Ask me about Math, English, German, History, or Science!"}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
              {[
                { text: "Erklaere den Satz des Pythagoras", subject: "math" },
                { text: "What are conditional sentences?", subject: "english" },
                { text: "Erklaere die Weimarer Republik", subject: "history" },
                { text: "Was ist Photosynthese?", subject: "science" },
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(suggestion.text); inputRef.current?.focus(); }}
                  className="p-3 rounded-xl border border-gray-200 dark:border-gray-700 text-left text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-blue-300 dark:hover:border-blue-600 transition-all"
                >
                  {suggestion.text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-4xl mx-auto">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] lg:max-w-[75%] rounded-2xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white rounded-br-md"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md"
                  }`}
                >
                  {msg.role === "assistant" ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-table:my-2 prose-pre:my-2 prose-code:text-blue-600 dark:prose-code:text-blue-400">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  )}

                  {/* Message Actions */}
                  {msg.role === "assistant" && (
                    <div className="flex items-center gap-1 mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                      <button
                        onClick={() => copyToClipboard(msg.content, idx)}
                        className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                        title="Kopieren"
                      >
                        {copiedIdx === idx ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                      {msg.subject && (
                        <Badge variant="secondary" className="ml-auto text-xs">
                          {SUBJECTS.find(s => s.id === msg.subject)?.name || msg.subject}
                        </Badge>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isSending && (
              <div className="flex justify-start">
                <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-bl-md px-4 py-3">
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </ScrollArea>

      {/* Detail Level Buttons */}
      {messages.length > 0 && messages[messages.length - 1]?.role === "assistant" && (
        <div className="px-4 pb-2 flex justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDetailRequest("simpler")}
            disabled={isSending}
            className="text-xs gap-1"
          >
            <ChevronDown className="w-3 h-3" />
            {language === "de" ? "Einfacher erklaeren" : "Explain simpler"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDetailRequest("detailed")}
            disabled={isSending}
            className="text-xs gap-1"
          >
            <ChevronUp className="w-3 h-3" />
            {language === "de" ? "Mehr Details" : "More details"}
          </Button>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3 lg:p-4">
        <div className="flex items-center gap-2 max-w-4xl mx-auto">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={language === "de" ? "Stelle eine Frage..." : "Ask a question..."}
            disabled={isSending}
            className="flex-1"
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            size="icon"
            className="shrink-0"
          >
            {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
