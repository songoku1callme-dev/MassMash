import { useState, useEffect, useRef } from "react";
import { pomodoroApi } from "../services/api";
import { Button } from "@/components/ui/button";
import { Timer, Play, Pause, RotateCcw, Coffee, Loader2 } from "lucide-react";

type TimerState = "idle" | "work" | "break" | "long_break";

export default function PomodoroPage() {
  const [timerState, setTimerState] = useState<TimerState>("idle");
  const [secondsLeft, setSecondsLeft] = useState(25 * 60);
  const [isRunning, setIsRunning] = useState(false);
  const [pomodorosCompleted, setPomodorosCompleted] = useState(0);
  const [subject, setSubject] = useState("general");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<{ today: number; today_minutes: number; week: number; total: number } | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const WORK_DURATION = 25 * 60;
  const BREAK_DURATION = 5 * 60;
  const LONG_BREAK_DURATION = 30 * 60;

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    if (isRunning && secondsLeft > 0) {
      intervalRef.current = setInterval(() => {
        setSecondsLeft((prev) => prev - 1);
      }, 1000);
    } else if (secondsLeft === 0) {
      handleTimerEnd();
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isRunning, secondsLeft]);

  const loadStats = async () => {
    try {
      const data = await pomodoroApi.stats();
      setStats(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleTimerEnd = async () => {
    setIsRunning(false);
    if (intervalRef.current) clearInterval(intervalRef.current);

    if (timerState === "work") {
      // Pomodoro completed!
      setLoading(true);
      try {
        await pomodoroApi.complete(subject, 25);
        await loadStats();
      } catch (e) {
        console.error(e);
      }
      setLoading(false);

      const newCount = pomodorosCompleted + 1;
      setPomodorosCompleted(newCount);

      // Every 4 pomodoros: long break
      if (newCount % 4 === 0) {
        setTimerState("long_break");
        setSecondsLeft(LONG_BREAK_DURATION);
      } else {
        setTimerState("break");
        setSecondsLeft(BREAK_DURATION);
      }
    } else {
      // Break ended, start work
      setTimerState("work");
      setSecondsLeft(WORK_DURATION);
    }
  };

  const startWork = () => {
    setTimerState("work");
    setSecondsLeft(WORK_DURATION);
    setIsRunning(true);
  };

  const togglePause = () => {
    setIsRunning(!isRunning);
  };

  const reset = () => {
    setIsRunning(false);
    if (intervalRef.current) clearInterval(intervalRef.current);
    setTimerState("idle");
    setSecondsLeft(WORK_DURATION);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const progress = (() => {
    const total = timerState === "work" ? WORK_DURATION : timerState === "long_break" ? LONG_BREAK_DURATION : BREAK_DURATION;
    return ((total - secondsLeft) / total) * 100;
  })();

  const stateColors = {
    idle: "text-gray-600",
    work: "text-red-600 dark:text-red-400",
    break: "text-green-600 dark:text-green-400",
    long_break: "text-blue-600 dark:text-blue-400",
  };

  const stateLabels = {
    idle: "Bereit",
    work: "Lernzeit",
    break: "Kurze Pause",
    long_break: "Lange Pause",
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Pomodoro Lern-Timer</h1>
      <p className="text-gray-500 dark:text-gray-400 mb-6">25 Min lernen, 5 Min Pause. Nach 4 Runden: 30 Min Pause.</p>

      {/* Timer Display */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-sm border border-gray-200 dark:border-gray-700 text-center mb-6">
        <p className={`text-sm font-medium mb-2 ${stateColors[timerState]}`}>
          {timerState === "work" && <Timer className="w-4 h-4 inline mr-1" />}
          {(timerState === "break" || timerState === "long_break") && <Coffee className="w-4 h-4 inline mr-1" />}
          {stateLabels[timerState]}
        </p>

        <div className="relative w-48 h-48 mx-auto mb-6">
          <svg className="w-48 h-48 transform -rotate-90" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" className="text-gray-200 dark:text-gray-700" strokeWidth="6" />
            <circle
              cx="50" cy="50" r="45" fill="none"
              stroke="currentColor"
              className={timerState === "work" ? "text-red-500" : timerState === "break" || timerState === "long_break" ? "text-green-500" : "text-gray-400"}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 45}`}
              strokeDashoffset={`${2 * Math.PI * 45 * (1 - progress / 100)}`}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-4xl font-mono font-bold text-gray-900 dark:text-white">
              {formatTime(secondsLeft)}
            </span>
          </div>
        </div>

        {/* Subject selector */}
        {timerState === "idle" && (
          <div className="mb-4">
            <select
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="p-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white text-sm"
            >
              <option value="general">Allgemein</option>
              <option value="math">Mathematik</option>
              <option value="german">Deutsch</option>
              <option value="english">Englisch</option>
              <option value="physics">Physik</option>
              <option value="chemistry">Chemie</option>
              <option value="biology">Biologie</option>
              <option value="history">Geschichte</option>
            </select>
          </div>
        )}

        {/* Controls */}
        <div className="flex justify-center gap-3">
          {timerState === "idle" ? (
            <Button onClick={startWork} size="lg" className="gap-2">
              <Play className="w-5 h-5" />
              Starten
            </Button>
          ) : (
            <>
              <Button onClick={togglePause} variant="outline" size="lg" className="gap-2">
                {isRunning ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                {isRunning ? "Pause" : "Weiter"}
              </Button>
              <Button onClick={reset} variant="ghost" size="lg" className="gap-2">
                <RotateCcw className="w-5 h-5" />
                Reset
              </Button>
            </>
          )}
        </div>

        {loading && (
          <div className="mt-3 flex items-center justify-center gap-2 text-green-600">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">+25 XP verdient!</span>
          </div>
        )}
      </div>

      {/* Pomodoro Counter */}
      <div className="flex gap-2 justify-center mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              i <= (pomodorosCompleted % 4 || (pomodorosCompleted > 0 && pomodorosCompleted % 4 === 0 ? 4 : 0))
                ? "bg-red-500 text-white"
                : "bg-gray-200 dark:bg-gray-700 text-gray-400"
            }`}
          >
            {i}
          </div>
        ))}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center border border-gray-200 dark:border-gray-700">
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.today}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Heute ({stats.today_minutes} Min)</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center border border-gray-200 dark:border-gray-700">
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">{stats.week}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Diese Woche</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center border border-gray-200 dark:border-gray-700">
            <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{stats.total}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Gesamt</p>
          </div>
        </div>
      )}
    </div>
  );
}
