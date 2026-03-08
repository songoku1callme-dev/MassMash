import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { shopApi, ShopItem } from "../services/api";
import { useShopItems } from "../hooks/useApiQueries";
import { ShoppingBag, Palette, Bot, Crown, Gem, Zap, Lightbulb, SkipForward, Loader2, Check } from "lucide-react";
import { PageLoader, ErrorState } from "../components/PageStates";

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

const CATEGORY_GRADIENT_STYLES: Record<string, { bg: string; border: string }> = {
 theme: { bg: "linear-gradient(135deg, rgba(59,130,246,0.15), rgba(6,182,212,0.15))", border: "rgba(59,130,246,0.3)" },
 ki: { bg: "linear-gradient(135deg, rgba(139,92,246,0.15), rgba(236,72,153,0.15))", border: "rgba(139,92,246,0.3)" },
 frame: { bg: "linear-gradient(135deg, rgba(234,179,8,0.15), rgba(249,115,22,0.15))", border: "rgba(234,179,8,0.3)" },
 boost: { bg: "linear-gradient(135deg, rgba(16,185,129,0.15), rgba(34,197,94,0.15))", border: "rgba(16,185,129,0.3)" },
};

const CATEGORY_COLORS: Record<string, string> = {
 theme: "from-blue-500 to-cyan-500",
 ki: "from-purple-500 to-pink-500",
 frame: "from-yellow-500 to-orange-500",
 boost: "from-green-500 to-emerald-500",
};

