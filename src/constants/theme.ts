export const COLORS = {
  background: "#0B0F19",
  surface: "#131829",
  surfaceLight: "#1C2333",
  purpleAccent: "#8A2BE2",
  cyberBlue: "#00E5FF",
  successGreen: "#00FF7F",
  dangerRed: "#FF4757",
  warningYellow: "#FFD700",
  textPrimary: "#FFFFFF",
  textSecondary: "#A0AEC0",
  textMuted: "#4A5568",
} as const;

export const FONTS = {
  inter: {
    regular: "Inter_400Regular",
    medium: "Inter_500Medium",
    semibold: "Inter_600SemiBold",
    bold: "Inter_700Bold",
  },
  poppins: {
    regular: "Poppins_400Regular",
    medium: "Poppins_500Medium",
    semibold: "Poppins_600SemiBold",
    bold: "Poppins_700Bold",
  },
} as const;

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const BORDER_RADIUS = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 9999,
} as const;

/** XP required per level: level N requires N * 100 XP */
export const XP_PER_LEVEL = 100;

/** Starting HP for new users */
export const DEFAULT_HP = 100;
export const MAX_HP = 100;

/** HP penalty for missing a daily habit */
export const HP_MISS_PENALTY = 5;

/** Default XP reward for completing a habit */
export const DEFAULT_XP_REWARD = 25;
