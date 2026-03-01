import { jwtDecode } from "jwt-decode";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  skipAuth?: boolean;
}

interface JwtPayload {
  sub: string;
  exp: number;
  type: string;
}

// --- Token helpers ---

export function getAccessToken(): string | null {
  return localStorage.getItem("eduai_token");
}

export function getRefreshToken(): string | null {
  return localStorage.getItem("eduai_refresh_token");
}

export function setTokens(access: string, refresh?: string): void {
  localStorage.setItem("eduai_token", access);
  if (refresh) {
    localStorage.setItem("eduai_refresh_token", refresh);
  }
}

export function clearTokens(): void {
  localStorage.removeItem("eduai_token");
  localStorage.removeItem("eduai_refresh_token");
}

/** Returns true if the access token expires within `bufferSec` seconds. */
export function isTokenExpiringSoon(bufferSec: number = 120): boolean {
  const token = getAccessToken();
  if (!token) return true;
  try {
    const { exp } = jwtDecode<JwtPayload>(token);
    return Date.now() / 1000 > exp - bufferSec;
  } catch {
    return true;
  }
}

// --- Token refresh logic ---

let refreshPromise: Promise<string> | null = null;

/** Calls /api/auth/refresh and stores the new access token. */
export async function refreshAccessToken(): Promise<string> {
  // Deduplicate concurrent refresh calls
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) throw new Error("No refresh token");

    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) throw new Error("Refresh failed");
    const data: { access_token: string } = await res.json();
    setTokens(data.access_token);
    return data.access_token;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

// --- Core request function with auto-refresh on 401 ---

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  let token = getAccessToken();

  // Proactively refresh if token is expiring soon (within 2 min)
  if (!options.skipAuth && token && isTokenExpiringSoon(120)) {
    try {
      token = await refreshAccessToken();
    } catch {
      // Will try with current token; 401 handler below is the safety net
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  if (token && !options.skipAuth) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response = await fetch(`${API_URL}${endpoint}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  // On 401, try refreshing once and retry the original request
  if (response.status === 401 && !options.skipAuth) {
    try {
      const newToken = await refreshAccessToken();
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(`${API_URL}${endpoint}`, {
        method: options.method || "GET",
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
      });
    } catch {
      // Refresh failed — clear tokens and let the error propagate
      clearTokens();
      throw new Error("Session expired. Please log in again.");
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }

  return response.json();
}

// Auth
export const authApi = {
  register: (data: {
    email: string;
    username: string;
    password: string;
    full_name: string;
    school_grade: string;
    school_type: string;
    preferred_language: string;
  }) => request<{ access_token: string; refresh_token: string; user: User }>("/api/auth/register", { method: "POST", body: data }),

  login: (data: { username: string; password: string }) =>
    request<{ access_token: string; refresh_token: string; user: User }>("/api/auth/login", { method: "POST", body: data }),

  me: () => request<User>("/api/auth/me"),

  update: (data: { full_name?: string; school_grade?: string; school_type?: string; preferred_language?: string }) =>
    request<User>("/api/auth/me", { method: "PUT", body: data }),

  refresh: () => refreshAccessToken(),
};

// Chat
export const chatApi = {
  send: (data: {
    message: string;
    session_id?: number | null;
    subject?: string;
    language?: string;
    detail_level?: string;
  }) => request<ChatResponse>("/api/chat", { method: "POST", body: data }),

  sessions: () => request<ChatSession[]>("/api/chat/sessions"),

  session: (id: number) => request<ChatSessionDetail>(`/api/chat/sessions/${id}`),

  deleteSession: (id: number) => request<void>(`/api/chat/sessions/${id}`, { method: "DELETE" }),
};

// Quiz
export const quizApi = {
  generate: (data: {
    subject: string;
    difficulty?: string;
    num_questions?: number;
    quiz_type?: string;
    language?: string;
    topic?: string;
  }) => request<QuizData>("/api/quiz/generate", { method: "POST", body: data }),

  submit: (data: {
    quiz_id: string;
    subject: string;
    answers: { question_id: number; user_answer: string }[];
    difficulty?: string;
  }) => request<QuizResult>("/api/quiz/submit", { method: "POST", body: data }),

  checkAnswer: (data: {
    quiz_id: string;
    question_id: number;
    user_answer: string;
  }) => request<AnswerCheckResult>("/api/quiz/check-answer", { method: "POST", body: data }),

  history: () => request<QuizHistoryItem[]>("/api/quiz/history"),
};

// Learning
export const learningApi = {
  subjects: () => request<Subject[]>("/api/subjects"),
  profile: () => request<LearningProfile[]>("/api/profile"),
  progress: () => request<Progress>("/api/progress"),
  learningPath: (subject: string) => request<LearningPath>(`/api/learning-path/${subject}`),
};

// RAG
export const ragApi = {
  query: (data: { query: string; top_k?: number; filter_metadata?: Record<string, string> }) =>
    request<RAGQueryResponse>("/api/rag/query", { method: "POST", body: data }),

  indexDocument: (data: { content: string; doc_id?: string; metadata?: Record<string, string> }) =>
    request<{ doc_id: string; chunks_created: number }>("/api/rag/index", { method: "POST", body: data }),

  uploadFile: async (file: File, subject: string = "general", language: string = "de", source: string = ""): Promise<{ doc_id: string; chunks_created: number }> => {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append("file", file);
    formData.append("subject", subject);
    formData.append("language", language);
    formData.append("source", source);

    const res = await fetch(`${API_URL}/api/rag/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  },

  listDocuments: () => request<RAGDocument[]>("/api/rag/documents"),

  deleteDocument: (docId: string) =>
    request<{ message: string }>(`/api/rag/documents/${docId}`, { method: "DELETE" }),

  stats: () => request<RAGStats>("/api/rag/stats"),

  seed: () => request<{ message: string; documents_indexed: number }>("/api/rag/seed", { method: "POST" }),
};

// Types
export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  school_grade: string;
  school_type: string;
  preferred_language: string;
  created_at: string;
}

