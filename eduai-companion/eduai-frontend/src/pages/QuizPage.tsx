import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { quizApi, type QuizData, type QuizResult, type QuizHistoryItem, type AnswerCheckResult } from "../services/api";
import {
  BrainCircuit, CheckCircle2, XCircle, ArrowRight, RotateCcw, Trophy,
  Calculator, Languages, BookOpenCheck, Clock, FlaskConical, Loader2
} from "lucide-react";

const SUBJECTS = [
  { id: "math", name: "Mathe", icon: <Calculator className="w-5 h-5" />, color: "from-blue-500 to-blue-600" },
  { id: "english", name: "Englisch", icon: <Languages className="w-5 h-5" />, color: "from-emerald-500 to-emerald-600" },
  { id: "german", name: "Deutsch", icon: <BookOpenCheck className="w-5 h-5" />, color: "from-amber-500 to-amber-600" },
  { id: "history", name: "Geschichte", icon: <Clock className="w-5 h-5" />, color: "from-purple-500 to-purple-600" },
  { id: "science", name: "Naturwiss.", icon: <FlaskConical className="w-5 h-5" />, color: "from-rose-500 to-rose-600" },
];

const DIFFICULTIES = [
  { id: "beginner", name: "Anfänger", desc: "Grundlagen" },
  { id: "intermediate", name: "Mittel", desc: "Fortgeschritten" },
  { id: "advanced", name: "Schwer", desc: "Experte" },
];

type QuizState = "setup" | "playing" | "results";

