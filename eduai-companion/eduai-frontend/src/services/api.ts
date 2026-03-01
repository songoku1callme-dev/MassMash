const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const token = localStorage.getItem("eduai_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

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
  }) => request<{ access_token: string; user: User }>("/api/auth/register", { method: "POST", body: data }),

  login: (data: { username: string; password: string }) =>
    request<{ access_token: string; user: User }>("/api/auth/login", { method: "POST", body: data }),

  me: () => request<User>("/api/auth/me"),

  update: (data: { full_name?: string; school_grade?: string; school_type?: string; preferred_language?: string }) =>
    request<User>("/api/auth/me", { method: "PUT", body: data }),
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
