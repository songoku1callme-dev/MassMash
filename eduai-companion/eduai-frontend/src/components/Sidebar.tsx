import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "../stores/authStore";
import { useChatStore } from "../stores/chatStore";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import GlobalSearch from "./GlobalSearch";
import { sidebarItem, mobileOverlay, mobileSidebarSlide, APPLE_EASE } from "../lib/animations";
import {
  GraduationCap, MessageSquarePlus, LayoutDashboard, MessageCircle,
  BrainCircuit, BookOpen, Settings, LogOut, Trash2, Menu, X,
  Calculator, Languages, BookOpenCheck, Clock, FlaskConical, Database,
  CreditCard, Star, Globe, Trophy, Users, Shield, Swords, Brain,
  Layers, FileText, CalendarDays, Lock, School, Sparkles, Timer,
  ShoppingBag, Target, Mic, Heart, Calendar, Handshake, Store, BarChart3,
  Camera, AudioLines
} from "lucide-react";

const SUBJECT_ICONS: Record<string, React.ReactNode> = {
  math: <Calculator className="w-4 h-4" />,
  english: <Languages className="w-4 h-4" />,
  german: <BookOpenCheck className="w-4 h-4" />,
  history: <Clock className="w-4 h-4" />,
  science: <FlaskConical className="w-4 h-4" />,
  general: <MessageCircle className="w-4 h-4" />,
};

interface SidebarProps {
  currentPage: string;
  onPageChange: (page: string) => void;
}

