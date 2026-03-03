import { useState, useEffect } from "react";
import { marketplaceApi } from "../services/api";
import { Store, Download, Star, Package, BookOpen, Layers, Loader2 } from "lucide-react";

const TYPE_LABELS: Record<string, string> = {
  quiz_set: "Quiz-Set",
  flashcard_deck: "Karteikarten",
  lernplan: "Lernplan",
};

const TYPE_ICONS: Record<string, React.ReactNode> = {
  quiz_set: <BookOpen className="w-4 h-4" />,
  flashcard_deck: <Layers className="w-4 h-4" />,
  lernplan: <Package className="w-4 h-4" />,
};

export default function MarketplacePage() {
  /* eslint-disable @typescript-eslint/no-explicit-any */
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    loadItems();
  }, [filter]);

  const loadItems = async () => {
    setLoading(true);
    try {
      const data = await marketplaceApi.items(filter || undefined);
      setItems(data.items);
    } catch {
      // Error
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (itemId: number) => {
    try {
      await marketplaceApi.download(itemId);
      // Refresh to update download count
      loadItems();
    } catch {
      // Error
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Store className="w-7 h-7 text-emerald-600" />
          Lehrer-Marketplace
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Quiz-Sets, Karteikarten und Lernpläne von Lehrern — für Schüler gemacht!
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-2">
        {[
          { value: "", label: "Alle" },
          { value: "quiz_set", label: "Quiz-Sets" },
          { value: "flashcard_deck", label: "Karteikarten" },
          { value: "lernplan", label: "Lernpläne" },
        ].map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === f.value
                ? "bg-emerald-600 text-white"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <Store className="w-16 h-16 mx-auto mb-4 opacity-30" />
          <p className="text-lg">Noch keine Items im Marketplace</p>
          <p className="text-sm mt-1">Lehrer können hier bald ihre Inhalte verkaufen.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item: any) => (
            <div key={item.id} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-md transition-all">
              {/* Header */}
              <div className="p-4 border-b border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-2 mb-2">
                  <span className="p-1.5 bg-emerald-50 dark:bg-emerald-900/30 rounded-lg text-emerald-600">
                    {TYPE_ICONS[item.item_type] || <Package className="w-4 h-4" />}
                  </span>
                  <span className="text-xs text-gray-400 font-medium">
                    {TYPE_LABELS[item.item_type] || item.item_type}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white">{item.title}</h3>
                {item.description && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">{item.description}</p>
                )}
              </div>

              {/* Stats */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <Download className="w-3 h-3" /> {item.downloads}
                  </span>
                  {item.rating > 0 && (
                    <span className="flex items-center gap-1">
                      <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" /> {item.rating}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {item.price_cents > 0 ? (
                    <span className="text-sm font-bold text-emerald-600">{item.price_display} EUR</span>
                  ) : (
                    <span className="text-sm font-medium text-green-600">Gratis</span>
                  )}
                  <button
                    onClick={() => handleDownload(item.id)}
                    className="p-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Creator */}
              <div className="px-4 pb-3">
                <p className="text-xs text-gray-400">von {item.creator_name}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
  /* eslint-enable @typescript-eslint/no-explicit-any */
}
