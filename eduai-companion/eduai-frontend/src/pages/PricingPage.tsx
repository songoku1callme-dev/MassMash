import { useState } from "react";
import { useAuthStore } from "../stores/authStore";
import { stripeApi } from "../services/api";
import { useIsOwner } from "../utils/ownerEmails";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
 Star, Check, Zap, Camera, Mic, FileText, BarChart3, Crown, Loader2,
 Users, GraduationCap, Palette, Brain, Shield, Rocket, Heart
} from "lucide-react";

type PlanKey = "pro" | "max" | "eltern";
type BillingPeriod = "monthly" | "yearly";

export default function PricingPage() {
 const { user } = useAuthStore();
 const [loading, setLoading] = useState<PlanKey | null>(null);
 const [error, setError] = useState("");
 const [billing, setBilling] = useState<BillingPeriod>("yearly");

 const tier = user?.subscription_tier || "free";
 const isOwner = useIsOwner();

 const paymentLinks: Record<PlanKey, Record<BillingPeriod, string | undefined>> = {
 pro: {
 monthly: import.meta.env.VITE_STRIPE_LINK_PRO_MONTHLY,
 yearly: import.meta.env.VITE_STRIPE_LINK_PRO_YEARLY,
 },
 max: {
 monthly: import.meta.env.VITE_STRIPE_LINK_MAX_MONTHLY,
 yearly: import.meta.env.VITE_STRIPE_LINK_MAX_YEARLY,
 },
 eltern: {
 monthly: import.meta.env.VITE_STRIPE_LINK_ELTERN_MONTHLY,
 yearly: import.meta.env.VITE_STRIPE_LINK_ELTERN_YEARLY,
 },
 };

 const handleUpgrade = async (plan: PlanKey) => {
 if (isOwner) return; // Owner braucht kein Upgrade
 setLoading(plan);
 setError("");

 try {
 // Preferred: Stripe Payment Links (supports prefilled_email)
 const paymentLink = paymentLinks[plan]?.[billing];
 if (paymentLink) {
 const url = new URL(paymentLink);
 if (user?.email) {
 url.searchParams.set("prefilled_email", user.email);
 }
 window.location.href = url.toString();
 return;
 }

 // Fallback: API-based Checkout Session
 const currentUrl = window.location.origin;
 const result = await stripeApi.createCheckout({
 success_url: `${currentUrl}/dashboard?upgrade=success&plan=${plan}`,
 cancel_url: `${currentUrl}/pricing`,
 plan,
 billing,
 });
 if (result.checkout_url) {
 window.location.href = result.checkout_url;
 }
 } catch (err) {
 setError(err instanceof Error ? err.message : "Fehler beim Erstellen der Checkout-Session");
 } finally {
 setLoading(null);
 }
 };

 const freePlan = [
 "KI-Tutor Chat (begrenzt)",
 "50 OCR-Anfragen/Monat",
 "50 Spracheingaben/Monat",
 "5 KI-Stile",
 "Basis Quiz-Themen (16 Fächer)",
 "16 Fächer + Quiz & Lernpfade",
 ];

 const proPlan = [
 "Unbegrenzt KI-Tutor Chat",
 "Unbegrenzt OCR & Mathe-Fotos",
 "Unbegrenzt Spracheingabe & Vorlesen",
 "12 KI-Stile (+ Humorvoll, Abi-Coach, Mentor, ...)",
 "300+ Quiz-Themen über 16 Fächer",
 "Custom Quiz-Themen erstellen",
 "PDF-Export von Chats",
 "Priorisierte KI (schnellere Antworten)",
 ];

 const maxPlan = [
 "Alles aus Pro +",
 "20 KI-Stile (+ Einstein, Zen-Meister, Cyber-Coach, ...)",
 "300+ Quiz-Themen über 16 Fächer",
 "Wochen-Coach (8-Wochen Abitur-Lernplan)",
 "Abitur-Simulation (Timer, Notenpunkte)",
 "Internet-Recherche (Live Quellen)",
 "User Memory (Adaptive Schwachstellen)",
 "Gruppen-Chats mit Mitschülern",
 "Eltern-Share & PDF/Word Export",
 ];

 return (
 <div className="min-h-screen p-4 lg:p-6 max-w-6xl mx-auto space-y-8" style={{ background: "var(--lumnos-bg)" }}>
 {/* Header */}
 <div className="text-center">
 <h1 className="text-2xl sm:text-3xl font-bold text-white">
 Wähle deinen Plan
 </h1>
 <p className="text-slate-400 mt-2 text-base sm:text-lg">
 Lerne besser mit Lumnos — vom Einsteiger bis zum Abitur
 </p>
 </div>

 {/* Billing Toggle */}
 <div className="flex items-center justify-center gap-4">
 <span className={`text-sm font-medium ${billing === "monthly" ? "text-white" : "text-slate-500"}`}>
 Monatlich
 </span>
 <button
 onClick={() => setBilling(billing === "monthly" ? "yearly" : "monthly")}
 className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors ${
 billing === "yearly" ? "bg-emerald-600" : "bg-slate-600"
 }`}
 >
 <span
 className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
 billing === "yearly" ? "translate-x-8" : "translate-x-1"
 }`}
 />
 </button>
 <span className={`text-sm font-medium ${billing === "yearly" ? "text-white" : "text-slate-500"}`}>
 Jährlich
 </span>
 {billing === "yearly" && (
 <span className="text-xs font-bold text-emerald-400 bg-emerald-900/30 px-2 py-1 rounded-full">
 2 Monate GRATIS!
 </span>
 )}
 </div>

 {(tier !== "free" || isOwner) && (
 <div className="flex items-center justify-center gap-2 p-4 rounded-xl border border-yellow-800" style={{ background: "rgba(234,179,8,0.1)" }}>
 <Crown className="w-6 h-6 text-yellow-500" />
 <span className="text-lg font-semibold text-yellow-300">
 Du bist {isOwner ? "Owner" : tier === "max" ? "Max" : "Pro"}-Mitglied!
 </span>
 <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
 </div>
 )}

 {error && (
 <div className="p-4 rounded-lg bg-red-900/20 text-red-400 text-center">
 {error}
 </div>
 )}

 {/* Pricing Cards - 4 Tiers */}
 <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
 {/* Free Plan */}
 <Card className="relative border border-indigo-500/20 bg-[var(--lumnos-surface)]">
 <CardHeader>
 <CardTitle className="text-xl text-white">Kostenlos</CardTitle>
 <CardDescription className="text-slate-400">Perfekt zum Ausprobieren</CardDescription>
 <div className="mt-4">
 <span className="text-4xl font-bold text-white">0€</span>
 <span className="text-slate-400 ml-1">/Monat</span>
 </div>
 </CardHeader>
 <CardContent>
 <ul className="space-y-3">
 {freePlan.map((feature, i) => (
 <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
 <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
 {feature}
 </li>
 ))}
 </ul>
 <Button variant="outline" className="w-full mt-6 border-indigo-500/30 text-slate-300" disabled>
 {tier === "free" ? "Aktueller Plan" : "Kostenlos"}
 </Button>
 </CardContent>
 </Card>

 {/* Pro Plan */}
 <Card className="relative border-2 border-indigo-500 bg-[var(--lumnos-surface)]" style={{ boxShadow: "0 0 30px rgba(99,102,241,0.2)" }}>
 <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 text-white text-xs font-bold rounded-full uppercase tracking-wider" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
 Beliebt
 </div>
 <CardHeader>
 <CardTitle className="text-xl flex items-center gap-2 text-white">
 Pro
 <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
 </CardTitle>
 <CardDescription className="text-slate-400">Für ambitionierte Schüler</CardDescription>
 <div className="mt-4">
 <span className="text-4xl font-bold text-white">{billing === "yearly" ? "39,99" : "4,99"}€</span>
 <span className="text-slate-400 ml-1">/{billing === "yearly" ? "Jahr" : "Monat"}</span>
 </div>
 {billing === "yearly" && (
 <p className="text-sm text-emerald-600 font-medium mt-1">Spare 20€ vs. monatlich!</p>
 )}
 </CardHeader>
 <CardContent>
 <ul className="space-y-3">
 {proPlan.map((feature, i) => (
 <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
 <Zap className="w-4 h-4 text-indigo-400 flex-shrink-0" />
 {feature}
 </li>
 ))}
 </ul>
 {tier === "pro" || tier === "max" ? (
 <Button className="w-full mt-6 bg-emerald-600 hover:bg-emerald-700" disabled>
 <Check className="w-4 h-4 mr-2" />
 {tier === "pro" ? "Aktiv" : "Enthalten in Max"}
 </Button>
 ) : (
 <Button
 className="w-full mt-6 bg-blue-600 hover:bg-blue-700"
 onClick={() => handleUpgrade("pro")}
 disabled={loading !== null}
 >
 {loading === "pro" ? (
 <Loader2 className="w-4 h-4 mr-2 animate-spin" />
 ) : (
 <Star className="w-4 h-4 mr-2" />
 )}
 {loading === "pro" ? "Wird geladen..." : "Pro holen"}
 </Button>
 )}
 </CardContent>
 </Card>

 {/* Max Plan */}
 <Card className="relative border-2 border-purple-500 bg-[var(--lumnos-surface)]" style={{ boxShadow: "0 0 30px rgba(139,92,246,0.2)" }}>
 <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-purple-600 to-pink-600 text-white text-xs font-bold rounded-full uppercase tracking-wider">
 Premium
 </div>
 <CardHeader>
 <CardTitle className="text-xl flex items-center gap-2 text-white">
 Max
 <Crown className="w-5 h-5 text-purple-400" />
 </CardTitle>
 <CardDescription className="text-slate-400">Für Abitur-Champions</CardDescription>
 <div className="mt-4">
 <span className="text-4xl font-bold text-white">{billing === "yearly" ? "79,99" : "9,99"}€</span>
 <span className="text-slate-400 ml-1">/{billing === "yearly" ? "Jahr" : "Monat"}</span>
 </div>
 {billing === "yearly" && (
 <p className="text-sm text-emerald-600 font-medium mt-1">Spare 40 EUR vs. monatlich! (2 Monate GRATIS)</p>
 )}
 </CardHeader>
 <CardContent>
 <ul className="space-y-3">
 {maxPlan.map((feature, i) => (
 <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
 <Crown className="w-4 h-4 text-purple-400 flex-shrink-0" />
 {feature}
 </li>
 ))}
 </ul>
 {tier === "max" ? (
 <Button className="w-full mt-6 bg-emerald-600 hover:bg-emerald-700" disabled>
 <Check className="w-4 h-4 mr-2" />
 Aktiv
 </Button>
 ) : (
 <Button
 className="w-full mt-6 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
 onClick={() => handleUpgrade("max")}
 disabled={loading !== null}
 >
 {loading === "max" ? (
 <Loader2 className="w-4 h-4 mr-2 animate-spin" />
 ) : (
 <Rocket className="w-4 h-4 mr-2" />
 )}
 {loading === "max" ? "Wird geladen..." : "Max holen"}
 </Button>
 )}
 </CardContent>
 </Card>

 {/* Eltern-Abo Plan - Supreme 11.0 Phase 10 */}
 <Card className="relative border-2 border-pink-500 bg-[var(--lumnos-surface)]" style={{ boxShadow: "0 0 30px rgba(236,72,153,0.15)" }}>
 <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-pink-500 text-white text-xs font-bold rounded-full uppercase tracking-wider">
 Für Eltern
 </div>
 <CardHeader>
 <CardTitle className="text-xl flex items-center gap-2 text-white">
 Eltern
 <Heart className="w-5 h-5 text-pink-400" />
 </CardTitle>
 <CardDescription className="text-slate-400">Lernfortschritt deines Kindes verfolgen</CardDescription>
 <div className="mt-4">
 <span className="text-4xl font-bold text-white">{billing === "yearly" ? "23,99" : "2,99"}€</span>
 <span className="text-slate-400 ml-1">/{billing === "yearly" ? "Jahr" : "Monat"}</span>
 </div>
 {billing === "yearly" && (
 <p className="text-sm text-emerald-600 font-medium mt-1">Spare 12 EUR vs. monatlich!</p>
 )}
 </CardHeader>
 <CardContent>
 <ul className="space-y-3">
 {[
 "Lernfortschritt in Echtzeit",
 "Wöchentliche E-Mail Berichte",
 "Streak-Alerts (wenn Kind nicht lernt)",
 "Schwächen-Analyse pro Fach",
 "Prüfungs-Kalender Einblick",
 "Aktivitäts-Statistiken",
 ].map((feature, i) => (
 <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
 <Heart className="w-4 h-4 text-pink-400 flex-shrink-0" />
 {feature}
 </li>
 ))}
 </ul>
 <Button
 className="w-full mt-6 bg-pink-500 hover:bg-pink-600"
 onClick={() => handleUpgrade("eltern")}
 disabled={loading !== null}
 >
 {loading === "eltern" ? (
 <Loader2 className="w-4 h-4 mr-2 animate-spin" />
 ) : (
 <Heart className="w-4 h-4 mr-2" />
 )}
 {loading === "eltern" ? "Wird geladen..." : "Eltern-Abo holen"}
 </Button>
 </CardContent>
 </Card>
 </div>

 {/* Feature Comparison */}
 <Card className="border border-indigo-500/20 bg-[var(--lumnos-surface)]">
 <CardHeader>
 <CardTitle className="text-lg text-white">Alle Features im Überblick</CardTitle>
 </CardHeader>
 <CardContent>
 <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
 <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-indigo-500/10">
 <Palette className="w-5 h-5 text-purple-500 mt-0.5" />
 <div>
 <p className="font-medium text-white text-sm">20 KI-Persönlichkeiten</p>
 <p className="text-xs text-slate-400">Von Freundlich bis Einstein, Zen-Meister, Cyber-Coach</p>
 </div>
 </div>
 <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-indigo-500/10">
 <Brain className="w-5 h-5 text-blue-500 mt-0.5" />
 <div>
 <p className="font-medium text-white text-sm">300+ Quiz-Themen</p>
 <p className="text-xs text-slate-400">16 Fächer, alle Klassenstufen</p>
 </div>
 </div>
 <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-indigo-500/10">
 <Camera className="w-5 h-5 text-blue-500 mt-0.5" />
 <div>
 <p className="font-medium text-white text-sm">Unbegrenzt OCR</p>
 <p className="text-xs text-slate-400">Mathe-Fotos ohne Limit (Pro+)</p>
 </div>
 </div>
 <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-indigo-500/10">
 <Mic className="w-5 h-5 text-blue-500 mt-0.5" />
 <div>
 <p className="font-medium text-white text-sm">Unbegrenzt Sprache</p>
 <p className="text-xs text-slate-400">Eingabe & Vorlesen (Pro+)</p>
 </div>
 </div>
 <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-indigo-500/10">
 <GraduationCap className="w-5 h-5 text-purple-500 mt-0.5" />
 <div>
 <p className="font-medium text-white text-sm">Abitur-Simulation</p>
 <p className="text-xs text-slate-400">Echte Prüfungsbedingungen (Max)</p>
 </div>
 </div>
 <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-indigo-500/10">
 <Users className="w-5 h-5 text-purple-500 mt-0.5" />
 <div>
 <p className="font-medium text-white text-sm">Gruppen-Chats</p>
 <p className="text-xs text-slate-400">Zusammen lernen (Max)</p>
 </div>
 </div>
 <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-indigo-500/10">
 <BarChart3 className="w-5 h-5 text-purple-500 mt-0.5" />
 <div>
 <p className="font-medium text-white text-sm">Wochen-Coach</p>
 <p className="text-xs text-slate-400">KI erstellt deinen Lernplan (Max)</p>
 </div>
 </div>
 <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-indigo-500/10">
 <FileText className="w-5 h-5 text-blue-500 mt-0.5" />
 <div>
 <p className="font-medium text-white text-sm">PDF/Word Export</p>
 <p className="text-xs text-slate-400">Chats & Quizze exportieren</p>
 </div>
 </div>
 <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-indigo-500/10">
 <Shield className="w-5 h-5 text-emerald-500 mt-0.5" />
 <div>
 <p className="font-medium text-white text-sm">Eltern-Share</p>
 <p className="text-xs text-slate-400">Fortschritt mit Eltern teilen (Max)</p>
 </div>
 </div>
 </div>
 </CardContent>
 </Card>

 <p className="text-center text-xs text-slate-500">
 Sichere Zahlung über Stripe. Jederzeit kündbar. DSGVO-konform.
 </p>
 </div>
 );
}
