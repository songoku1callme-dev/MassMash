// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// LUMNOS Animation Library — Apple-Level UI
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// APPLE EASING CURVES — genau wie iOS
export const APPLE_EASE = [0.25, 0.46, 0.45, 0.94] as const;
export const APPLE_SPRING = {
  type: "spring" as const,
  stiffness: 400,
  damping: 30,
};
export const APPLE_SPRING_SOFT = {
  type: "spring" as const,
  stiffness: 200,
  damping: 25,
};

// PAGE TRANSITIONS
export const pageVariants = {
  initial: { opacity: 0, y: 20, scale: 0.98 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.4, ease: APPLE_EASE },
  },
  exit: {
    opacity: 0,
    y: -10,
    scale: 0.98,
    transition: { duration: 0.25, ease: APPLE_EASE },
  },
};

// STAGGER CHILDREN (fuer Listen)
export const staggerContainer = {
  initial: {},
  animate: {
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

export const staggerItem = {
  initial: { opacity: 0, y: 16 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: APPLE_EASE },
  },
};

// CARD HOVER
export const cardHover = {
  rest: { scale: 1, y: 0 },
  hover: {
    scale: 1.02,
    y: -4,
    transition: APPLE_SPRING,
  },
  tap: { scale: 0.98 },
};

// BUTTON PRESS
export const buttonTap = {
  whileTap: { scale: 0.95 },
  whileHover: { scale: 1.02 },
  transition: { type: "spring" as const, stiffness: 600, damping: 25 },
};

// MODAL/SHEET SLIDE UP (wie iOS Sheets)
export const sheetVariants = {
  initial: { opacity: 0, y: "100%", scale: 0.95 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 300, damping: 30 },
  },
  exit: {
    opacity: 0,
    y: "100%",
    scale: 0.95,
    transition: { duration: 0.25, ease: APPLE_EASE },
  },
};

// SIDEBAR ITEM
export const sidebarItem = {
  initial: { opacity: 0, x: -20 },
  animate: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.04, duration: 0.3, ease: APPLE_EASE },
  }),
};

// FADE IN (fuer Content-Bereiche)
export const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.4 } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
};

// CHAT MESSAGE ANIMATIONS
export const userMessageVariants = {
  initial: { opacity: 0, x: 30, scale: 0.9 },
  animate: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 350, damping: 28 },
  },
};

export const aiMessageVariants = {
  initial: { opacity: 0, x: -20, scale: 0.95 },
  animate: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 300, damping: 26, delay: 0.05 },
  },
};

// TYPING INDICATOR DOT
export const typingDot = (delay: number) => ({
  animate: {
    scale: [1, 1.4, 1],
    opacity: [0.5, 1, 0.5],
  },
  transition: {
    duration: 0.8,
    repeat: Infinity,
    delay: delay * 0.16,
  },
});

// TOAST NOTIFICATION
export const toastVariants = {
  initial: { opacity: 0, x: 100, scale: 0.9 },
  animate: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 400, damping: 28 },
  },
  exit: {
    opacity: 0,
    x: 100,
    scale: 0.9,
    transition: { duration: 0.25, ease: APPLE_EASE },
  },
};

// XP BAR FILL
export const xpBarFill = (percent: number) => ({
  initial: { width: "0%" },
  animate: {
    width: `${percent}%`,
    transition: { duration: 1.2, ease: APPLE_EASE, delay: 0.3 },
  },
});

// XP SHIMMER
export const xpShimmer = {
  animate: { x: ["-100%", "200%"] },
  transition: { duration: 2, repeat: Infinity, ease: "linear" as const, delay: 1.5 },
};

// XP GAINED POPUP
export const xpGainedPopup = {
  initial: { opacity: 0, y: 0, scale: 0.8 },
  animate: { opacity: 1, y: -40, scale: 1 },
  exit: { opacity: 0, y: -70, scale: 0.8 },
  transition: { type: "spring" as const, stiffness: 400, damping: 20 },
};

// MOBILE OVERLAY
export const mobileOverlay = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.2 },
};

// MOBILE SIDEBAR SLIDE
export const mobileSidebarSlide = {
  initial: { x: "-100%" },
  animate: { x: 0, transition: APPLE_SPRING },
  exit: { x: "-100%", transition: { duration: 0.25, ease: APPLE_EASE } },
};
