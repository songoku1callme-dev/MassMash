import { MessageSquare, Code, FileSearch, Gamepad2, Cpu } from "lucide-react";
import type { ChatMode, Theme } from "@/types";

interface Props {
  mode: ChatMode;
  onChange: (mode: ChatMode) => void;
  theme?: Theme;
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
  {
    value: "gaming_optimizer",
    label: "Gaming Optimizer",
    icon: <Gamepad2 size={16} />,
    desc: "Fortnite/Warzone/Minecraft Tuning, Monitor, Netzwerk, AMD Tweaks",
  },
  {
    value: "hardware_advisor",
    label: "Hardware Advisor",
    icon: <Cpu size={16} />,
    desc: "CPU/GPU-Kaufberatung, PC-Bau, Upgrade-Pfade",
  },
];

export function ModeSelector({ mode, onChange, theme = "dark" }: Props) {
  const isDark = theme === "dark";

  return (
    <div className={`flex gap-1 p-1 rounded-lg ${isDark ? "bg-zinc-900" : "bg-gray-100"}`}>
      {modes.map((m) => (
        <button
          key={m.value}
          onClick={() => onChange(m.value)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            mode === m.value
              ? isDark ? "bg-zinc-700 text-zinc-100 shadow-sm" : "bg-white text-gray-900 shadow-sm"
              : isDark ? "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800" : "text-gray-500 hover:text-gray-700 hover:bg-gray-200"
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
