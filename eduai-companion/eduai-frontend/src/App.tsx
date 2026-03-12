import { lazy, Suspense, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth as useClerkAuth, useUser as useClerkUser } from "@clerk/clerk-react";
import { useAuthStore } from "./stores/authStore";
import { useChatStore } from "./stores/chatStore";
import { useThemeStore } from "./stores/themeStore";
import { useAuthRefresh } from "./hooks/useAuthRefresh";
import { registerClerkGetToken } from "./services/api";
import { useStatusBar } from "./hooks/useCapacitor";
import { pageVariants } from "./lib/animations";
import Sidebar from "./components/Sidebar";
import PWAInstallBanner from "./components/PWAInstallBanner";
import CookieBanner from "./components/CookieBanner";
import OfflineBanner from "./components/OfflineBanner";
import GlobalHeader from "./components/GlobalHeader";
import ErrorBoundary from "./components/ErrorBoundary";

// Lazy-loaded pages — each page is loaded on-demand for faster initial load
const AuthPage = lazy(() => import("./pages/AuthPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ChatPage = lazy(() => import("./pages/ChatPage"));
const QuizPage = lazy(() => import("./pages/QuizPage"));
const LearningPathPage = lazy(() => import("./pages/LearningPathPage"));
const RAGPage = lazy(() => import("./pages/RAGPage"));
const AbiturPage = lazy(() => import("./pages/AbiturPage"));
const ResearchPage = lazy(() => import("./pages/ResearchPage"));
const GamificationPage = lazy(() => import("./pages/GamificationPage"));
const GroupsPage = lazy(() => import("./pages/GroupsPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const TurnierPage = lazy(() => import("./pages/TurnierPage"));
const IQTestPage = lazy(() => import("./pages/IQTestPage"));
const PricingPage = lazy(() => import("./pages/PricingPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const FlashcardsPage = lazy(() => import("./pages/FlashcardsPage"));
const NotesPage = lazy(() => import("./pages/NotesPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const MultiplayerPage = lazy(() => import("./pages/MultiplayerPage"));
const DatenschutzPage = lazy(() => import("./pages/DatenschutzPage"));
const SchoolPage = lazy(() => import("./pages/SchoolPage"));
const IntelligencePage = lazy(() => import("./pages/IntelligencePage"));
const PomodoroPage = lazy(() => import("./pages/PomodoroPage"));
const ShopPage = lazy(() => import("./pages/ShopPage"));
const ChallengesPage = lazy(() => import("./pages/ChallengesPage"));
const VoicePage = lazy(() => import("./pages/VoicePage"));
const ParentsPage = lazy(() => import("./pages/ParentsPage"));
const QuestsPage = lazy(() => import("./pages/QuestsPage"));
const EventsPage = lazy(() => import("./pages/EventsPage"));
const MatchingPage = lazy(() => import("./pages/MatchingPage"));
const MarketplacePage = lazy(() => import("./pages/MarketplacePage"));
const BattlePassPage = lazy(() => import("./pages/BattlePassPage"));
const StatsPage = lazy(() => import("./pages/StatsPage"));
const LandingPage = lazy(() => import("./pages/LandingPage"));
const ScannerPage = lazy(() => import("./pages/ScannerPage"));
const VoiceExamPage = lazy(() => import("./pages/VoiceExamPage"));
const ForschungsSeite = lazy(() => import("./pages/ForschungsSeite"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const OnboardingPage = lazy(() => import("./pages/OnboardingPage"));

function PageLoader() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-pulse-glow rounded-full h-10 w-10 bg-lumnos-gradient mx-auto flex items-center justify-center text-white text-sm font-bold">{"✦"}</div>
        <p className="mt-3 text-lumnos-muted text-xs">Laden...</p>
      </div>
    </div>
  );
}

/** Lumnos-branded splash screen shown while Clerk SDK initialises */
function ClerkSplash() {
  return (
    <div className="min-h-screen cyber-bg flex items-center justify-center">
      <div className="text-center">
        <div className="animate-pulse-glow rounded-full h-16 w-16 bg-lumnos-gradient mx-auto flex items-center justify-center text-white text-2xl font-bold">{"✦"}</div>
        <h1 className="mt-4 text-lumnos-accent text-lg font-bold tracking-wide">Lumnos</h1>
        <p className="mt-1 text-lumnos-muted text-xs">KI-Lerncoach wird geladen...</p>
      </div>
    </div>
  );
}

function App() {
  const { isAuthenticated, isLoading, loadUser, isGuest, enterGuestMode, loginWithClerk } = useAuthStore();
  // Clerk auth state
  const clerkAuth = useClerkAuth();
  const clerkUser = useClerkUser();
  const { loadSessions } = useChatStore();
  useAuthRefresh();
  useStatusBar(); // Configure native status bar (dark theme, #0f172a background)
  const [currentPage, setCurrentPage] = useState("chat");
  const [showLanding, setShowLanding] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [backendWaking, setBackendWaking] = useState(false);
  // Ensure theme store is initialized + subscribed
  useThemeStore((s) => s.resolvedTheme);

  // Backend pre-warm: ping backend on app load to wake it from Render free-tier sleep
  const preWarmBackend = useCallback(() => {
    const apiUrl = import.meta.env.VITE_API_URL;
    if (!apiUrl) return;
    setBackendWaking(true);
    fetch(`${apiUrl}/api/ping`, { method: "GET", mode: "cors" })
      .then(() => setBackendWaking(false))
      .catch(() => {
        // Retry once after 3s
        setTimeout(() => {
          fetch(`${apiUrl}/api/ping`, { method: "GET", mode: "cors" })
            .finally(() => setBackendWaking(false));
        }, 3000);
      });
  }, []);

  useEffect(() => {
    preWarmBackend();
  }, [preWarmBackend]);

  // Keep-Alive: Ping backend every 5 minutes to prevent Render free-tier sleep
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL;
    if (!apiUrl) return;
    const ping = () => fetch(`${apiUrl}/healthz`, { method: "GET", mode: "cors" }).catch(() => {});
    // Initial ping already handled by preWarmBackend, start interval only
    const interval = setInterval(ping, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);


  // Register Clerk's getToken so the API layer can refresh tokens automatically.
  // This MUST run before any API calls so getFreshClerkToken() works.
  useEffect(() => {
    if (clerkAuth.isSignedIn && clerkAuth.getToken) {
      registerClerkGetToken(() => clerkAuth.getToken());
    }
  }, [clerkAuth.isSignedIn, clerkAuth.getToken]);

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
  }, [clerkAuth.isSignedIn, clerkUser.user, isAuthenticated]);

  useEffect(() => {
    loadUser();
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadSessions();
    }
  }, [isAuthenticated]);


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

  // Show branded splash while Clerk SDK is loading (prevents blank white page)
  if (!clerkAuth.isLoaded) {
    return <ClerkSplash />;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen cyber-bg flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse-glow rounded-full h-12 w-12 bg-lumnos-gradient mx-auto flex items-center justify-center text-white text-lg font-bold">{"✦"}</div>
          {backendWaking ? (
            <>
              <p className="mt-4 text-lumnos-accent text-sm font-medium">KI-Gehirn wird geweckt...</p>
              <p className="mt-1 text-lumnos-muted text-xs">Erster Start kann bis zu 30 Sekunden dauern</p>
            </>
          ) : (
            <p className="mt-4 text-lumnos-muted text-sm">Laden...</p>
          )}
        </div>
      </div>
    );
  }

  // Auth-Guard komplett entfernt für Testing — direkt zum Chat
  if (!isAuthenticated && !isGuest) {
    if (showLanding) {
      return (
        <Suspense fallback={<PageLoader />}>
          <LandingPage
            onLogin={() => setShowLanding(false)}
            onRegister={() => setShowLanding(false)}
            onIQTest={() => setShowLanding(false)}
            onGuestChat={() => {
              enterGuestMode();
              setCurrentPage("chat");
            }}
          />
        </Suspense>
      );
    }
    return <Suspense fallback={<PageLoader />}><AuthPage /></Suspense>;
  }

  if (showOnboarding) {
    return <Suspense fallback={<PageLoader />}><OnboardingPage onComplete={() => setShowOnboarding(false)} /></Suspense>;
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
      case "notifications":
        return <NotificationsPage />;
      case "pricing":
        return <PricingPage />;
      case "settings":
        return <SettingsPage />;
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
          background: "var(--gradient-bg)",
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
          <GlobalHeader />
          <AnimatePresence mode="wait">
            <motion.div
              key={currentPage}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              style={{ flex: 1, overflowY: "auto", overflowX: "hidden", display: "flex", flexDirection: "column" }}
              className="scrollable mobile-safe-bottom"
            >
              <Suspense fallback={<PageLoader />}>
                {renderPage()}
              </Suspense>
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
