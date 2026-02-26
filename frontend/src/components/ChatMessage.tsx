import { Bot, User } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/types";

interface Props {
  message: ChatMessageType;
}

function formatContent(content: string): string {
  // Simple markdown-like formatting
  return content
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');
}

export function ChatMessageItem({ message }: Props) {
  const isUser = message.role === "user";

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
        <div
          className="text-sm text-zinc-200 leading-relaxed prose prose-invert max-w-none"
          dangerouslySetInnerHTML={{ __html: formatContent(message.content) }}
        />
      </div>
    </div>
  );
}
