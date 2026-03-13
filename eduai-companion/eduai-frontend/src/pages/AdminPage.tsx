import { useState, useEffect } from "react";
import { adminApi } from "../services/api";
import { useAuthStore } from "../stores/authStore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
 Shield, Users, BarChart3, Ticket, Search, Gift, Loader2, Crown, Star,
 TrendingUp, DollarSign, Brain, ShieldOff, Clock, Play, CheckCircle, XCircle
} from "lucide-react";
import { PageLoader, ErrorState } from "../components/PageStates";

// Hardcoded admin whitelist — Fallback falls API nicht erreichbar
const ADMIN_EMAILS = [
 "songoku1callme@gmail.com",
 "ahmadalkhalaf2019@gmail.com",
 "ahmadalkhalaf20024@gmail.com",
 "ahmadalkhalaf1245@gmail.com",
 "261g2g261@gmail.com",
 "261al3nzi261@gmail.com",
];

interface AdminStats {
 total_users: number;
 pro_users: number;
 max_users: number;
 total_chat_sessions: number;
 total_quizzes: number;
 avg_quiz_score: number;
 active_coupons: number;
 total_tournaments: number;
 activity_last_24h: number;
 active_subscriptions: { id: number; username: string; email: string; subscription_tier: string; pro_expires_at: string }[];
}

interface SearchUser {
 id: number;
 username: string;
 email: string;
 subscription_tier: string;
 pro_expires_at: string;
 created_at: string;
 clerk_user_id?: string;
}

interface Coupon {
 id: number;
 code: string;
 tier: string;
 duration_days: number;
 max_uses: number;
 current_uses: number;
 is_active: number;
 created_at: string;
}

interface AnalyticsData {
 daily_signups: { day: string; count: number }[];
 revenue: { breakdown: { tier: string; period: string; users: number; mrr: number }[]; total_mrr: number };
 popular_subjects: { subject: string; count: number }[];
 tournament_participants: number;
 iq_tests: { total: number; avg_iq: number };
}

