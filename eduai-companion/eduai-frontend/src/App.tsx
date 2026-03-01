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
import AdminPage from "./pages/AdminPage";
import TurnierPage from "./pages/TurnierPage";
import IQTestPage from "./pages/IQTestPage";
import PricingPage from "./pages/PricingPage";
import SettingsPage from "./pages/SettingsPage";
import FlashcardsPage from "./pages/FlashcardsPage";
import NotesPage from "./pages/NotesPage";
import CalendarPage from "./pages/CalendarPage";
import MultiplayerPage from "./pages/MultiplayerPage";
import DatenschutzPage from "./pages/DatenschutzPage";
import SchoolPage from "./pages/SchoolPage";
import IntelligencePage from "./pages/IntelligencePage";
import PomodoroPage from "./pages/PomodoroPage";
import ShopPage from "./pages/ShopPage";
import ChallengesPage from "./pages/ChallengesPage";
import VoicePage from "./pages/VoicePage";
import ParentsPage from "./pages/ParentsPage";
import QuestsPage from "./pages/QuestsPage";
import EventsPage from "./pages/EventsPage";
import MatchingPage from "./pages/MatchingPage";
import MarketplacePage from "./pages/MarketplacePage";
import BattlePassPage from "./pages/BattlePassPage";
import LandingPage from "./pages/LandingPage";
import OnboardingPage from "./pages/OnboardingPage";
import Sidebar from "./components/Sidebar";
import PWAInstallBanner from "./components/PWAInstallBanner";
import CookieBanner from "./components/CookieBanner";
import OfflineBanner from "./components/OfflineBanner";

function App() {
  const { isAuthenticated, isLoading, loadUser } = useAuthStore();
  const { loadSessions } = useChatStore();
  useAuthRefresh();
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [showLanding, setShowLanding] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);
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
    if (showLanding) {
      return (
        <LandingPage
          onLogin={() => setShowLanding(false)}
          onRegister={() => setShowLanding(false)}
          onIQTest={() => setShowLanding(false)}
        />
      );
    }
    return <AuthPage />;
  }

  if (showOnboarding) {
    return <OnboardingPage onComplete={() => setShowOnboarding(false)} />;
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
      case "admin":
        return <AdminPage />;
      case "turnier":
        return <TurnierPage />;
      case "iq-test":
        return <IQTestPage />;
      case "flashcards":
        return <FlashcardsPage />;
      case "notes":
        return <NotesPage />;
      case "calendar":
        return <CalendarPage />;
      case "multiplayer":
        return <MultiplayerPage />;
      case "datenschutz":
        return <DatenschutzPage />;
      case "school":
        return <SchoolPage />;
      case "intelligence":
        return <IntelligencePage />;
      case "pomodoro":
        return <PomodoroPage />;
      case "shop":
        return <ShopPage />;
      case "challenges":
        return <ChallengesPage />;
      case "voice":
        return <VoicePage />;
      case "parents":
        return <ParentsPage />;
      case "quests":
        return <QuestsPage />;
      case "events":
        return <EventsPage />;
      case "matching":
        return <MatchingPage />;
      case "marketplace":
        return <MarketplacePage />;
      case "battle-pass":
        return <BattlePassPage />;
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
      <PWAInstallBanner />
      <CookieBanner />
      <OfflineBanner />
    </div>
  );
}

export default App;
