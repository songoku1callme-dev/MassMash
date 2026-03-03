import { useState, useEffect } from "react";
import { shopApi, ShopItem } from "../services/api";
import { Button } from "@/components/ui/button";
import { ShoppingBag, Palette, Bot, Crown, Gem, Zap, Lightbulb, SkipForward, Loader2, Check } from "lucide-react";

const ICON_MAP: Record<string, React.ReactNode> = {
  palette: <Palette className="w-6 h-6" />,
  bot: <Bot className="w-6 h-6" />,
  crown: <Crown className="w-6 h-6" />,
  gem: <Gem className="w-6 h-6" />,
  zap: <Zap className="w-6 h-6" />,
  lightbulb: <Lightbulb className="w-6 h-6" />,
  "skip-forward": <SkipForward className="w-6 h-6" />,
};

const CATEGORY_LABELS: Record<string, string> = {
  theme: "Themes",
  ki: "KI-Persönlichkeiten",
  frame: "Profilrahmen",
  boost: "Boosts",
};

const CATEGORY_COLORS: Record<string, string> = {
  theme: "from-blue-500 to-cyan-500",
  ki: "from-purple-500 to-pink-500",
  frame: "from-yellow-500 to-orange-500",
  boost: "from-green-500 to-emerald-500",
};

export default function ShopPage() {
  const [items, setItems] = useState<ShopItem[]>([]);
  const [userXp, setUserXp] = useState(0);
  const [loading, setLoading] = useState(true);
  const [buying, setBuying] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    loadShop();
  }, []);

  const loadShop = async () => {
    setLoading(true);
    try {
      const data = await shopApi.items();
      setItems(data.items);
      setUserXp(data.user_xp);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const buyItem = async (itemId: string) => {
    setBuying(itemId);
    setMessage(null);
    try {
      const data = await shopApi.buy(itemId);
      setMessage(data.message);
      setUserXp(data.remaining_xp);
      // Update item status
      setItems((prev) =>
        prev.map((i) => (i.id === itemId ? { ...i, unlocked: true, can_afford: data.remaining_xp >= i.price } : { ...i, can_afford: data.remaining_xp >= i.price }))
      );
    } catch (e: unknown) {
      const err = e as Error;
      setMessage(err.message || "Fehler beim Kauf");
    }
    setBuying(null);
  };

  const categories = [...new Set(items.map((i) => i.category))];
  const filteredItems = filter === "all" ? items : items.filter((i) => i.category === filter);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <ShoppingBag className="w-6 h-6" />
            Belohnungs-Shop
          </h1>
          <p className="text-gray-500 dark:text-gray-400">Gib deine XP für Themes, KI-Stile und Boosts aus</p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold text-yellow-600 dark:text-yellow-400">{userXp}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Verfügbare XP</p>
        </div>
      </div>

      {message && (
        <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-lg text-sm">
          {message}
        </div>
      )}

      {/* Category Filter */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        <button
          onClick={() => setFilter("all")}
          className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap ${
            filter === "all" ? "bg-blue-600 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
          }`}
        >
          Alle
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap ${
              filter === cat ? "bg-blue-600 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
            }`}
          >
            {CATEGORY_LABELS[cat] || cat}
          </button>
        ))}
      </div>

      {/* Items Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredItems.map((item) => (
          <div
            key={item.id}
            className={`relative bg-white dark:bg-gray-800 rounded-xl overflow-hidden border transition-all ${
              item.unlocked
                ? "border-green-300 dark:border-green-700"
                : "border-gray-200 dark:border-gray-700 hover:shadow-md"
            }`}
          >
            {/* Gradient header */}
            <div className={`h-2 bg-gradient-to-r ${CATEGORY_COLORS[item.category] || "from-gray-400 to-gray-500"}`} />

            <div className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${CATEGORY_COLORS[item.category] || "from-gray-400 to-gray-500"} flex items-center justify-center text-white`}>
                  {ICON_MAP[item.icon] || <ShoppingBag className="w-6 h-6" />}
                </div>
                {item.unlocked && (
                  <span className="flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30 px-2 py-1 rounded-full">
                    <Check className="w-3 h-3" />
                    Freigeschaltet
                  </span>
                )}
              </div>

              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{item.name}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                {CATEGORY_LABELS[item.category] || item.category}
              </p>

              <div className="flex items-center justify-between">
                <span className="text-lg font-bold text-yellow-600 dark:text-yellow-400">{item.price} XP</span>
                {!item.unlocked && (
                  <Button
                    size="sm"
                    disabled={!item.can_afford || buying === item.id}
                    onClick={() => buyItem(item.id)}
                  >
                    {buying === item.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : item.can_afford ? (
                      "Kaufen"
                    ) : (
                      "Zu wenig XP"
                    )}
                  </Button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
