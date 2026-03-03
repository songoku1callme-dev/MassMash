/**
 * FachSelector.tsx — Fächer-Expansion 5.0 Block 6
 *
 * Searchable subject selector with:
 * - 32 subjects grouped by 6 categories
 * - Favorites (stored in localStorage, pinned at top)
 * - Search/filter input
 * - Compact chip design with emoji + name
 */
import { useState, useMemo, useCallback } from "react";
import { Search, Star } from "lucide-react";

// ── 32 Fächer in 6 Kategorien ──────────────────────────────────────
export interface FachItem {
  id: string;
  name: string;
  emoji: string;
  kategorie: string;
}

export const ALLE_FAECHER: FachItem[] = [
  // Sprachen
  { id: "german", name: "Deutsch", emoji: "📖", kategorie: "Sprachen" },
  { id: "english", name: "Englisch", emoji: "🇬🇧", kategorie: "Sprachen" },
  { id: "french", name: "Französisch", emoji: "🇫🇷", kategorie: "Sprachen" },
  { id: "latin", name: "Latein", emoji: "🏛️", kategorie: "Sprachen" },
  { id: "spanish", name: "Spanisch", emoji: "🇪🇸", kategorie: "Sprachen" },
  { id: "italian", name: "Italienisch", emoji: "🇮🇹", kategorie: "Sprachen" },
  { id: "russian", name: "Russisch", emoji: "🇷🇺", kategorie: "Sprachen" },
  { id: "turkish", name: "Türkisch", emoji: "🇹🇷", kategorie: "Sprachen" },
  { id: "ancient_greek", name: "Altgriechisch", emoji: "🏺", kategorie: "Sprachen" },

  // MINT
  { id: "math", name: "Mathematik", emoji: "📐", kategorie: "MINT" },
  { id: "physics", name: "Physik", emoji: "⚛️", kategorie: "MINT" },
  { id: "chemistry", name: "Chemie", emoji: "🧪", kategorie: "MINT" },
  { id: "biology", name: "Biologie", emoji: "🧬", kategorie: "MINT" },
  { id: "computer_science", name: "Informatik", emoji: "💻", kategorie: "MINT" },
  { id: "astronomy", name: "Astronomie", emoji: "🔭", kategorie: "MINT" },
  { id: "technology", name: "Technik", emoji: "⚙️", kategorie: "MINT" },

  // Gesellschaft
  { id: "history", name: "Geschichte", emoji: "📜", kategorie: "Gesellschaft" },
  { id: "geography", name: "Geografie", emoji: "🌍", kategorie: "Gesellschaft" },
  { id: "economics", name: "Wirtschaft", emoji: "📊", kategorie: "Gesellschaft" },
  { id: "politics", name: "Politik", emoji: "🏛️", kategorie: "Gesellschaft" },
  { id: "social_studies", name: "Sozialkunde", emoji: "👥", kategorie: "Gesellschaft" },
  { id: "psychology", name: "Psychologie", emoji: "🧠", kategorie: "Gesellschaft" },
  { id: "pedagogy", name: "Pädagogik", emoji: "📚", kategorie: "Gesellschaft" },
  { id: "social_science", name: "Sozialwissenschaften", emoji: "🔬", kategorie: "Gesellschaft" },
  { id: "law", name: "Recht", emoji: "⚖️", kategorie: "Gesellschaft" },

  // Religion & Ethik
  { id: "religion_catholic", name: "Religion (Kath.)", emoji: "✝️", kategorie: "Religion & Ethik" },
  { id: "religion_protestant", name: "Religion (Ev.)", emoji: "⛪", kategorie: "Religion & Ethik" },
  { id: "islam", name: "Islamunterricht", emoji: "☪️", kategorie: "Religion & Ethik" },
  { id: "ethics", name: "Ethik", emoji: "🤔", kategorie: "Religion & Ethik" },
  { id: "values_norms", name: "Werte und Normen", emoji: "💡", kategorie: "Religion & Ethik" },

  // Kreativ
  { id: "art", name: "Kunst", emoji: "🎨", kategorie: "Kreativ" },
  { id: "music", name: "Musik", emoji: "🎵", kategorie: "Kreativ" },
  { id: "drama", name: "Darstellendes Spiel", emoji: "🎭", kategorie: "Kreativ" },

  // Haushalt
  { id: "home_economics", name: "Hauswirtschaft", emoji: "🍳", kategorie: "Haushalt" },
  { id: "nutrition", name: "Ernährungslehre", emoji: "🥗", kategorie: "Haushalt" },
  { id: "wat", name: "WAT", emoji: "🔧", kategorie: "Haushalt" },
];

