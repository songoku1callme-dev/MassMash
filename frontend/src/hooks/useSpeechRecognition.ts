/**
 * Custom hook for Web Speech Recognition API (voice input).
 *
 * Provides start/stop controls and live transcript text.
 * Falls back gracefully when the browser does not support the API.
 */

import { useState, useRef, useCallback, useEffect } from "react";

/** Augment Window with vendor-prefixed SpeechRecognition. */
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

type SpeechRecognitionErrorEvent = Event & { error: string; message?: string };

interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((ev: SpeechRecognitionEvent) => void) | null;
  onerror: ((ev: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

function getSpeechRecognitionCtor(): SpeechRecognitionConstructor | null {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as SpeechRecognitionConstructor | null;
}

export interface UseSpeechRecognitionReturn {
  /** Whether the browser supports speech recognition. */
  supported: boolean;
  /** Whether the recognizer is currently listening. */
  listening: boolean;
  /** Live transcript (interim + final combined). */
  transcript: string;
  /** Start listening. */
  start: () => void;
  /** Stop listening (delivers final result). */
  stop: () => void;
  /** Clear the transcript buffer. */
  clear: () => void;
  /** Last error message, if any. */
  error: string | null;
}

export function useSpeechRecognition(
  lang = "de-DE",
): UseSpeechRecognitionReturn {
  const supported = getSpeechRecognitionCtor() !== null;
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const finalTranscriptRef = useRef("");

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  const start = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setError("Speech Recognition wird von diesem Browser nicht unterstuetzt.");
      return;
    }

    // Abort any existing session
    recognitionRef.current?.abort();

    const rec = new Ctor();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = lang;

    finalTranscriptRef.current = "";
    setTranscript("");
    setError(null);

    rec.onstart = () => setListening(true);

    rec.onresult = (ev: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const result = ev.results[i];
        if (result.isFinal) {
          finalTranscriptRef.current += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }
      setTranscript(finalTranscriptRef.current + interim);
    };

    rec.onerror = (ev: SpeechRecognitionErrorEvent) => {
      // "aborted" is not a real error, just the user stopping
      if (ev.error !== "aborted") {
        setError(`Spracherkennung-Fehler: ${ev.error}`);
      }
      setListening(false);
    };

    rec.onend = () => {
      setListening(false);
    };

    recognitionRef.current = rec;
    rec.start();
  }, [lang]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const clear = useCallback(() => {
    finalTranscriptRef.current = "";
    setTranscript("");
  }, []);

  return { supported, listening, transcript, start, stop, clear, error };
}
