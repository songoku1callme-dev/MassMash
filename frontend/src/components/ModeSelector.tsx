import { MessageSquare, Code, FileSearch } from "lucide-react";
import type { ChatMode } from "@/types";

interface Props {
  mode: ChatMode;
  onChange: (mode: ChatMode) => void;
}

const modes: { value: ChatMode; label: string; icon: React.ReactNode; desc: string }[] = [
  {
    value: "normal",
    label: "Normal Chat",
    icon: <MessageSquare size={16} />,
    desc: "Allgemeiner Assistent",
  },
  {
    value: "programmer",
    label: "Programmier-Assistent",
    icon: <Code size={16} />,
    desc: "Code-Hilfe & Debugging",
  },
  {
    value: "document_analysis",
    label: "Dokumenten-Analyse",
    icon: <FileSearch size={16} />,
    desc: "Texte analysieren & zusammenfassen",
  },
];

export function ModeSelector({ mode, onChange }: Props) {
  return (
    <div className="flex gap-1 p-1 bg-zinc-900 rounded-lg">
      {modes.map((m) => (
        <button
          key={m.value}
          onClick={() => onChange(m.value)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            mode === m.value
              ? "bg-zinc-700 text-zinc-100 shadow-sm"
              : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
          }`}
          title={m.desc}
        >
          {m.icon}
          <span className="hidden sm:inline">{m.label}</span>
        </button>
      ))}
    </div>
  );
}
