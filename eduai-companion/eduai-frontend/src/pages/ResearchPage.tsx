import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { researchApi, type ResearchResult } from "../services/api";
import ReactMarkdown from "react-markdown";
import {
 Search, Globe, ExternalLink, Loader2, Lock, BookOpen, Sparkles
} from "lucide-react";

export default function ResearchPage() {
 const [query, setQuery] = useState("");
 const [subject, setSubject] = useState("");
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState("");
 const [results, setResults] = useState<ResearchResult[]>([]);
 const [answer, setAnswer] = useState("");
 const [tavilyEnabled, setTavilyEnabled] = useState(false);

 const handleSearch = async () => {
 if (!query.trim()) return;
 setLoading(true);
 setError("");
 setAnswer("");
 try {
 const data = await researchApi.search({ query: query.trim(), subject });
 setResults(data.results);
 setTavilyEnabled(data.tavily_enabled);
 } catch (err: unknown) {
 const msg = err instanceof Error ? err.message : "Fehler bei der Suche";
 setError(msg);
 } finally {
 setLoading(false);
 }
 };

 const handleAskWithSources = async () => {
 if (!query.trim()) return;
 setLoading(true);
 setError("");
 try {
 const data = await researchApi.askWithSources({ question: query.trim(), subject });
 setAnswer(data.answer);
 setResults(data.sources);
 setTavilyEnabled(data.tavily_enabled);
 } catch (err: unknown) {
 const msg = err instanceof Error ? err.message : "Fehler bei der Anfrage";
 setError(msg);
 } finally {
 setLoading(false);
 }
 };

 return (
 <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
 <div>
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <Globe className="w-7 h-7 text-purple-600" />
 Internet-Recherche
 </h1>
 <p className="theme-text-secondary mt-1">
 Suche nach Abitur-relevanten Quellen und Lehrplaninhalten (Max)
 </p>
 </div>

 {error && (
 <div className="p-4 rounded-lg bg-red-500/10 text-red-500 flex items-center gap-2">
 <Lock className="w-5 h-5" />
 {error}
 </div>
 )}

 {/* Search Input */}
 <Card>
 <CardContent className="p-4">
 <div className="flex flex-col sm:flex-row gap-3">
 <Input
 value={query}
 onChange={(e) => setQuery(e.target.value)}
 onKeyDown={(e) => e.key === "Enter" && handleSearch()}
 placeholder="z.B. 'Thermodynamik Abitur 2026 Bayern' oder 'Epochen der deutschen Literatur'"
 className="flex-1"
 />
 <select
 value={subject}
 onChange={(e) => setSubject(e.target.value)}
 className="px-3 py-2 rounded-md border border-[var(--border-color)] theme-card text-sm"
 >
 <option value="">Alle Fächer</option>
 <option value="math">Mathe</option>
 <option value="german">Deutsch</option>
 <option value="english">Englisch</option>
 <option value="physics">Physik</option>
 <option value="chemistry">Chemie</option>
 <option value="biology">Biologie</option>
 <option value="history">Geschichte</option>
 </select>
 </div>
 <div className="flex gap-2 mt-3">
 <Button onClick={handleSearch} className="gap-2" disabled={loading || !query.trim()}>
 {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
 Quellen suchen
 </Button>
 <Button onClick={handleAskWithSources} variant="outline" className="gap-2" disabled={loading || !query.trim()}>
 <Sparkles className="w-4 h-4" />
 KI-Antwort mit Quellen
 </Button>
 </div>
 {!tavilyEnabled && results.length > 0 && (
 <p className="text-xs text-amber-600 mt-2">
 Hinweis: Tavily API nicht konfiguriert - Beispiel-Ergebnisse werden angezeigt.
 </p>
 )}
 </CardContent>
 </Card>

 {/* AI Answer */}
 {answer && (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Sparkles className="w-5 h-5 text-purple-500" />
 KI-Antwort mit Quellen
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="prose prose-sm max-w-none">
 <ReactMarkdown>{answer}</ReactMarkdown>
 </div>
 </CardContent>
 </Card>
 )}

 {/* Search Results */}
 {results.length > 0 && (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <BookOpen className="w-5 h-5 text-blue-500" />
 Quellen ({results.length})
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="space-y-4">
 {results.map((r, idx) => (
 <div key={idx} className="p-4 rounded-xl border border-[var(--border-color)] hover:border-blue-300 transition-colors">
 <div className="flex items-start justify-between gap-2">
 <div className="flex-1">
 <h3 className="font-medium theme-text text-sm">{r.title}</h3>
 <a
 href={r.url}
 target="_blank"
 rel="noopener noreferrer"
 className="text-xs text-blue-500 hover:underline flex items-center gap-1 mt-1"
 >
 {r.url} <ExternalLink className="w-3 h-3" />
 </a>
 </div>
 <Badge variant="secondary" className="text-xs shrink-0">
 {Math.round(r.score * 100)}%
 </Badge>
 </div>
 <p className="text-sm theme-text-secondary mt-2 line-clamp-3">
 {r.content}
 </p>
 </div>
 ))}
 </div>
 </CardContent>
 </Card>
 )}

 {!loading && results.length === 0 && !error && (
 <div className="text-center py-12 theme-text-secondary">
 <Globe className="w-16 h-16 mx-auto mb-4 opacity-30" />
 <p>Suche nach Abitur-Themen, Lehrplaninhalten oder Fachbegriffen</p>
 </div>
 )}
 </div>
 );
}
