import { useState, useEffect } from "react";
import { eventsApi } from "../services/api";
import { Calendar, Trophy, Star, Clock, CheckCircle, Loader2 } from "lucide-react";

export default function EventsPage() {
 /* eslint-disable @typescript-eslint/no-explicit-any */
 const [events, setEvents] = useState<any[]>([]);
 const [selectedEvent, setSelectedEvent] = useState<any>(null);
 const [progress, setProgress] = useState<any>(null);
 const [loading, setLoading] = useState(true);

 useEffect(() => {
 loadEvents();
 }, []);

 const loadEvents = async () => {
 try {
 const data = await eventsApi.all();
 setEvents(data.events);
 } catch {
 // No events
 } finally {
 setLoading(false);
 }
 };

 const loadProgress = async (eventId: string) => {
 try {
 const data = await eventsApi.progress(eventId);
 setProgress(data);
 } catch {
 // Error
 }
 };

 const handleSelectEvent = (event: any) => {
 setSelectedEvent(event);
 loadProgress(event.id);
 };

 const statusColors: Record<string, string> = {
 active: "bg-green-100 text-green-700",
 upcoming: "bg-blue-100 text-blue-700",
 ended: "bg-[var(--bg-surface)] theme-text-secondary",
 };

 const statusLabels: Record<string, string> = {
 active: "Aktiv",
 upcoming: "Bald",
 ended: "Beendet",
 };

 if (loading) {
 return (
 <div className="flex justify-center items-center h-64">
 <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
 </div>
 );
 }

 return (
 <div className="p-6 max-w-4xl mx-auto">
 <div className="mb-8">
 <h1 className="text-2xl font-bold theme-text flex items-center gap-2">
 <Calendar className="w-7 h-7 text-purple-600" />
 Saisonale Events
 </h1>
 <p className="theme-text-secondary mt-1">
 Nimm an saisonalen Challenges teil und verdiene besondere Belohnungen!
 </p>
 </div>

 <div className="grid md:grid-cols-2 gap-6">
 {/* Events List */}
 <div className="space-y-4">
 {events.map((event: any) => (
 <button
 key={event.id}
 onClick={() => handleSelectEvent(event)}
 className={`w-full text-left p-5 rounded-xl border transition-all hover:shadow-md ${
 selectedEvent?.id === event.id
 ? "border-purple-500 bg-purple-50"
 : "border-[var(--border-color)] theme-card"
 }`}
 >
 <div className="flex items-start justify-between mb-2">
 <h3 className="font-semibold theme-text">{event.name}</h3>
 <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[event.status] || statusColors.ended}`}>
 {statusLabels[event.status] || event.status}
 </span>
 </div>
 <p className="text-sm theme-text-secondary mb-3">{event.description}</p>
 <div className="flex items-center gap-3 text-xs text-gray-400">
 <span className="flex items-center gap-1">
 <Clock className="w-3 h-3" />
 {event.start_date} - {event.end_date}
 </span>
 <span className="flex items-center gap-1">
 <Star className="w-3 h-3" />
 +{event.rewards?.xp_bonus || 0} XP
 </span>
 </div>
 </button>
 ))}
 </div>

 {/* Event Progress */}
 {selectedEvent && (
 <div className="theme-card rounded-xl border border-[var(--border-color)] p-6">
 <h2 className="text-lg font-bold theme-text mb-2">{selectedEvent.name}</h2>
 <p className="text-sm theme-text-secondary mb-6">{selectedEvent.description}</p>

 {/* Rewards */}
 <div className="mb-6 p-3 bg-yellow-50 rounded-lg">
 <p className="text-sm font-medium text-yellow-700 flex items-center gap-2">
 <Trophy className="w-4 h-4" />
 Belohnungen: {selectedEvent.rewards?.xp_bonus} Bonus-XP + Badge "{selectedEvent.rewards?.badge}"
 </p>
 </div>

 {/* Challenges */}
 <h3 className="font-medium theme-text mb-3">Challenges</h3>
 {progress ? (
 <div className="space-y-3">
 {progress.challenges?.map((ch: any, idx: number) => (
 <div key={idx} className="p-3 rounded-lg border border-[var(--border-color)]">
 <div className="flex items-center justify-between mb-1">
 <span className="text-sm font-medium theme-text flex items-center gap-2">
 {ch.completed ? (
 <CheckCircle className="w-4 h-4 text-green-500" />
 ) : (
 <Circle className="w-4 h-4 text-gray-300" />
 )}
 {ch.title}
 </span>
 <span className="text-xs text-yellow-600 font-medium">+{ch.xp} XP</span>
 </div>
 <div className="flex items-center gap-2 mt-1">
 <div className="flex-1 bg-[var(--progress-bg)] rounded-full h-1.5">
 <div
 className={`h-1.5 rounded-full ${ch.completed ? "bg-green-500" : "bg-purple-500"}`}
 style={{ width: `${(ch.progress / ch.target) * 100}%` }}
 />
 </div>
 <span className="text-xs text-gray-400">{ch.progress}/{ch.target}</span>
 </div>
 </div>
 ))}

 <div className="mt-4 pt-4 border-t border-[var(--border-color)]">
 <p className="text-sm text-gray-600">
 {progress.total_completed}/{progress.total_challenges} Challenges abgeschlossen
 </p>
 </div>
 </div>
 ) : (
 <p className="text-sm theme-text-secondary">Lade Fortschritt...</p>
 )}
 </div>
 )}
 </div>
 </div>
 );
 /* eslint-enable @typescript-eslint/no-explicit-any */
}

function Circle(props: React.SVGProps<SVGSVGElement> & { className?: string }) {
 return (
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
 <circle cx="12" cy="12" r="10" />
 </svg>
 );
}
