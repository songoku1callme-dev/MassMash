/** Types for the AI Desktop Client frontend. */

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResult {
  tool_call_id: string;
  name: string;
  result: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  mode: string;
  system_prompt?: string;
  file_context?: string;
  enable_tools?: boolean;
}

export interface ChatResponse {
  message: ChatMessage;
  provider: string;
  model: string;
  tool_calls: ToolCall[];
  tool_results: ToolResult[];
}

export interface ToolInfo {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface FileUploadResponse {
  filename: string;
  extracted_text: string;
  char_count: number;
}

export interface SettingsData {
  llm_provider: string;
  openai_api_key_set: boolean;
  openai_model: string;
  openai_base_url: string;
  gemini_api_key_set: boolean;
  gemini_model: string;
  anthropic_api_key_set: boolean;
  anthropic_model: string;
  ollama_base_url: string;
  ollama_model: string;
}

export interface SettingsUpdate {
  llm_provider?: string;
  openai_api_key?: string;
  openai_model?: string;
  openai_base_url?: string;
  gemini_api_key?: string;
  gemini_model?: string;
  anthropic_api_key?: string;
  anthropic_model?: string;
  ollama_base_url?: string;
  ollama_model?: string;
}

export interface OllamaModelInfo {
  name: string;
  size: number;
  digest: string;
}

export interface OllamaStatus {
  available: boolean;
  base_url: string;
  models: OllamaModelInfo[];
}

export type ChatMode = "normal" | "programmer" | "document_analysis" | "gaming_optimizer" | "hardware_advisor";

/** Theme preference. */
export type Theme = "dark" | "light";

/** Tool data attached to a specific message index in a conversation. */
export interface MessageToolData {
  toolCalls: ToolCall[];
  toolResults: ToolResult[];
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  mode: ChatMode;
  fileContext?: string;
  createdAt: number;
  /** Map from message index to tool data (only for assistant messages that used tools). */
  toolDataByIndex?: Record<number, MessageToolData>;
}

/** Voice I/O settings persisted in localStorage. */
export interface VoiceSettings {
  /** Speech synthesis rate (0.5 – 2.0, default 1). */
  rate: number;
  /** Speech synthesis pitch (0.0 – 2.0, default 1). */
  pitch: number;
  /** SpeechSynthesis voice URI (empty = browser default). */
  voiceURI: string;
  /** Auto-read assistant messages aloud. */
  autoRead: boolean;
  /** Speech recognition language (BCP-47, e.g. "de-DE"). */
  recognitionLang: string;
}
