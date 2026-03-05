import { useState } from "react";
import { useAuthStore } from "../stores/authStore";
import ThemeToggle from "../components/ThemeToggle";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
 Settings, User, Shield, Moon, Globe, Save, Loader2, Star, Crown, CreditCard
} from "lucide-react";

export default function SettingsPage() {
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
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <Settings className="w-7 h-7" style={{ color: "var(--icon-color)" }} />
 Einstellungen
 </h1>
 <p className="theme-text-secondary mt-1">Verwalte dein Profil und Einstellungen</p>
 </div>

 {/* Pro Status */}
 {user?.is_pro ? (
 <Card className="border-yellow-200">
 <CardContent className="flex items-center gap-4 p-6">
 <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-yellow-400 to-amber-500 flex items-center justify-center">
 <Crown className="w-6 h-6 text-white" />
 </div>
 <div className="flex-1">
 <p className="font-semibold theme-text flex items-center gap-2">
 Pro-Mitglied
 <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
 </p>
 <p className="text-sm theme-text-secondary">
 Unbegrenzt OCR, Spracheingabe & priorisierte KI-Antworten
 </p>
 </div>
 </CardContent>
 </Card>
 ) : (
 <Card>
 <CardContent className="flex items-center gap-4 p-6">
 <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center">
 <CreditCard className="w-6 h-6 text-white" />
 </div>
 <div className="flex-1">
 <p className="font-semibold theme-text">Kostenloser Plan</p>
 <p className="text-sm theme-text-secondary">
 50 OCR & 50 Spracheingaben pro Monat
 </p>
 </div>
 <Button size="sm">
 <Star className="w-4 h-4 mr-1" />
 Pro Upgrade
 </Button>
 </CardContent>
 </Card>
 )}

 {/* Profile Settings */}
 <Card>
 <CardHeader>
 <div className="flex items-center gap-2">
 <User className="w-5 h-5" style={{ color: "var(--icon-color)" }} />
 <CardTitle className="text-base">Profil</CardTitle>
 </div>
 <CardDescription>Deine persönlichen Informationen</CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
 <div>
 <label className="text-sm font-medium theme-text-tertiary mb-1 block">Name</label>
 <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
 </div>
 <div>
 <label className="text-sm font-medium theme-text-tertiary mb-1 block">E-Mail</label>
 <Input value={user?.email || ""} disabled className="opacity-60" />
 </div>
 <div>
 <label className="text-sm font-medium theme-text-tertiary mb-1 block">Benutzername</label>
 <Input value={user?.username || ""} disabled className="opacity-60" />
 </div>
 <div>
 <label className="text-sm font-medium theme-text-tertiary mb-1 block">Mitglied seit</label>
 <Input
 value={user?.created_at ? new Date(user.created_at).toLocaleDateString("de-DE") : ""}
 disabled
 className="opacity-60"
 />
 </div>
 </div>

 <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
 <div>
 <label className="text-sm font-medium theme-text-tertiary mb-1 block">Klasse</label>
 <select
 value={schoolGrade}
 onChange={(e) => setSchoolGrade(e.target.value)}
 className="theme-input flex h-10 w-full px-3 py-2 text-sm"
 >
 {["5", "6", "7", "8", "9", "10", "11", "12", "13"].map((g) => (
 <option key={g} value={g}>{g}. Klasse</option>
 ))}
 </select>
 </div>
 <div>
 <label className="text-sm font-medium theme-text-tertiary mb-1 block">Schulart</label>
 <select
 value={schoolType}
 onChange={(e) => setSchoolType(e.target.value)}
 className="theme-input flex h-10 w-full px-3 py-2 text-sm"
 >
 <option value="Gymnasium">Gymnasium</option>
 <option value="Realschule">Realschule</option>
 <option value="Gesamtschule">Gesamtschule</option>
 </select>
 </div>
 <div>
 <label className="text-sm font-medium theme-text-tertiary mb-1 block">Sprache</label>
 <select
 value={preferredLanguage}
 onChange={(e) => setPreferredLanguage(e.target.value)}
 className="theme-input flex h-10 w-full px-3 py-2 text-sm"
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
 <Moon className="w-5 h-5" style={{ color: "var(--icon-color)" }} />
 <CardTitle className="text-base">Erscheinungsbild</CardTitle>
 </div>
 <CardDescription>Dark / Light / System</CardDescription>
 </CardHeader>
 <CardContent>
 <div className="flex items-center justify-between gap-4 flex-wrap">
 <div>
 <p className="font-medium theme-text">Theme</p>
 <p className="text-sm theme-text-secondary">Wähle Dark, Light oder System</p>
 </div>
 <ThemeToggle />
 </div>
 </CardContent>
 </Card>

 {/* Privacy / GDPR */}
 <Card>
 <CardHeader>
 <div className="flex items-center gap-2">
 <Shield className="w-5 h-5" style={{ color: "var(--icon-color)" }} />
 <CardTitle className="text-base">Datenschutz (DSGVO)</CardTitle>
 </div>
 <CardDescription>Deine Daten, deine Kontrolle</CardDescription>
 </CardHeader>
 <CardContent className="space-y-3">
 <div
 className="flex items-center gap-3 p-3 rounded-xl"
 style={{ background: "var(--success-bg)", border: "1px solid var(--border-color)" }}
 >
 <Shield className="w-5 h-5" style={{ color: "var(--success-text)" }} />
 <div>
 <p className="text-sm font-medium" style={{ color: "var(--success-text)" }}>DSGVO-konform</p>
 <p className="text-xs theme-text-secondary">
 Deine Daten werden nach EU-Datenschutzrichtlinien verarbeitet
 </p>
 </div>
 </div>
 <div className="space-y-2 text-sm theme-text-secondary">
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
