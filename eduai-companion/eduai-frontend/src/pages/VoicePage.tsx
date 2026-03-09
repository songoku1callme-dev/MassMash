import { useState, useRef } from "react";
import { voiceApi } from "../services/api";
import { Mic, MicOff, Volume2, Loader2, MessageCircle, Sparkles, Brain, History } from "lucide-react";
import { EmptyState } from "../components/PageStates";

interface ConversationEntry {
 role: "user" | "mentor";
 text: string;
 timestamp: Date;
}

export default function VoicePage() {
 const [isRecording, setIsRecording] = useState(false);
 const [isProcessing, setIsProcessing] = useState(false);
 const [error, setError] = useState("");
 const [isPlaying, setIsPlaying] = useState(false);
 const [conversation, setConversation] = useState<ConversationEntry[]>([]);
 const [recordingDuration, setRecordingDuration] = useState(0);
 const mediaRecorderRef = useRef<MediaRecorder | null>(null);
 const chunksRef = useRef<Blob[]>([]);
 const audioRef = useRef<HTMLAudioElement | null>(null);
 const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
 const conversationEndRef = useRef<HTMLDivElement | null>(null);

 const scrollToBottom = () => {
  setTimeout(() => conversationEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
 };

 const startRecording = async () => {
  try {
   setError("");
   setRecordingDuration(0);
   const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
   const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
   mediaRecorderRef.current = mediaRecorder;
   chunksRef.current = [];

   mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunksRef.current.push(e.data);
   };

   mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
    stream.getTracks().forEach((t) => t.stop());
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    await processAudio(audioBlob);
   };

   mediaRecorder.start();
   setIsRecording(true);
   timerRef.current = setInterval(() => {
    setRecordingDuration((d) => d + 1);
   }, 1000);
  } catch {
   setError("Mikrofon-Zugriff verweigert. Bitte erlaube den Zugriff in den Browser-Einstellungen.");
  }
 };

 const stopRecording = () => {
  if (mediaRecorderRef.current && isRecording) {
   mediaRecorderRef.current.stop();
   setIsRecording(false);
   if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }
 };

 const processAudio = async (audioBlob: Blob) => {
  setIsProcessing(true);
  try {
   // Step 1: Transcribe
   const result = await voiceApi.transcribe(audioBlob);
   if (result.text) {
    setConversation((prev) => [...prev, { role: "user", text: result.text, timestamp: new Date() }]);
    scrollToBottom();

    // Step 2: Voice chat — get mentor response
    try {
     const chatResult = await voiceApi.voiceChat(audioBlob);
     if (chatResult.response) {
      // Add mentor response with pauses for natural feel
      const mentorText = chatResult.response;
      setConversation((prev) => [...prev, { role: "mentor", text: mentorText, timestamp: new Date() }]);
      scrollToBottom();

      // Step 3: Auto-play TTS — realistic mentor voice
      try {
       const audioResult = await voiceApi.tts(mentorText);
       const url = URL.createObjectURL(audioResult);
       const audio = new Audio(url);
       audioRef.current = audio;
       setIsPlaying(true);
       audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
       };
       audio.play();
      } catch {
       // TTS fehlgeschlagen, aber Text-Antwort vorhanden
      }
     } else {
      setConversation((prev) => [...prev, {
       role: "mentor",
       text: "Ich konnte deine Frage leider nicht verarbeiten. Versuche es nochmal!",
       timestamp: new Date(),
      }]);
      scrollToBottom();
     }
    } catch {
     setConversation((prev) => [...prev, {
      role: "mentor",
      text: "Transkription erfolgreich! Sende die Nachricht im Chat für eine KI-Antwort.",
      timestamp: new Date(),
     }]);
     scrollToBottom();
    }
   }
  } catch (err) {
   setError(err instanceof Error ? err.message : "Fehler bei der Verarbeitung");
  } finally {
   setIsProcessing(false);
  }
 };

 const playTTS = async (text: string) => {
  setIsPlaying(true);
  try {
   const audioBlob = await voiceApi.tts(text);
   const url = URL.createObjectURL(audioBlob);
   const audio = new Audio(url);
   audioRef.current = audio;
   audio.onended = () => {
    setIsPlaying(false);
    URL.revokeObjectURL(url);
   };
   audio.play();
  } catch {
   setError("Sprachausgabe fehlgeschlagen");
   setIsPlaying(false);
  }
 };

 const formatDuration = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
 };

 return (
  <div className="p-6 max-w-2xl mx-auto flex flex-col" style={{ minHeight: "calc(100vh - 80px)" }}>
   {/* Header */}
   <div className="mb-6">
    <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
     <Brain className="w-7 h-7 text-purple-500" />
     KI-Mentor Voice
    </h1>
    <p className="theme-text-secondary mt-1">
     Sprich mit deinem persönlichen KI-Mentor — realistische Stimme mit Pausen und Betonung.
    </p>
   </div>

   {error && (
    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm">
     {error}
    </div>
   )}

   {/* Conversation History */}
   <div className="flex-1 mb-6 space-y-4 overflow-y-auto max-h-[400px] pr-1">
    {conversation.length === 0 && !isRecording && !isProcessing && (
     <EmptyState
      title="Kein Gespräch"
      description="Klicke den Mikrofon-Button und stelle deinem KI-Mentor eine Frage. Er antwortet mit natürlicher Stimme!"
      icon={<Mic className="w-8 h-8 text-indigo-400" />}
     />
    )}

    {conversation.map((entry, i) => (
     <div
      key={i}
      className={`flex ${entry.role === "user" ? "justify-end" : "justify-start"}`}
     >
      <div
       className={`max-w-[85%] p-4 rounded-2xl ${
        entry.role === "user"
         ? "bg-blue-600/20 border border-blue-500/30 rounded-br-md"
         : "bg-purple-600/10 border border-purple-500/20 rounded-bl-md"
       }`}
      >
       <div className="flex items-center gap-2 mb-1.5">
        {entry.role === "mentor" ? (
         <>
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-xs font-semibold text-purple-400">KI-Mentor</span>
         </>
        ) : (
         <>
          <MessageCircle className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-xs font-semibold text-blue-400">Du</span>
         </>
        )}
        <span className="text-[10px] theme-text-secondary ml-auto">
         {entry.timestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}
        </span>
       </div>
       <p className="text-sm theme-text">{entry.text}</p>
       {entry.role === "mentor" && (
        <button
         onClick={() => playTTS(entry.text)}
         disabled={isPlaying}
         className="mt-2 flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300"
        >
         <Volume2 className="w-3 h-3" />
         {isPlaying ? "Spielt..." : "Nochmal anhören"}
        </button>
       )}
      </div>
     </div>
    ))}

    {isProcessing && (
     <div className="flex justify-start">
      <div className="p-4 rounded-2xl rounded-bl-md bg-purple-600/10 border border-purple-500/20">
       <div className="flex items-center gap-2">
        <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />
        <span className="text-sm text-purple-400">Mentor denkt nach...</span>
       </div>
      </div>
     </div>
    )}

    <div ref={conversationEndRef} />
   </div>

   {/* Recording Controls */}
   <div className="flex flex-col items-center gap-4 py-4 border-t border-[var(--border-color)]">
    {/* Recording animation rings */}
    <div className="relative">
     {isRecording && (
      <>
       <div className="absolute inset-0 w-28 h-28 -m-2 rounded-full bg-red-500/20 animate-ping" />
       <div className="absolute inset-0 w-24 h-24 rounded-full bg-red-500/10 animate-pulse" />
      </>
     )}
     <button
      onClick={isRecording ? stopRecording : startRecording}
      disabled={isProcessing}
      className={`relative w-24 h-24 rounded-full flex items-center justify-center transition-all shadow-lg z-10 ${
       isRecording
        ? "bg-red-500 hover:bg-red-600 scale-110"
        : isProcessing
        ? "bg-gray-400 cursor-not-allowed"
        : "bg-gradient-to-br from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 hover:scale-105"
      }`}
      style={!isRecording && !isProcessing ? {
       background: "linear-gradient(135deg, #7c3aed, #2563eb)",
       boxShadow: "0 0 30px rgba(124,58,237,0.3)",
      } : undefined}
     >
      {isProcessing ? (
       <Loader2 className="w-10 h-10 text-white animate-spin" />
      ) : isRecording ? (
       <MicOff className="w-10 h-10 text-white" />
      ) : (
       <Mic className="w-10 h-10 text-white" />
      )}
     </button>
    </div>

    <p className="text-sm theme-text-secondary">
     {isRecording
      ? `Aufnahme läuft... ${formatDuration(recordingDuration)}`
      : isProcessing
      ? "Verarbeite Audio..."
      : "Klicke zum Sprechen"}
    </p>

    {conversation.length > 0 && (
     <div className="flex items-center gap-1 text-xs theme-text-secondary">
      <History className="w-3 h-3" />
      {conversation.length} Nachrichten in diesem Gespräch
     </div>
    )}
   </div>

   {/* Mentor Info */}
   <div className="mt-4 p-4 bg-[var(--bg-surface)] rounded-xl border border-[var(--border-color)]">
    <h3 className="font-medium theme-text mb-2 flex items-center gap-2">
     <Sparkles className="w-4 h-4 text-purple-400" />
     So funktioniert dein KI-Mentor
    </h3>
    <ul className="text-sm theme-text-secondary space-y-1.5">
     <li className="flex items-start gap-2">
      <span className="text-purple-400 font-bold">1.</span>
      Klicke den Mikrofon-Button und stelle deine Frage
     </li>
     <li className="flex items-start gap-2">
      <span className="text-purple-400 font-bold">2.</span>
      Whisper AI transkribiert deine Sprache in Text
     </li>
     <li className="flex items-start gap-2">
      <span className="text-purple-400 font-bold">3.</span>
      Dein KI-Mentor antwortet wie ein echter Tutor — mit Pausen und Betonung
     </li>
     <li className="flex items-start gap-2">
      <span className="text-purple-400 font-bold">4.</span>
      Die Antwort wird automatisch vorgelesen — oder klicke Nochmal anhören
     </li>
    </ul>
   </div>
  </div>
 );
}
