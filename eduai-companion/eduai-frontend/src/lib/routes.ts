/**
 * Route configuration for LUMNOS React Router.
 *
 * Maps page IDs (used in Sidebar nav items) to URL paths.
 * Provides helpers to convert between page IDs and paths.
 */

export interface RouteConfig {
  id: string;
  path: string;
}

/** All app routes — order matters for matching */
export const ROUTES: RouteConfig[] = [
  { id: "dashboard", path: "/dashboard" },
  { id: "chat", path: "/chat" },
  { id: "quiz", path: "/quiz" },
  { id: "iq-test", path: "/iq-test" },
  { id: "learning", path: "/learning" },
  { id: "rag", path: "/rag" },
  { id: "abitur", path: "/abitur" },
  { id: "research", path: "/research" },
  { id: "gamification", path: "/gamification" },
  { id: "groups", path: "/groups" },
  { id: "turnier", path: "/turnier" },
  { id: "flashcards", path: "/flashcards" },
  { id: "notes", path: "/notes" },
  { id: "calendar", path: "/calendar" },
  { id: "multiplayer", path: "/multiplayer" },
  { id: "intelligence", path: "/intelligence" },
  { id: "pomodoro", path: "/pomodoro" },
  { id: "shop", path: "/shop" },
  { id: "challenges", path: "/challenges" },
  { id: "voice", path: "/voice" },
  { id: "quests", path: "/quests" },
  { id: "events", path: "/events" },
  { id: "matching", path: "/matching" },
  { id: "marketplace", path: "/marketplace" },
  { id: "battle-pass", path: "/battle-pass" },
  { id: "meine-stats", path: "/meine-stats" },
  { id: "voice-exam", path: "/voice-exam" },
  { id: "scanner", path: "/scanner" },
  { id: "parents", path: "/parents" },
  { id: "school", path: "/school" },
  { id: "admin", path: "/admin" },
  { id: "forschung", path: "/forschung" },
  { id: "datenschutz", path: "/datenschutz" },
  { id: "pricing", path: "/pricing" },
  { id: "settings", path: "/settings" },
];

const idToPath = new Map(ROUTES.map((r) => [r.id, r.path]));
const pathToId = new Map(ROUTES.map((r) => [r.path, r.id]));

/** Convert a page ID (e.g. "chat") to a URL path (e.g. "/chat"). */
export function pageIdToPath(id: string): string {
  return idToPath.get(id) || "/dashboard";
}

/** Convert a URL path (e.g. "/chat") to a page ID (e.g. "chat"). */
export function pathToPageId(path: string): string {
  return pathToId.get(path) || "dashboard";
}
