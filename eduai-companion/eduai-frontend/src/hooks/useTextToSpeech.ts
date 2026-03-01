/**
 * Custom hook for browser-native Text-to-Speech (TTS) using the Web Speech API.
 * Provides "Laut vorlesen" (Read aloud) functionality for AI responses.
 * Supports German (de-DE) and English (en-US) voices.
 */
import { useState, useRef, useCallback, useEffect } from "react";

/** Strip markdown/LaTeX formatting for cleaner TTS output. */
function cleanTextForSpeech(text: string): string {
  return text
    // Remove LaTeX block math $$...$$
    .replace(/\$\$[^$]+\$\$/g, " Formel ")
    // Remove LaTeX inline math $...$
    .replace(/\$[^$]+\$/g, " Formel ")
    // Remove markdown bold **text**
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    // Remove markdown italic *text*
    .replace(/\*([^*]+)\*/g, "$1")
    // Remove markdown headers ###
    .replace(/#{1,6}\s*/g, "")
    // Remove markdown links [text](url)
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    // Remove markdown images ![alt](url)
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")
    // Remove markdown code blocks ```...```
    .replace(/```[\s\S]*?```/g, " Code-Block ")
    // Remove inline code `text`
    .replace(/`([^`]+)`/g, "$1")
    // Remove markdown horizontal rules ---
    .replace(/^---+$/gm, "")
    // Remove markdown list markers
    .replace(/^[\s]*[-*+]\s/gm, "")
    // Remove markdown table formatting
    .replace(/\|/g, "")
    // Remove multiple spaces/newlines
    .replace(/\n{2,}/g, ". ")
    .replace(/\n/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function useTextToSpeech() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakingMessageIdx, setSpeakingMessageIdx] = useState<number | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const isSupported =
    typeof window !== "undefined" && "speechSynthesis" in window;

  /** Stop any ongoing speech. */
  const stopSpeaking = useCallback(() => {
    if (isSupported) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
    setSpeakingMessageIdx(null);
    utteranceRef.current = null;
  }, [isSupported]);

  /** Speak the given text aloud. */
  const speak = useCallback(
    (text: string, language: string = "de", messageIdx?: number) => {
      if (!isSupported) return;

      // If already speaking this message, stop it (toggle behavior)
      if (isSpeaking && speakingMessageIdx === messageIdx) {
        stopSpeaking();
        return;
      }

      // Cancel any ongoing speech first
      window.speechSynthesis.cancel();

      const cleanText = cleanTextForSpeech(text);
      if (!cleanText) return;

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = language === "de" ? "de-DE" : "en-US";
      utterance.rate = 0.9; // Slightly slower for educational content
      utterance.pitch = 1.0;

      // Try to find a good German voice
      const voices = window.speechSynthesis.getVoices();
      const langPrefix = language === "de" ? "de" : "en";
      const preferredVoice = voices.find(
        (v) => v.lang.startsWith(langPrefix) && v.localService
      ) || voices.find((v) => v.lang.startsWith(langPrefix));
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.onstart = () => {
        setIsSpeaking(true);
        setSpeakingMessageIdx(messageIdx ?? null);
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        setSpeakingMessageIdx(null);
        utteranceRef.current = null;
      };

      utterance.onerror = () => {
        setIsSpeaking(false);
        setSpeakingMessageIdx(null);
        utteranceRef.current = null;
      };

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [isSupported, isSpeaking, speakingMessageIdx, stopSpeaking],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isSupported) {
        window.speechSynthesis.cancel();
      }
    };
  }, [isSupported]);

  return {
    isSpeaking,
    speakingMessageIdx,
    isSupported,
    speak,
    stopSpeaking,
  };
}
