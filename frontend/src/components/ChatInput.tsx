import { useState, useRef, type KeyboardEvent } from "react";
import { Send, Paperclip, X, FileText } from "lucide-react";
import { uploadFile } from "@/services/api";
import type { FileUploadResponse } from "@/types";

interface Props {
  onSend: (message: string, fileContext?: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [input, setInput] = useState("");
  const [uploadedFile, setUploadedFile] = useState<FileUploadResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, uploadedFile?.extracted_text);
    setInput("");
    setUploadedFile(null);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError("");

    try {
      const result = await uploadFile(file);
      setUploadedFile(result);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload fehlgeschlagen");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="border-t border-zinc-800 bg-zinc-900/80 p-4">
      {/* File attachment indicator */}
      {uploadedFile && (
        <div className="flex items-center gap-2 mb-2 px-3 py-2 bg-zinc-800 rounded-lg text-sm">
          <FileText size={14} className="text-emerald-400" />
          <span className="text-zinc-300 flex-1 truncate">
            {uploadedFile.filename} ({uploadedFile.char_count.toLocaleString()} Zeichen)
          </span>
          <button
            onClick={() => setUploadedFile(null)}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {uploadError && (
        <div className="mb-2 px-3 py-2 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-400">
          {uploadError}
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* File upload button */}
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading || disabled}
          className="flex-shrink-0 p-2.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded-lg transition-colors disabled:opacity-50"
          title="Datei hochladen (PDF, TXT, DOCX)"
        >
          <Paperclip size={18} />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.pdf,.docx"
          onChange={handleFileUpload}
          className="hidden"
        />

        {/* Text input */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={uploading ? "Datei wird hochgeladen..." : "Nachricht eingeben... (Shift+Enter für neue Zeile)"}
          disabled={disabled || uploading}
          rows={1}
          className="flex-1 resize-none bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent disabled:opacity-50 max-h-32"
          style={{ minHeight: "42px" }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = "42px";
            target.style.height = Math.min(target.scrollHeight, 128) + "px";
          }}
        />

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={!input.trim() || disabled || uploading}
          className="flex-shrink-0 p-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:hover:bg-blue-600"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
