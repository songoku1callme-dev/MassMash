import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "../stores/chatStore";
import { useAuthStore } from "../stores/authStore";
import ReactMarkdown from "react-markdown";
import { ErrorState } from "../components/PageStates";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { ocrApi, quizApi, guestApi, visionApi, audioApi, getAccessToken } from "../services/api";
import { useIsOwner } from "../utils/ownerEmails";
import type { KIPersonality } from "../services/api";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import FachSelector, { ALLE_FAECHER } from "../components/FachSelector";
import LumnosOrb from "../components/LumnosOrb";
import { userMessageVariants, aiMessageVariants } from "../lib/animations";

/* ============================================================
 LUMNOS 1.0 — BLOCK B: Chat UI (Nuclear Reset)
 Perplexity-Standard UI mit Glassmorphism, KI-Avatar,
 Action-Buttons, Welcome Message, Tutor-Modus Toggle
 ============================================================ */

/**
 * Client-side safety net: Strip <thinking> and other internal tags
 * from AI responses before rendering. Backend should already clean these,
 * but this ensures they NEVER reach the user even if backend fails.
 */
function cleanThinkingTags(text: string): string {
 if (!text) return "";

 let cleaned = text;

 // 1a. UNWRAP <output> tags — keep content, remove tags only.
 // LLMs (e.g. DeepSeek) wrap the actual answer in <output>...</output>
 // after their <thinking> block. We must preserve this content.
 // Also: <output> is a valid HTML5 element, so ReactMarkdown would
 // swallow it if left in place.
 cleaned = cleaned.replace(/<output>([\s\S]*?)<\/output>/gi, '$1');
 cleaned = cleaned.replace(/<\/?output>/gi, '');

 // 1b. Remove ALL known internal tag blocks (complete pairs)
 const internalTags = [
 'thinking', 'reasoning', 'internal', 'scratchpad',
 'reflection', 'critique', 'analysis', 'planning',
 ];
 for (const tag of internalTags) {
 // Remove complete <tag>...</tag> blocks
 cleaned = cleaned.replace(new RegExp(`<${tag}>[\\s\\S]*?</${tag}>`, 'gi'), '');
 // Remove unclosed <tag>...
 cleaned = cleaned.replace(new RegExp(`<${tag}>[\\s\\S]*`, 'gi'), '');
 // Remove orphaned closing/opening tags
 cleaned = cleaned.replace(new RegExp(`</?${tag}>`, 'gi'), '');
 }
 // Clean excessive newlines
 cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
 return cleaned.trim();
}

/**
 * Extract thinking text from raw AI response BEFORE cleaning.
 * Returns [thinkingContent, cleanedResponse].
 */
interface Karteikarte {
 frage: string;
 antwort: string;
}

interface WebQuelle {
 url: string;
 titel: string;
}

interface Msg {
 role: "user" | "assistant";
 content: string;
 subject?: string;
 karteikarten?: Karteikarte[];
 zusammenfassung?: string;
 quellen?: string[];
 web_quellen?: WebQuelle[];
 internet_genutzt?: boolean;
 is_verified?: boolean;
 confidence?: number;
 thinking?: string;
 wiki_genutzt?: boolean;
}

