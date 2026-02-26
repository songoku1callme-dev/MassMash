import { Plus, MessageSquare, Trash2, Settings } from "lucide-react";
import type { Conversation } from "@/types";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onOpenSettings: () => void;
}

export function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onOpenSettings,
}: Props) {
  return (
    <div className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800">
        <h1 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
          <span className="text-xl">🤖</span> MassMash AI
        </h1>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          Neuer Chat
        </button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        {conversations.length === 0 ? (
          <p className="text-zinc-600 text-xs text-center mt-4">
            Noch keine Unterhaltungen
          </p>
        ) : (
          <div className="space-y-1">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  activeId === conv.id
                    ? "bg-zinc-800 text-zinc-100"
                    : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
                }`}
                onClick={() => onSelect(conv.id)}
              >
                <MessageSquare size={14} className="flex-shrink-0" />
                <span className="flex-1 text-sm truncate">{conv.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-all"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Settings Button */}
      <div className="p-3 border-t border-zinc-800">
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center gap-2 px-3 py-2 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg text-sm transition-colors"
        >
          <Settings size={16} />
          Einstellungen
        </button>
      </div>
    </div>
  );
}
