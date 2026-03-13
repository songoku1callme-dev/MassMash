/**
 * useMicrophone — Cross-Browser Mikrofon-Hook
 *
 * Unterstützt:
 * - Web Speech API (Chrome, Edge, Safari 14.1+)
 * - MediaRecorder Fallback (Firefox, alle modernen Browser)
 * - Capacitor Speech Recognition (iOS/Android native)
 *
 * Gibt einheitliches Interface zurück unabhängig vom verwendeten Backend.
 */
import { useState, useRef, useCallback, useEffect } from "react";

type MicrophoneBackend = "webspeech" | "mediarecorder" | "capacitor" | "none";

interface MicrophoneState {
  isListening: boolean;
  transcript: string;
  error: string | null;
  isSupported: boolean;
  backend: MicrophoneBackend;
  hasPermission: boolean | null;
}

interface MicrophoneActions {
  startListening: (onResult?: (text: string) => void) => void;
  stopListening: () => void;
  requestPermission: () => Promise<boolean>;
  clearError: () => void;
}

export type UseMicrophoneReturn = MicrophoneState & MicrophoneActions;

// Detect which backend is available
function detectBackend(): MicrophoneBackend {
  if (typeof window === "undefined") return "none";

  // Check for Capacitor native plugin
  if (
    typeof (window as Record<string, unknown>).Capacitor !== "undefined" &&
    typeof (window as Record<string, unknown>).SpeechRecognition !== "undefined"
  ) {
    return "capacitor";
  }

  // Check for Web Speech API
  const SR = (window as Record<string, unknown>).SpeechRecognition ||
    (window as Record<string, unknown>).webkitSpeechRecognition;
  if (SR) return "webspeech";

  // Check for MediaRecorder (Firefox, etc.)
  if (typeof MediaRecorder !== "undefined" && navigator.mediaDevices?.getUserMedia) {
    return "mediarecorder";
  }

  return "none";
}

export function useMicrophone(language: string = "de"): UseMicrophoneReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  const backend = detectBackend();
  const isSupported = backend !== "none";

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const transcriptRef = useRef("");

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch { /* noop */ }
      }
      if (mediaRecorderRef.current?.state === "recording") {
        try { mediaRecorderRef.current.stop(); } catch { /* noop */ }
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  const clearError = useCallback(() => setError(null), []);

  // Request microphone permission
  const requestPermission = useCallback(async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(t => t.stop()); // Release immediately
      setHasPermission(true);
      return true;
    } catch {
      setHasPermission(false);
      setError("Mikrofon-Zugriff verweigert. Bitte erlaube den Zugriff in den Browser-Einstellungen.");
      return false;
    }
  }, []);

  // Stop listening (all backends)
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
      recognitionRef.current = null;
    }
    if (mediaRecorderRef.current?.state === "recording") {
      try { mediaRecorderRef.current.stop(); } catch { /* ignore */ }
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setIsListening(false);
  }, []);

  // Start listening with Web Speech API
  const startWebSpeech = useCallback((onResult?: (text: string) => void) => {
    const SR = (window as unknown as Record<string, unknown>).SpeechRecognition ||
      (window as unknown as Record<string, unknown>).webkitSpeechRecognition;
    if (!SR) {
      setError("Web Speech API nicht verfügbar.");
      return;
    }

    // Stop any existing recognition
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch { /* ignore */ }
    }

    const recog = new (SR as new () => SpeechRecognition)();
    recog.lang = language === "de" ? "de-DE" : language === "en" ? "en-US" : `${language}-${language.toUpperCase()}`;
    recog.continuous = false;
    recog.interimResults = true;

    setIsListening(true);
    setTranscript("");
    setError(null);
    transcriptRef.current = "";

    recog.onresult = (e: SpeechRecognitionEvent) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) {
        text += e.results[i][0].transcript;
      }
      setTranscript(text);
      transcriptRef.current = text;
    };

    recog.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
      const finalText = transcriptRef.current.trim();
      if (finalText && onResult) {
        onResult(finalText);
      }
    };

    recog.onerror = (e: SpeechRecognitionErrorEvent) => {
      setIsListening(false);
      recognitionRef.current = null;
      switch (e.error) {
        case "not-allowed":
          setError("Mikrofon-Zugriff verweigert. Klicke auf das Schloss-Symbol in der Adressleiste.");
          setHasPermission(false);
          break;
        case "no-speech":
          setError("Keine Sprache erkannt. Bitte sprich lauter oder näher am Mikrofon.");
          break;
        case "audio-capture":
          setError("Kein Mikrofon gefunden. Bitte schließe ein Mikrofon an.");
          break;
        case "network":
          setError("Netzwerkfehler bei der Spracherkennung.");
          break;
        case "aborted":
          break; // User cancelled
        default:
          setError(`Spracherkennungsfehler: ${e.error}`);
      }
    };

    recognitionRef.current = recog;
    try {
      recog.start();
    } catch {
      setError("Spracherkennung konnte nicht gestartet werden.");
      setIsListening(false);
    }
  }, [language]);

  // Start listening with MediaRecorder (fallback for Firefox etc.)
  const startMediaRecorder = useCallback(async (onResult?: (text: string) => void) => {
    setError(null);
    setTranscript("");
    setIsListening(true);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      setHasPermission(true);

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = recorder;
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        streamRef.current = null;
        setIsListening(false);

        if (chunks.length > 0) {
          // MediaRecorder can't do STT locally — show info message
          setTranscript("[Audioaufnahme beendet — wird verarbeitet...]");
          if (onResult) {
            onResult("[audio_recorded]");
          }
        }
      };

      recorder.onerror = () => {
        setError("Aufnahmefehler. Bitte versuche es erneut.");
        setIsListening(false);
      };

      recorder.start();

      // Auto-stop after 30 seconds
      setTimeout(() => {
        if (recorder.state === "recording") {
          recorder.stop();
        }
      }, 30000);
    } catch {
      setError("Mikrofon-Zugriff fehlgeschlagen. Bitte erlaube den Zugriff.");
      setIsListening(false);
      setHasPermission(false);
    }
  }, []);

  // Unified startListening
  const startListening = useCallback((onResult?: (text: string) => void) => {
    if (!isSupported) {
      setError(
        "Dein Browser unterstützt keine Spracheingabe. " +
        "Bitte verwende Chrome, Edge oder Safari für die beste Erfahrung."
      );
      return;
    }

    switch (backend) {
      case "webspeech":
      case "capacitor":
        startWebSpeech(onResult);
        break;
      case "mediarecorder":
        startMediaRecorder(onResult);
        break;
      default:
        setError("Keine Spracheingabe-Methode verfügbar.");
    }
  }, [backend, isSupported, startWebSpeech, startMediaRecorder]);

  return {
    isListening,
    transcript,
    error,
    isSupported,
    backend,
    hasPermission,
    startListening,
    stopListening,
    requestPermission,
    clearError,
  };
}
