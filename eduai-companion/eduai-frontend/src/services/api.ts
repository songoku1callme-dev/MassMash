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
    personality_id?: number;
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
    thema_custom?: string;
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

  topics: (subject?: string) =>
    request<QuizTopicsResponse>(subject ? `/api/quiz/topics?subject=${subject}` : "/api/quiz/topics"),

  personalities: () => request<KIPersonalitiesResponse>("/api/quiz/personalities"),

  setPersonality: (personalityId: number) =>
    request<{ personality_id: number; name: string }>(`/api/quiz/personality?personality_id=${personalityId}`, { method: "PUT" }),
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

// OCR
export const ocrApi = {
  solveImage: async (file: File): Promise<OCRResult> => {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_URL}/api/ocr/solve-image`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "OCR failed" }));
      throw new Error(err.detail || "OCR failed");
    }
    return res.json();
  },

  solveText: async (equation: string): Promise<OCRResult> => {
    const token = getAccessToken();
    const formData = new URLSearchParams();
    formData.append("equation", equation);

    const res = await fetch(`${API_URL}/api/ocr/solve-text`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData.toString(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Solve failed" }));
      throw new Error(err.detail || "Solve failed");
    }
    return res.json();
  },
};

// Types
export interface OCRResult {
  ocr_text: string;
  equations: string[];
  results: OCREquationResult[];
  formatted_response: string;
}

export interface OCREquationResult {
  equation: string;
  variable: string | null;
  solution: string[] | string | null;
  steps: string[];
  latex: string | null;
  solution_latex?: string[];
  error?: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  school_grade: string;
  school_type: string;
  preferred_language: string;
  is_pro: boolean;
  subscription_tier: string;
  ki_personality_id: number;
  ki_personality_name: string;
  avatar_url: string;
  auth_provider: string;
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
  weak_topic_detected?: string;
  weak_topic_suggestion?: string;
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

// Stripe
export interface QuizTopic {
  id: number;
  name: string;
  tier: string;
  difficulty_range: number[];
}

export interface QuizTopicsResponse {
  subjects?: Record<string, QuizTopic[]>;
  subject?: string;
  topics?: QuizTopic[];
  tier: string;
  total_topics?: number;
}

export interface KIPersonality {
  id: number;
  name: string;
  emoji: string;
  tier: string;
  temperature: number;
  preview: string;
  system_prompt: string;
  accessible: boolean;
}

export interface KIPersonalitiesResponse {
  personalities: KIPersonality[];
  current_id: number;
  tier: string;
}

export interface StripeConfig {
  enabled: boolean;
  publishable_key: string;
  pro_price_eur: string;
}

export interface SubscriptionStatus {
  is_pro: boolean;
  subscription_tier: string;
  stripe_customer_id: string;
  pro_since: string;
  stripe_enabled: boolean;
}

export const stripeApi = {
  config: () => request<StripeConfig>("/api/stripe/config"),
  createCheckout: (data: { success_url: string; cancel_url: string; plan?: string; billing?: string }) =>
    request<{ checkout_url: string; session_id: string }>("/api/stripe/create-checkout", { method: "POST", body: data }),
  subscriptionStatus: () => request<SubscriptionStatus>("/api/stripe/subscription-status"),
};

// Clerk config
export interface ClerkConfig {
  enabled: boolean;
  publishable_key: string;
}

export const clerkApi = {
  config: () => request<ClerkConfig>("/api/auth/clerk-config"),
};

// Memory (User Adaptive Learning)
export interface MemoryFeedbackResponse {
  topic_id: string;
  feedback: number;
  schwach: boolean;
  message: string;
}

export interface WeakTopic {
  topic_id: string;
  subject: string;
  topic_name: string;
  feedback_score: number;
  times_asked: number;
  times_correct: number;
  letzte_frage: string;
}

export interface MemoryStats {
  total_topics_tracked: number;
  weak_topics_count: number;
  strong_topics_count: number;
  by_subject: { subject: string; count: number; weak_count: number }[];
}

export const memoryApi = {
  submitFeedback: (data: { topic_id: string; feedback: number; subject?: string; topic_name?: string }) =>
    request<MemoryFeedbackResponse>(
      `/api/memory/feedback?topic_id=${data.topic_id}&feedback=${data.feedback}&subject=${data.subject || ""}&topic_name=${encodeURIComponent(data.topic_name || "")}`,
      { method: "POST" }
    ),
  weakTopics: (subject?: string) =>
    request<{ weak_topics: WeakTopic[]; count: number }>(
      subject ? `/api/memory/weak-topics?subject=${subject}` : "/api/memory/weak-topics"
    ),
  stats: () => request<MemoryStats>("/api/memory/stats"),
  adaptivePrompt: (subject: string) =>
    request<{ prompt: string; weak_topics: WeakTopic[] }>(`/api/memory/adaptive-prompt?subject=${subject}`),
};

// Abitur Simulation
export interface AbiturSimulation {
  simulation_id: number;
  subject: string;
  duration_minutes: number;
  questions: { id: number; question: string; options: string[]; difficulty: string; topic: string }[];
  status: string;
  start_time: string;
}

export interface AbiturResult {
  simulation_id: number;
  subject: string;
  total_questions: number;
  correct_answers: number;
  score_percent: number;
  note_punkte: number;
  note: string;
  graded_answers: { question_id: number; user_answer: string; correct_answer: string; is_correct: boolean }[];
  status: string;
}

export interface AbiturHistoryItem {
  id: number;
  subject: string;
  duration_minutes: number;
  score: number;
  note_punkte: number;
  note: string;
  status: string;
  created_at: string;
}

export interface StudyPlan {
  plan_id: number;
  subject: string;
  weeks: number;
  plan: { woche: number; thema: string; aufgaben: string[]; tage_pro_woche: number; stunden_pro_tag: number }[];
  weak_topics_included: string[];
}

export interface StudyPlanListItem {
  id: number;
  subject: string;
  week_count: number;
  current_week: number;
  status: string;
  created_at: string;
}

export const abiturApi = {
  start: (data: { subject: string; duration_minutes?: number; num_questions?: number; thema_custom?: string }) =>
    request<AbiturSimulation>(
      `/api/abitur/start?subject=${data.subject}&duration_minutes=${data.duration_minutes || 180}&num_questions=${data.num_questions || 20}${data.thema_custom ? `&thema_custom=${encodeURIComponent(data.thema_custom)}` : ""}`,
      { method: "POST" }
    ),
  pause: (data: { simulation_id: number; elapsed_seconds?: number }) =>
    request<{ simulation_id: number; status: string; elapsed_seconds: number }>(
      `/api/abitur/pause?simulation_id=${data.simulation_id}&elapsed_seconds=${data.elapsed_seconds || 0}`,
      { method: "POST" }
    ),
  resume: (simulation_id: number) =>
    request<{ simulation_id: number; status: string; elapsed_seconds: number; remaining_minutes: number }>(
      `/api/abitur/resume?simulation_id=${simulation_id}`,
      { method: "POST" }
    ),
  submit: (data: { simulation_id: number; answers: { question_id: number; user_answer: string }[] }) =>
    request<AbiturResult>(
      `/api/abitur/submit?simulation_id=${data.simulation_id}`,
      { method: "POST", body: data.answers }
    ),
  history: () => request<{ simulations: AbiturHistoryItem[] }>("/api/abitur/history"),
  createPlan: (data: { subject: string; weeks?: number }) =>
    request<StudyPlan>(
      `/api/abitur/coach/plan?subject=${data.subject}&weeks=${data.weeks || 8}`,
      { method: "POST" }
    ),
  getPlans: () => request<{ plans: StudyPlanListItem[] }>("/api/abitur/coach/plans"),
  getPlanDetail: (planId: number) => request<StudyPlan>(`/api/abitur/coach/plan/${planId}`),
  updateProgress: (planId: number, currentWeek: number) =>
    request<{ plan_id: number; current_week: number; status: string }>(
      `/api/abitur/coach/plan/${planId}/progress?current_week=${currentWeek}`,
      { method: "PUT" }
    ),
};

// Research (Internet Search)
export interface ResearchResult {
  title: string;
  url: string;
  content: string;
  score: number;
}

export interface ResearchResponse {
  query: string;
  enhanced_query: string;
  results: ResearchResult[];
  source_count: number;
  tavily_enabled: boolean;
}

export interface AskWithSourcesResponse {
  answer: string;
  sources: ResearchResult[];
  source_count: number;
  tavily_enabled: boolean;
}

export const researchApi = {
  search: (data: { query: string; subject?: string; max_results?: number }) =>
    request<ResearchResponse>(
      `/api/research/search?query=${encodeURIComponent(data.query)}&subject=${data.subject || ""}&max_results=${data.max_results || 10}`,
      { method: "POST" }
    ),
  askWithSources: (data: { question: string; subject?: string }) =>
    request<AskWithSourcesResponse>(
      `/api/research/ask-with-sources?question=${encodeURIComponent(data.question)}&subject=${data.subject || ""}`,
      { method: "POST" }
    ),
  history: () => request<{ results: { id: number; query: string; source_count: number; created_at: string }[] }>("/api/research/history"),
};

// Gamification
export interface GamificationProfile {
  xp: number;
  level: number;
  level_name: string;
  level_emoji: string;
  xp_to_next_level: number;
  next_level_name: string;
  streak_days: number;
  quizzes_completed: number;
  chats_sent: number;
  abitur_completed: number;
  achievements: { id: string; earned_at: string }[];
  all_achievements: { id: string; name: string; desc: string; emoji: string; xp_reward: number }[];
  all_levels: { level: number; name: string; min_xp: number; emoji: string }[];
}

export interface LeaderboardEntry {
  rank: number;
  name: string;
  xp: number;
  level: number;
  level_name: string;
  streak_days: number;
  is_you: boolean;
}

export const gamificationApi = {
  profile: () => request<GamificationProfile>("/api/gamification/profile"),
  leaderboard: () => request<{ leaderboard: LeaderboardEntry[] }>("/api/gamification/leaderboard"),
  addXp: (xp: number, activity: string) =>
    request<{ xp_gained: number; total_xp: number; level: number; level_name: string }>(
      `/api/gamification/add-xp?xp=${xp}&activity=${activity}`, { method: "POST" }
    ),
};

// Group Chats
export interface GroupChat {
  id: number;
  name: string;
  subject: string;
  member_count: number;
  max_members: number;
  is_member: boolean;
  created_at: string;
}

export interface GroupMessage {
  user_id: number;
  username: string;
  content: string;
  timestamp: string;
}

export const groupsApi = {
  list: () => request<{ groups: GroupChat[] }>("/api/groups/list"),
  create: (name: string, subject: string) =>
    request<{ group_id: number; name: string; subject: string }>(
      `/api/groups/create?name=${encodeURIComponent(name)}&subject=${subject}`, { method: "POST" }
    ),
  join: (groupId: number) =>
    request<{ message: string; group_id: number }>(`/api/groups/${groupId}/join`, { method: "POST" }),
  leave: (groupId: number) =>
    request<{ message: string; group_id: number }>(`/api/groups/${groupId}/leave`, { method: "POST" }),
  messages: (groupId: number) =>
    request<{ messages: GroupMessage[]; group_id: number }>(`/api/groups/${groupId}/messages`),
  send: (groupId: number, message: string) =>
    request<{ message: string; msg: GroupMessage }>(
      `/api/groups/${groupId}/send?message=${encodeURIComponent(message)}`, { method: "POST" }
    ),
};

// Learning Profile (Memory 2.0)
export interface LearningProfileFull {
  schwache_themen: WeakTopic[];
  starke_themen: WeakTopic[];
  letzte_fehler: { topic_id: string; subject: string; topic_name: string; letzte_frage: string }[];
  niveau_pro_fach: { subject: string; total: number; weak_count: number; avg_score: number; niveau: string }[];
  gamification: { xp?: number; level?: number; level_name?: string; streak_days?: number; quizzes_completed?: number };
}

// Admin API
/* eslint-disable @typescript-eslint/no-explicit-any */
export const adminApi = {
  stats: () => request<any>("/api/admin/stats"),
  analytics: (days: number = 7) => request<any>(`/api/admin/analytics?days=${days}`),
  searchUsers: (query: string) =>
    request<{ users: any[] }>(`/api/admin/search-users?query=${encodeURIComponent(query)}`),
  grantSubscription: (data: { user_id: number; tier: string; duration_days: number }) =>
    request<{ message: string }>("/api/admin/grant-subscription", { method: "POST", body: data }),
  createCoupon: (data: { code: string; tier: string; duration_days: number; max_uses: number }) =>
    request<{ message: string }>("/api/admin/create-coupon", { method: "POST", body: data }),
  coupons: () => request<{ coupons: any[] }>("/api/admin/coupons"),
};

// Coupon Redeem
export const couponApi = {
  redeem: (code: string) =>
    request<{ message: string; tier: string; duration_days: number }>(
      `/api/redeem-coupon?code=${encodeURIComponent(code)}`, { method: "POST" }
    ),
};

// Tournament API
export const tournamentApi = {
  current: () => request<{ tournament: any }>("/api/turnier/aktuell"),
  join: (tournamentId: number) =>
    request<{ message: string; tournament_id: number }>(
      `/api/turnier/teilnehmen?tournament_id=${tournamentId}`, { method: "POST" }
    ),
  submit: (tournamentId: number, answers: { question_id: number; answer: string }[], timeTaken: number) =>
    request<{ score: number; correct_answers: number; total_questions: number }>(
      `/api/turnier/abgeben?tournament_id=${tournamentId}&time_taken_seconds=${timeTaken}`,
      { method: "POST", body: answers }
    ),
  rankings: (tournamentId: number) =>
    request<{ rankings: any[]; tournament_id: number }>(`/api/turnier/rangliste?tournament_id=${tournamentId}`),
  winners: () => request<{ winners: any[]; tournament: any }>("/api/turnier/gewinner"),
  history: () => request<{ tournaments: any[] }>("/api/turnier/verlauf"),
};
/* eslint-enable @typescript-eslint/no-explicit-any */

// IQ-Test Types
export interface IQTestQuestion {
  id: number;
  kategorie: string;
  frage: string;
  optionen: string[];
  zeit_sekunden: number;
  schwierigkeit: number;
}

export interface IQTestData {
  test_id: number;
  questions: IQTestQuestion[];
  num_questions: number;
  time_limit_seconds: number;
  kategorien: string[];
}

export interface IQTestResult {
  iq: number;
  iq_range: string;
  percentile: number;
  klassifikation: string;
  kategorien: Record<string, number>;
  kategorie_iq?: Record<string, number>;
  staerken: string[];
  schwaechen: string[];
  vergleich: string;
  raw_score: number;
  max_score: number;
  training?: string[];
  iq_table?: { range: string; label: string; percent: string }[];
  total_correct?: number;
  total_questions?: number;
}

export interface IQCooldownResponse {
  can_take_test: boolean;
  days_remaining: number;
}

export interface IQResultResponse extends IQTestResult {
  has_result: boolean;
  test_date?: string;
}

export const iqApi = {
  generate: () => request<IQTestData>("/api/iq/generieren", { method: "POST" }),
  submit: (data: {
    test_id: number;
    answers: { question_id: number; answer: number; time_seconds: number }[];
  }) => request<IQTestResult>("/api/iq/berechnen", { method: "POST", body: data }),
  result: () => request<IQResultResponse>("/api/iq/ergebnis"),
  cooldown: () => request<IQCooldownResponse>("/api/iq/cooldown"),
};

// Supreme 9.0: KI Intelligence API
/* eslint-disable @typescript-eslint/no-explicit-any */
export const intelligenceApi = {
  lernstil: () => request<{ lernstil: string; beschreibung: string; tipps: string[] }>("/api/intelligence/lernstil"),
  feynman: (thema: string, erklaerung: string) =>
    request<{ bewertung: string; thema: string }>(
      `/api/intelligence/feynman?thema=${encodeURIComponent(thema)}&erklaerung=${encodeURIComponent(erklaerung)}`,
      { method: "POST" }
    ),
  sokrates: (frage: string) =>
    request<{ antwort: string; methode: string }>(
      `/api/intelligence/sokrates?frage=${encodeURIComponent(frage)}`,
      { method: "POST" }
    ),
  wissensscanStart: (subject: string) =>
    request<{ subject: string; grade: string; questions: any[] }>(
      `/api/intelligence/wissensscan/start?subject=${subject}`
    ),
  wissensscanResult: (subject: string, answers: number[]) =>
    request<{ score: number; correct: number; total: number; gaps: string[]; strengths: string[]; recommendation: string }>(
      `/api/intelligence/wissensscan/result?subject=${subject}&answers=${encodeURIComponent(JSON.stringify(answers))}`,
      { method: "POST" }
    ),
  weeklyPlan: () => request<{ plan: string; weak_topics: string[]; upcoming_exams: string[] }>("/api/intelligence/weekly-plan"),
};

// Supreme 9.0: Pomodoro Timer API
export const pomodoroApi = {
  complete: (subject: string = "general", duration: number = 25) =>
    request<{ message: string; xp_earned: number; duration: number }>(
      `/api/pomodoro/complete?subject=${subject}&duration_minutes=${duration}`,
      { method: "POST" }
    ),
  stats: () => request<{ today: number; today_minutes: number; week: number; week_minutes: number; total: number; total_minutes: number }>("/api/pomodoro/stats"),
};

// Supreme 9.0: Shop API
export interface ShopItem {
  id: string;
  name: string;
  category: string;
  price: number;
  icon: string;
  unlocked: boolean;
  can_afford: boolean;
}

export const shopApi = {
  items: () => request<{ items: ShopItem[]; user_xp: number }>("/api/shop/items"),
  buy: (itemId: string) =>
    request<{ message: string; item: ShopItem; remaining_xp: number }>(
      `/api/shop/buy?item_id=${itemId}`,
      { method: "POST" }
    ),
};

// Supreme 9.0: Challenges API
export interface Challenge {
  challenge_id: string;
  title: string;
  description: string;
  subject: string;
  target_score: number;
  xp_reward: number;
  deadline_days: number;
  creator_id: number;
  created_at: string;
  participants: number;
  completions: number;
}

export const challengesApi = {
  list: () => request<{ challenges: Challenge[] }>("/api/challenges/list"),
  create: (data: { title: string; description: string; subject?: string; target_score?: number; xp_reward?: number; deadline_days?: number }) =>
    request<Challenge>(
      `/api/challenges/create?title=${encodeURIComponent(data.title)}&description=${encodeURIComponent(data.description)}&subject=${data.subject || "math"}&target_score=${data.target_score || 80}&xp_reward=${data.xp_reward || 100}&deadline_days=${data.deadline_days || 7}`,
      { method: "POST" }
    ),
  join: (challengeId: string) =>
    request<{ message: string; challenge_id: string }>(`/api/challenges/join/${challengeId}`, { method: "POST" }),
  complete: (challengeId: string, score: number) =>
    request<{ message: string; xp_earned: number }>(`/api/challenges/complete/${challengeId}?score=${score}`, { method: "POST" }),
};

// Supreme 10.0: Voice Mode API
export const voiceApi = {
  transcribe: async (audioBlob: Blob): Promise<{ text: string; language: string }> => {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");
    const res = await fetch(`${API_URL}/api/voice/transcribe`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Transcription failed" }));
      throw new Error(err.detail || "Transcription failed");
    }
    return res.json();
  },
  tts: async (text: string): Promise<Blob> => {
    const token = getAccessToken();
    const res = await fetch(`${API_URL}/api/voice/tts?text=${encodeURIComponent(text)}&lang=de`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("TTS failed");
    return res.blob();
  },
};

// Supreme 10.0: Push Notifications API
/* eslint-disable @typescript-eslint/no-explicit-any */
export const notificationsApi = {
  subscribe: (endpoint: string, p256dh: string, authKey: string) =>
    request<{ message: string }>(`/api/notifications/subscribe?endpoint=${encodeURIComponent(endpoint)}&p256dh=${p256dh}&auth_key=${authKey}`, { method: "POST" }),
  unsubscribe: (endpoint: string) =>
    request<{ message: string }>(`/api/notifications/unsubscribe?endpoint=${encodeURIComponent(endpoint)}`, { method: "DELETE" }),
  vapidKey: () => request<{ public_key: string }>("/api/notifications/vapid-key"),
  sendTest: () => request<{ message: string; sent: number }>("/api/notifications/send-test", { method: "POST" }),
  weeklyStats: () => request<any>("/api/notifications/weekly-stats"),
  sendWeeklyReport: () => request<{ message: string; stats: any }>("/api/notifications/send-weekly-report", { method: "POST" }),
};

// Supreme 10.0: Parents Dashboard API
export const parentsApi = {
  linkChild: (childEmail: string) =>
    request<{ message: string; child_id: number; child_username: string }>(`/api/parents/link-child?child_email=${encodeURIComponent(childEmail)}`, { method: "POST" }),
  children: () => request<{ children: any[] }>("/api/parents/children"),
  unlinkChild: (childId: number) =>
    request<{ message: string }>(`/api/parents/unlink/${childId}`, { method: "DELETE" }),
};

// Supreme 10.0: Daily Quests API
export const questsApi = {
  today: () => request<{ quests: any[]; date: string }>("/api/quests/today"),
  updateProgress: (questId: string, progress: number = 1) =>
    request<{ quest_id: string; progress: number; target: number; completed: boolean; xp_earned: number }>(
      `/api/quests/progress/${questId}?progress=${progress}`, { method: "POST" }
    ),
};

// Supreme 10.0: Events API
export const eventsApi = {
  active: () => request<{ events: any[]; total: number }>("/api/events/active"),
  all: () => request<{ events: any[] }>("/api/events/all"),
  progress: (eventId: string) => request<any>(`/api/events/progress/${eventId}`),
};

// Supreme 10.0: Learning Partner Matching API
export const matchingApi = {
  findPartners: () => request<{ partners: any[]; my_weak_subjects?: string[] }>("/api/matching/lernpartner"),
};

// Supreme 10.0: Marketplace API
export const marketplaceApi = {
  items: (category?: string) =>
    request<{ items: any[] }>(category ? `/api/marketplace/items?category=${category}` : "/api/marketplace/items"),
  create: (data: { title: string; description?: string; price_cents?: number; item_type?: string }) =>
    request<{ id: number; title: string; message: string }>(
      `/api/marketplace/create?title=${encodeURIComponent(data.title)}&description=${encodeURIComponent(data.description || "")}&price_cents=${data.price_cents || 499}&item_type=${data.item_type || "quiz_set"}`,
      { method: "POST" }
    ),
  download: (itemId: number) =>
    request<{ title: string; content: any[]; message: string }>(`/api/marketplace/download/${itemId}`, { method: "POST" }),
  rate: (itemId: number, rating: number) =>
    request<{ message: string; new_rating: number }>(`/api/marketplace/rate/${itemId}?rating=${rating}`, { method: "POST" }),
};

// Supreme 10.0: PDF Export API
export const exportApi = {
  notePdfUrl: (noteId: number) => `${API_URL}/api/export/notizen/${noteId}/pdf`,
  lernplanPdfUrl: () => `${API_URL}/api/export/lernplan/pdf`,
};
/* eslint-enable @typescript-eslint/no-explicit-any */
