import { XP_PER_LEVEL } from "../constants/theme";

/**
 * Calculate user level from total XP.
 * Level = floor(xp / XP_PER_LEVEL) + 1  (minimum level 1)
 */
export function calculateLevel(xp: number): number {
  return Math.floor(xp / XP_PER_LEVEL) + 1;
}

/**
 * Get the XP progress within the current level (0 to XP_PER_LEVEL).
 */
export function xpInCurrentLevel(xp: number): number {
  return xp % XP_PER_LEVEL;
}

/**
 * Get the percentage progress toward the next level (0..1).
 */
export function levelProgress(xp: number): number {
  return (xp % XP_PER_LEVEL) / XP_PER_LEVEL;
}

/**
 * Calculate life score from habit completion data.
 * Score = (completed / total) * 100, clamped 0-100.
 */
export function calculateLifeScore(
  completed: number,
  total: number
): number {
  if (total === 0) return 0;
  return Math.round(Math.min((completed / total) * 100, 100));
}

/**
 * Format XP for display: "1,250 XP"
 */
export function formatXP(xp: number): string {
  return `${xp.toLocaleString()} XP`;
}

/**
 * Get the title/rank based on level.
 */
export function getLevelTitle(level: number): string {
  if (level < 5) return "Apprentice";
  if (level < 10) return "Warrior";
  if (level < 20) return "Champion";
  if (level < 35) return "Master";
  if (level < 50) return "Grand Master";
  return "Legend";
}
