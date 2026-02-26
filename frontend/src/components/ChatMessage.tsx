import { Bot, User, Search, Code, FolderOpen, FileText, Wrench } from "lucide-react";
import type { ChatMessage as ChatMessageType, ToolCall, ToolResult } from "@/types";

interface Props {
  message: ChatMessageType;
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
}

function formatContent(content: string): string {
  // Simple markdown-like formatting
  return content
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');
}

const TOOL_ICONS: Record<string, typeof Search> = {
  web_search: Search,
  code_execution: Code,
  file_list: FolderOpen,
  file_read: FileText,
};

const TOOL_LABELS: Record<string, string> = {
  web_search: "Web-Suche",
  code_execution: "Code-Ausfuehrung",
  file_list: "Dateien auflisten",
  file_read: "Datei lesen",
};

function ToolCallBadge({ toolCall }: { toolCall: ToolCall }) {
  const Icon = TOOL_ICONS[toolCall.name] || Wrench;
  const label = TOOL_LABELS[toolCall.name] || toolCall.name;
  const args = Object.entries(toolCall.arguments)
    .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(", ");

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-900/30 border border-amber-700/40 rounded-lg text-xs text-amber-300">
      <Icon size={14} className="flex-shrink-0" />
      <span className="font-medium">{label}</span>
      {args && (
        <span className="text-amber-400/70 truncate max-w-xs">({args})</span>
      )}
    </div>
  );
}

function ToolResultBlock({ result }: { result: ToolResult }) {
  const Icon = TOOL_ICONS[result.name] || Wrench;
  const label = TOOL_LABELS[result.name] || result.name;

  return (
    <div className="mt-2 border border-zinc-700/50 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800/80 text-xs text-zinc-400">
        <Icon size={12} />
        <span>{label} - Ergebnis</span>
      </div>
      <pre className="px-3 py-2 text-xs text-zinc-300 bg-zinc-900/50 overflow-x-auto whitespace-pre-wrap max-h-64 overflow-y-auto">
        {result.result}
      </pre>
    </div>
  );
}

export function ChatMessageItem({ message, toolCalls, toolResults }: Props) {
  const isUser = message.role === "user";
  const hasTools = (toolCalls && toolCalls.length > 0) || (toolResults && toolResults.length > 0);

  return (
    <div className={`flex gap-3 px-4 py-4 ${isUser ? "bg-zinc-900/30" : "bg-zinc-900/60"}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
          isUser ? "bg-blue-600" : "bg-emerald-600"
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-zinc-500 mb-1 font-medium">
          {isUser ? "Du" : "Assistent"}
        </p>

        {/* Tool call badges */}
        {hasTools && toolCalls && toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {toolCalls.map((tc) => (
              <ToolCallBadge key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Tool results */}
        {hasTools && toolResults && toolResults.length > 0 && (
          <div className="mb-3">
            {toolResults.map((tr) => (
              <ToolResultBlock key={tr.tool_call_id} result={tr} />
            ))}
          </div>
        )}

        {/* Message content */}
        <div
          className="text-sm text-zinc-200 leading-relaxed prose prose-invert max-w-none"
          dangerouslySetInnerHTML={{ __html: formatContent(message.content) }}
        />
      </div>
    </div>
  );
}