export const KATEGORIEN = [
  "Sprachen",
  "MINT",
  "Gesellschaft",
  "Religion & Ethik",
  "Kreativ",
  "Haushalt",
];

const FAVORITEN_KEY = "fach_favoriten";

function getFavoriten(): string[] {
  try {
    const raw = localStorage.getItem(FAVORITEN_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function setFavoriten(ids: string[]) {
  localStorage.setItem(FAVORITEN_KEY, JSON.stringify(ids));
}

interface FachSelectorProps {
  selected: string;
  onSelect: (id: string) => void;
  /** If true, show "Alle Fächer" as first option */
  showAll?: boolean;
}

export default function FachSelector({ selected, onSelect, showAll = true }: FachSelectorProps) {
  const [search, setSearch] = useState("");
  const [favoriten, setFavoritenState] = useState<string[]>(getFavoriten);

  const toggleFavorit = useCallback(
    (id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      setFavoritenState((prev) => {
        const next = prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id];
        setFavoriten(next);
        return next;
      });
    },
    [],
  );

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return ALLE_FAECHER;
    return ALLE_FAECHER.filter(
      (f) =>
        f.name.toLowerCase().includes(q) ||
        f.kategorie.toLowerCase().includes(q) ||
        f.id.toLowerCase().includes(q),
    );
  }, [search]);

  // Split into favoriten + rest, grouped by category
  const favFächer = useMemo(
    () => filtered.filter((f) => favoriten.includes(f.id)),
    [filtered, favoriten],
  );
  const restByKategorie = useMemo(() => {
    const map: Record<string, FachItem[]> = {};
    for (const k of KATEGORIEN) map[k] = [];
    for (const f of filtered) {
      if (!favoriten.includes(f.id)) {
        (map[f.kategorie] ??= []).push(f);
      }
    }
    return map;
  }, [filtered, favoriten]);

  return (
    <div className="w-full space-y-2">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Fach suchen..."
          className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex flex-wrap gap-1.5 max-h-[320px] overflow-y-auto pr-1">
        {/* "Alle Fächer" chip */}
        {showAll && (
          <FachChip
            fach={{ id: "general", name: "Alle Fächer", emoji: "✨", kategorie: "" }}
            isSelected={selected === "general"}
            isFavorit={false}
            onSelect={() => onSelect("general")}
            onToggleFavorit={() => {}}
          />
        )}

        {/* Favoriten section */}
        {favFächer.length > 0 && (
          <>
            <div className="w-full text-[10px] font-semibold text-yellow-600 dark:text-yellow-400 uppercase tracking-wider mt-1">
              Meine Fächer
            </div>
            {favFächer.map((f) => (
              <FachChip
                key={f.id}
                fach={f}
                isSelected={selected === f.id}
                isFavorit={true}
                onSelect={() => onSelect(f.id)}
                onToggleFavorit={(e) => toggleFavorit(f.id, e)}
              />
            ))}
          </>
        )}

        {/* Rest grouped by category */}
        {KATEGORIEN.map((kat) => {
          const items = restByKategorie[kat];
          if (!items || items.length === 0) return null;
          return (
            <div key={kat} className="w-full">
              <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mt-1.5 mb-0.5">
                {kat}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {items.map((f) => (
                  <FachChip
                    key={f.id}
                    fach={f}
                    isSelected={selected === f.id}
                    isFavorit={false}
                    onSelect={() => onSelect(f.id)}
                    onToggleFavorit={(e) => toggleFavorit(f.id, e)}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Chip sub-component ──────────────────────────────────────────────
function FachChip({
  fach,
  isSelected,
  isFavorit,
  onSelect,
  onToggleFavorit,
}: {
  fach: FachItem;
  isSelected: boolean;
  isFavorit: boolean;
  onSelect: () => void;
  onToggleFavorit: (e: React.MouseEvent) => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={`group relative flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
        isSelected
          ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 ring-2 ring-blue-400 scale-105"
          : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
      }`}
    >
      <span>{fach.emoji}</span>
      <span>{fach.name}</span>
      {fach.id !== "general" && (
        <span
          onClick={onToggleFavorit}
          className={`ml-0.5 transition-opacity ${
            isFavorit
              ? "text-yellow-500 opacity-100"
              : "text-gray-300 opacity-0 group-hover:opacity-100"
          }`}
          title={isFavorit ? "Favorit entfernen" : "Als Favorit merken"}
        >
          <Star className="w-3 h-3" fill={isFavorit ? "currentColor" : "none"} />
        </span>
      )}
    </button>
  );
}
