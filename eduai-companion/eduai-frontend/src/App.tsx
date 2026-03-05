import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth as useClerkAuth, useUser as useClerkUser } from "@clerk/clerk-react";
import { useAuthStore } from "./stores/authStore";
import { useChatStore } from "./stores/chatStore";
import { useAuthRefresh } from "./hooks/useAuthRefresh";
import { pageVariants } from "./lib/animations";
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
import StatsPage from "./pages/StatsPage";
import LandingPage from "./pages/LandingPage";
import ScannerPage from "./pages/ScannerPage";
import VoiceExamPage from "./pages/VoiceExamPage";
import ForschungsSeite from "./pages/ForschungsSeite";
import OnboardingPage from "./pages/OnboardingPage";
import Sidebar from "./components/Sidebar";
import PWAInstallBanner from "./components/PWAInstallBanner";
import CookieBanner from "./components/CookieBanner";
import OfflineBanner from "./components/OfflineBanner";
import NotificationBell from "./components/NotificationBell";
import ErrorBoundary from "./components/ErrorBoundary";

function App() {
  const { isAuthenticated, isLoading, loadUser, isGuest, enterGuestMode, loginWithClerk } = useAuthStore();
  // Clerk auth state
  const clerkAuth = useClerkAuth();
  const clerkUser = useClerkUser();
  const { loadSessions } = useChatStore();
  useAuthRefresh();
  const [currentPage, setCurrentPage] = useState("chat");
  const [showLanding, setShowLanding] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("lumnos_dark") === "true" ||
        window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return false;
  });

  // Clerk → AuthStore sync: when Clerk signs in, get token and sync
  useEffect(() => {
    if (clerkAuth.isSignedIn && clerkUser.user && !isAuthenticated) {
      clerkAuth.getToken().then((token) => {
        if (token) {
          loginWithClerk(token, {
            id: clerkUser.user!.id,
            email: clerkUser.user!.primaryEmailAddress?.emailAddress || "",
            firstName: clerkUser.user!.firstName || "",
            lastName: clerkUser.user!.lastName || "",
            imageUrl: clerkUser.user!.imageUrl || "",
          });
        }
      });
    }
  }, [clerkAuth.isSignedIn, clerkUser.user]);

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
    localStorage.setItem("lumnos_dark", String(darkMode));
  }, [darkMode]);

  // Allow navigation from pages that don't receive onNavigate props (e.g. Chat header upgrade button)
  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (typeof detail === "string") {
        setCurrentPage(detail);
      }
    };

    window.addEventListener("navigate", handler);
    return () => window.removeEventListener("navigate", handler);
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen cyber-bg flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse-glow rounded-full h-12 w-12 bg-lumnos-gradient mx-auto flex items-center justify-center text-white text-lg font-bold">{"\u2726"}</div>
          <p className="mt-4 text-lumnos-muted text-sm">Laden...</p>
        </div>
      </div>
    );
  }

  // Auth-Guard komplett entfernt fuer Testing — direkt zum Chat
  if (!isAuthenticated && !isGuest) {
    if (showLanding) {
      return (
        <LandingPage
          onLogin={() => setShowLanding(false)}
          onRegister={() => setShowLanding(false)}
          onIQTest={() => setShowLanding(false)}
          onGuestChat={() => {
            enterGuestMode();
            setCurrentPage("chat");
          }}
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
      case "meine-stats":
        return <StatsPage />;
      case "scanner":
        return <ScannerPage />;
      case "voice-exam":
        return <VoiceExamPage />;
      case "forschung":
        return <ForschungsSeite />;
      case "pricing":
        return <PricingPage />;
      case "settings":
        return <SettingsPage darkMode={darkMode} onDarkModeToggle={() => setDarkMode(!darkMode)} />;
      default:
        return <DashboardPage onNavigate={setCurrentPage} />;
    }
  };

  return (
    <ErrorBoundary>
      <div
        style={{
          display: "flex",
          height: "100dvh",
          width: "100vw",
          overflow: "hidden",
          backgroundColor: "#0a0f1e",
          position: "relative",
        }}
        className="text-lumnos-text"
      >
        <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} />
        <main
          style={{
            flex: 1,
            height: "100dvh",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            position: "relative",
            minWidth: 0,
          }}
        >
          <div className="absolute top-4 right-4 z-30">
            <NotificationBell />
          </div>
          <AnimatePresence mode="wait">
            <motion.div
              key={currentPage}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              style={{ flex: 1, overflowY: "auto", overflowX: "hidden", display: "flex", flexDirection: "column" }}
              className="scrollable"
            >
              {renderPage()}
            </motion.div>
          </AnimatePresence>
        </main>
        <PWAInstallBanner />
        <CookieBanner />
        <OfflineBanner />
      </div>
    </ErrorBoundary>
  );
}

export default App;
