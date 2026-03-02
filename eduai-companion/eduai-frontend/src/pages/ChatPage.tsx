import { useState, useRef, useEffect, useCallback } from "react";
import { useChatStore } from "../stores/chatStore";
import { useAuthStore } from "../stores/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { ocrApi, quizApi } from "../services/api";
import type { KIPersonality } from "../services/api";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import {
  Send, Loader2, Copy, Check, ChevronDown, ChevronUp,
  Sparkles, Camera, Mic, MicOff, Lock, Baby
} from "lucide-react";
import FachSelector, { ALLE_FAECHER } from "../components/FachSelector";

export default function ChatPage() {
  const {
    messages, isSending, currentSubject, language,
    sendMessage, setSubject, setLanguage, setDetailLevel, addMessage
  } = useChatStore();
  const { user } = useAuthStore();
  const [input, setInput] = useState("");
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [isOcrLoading, setIsOcrLoading] = useState(false);
  const [personalities, setPersonalities] = useState<KIPersonality[]>([]);
  const [selectedPersonality, setSelectedPersonality] = useState<number>(user?.ki_personality_id || 1);
  const [showPersonalities, setShowPersonalities] = useState(false);
  const [tutorModus, setTutorModus] = useState(() => localStorage.getItem("eduai_tutor_modus") === "true");
  const [eli5, setEli5] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { isListening, transcript, error: speechError, isSupported: speechSupported, startListening, stopListening } = useSpeechRecognition(language);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Load KI personalities
  useEffect(() => {
    quizApi.personalities().then((res) => {
      setPersonalities(res.personalities);
      setSelectedPersonality(res.current_id);
    }).catch(() => {});
  }, []);

  const handlePersonalityChange = useCallback(async (id: number) => {
    setSelectedPersonality(id);
    setShowPersonalities(false);
    try {
      await quizApi.setPersonality(id);
    } catch {
      // silently ignore if not saved
    }
  }, []);

  const currentPersonality = personalities.find(p => p.id === selectedPersonality);

  // Update input with speech transcript as it comes in
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  const handleTutorToggle = useCallback(() => {
    const next = !tutorModus;
    setTutorModus(next);
    localStorage.setItem("eduai_tutor_modus", String(next));
  }, [tutorModus]);

  const handleSend = () => {
    if (!input.trim() || isSending) return;
    sendMessage(input.trim(), selectedPersonality, tutorModus, eli5);
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

  const handleOcrUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    // Reset the file input so the same file can be selected again
    e.target.value = "";

    setIsOcrLoading(true);
    // Add a user message showing the upload
    addMessage({ role: "user", content: `[Bild hochgeladen: ${file.name}]` });

    try {
      const result = await ocrApi.solveImage(file);
      addMessage({ role: "assistant", content: result.formatted_response, subject: "math" });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "OCR fehlgeschlagen";
      addMessage({ role: "assistant", content: `OCR-Fehler: ${errorMsg}. Bitte versuche es mit einem klareren Bild.` });
    } finally {
      setIsOcrLoading(false);
    }
  }, [addMessage]);

  const handleMicToggle = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening((text: string) => {
        setInput(text);
        inputRef.current?.focus();
      });
    }
  }, [isListening, startListening, stopListening]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3 lg:p-4">
        <div className="flex flex-wrap items-center gap-2">
          {/* Subject Selector — Faecher-Expansion 5.0 Block 6 */}
          <div className="flex-1 min-w-0">
            <FachSelector selected={currentSubject} onSelect={setSubject} showAll />
          </div>

          {/* KI Personality + Language Toggle */}
          <div className="ml-auto flex items-center gap-2 relative">
            {/* KI Personality Selector */}
            <button
              onClick={() => setShowPersonalities(!showPersonalities)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-purple-50 dark:bg-purple-900/30 text-xs font-medium text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/50 transition-colors border border-purple-200 dark:border-purple-700"
              title="KI-Persönlichkeit wählen"
            >
              <span>{currentPersonality?.emoji || "😊"}</span>
              <span className="hidden sm:inline">{currentPersonality?.name || "Freundlich"}</span>
            </button>

            {/* Personality Dropdown */}
            {showPersonalities && (
              <div className="absolute top-full right-12 mt-1 w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl z-50 max-h-80 overflow-y-auto">
                <div className="p-2 border-b border-gray-100 dark:border-gray-700">
                  <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 px-2">KI-Persönlichkeit</p>
                </div>
                <div className="p-1">
                  {personalities.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => p.accessible ? handlePersonalityChange(p.id) : undefined}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${
                        selectedPersonality === p.id
                          ? "bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
                          : p.accessible
                            ? "hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                            : "opacity-50 cursor-not-allowed text-gray-400 dark:text-gray-500"
                      }`}
                      disabled={!p.accessible}
                    >
                      <span className="text-lg">{p.emoji}</span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-xs">{p.name}</p>
                        <p className="text-[10px] text-gray-400 dark:text-gray-500 truncate">{p.preview}</p>
                      </div>
                      {!p.accessible && (
                        <Lock className="w-3 h-3 text-gray-400 flex-shrink-0" />
                      )}
                      {!p.accessible && (
                        <Badge variant="outline" className="text-[9px] px-1 py-0 flex-shrink-0">
                          {p.tier}
                        </Badge>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

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
                { text: "Erkläre den Satz des Pythagoras", subject: "math" },
                { text: "What are conditional sentences?", subject: "english" },
                { text: "Erkläre die Weimarer Republik", subject: "history" },
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
                      <ReactMarkdown
                        remarkPlugins={[remarkMath]}
                        rehypePlugins={[rehypeKatex]}
                      >{msg.content}</ReactMarkdown>
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
                          {ALLE_FAECHER.find(s => s.id === msg.subject)?.name || msg.subject}
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
            {language === "de" ? "Einfacher erklären" : "Explain simpler"}
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

      {/* Speech error / listening indicator */}
      {(speechError || isListening) && (
        <div className={`px-4 py-1.5 text-center text-xs ${
          speechError
            ? "bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400"
            : "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
        }`}>
          {speechError || (language === "de" ? "Spracherkennung aktiv... Sprich jetzt!" : "Listening... Speak now!")}
        </div>
      )}

      {/* OCR loading indicator */}
      {isOcrLoading && (
        <div className="px-4 py-1.5 text-center text-xs bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 flex items-center justify-center gap-2">
          <Loader2 className="w-3 h-3 animate-spin" />
          {language === "de" ? "Bild wird analysiert..." : "Analyzing image..."}
        </div>
      )}

      {/* Perfect School 4.1: Tutor-Modus + ELI5 toggles */}
      <div className="px-4 pb-1 flex justify-center gap-2">
        <button
          onClick={handleTutorToggle}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors border ${
            tutorModus
              ? "bg-purple-100 text-purple-700 border-purple-300 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-700"
              : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700"
          }`}
          title="Tutor-Modus: KI stellt nur Gegenfragen (Sokratische Methode)"
        >
          <GraduationCap className="w-3.5 h-3.5" />
          Tutor-Modus {tutorModus ? "AN" : "AUS"}
        </button>
        <button
          onClick={() => setEli5(!eli5)}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors border ${
            eli5
              ? "bg-pink-100 text-pink-700 border-pink-300 dark:bg-pink-900/30 dark:text-pink-300 dark:border-pink-700"
              : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700"
          }`}
          title="ELI5: Erklaere wie ich 5 bin"
        >
          <Baby className="w-3.5 h-3.5" />
          ELI5 {eli5 ? "AN" : "AUS"}
        </button>
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3 lg:p-4">
        <div className="flex items-center gap-2 max-w-4xl mx-auto">
          {/* Camera/OCR Button */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={handleOcrUpload}
          />
          <Button
            variant="outline"
            size="icon"
            className="shrink-0"
            onClick={() => fileInputRef.current?.click()}
            disabled={isSending || isOcrLoading}
            title={language === "de" ? "Mathe-Foto hochladen" : "Upload math photo"}
          >
            {isOcrLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Camera className="w-4 h-4" />}
          </Button>

          {/* Mic Button */}
          {speechSupported && (
            <Button
              variant={isListening ? "default" : "outline"}
              size="icon"
              className={`shrink-0 ${isListening ? "bg-red-500 hover:bg-red-600 text-white" : ""}`}
              onClick={handleMicToggle}
              disabled={isSending}
              title={language === "de" ? "Spracheingabe" : "Voice input"}
            >
              {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </Button>
          )}

          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isListening
                ? (language === "de" ? "Sprich jetzt..." : "Speak now...")
                : tutorModus
                ? (language === "de" ? "Stelle eine Frage — die KI antwortet nur mit Gegenfragen..." : "Ask a question — AI will only ask guiding questions...")
                : (language === "de" ? "Stelle eine Frage..." : "Ask a question...")
            }
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