export interface ChatResponse {
  response: string;
  session_id: number;
  subject: string;
  detected_subject: string | null;
  proficiency_level: string;
}

export interface ChatSession {
  id: number;
  subject: string;
  title: string;
  language: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  subject?: string;
  timestamp?: string;
}

export interface Subject {
  id: string;
  name: string;
  name_de: string;
  icon: string;
  description: string;
  description_de: string;
  topics: string[];
}

export interface QuizData {
  quiz_id: string;
  subject: string;
  difficulty: string;
  questions: QuizQuestion[];
}

export interface QuizQuestion {
  id: number;
  question: string;
  options: string[] | null;
  difficulty: string;
  topic: string;
}

export interface AnswerCheckResult {
  correct: boolean;
  correct_answer: string;
  explanation: string;
}

export interface QuizResult {
  total_questions: number;
  correct_answers: number;
  score: number;
  feedback: string;
  new_proficiency: string;
}

export interface QuizHistoryItem {
  id: number;
  subject: string;
  quiz_type: string;
  total_questions: number;
  correct_answers: number;
  score: number;
  difficulty: string;
  completed_at: string;
}

export interface LearningProfile {
  subject: string;
  proficiency_level: string;
  mastery_score: number;
  topics_completed: number;
  total_questions_answered: number;
  correct_answers: number;
  accuracy: number;
  last_active: string;
}

export interface Progress {
  profiles: LearningProfile[];
  total_sessions: number;
  total_quizzes: number;
  recent_activity: ActivityItem[];
  streak_days: number;
}

export interface ActivityItem {
  activity_type: string;
  subject: string;
  description: string;
  created_at: string;
}

export interface LearningPath {
  subject: string;
  current_level: string;
  recommended_topics: LearningPathTopic[];
  next_milestone: string;
}

export interface LearningPathTopic {
  topic: string;
  subject: string;
  difficulty: string;
  mastered: boolean;
  recommended: boolean;
  description: string;
}

export interface RAGSearchResult {
  doc_id: string;
  chunk_text: string;
  score: number;
  metadata: Record<string, string>;
  source: string;
}

export interface RAGQueryResponse {
  results: RAGSearchResult[];
  query: string;
}

export interface RAGDocument {
  doc_id: string;
  metadata: Record<string, string>;
  created_at: string;
}

export interface RAGStats {
  total_documents: number;
  total_chunks: number;
  embedding_model: string;
  embedding_dim: number;
  chunk_size: number;
}
