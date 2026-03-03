import { useState } from "react";
import { useAuthStore } from "../stores/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BookOpen, GraduationCap, Chrome, Zap } from "lucide-react";
import { setTokens } from "../services/api";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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

  return (
    <div className="min-h-screen cyber-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-lumnos-gradient text-white mb-4 shadow-glow-md animate-pulse-glow">
            <span className="text-2xl font-bold">{"\u2726"}</span>
          </div>
          <h1 className="text-3xl font-bold text-lumnos-text">Lumnos</h1>
          <p className="text-lumnos-muted mt-1 flex items-center justify-center gap-1">
            <BookOpen className="w-4 h-4" />
            Dein KI-Lerncoach
          </p>
        </div>

        <Card className="shadow-xl border-0">
          <CardHeader className="text-center pb-2">
            <CardTitle>{isLogin ? "Anmelden" : "Registrieren"}</CardTitle>
            <CardDescription>
              {isLogin
                ? "Melde dich an, um weiterzulernen"
                : "Erstelle ein Konto und starte deine Lernreise"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Perfect School 4.1 Block 3.3: Google OAuth via Clerk */}
            <Button
              variant="outline"
              className="w-full mb-4 flex items-center gap-2"
              size="lg"
              onClick={() => {
                const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
                if (clerkKey) {
                  // Redirect to Clerk hosted sign-in with Google
                  const domain = clerkKey.replace("pk_test_", "").replace("pk_live_", "").replace(/\$.*/, "");
                  window.location.href = `https://${domain}.clerk.accounts.dev/sign-in?redirect_url=${encodeURIComponent(window.location.origin + "/dashboard")}`;
                } else {
                  setError("Google OAuth erfordert Clerk-Konfiguration. Kontaktiere den Admin.");
                }
              }}
            >
              <Chrome className="w-5 h-5 text-blue-500" />
              Mit Google anmelden
            </Button>

            <div className="relative mb-4">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-gray-300 dark:border-gray-600" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white dark:bg-gray-900 px-2 text-gray-500">oder</span>
              </div>
            </div>

            {isLogin ? (
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Benutzername</label>
                  <Input
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Dein Benutzername"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Passwort</label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Dein Passwort"
                    required
                  />
                </div>
                <Button type="submit" className="w-full" size="lg" disabled={loading}>
                  {loading ? "Anmelden..." : "Anmelden"}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Name</label>
                    <Input
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Vor- und Nachname"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Benutzername</label>
                    <Input
                      value={regUsername}
                      onChange={(e) => setRegUsername(e.target.value)}
                      placeholder="Benutzername"
                      required
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">E-Mail</label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="deine@email.de"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Passwort</label>
                  <Input
                    type="password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="Mindestens 6 Zeichen"
                    required
                    minLength={6}
                  />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Klasse</label>
                    <select
                      value={schoolGrade}
                      onChange={(e) => setSchoolGrade(e.target.value)}
                      className="flex h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
                    >
                      {["5", "6", "7", "8", "9", "10", "11", "12", "13"].map((g) => (
                        <option key={g} value={g}>{g}. Klasse</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Schulart</label>
                    <select
                      value={schoolType}
                      onChange={(e) => setSchoolType(e.target.value)}
                      className="flex h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
                    >
                      <option value="Gymnasium">Gymnasium</option>
                      <option value="Realschule">Realschule</option>
                      <option value="Gesamtschule">Gesamtschule</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Sprache</label>
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="flex h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
                    >
                      <option value="de">Deutsch</option>
                      <option value="en">English</option>
                    </select>
                  </div>
                </div>
                <Button type="submit" className="w-full" size="lg" disabled={loading}>
                  {loading ? "Registrieren..." : "Konto erstellen"}
                </Button>
              </form>
            )}

            {/* DEV BYPASS LOGIN — server-side via proxy, no fetch() needed */}
            {import.meta.env.VITE_DEV_BYPASS === "true" && (
              <div className="mt-4 pt-4 border-t border-dashed border-red-300 dark:border-red-700">
                <Button
                  variant="destructive"
                  className="w-full flex items-center gap-2"
                  size="lg"
                  onClick={() => {
                    // Navigate to /dev-bypass — proxy handles everything server-side
                    // No fetch() needed, avoids credentials-in-URL browser block
                    window.location.href = "/dev-bypass";
                  }}
                  disabled={loading}
                >
                  <Zap className="w-5 h-5" />
                  DEV BYPASS LOGIN (Max-Tier Testing)
                </Button>
                <p className="text-xs text-red-400 text-center mt-1">Nur für Entwickler-Testing</p>
              </div>
            )}

            <div className="mt-4 text-center">
              <button
                onClick={() => { setIsLogin(!isLogin); setError(""); }}
                className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
              >
                {isLogin
                  ? "Noch kein Konto? Jetzt registrieren"
                  : "Bereits registriert? Jetzt anmelden"}
              </button>
            </div>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-gray-400 dark:text-gray-600 mt-4">
          DSGVO-konform. Deine Daten sind sicher.
        </p>
      </div>
    </div>
  );
}
