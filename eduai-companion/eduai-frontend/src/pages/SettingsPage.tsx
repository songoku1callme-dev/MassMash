import { useState } from "react";
import { useAuthStore } from "../stores/authStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Settings, User, Shield, Moon, Sun, Globe, Save, Loader2
} from "lucide-react";

interface SettingsPageProps {
  darkMode: boolean;
  onDarkModeToggle: () => void;
}

export default function SettingsPage({ darkMode, onDarkModeToggle }: SettingsPageProps) {
  const { user, updateUser, logout } = useAuthStore();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [schoolGrade, setSchoolGrade] = useState(user?.school_grade || "10");
  const [schoolType, setSchoolType] = useState(user?.school_type || "Gymnasium");
  const [preferredLanguage, setPreferredLanguage] = useState(user?.preferred_language || "de");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateUser({
        full_name: fullName,
        school_grade: schoolGrade,
        school_type: schoolType,
        preferred_language: preferredLanguage,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to update profile:", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 lg:p-6 max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Settings className="w-7 h-7 text-blue-600" />
          Einstellungen
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Verwalte dein Profil und Einstellungen
        </p>
      </div>

      {/* Profile Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-blue-600" />
            <CardTitle className="text-base">Profil</CardTitle>
          </div>
          <CardDescription>Deine persönlichen Informationen</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Name</label>
              <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">E-Mail</label>
              <Input value={user?.email || ""} disabled className="opacity-60" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Benutzername</label>
              <Input value={user?.username || ""} disabled className="opacity-60" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">Mitglied seit</label>
              <Input
                value={user?.created_at ? new Date(user.created_at).toLocaleDateString("de-DE") : ""}
                disabled
                className="opacity-60"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
                value={preferredLanguage}
                onChange={(e) => setPreferredLanguage(e.target.value)}
                className="flex h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              >
                <option value="de">Deutsch</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>

          <Button onClick={handleSave} className="gap-2" disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saved ? "Gespeichert!" : "Speichern"}
          </Button>
        </CardContent>
      </Card>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            {darkMode ? <Moon className="w-5 h-5 text-blue-600" /> : <Sun className="w-5 h-5 text-blue-600" />}
            <CardTitle className="text-base">Darstellung</CardTitle>
          </div>
          <CardDescription>Passe das Aussehen an</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Dark Mode</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Dunkles Design aktivieren</p>
            </div>
            <button
              onClick={onDarkModeToggle}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                darkMode ? "bg-blue-600" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  darkMode ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Privacy / GDPR */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-blue-600" />
            <CardTitle className="text-base">Datenschutz (DSGVO)</CardTitle>
          </div>
          <CardDescription>Deine Daten, deine Kontrolle</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
            <Shield className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <div>
              <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300">DSGVO-konform</p>
              <p className="text-xs text-emerald-600 dark:text-emerald-400">
                Deine Daten werden nach EU-Datenschutzrichtlinien verarbeitet
              </p>
            </div>
          </div>
          <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <p>Wir speichern nur die Daten, die für dein Lernerlebnis notwendig sind:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Profildaten (Name, Schule, Klasse)</li>
              <li>Lernfortschritt und Quiz-Ergebnisse</li>
              <li>Chat-Verlauf für personalisierte Hilfe</li>
            </ul>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="outline" size="sm">
              <Globe className="w-4 h-4 mr-2" />
              Daten exportieren
            </Button>
            <Button variant="destructive" size="sm" onClick={logout}>
              Konto löschen
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
