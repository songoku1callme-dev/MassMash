import { useState } from "react";
import { SignIn, SignUp } from "@clerk/clerk-react";
import { dark } from "@clerk/themes";
import { useAuthStore } from "../stores/authStore";
import { BookOpen, Zap, Eye, EyeOff } from "lucide-react";

const CLERK_ENABLED = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

/* ── Clerk Cyber-Zen Appearance ── */
const clerkAppearance = {
  baseTheme: dark,
  variables: {
    colorBackground: "#0d0d2b",
    colorInputBackground: "rgba(255,255,255,0.05)",
    colorInputText: "#ffffff",
    colorText: "#ffffff",
    colorTextSecondary: "#94a3b8",
    colorPrimary: "#6366f1",
    colorDanger: "#ef4444",
    borderRadius: "12px",
    fontFamily: "inherit",
  },
  elements: {
    rootBox: "w-full",
    card: "bg-transparent shadow-none border-0",
    headerTitle: "text-white text-2xl font-bold",
    headerSubtitle: "text-slate-400 text-sm",
    socialButtonsBlockButton:
      "bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-all",
    socialButtonsBlockButtonText: "text-white",
    dividerLine: "bg-white/10",
    dividerText: "text-slate-500",
    formFieldLabel: "text-slate-300 text-sm",
    formFieldInput:
      "bg-white/5 border-white/10 text-white focus:border-indigo-500 rounded-xl",
    formButtonPrimary:
      "bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-semibold rounded-xl transition-all shadow-lg",
    footerActionLink: "text-indigo-400 hover:text-indigo-300",
    footerActionText: "text-slate-400",
    identityPreviewText: "text-white",
    identityPreviewEditButton: "text-indigo-400",
    formFieldAction: "text-indigo-400",
    alertText: "text-red-400",
    formFieldErrorText: "text-red-400",
    otpCodeFieldInput: "bg-white/5 border-white/10 text-white",
  },
};

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Login fields
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // Register fields
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [regUsername, setRegUsername] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [schoolGrade, setSchoolGrade] = useState("10");
  const [schoolType, setSchoolType] = useState("Gymnasium");
  const [language, setLanguage] = useState("de");

  const { login, register } = useAuthStore();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register({
        email,
        username: regUsername,
        password: regPassword,
        full_name: fullName,
        school_grade: schoolGrade,
        school_type: schoolType,
        preferred_language: language,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registrierung fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  /* ── Shared input classes (Cyber-Zen) ── */
  const inputClass =
    "w-full h-11 rounded-xl bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] " +
    "text-white placeholder-slate-500 px-4 text-sm focus:outline-none focus:border-indigo-500/50 " +
    "focus:ring-1 focus:ring-indigo-500/30 transition-all";

  const labelClass = "text-sm font-medium text-slate-300 mb-1.5 block";

  const selectClass =
    "w-full h-11 rounded-xl bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] " +
    "text-white px-3 text-sm focus:outline-none focus:border-indigo-500/50 " +
    "focus:ring-1 focus:ring-indigo-500/30 transition-all appearance-none cursor-pointer";

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        background: "linear-gradient(135deg, #0a0a1a 0%, #0d0d2b 50%, #0a0a1a 100%)",
      }}
    >
      {/* Subtle background glow */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 600px 400px at 50% 30%, rgba(99,102,241,0.08) 0%, transparent 70%)",
        }}
      />

      <div className="w-full max-w-md relative z-10 animate-fade-in">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl text-white mb-4"
            style={{
              background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
              boxShadow: "0 0 30px rgba(99,102,241,0.3), 0 0 60px rgba(139,92,246,0.15)",
            }}
          >
            <span className="text-2xl font-bold">{"\u2726"}</span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Lumnos</h1>
          <p className="text-slate-400 mt-1 flex items-center justify-center gap-1.5 text-sm">
            <BookOpen className="w-4 h-4" />
            KI-Lerncoach
          </p>
        </div>

        {/* Main Card — Glassmorphismus */}
        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            borderRadius: "24px",
            padding: "40px",
          }}
        >
          {/* Clerk OAuth Login/Register */}
          {CLERK_ENABLED ? (
            <div className="flex flex-col items-center">
              {isLogin ? (
                <SignIn routing="hash" appearance={clerkAppearance} />
              ) : (
                <SignUp routing="hash" appearance={clerkAppearance} />
              )}
              <div className="mt-4 text-center">
                <button
                  onClick={() => setIsLogin(!isLogin)}
                  className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  {isLogin
                    ? "Noch kein Konto? Jetzt registrieren"
                    : "Bereits registriert? Jetzt anmelden"}
                </button>
              </div>
            </div>
          ) : (
            /* Fallback: Manual Login/Register when Clerk is not configured */
            <>
              {/* Tab Switcher */}
              <div className="flex gap-1 p-1 rounded-xl bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] mb-6">
                <button
                  onClick={() => { setIsLogin(true); setError(""); }}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isLogin
                      ? "bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-lg shadow-indigo-500/25"
                      : "text-slate-400 hover:text-slate-300"
                  }`}
                >
                  Anmelden
                </button>
                <button
                  onClick={() => { setIsLogin(false); setError(""); }}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    !isLogin
                      ? "bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-lg shadow-indigo-500/25"
                      : "text-slate-400 hover:text-slate-300"
                  }`}
                >
                  Registrieren
                </button>
              </div>

              {/* Subtitle */}
              <p className="text-slate-400 text-sm text-center mb-6">
                {isLogin
                  ? "Melde dich an, um weiterzulernen"
                  : "Erstelle ein Konto und starte deine Lernreise"}
              </p>

              {/* Error Message — Cyber-Zen styled */}
              {error && (
                <div
                  className="mb-5 p-3 rounded-xl text-sm flex items-center gap-2"
                  style={{
                    background: "rgba(239,68,68,0.1)",
                    border: "1px solid rgba(239,68,68,0.2)",
                    color: "#f87171",
                  }}
                >
                  <span className="text-red-400 text-base">!</span>
                  {error}
                </div>
              )}

              {isLogin ? (
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label className={labelClass}>Benutzername</label>
                    <input
                      className={inputClass}
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="Dein Benutzername"
                      required
                      autoComplete="username"
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Passwort</label>
                    <div className="relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        className={inputClass + " pr-11"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Dein Passwort"
                        required
                        autoComplete="current-password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full h-11 rounded-xl font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{
                      background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                      boxShadow: loading ? "none" : "0 4px 20px rgba(99,102,241,0.25)",
                    }}
                  >
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Anmelden...
                      </span>
                    ) : (
                      "Anmelden"
                    )}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleRegister} className="space-y-3.5">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={labelClass}>Name</label>
                      <input
                        className={inputClass}
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="Vor- und Nachname"
                        required
                        autoComplete="name"
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Benutzername</label>
                      <input
                        className={inputClass}
                        value={regUsername}
                        onChange={(e) => setRegUsername(e.target.value)}
                        placeholder="Benutzername"
                        required
                        autoComplete="username"
                      />
                    </div>
                  </div>
                  <div>
                    <label className={labelClass}>E-Mail</label>
                    <input
                      type="email"
                      className={inputClass}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="deine@email.de"
                      required
                      autoComplete="email"
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Passwort</label>
                    <div className="relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        className={inputClass + " pr-11"}
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        placeholder="Mindestens 6 Zeichen"
                        required
                        minLength={6}
                        autoComplete="new-password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className={labelClass}>Klasse</label>
                      <select
                        value={schoolGrade}
                        onChange={(e) => setSchoolGrade(e.target.value)}
                        className={selectClass}
                      >
                        {["5", "6", "7", "8", "9", "10", "11", "12", "13"].map((g) => (
                          <option key={g} value={g} className="bg-[#0d0d2b] text-white">
                            {g}. Klasse
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>Schulart</label>
                      <select
                        value={schoolType}
                        onChange={(e) => setSchoolType(e.target.value)}
                        className={selectClass}
                      >
                        <option value="Gymnasium" className="bg-[#0d0d2b] text-white">Gymnasium</option>
                        <option value="Realschule" className="bg-[#0d0d2b] text-white">Realschule</option>
                        <option value="Gesamtschule" className="bg-[#0d0d2b] text-white">Gesamtschule</option>
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>Sprache</label>
                      <select
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                        className={selectClass}
                      >
                        <option value="de" className="bg-[#0d0d2b] text-white">Deutsch</option>
                        <option value="en" className="bg-[#0d0d2b] text-white">English</option>
                      </select>
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full h-11 rounded-xl font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{
                      background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                      boxShadow: loading ? "none" : "0 4px 20px rgba(99,102,241,0.25)",
                    }}
                  >
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Registrieren...
                      </span>
                    ) : (
                      "Konto erstellen"
                    )}
                  </button>
                </form>
              )}

              {/* Google Login Button */}
              <div className="mt-5">
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex-1 h-px bg-[rgba(255,255,255,0.08)]" />
                  <span className="text-slate-500 text-xs">oder</span>
                  <div className="flex-1 h-px bg-[rgba(255,255,255,0.08)]" />
                </div>
                <button
                  type="button"
                  className="w-full h-11 rounded-xl font-medium text-white flex items-center justify-center gap-3 transition-all hover:bg-[rgba(255,255,255,0.08)]"
                  style={{
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.1)",
                  }}
                  onClick={() => {
                    // Will be handled by Clerk in production
                    setError("Google-Login wird bald verfuegbar sein!");
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Mit Google anmelden
                </button>
              </div>

              {/* DEV BYPASS LOGIN */}
              {import.meta.env.VITE_DEV_BYPASS === "true" && (
                <div
                  className="mt-5 pt-4"
                  style={{ borderTop: "1px dashed rgba(239,68,68,0.3)" }}
                >
                  <button
                    className="w-full h-11 rounded-xl font-semibold text-white flex items-center justify-center gap-2 transition-all hover:opacity-90"
                    style={{
                      background: "linear-gradient(135deg, #dc2626 0%, #991b1b 100%)",
                      boxShadow: "0 4px 15px rgba(220,38,38,0.2)",
                    }}
                    onClick={() => {
                      window.location.href = "/dev-bypass";
                    }}
                    disabled={loading}
                  >
                    <Zap className="w-4 h-4" />
                    DEV BYPASS LOGIN (Max-Tier)
                  </button>
                  <p className="text-xs text-red-400/60 text-center mt-1.5">Nur fuer Entwickler-Testing</p>
                </div>
              )}

              {/* Toggle Login/Register */}
              <div className="mt-5 text-center">
                <button
                  onClick={() => { setIsLogin(!isLogin); setError(""); }}
                  className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  {isLogin
                    ? "Noch kein Konto? Jetzt registrieren"
                    : "Bereits registriert? Jetzt anmelden"}
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-slate-600 mt-5">
          DSGVO-konform. Deine Daten sind sicher.
        </p>
      </div>
    </div>
  );
}
