/** Types for the AI Desktop Client frontend. */

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  mode: string;
  system_prompt?: string;
  file_context?: string;
}

export interface ChatResponse {
  message: ChatMessage;
  provider: string;
  model: string;
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
}

export type ChatMode = "normal" | "programmer" | "document_analysis";

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  mode: ChatMode;
  fileContext?: string;
  createdAt: number;
}
