import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ActivityIndicator,
} from "react-native";
import { COLORS } from "../../src/constants/theme";
import { useChatStore } from "../../src/stores/chatStore";
import { useAuthStore } from "../../src/stores/authStore";
import { ChatBubble } from "../../src/components/ChatBubble";
import { useHaptics } from "../../src/hooks/useHaptics";
import { useProGate } from "../../src/hooks/useProGate";
import type { ChatMessage } from "../../src/types";

export default function CoachScreen() {
  const {
    messages,
    isLoading,
    fetchMessages,
    sendMessage,
    canSendMessage,
    countTodayInteractions,
  } = useChatStore();
  const profile = useAuthStore((s) => s.profile);
  const [inputText, setInputText] = useState("");
  const flatListRef = useRef<FlatList<ChatMessage>>(null);
  const { lightTap } = useHaptics();
  const { isPro } = useProGate();

  useEffect(() => {
    fetchMessages();
    countTodayInteractions();
  }, [fetchMessages, countTodayInteractions]);

  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;
    lightTap();

    const text = inputText.trim();
    setInputText("");
    await sendMessage(text);
  };

  const canSend = canSendMessage();

  return (
    <SafeAreaView
      className="flex-1"
      style={{ backgroundColor: COLORS.background }}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        className="flex-1"
        keyboardVerticalOffset={90}
      >
        {/* Header */}
        <View
          className="px-6 py-4 flex-row items-center"
          style={{
            borderBottomWidth: 1,
            borderBottomColor: COLORS.surfaceLight,
          }}
        >
          <Text className="text-2xl mr-3">{"\uD83E\uDD16"}</Text>
          <View>
            <Text className="text-text-primary font-poppins-bold text-lg">
              AI Coach
            </Text>
            <Text className="text-text-secondary font-inter text-xs">
              {isPro
                ? "Unlimited coaching"
                : `${canSend ? "1 free message today" : "Upgrade for more"}`}
            </Text>
          </View>
        </View>

        {/* Messages */}
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <ChatBubble message={item} />}
          contentContainerStyle={{
            padding: 16,
            flexGrow: 1,
            justifyContent: messages.length === 0 ? "center" : "flex-end",
          }}
          onContentSizeChange={() =>
            flatListRef.current?.scrollToEnd({ animated: true })
          }
          ListEmptyComponent={
            <View className="items-center">
              <Text className="text-5xl mb-4">{"\uD83D\uDCAC"}</Text>
              <Text className="text-text-primary font-poppins-semibold text-lg text-center">
                Hey {profile?.display_name ?? "there"}!
              </Text>
              <Text className="text-text-secondary font-inter text-sm text-center mt-2 px-8">
                I&apos;m your AI coach. Ask me anything about your habits,
                goals, or how to level up your life!
              </Text>
            </View>
          }
        />

        {/* Loading indicator */}
        {isLoading && (
          <View className="px-4 py-2 flex-row items-center">
            <ActivityIndicator size="small" color={COLORS.purpleAccent} />
            <Text className="text-text-secondary font-inter text-sm ml-2">
              Thinking...
            </Text>
          </View>
        )}

        {/* Input */}
        <View
          className="flex-row items-end px-4 py-3"
          style={{
            borderTopWidth: 1,
            borderTopColor: COLORS.surfaceLight,
          }}
        >
          <TextInput
            value={inputText}
            onChangeText={setInputText}
            placeholder={
              canSend
                ? "Ask your AI coach..."
                : "Upgrade to Pro for more messages"
            }
            placeholderTextColor={COLORS.textMuted}
            multiline
            maxLength={500}
            editable={canSend}
            className="flex-1 text-text-primary font-inter text-base p-3 rounded-xl mr-3 max-h-24"
            style={{ backgroundColor: COLORS.surface }}
          />
          <Pressable
            onPress={handleSend}
            disabled={!inputText.trim() || isLoading || !canSend}
            className="w-11 h-11 rounded-full items-center justify-center"
            style={{
              backgroundColor:
                inputText.trim() && canSend
                  ? COLORS.purpleAccent
                  : COLORS.surfaceLight,
            }}
          >
            <Text className="text-text-primary text-lg">{"\u2191"}</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
