/**
 * Perfect School 4.1 Block 4: Offline-First Karteikarten
 *
 * IndexedDB storage + SM-2 spaced repetition algorithm.
 * Cards are stored locally and synced when online.
 */

const DB_NAME = "eduai_flashcards";
const DB_VERSION = 1;
const STORE_DECKS = "decks";
const STORE_CARDS = "cards";

export interface LocalDeck {
  id: string;
  name: string;
  subject: string;
  createdAt: string;
  synced: boolean;
}

export interface LocalCard {
  id: string;
  deckId: string;
  front: string;
  back: string;
  // SM-2 fields
  easeFactor: number; // starts at 2.5
  interval: number; // days until next review
  repetitions: number; // successful reviews in a row
  nextReview: string; // ISO date
  synced: boolean;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_DECKS)) {
        db.createObjectStore(STORE_DECKS, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(STORE_CARDS)) {
        const store = db.createObjectStore(STORE_CARDS, { keyPath: "id" });
        store.createIndex("deckId", "deckId", { unique: false });
        store.createIndex("nextReview", "nextReview", { unique: false });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// --- Deck CRUD ---

export async function getAllDecks(): Promise<LocalDeck[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_DECKS, "readonly");
    const store = tx.objectStore(STORE_DECKS);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function saveDeck(deck: LocalDeck): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_DECKS, "readwrite");
    const store = tx.objectStore(STORE_DECKS);
    store.put(deck);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteDeck(id: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORE_DECKS, STORE_CARDS], "readwrite");
    tx.objectStore(STORE_DECKS).delete(id);
    // Also delete all cards in the deck
    const cardStore = tx.objectStore(STORE_CARDS);
    const idx = cardStore.index("deckId");
    const cursorReq = idx.openCursor(IDBKeyRange.only(id));
    cursorReq.onsuccess = () => {
      const cursor = cursorReq.result;
      if (cursor) {
        cursor.delete();
        cursor.continue();
      }
    };
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// --- Card CRUD ---

export async function getCardsByDeck(deckId: string): Promise<LocalCard[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_CARDS, "readonly");
    const store = tx.objectStore(STORE_CARDS);
    const idx = store.index("deckId");
    const req = idx.getAll(IDBKeyRange.only(deckId));
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function getDueCards(deckId: string): Promise<LocalCard[]> {
  const cards = await getCardsByDeck(deckId);
  const now = new Date().toISOString();
  return cards.filter((c) => c.nextReview <= now);
}

export async function saveCard(card: LocalCard): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_CARDS, "readwrite");
    tx.objectStore(STORE_CARDS).put(card);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteCard(id: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_CARDS, "readwrite");
    tx.objectStore(STORE_CARDS).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// --- SM-2 Algorithm ---

/**
 * SM-2 Spaced Repetition Algorithm.
 * quality: 0-5 (0=total blackout, 5=perfect response)
 *
 * Returns updated card fields.
 */
export function sm2Review(
  card: LocalCard,
  quality: number
): Pick<LocalCard, "easeFactor" | "interval" | "repetitions" | "nextReview"> {
  let { easeFactor, interval, repetitions } = card;

  if (quality < 3) {
    // Failed: reset
    repetitions = 0;
    interval = 1;
  } else {
    // Passed
    repetitions += 1;
    if (repetitions === 1) {
      interval = 1;
    } else if (repetitions === 2) {
      interval = 6;
    } else {
      interval = Math.round(interval * easeFactor);
    }
  }

  // Update ease factor (min 1.3)
  easeFactor = Math.max(
    1.3,
    easeFactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
  );

  const nextDate = new Date();
  nextDate.setDate(nextDate.getDate() + interval);

  return {
    easeFactor,
    interval,
    repetitions,
    nextReview: nextDate.toISOString(),
  };
}

/**
 * Create a new card with default SM-2 values.
 */
export function createCard(
  deckId: string,
  front: string,
  back: string
): LocalCard {
  return {
    id: `card_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    deckId,
    front,
    back,
    easeFactor: 2.5,
    interval: 0,
    repetitions: 0,
    nextReview: new Date().toISOString(),
    synced: false,
  };
}
