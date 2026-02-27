import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  Modal,
  ScrollView,
} from "react-native";
import { COLORS } from "../constants/theme";
import { useHaptics } from "../hooks/useHaptics";

const HABIT_ICONS = [
  "\uD83D\uDCA7", // water
  "\uD83C\uDFCB\uFE0F", // gym
  "\uD83D\uDCDA", // reading
  "\uD83E\uDDD8", // meditation
  "\uD83C\uDF4E", // nutrition
  "\uD83D\uDCA4", // sleep
  "\uD83D\uDEB6", // walking
  "\u270D\uFE0F", // journaling
  "\uD83D\uDCBB", // coding
  "\uD83C\uDFB5", // music
  "\uD83C\uDF3F", // nature
  "\uD83D\uDE4F", // gratitude
  "\uD83D\uDCAA", // strength
  "\uD83E\uDD57", // salad
  "\uD83C\uDFC3", // running
  "\uD83D\uDDE3\uFE0F", // speaking
];

interface AddHabitModalProps {
  visible: boolean;
  onClose: () => void;
  onAdd: (title: string, description: string, icon: string) => void;
}

export function AddHabitModal({ visible, onClose, onAdd }: AddHabitModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedIcon, setSelectedIcon] = useState(HABIT_ICONS[0]);
  const { lightTap } = useHaptics();

  const handleAdd = () => {
    if (!title.trim()) return;
    lightTap();
    onAdd(title.trim(), description.trim(), selectedIcon);
    setTitle("");
    setDescription("");
    setSelectedIcon(HABIT_ICONS[0]);
    onClose();
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View className="flex-1 justify-end">
        <Pressable className="flex-1" onPress={onClose} />
        <View
          className="rounded-t-3xl p-6"
          style={{ backgroundColor: COLORS.surface }}
        >
          <View className="w-12 h-1 bg-text-muted rounded-full self-center mb-6" />

          <Text className="text-text-primary font-poppins-bold text-xl mb-6">
            New Quest
          </Text>

          {/* Icon Selection */}
          <Text className="text-text-secondary font-inter text-sm mb-3">
            Choose an icon
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mb-4">
            {HABIT_ICONS.map((icon) => (
              <Pressable
                key={icon}
                onPress={() => {
                  lightTap();
                  setSelectedIcon(icon);
                }}
                className="w-12 h-12 rounded-xl items-center justify-center mr-2"
                style={{
                  backgroundColor:
                    selectedIcon === icon
                      ? `${COLORS.purpleAccent}40`
                      : COLORS.surfaceLight,
                  borderWidth: selectedIcon === icon ? 2 : 0,
                  borderColor: COLORS.purpleAccent,
                }}
              >
                <Text className="text-xl">{icon}</Text>
              </Pressable>
            ))}
          </ScrollView>

          {/* Title Input */}
          <TextInput
            placeholder="Quest name"
            placeholderTextColor={COLORS.textMuted}
            value={title}
            onChangeText={setTitle}
            className="text-text-primary font-inter text-base p-4 rounded-xl mb-3"
            style={{ backgroundColor: COLORS.surfaceLight }}
          />

          {/* Description Input */}
          <TextInput
            placeholder="Description (optional)"
            placeholderTextColor={COLORS.textMuted}
            value={description}
            onChangeText={setDescription}
            className="text-text-primary font-inter text-base p-4 rounded-xl mb-6"
            style={{ backgroundColor: COLORS.surfaceLight }}
            multiline
          />

          {/* Add Button */}
          <Pressable
            onPress={handleAdd}
            className="rounded-xl p-4 items-center"
            style={{
              backgroundColor: title.trim()
                ? COLORS.purpleAccent
                : COLORS.textMuted,
            }}
          >
            <Text className="text-text-primary font-poppins-bold text-base">
              Add Quest
            </Text>
          </Pressable>

          <Pressable onPress={onClose} className="mt-3 p-3 items-center">
            <Text className="text-text-secondary font-inter text-base">
              Cancel
            </Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}
