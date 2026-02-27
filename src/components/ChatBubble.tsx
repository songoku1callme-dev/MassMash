import React from "react";
import { View, Text } from "react-native";
import { COLORS } from "../constants/theme";
import type { ChatMessage } from "../types";

interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";

  return (
    <View
      className={`mb-3 max-w-[85%] ${isUser ? "self-end" : "self-start"}`}
    >
      <View
        className="rounded-2xl px-4 py-3"
        style={{
          backgroundColor: isUser ? COLORS.purpleAccent : COLORS.surface,
          borderBottomRightRadius: isUser ? 4 : 16,
          borderBottomLeftRadius: isUser ? 16 : 4,
        }}
      >
        <Text
          className="font-inter text-sm leading-5"
          style={{ color: COLORS.textPrimary }}
        >
          {message.content}
        </Text>
      </View>
      <Text
        className={`text-text-muted font-inter text-xs mt-1 ${
          isUser ? "text-right" : "text-left"
        }`}
      >
        {new Date(message.created_at).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}
      </Text>
    </View>
  );
}
