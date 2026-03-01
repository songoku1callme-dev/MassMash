import { useState, useEffect, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { groupsApi, type GroupChat, type GroupMessage } from "../services/api";
import {
  Users, MessageCircle, Plus, Send, ArrowLeft, Loader2, Lock,
  Calculator, Languages, BookOpenCheck, FlaskConical, Atom, Leaf,
  Clock, Globe, Landmark, Brain, Code, Palette, Music, BookOpen
} from "lucide-react";

const SUBJECT_OPTIONS = [
  { id: "math", name: "Mathe", icon: <Calculator className="w-4 h-4" /> },
  { id: "german", name: "Deutsch", icon: <BookOpenCheck className="w-4 h-4" /> },
  { id: "english", name: "Englisch", icon: <Languages className="w-4 h-4" /> },
  { id: "physics", name: "Physik", icon: <Atom className="w-4 h-4" /> },
  { id: "chemistry", name: "Chemie", icon: <FlaskConical className="w-4 h-4" /> },
  { id: "biology", name: "Biologie", icon: <Leaf className="w-4 h-4" /> },
  { id: "history", name: "Geschichte", icon: <Clock className="w-4 h-4" /> },
  { id: "geography", name: "Geografie", icon: <Globe className="w-4 h-4" /> },
  { id: "economics", name: "Wirtschaft", icon: <Landmark className="w-4 h-4" /> },
  { id: "ethics", name: "Ethik", icon: <Brain className="w-4 h-4" /> },
  { id: "computer_science", name: "Informatik", icon: <Code className="w-4 h-4" /> },
  { id: "art", name: "Kunst", icon: <Palette className="w-4 h-4" /> },
  { id: "music", name: "Musik", icon: <Music className="w-4 h-4" /> },
  { id: "latin", name: "Latein", icon: <BookOpen className="w-4 h-4" /> },
];

type ViewState = "list" | "chat" | "create";

export default function GroupsPage() {
  const [view, setView] = useState<ViewState>("list");
  const [groups, setGroups] = useState<GroupChat[]>([]);
  const [activeGroup, setActiveGroup] = useState<GroupChat | null>(null);
  const [messages, setMessages] = useState<GroupMessage[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupSubject, setNewGroupSubject] = useState("math");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadGroups();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadGroups = async () => {
    setLoading(true);
    try {
      const data = await groupsApi.list();
      setGroups(data.groups);
    } catch (err) {
      console.error("Failed to load groups:", err);
      setError("Gruppen-Chats sind nur für Max-Nutzer verfügbar.");
    } finally {
      setLoading(false);
    }
  };

  const openGroup = async (group: GroupChat) => {
    setActiveGroup(group);
    setView("chat");
    try {
      const data = await groupsApi.messages(group.id);
      setMessages(data.messages);
    } catch { setMessages([]); }
    // Poll for new messages every 5 seconds
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const data = await groupsApi.messages(group.id);
        setMessages(data.messages);
      } catch { /* ignore */ }
    }, 5000);
  };

  const joinGroup = async (groupId: number) => {
    try {
      await groupsApi.join(groupId);
      loadGroups();
    } catch (err) {
      console.error("Failed to join group:", err);
    }
  };

  const leaveGroup = async (groupId: number) => {
    try {
      await groupsApi.leave(groupId);
      if (activeGroup?.id === groupId) {
        setView("list");
        setActiveGroup(null);
        if (pollRef.current) clearInterval(pollRef.current);
      }
      loadGroups();
    } catch (err) {
      console.error("Failed to leave group:", err);
    }
  };

  const sendMessage = async () => {
    if (!activeGroup || !newMessage.trim()) return;
    setSending(true);
    try {
      await groupsApi.send(activeGroup.id, newMessage.trim());
      setNewMessage("");
      const data = await groupsApi.messages(activeGroup.id);
      setMessages(data.messages);
    } catch (err) {
      console.error("Failed to send message:", err);
    } finally {
      setSending(false);
    }
  };

  const createGroup = async () => {
    if (!newGroupName.trim()) return;
    setLoading(true);
    try {
      await groupsApi.create(newGroupName.trim(), newGroupSubject);
      setNewGroupName("");
      setView("list");
      loadGroups();
    } catch (err) {
      console.error("Failed to create group:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading && view === "list") {
    return (
      <div className="p-4 lg:p-6 max-w-4xl mx-auto flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 lg:p-6 max-w-4xl mx-auto">
        <div className="text-center py-12">
          <Lock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Max-Abo erforderlich</h2>
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  // Create Group View
  if (view === "create") {
    return (
      <div className="p-4 lg:p-6 max-w-2xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => setView("list")}><ArrowLeft className="w-4 h-4" /></Button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Neue Gruppe erstellen</h1>
        </div>

        <Card>
          <CardContent className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Gruppenname</label>
              <Input value={newGroupName} onChange={(e) => setNewGroupName(e.target.value)}
                placeholder="z.B. Mathe-LK Abitur 2026" className="p-3" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Fach</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {SUBJECT_OPTIONS.map((s) => (
                  <button key={s.id} onClick={() => setNewGroupSubject(s.id)}
                    className={`flex items-center gap-2 p-2 rounded-lg border-2 text-sm transition-all ${
                      newGroupSubject === s.id ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20" : "border-gray-200 dark:border-gray-700"
                    }`}>
                    {s.icon} {s.name}
                  </button>
                ))}
              </div>
            </div>
            <Button onClick={createGroup} className="w-full gap-2" disabled={!newGroupName.trim() || loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Gruppe erstellen
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Chat View
  if (view === "chat" && activeGroup) {
    return (
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => {
            setView("list"); setActiveGroup(null);
            if (pollRef.current) clearInterval(pollRef.current);
          }}><ArrowLeft className="w-4 h-4" /></Button>
          <div className="flex-1">
            <h2 className="font-bold text-gray-900 dark:text-white">{activeGroup.name}</h2>
            <p className="text-xs text-gray-500">{activeGroup.member_count}/{activeGroup.max_members} Mitglieder - {SUBJECT_OPTIONS.find(s => s.id === activeGroup.subject)?.name || activeGroup.subject}</p>
          </div>
          <Button variant="outline" size="sm" className="text-red-500" onClick={() => leaveGroup(activeGroup.id)}>
            Verlassen
          </Button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-center text-gray-500 py-8">Noch keine Nachrichten. Starte die Unterhaltung!</p>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                {msg.username[0]?.toUpperCase()}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">{msg.username}</span>
                  <span className="text-xs text-gray-500">{new Date(msg.timestamp).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}</span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg p-3">{msg.content}</p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex gap-2">
            <Input value={newMessage} onChange={(e) => setNewMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder="Nachricht schreiben..." className="flex-1" />
            <Button onClick={sendMessage} disabled={!newMessage.trim() || sending}>
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Groups List View
  return (
    <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="w-7 h-7 text-indigo-600" /> Gruppen-Chats
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Lerne zusammen mit anderen Schülern (Max)</p>
        </div>
        <Button onClick={() => setView("create")} className="gap-2">
          <Plus className="w-4 h-4" /> Neue Gruppe
        </Button>
      </div>

      {groups.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <MessageCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Keine Gruppen vorhanden</h3>
            <p className="text-gray-500 mb-4">Erstelle eine neue Gruppe oder warte, bis andere eine erstellen.</p>
            <Button onClick={() => setView("create")} className="gap-2"><Plus className="w-4 h-4" /> Gruppe erstellen</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {groups.map((group) => (
            <Card key={group.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center text-white">
                    {SUBJECT_OPTIONS.find(s => s.id === group.subject)?.icon || <Users className="w-5 h-5" />}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900 dark:text-white">{group.name}</h3>
                    <p className="text-xs text-gray-500">
                      {SUBJECT_OPTIONS.find(s => s.id === group.subject)?.name || group.subject} - {group.member_count}/{group.max_members} Mitglieder
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  {group.is_member ? (
                    <>
                      <Button size="sm" className="flex-1 gap-1" onClick={() => openGroup(group)}>
                        <MessageCircle className="w-4 h-4" /> Chat öffnen
                      </Button>
                      <Button size="sm" variant="outline" className="text-red-500" onClick={() => leaveGroup(group.id)}>
                        Verlassen
                      </Button>
                    </>
                  ) : (
                    <Button size="sm" className="flex-1 gap-1" onClick={() => joinGroup(group.id)}>
                      <Plus className="w-4 h-4" /> Beitreten
                    </Button>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  Erstellt: {new Date(group.created_at).toLocaleDateString("de-DE")}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card className="bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <Badge variant="secondary" className="bg-indigo-100 text-indigo-700">Max</Badge>
            <p className="text-sm text-indigo-700 dark:text-indigo-300">
              Gruppen-Chats sind exklusiv für Max-Abonnenten. Max. 10 Mitglieder pro Gruppe.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
