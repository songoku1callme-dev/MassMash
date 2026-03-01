import { useState, useRef } from "react";
import { voiceApi } from "../services/api";
import { Mic, MicOff, Volume2, Loader2, MessageCircle } from "lucide-react";

export default function VoicePage() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [error, setError] = useState("");
  const [isPlaying, setIsPlaying] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const startRecording = async () => {
    try {
      setError("");
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
        await processAudio(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch {
      setError("Mikrofon-Zugriff verweigert. Bitte erlaube den Zugriff in den Browser-Einstellungen.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processAudio = async (audioBlob: Blob) => {
    setIsProcessing(true);
    try {
      // Step 1: Transcribe
      const result = await voiceApi.transcribe(audioBlob);
      setTranscript(result.text);

      // Step 2: Get TTS response (we send the transcript to chat API separately)
      // For now, just show the transcript
      setResponse("Transkription erfolgreich! Sende die Nachricht im Chat fuer eine KI-Antwort.");
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

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Mic className="w-7 h-7 text-blue-600" />
          Voice-Modus
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Sprich mit deinem KI-Tutor! Whisper erkennt deine Sprache, gTTS antwortet.
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Recording Button */}
      <div className="flex flex-col items-center gap-6 mb-8">
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing}
          className={`w-32 h-32 rounded-full flex items-center justify-center transition-all shadow-lg ${
            isRecording
              ? "bg-red-500 hover:bg-red-600 animate-pulse scale-110"
              : isProcessing
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700 hover:scale-105"
          }`}
        >
          {isProcessing ? (
            <Loader2 className="w-12 h-12 text-white animate-spin" />
          ) : isRecording ? (
            <MicOff className="w-12 h-12 text-white" />
          ) : (
            <Mic className="w-12 h-12 text-white" />
          )}
        </button>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {isRecording
            ? "Aufnahme laeuft... Klicke zum Stoppen"
            : isProcessing
            ? "Verarbeite Audio..."
            : "Klicke zum Sprechen"}
        </p>
      </div>

      {/* Transcript */}
      {transcript && (
        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 mb-2">
            <MessageCircle className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Deine Nachricht</span>
          </div>
          <p className="text-gray-800 dark:text-gray-200">{transcript}</p>
        </div>
      )}

      {/* Response */}
      {response && (
        <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-green-700 dark:text-green-300">KI-Antwort</span>
            <button
              onClick={() => playTTS(response)}
              disabled={isPlaying}
              className="flex items-center gap-1 text-sm text-green-600 hover:text-green-700"
            >
              <Volume2 className="w-4 h-4" />
              {isPlaying ? "Spielt..." : "Vorlesen"}
            </button>
          </div>
          <p className="text-gray-800 dark:text-gray-200">{response}</p>
        </div>
      )}

      {/* Info */}
      <div className="mt-8 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <h3 className="font-medium text-gray-900 dark:text-white mb-2">So funktioniert's</h3>
        <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
          <li>1. Klicke den Mikrofon-Button und stelle deine Frage</li>
          <li>2. Whisper AI transkribiert deine Sprache in Text</li>
          <li>3. Der KI-Tutor antwortet auf deine Frage</li>
          <li>4. Klicke "Vorlesen" fuer die Sprachausgabe</li>
        </ul>
      </div>
    </div>
  );
}
