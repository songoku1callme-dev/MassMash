import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from "react-native-reanimated";
import { supabase } from "../../src/lib/supabase";
import { COLORS } from "../../src/constants/theme";
import { useHaptics } from "../../src/hooks/useHaptics";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [magicLinkSent, setMagicLinkSent] = useState(false);
  const { lightTap } = useHaptics();

  const buttonScale = useSharedValue(1);
  const buttonAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(buttonScale.value) }],
  }));

  const handleMagicLink = async () => {
    if (!email.trim()) {
      Alert.alert("Error", "Please enter your email address.");
      return;
    }

    lightTap();
    setIsLoading(true);

    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: {
        emailRedirectTo: "evolveai://auth/callback",
      },
    });

    setIsLoading(false);

    if (error) {
      Alert.alert("Error", error.message);
      return;
    }

    setMagicLinkSent(true);
  };

  const handleGoogleSignIn = async () => {
    lightTap();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: "evolveai://auth/callback",
      },
    });

    if (error) {
      Alert.alert("Error", error.message);
    }
  };

  const handleAppleSignIn = async () => {
    lightTap();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "apple",
      options: {
        redirectTo: "evolveai://auth/callback",
      },
    });

    if (error) {
      Alert.alert("Error", error.message);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      className="flex-1"
      style={{ backgroundColor: COLORS.background }}
    >
      <ScrollView
        contentContainerStyle={{ flexGrow: 1, justifyContent: "center" }}
        keyboardShouldPersistTaps="handled"
      >
        <View className="flex-1 justify-center px-6">
          {/* Header */}
          <View className="items-center mb-12">
            <Text
              className="font-poppins-bold text-5xl mb-2"
              style={{ color: COLORS.purpleAccent }}
            >
              EvolveAI
            </Text>
            <Text className="text-text-secondary font-inter text-lg text-center">
              Your life is an RPG.{"\n"}Level up every day.
            </Text>
          </View>

          {magicLinkSent ? (
            /* Magic Link Sent State */
            <View className="items-center">
              <Text className="text-6xl mb-4">{"\u2709\uFE0F"}</Text>
              <Text className="text-text-primary font-poppins-bold text-xl mb-2">
                Check your email
              </Text>
              <Text className="text-text-secondary font-inter text-base text-center mb-6">
                We sent a magic link to{"\n"}
                <Text className="text-cyber-blue">{email}</Text>
              </Text>
              <Pressable onPress={() => setMagicLinkSent(false)}>
                <Text className="text-purple-accent font-inter-semibold text-base">
                  Use a different email
                </Text>
              </Pressable>
            </View>
          ) : (
            <>
              {/* Social Login Buttons */}
              <AnimatedPressable
                onPress={handleAppleSignIn}
                onPressIn={() => { buttonScale.value = 0.96; }}
                onPressOut={() => { buttonScale.value = 1; }}
                style={[buttonAnimStyle]}
                className="flex-row items-center justify-center p-4 rounded-xl mb-3"
                accessibilityRole="button"
                accessibilityLabel="Continue with Apple"
              >
                <View
                  className="flex-row items-center justify-center p-4 rounded-xl w-full"
                  style={{ backgroundColor: COLORS.textPrimary }}
                >
                  <Text className="text-xl mr-3">{"\uF8FF"}</Text>
                  <Text className="font-poppins-semibold text-base" style={{ color: COLORS.background }}>
                    Continue with Apple
                  </Text>
                </View>
              </AnimatedPressable>

              <AnimatedPressable
                onPress={handleGoogleSignIn}
                onPressIn={() => { buttonScale.value = 0.96; }}
                onPressOut={() => { buttonScale.value = 1; }}
                style={[buttonAnimStyle]}
                className="flex-row items-center justify-center p-4 rounded-xl mb-6"
                accessibilityRole="button"
                accessibilityLabel="Continue with Google"
              >
                <View
                  className="flex-row items-center justify-center p-4 rounded-xl w-full"
                  style={{ backgroundColor: COLORS.surface }}
                >
                  <Text className="text-xl mr-3">G</Text>
                  <Text className="text-text-primary font-poppins-semibold text-base">
                    Continue with Google
                  </Text>
                </View>
              </AnimatedPressable>

              {/* Divider */}
              <View className="flex-row items-center mb-6">
                <View className="flex-1 h-px" style={{ backgroundColor: COLORS.surfaceLight }} />
                <Text className="text-text-muted font-inter text-sm mx-4">
                  or
                </Text>
                <View className="flex-1 h-px" style={{ backgroundColor: COLORS.surfaceLight }} />
              </View>

              {/* Email Input */}
              <TextInput
                placeholder="Enter your email"
                placeholderTextColor={COLORS.textMuted}
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                className="text-text-primary font-inter text-base p-4 rounded-xl mb-4"
                style={{ backgroundColor: COLORS.surface }}
              />

              {/* Magic Link Button */}
              <AnimatedPressable
                onPress={handleMagicLink}
                disabled={isLoading}
                onPressIn={() => { buttonScale.value = 0.96; }}
                onPressOut={() => { buttonScale.value = 1; }}
                style={[buttonAnimStyle]}
                accessibilityRole="button"
                accessibilityLabel="Send Magic Link"
              >
                <View
                  className="p-4 rounded-xl items-center"
                  style={{
                    backgroundColor: isLoading
                      ? COLORS.textMuted
                      : COLORS.purpleAccent,
                  }}
                >
                  <Text className="text-text-primary font-poppins-bold text-base">
                    {isLoading ? "Sending..." : "Send Magic Link"}
                  </Text>
                </View>
              </AnimatedPressable>
            </>
          )}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
