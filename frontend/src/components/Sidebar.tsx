import { Plus, MessageSquare, Trash2, Settings, Download, Upload, Sun, Moon } from "lucide-react";
import type { Conversation, Theme } from "@/types";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onOpenSettings: () => void;
  onExport: () => void;
  onImport: () => void;
  theme: Theme;
  onToggleTheme: () => void;
}

export function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onOpenSettings,
  onExport,
  onImport,
  theme,
  onToggleTheme,
}: Props) {
  const isDark = theme === "dark";

  return (
    <div className={`w-64 ${isDark ? "bg-zinc-900 border-r border-zinc-800" : "bg-white border-r border-gray-200"} flex flex-col h-full`}>
      {/* Header */}
      <div className={`p-4 border-b ${isDark ? "border-zinc-800" : "border-gray-200"} flex items-center justify-between`}>
        <h1 className={`text-lg font-bold ${isDark ? "text-zinc-100" : "text-gray-900"} flex items-center gap-2`}>
          <span className="text-xl">🤖</span> MassMash AI
        </h1>
        <button
          onClick={onToggleTheme}
          className={`p-1.5 rounded-lg transition-colors ${isDark ? "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}
          title={isDark ? "Light Mode" : "Dark Mode"}
        >
          {isDark ? <Sun size={16} /> : <Moon size={16} />}
        </button>
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
          <p className={`text-xs text-center mt-4 ${isDark ? "text-zinc-600" : "text-gray-400"}`}>
            Noch keine Unterhaltungen
          </p>
        ) : (
          <div className="space-y-1">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  activeId === conv.id
                    ? isDark ? "bg-zinc-800 text-zinc-100" : "bg-blue-50 text-blue-900"
                    : isDark ? "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200" : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
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

      {/* Export / Import */}
      <div className={`px-3 py-2 border-t ${isDark ? "border-zinc-800" : "border-gray-200"} flex gap-1`}>
        <button
          onClick={onExport}
          className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-xs transition-colors ${isDark ? "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}
          title="Chats exportieren (JSON)"
        >
          <Download size={14} />
          Export
        </button>
        <button
          onClick={onImport}
          className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-xs transition-colors ${isDark ? "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}
          title="Chats importieren (JSON)"
        >
          <Upload size={14} />
          Import
        </button>
      </div>

      {/* Settings Button */}
      <div className={`p-3 border-t ${isDark ? "border-zinc-800" : "border-gray-200"}`}>
        <button
          onClick={onOpenSettings}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${isDark ? "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}
        >
          <Settings size={16} />
          Einstellungen
        </button>
      </div>
    </div>
  );
}
