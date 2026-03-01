import { useEffect, useState } from "react";
import { useAuthStore } from "./stores/authStore";
import { useChatStore } from "./stores/chatStore";
import { useAuthRefresh } from "./hooks/useAuthRefresh";
import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import ChatPage from "./pages/ChatPage";
import QuizPage from "./pages/QuizPage";
import LearningPathPage from "./pages/LearningPathPage";
import RAGPage from "./pages/RAGPage";
import AbiturPage from "./pages/AbiturPage";
import ResearchPage from "./pages/ResearchPage";
import GamificationPage from "./pages/GamificationPage";
import GroupsPage from "./pages/GroupsPage";
import PricingPage from "./pages/PricingPage";
import SettingsPage from "./pages/SettingsPage";
import Sidebar from "./components/Sidebar";

function App() {
  const { isAuthenticated, isLoading, loadUser } = useAuthStore();
  const { loadSessions } = useChatStore();
  useAuthRefresh();
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("eduai_dark") === "true" ||
        window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return false;
  });

  useEffect(() => {
    loadUser();
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadSessions();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("eduai_dark", String(darkMode));
  }, [darkMode]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-500 dark:text-gray-400 text-sm">Laden...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthPage />;
  }

  const renderPage = () => {
    switch (currentPage) {
      case "dashboard":
        return <DashboardPage onNavigate={setCurrentPage} />;
      case "chat":
        return <ChatPage />;
      case "quiz":
        return <QuizPage />;
      case "learning":
        return <LearningPathPage onNavigate={setCurrentPage} />;
      case "rag":
        return <RAGPage />;
      case "abitur":
        return <AbiturPage />;
      case "research":
        return <ResearchPage />;
      case "gamification":
        return <GamificationPage />;
      case "groups":
        return <GroupsPage />;
      case "pricing":
        return <PricingPage />;
      case "settings":
        return <SettingsPage darkMode={darkMode} onDarkModeToggle={() => setDarkMode(!darkMode)} />;
      default:
        return <DashboardPage onNavigate={setCurrentPage} />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} />
      <main className="flex-1 overflow-auto">
        {renderPage()}
      </main>
    </div>
  );
}

export default App;
