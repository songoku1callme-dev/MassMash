/** API service for communicating with the backend. */

import type {
  ChatRequest,
  ChatResponse,
  FileUploadResponse,
  SettingsData,
  SettingsUpdate,
  ToolInfo,
} from "@/types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function sendChat(data: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function uploadFile(file: File): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/files/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function getSettings(): Promise<SettingsData> {
  return request<SettingsData>("/api/settings/");
}

export async function updateSettings(
  data: SettingsUpdate
): Promise<SettingsData> {
  return request<SettingsData>("/api/settings/", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function healthCheck(): Promise<{ status: string }> {
  return request<{ status: string }>("/healthz");
}

export async function listTools(): Promise<ToolInfo[]> {
  return request<ToolInfo[]>("/api/tools/");
}
