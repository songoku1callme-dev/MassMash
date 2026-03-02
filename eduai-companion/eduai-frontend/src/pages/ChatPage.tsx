import { useState, useRef, useEffect, useCallback } from "react";
import { useChatStore } from "../stores/chatStore";
import { useAuthStore } from "../stores/authStore";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { ocrApi, quizApi } from "../services/api";
import type { KIPersonality } from "../services/api";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import FachSelector, { ALLE_FAECHER } from "../components/FachSelector";

/* ============================================================
   LUMNOS 1.0 — BLOCK B: Chat UI (Nuclear Reset)
   Perplexity-Standard UI mit Glassmorphism, KI-Avatar,
   Action-Buttons, Welcome Message, Tutor-Modus Toggle
   ============================================================ */

interface Msg {
  role: "user" | "assistant";
  content: string;
  subject?: string;
}

export default function ChatPage() {
  const {
    messages, isSending, currentSubject, language,
    sendMessage, setSubject, setLanguage, addMessage
  } = useChatStore();
  const { user } = useAuthStore();
  const [input, setInput] = useState("");
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [isOcrLoading, setIsOcrLoading] = useState(false);
  const [personalities, setPersonalities] = useState<KIPersonality[]>([]);
  const [selectedPersonality, setSelectedPersonality] = useState<number>(user?.ki_personality_id || 1);
  const [showPersonalities, setShowPersonalities] = useState(false);
  const [tutorModus, setTutorModus] = useState(() => localStorage.getItem("lumnos_tutor_modus") === "true");
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
    localStorage.setItem("lumnos_tutor_modus", String(next));
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

  const handleActionButton = (action: string) => {
    if (messages.length === 0 || isSending) return;
    const prompts: Record<string, string> = {
      einfacher: "Erkl\u00e4re das nochmal einfacher, als w\u00e4re ich 10 Jahre alt.",
      details: "Gib mir mehr Details und Hintergrundinformationen dazu.",
      aufgabe: "Gib mir eine \u00dcbungsaufgabe zu diesem Thema mit L\u00f6sung.",
    };
    if (prompts[action]) {
      sendMessage(prompts[action], selectedPersonality, tutorModus, eli5);
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

  const tierLabel = user?.subscription_tier === "max" ? "Max" : user?.subscription_tier === "pro" ? "Pro" : "Free";

  return (
    <div className="flex flex-col h-full" style={{ background: "#0a0f1e" }}>
      {/* ===== HEADER ===== */}
      <div
        className="border-b border-indigo-500/20 p-3 lg:p-4"
        style={{ background: "rgba(10,15,30,0.85)", backdropFilter: "blur(20px)" }}
      >
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex-1 min-w-0">
            <FachSelector selected={currentSubject} onSelect={setSubject} showAll />
          </div>

          {/* Tutor-Modus Toggle */}
          <button
            onClick={handleTutorToggle}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all border ${
              tutorModus
                ? "text-emerald-300 border-emerald-500/50"
                : "text-slate-400 border-slate-600 hover:border-slate-500"
            }`}
            style={tutorModus ? { background: "rgba(16,185,129,0.15)", boxShadow: "0 0 12px rgba(16,185,129,0.3)" } : { background: "rgba(30,41,59,0.5)" }}
            title="Tutor-Modus: KI stellt nur Gegenfragen (Sokratische Methode)"
          >
            Tutor {tutorModus ? "AN" : "AUS"}
          </button>

          {/* ELI5 Toggle */}
          <button
            onClick={() => setEli5(!eli5)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all border ${
              eli5
                ? "text-pink-300 border-pink-500/50"
                : "text-slate-400 border-slate-600 hover:border-slate-500"
            }`}
            style={eli5 ? { background: "rgba(236,72,153,0.15)", boxShadow: "0 0 12px rgba(236,72,153,0.3)" } : { background: "rgba(30,41,59,0.5)" }}
          >
            ELI5 {eli5 ? "AN" : "AUS"}
          </button>

          {/* Upgrade Button for Free users */}
          {user?.subscription_tier === "free" && (
            <button
              onClick={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "pricing" }))}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-bold text-white transition-all hover:scale-105"
              style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.4)" }}
            >
              Pro &middot; 4,99&euro;
            </button>
          )}

          {/* Tier Badge */}
          {user?.subscription_tier !== "free" && (
            <span
              className="px-3 py-1 rounded-full text-xs font-bold"
              style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", color: "#fff" }}
            >
              {tierLabel}
            </span>
          )}

          {/* KI Personality + Language */}
          <div className="ml-auto flex items-center gap-2 relative">
            <button
              onClick={() => setShowPersonalities(!showPersonalities)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-purple-300 hover:bg-purple-900/50 transition-colors border border-purple-700"
              style={{ background: "rgba(88,28,135,0.3)" }}
              title="KI-Pers\u00f6nlichkeit w\u00e4hlen"
            >
              <span>{currentPersonality?.emoji || "\ud83d\ude0a"}</span>
              <span className="hidden sm:inline">{currentPersonality?.name || "Freundlich"}</span>
            </button>

            {showPersonalities && (
              <div
                className="absolute top-full right-12 mt-1 w-72 rounded-xl shadow-xl z-50 max-h-80 overflow-y-auto border border-indigo-500/20"
                style={{ background: "rgba(30,41,59,0.95)", backdropFilter: "blur(20px)" }}
              >
                <div className="p-2 border-b border-indigo-500/10">
                  <p className="text-xs font-semibold text-slate-400 px-2">KI-Pers\u00f6nlichkeit</p>
                </div>
                <div className="p-1">
                  {personalities.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => p.accessible ? handlePersonalityChange(p.id) : undefined}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${
                        selectedPersonality === p.id
                          ? "bg-purple-900/30 text-purple-300"
                          : p.accessible
                            ? "hover:bg-slate-700 text-slate-300"
                            : "opacity-50 cursor-not-allowed text-slate-500"
                      }`}
                      disabled={!p.accessible}
                    >
                      <span className="text-lg">{p.emoji}</span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-xs">{p.name}</p>
                        <p className="text-[10px] text-slate-500 truncate">{p.preview}</p>
                      </div>
                      {!p.accessible && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded border border-slate-600 text-slate-400">{p.tier}</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={() => setLanguage(language === "de" ? "en" : "de")}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-full text-xs font-medium hover:bg-slate-700 transition-colors text-slate-300 border border-slate-600"
              style={{ background: "rgba(30,41,59,0.5)" }}
            >
              {language === "de" ? "DE" : "EN"}
            </button>
          </div>
        </div>
      </div>

      {/* ===== MESSAGES ===== */}
      <div className="flex-1 overflow-y-auto p-4 lg:p-6" style={{ scrollbarWidth: "thin", scrollbarColor: "#6366f1 transparent" }}>
        {messages.length === 0 ? (
          /* === WELCOME MESSAGE === */
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            {/* KI Avatar */}
            <div
              className="w-24 h-24 rounded-2xl flex items-center justify-center text-white shadow-2xl mb-6"
              style={{
                background: "linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4)",
                boxShadow: "0 0 40px rgba(99,102,241,0.5), 0 0 80px rgba(99,102,241,0.2)",
                fontSize: "40px",
              }}
            >
              &#10022;
            </div>
            <h2 className="text-3xl font-bold text-white mb-2">
              {language === "de" ? "Was m\u00f6chtest du wissen?" : "What would you like to know?"}
            </h2>
            <p className="text-slate-400 max-w-md mb-8 text-sm">
              {language === "de"
                ? "Stelle eine konkrete Frage \u2014 ich antworte direkt und pr\u00e4zise."
                : "Ask a specific question \u2014 I answer directly and precisely."}
            </p>
            {/* Example Questions */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
              {[
                { text: "Was ist \u221A122?", fach: "math" },
                { text: "Erkl\u00e4re den Satz des Pythagoras", fach: "math" },
                { text: "Was ist Photosynthese?", fach: "biologie" },
                { text: "Erkl\u00e4re die Weimarer Republik", fach: "geschichte" },
              ].map((q, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(q.text); inputRef.current?.focus(); }}
                  className="p-3 rounded-xl text-left text-sm text-slate-300 transition-all hover:scale-[1.02]"
                  style={{
                    background: "rgba(30,41,59,0.5)",
                    border: "1px solid rgba(99,102,241,0.2)",
                    backdropFilter: "blur(10px)",
                  }}
                >
                  {q.text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* === MESSAGE LIST === */
          <div className="space-y-4 max-w-4xl mx-auto">
            {messages.map((msg: Msg, idx: number) => (
              <div
                key={idx}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {/* KI Avatar */}
                {msg.role === "assistant" && (
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-white flex-shrink-0 mt-1"
                    style={{
                      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                      boxShadow: "0 0 12px rgba(99,102,241,0.4)",
                      fontSize: "14px",
                    }}
                  >
                    &#10022;
                  </div>
                )}

                <div
                  className={`max-w-[85%] lg:max-w-[75%] rounded-2xl px-4 py-3 ${
                    msg.role === "user"
                      ? "text-white rounded-br-md"
                      : "text-slate-100 rounded-bl-md"
                  }`}
                  style={msg.role === "user"
                    ? { background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 0 15px rgba(99,102,241,0.3)" }
                    : { background: "rgba(30,41,59,0.6)", border: "1px solid rgba(99,102,241,0.15)", backdropFilter: "blur(10px)" }
                  }
                >
                  {msg.role === "assistant" ? (
                    <div className="prose prose-sm prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-table:my-2 prose-pre:my-2 prose-code:text-cyan-400">
                      <ReactMarkdown
                        remarkPlugins={[remarkMath]}
                        rehypePlugins={[rehypeKatex]}
                      >{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  )}

                  {/* Action Buttons under KI responses */}
                  {msg.role === "assistant" && (
                    <div className="flex items-center gap-1.5 mt-3 pt-2 border-t border-indigo-500/20 flex-wrap">
                      {/* Copy */}
                      <button
                        onClick={() => copyToClipboard(msg.content, idx)}
                        className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-all"
                        title="Kopieren"
                      >
                        {copiedIdx === idx ? "\u2713 Kopiert" : "Kopieren"}
                      </button>
                      {/* Einfacher */}
                      <button
                        onClick={() => handleActionButton("einfacher")}
                        className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-all"
                        disabled={isSending}
                      >
                        Einfacher
                      </button>
                      {/* Details */}
                      <button
                        onClick={() => handleActionButton("details")}
                        className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-all"
                        disabled={isSending}
                      >
                        Details
                      </button>
                      {/* Aufgabe */}
                      <button
                        onClick={() => handleActionButton("aufgabe")}
                        className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-all"
                        disabled={isSending}
                      >
                        Aufgabe
                      </button>
                      {/* Subject badge */}
                      {msg.subject && (
                        <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full border border-indigo-500/30 text-indigo-300 bg-indigo-500/10">
                          {ALLE_FAECHER.find(s => s.id === msg.subject)?.name || msg.subject}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing indicator with KI avatar */}
            {isSending && (
              <div className="flex gap-3 justify-start">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-white flex-shrink-0"
                  style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", fontSize: "14px" }}
                >
                  &#10022;
                </div>
                <div
                  className="rounded-2xl rounded-bl-md px-4 py-3"
                  style={{ background: "rgba(30,41,59,0.6)", border: "1px solid rgba(99,102,241,0.2)" }}
                >
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: "#6366f1", animationDelay: "0ms" }} />
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: "#8b5cf6", animationDelay: "150ms" }} />
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: "#06b6d4", animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Rate limit warning for Free users */}
      {user?.subscription_tier === "free" && messages.length >= 8 && (
        <div
          className="mx-4 mb-2 p-3 rounded-xl text-center text-xs"
          style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.3)" }}
        >
          <span className="text-indigo-300">
            {language === "de"
              ? "Free-Limit fast erreicht (10 Nachrichten/Tag). "
              : "Free limit almost reached (10 messages/day). "}
          </span>
          <button
            onClick={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "pricing" }))}
            className="font-bold text-indigo-400 hover:text-indigo-300 underline"
          >
            {language === "de" ? "Upgrade auf Pro" : "Upgrade to Pro"}
          </button>
        </div>
      )}

      {/* Speech error / listening indicator */}
      {(speechError || isListening) && (
        <div className={`px-4 py-1.5 text-center text-xs ${
          speechError ? "text-red-400" : "text-cyan-400"
        }`} style={{ background: speechError ? "rgba(239,68,68,0.1)" : "rgba(6,182,212,0.1)" }}>
          {speechError || (language === "de" ? "Spracherkennung aktiv... Sprich jetzt!" : "Listening... Speak now!")}
        </div>
      )}

      {/* OCR loading indicator */}
      {isOcrLoading && (
        <div
          className="px-4 py-1.5 text-center text-xs text-amber-400 flex items-center justify-center gap-2"
          style={{ background: "rgba(245,158,11,0.1)" }}
        >
          <span className="animate-spin inline-block w-3 h-3 border-2 border-amber-400 border-t-transparent rounded-full" />
          {language === "de" ? "Bild wird analysiert..." : "Analyzing image..."}
        </div>
      )}

      {/* ===== INPUT AREA ===== */}
      <div
        className="border-t border-indigo-500/20 p-3 lg:p-4"
        style={{ background: "rgba(10,15,30,0.9)", backdropFilter: "blur(20px)" }}
      >
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
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isSending || isOcrLoading}
            className="flex items-center justify-center w-10 h-10 rounded-xl text-slate-400 hover:text-white transition-all border border-slate-600 hover:border-indigo-500/50 disabled:opacity-50"
            style={{ background: "rgba(30,41,59,0.5)" }}
            title={language === "de" ? "Mathe-Foto hochladen" : "Upload math photo"}
          >
            {isOcrLoading ? (
              <span className="animate-spin inline-block w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full" />
            ) : (
              <span style={{ fontSize: "16px" }}>&#128247;</span>
            )}
          </button>

          {/* Mic Button */}
          {speechSupported && (
            <button
              onClick={handleMicToggle}
              disabled={isSending}
              className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all border disabled:opacity-50 ${
                isListening
                  ? "text-red-400 border-red-500/50"
                  : "text-slate-400 hover:text-white border-slate-600 hover:border-indigo-500/50"
              }`}
              style={isListening
                ? { background: "rgba(239,68,68,0.15)", boxShadow: "0 0 12px rgba(239,68,68,0.3)" }
                : { background: "rgba(30,41,59,0.5)" }
              }
              title={language === "de" ? "Spracheingabe" : "Voice input"}
            >
              <span style={{ fontSize: "16px" }}>{isListening ? "\u23F9" : "\uD83C\uDF99"}</span>
            </button>
          )}

          {/* Text Input */}
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isListening
                ? (language === "de" ? "Sprich jetzt..." : "Speak now...")
                : tutorModus
                ? (language === "de" ? "Stelle eine Frage \u2014 die KI antwortet nur mit Gegenfragen..." : "Ask \u2014 AI responds with guiding questions only...")
                : (language === "de" ? "Stelle eine Frage..." : "Ask a question...")
            }
            disabled={isSending}
            className="flex-1 h-10 px-4 rounded-xl text-sm text-white placeholder-slate-500 outline-none transition-all disabled:opacity-50"
            style={{
              background: "rgba(30,41,59,0.5)",
              border: "1px solid rgba(99,102,241,0.2)",
            }}
          />

          {/* Send Button */}
          <button
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            className="flex items-center justify-center w-10 h-10 rounded-xl text-white transition-all hover:scale-105 disabled:opacity-30 disabled:hover:scale-100"
            style={{
              background: input.trim() && !isSending
                ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
                : "rgba(30,41,59,0.5)",
              boxShadow: input.trim() && !isSending ? "0 0 15px rgba(99,102,241,0.4)" : "none",
            }}
          >
            {isSending ? (
              <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            ) : (
              <span style={{ fontSize: "18px" }}>&#8594;</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