export default function ShopPage() {
 // React Query for automatic caching & refetch
 const { data: shopData, isLoading: loading, isError: error, refetch: refetchShop } = useShopItems();
 const shopResult = shopData as { items?: ShopItem[]; user_xp?: number } | undefined;
 const [items, setItems] = useState<ShopItem[]>([]);
 const [userXp, setUserXp] = useState(0);
 const [buying, setBuying] = useState<string | null>(null);
 const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
 const [filter, setFilter] = useState<string>("all");

 // Sync React Query data to local state for optimistic updates
 useState(() => {
 if (shopResult?.items) setItems(shopResult.items);
 if (shopResult?.user_xp) setUserXp(shopResult.user_xp);
 });

 const buyItem = async (itemId: string) => {
 setBuying(itemId);
 setMessage(null);
 try {
 const data = await shopApi.buy(itemId);
 setMessage({ text: data.message || "Erfolgreich gekauft!", type: "success" });
 setUserXp(data.remaining_xp);
 setItems((prev) =>
 prev.map((i) => (i.id === itemId ? { ...i, unlocked: true, can_afford: data.remaining_xp >= i.price } : { ...i, can_afford: data.remaining_xp >= i.price }))
 );
 // Auto-hide message
 setTimeout(() => setMessage(null), 3000);
 } catch (e: unknown) {
 const err = e as Error;
 setMessage({ text: err.message || "Fehler beim Kauf", type: "error" });
 setTimeout(() => setMessage(null), 4000);
 }
 setBuying(null);
 };

 const categories = [...new Set(items.map((i) => i.category))];
 const filteredItems = filter === "all" ? items : items.filter((i) => i.category === filter);

 if (loading) {
 return (
 <div className="p-6 max-w-4xl mx-auto space-y-4">
 <div className="animate-pulse space-y-4">
 <div className="h-12 rounded-xl w-48" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 <div className="flex gap-2">
 {[1,2,3,4].map(i => (
 <div key={i} className="h-10 w-20 rounded-lg" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 ))}
 </div>
 <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
 {[1,2,3,4,5,6].map(i => (
 <div key={i} className="h-44 rounded-2xl" style={{ background: "rgba(var(--surface-rgb),0.5)" }} />
 ))}
 </div>
 </div>
 </div>
 );
 }

 if (error) {
 return (
 <div className="p-6 max-w-4xl mx-auto text-center py-20">
 <div className="text-4xl mb-4">🛒</div>
 <p className="text-foreground font-bold text-lg mb-2">Shop nicht erreichbar</p>
 <p className="text-muted-foreground mb-4">Die Shop-Daten konnten nicht geladen werden.</p>
 <button onClick={() => refetchShop()} className="px-4 py-2 rounded-xl text-sm font-bold text-white" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
 Erneut versuchen
 </button>
 </div>
 );
 }

 return (
 <motion.div
 initial={{ opacity: 0, y: 12 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ duration: 0.35 }}
 className="p-6 max-w-4xl mx-auto pb-20">
 <div className="flex items-center justify-between mb-6">
 <div>
 <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
 <ShoppingBag className="w-6 h-6" />
 Belohnungs-Shop
 </h1>
 <p className="text-muted-foreground">Gib deine XP für Themes, KI-Stile und Boosts aus</p>
 </div>
 <div className="text-right px-4 py-2 rounded-2xl" style={{ background: "rgba(234,179,8,0.1)", border: "1px solid rgba(234,179,8,0.3)" }}>
 <p className="text-3xl font-bold text-yellow-500">{userXp}</p>
 <p className="text-xs text-muted-foreground">Verfügbare XP</p>
 </div>
 </div>

 {/* Toast Message */}
 <AnimatePresence>
 {message && (
 <motion.div
 initial={{ opacity: 0, y: -10 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -10 }}
 className="mb-4 p-3 rounded-xl text-sm font-medium"
 style={{
 background: message.type === "success" ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
 border: `1px solid ${message.type === "success" ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
 color: message.type === "success" ? "#10b981" : "#ef4444",
 }}>
 {message.type === "success" ? "✓ " : "✗ "}{message.text}
 </motion.div>
 )}
 </AnimatePresence>

 {/* Category Filter */}
 <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
 <button
 onClick={() => setFilter("all")}
 className="px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all"
 style={{
 background: filter === "all" ? "linear-gradient(135deg, #6366f1, #8b5cf6)" : "rgba(var(--surface-rgb),0.5)",
 color: filter === "all" ? "#fff" : "var(--muted-foreground)",
 border: filter === "all" ? "1px solid rgba(99,102,241,0.5)" : "1px solid rgba(var(--surface-rgb),0.8)",
 }}
 >
 Alle
 </button>
 {categories.map((cat) => (
 <button
 key={cat}
 onClick={() => setFilter(cat)}
 className="px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all"
 style={{
 background: filter === cat ? "linear-gradient(135deg, #6366f1, #8b5cf6)" : "rgba(var(--surface-rgb),0.5)",
 color: filter === cat ? "#fff" : "var(--muted-foreground)",
 border: filter === cat ? "1px solid rgba(99,102,241,0.5)" : "1px solid rgba(var(--surface-rgb),0.8)",
 }}
 >
 {CATEGORY_LABELS[cat] || cat}
 </button>
 ))}
 </div>

 {/* Empty state */}
 {filteredItems.length === 0 && (
 <div className="text-center py-16">
 <div className="text-4xl mb-3">🏪</div>
 <p className="text-foreground font-bold">Keine Items in dieser Kategorie</p>
 <p className="text-muted-foreground text-sm">Wähle eine andere Kategorie oder schau später vorbei.</p>
 </div>
 )}

 {/* Items Grid */}
 <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
 {filteredItems.map((item, i) => {
 const catStyle = CATEGORY_GRADIENT_STYLES[item.category] || { bg: "rgba(var(--surface-rgb),0.4)", border: "rgba(var(--surface-rgb),0.8)" };
 return (
 <motion.div
 key={item.id}
 initial={{ opacity: 0, y: 15 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: i * 0.04 }}
 whileHover={{ scale: 1.02, y: -2 }}
 className="relative rounded-2xl overflow-hidden"
 style={{
 background: item.unlocked ? "rgba(16,185,129,0.08)" : catStyle.bg,
 border: item.unlocked ? "1px solid rgba(16,185,129,0.3)" : `1px solid ${catStyle.border}`,
 }}
 >
 {/* Gradient header */}
 <div className={`h-1.5 bg-gradient-to-r ${CATEGORY_COLORS[item.category] || "from-gray-400 to-gray-500"}`} />

 <div className="p-4">
 <div className="flex items-start justify-between mb-3">
 <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${CATEGORY_COLORS[item.category] || "from-gray-400 to-gray-500"} flex items-center justify-center text-white`}>
 {ICON_MAP[item.icon] || <ShoppingBag className="w-6 h-6" />}
 </div>
 {item.unlocked && (
 <span className="flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full" style={{ background: "rgba(16,185,129,0.15)", color: "#10b981" }}>
 <Check className="w-3 h-3" />
 Freigeschaltet
 </span>
 )}
 </div>

 <h3 className="font-semibold text-foreground mb-1">{item.name}</h3>
 <p className="text-xs text-muted-foreground mb-3">
 {CATEGORY_LABELS[item.category] || item.category}
 </p>

 <div className="flex items-center justify-between">
 <span className="text-lg font-bold text-yellow-500">{item.price} XP</span>
 {!item.unlocked && (
 <motion.button
 whileHover={{ scale: 1.05 }}
 whileTap={{ scale: 0.95 }}
 disabled={!item.can_afford || buying === item.id}
 onClick={() => buyItem(item.id)}
 className="px-4 py-2 rounded-xl text-sm font-bold text-white disabled:opacity-50 transition-all"
 style={{
 background: item.can_afford
 ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
 : "rgba(var(--surface-rgb),0.6)",
 color: item.can_afford ? "#fff" : "var(--muted-foreground)",
 }}
 >
 {buying === item.id ? (
 <Loader2 className="w-4 h-4 animate-spin" />
 ) : item.can_afford ? (
 "Kaufen"
 ) : (
 "Zu wenig XP"
 )}
 </motion.button>
 )}
 </div>
 </div>
 </motion.div>
 );
 })}
 </div>
 </motion.div>
 );
}