export default function QuizPage() {
  const [state, setState] = useState<QuizState>("setup");
  const [subject, setSubject] = useState("math");
  const [difficulty, setDifficulty] = useState("beginner");
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [showAnswer, setShowAnswer] = useState(false);
  const [answerResult, setAnswerResult] = useState<AnswerCheckResult | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<QuizHistoryItem[]>([]);
  const [fillAnswer, setFillAnswer] = useState("");

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await quizApi.history();
      setHistory(data);
    } catch (err) {
      console.error("Failed to load quiz history:", err);
    }
  };

  const startQuiz = async () => {
    setLoading(true);
    try {
      const data = await quizApi.generate({
        subject,
        difficulty,
        num_questions: 5,
        quiz_type: "mixed",
        language: "de",
      });
      setQuiz(data);
      setCurrentQ(0);
      setAnswers({});
      setShowAnswer(false);
      setResult(null);
      setFillAnswer("");
      setState("playing");
    } catch (err) {
      console.error("Failed to generate quiz:", err);
    } finally {
      setLoading(false);
    }
  };

  const selectAnswer = async (questionId: number, answer: string) => {
    if (showAnswer || !quiz) return;
    setAnswers({ ...answers, [questionId]: answer });
    setShowAnswer(true);
    // Check answer against server
    try {
      const checkResult = await quizApi.checkAnswer({
        quiz_id: quiz.quiz_id,
        question_id: questionId,
        user_answer: answer,
      });
      setAnswerResult(checkResult);
    } catch (err) {
      console.error("Failed to check answer:", err);
      setAnswerResult(null);
    }
  };

  const submitFillAnswer = () => {
    if (!quiz || !fillAnswer.trim()) return;
    const q = quiz.questions[currentQ];
    selectAnswer(q.id, fillAnswer.trim());
    setFillAnswer("");
  };

  const nextQuestion = () => {
    if (!quiz) return;
    if (currentQ < quiz.questions.length - 1) {
      setCurrentQ(currentQ + 1);
      setShowAnswer(false);
      setAnswerResult(null);
    } else {
      submitQuiz();
    }
  };

  const submitQuiz = async () => {
    if (!quiz) return;
    setLoading(true);
    try {
      const answersList = quiz.questions.map((q) => ({
        question_id: q.id,
        user_answer: answers[q.id] || "",
      }));
      const res = await quizApi.submit({
        quiz_id: quiz.quiz_id,
        subject: quiz.subject,
        answers: answersList,
        difficulty: quiz.difficulty,
      });
      setResult(res);
      setState("results");
      loadHistory();
    } catch (err) {
      console.error("Failed to submit quiz:", err);
    } finally {
      setLoading(false);
    }
  };

  const resetQuiz = () => {
    setState("setup");
    setQuiz(null);
    setResult(null);
    setAnswers({});
    setCurrentQ(0);
    setShowAnswer(false);
    setAnswerResult(null);
  };

  // Setup screen
  if (state === "setup") {
    return (
      <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <BrainCircuit className="w-7 h-7 text-blue-600" />
            Quiz-Modus
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Teste dein Wissen und verbessere deine Fähigkeiten!
          </p>
        </div>

        {/* Subject Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Fach wählen</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {SUBJECTS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSubject(s.id)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    subject === s.id
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400"
                      : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                  }`}
                >
                  <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${s.color} flex items-center justify-center text-white`}>
                    {s.icon}
                  </div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{s.name}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Difficulty Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Schwierigkeitsgrad</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d.id}
                  onClick={() => setDifficulty(d.id)}
                  className={`p-4 rounded-xl border-2 text-center transition-all ${
                    difficulty === d.id
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400"
                      : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                  }`}
                >
                  <p className="font-medium text-gray-900 dark:text-white">{d.name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{d.desc}</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Button onClick={startQuiz} size="lg" className="w-full gap-2" disabled={loading}>
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <BrainCircuit className="w-5 h-5" />}
          {loading ? "Quiz wird erstellt..." : "Quiz starten"}
        </Button>

        {/* Quiz History */}
        {history.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Letzte Quizzes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {history.slice(0, 5).map((h, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${SUBJECTS.find(s => s.id === h.subject)?.color || "from-gray-500 to-gray-600"} flex items-center justify-center text-white text-xs`}>
                        {SUBJECTS.find(s => s.id === h.subject)?.icon}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {SUBJECTS.find(s => s.id === h.subject)?.name || h.subject}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date(h.completed_at).toLocaleDateString("de-DE")} - {h.difficulty}
                        </p>
                      </div>
                    </div>
                    <Badge variant={h.score >= 80 ? "success" : h.score >= 50 ? "warning" : "destructive"}>
                      {h.correct_answers}/{h.total_questions} ({h.score}%)
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  // Playing screen
  if (state === "playing" && quiz) {
    const question = quiz.questions[currentQ];
    const isAnswered = showAnswer;
    const userAnswer = answers[question.id];
    const isCorrect = answerResult?.correct ?? false;
    const hasOptions = question.options && question.options.length > 0;

    return (
      <div className="p-4 lg:p-6 max-w-2xl mx-auto space-y-6">
        {/* Progress */}
        <div className="flex items-center justify-between">
          <Badge variant="secondary" className="text-sm">
            Frage {currentQ + 1} von {quiz.questions.length}
          </Badge>
          <Badge variant="default">
            {SUBJECTS.find(s => s.id === quiz.subject)?.name} - {difficulty}
          </Badge>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all"
            style={{ width: `${((currentQ + (isAnswered ? 1 : 0)) / quiz.questions.length) * 100}%` }}
          />
        </div>

        {/* Question */}
        <Card className="shadow-lg">
          <CardContent className="p-6">
            <p className="text-lg font-medium text-gray-900 dark:text-white mb-6">
              {question.question}
            </p>

            {/* MCQ Options */}
            {hasOptions ? (
              <div className="space-y-3">
                {question.options!.map((opt, idx) => {
                  const isSelected = userAnswer === opt;
                  const isRight = answerResult ? opt === answerResult.correct_answer : false;
                  let optionStyle = "border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600";
                  if (isAnswered) {
                    if (isRight) optionStyle = "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20";
                    else if (isSelected && !isRight) optionStyle = "border-red-500 bg-red-50 dark:bg-red-900/20";
                    else optionStyle = "border-gray-200 dark:border-gray-700 opacity-60";
                  } else if (isSelected) {
                    optionStyle = "border-blue-500 bg-blue-50 dark:bg-blue-900/20";
                  }

                  return (
                    <button
                      key={idx}
                      onClick={() => selectAnswer(question.id, opt)}
                      disabled={isAnswered}
                      className={`w-full text-left p-4 rounded-xl border-2 transition-all flex items-center gap-3 ${optionStyle}`}
                    >
                      <span className="w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm font-medium shrink-0">
                        {String.fromCharCode(65 + idx)}
                      </span>
                      <span className="text-gray-900 dark:text-white">{opt}</span>
                      {isAnswered && isRight && <CheckCircle2 className="w-5 h-5 text-emerald-500 ml-auto shrink-0" />}
                      {isAnswered && isSelected && !isRight && <XCircle className="w-5 h-5 text-red-500 ml-auto shrink-0" />}
                    </button>
                  );
                })}
              </div>
            ) : (
              /* Fill-in-blank */
              <div className="space-y-3">
                {!isAnswered ? (
                  <div className="flex gap-2">
                    <Input
                      value={fillAnswer}
                      onChange={(e) => setFillAnswer(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && submitFillAnswer()}
                      placeholder="Deine Antwort eingeben..."
                      className="flex-1"
                    />
                    <Button onClick={submitFillAnswer} disabled={!fillAnswer.trim()}>
                      Prüfen
                    </Button>
                  </div>
                ) : (
                  <div className={`p-4 rounded-xl border-2 ${isCorrect ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20" : "border-red-500 bg-red-50 dark:bg-red-900/20"}`}>
                    <div className="flex items-center gap-2 mb-1">
                      {isCorrect ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <XCircle className="w-5 h-5 text-red-500" />}
                      <span className="font-medium">{isCorrect ? "Richtig!" : "Falsch"}</span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Deine Antwort: <strong>{userAnswer}</strong>
                    </p>
                    {!isCorrect && answerResult && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Richtige Antwort: <strong>{answerResult.correct_answer}</strong>
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Explanation */}
            {isAnswered && answerResult?.explanation && (
              <div className="mt-4 p-4 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                <p className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-1">Erklärung:</p>
                <p className="text-sm text-blue-700 dark:text-blue-400">{answerResult.explanation}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Navigation */}
        {isAnswered && (
          <Button onClick={nextQuestion} size="lg" className="w-full gap-2">
            {currentQ < quiz.questions.length - 1 ? (
              <>Nächste Frage <ArrowRight className="w-4 h-4" /></>
            ) : (
              <>Quiz beenden <Trophy className="w-4 h-4" /></>
            )}
          </Button>
        )}
      </div>
    );
  }

  // Results screen
  if (state === "results" && result) {
    const scoreColor = result.score >= 80 ? "text-emerald-600" : result.score >= 50 ? "text-amber-600" : "text-red-600";
    const scoreBg = result.score >= 80 ? "from-emerald-500 to-emerald-600" : result.score >= 50 ? "from-amber-500 to-amber-600" : "from-red-500 to-red-600";

    return (
      <div className="p-4 lg:p-6 max-w-2xl mx-auto space-y-6">
        <Card className="shadow-xl text-center">
          <CardContent className="p-8">
            <div className={`w-24 h-24 mx-auto rounded-full bg-gradient-to-br ${scoreBg} flex items-center justify-center text-white shadow-lg mb-6`}>
              <Trophy className="w-12 h-12" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Quiz abgeschlossen!</h2>
            <p className={`text-5xl font-bold ${scoreColor} mb-2`}>{result.score}%</p>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              {result.correct_answers} von {result.total_questions} richtig
            </p>
            <Badge variant={result.score >= 80 ? "success" : result.score >= 50 ? "warning" : "destructive"} className="text-sm px-4 py-1">
              Neues Level: {result.new_proficiency}
            </Badge>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-4 max-w-md mx-auto">
              {result.feedback}
            </p>
          </CardContent>
        </Card>

        <div className="flex gap-3">
          <Button onClick={startQuiz} className="flex-1 gap-2" disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
            Nochmal spielen
          </Button>
          <Button onClick={resetQuiz} variant="outline" className="flex-1">
            Anderes Fach
          </Button>
        </div>
      </div>
    );
  }

  return null;
}