export default function Sidebar({ currentPage, onPageChange }: SidebarProps) {
  const { user, logout, isGuest, exitGuestMode } = useAuthStore();
  const { sessions, newChat, loadSession, deleteSession } = useChatStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isAdmin = user?.username === "admin" || user?.is_admin || user?.subscription_tier === "max";

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: "chat", label: "KI-Tutor", icon: <MessageCircle className="w-5 h-5" /> },
    { id: "quiz", label: "Quiz", icon: <BrainCircuit className="w-5 h-5" /> },
    { id: "iq-test", label: "IQ-Test", icon: <Brain className="w-5 h-5" /> },
    { id: "learning", label: "Lernpfad", icon: <BookOpen className="w-5 h-5" /> },
    { id: "rag", label: "Wissensdatenbank", icon: <Database className="w-5 h-5" /> },
    { id: "abitur", label: "Abitur-Simulation", icon: <GraduationCap className="w-5 h-5" /> },
    { id: "research", label: "Internet-Recherche", icon: <Globe className="w-5 h-5" /> },
    { id: "gamification", label: "Gamification", icon: <Trophy className="w-5 h-5" /> },
    { id: "groups", label: "Gruppen-Chats", icon: <Users className="w-5 h-5" /> },
    { id: "turnier", label: "Turniere", icon: <Swords className="w-5 h-5" /> },
    { id: "flashcards", label: "Karteikarten", icon: <Layers className="w-5 h-5" /> },
    { id: "notes", label: "Notizen", icon: <FileText className="w-5 h-5" /> },
    { id: "calendar", label: "Prüfungs-Kalender", icon: <CalendarDays className="w-5 h-5" /> },
    { id: "multiplayer", label: "Multiplayer-Quiz", icon: <Swords className="w-5 h-5" /> },
    { id: "intelligence", label: "KI-Intelligenz", icon: <Sparkles className="w-5 h-5" /> },
    { id: "pomodoro", label: "Pomodoro-Timer", icon: <Timer className="w-5 h-5" /> },
    { id: "shop", label: "Belohnungs-Shop", icon: <ShoppingBag className="w-5 h-5" /> },
    { id: "challenges", label: "Challenges", icon: <Target className="w-5 h-5" /> },
    { id: "voice", label: "Voice-Modus", icon: <Mic className="w-5 h-5" /> },
    { id: "quests", label: "Tägliche Quests", icon: <Target className="w-5 h-5" /> },
    { id: "events", label: "Saisonale Events", icon: <Calendar className="w-5 h-5" /> },
    { id: "matching", label: "Lernpartner", icon: <Handshake className="w-5 h-5" /> },
    { id: "marketplace", label: "Marketplace", icon: <Store className="w-5 h-5" /> },
    { id: "battle-pass", label: "Battle Pass", icon: <Trophy className="w-5 h-5" /> },
    { id: "meine-stats", label: "Meine Statistiken", icon: <BarChart3 className="w-5 h-5" /> },
    { id: "voice-exam", label: "Mündliche Prüfung", icon: <AudioLines className="w-5 h-5" /> },
    { id: "scanner", label: "Schulbuch-Scanner", icon: <Camera className="w-5 h-5" /> },
    { id: "parents", label: "Eltern-Dashboard", icon: <Heart className="w-5 h-5" /> },
    { id: "school", label: "Schul-Lizenzen", icon: <School className="w-5 h-5" /> },
    ...(isAdmin ? [
      { id: "admin", label: "Admin-Panel", icon: <Shield className="w-5 h-5" /> },
      { id: "forschung", label: "Forschungs-Zentrum", icon: <Brain className="w-5 h-5" /> },
    ] : []),
    { id: "datenschutz", label: "Datenschutz", icon: <Lock className="w-5 h-5" /> },
    { id: "pricing", label: "Abo & Preise", icon: <CreditCard className="w-5 h-5" /> },
    { id: "settings", label: "Einstellungen", icon: <Settings className="w-5 h-5" /> },
  ];

  const handleNewChat = () => {
    newChat();
    onPageChange("chat");
    setMobileOpen(false);
  };

  const handleSessionClick = (id: number) => {
    loadSession(id);
    onPageChange("chat");
    setMobileOpen(false);
  };

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Brand */}
      <div className="p-4 flex items-center gap-3 border-b border-lumnos-border">
        <div className="w-10 h-10 rounded-xl bg-lumnos-gradient flex items-center justify-center text-white shadow-glow-sm animate-pulse-glow">
          <span className="text-lg font-bold">{"\u2726"}</span>
        </div>
        <div>
          <h2 className="font-bold text-lumnos-text text-sm">Lumnos</h2>
          <p className="text-xs text-lumnos-muted">KI-Lerncoach</p>
        </div>
      </div>

      {/* New Chat */}
      <div className="p-3">
        <Button onClick={handleNewChat} className="w-full gap-2 lumnos-btn-primary border-0" size="sm">
          <MessageSquarePlus className="w-4 h-4" />
          Neuer Chat
        </Button>
      </div>

      {/* Global Search (Cmd/Ctrl+K) */}
      <div className="px-3 pb-2">
        <GlobalSearch onNavigate={onPageChange} />
      </div>

      {/* Navigation */}
      <nav className="px-3 space-y-1">
        {navItems.map((item, i) => (
          <motion.button
            key={item.id}
            custom={i}
            variants={sidebarItem}
            initial="initial"
            animate="animate"
            whileHover={{ x: 6, backgroundColor: "rgba(99,102,241,0.08)", transition: { duration: 0.2, ease: APPLE_EASE } }}
            whileTap={{ scale: 0.97 }}
            onClick={() => { onPageChange(item.id); setMobileOpen(false); }}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
              currentPage === item.id
                ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium"
                : "text-lumnos-muted hover:bg-lumnos-surface hover:text-lumnos-text"
            }`}
          >
            {item.icon}
            {item.label}
          </motion.button>
        ))}
      </nav>

      {/* Chat History (nur für eingeloggte User) */}
      {!isGuest && (
        <>
          <div className="mt-4 px-3">
            <p className="text-xs font-semibold text-lumnos-muted uppercase tracking-wider mb-2 px-3">
              Letzte Chats
            </p>
          </div>
          <ScrollArea className="flex-1 px-3">
            <div className="space-y-1 pb-4">
              {sessions.slice(0, 10).map((session) => (
                <div
                  key={session.id}
                  className="group flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer hover:bg-lumnos-surface transition-colors"
                  onClick={() => handleSessionClick(session.id)}
                >
                  {SUBJECT_ICONS[session.subject] || SUBJECT_ICONS.general}
                  <span className="flex-1 truncate text-lumnos-muted">
                    {session.title}
                  </span>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                    className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              {sessions.length === 0 && (
                <p className="text-xs text-gray-400 dark:text-gray-500 px-3 py-2">
                  Noch keine Chats vorhanden
                </p>
              )}
            </div>
          </ScrollArea>
        </>
      )}

      {/* Gast-Modus: Spacer wenn keine Chat-History */}
      {isGuest && <div className="flex-1" />}

      {/* UPGRADE BANNER für Free-User */}
      {(!user?.subscription_tier || user.subscription_tier === "free") && (
        <div className="mx-3 mb-3 rounded-xl p-3 cursor-pointer"
             style={{
               background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))",
               border: "1px solid rgba(99,102,241,0.4)",
               boxShadow: "0 0 15px rgba(99,102,241,0.1)"
             }}
             onClick={() => { onPageChange("pricing"); setMobileOpen(false); }}>
          <div className="flex items-center gap-2">
            <span className="text-lg">{"\u26A1"}</span>
            <div className="flex-1">
              <div className="font-bold text-white text-xs">Pro upgraden</div>
              <div className="text-[10px] text-slate-400">Ab 4,99€/Monat</div>
            </div>
            <div className="px-2 py-1 rounded-lg text-[10px] font-bold text-white"
                 style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
              Upgrade
            </div>
          </div>
        </div>
      )}

      {/* User Profile & Logout / Gast-Anmelden */}
      <div className="p-3 border-t border-lumnos-border">
        {isGuest ? (
          <button
            onClick={() => { exitGuestMode(); window.location.reload(); }}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-bold text-white transition-all"
            style={{
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              boxShadow: "0 0 20px rgba(99,102,241,0.4)",
            }}
          >
            <GraduationCap className="w-5 h-5" />
            Anmelden / Registrieren
          </button>
        ) : (
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-lumnos-gradient flex items-center justify-center text-white text-sm font-bold shadow-glow-sm">
              {user?.full_name?.[0] || user?.username?.[0] || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-lumnos-text truncate flex items-center gap-1">
                {user?.full_name || user?.username}
                {user?.subscription_tier === "max" && <Star className="w-3.5 h-3.5 text-purple-500 fill-purple-500" />}
                {user?.subscription_tier === "pro" && <Star className="w-3.5 h-3.5 text-yellow-500 fill-yellow-500" />}
              </p>
              <p className="text-xs text-lumnos-muted">
                {user?.subscription_tier === "max" ? "Max" : user?.subscription_tier === "pro" ? "Pro" : user?.school_type} {user?.school_grade}. Klasse
              </p>
            </div>
            <button
              onClick={logout}
              className="text-gray-400 hover:text-red-500 transition-colors"
              title="Abmelden"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg glass border border-lumnos-border shadow-glow-sm"
      >
        {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            key="sidebar-overlay"
            initial={mobileOverlay.initial}
            animate={mobileOverlay.animate}
            exit={mobileOverlay.exit}
            transition={mobileOverlay.transition}
            className="lg:hidden fixed inset-0 z-40 bg-black/50"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar — Desktop: always visible, Mobile: animated slide */}
      <aside className="hidden lg:block w-72 bg-lumnos-bg border-r border-lumnos-border">
        {sidebarContent}
      </aside>

      <AnimatePresence>
        {mobileOpen && (
          <motion.aside
            key="mobile-sidebar"
            initial={mobileSidebarSlide.initial}
            animate={mobileSidebarSlide.animate}
            exit={mobileSidebarSlide.exit}
            className="lg:hidden fixed inset-y-0 left-0 z-40 w-72 bg-lumnos-bg border-r border-lumnos-border"
          >
            {sidebarContent}
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
