"""Pydantic schemas for request/response models."""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Auth schemas
class UserRegister(BaseModel):
    email: str
    username: str
    password: str
    full_name: str = ""
    school_grade: str = "10"
    school_type: str = "Gymnasium"
    preferred_language: str = "de"


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    school_grade: str
    school_type: str
    preferred_language: str
    is_pro: bool = False
    subscription_tier: str = "free"
    ki_personality_id: int = 1
    ki_personality_name: str = "Freundlich"
    avatar_url: str = ""
    auth_provider: str = "local"
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"
    user: UserResponse


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    school_grade: Optional[str] = None
    school_type: Optional[str] = None
    preferred_language: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Chat schemas
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    subject: Optional[str] = None
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    subject: Optional[str] = None
    language: str = "de"
    detail_level: str = "normal"  # "simpler", "normal", "detailed"
    personality_id: Optional[int] = None  # KI-Persoenlichkeit ID (1-5)
    tutor_modus: bool = False  # Perfect School 4.1: Socratic method toggle
    eli5: bool = False  # Perfect School 4.1: Explain Like I'm 5


class ChatResponse(BaseModel):
    response: str
    session_id: int
    subject: str
    detected_subject: Optional[str] = None
    proficiency_level: str = "intermediate"


class ChatSessionResponse(BaseModel):
    id: int
    subject: str
    title: str
    language: str
    message_count: int
    created_at: str
    updated_at: str


# Quiz schemas
class QuizGenerateRequest(BaseModel):
    subject: str
    topic: Optional[str] = None
    thema_custom: Optional[str] = None  # Free text topic input (Pro+)
    difficulty: str = "intermediate"
    num_questions: int = 5  # 5, 10, 20, 50
    quiz_type: str = "mixed"  # "mcq", "true_false", "fill_blank", "free_text", "mixed"
    language: str = "de"


class QuizQuestion(BaseModel):
    """Full quiz question (internal use only — includes correct_answer)."""
    id: int
    question: str
    options: Optional[List[str]] = None  # For MCQ
    correct_answer: str
    explanation: str
    difficulty: str
    topic: str


class QuizQuestionPublic(BaseModel):
    """Quiz question sent to the client — no correct_answer or explanation."""
    id: int
    question: str
    options: Optional[List[str]] = None
    difficulty: str
    topic: str


class QuizResponse(BaseModel):
    quiz_id: str
    subject: str
    difficulty: str
    questions: List[QuizQuestionPublic]


class AnswerCheckRequest(BaseModel):
    quiz_id: str
    question_id: int
    user_answer: str


class AnswerCheckResponse(BaseModel):
    correct: bool
    correct_answer: str
    explanation: str


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    subject: str
    answers: List[dict]  # [{question_id, user_answer}]
    difficulty: str = "intermediate"


class QuizResultResponse(BaseModel):
    total_questions: int
    correct_answers: int
    score: float
    feedback: str
    new_proficiency: str
    weak_topic_detected: Optional[str] = None
    weak_topic_suggestion: Optional[str] = None


# Profile schemas
class LearningProfileResponse(BaseModel):
    subject: str
    proficiency_level: str
    mastery_score: float
    topics_completed: int
    total_questions_answered: int
    correct_answers: int
    accuracy: float
    last_active: str


class ProgressResponse(BaseModel):
    profiles: List[LearningProfileResponse]
    total_sessions: int
    total_quizzes: int
    recent_activity: List[dict]
    streak_days: int


# Learning Path schemas
class LearningPathTopic(BaseModel):
    topic: str
    subject: str
    difficulty: str
    mastered: bool
    recommended: bool
    description: str


class LearningPathResponse(BaseModel):
    subject: str
    current_level: str
    recommended_topics: List[LearningPathTopic]
    next_milestone: str


# Subject schemas
class SubjectInfo(BaseModel):
    id: str
    name: str
    name_de: str
    icon: str
    description: str
    description_de: str
    topics: List[str]
