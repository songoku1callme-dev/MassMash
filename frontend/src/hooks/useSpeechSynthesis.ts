/**
 * Custom hook for Web Speech Synthesis API (text-to-speech output).
 *
 * Provides speak/stop controls with configurable rate, pitch, and voice.
 */

import { useState, useCallback, useEffect, useRef } from "react";
import type { VoiceSettings } from "@/types";

export interface UseSpeechSynthesisReturn {
  /** Whether the browser supports speech synthesis. */
  supported: boolean;
  /** Whether TTS is currently speaking. */
  speaking: boolean;
  /** Available voices the browser offers. */
  voices: SpeechSynthesisVoice[];
  /** Speak the given text aloud. */
  speak: (text: string) => void;
  /** Stop any current speech. */
  stop: () => void;
}

/** Strip simple HTML/markdown so TTS reads plain text. */
function stripMarkup(text: string): string {
  return text
    .replace(/<[^>]+>/g, "")
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/#{1,6}\s/g, "")
    .trim();
}

export function useSpeechSynthesis(
  settings: VoiceSettings,
): UseSpeechSynthesisReturn {
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  const [speaking, setSpeaking] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Load available voices (they load asynchronously in some browsers)
  useEffect(() => {
    if (!supported) return;

    const loadVoices = () => {
      const v = window.speechSynthesis.getVoices();
      if (v.length > 0) setVoices(v);
    };

    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);
    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoices);
    };
  }, [supported]);

  // Cancel speech on unmount
  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (!supported) return;

      // Cancel any ongoing speech first
      window.speechSynthesis.cancel();

      const plain = stripMarkup(text);
      if (!plain) return;

      const utt = new SpeechSynthesisUtterance(plain);
      utt.rate = settings.rate;
      utt.pitch = settings.pitch;
      utt.lang = settings.recognitionLang || "de-DE";

      // Find the selected voice by URI
      if (settings.voiceURI) {
        const match = voices.find((v) => v.voiceURI === settings.voiceURI);
        if (match) utt.voice = match;
      }

      utt.onstart = () => setSpeaking(true);
      utt.onend = () => setSpeaking(false);
      utt.onerror = () => setSpeaking(false);

      utteranceRef.current = utt;
      window.speechSynthesis.speak(utt);
    },
    [supported, settings, voices],
  );

  const stop = useCallback(() => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  return { supported, speaking, voices, speak, stop };
}
