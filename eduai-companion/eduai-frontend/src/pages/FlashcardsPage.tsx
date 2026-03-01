import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  BookOpen, Plus, RotateCcw, Sparkles, ChevronLeft,
  Loader2, Check, X, Brain
} from "lucide-react";
import { getAccessToken } from "../services/api";

const API = import.meta.env.VITE_API_URL || "";

interface Deck {
  id: number;
  name: string;
  subject: string;
  card_count: number;
  due_count: number;
}

interface FlashCard {
  id: number;
  front: string;
  back: string;
}

async function apiFetch(path: string, opts: RequestInit = {}) {
  const token = getAccessToken();
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...opts.headers },
  });
  return res.json();
}

export default function FlashcardsPage() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDeck, setSelectedDeck] = useState<number | null>(null);
  const [reviewCards, setReviewCards] = useState<FlashCard[]>([]);
  const [currentCard, setCurrentCard] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showAI, setShowAI] = useState(false);
  const [newDeckName, setNewDeckName] = useState("");
  const [aiTopic, setAiTopic] = useState("");
  const [aiCount, setAiCount] = useState(10);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    loadDecks();
  }, []);

  const loadDecks = async () => {
    try {
      const data = await apiFetch("/api/flashcards/decks");
      setDecks(data.decks || []);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  const createDeck = async () => {
    if (!newDeckName.trim()) return;
    await apiFetch("/api/flashcards/decks", {
      method: "POST",
      body: JSON.stringify({ name: newDeckName, subject: "general" }),
    });
    setNewDeckName("");
    setShowCreate(false);
    loadDecks();
  };

  const startReview = async (deckId: number) => {
    const data = await apiFetch(`/api/flashcards/review/${deckId}`);
    setReviewCards(data.cards || []);
    setSelectedDeck(deckId);
    setCurrentCard(0);
    setFlipped(false);
  };

  const submitReview = async (quality: number) => {
    const card = reviewCards[currentCard];
    await apiFetch("/api/flashcards/review", {
      method: "POST",
      body: JSON.stringify({ card_id: card.id, quality }),
    });
    setFlipped(false);
    if (currentCard < reviewCards.length - 1) {
      setCurrentCard(currentCard + 1);
    } else {
      setSelectedDeck(null);
      setReviewCards([]);
      loadDecks();
    }
  };

  const generateAI = async () => {
    if (!aiTopic.trim()) return;
    setAiLoading(true);
    try {
      await apiFetch("/api/flashcards/ai-generate", {
        method: "POST",
        body: JSON.stringify({ topic: aiTopic, count: aiCount }),
      });
      setAiTopic("");
      setShowAI(false);
      loadDecks();
    } catch {
      /* ignore */
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  // Review mode
  if (selectedDeck !== null && reviewCards.length > 0) {
    const card = reviewCards[currentCard];
    return (
      <div className="p-4 lg:p-6 max-w-2xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => { setSelectedDeck(null); setReviewCards([]); }}>
            <ChevronLeft className="w-4 h-4 mr-1" /> Zurück
          </Button>
          <span className="text-sm text-gray-500">{currentCard + 1} / {reviewCards.length}</span>
        </div>

        <div
          className="cursor-pointer perspective-1000"
          onClick={() => setFlipped(!flipped)}
        >
          <Card className={`min-h-[250px] flex items-center justify-center transition-all duration-300 ${flipped ? "bg-indigo-50 dark:bg-indigo-900/20" : ""}`}>
            <CardContent className="p-8 text-center">
              <p className="text-xs text-gray-400 mb-2">{flipped ? "Antwort" : "Frage"}</p>
              <p className="text-xl font-medium text-gray-900 dark:text-white">
                {flipped ? card.back : card.front}
              </p>
              {!flipped && (
                <p className="text-sm text-gray-400 mt-4">Klicke zum Umdrehen</p>
              )}
            </CardContent>
          </Card>
        </div>

        {flipped && (
          <div className="space-y-2">
            <p className="text-sm text-gray-500 text-center mb-2">Wie gut wusstest du die Antwort?</p>
            <div className="grid grid-cols-3 gap-2">
              <Button variant="outline" className="border-red-200 text-red-600 hover:bg-red-50" onClick={() => submitReview(1)}>
                <X className="w-4 h-4 mr-1" /> Nicht gewusst
              </Button>
              <Button variant="outline" className="border-yellow-200 text-yellow-600 hover:bg-yellow-50" onClick={() => submitReview(3)}>
                <RotateCcw className="w-4 h-4 mr-1" /> Schwer
              </Button>
              <Button variant="outline" className="border-green-200 text-green-600 hover:bg-green-50" onClick={() => submitReview(5)}>
                <Check className="w-4 h-4 mr-1" /> Leicht
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <BookOpen className="w-7 h-7 text-indigo-600" />
            Karteikarten
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Spaced Repetition für effizientes Lernen</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowAI(true)} className="gap-1">
            <Sparkles className="w-4 h-4" /> KI generieren
          </Button>
          <Button onClick={() => setShowCreate(true)} className="gap-1">
            <Plus className="w-4 h-4" /> Neues Deck
          </Button>
        </div>
      </div>

      {/* Create deck dialog */}
      {showCreate && (
        <Card className="border-indigo-200">
          <CardContent className="p-4 flex gap-3">
            <Input
              placeholder="Deck-Name (z.B. Mathe Klausur)"
              value={newDeckName}
              onChange={(e) => setNewDeckName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createDeck()}
            />
            <Button onClick={createDeck}>Erstellen</Button>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Abbrechen</Button>
          </CardContent>
        </Card>
      )}

      {/* AI generate dialog */}
      {showAI && (
        <Card className="border-purple-200">
          <CardContent className="p-4 space-y-3">
            <Input
              placeholder="Thema (z.B. Photosynthese, Quadratische Gleichungen)"
              value={aiTopic}
              onChange={(e) => setAiTopic(e.target.value)}
            />
            <div className="flex gap-3 items-center">
              <label className="text-sm text-gray-500">Anzahl:</label>
              <Input
                type="number"
                min={1}
                max={20}
                value={aiCount}
                onChange={(e) => setAiCount(parseInt(e.target.value) || 10)}
                className="w-20"
              />
              <Button onClick={generateAI} disabled={aiLoading} className="gap-1">
                {aiLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Generieren
              </Button>
              <Button variant="ghost" onClick={() => setShowAI(false)}>Abbrechen</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Deck list */}
      {decks.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Brain className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">Noch keine Karteikarten-Decks vorhanden.</p>
            <p className="text-sm text-gray-400 mt-1">Erstelle ein Deck oder lass die KI Karten generieren!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {decks.map((deck) => (
            <Card key={deck.id} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => startReview(deck.id)}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center justify-between">
                  {deck.name}
                  {deck.due_count > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-xs font-medium">
                      {deck.due_count} fällig
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-500">{deck.card_count} Karten</p>
                <Button variant="outline" className="w-full mt-3 gap-1" size="sm">
                  <RotateCcw className="w-4 h-4" /> Lernen
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