export default function ChatPage() {
 const {
 sessions,
 currentSessionId,
 messages,
 isSending,
 isStreaming,
 streamStatus,
 currentSubject,
 language,
 sendMessageStream,
 setSubject,
 setLanguage,
 addMessage,
 isThinking,
 thinkingText,
 loadSessions,
 loadSession,
 newChat,
 deleteSession,
 } = useChatStore();
 const { user, isGuest, guestSessionId, exitGuestMode } = useAuthStore();
 const isOwner = useIsOwner();
 const [input, setInput] = useState("");
 const [guestRemaining, setGuestRemaining] = useState(3);
 const [showPaywall, setShowPaywall] = useState(false);
 const [guestSending, setGuestSending] = useState(false);
 const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
 const [expandedKarten, setExpandedKarten] = useState<Record<number, boolean>>({});
 const [flippedCards, setFlippedCards] = useState<Record<string, boolean>>({});
 const [feedbackGiven, setFeedbackGiven] = useState<Record<number, string>>({});
 const [expandedThinking, setExpandedThinking] = useState<Record<number, boolean>>({});
 const [isOcrLoading, setIsOcrLoading] = useState(false);
 const [uploadedFile, setUploadedFile] = useState<{ file: File; type: 'image' | 'audio'; preview?: string } | null>(null);
 const [isAnalysing, setIsAnalysing] = useState(false);
 const [personalities, setPersonalities] = useState<KIPersonality[]>([]);
 const [selectedPersonality, setSelectedPersonality] = useState<number>(user?.ki_personality_id || 1);
 const [showPersonalities, setShowPersonalities] = useState(false);
 const [tutorModus, setTutorModus] = useState(() => localStorage.getItem("lumnos_tutor_modus") === "true");
 const [eli5, setEli5] = useState(false);
 const [modus, setModus] = useState<"normal" | "deep" | "fast">("normal");
 const [showSidebar, setShowSidebar] = useState(false);
 const [starRating, setStarRating] = useState<Record<number, number>>({});
 const [starHover, setStarHover] = useState<Record<number, number>>({});
 const messagesEndRef = useRef<HTMLDivElement>(null);
 const messagesContainerRef = useRef<HTMLDivElement>(null);
 const inputRef = useRef<HTMLTextAreaElement>(null);
 const fileInputRef = useRef<HTMLInputElement>(null);
 const mediaInputRef = useRef<HTMLInputElement>(null);

 const { isListening, transcript, error: speechError, isSupported: speechSupported, startListening, stopListening, clearError } = useSpeechRecognition(language);

 // Auto-scroll ans Ende wenn neue Nachricht kommt
 useEffect(() => {
 if (messagesEndRef.current) {
 messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
 }
 }, [messages, isSending, isStreaming]);

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

 // Load chat sessions (sidebar)
 useEffect(() => {
  loadSessions();
 }, [loadSessions]);

 const handleStarRating = useCallback((msgIdx: number, stars: number) => {
  setStarRating((prev) => ({ ...prev, [msgIdx]: stars }));

  const sessionId = currentSessionId || 0;
  if (!sessionId) return;

  const rating = stars >= 4 ? "positive" : stars <= 2 ? "negative" : "positive";
  const reason = `stars_${stars}`;
  const token = getAccessToken() || localStorage.getItem("lumnos_token") || "";

  fetch(
   `/api/chat/feedback?message_index=${msgIdx}&session_id=${sessionId}&rating=${rating}&reason=${encodeURIComponent(reason)}&fach=${encodeURIComponent(currentSubject || "")}`,
   {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
   },
  ).catch(() => {});
 }, [currentSessionId, currentSubject]);

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

 const handleSend = async () => {
 if (!input.trim() || isSending || guestSending) return;
 const msg = input.trim();
 setInput("");

 // Guest mode: use guest API endpoint
 if (isGuest && guestSessionId) {
 if (guestRemaining <= 0) {
 setShowPaywall(true);
 return;
 }
 setGuestSending(true);
 addMessage({ role: "user", content: msg, timestamp: new Date().toISOString() });
 try {
 const res = await guestApi.chat({
 message: msg,
 guest_session_id: guestSessionId,
 subject: currentSubject !== "general" ? currentSubject : undefined,
 });
 addMessage({
 role: "assistant",
 content: res.response,
 subject: res.subject,
 timestamp: new Date().toISOString(),
 web_quellen: res.web_quellen || [],
 internet_genutzt: res.internet_genutzt || false,
 is_verified: res.is_verified || false,
 confidence: res.confidence || 0,
 });
 setGuestRemaining(res.guest_remaining);
 } catch (err: unknown) {
 const errorMsg = err instanceof Error ? err.message : "";
 if (errorMsg.includes("Gast-Limit") || errorMsg.includes("403")) {
 setGuestRemaining(0);
 setShowPaywall(true);
 } else {
 addMessage({ role: "assistant", content: `Fehler: ${errorMsg || "Bitte versuche es erneut."}` });
 }
 } finally {
 setGuestSending(false);
 }
 return;
 }

 // Authenticated mode: use streaming
 sendMessageStream(msg, selectedPersonality, tutorModus, eli5, modus);
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
 sendMessageStream(prompts[action], selectedPersonality, tutorModus, eli5, modus);
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

 // ===== MEDIA UPLOAD (Bild + Audio) =====
 const handleMediaSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
 const file = e.target.files?.[0];
 if (!file) return;
 e.target.value = "";

 const isImage = file.type.startsWith("image/");
 const isAudio = file.type.startsWith("audio/") || file.type === "video/webm";

 if (!isImage && !isAudio) {
 addMessage({ role: "assistant", content: "Nur Bild- und Audio-Dateien werden unterstützt (JPG, PNG, GIF, WebP, MP3, WAV, M4A, OGG, FLAC, WebM)." });
 return;
 }

 // Size validation
 const maxMB = isImage ? 10 : 25;
 if (file.size > maxMB * 1024 * 1024) {
 addMessage({ role: "assistant", content: `Datei zu groß (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum: ${maxMB}MB` });
 return;
 }

 if (isImage) {
 const reader = new FileReader();
 reader.onload = (ev) => {
 setUploadedFile({ file, type: "image", preview: ev.target?.result as string });
 };
 reader.readAsDataURL(file);
 } else {
 setUploadedFile({ file, type: "audio" });
 }
 }, [addMessage]);

 const handleMediaUploadSend = useCallback(async () => {
 if (!uploadedFile) return;
 const { file, type } = uploadedFile;
 const fach = currentSubject !== "general" ? currentSubject : undefined;
 const frage = input.trim() || undefined;

 setIsAnalysing(true);
 setUploadedFile(null);

 if (type === "image") {
 // Show user message with image
 addMessage({ role: "user", content: `📷 **Bild hochgeladen:** ${file.name}${frage ? `\n\n${frage}` : ""}` });
 try {
 const result = await visionApi.analyse(file, frage, fach);
 addMessage({ role: "assistant", content: result.analyse, subject: fach });
 } catch (err) {
 const errorMsg = err instanceof Error ? err.message : "Bild-Analyse fehlgeschlagen";
 addMessage({ role: "assistant", content: `Fehler: ${errorMsg}` });
 }
 } else {
 // Audio
 addMessage({ role: "user", content: `🎙️ **Audio hochgeladen:** ${file.name}${frage ? `\n\n${frage}` : ""}` });
 try {
 const result = await audioApi.transkribieren(file, frage, fach);
 const content = `**Transkription** (${result.dauer_sekunden}s):\n> ${result.transkription}\n\n---\n\n${result.ki_antwort}`;
 addMessage({ role: "assistant", content, subject: fach });
 } catch (err) {
 const errorMsg = err instanceof Error ? err.message : "Audio-Analyse fehlgeschlagen";
 addMessage({ role: "assistant", content: `Fehler: ${errorMsg}` });
 }
 }

 setInput("");
 setIsAnalysing(false);
 }, [uploadedFile, input, currentSubject, addMessage]);

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

 const tierLabel = isGuest ? "Gast" : isOwner ? "Owner" : user?.subscription_tier === "max" ? "Max" : user?.subscription_tier === "pro" ? "Pro" : "Free";

 // Textarea auto-resize handler
 const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
 setInput(e.target.value);
 const ta = e.target;
 ta.style.height = "auto";
 ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
 };

 return (
 <div style={{
 display: "flex",
 flexDirection: "column",
 height: "100%",
 overflow: "hidden",
 position: "relative",
 background: "var(--lumnos-bg)",
 }}>

 {/* ===== CHAT-VERLAUF SIDEBAR (Overlay) ===== */}
 <AnimatePresence>
 {showSidebar && (
  <>
   <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="absolute inset-0"
    style={{ background: "rgba(0,0,0,0.55)", zIndex: 40 }}
    onClick={() => setShowSidebar(false)}
   />
   <motion.div
    initial={{ x: -320, opacity: 0 }}
    animate={{ x: 0, opacity: 1 }}
    exit={{ x: -320, opacity: 0 }}
    transition={{ type: "spring", stiffness: 300, damping: 30 }}
    className="absolute left-0 top-0 h-full flex flex-col"
    style={{
     width: 320,
     background: "rgba(var(--overlay-rgb),0.98)",
     backdropFilter: "blur(20px)",
     borderRight: "1px solid rgba(99,102,241,0.2)",
     zIndex: 50,
    }}
   >
    <div className="p-3 border-b flex items-center justify-between" style={{ borderColor: "rgba(99,102,241,0.2)" }}>
     <h3 className="text-sm font-bold text-white">Chat-Verlauf</h3>
     <div className="flex items-center gap-2">
      <button
       onClick={() => {
        newChat();
        setShowSidebar(false);
       }}
       className="px-2 py-1 rounded-lg text-[11px] font-bold text-indigo-400 hover:bg-indigo-900/30 transition-all"
      >
       + Neuer Chat
      </button>
      <button onClick={() => setShowSidebar(false)} className="text-slate-400 hover:text-white text-lg px-1">&#10005;</button>
     </div>
    </div>

    <div className="flex-1 overflow-y-auto p-2 space-y-1">
     {sessions.length === 0 ? (
      <p className="text-xs text-slate-500 text-center py-8">Keine gespeicherten Chats</p>
     ) : (
      sessions.map((s) => (
       <div
        key={s.id}
        className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-all text-sm ${
         currentSessionId === s.id
          ? "bg-indigo-900/30 text-indigo-300"
          : "text-slate-300 hover:bg-slate-800/50"
        }`}
        onClick={() => {
         loadSession(s.id);
         setShowSidebar(false);
        }}
       >
        <span className="flex-1 truncate text-xs">{s.title || `Chat #${s.id}`}</span>
        <button
         onClick={(e) => {
          e.stopPropagation();
          deleteSession(s.id);
         }}
         className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 text-xs transition-opacity"
         title="Chat löschen"
        >
         &#128465;
        </button>
       </div>
      ))
     )}
    </div>
   </motion.div>
  </>
 )}
 </AnimatePresence>

 {/* ===== GAST-BANNER ===== */}
 {isGuest && (
 <div
 className="px-4 py-2.5 text-center text-sm font-medium border-b border-emerald-500/20"
 style={{ background: "linear-gradient(90deg, rgba(16,185,129,0.15), rgba(99,102,241,0.15))" }}
 >
 <span className="text-emerald-400">
 {guestRemaining > 0
 ? `\uD83D\uDC4B Gast-Modus: Du kannst noch ${guestRemaining} ${guestRemaining === 1 ? "Frage" : "Fragen"} stellen.`
 : "\u26A0\uFE0F Gast-Limit erreicht! Melde dich an, um weiter zu lernen."}
 </span>
 <button
 onClick={() => { exitGuestMode(); window.location.reload(); }}
 className="ml-3 text-indigo-400 hover:text-indigo-300 underline text-xs font-bold"
 >
 Jetzt anmelden
 </button>
 </div>
 )}

 {/* ===== PAYWALL MODAL ===== */}
 {showPaywall && (
 <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)" }}>
 <div
 className="relative max-w-md w-full mx-4 p-8 rounded-2xl text-center"
 style={{
 background: "rgba(var(--modal-rgb),0.95)",
 border: "1px solid rgba(99,102,241,0.4)",
 boxShadow: "0 0 40px rgba(99,102,241,0.3)",
 }}
 >
 <div className="text-4xl mb-4">{"\u2728"}</div>
 <h2 className="text-xl font-bold text-white mb-2">Dein Probe-Limit ist erreicht!</h2>
 <p className="text-slate-400 mb-6">
 Melde dich kostenlos an, um LUMNOS weiter zu nutzen und deinen Fortschritt zu speichern.
 </p>
 <button
 onClick={() => { exitGuestMode(); window.location.reload(); }}
 className="w-full py-3 rounded-xl text-white font-bold text-base transition-all"
 style={{
 background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
 boxShadow: "0 0 25px rgba(99,102,241,0.5)",
 }}
 >
 Jetzt kostenlos anmelden
 </button>
 <button
 onClick={() => setShowPaywall(false)}
 className="mt-3 text-sm text-slate-500 hover:text-slate-400"
 >
 Sp\u00e4ter
 </button>
 </div>
 </div>
 )}

 {/* ===== HEADER (fixiert, scrollt nicht mit) ===== */}
 <div
 style={{
 flexShrink: 0,
 borderBottom: "1px solid rgba(99,102,241,0.2)",
 background: "rgba(var(--overlay-rgb),0.95)",
 backdropFilter: "blur(20px)",
 zIndex: 10,
 padding: "12px 16px",
 }}
 >
 <div className="flex flex-wrap items-center gap-2">
 {/* Sidebar Toggle */}
 <button
  onClick={() => setShowSidebar(!showSidebar)}
  className="flex items-center justify-center w-8 h-8 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-all"
  title="Chat-Verlauf"
 >
  <span style={{ fontSize: "16px" }}>&#9776;</span>
 </button>
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
 style={tutorModus ? { background: "rgba(16,185,129,0.15)", boxShadow: "0 0 12px rgba(16,185,129,0.3)" } : { background: "rgba(var(--surface-rgb),0.5)" }}
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
 style={eli5 ? { background: "rgba(236,72,153,0.15)", boxShadow: "0 0 12px rgba(236,72,153,0.3)" } : { background: "rgba(var(--surface-rgb),0.5)" }}
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
 style={{ background: "rgba(var(--surface-rgb),0.95)", backdropFilter: "blur(20px)" }}
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
 style={{ background: "rgba(var(--surface-rgb),0.5)" }}
 >
 {language === "de" ? "DE" : "EN"}
 </button>
 </div>
 </div>
 </div>

 {/* ===== MESSAGES (einziger scrollbarer Bereich!) ===== */}
 <div
 ref={messagesContainerRef}
 className="scrollable"
 style={{
 flex: 1,
 overflowY: "auto",
 overflowX: "hidden",
 padding: "24px 20px",
 display: "flex",
 flexDirection: "column",
 gap: "16px",
 scrollbarWidth: "thin",
 scrollbarColor: "#6366f1 transparent",
 }}
 >
 {messages.length === 0 ? (
 /* === WELCOME MESSAGE === */
 <div className="flex flex-col items-center justify-center h-full text-center py-20">
 {/* KI Orb */}
 <LumnosOrb fach={currentSubject} size="lg" />
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
 background: "rgba(var(--surface-rgb),0.5)",
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
 {/* Chain-of-Thought Thinking Indicator */}
 {isThinking && (
 <div className="flex justify-start">
 <div
 className="inline-flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-xs font-medium"
 style={{
 background: "rgba(139,92,246,0.12)",
 border: "1px solid rgba(139,92,246,0.3)",
 color: "#c4b5fd",
 }}
 >
 <span className="inline-block w-4 h-4 animate-spin" style={{ borderRadius: "50%", border: "2px solid rgba(139,92,246,0.3)", borderTopColor: "#8b5cf6" }} />
 Lumnos überlegt...
 </div>
 </div>
 )}

 {/* SSE Status Chips (Quality Engine v2 Block 1) */}
 {isStreaming && streamStatus && !isThinking && (
 <div className="flex justify-start">
 <div
 className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium animate-pulse"
 style={{
 background: streamStatus.includes("Durchsuche") ? "rgba(59,130,246,0.15)" :
 streamStatus.includes("Prüfe") || streamStatus.includes("Verifiziere") ? "rgba(245,158,11,0.15)" :
 streamStatus.includes("Schreibe") || streamStatus.includes("Generiere") ? "rgba(16,185,129,0.15)" :
 streamStatus.includes("Korrigiere") ? "rgba(239,68,68,0.15)" :
 "rgba(99,102,241,0.15)",
 border: streamStatus.includes("Durchsuche") ? "1px solid rgba(59,130,246,0.3)" :
 streamStatus.includes("Prüfe") || streamStatus.includes("Verifiziere") ? "1px solid rgba(245,158,11,0.3)" :
 streamStatus.includes("Schreibe") || streamStatus.includes("Generiere") ? "1px solid rgba(16,185,129,0.3)" :
 streamStatus.includes("Korrigiere") ? "1px solid rgba(239,68,68,0.3)" :
 "1px solid rgba(99,102,241,0.3)",
 color: streamStatus.includes("Durchsuche") ? "#60a5fa" :
 streamStatus.includes("Prüfe") || streamStatus.includes("Verifiziere") ? "#fbbf24" :
 streamStatus.includes("Schreibe") || streamStatus.includes("Generiere") ? "#34d399" :
 streamStatus.includes("Korrigiere") ? "#f87171" :
 "#818cf8",
 }}
 >
 <span className="inline-block w-2 h-2 rounded-full animate-ping" style={{
 background: streamStatus.includes("Durchsuche") ? "#3b82f6" :
 streamStatus.includes("Prüfe") || streamStatus.includes("Verifiziere") ? "#f59e0b" :
 streamStatus.includes("Schreibe") || streamStatus.includes("Generiere") ? "#10b981" :
 streamStatus.includes("Korrigiere") ? "#ef4444" :
 "#6366f1",
 }} />
 {streamStatus}
 </div>
 </div>
 )}
 {messages.map((msg: Msg, idx: number) => (
 <motion.div
 key={idx}
 variants={msg.role === "user" ? userMessageVariants : aiMessageVariants}
 initial="initial"
 animate="animate"
 className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
 >
 {/* KI Avatar */}
 {msg.role === "assistant" && (
 <div className="flex-shrink-0 mt-1">
 <LumnosOrb fach={currentSubject} size="sm" isTyping={isSending && idx === messages.length - 1} />
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
 : { background: "rgba(var(--surface-rgb),0.6)", border: "1px solid rgba(99,102,241,0.15)", backdropFilter: "blur(10px)" }
 }
 >
 {msg.role === "assistant" ? (
 <>
 {/* Chain-of-Thought Collapsible (Pedagogical Brain) */}
 {(thinkingText && idx === messages.length - 1 && isStreaming) || msg.thinking ? (
 <div className="mb-3">
 <button
 onClick={() => setExpandedThinking(prev => ({ ...prev, [idx]: !prev[idx] }))}
 className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all hover:scale-[1.01]"
 style={{
 background: "rgba(139,92,246,0.1)",
 border: "1px solid rgba(139,92,246,0.25)",
 color: "#c4b5fd",
 }}
 >
 <span style={{ fontSize: "14px" }}>&#129504;</span>
 {expandedThinking[idx] ? "Denkprozess ausblenden" : "Denkprozess anzeigen"}
 <span style={{ transform: expandedThinking[idx] ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.2s" }}>
 &#9660;
 </span>
 </button>
 {expandedThinking[idx] && (
 <div
 className="mt-2 p-3 rounded-lg text-[11px] text-purple-200/80 leading-relaxed"
 style={{
 background: "rgba(139,92,246,0.08)",
 border: "1px solid rgba(139,92,246,0.15)",
 maxHeight: "200px",
 overflowY: "auto",
 }}
 >
 <ReactMarkdown
 remarkPlugins={[remarkMath]}
 rehypePlugins={[rehypeKatex]}
 >{(msg.thinking || thinkingText || "")}</ReactMarkdown>
 </div>
 )}
 </div>
 ) : null}

 <div className="prose prose-sm prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-table:my-2 prose-pre:my-2 prose-code:text-cyan-400">
 <ReactMarkdown
 remarkPlugins={[remarkMath]}
 rehypePlugins={[rehypeKatex]}
 >{cleanThinkingTags(msg.content)}</ReactMarkdown>
 </div>
 </>
 ) : (
 <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
 )}

 {/* Auto-Karteikarten (Block 4) */}
 {msg.role === "assistant" && msg.karteikarten && msg.karteikarten.length > 0 && (
 <div className="mt-3 pt-2 border-t border-indigo-500/20">
 {msg.zusammenfassung && (
 <p className="text-[11px] text-cyan-400 mb-2 italic">{msg.zusammenfassung}</p>
 )}
 <button
 onClick={() => setExpandedKarten(prev => ({ ...prev, [idx]: !prev[idx] }))}
 className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-bold text-amber-400 hover:bg-amber-900/20 transition-all mb-2"
 >
 <span>&#128196;</span>
 {expandedKarten[idx] ? "Karteikarten ausblenden" : `${msg.karteikarten.length} Karteikarten anzeigen`}
 </button>
 {expandedKarten[idx] && (
 <div className="grid gap-2">
 {msg.karteikarten.map((k, ki) => {
 const cardKey = `${idx}-${ki}`;
 const isFlipped = flippedCards[cardKey];
 return (
 <button
 key={ki}
 onClick={() => setFlippedCards(prev => ({ ...prev, [cardKey]: !prev[cardKey] }))}
 className="w-full text-left p-3 rounded-xl transition-all hover:scale-[1.01] cursor-pointer"
 style={{
 background: isFlipped
 ? "rgba(16,185,129,0.15)"
 : "rgba(99,102,241,0.1)",
 border: isFlipped
 ? "1px solid rgba(16,185,129,0.3)"
 : "1px solid rgba(99,102,241,0.2)",
 }}
 >
 <p className="text-[10px] font-bold mb-1" style={{ color: isFlipped ? "#10b981" : "#818cf8" }}>
 {isFlipped ? "Antwort" : "Frage"} {ki + 1}/3
 </p>
 <p className="text-xs text-slate-200">
 {isFlipped ? k.antwort : k.frage}
 </p>
 <p className="text-[9px] text-slate-500 mt-1">
 {isFlipped ? "Klicke für Frage" : "Klicke für Antwort"}
 </p>
 </button>
 );
 })}
 </div>
 )}
 </div>
 )}

 {/* ===== QUALITY ENGINE BADGES (Perplexity-Style) ===== */}
 {msg.role === "assistant" && (msg.is_verified || msg.confidence || msg.internet_genutzt) && (
 <div className="mt-3 pt-3 border-t border-slate-700/50">
 <div className="flex flex-wrap items-center gap-2">
 {/* KI-Geprüft Badge */}
 {msg.is_verified && (
 <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
 <span className="text-emerald-400 text-xs">✓</span>
 <span className="text-emerald-400 text-[11px] font-medium">KI-Geprüft</span>
 </div>
 )}

 {/* Präzisions-Score — NUR anzeigen wenn < 80% (Bug-Fix 3) */}
 {typeof msg.confidence === "number" && msg.confidence > 0 && msg.confidence < 80 && (
 <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">
 <span className={`text-[11px] font-medium ${
 msg.confidence >= 60 ? "text-amber-400" : "text-red-400"
 }`}>
 Präzision: {msg.confidence}%
 </span>
 </div>
 )}

 {/* Live Web-Suche Badge */}
 {msg.internet_genutzt && (
 <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">
 <span className="text-amber-400 text-xs">&#127760;</span>
 <span className="text-amber-400 text-[11px] font-medium">Live Web-Suche</span>
 </div>
 )}
 </div>

 {/* Web-Quellen Liste (Perplexity-Style klickbar) */}
 {msg.web_quellen && msg.web_quellen.length > 0 && (
 <div className="mt-3">
 <span className="text-slate-400 text-xs font-medium mb-2 block">Quellen:</span>
 <div className="flex flex-wrap gap-2">
 {msg.web_quellen.map((quelle: WebQuelle, qIdx: number) => (
 <a
 key={qIdx}
 href={quelle.url}
 target="_blank"
 rel="noopener noreferrer"
 className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 transition-colors max-w-[200px]"
 >
 <div className="w-4 h-4 rounded bg-slate-700 flex items-center justify-center text-[9px] text-slate-300 shrink-0">
 {qIdx + 1}
 </div>
 <span className="text-xs text-slate-300 truncate">{quelle.titel || `Quelle ${qIdx + 1}`}</span>
 </a>
 ))}
 </div>
 </div>
 )}

 {/* Fallback: alte string-Quellen anzeigen */}
 {(!msg.web_quellen || msg.web_quellen.length === 0) && msg.quellen && msg.quellen.length > 0 && (
 <div className="mt-3">
 <span className="text-slate-400 text-xs font-medium mb-2 block">Quellen:</span>
 <div className="space-y-0.5">
 {msg.quellen.map((q, qi) => (
 <p key={qi} className="text-[10px] text-indigo-400">
 <ReactMarkdown
 remarkPlugins={[remarkMath]}
 rehypePlugins={[rehypeKatex]}
 components={{
 p: ({ children }) => <span>{children}</span>,
 a: ({ href, children }) => (
 <a href={href} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300 underline">
 {children}
 </a>
 ),
 }}
 >{q}</ReactMarkdown>
 </p>
 ))}
 </div>
 </div>
 )}
 </div>
 )}

 {/* Action Buttons + Feedback (Block 5) */}
 {msg.role === "assistant" && (
 <div className="flex items-center gap-1.5 mt-3 pt-2 border-t border-indigo-500/20 flex-wrap">
 {/* Feedback Buttons */}
 {!feedbackGiven[idx] ? (
 <>
 <button
 onClick={() => {
 setFeedbackGiven(prev => ({ ...prev, [idx]: "positive" }));
 fetch(`/api/chat/feedback?message_index=${idx}&session_id=${useChatStore.getState().currentSessionId || 0}&rating=positive&fach=${msg.subject || ""}`, {
 method: "POST",
 headers: { Authorization: `Bearer ${localStorage.getItem("lumnos_token")}` },
 }).catch(() => {});
 }}
 className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] text-slate-400 hover:text-emerald-400 hover:bg-emerald-900/20 transition-all"
 title="Gute Antwort"
 >
 &#128077;
 </button>
 <button
 onClick={() => {
 setFeedbackGiven(prev => ({ ...prev, [idx]: "negative" }));
 fetch(`/api/chat/feedback?message_index=${idx}&session_id=${useChatStore.getState().currentSessionId || 0}&rating=negative&fach=${msg.subject || ""}`, {
 method: "POST",
 headers: { Authorization: `Bearer ${localStorage.getItem("lumnos_token")}` },
 }).catch(() => {});
 }}
 className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] text-slate-400 hover:text-red-400 hover:bg-red-900/20 transition-all"
 title="Schlechte Antwort"
 >
 &#128078;
 </button>
 </>
 ) : (
 <span className={`text-[10px] px-2 py-0.5 rounded-full ${
 feedbackGiven[idx] === "positive"
 ? "text-emerald-400 bg-emerald-900/20"
 : "text-red-400 bg-red-900/20"
 }`}>
 {feedbackGiven[idx] === "positive" ? "Danke! \u2713" : "Feedback gesendet"}
 </span>
 )}

 {/* Star Rating */}
 {!starRating[idx] ? (
  <div className="flex items-center gap-0.5 ml-1">
   {[1, 2, 3, 4, 5].map((star) => (
    <button
     key={star}
     onClick={() => handleStarRating(idx, star)}
     onMouseEnter={() => setStarHover((prev) => ({ ...prev, [idx]: star }))}
     onMouseLeave={() => setStarHover((prev) => ({ ...prev, [idx]: 0 }))}
     className="text-sm transition-transform hover:scale-125"
     title={`${star} Stern${star > 1 ? "e" : ""}`}
    >
     <span style={{ color: star <= (starHover[idx] || 0) ? "#f59e0b" : "#475569" }}>&#9733;</span>
    </button>
   ))}
  </div>
 ) : (
  <span className="text-[10px] px-2 py-0.5 rounded-full text-amber-400 bg-amber-900/20 ml-1">
   {"\u2B50".repeat(starRating[idx])} Bewertet
  </span>
 )}

 <span className="w-px h-4 bg-slate-700" />

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
 </motion.div>
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
 style={{ background: "rgba(var(--surface-rgb),0.6)", border: "1px solid rgba(99,102,241,0.2)" }}
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

 {/* ===== INPUT AREA (IMMER am Boden, NIEMALS bewegt!) ===== */}
 <div
 style={{
 flexShrink: 0,
 padding: "16px 20px 20px",
 borderTop: "1px solid var(--border-color)",
 background: "rgba(var(--overlay-rgb),0.98)",
 backdropFilter: "blur(20px)",
 }}
 >
 {/* Speech error / listening indicator */}
 {(speechError || isListening) && (
 <div className={`mb-2 px-3 py-1.5 rounded-lg text-center text-xs flex items-center justify-center gap-2 ${
 speechError ? "text-red-400" : "text-cyan-400"
 }`} style={{ background: speechError ? "rgba(239,68,68,0.1)" : "rgba(6,182,212,0.1)" }}>
 {speechError ? (
 <>
 {speechError}
 <button onClick={clearError} className="ml-2 text-red-400 hover:text-red-300 font-bold">&#10005;</button>
 </>
 ) : (
 <>
 <span className="inline-block w-2 h-2 bg-red-500 rounded-full animate-pulse" />
 {language === "de" ? "Spracherkennung aktiv... Sprich jetzt!" : "Listening... Speak now!"}
 </>
 )}
 </div>
 )}

 {/* OCR / Vision / Audio loading indicator */}
 {(isOcrLoading || isAnalysing) && (
 <div className="mb-2 px-3 py-1.5 rounded-lg text-center text-xs text-amber-400 flex items-center justify-center gap-2"
 style={{ background: "rgba(245,158,11,0.1)" }}>
 <span className="animate-spin inline-block w-3 h-3 border-2 border-amber-400 border-t-transparent rounded-full" />
 {isAnalysing
 ? (uploadedFile?.type === "audio" ? "Audio wird transkribiert..." : "Bild wird analysiert...")
 : (language === "de" ? "Bild wird analysiert..." : "Analyzing image...")}
 </div>
 )}

 {/* Uploaded file preview */}
 {uploadedFile && (
 <div className="mb-2 mx-auto max-w-4xl">
 <div className="flex items-center gap-3 px-3 py-2 rounded-xl" style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.3)" }}>
 {uploadedFile.type === "image" && uploadedFile.preview ? (
 <img src={uploadedFile.preview} alt="Vorschau" className="w-12 h-12 rounded-lg object-cover" />
 ) : (
 <div className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl" style={{ background: "rgba(99,102,241,0.2)" }}>
 {uploadedFile.type === "audio" ? "\uD83C\uDFB5" : "\uD83D\uDDBC"}
 </div>
 )}
 <div className="flex-1 min-w-0">
 <div className="text-sm text-white font-medium truncate">{uploadedFile.file.name}</div>
 <div className="text-xs text-slate-400">
 {uploadedFile.type === "image" ? "Bild" : "Audio"} &middot; {(uploadedFile.file.size / 1024 / 1024).toFixed(1)}MB
 </div>
 </div>
 <button
 onClick={() => setUploadedFile(null)}
 className="text-slate-400 hover:text-red-400 transition-colors text-lg font-bold"
 >
 &#10005;
 </button>
 </div>
 </div>
 )}

 {/* Rate limit warning for Free users */}
 {user?.subscription_tier === "free" && messages.length >= 8 && (
 <div className="mb-2 p-3 rounded-xl text-center text-xs"
 style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.3)" }}>
 <span className="text-indigo-300">
 {language === "de"
 ? "Free-Limit fast erreicht (10 Nachrichten/Tag). "
 : "Free limit almost reached (10 messages/day). "}
 </span>
 <button onClick={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "pricing" }))}
 className="font-bold text-indigo-400 hover:text-indigo-300 underline">
 {language === "de" ? "Upgrade auf Pro" : "Upgrade to Pro"}
 </button>
 </div>
 )}

 {/* ===== KI-MODUS BUTTONS (Fast / Standard / Deep) ===== */}
 <div className="flex gap-2 mb-2 max-w-4xl mx-auto">
 {([
 { id: "fast" as const, label: "\u26a1 Fast", desc: "Blitzschnell \u2014 1-2 Sek", color: "text-yellow-400 border-yellow-400/30", activeColor: "bg-yellow-400/20 border-yellow-400", activeBg: "rgba(250,204,21,0.15)" },
 { id: "normal" as const, label: "\u2728 Standard", desc: "Ausgewogen \u2014 3-5 Sek", color: "text-blue-400 border-blue-400/30", activeColor: "bg-blue-400/20 border-blue-400", activeBg: "rgba(96,165,250,0.15)" },
 { id: "deep" as const, label: "\ud83e\udde0 Deep", desc: "Pr\u00e4zision \u2014 15-30 Sek", color: "text-purple-400 border-purple-400/30", activeColor: "bg-purple-400/20 border-purple-400", activeBg: "rgba(192,132,252,0.15)" },
 ]).map(m => (
 <button
 key={m.id}
 onClick={() => setModus(m.id)}
 className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
 modus === m.id
 ? m.activeColor
 : m.color + " opacity-60 hover:opacity-100"
 }`}
 style={modus === m.id ? { background: m.activeBg, boxShadow: `0 0 10px ${m.activeBg}` } : { background: "rgba(var(--surface-rgb),0.3)" }}
 title={m.desc}
 >
 {m.label}
 </button>
 ))}
 </div>

 {/* Deep Thinking loading animation */}
 {isSending && modus === "deep" && (
 <div className="flex items-center gap-2 mb-2 max-w-4xl mx-auto text-purple-400 text-sm animate-pulse">
 <span>\ud83e\udde0</span>
 <span>Deep Thinking l&auml;uft... (bis 30s)</span>
 <div className="flex gap-1">
 {[0, 1, 2].map(i => (
 <span
 key={i}
 className="inline-block w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce"
 style={{ animationDelay: `${i * 0.15}s` }}
 />
 ))}
 </div>
 </div>
 )}

 <div className="flex items-end gap-2 max-w-4xl mx-auto">
 {/* Media Upload Button (Bild + Audio) */}
 <input ref={mediaInputRef} type="file" accept="image/*,audio/*,video/webm" className="hidden" onChange={handleMediaSelect} />
 <button
 onClick={() => mediaInputRef.current?.click()}
 disabled={isSending || isOcrLoading || isAnalysing}
 className="flex items-center justify-center w-10 h-10 rounded-xl text-slate-400 hover:text-white transition-all border border-slate-600 hover:border-indigo-500/50 disabled:opacity-50 flex-shrink-0"
 style={{ background: "rgba(var(--surface-rgb),0.5)" }}
 title="Bild oder Audio hochladen"
 >
 {isAnalysing ? (
 <span className="animate-spin inline-block w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full" />
 ) : (
 <span style={{ fontSize: "16px" }}>&#128206;</span>
 )}
 </button>

 {/* Camera/OCR Button */}
 <input ref={fileInputRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleOcrUpload} />
 <button
 onClick={() => fileInputRef.current?.click()}
 disabled={isSending || isOcrLoading || isAnalysing}
 className="flex items-center justify-center w-10 h-10 rounded-xl text-slate-400 hover:text-white transition-all border border-slate-600 hover:border-indigo-500/50 disabled:opacity-50 flex-shrink-0"
 style={{ background: "rgba(var(--surface-rgb),0.5)" }}
 title={language === "de" ? "Kamera / Mathe-Foto" : "Camera / math photo"}
 >
 {isOcrLoading ? (
 <span className="animate-spin inline-block w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full" />
 ) : (
 <span style={{ fontSize: "16px" }}>&#128247;</span>
 )}
 </button>

 {/* Mic Button */}
 <button
 onClick={speechSupported ? handleMicToggle : () => {}}
 disabled={isSending || !speechSupported}
 className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all border disabled:opacity-50 flex-shrink-0 ${
 isListening
 ? "text-red-400 border-red-500/50 animate-pulse"
 : !speechSupported
 ? "text-slate-600 border-slate-700 cursor-not-allowed"
 : "text-slate-400 hover:text-white border-slate-600 hover:border-indigo-500/50"
 }`}
 style={isListening
 ? { background: "rgba(239,68,68,0.15)", boxShadow: "0 0 12px rgba(239,68,68,0.3)" }
 : { background: "rgba(var(--surface-rgb),0.5)" }
 }
 title={
 !speechSupported
 ? "Spracheingabe nur in Chrome/Edge verfügbar"
 : isListening
 ? (language === "de" ? "Aufnahme stoppen" : "Stop recording")
 : (language === "de" ? "Spracheingabe starten" : "Start voice input")
 }
 >
 <span style={{ fontSize: "16px" }}>{isListening ? "\u23F9" : "\uD83C\uDF99"}</span>
 </button>

 {/* Textarea (auto-resize, max 5 Zeilen) */}
 <textarea
 ref={inputRef}
 value={input}
 onChange={handleTextareaChange}
 onKeyDown={(e) => {
 if (e.key === "Enter" && !e.shiftKey) {
 e.preventDefault();
 if (uploadedFile) {
 handleMediaUploadSend();
 } else {
 handleSend();
 }
 }
 }}
 placeholder={
 uploadedFile
 ? (uploadedFile.type === "image" ? "Optionale Frage zum Bild..." : "Optionale Frage zur Audio...")
 : isListening
 ? (language === "de" ? "Sprich jetzt..." : "Speak now...")
 : tutorModus
 ? (language === "de" ? "Stelle eine Frage \u2014 die KI antwortet nur mit Gegenfragen..." : "Ask \u2014 AI responds with guiding questions only...")
 : (language === "de" ? "Stelle eine Frage..." : "Ask a question...")
 }
 disabled={isSending}
 rows={1}
 className="flex-1 px-4 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 outline-none disabled:opacity-50 resize-none"
 style={{
 background: "rgba(var(--surface-rgb),0.5)",
 border: "1px solid rgba(99,102,241,0.2)",
 maxHeight: "120px",
 minHeight: "40px",
 lineHeight: "1.5",
 }}
 />

 {/* Send Button */}
 <button
 onClick={uploadedFile ? handleMediaUploadSend : handleSend}
 disabled={(!input.trim() && !uploadedFile) || isSending || isAnalysing}
 className="flex items-center justify-center w-10 h-10 rounded-xl text-white transition-all hover:scale-105 disabled:opacity-30 disabled:hover:scale-100 flex-shrink-0"
 style={{
 background: (input.trim() || uploadedFile) && !isSending && !isAnalysing
 ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
 : "rgba(var(--surface-rgb),0.5)",
 boxShadow: (input.trim() || uploadedFile) && !isSending && !isAnalysing ? "0 0 15px rgba(99,102,241,0.4)" : "none",
 }}
 >
 {isSending || isAnalysing ? (
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
