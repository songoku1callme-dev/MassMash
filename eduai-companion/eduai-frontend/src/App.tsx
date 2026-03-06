import { lazy, Suspense, useEffect, useState } from "react";
import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth as useClerkAuth, useUser as useClerkUser } from "@clerk/clerk-react";
import { useAuthStore } from "./stores/authStore";
import { useChatStore } from "./stores/chatStore";
import { useThemeStore } from "./stores/themeStore";
import { useAuthRefresh } from "./hooks/useAuthRefresh";
import { pageVariants } from "./lib/animations";
import { pageIdToPath } from "./lib/routes";
import Sidebar from "./components/Sidebar";
import PWAInstallBanner from "./components/PWAInstallBanner";
import CookieBanner from "./components/CookieBanner";
import OfflineBanner from "./components/OfflineBanner";
import NotificationBell from "./components/NotificationBell";
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
const OnboardingPage = lazy(() => import("./pages/OnboardingPage"));

function PageLoader() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-pulse-glow rounded-full h-10 w-10 bg-lumnos-gradient mx-auto flex items-center justify-center text-white text-sm font-bold">{"\u2726"}</div>
        <p className="mt-3 text-lumnos-muted text-xs">Laden...</p>
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
  const location = useLocation();
  const navigate = useNavigate();
  const [showLanding, setShowLanding] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  // Ensure theme store is initialized + subscribed
  useThemeStore((s) => s.resolvedTheme);

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

  // Legacy "navigate" CustomEvent bridge — pages that still dispatch
  // window events will be caught here and converted to router navigation.
  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (typeof detail === "string") {
        navigate(pageIdToPath(detail));
      }
    };

    window.addEventListener("navigate", handler);
    return () => window.removeEventListener("navigate", handler);
  }, [navigate]);

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

  // Auth-Guard: unauthenticated users see Landing/Auth pages
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
              navigate("/chat");
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
        <Sidebar />
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
              key={location.pathname}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              style={{ flex: 1, overflowY: "auto", overflowX: "hidden", display: "flex", flexDirection: "column" }}
              className="scrollable"
            >
              <Suspense fallback={<PageLoader />}>
                <Routes location={location}>
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/quiz" element={<QuizPage />} />
                  <Route path="/iq-test" element={<IQTestPage />} />
                  <Route path="/learning" element={<LearningPathPage />} />
                  <Route path="/rag" element={<RAGPage />} />
                  <Route path="/abitur" element={<AbiturPage />} />
                  <Route path="/research" element={<ResearchPage />} />
                  <Route path="/gamification" element={<GamificationPage />} />
                  <Route path="/groups" element={<GroupsPage />} />
                  <Route path="/turnier" element={<TurnierPage />} />
                  <Route path="/flashcards" element={<FlashcardsPage />} />
                  <Route path="/notes" element={<NotesPage />} />
                  <Route path="/calendar" element={<CalendarPage />} />
                  <Route path="/multiplayer" element={<MultiplayerPage />} />
                  <Route path="/intelligence" element={<IntelligencePage />} />
                  <Route path="/pomodoro" element={<PomodoroPage />} />
                  <Route path="/shop" element={<ShopPage />} />
                  <Route path="/challenges" element={<ChallengesPage />} />
                  <Route path="/voice" element={<VoicePage />} />
                  <Route path="/quests" element={<QuestsPage />} />
                  <Route path="/events" element={<EventsPage />} />
                  <Route path="/matching" element={<MatchingPage />} />
                  <Route path="/marketplace" element={<MarketplacePage />} />
                  <Route path="/battle-pass" element={<BattlePassPage />} />
                  <Route path="/meine-stats" element={<StatsPage />} />
                  <Route path="/voice-exam" element={<VoiceExamPage />} />
                  <Route path="/scanner" element={<ScannerPage />} />
                  <Route path="/parents" element={<ParentsPage />} />
                  <Route path="/school" element={<SchoolPage />} />
                  <Route path="/admin" element={<AdminPage />} />
                  <Route path="/forschung" element={<ForschungsSeite />} />
                  <Route path="/datenschutz" element={<DatenschutzPage />} />
                  <Route path="/pricing" element={<PricingPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                  {/* Catch-all: redirect to /chat */}
                  <Route path="*" element={<Navigate to="/chat" replace />} />
                </Routes>
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
