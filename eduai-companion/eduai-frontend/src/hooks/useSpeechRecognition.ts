/**
 * Custom hook for browser-native Speech-to-Text using the Web Speech API.
 * Works in Chrome, Edge, Safari (no backend needed).
 *
 * IMPORTANT: startListening MUST be called directly from a user click handler
 * (not from useEffect/setTimeout) — otherwise browsers block mic access.
 */
import { useState, useRef, useCallback } from "react";

// Type declarations for the Web Speech API (not in default TS lib)
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

interface SpeechRecognitionInstance extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition: new () => SpeechRecognitionInstance;
  }
}

// Browser-Kompatibilitaet: Chrome nutzt webkitSpeechRecognition
const getSpeechRecognitionClass = (): (new () => SpeechRecognitionInstance) | null => {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
};

export function useSpeechRecognition(language: string = "de") {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  const isSupported = getSpeechRecognitionClass() !== null;

  const clearError = useCallback(() => setError(null), []);

  const startListening = useCallback(
    (onResult?: (text: string) => void) => {
      // Clear any previous error first
      setError(null);
      setTranscript("");

      const SpeechRecognitionClass = getSpeechRecognitionClass();
      if (!SpeechRecognitionClass) {
        setError("Dein Browser unterstuetzt keine Spracheingabe. Bitte nutze Chrome oder Edge.");
        return;
      }

      // Stop any existing recognition first
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch { /* ignore */ }
        recognitionRef.current = null;
      }

      try {
        const recognition = new SpeechRecognitionClass();

        // Sprache korrekt setzen — MUSS de-DE sein für deutsche Erkennung!
        recognition.lang = language === "de" ? "de-DE" : "en-US";
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
          setIsListening(true);
        };

        recognition.onresult = (event: SpeechRecognitionEvent) => {
          let interimTranscript = "";
          let finalTranscript = "";

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            if (result.isFinal) {
              finalTranscript += result[0].transcript;
            } else {
              interimTranscript += result[0].transcript;
            }
          }

          const currentText = finalTranscript || interimTranscript;
          setTranscript(currentText);

          if (finalTranscript && onResult) {
            onResult(finalTranscript.trim());
          }
        };

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
          setIsListening(false);
          recognitionRef.current = null;

          // Detaillierte Fehlermeldungen je nach Fehlertyp
          switch (event.error) {
            case "not-allowed":
              setError("Mikrofon-Zugriff verweigert. Klicke auf das Schloss-Symbol in der Adressleiste und erlaube das Mikrofon.");
              break;
            case "no-speech":
              setError("Keine Sprache erkannt. Bitte versuche es nochmal.");
              break;
            case "audio-capture":
              setError("Kein Mikrofon gefunden. Bitte stelle sicher, dass ein Mikrofon angeschlossen ist.");
              break;
            case "network":
              setError("Netzwerkfehler bei der Spracherkennung. Pruefe deine Internetverbindung.");
              break;
            case "aborted":
              // User cancelled — no error message needed
              break;
            default:
              setError(`Spracherkennung-Fehler: ${event.error}`);
          }
        };

        recognition.onend = () => {
          setIsListening(false);
          recognitionRef.current = null;
        };

        recognitionRef.current = recognition;
        // IMPORTANT: This .start() call must happen synchronously within the
        // user's click event handler. Do NOT wrap in setTimeout/Promise.
        recognition.start();
      } catch {
        setError("Spracherkennung konnte nicht gestartet werden. Bitte versuche es erneut.");
        setIsListening(false);
        recognitionRef.current = null;
      }
    },
    [language],
  );

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
      recognitionRef.current = null;
    }
    setIsListening(false);
  }, []);

  return {
    isListening,
    transcript,
    error,
    isSupported,
    startListening,
    stopListening,
    clearError,
  };
}