export default function AdminPage() {
 const { user } = useAuthStore();
 const userEmail = (user?.email || "").toLowerCase();
 const localAdminCheck = ADMIN_EMAILS.some(e => e.toLowerCase() === userEmail);

 // API-basierter Admin-Check (Single Source of Truth)
 const [apiAdmin, setApiAdmin] = useState<boolean | null>(null);
 const [adminCheckDone, setAdminCheckDone] = useState(false);

 useEffect(() => {
   adminApi.check()
     .then((res) => { setApiAdmin(res.is_admin); setAdminCheckDone(true); })
     .catch(() => { setApiAdmin(null); setAdminCheckDone(true); });
 }, []);

 // API hat Vorrang, Fallback auf lokale Whitelist
 const isAdmin = apiAdmin !== null ? apiAdmin : localAdminCheck;

 const [stats, setStats] = useState<AdminStats | null>(null);
 const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
 const [users, setUsers] = useState<SearchUser[]>([]);
 const [coupons, setCoupons] = useState<Coupon[]>([]);
 const [searchQuery, setSearchQuery] = useState("");
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState("");
 const [grantUserId, setGrantUserId] = useState("");
 const [grantTier, setGrantTier] = useState("pro");
 const [grantDays, setGrantDays] = useState("30");
 const [granting, setGranting] = useState(false);
 const [couponCode, setCouponCode] = useState("");
 const [couponTier, setCouponTier] = useState("pro");
 const [couponDays, setCouponDays] = useState("30");
 const [couponMaxUses, setCouponMaxUses] = useState("100");
 const [creatingCoupon, setCreatingCoupon] = useState(false);
 const [message, setMessage] = useState("");
 const [schedulerJobs, setSchedulerJobs] = useState<{ job_id: string; beschreibung: string; zeitplan: string; naechste_ausfuehrung: string; aktiv: boolean }[]>([]);
 const [schedulerActive, setSchedulerActive] = useState(false);
 const [loadingScheduler, setLoadingScheduler] = useState(false);
 const [triggeringJob, setTriggeringJob] = useState<string | null>(null);

 useEffect(() => { if (adminCheckDone && isAdmin) { loadData(); loadScheduler(); } }, [adminCheckDone, isAdmin]);

 const loadData = async () => {
 setLoading(true);
 try {
 const [statsData, couponsData, analytics] = await Promise.all([
 adminApi.stats(),
 adminApi.coupons(),
 adminApi.analytics(30).catch(() => null),
 ]);
 setStats(statsData);
 setCoupons(couponsData.coupons || []);
 if (analytics) setAnalyticsData(analytics);
 } catch (err) {
 setError(err instanceof Error ? err.message : "Fehler beim Laden");
 } finally {
 setLoading(false);
 }
 };

 const loadScheduler = async () => {
 setLoadingScheduler(true);
 try {
 const data = await adminApi.schedulerStatus();
 setSchedulerJobs(data.jobs || []);
 setSchedulerActive(data.scheduler_aktiv);
 } catch {
 // Scheduler status not available
 } finally {
 setLoadingScheduler(false);
 }
 };

 const handleTriggerJob = async (jobId: string) => {
 setTriggeringJob(jobId);
 try {
 const result = await adminApi.triggerJob(jobId);
 setMessage(result.message);
 } catch (err) {
 setError(err instanceof Error ? err.message : "Job-Trigger fehlgeschlagen");
 } finally {
 setTriggeringJob(null);
 }
 };

 const handleSearch = async () => {
 try {
 const result = await adminApi.searchUsers(searchQuery);
 setUsers(result.users || []);
 } catch (err) {
 setError(err instanceof Error ? err.message : "Suche fehlgeschlagen");
 }
 };

 const handleGrant = async () => {
 if (!grantUserId) return;
 setGranting(true);
 try {
 await adminApi.grantSubscription({
 user_id: parseInt(grantUserId),
 tier: grantTier,
 duration_days: parseInt(grantDays),
 });
 setMessage("Abo erfolgreich vergeben!");
 loadData();
 } catch (err) {
 setError(err instanceof Error ? err.message : "Fehler");
 } finally {
 setGranting(false);
 }
 };

 const handleCreateCoupon = async () => {
 if (!couponCode) return;
 setCreatingCoupon(true);
 try {
 await adminApi.createCoupon({
 code: couponCode,
 tier: couponTier,
 duration_days: parseInt(couponDays),
 max_uses: parseInt(couponMaxUses),
 });
 setMessage("Gutschein erstellt!");
 setCouponCode("");
 loadData();
 } catch (err) {
 setError(err instanceof Error ? err.message : "Fehler");
 } finally {
 setCreatingCoupon(false);
 }
 };

 // Warte auf Admin-Check bevor Zugriff verweigert wird
 if (!adminCheckDone) return <PageLoader text="Admin-Berechtigung wird geprüft..." />;

 // Access control: only whitelisted admin emails can see the admin panel
 if (!isAdmin) {
 return (
 <div className="p-6 flex flex-col items-center justify-center min-h-[60vh] text-center">
 <ShieldOff className="w-16 h-16 text-red-500 mb-4" />
 <h1 className="text-2xl font-bold theme-text mb-2">Kein Zugriff</h1>
 <p className="theme-text-secondary">Nur für Admins — Du hast keine Berechtigung für das Admin-Panel.</p>
 </div>
 );
 }

 if (loading) return <PageLoader text="Admin-Panel laden..." />;
 if (error && !stats) return <ErrorState message={error} onRetry={loadData} />;

 return (
 <div className="p-4 lg:p-6 max-w-6xl mx-auto space-y-6">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <Shield className="w-7 h-7 text-red-600" />
 Admin-Panel
 </h1>
 <p className="theme-text-secondary mt-1">Verwalte User, Abos, Gutscheine und Statistiken</p>
 </div>

 {message && (
 <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-400 text-sm">
 {message}
 </div>
 )}
 {error && (
 <div className="p-3 rounded-lg bg-red-500/10 text-red-500 text-sm">
 {error}
 </div>
 )}

 {stats && (
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
 <Card><CardContent className="p-4 text-center">
 <Users className="w-6 h-6 text-blue-600 mx-auto mb-1" />
 <p className="text-2xl font-bold">{stats.total_users}</p>
 <p className="text-xs theme-text-secondary">User gesamt</p>
 </CardContent></Card>
 <Card><CardContent className="p-4 text-center">
 <Star className="w-6 h-6 text-yellow-500 mx-auto mb-1" />
 <p className="text-2xl font-bold">{stats.pro_users}</p>
 <p className="text-xs theme-text-secondary">Pro-User</p>
 </CardContent></Card>
 <Card><CardContent className="p-4 text-center">
 <Crown className="w-6 h-6 text-purple-500 mx-auto mb-1" />
 <p className="text-2xl font-bold">{stats.max_users}</p>
 <p className="text-xs theme-text-secondary">Max-User</p>
 </CardContent></Card>
 <Card><CardContent className="p-4 text-center">
 <BarChart3 className="w-6 h-6 text-emerald-600 mx-auto mb-1" />
 <p className="text-2xl font-bold">{stats.activity_last_24h}</p>
 <p className="text-xs theme-text-secondary">Aktiv (24h)</p>
 </CardContent></Card>
 </div>
 )}

 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Search className="w-5 h-5 text-blue-600" />
 User suchen
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-3">
 <div className="flex gap-2">
 <Input placeholder="Email oder Username..." value={searchQuery}
 onChange={(e) => setSearchQuery(e.target.value)}
 onKeyDown={(e) => e.key === "Enter" && handleSearch()} />
 <Button onClick={handleSearch} size="sm"><Search className="w-4 h-4" /></Button>
 </div>
 <div className="max-h-64 overflow-auto space-y-1">
 {users.map((u) => (
 <div key={u.id}
 className="flex items-center justify-between p-2 rounded bg-[var(--bg-surface)] text-sm cursor-pointer hover:bg-[var(--bg-card-hover)]"
 onClick={() => setGrantUserId(String(u.id))}>
 <div className="flex-1 min-w-0">
 <div className="flex items-center gap-2">
 <span className="font-medium">{u.username}</span>
 <span className="text-xs font-mono text-slate-500">ID:{u.id}</span>
 {u.clerk_user_id && (
 <span className="text-[10px] font-mono text-indigo-400 truncate max-w-[120px]" title={u.clerk_user_id}>
 {u.clerk_user_id.slice(0, 12)}...
 </span>
 )}
 </div>
 <span className="theme-text-secondary text-xs">{u.email}</span>
 </div>
 <div className="flex items-center gap-2 flex-shrink-0">
 <span className={`text-xs px-2 py-0.5 rounded ${
 u.subscription_tier === "max" ? "bg-purple-100 text-purple-700" :
 u.subscription_tier === "pro" ? "bg-blue-100 text-blue-700" :
 "bg-[var(--bg-surface)] theme-text-secondary"
 }`}>{u.subscription_tier}</span>
 {u.subscription_tier === "free" && (
 <Button size="sm" variant="outline" className="h-6 text-[10px] px-2"
 onClick={(e) => { e.stopPropagation(); setGrantUserId(String(u.id)); setGrantTier("pro"); }}>
 <Crown className="w-3 h-3 mr-1" /> Upgrade
 </Button>
 )}
 </div>
 </div>
 ))}
 </div>
 </CardContent>
 </Card>

 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Gift className="w-5 h-5 text-purple-600" />
 Abo vergeben
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-3">
 <Input placeholder="User-ID" value={grantUserId}
 onChange={(e) => setGrantUserId(e.target.value)} type="number" />
 <div className="flex gap-2">
 <select value={grantTier} onChange={(e) => setGrantTier(e.target.value)}
 className="flex h-10 rounded-lg border border-[var(--border-color)] bg-[var(--lumnos-surface)] px-3 py-2 text-sm theme-text">
 <option value="pro">Pro</option>
 <option value="max">Max</option>
 </select>
 <select value={grantDays} onChange={(e) => setGrantDays(e.target.value)}
 className="flex h-10 rounded-lg border border-[var(--border-color)] bg-[var(--lumnos-surface)] px-3 py-2 text-sm theme-text">
 <option value="30">1 Monat</option>
 <option value="90">3 Monate</option>
 <option value="365">1 Jahr</option>
 <option value="0">Permanent</option>
 </select>
 </div>
 <Button onClick={handleGrant} disabled={granting || !grantUserId} className="w-full">
 {granting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Gift className="w-4 h-4 mr-2" />}
 Abo aktivieren
 </Button>
 </CardContent>
 </Card>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Ticket className="w-5 h-5 text-emerald-600" />
 Gutschein erstellen
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-3">
 <Input placeholder="Code (z.B. ABITUR2026)" value={couponCode}
 onChange={(e) => setCouponCode(e.target.value.toUpperCase())} />
 <div className="flex gap-2">
 <select value={couponTier} onChange={(e) => setCouponTier(e.target.value)}
 className="flex h-10 rounded-lg border border-[var(--border-color)] bg-[var(--lumnos-surface)] px-3 py-2 text-sm theme-text">
 <option value="pro">Pro</option>
 <option value="max">Max</option>
 </select>
 <Input placeholder="Tage" value={couponDays}
 onChange={(e) => setCouponDays(e.target.value)} type="number" className="w-24" />
 <Input placeholder="Max. Einl." value={couponMaxUses}
 onChange={(e) => setCouponMaxUses(e.target.value)} type="number" className="w-24" />
 </div>
 <Button onClick={handleCreateCoupon} disabled={creatingCoupon || !couponCode}
 className="w-full bg-emerald-600 hover:bg-emerald-700">
 {creatingCoupon ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Ticket className="w-4 h-4 mr-2" />}
 Code erstellen
 </Button>
 </CardContent>
 </Card>

 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Ticket className="w-5 h-5 text-blue-600" />
 Aktive Gutscheine
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="max-h-48 overflow-auto space-y-2">
 {coupons.length === 0 && <p className="text-sm theme-text-secondary">Keine Gutscheine vorhanden</p>}
 {coupons.map((c) => (
 <div key={c.id} className="flex items-center justify-between p-2 rounded bg-[var(--bg-surface)] text-sm">
 <div>
 <span className="font-mono font-bold">{c.code}</span>
 <span className="theme-text-secondary ml-2">{c.tier} / {c.duration_days}d</span>
 </div>
 <span className="text-xs theme-text-secondary">{c.current_uses}/{c.max_uses || "∞"}</span>
 </div>
 ))}
 </div>
 </CardContent>
 </Card>
 </div>
 {/* Analytics Dashboard */}
 {analyticsData && (
 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <TrendingUp className="w-5 h-5 text-blue-600" />
 Neue User (30 Tage)
 </CardTitle>
 </CardHeader>
 <CardContent>
 {analyticsData.daily_signups.length === 0 ? (
 <p className="text-sm theme-text-secondary">Keine Daten</p>
 ) : (
 <div className="flex items-end gap-1 h-32">
 {analyticsData.daily_signups.slice(-14).map((d, i) => {
 const max = Math.max(...analyticsData.daily_signups.slice(-14).map(x => x.count), 1);
 return (
 <div key={i} className="flex-1 flex flex-col items-center gap-1">
 <span className="text-[10px] text-gray-400">{d.count}</span>
 <div
 className="w-full bg-blue-500 rounded-t"
 style={{ height: `${(d.count / max) * 100}%`, minHeight: d.count > 0 ? 4 : 1 }}
 />
 </div>
 );
 })}
 </div>
 )}
 </CardContent>
 </Card>

 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <DollarSign className="w-5 h-5 text-emerald-600" />
 Revenue (MRR)
 </CardTitle>
 </CardHeader>
 <CardContent>
 <p className="text-3xl font-bold text-emerald-600">{analyticsData.revenue.total_mrr.toFixed(2)}€</p>
 <p className="text-xs text-gray-400 mt-1">Monatlich wiederkehrend</p>
 <div className="mt-3 space-y-1">
 {analyticsData.revenue.breakdown.map((b, i) => (
 <div key={i} className="flex justify-between text-sm">
 <span className="theme-text-secondary">{b.tier} ({b.period})</span>
 <span className="font-medium">{b.users} User = {b.mrr}€</span>
 </div>
 ))}
 </div>
 </CardContent>
 </Card>

 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <BarChart3 className="w-5 h-5 text-indigo-600" />
 Beliebteste Fächer
 </CardTitle>
 </CardHeader>
 <CardContent>
 {analyticsData.popular_subjects.length === 0 ? (
 <p className="text-sm theme-text-secondary">Keine Daten</p>
 ) : (
 <div className="space-y-2">
 {analyticsData.popular_subjects.slice(0, 5).map((s, i) => {
 const max = analyticsData.popular_subjects[0]?.count || 1;
 return (
 <div key={i}>
 <div className="flex justify-between text-sm mb-0.5">
 <span className="theme-text-secondary">{s.subject}</span>
 <span className="theme-text-secondary">{s.count}</span>
 </div>
 <div className="h-2 bg-[var(--bg-surface)] rounded-full">
 <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${(s.count / max) * 100}%` }} />
 </div>
 </div>
 );
 })}
 </div>
 )}
 </CardContent>
 </Card>

 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Brain className="w-5 h-5 text-purple-600" />
 IQ-Test Statistiken
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="grid grid-cols-2 gap-4">
 <div className="text-center">
 <p className="text-2xl font-bold text-purple-600">{analyticsData.iq_tests.total}</p>
 <p className="text-xs theme-text-secondary">Tests absolviert</p>
 </div>
 <div className="text-center">
 <p className="text-2xl font-bold text-purple-600">{analyticsData.iq_tests.avg_iq || "—"}</p>
 <p className="text-xs theme-text-secondary">Durchschnitt-IQ</p>
 </div>
 </div>
 <div className="mt-3 pt-3 border-t border-[var(--border-color)]">
 <div className="flex justify-between text-sm">
 <span className="theme-text-secondary">Turnier-Teilnehmer</span>
 <span className="font-medium">{analyticsData.tournament_participants}</span>
 </div>
 </div>
 </CardContent>
 </Card>
 </div>
 )}

 {/* Scheduler Dashboard — AUFGABE 3 */}
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Clock className="w-5 h-5 text-orange-600" />
 Scheduler-Jobs (Auto-Updates)
 <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${schedulerActive ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
 {schedulerActive ? "Aktiv" : "Inaktiv"}
 </span>
 </CardTitle>
 </CardHeader>
 <CardContent>
 {loadingScheduler ? (
 <div className="flex justify-center py-4"><Loader2 className="w-6 h-6 animate-spin text-orange-500" /></div>
 ) : schedulerJobs.length === 0 ? (
 <p className="text-sm theme-text-secondary">Keine Scheduler-Jobs gefunden (Backend nicht erreichbar?)</p>
 ) : (
 <div className="space-y-2 max-h-96 overflow-auto">
 {schedulerJobs.map((job) => (
 <div key={job.job_id} className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-color)]">
 <div className="flex-1 min-w-0">
 <div className="flex items-center gap-2">
 {job.aktiv ? <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" /> : <XCircle className="w-4 h-4 text-red-400 shrink-0" />}
 <span className="text-sm font-medium theme-text truncate">{job.beschreibung}</span>
 </div>
 <div className="flex items-center gap-3 mt-1 ml-6">
 <span className="text-xs theme-text-secondary">{job.zeitplan}</span>
 <span className="text-[10px] font-mono theme-text-secondary">{job.job_id}</span>
 </div>
 </div>
 <button
 onClick={() => handleTriggerJob(job.job_id)}
 disabled={triggeringJob === job.job_id}
 className="shrink-0 flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-orange-500/10 text-orange-600 hover:bg-orange-500/20 transition-colors disabled:opacity-50"
 >
 {triggeringJob === job.job_id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
 Jetzt starten
 </button>
 </div>
 ))}
 </div>
 )}
 </CardContent>
 </Card>
 </div>
 );
}
