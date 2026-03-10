export const BRAND = {
    name: "Lumnos",
    tagline: "Dein KI-Lerncoach. Personalisiert. Intelligent. Für dich.",
    tagline_short: "Lerne smarter mit KI",
    description: "Lumnos ist Deutschlands intelligenteste Lernplattform.",
    domain: "lumnos.de",
    support_email: "hilfe@lumnos.de",
    color_primary: "#6366f1",    // Indigo-Neon
    color_secondary: "#8b5cf6",  // Violet
    logo_emoji: "\u2726",
    founded: "2026",

    // Fach-Farben für Neon-Glow
    fach_farben: {
        "Mathe":       "#3b82f6",  // Blau
        "Physik":      "#06b6d4",  // Cyan
        "Chemie":      "#10b981",  // Grün
        "Biologie":    "#22c55e",  // Hellgrün
        "Geschichte":  "#f59e0b",  // Gold
        "Deutsch":     "#ec4899",  // Pink
        "Englisch":    "#f97316",  // Orange
        "Informatik":  "#6366f1",  // Indigo
        "Latein":      "#a78bfa",  // Violett
        "Philosophie": "#8b5cf6",  // Lila
        "Musik":       "#f43f5e",  // Rot-Pink
        "Kunst":       "#fb923c",  // Orange
        "Sport":       "#84cc16",  // Lime
        "default":     "#6366f1",
    }
} as const;

export type FachName = keyof typeof BRAND.fach_farben;

export function getFachFarbe(fach: string): string {
    return (BRAND.fach_farben as Record<string, string>)[fach] || BRAND.fach_farben.default;
}
