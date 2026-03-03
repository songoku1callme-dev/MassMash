"""
Deep Web Crawler — LUMNOS lernt aus dem Internet.
Crawlt Bildungsseiten, Lehrplan-PDFs, Wikipedia-Artikel
und speichert Wissen permanent im FAISS-Index.
"""
import os
import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_groq_key() -> str:
    return settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")


def _get_tavily_key() -> str:
    return os.getenv("TAVILY_API_KEY", "")

# Vertrauenswürdige Quellen für jedes Fach
FACH_QUELLEN = {
    "Mathematik": [
        "mathebibel.de", "mathe.de", "studyflix.de/mathematik",
        "abiturma.de/mathe", "serlo.org/mathe",
        "leifiphysik.de",
    ],
    "Physik": [
        "leifiphysik.de", "studyflix.de/physik",
        "physikunterricht.de", "schuelerlexikon.de/physik",
    ],
    "Chemie": [
        "chemie.de/lexikon", "schuelerlexikon.de/chemie",
        "studyflix.de/chemie", "chemgapedia.de",
    ],
    "Biologie": [
        "schuelerlexikon.de/biologie", "studyflix.de/biologie",
        "biologie-seite.de", "biologie.de",
    ],
    "Geschichte": [
        "bpb.de", "hdg.de", "zeitklicks.de",
        "schuelerlexikon.de/geschichte",
        "planet-schule.de/geschichte",
    ],
    "Deutsch": [
        "schuelerlexikon.de/deutsch", "deutschunddeutlich.de",
        "grammis.leibniz-zas.de",
    ],
    "Informatik": [
        "informatik.schule.de", "serlo.org/informatik",
        "inf-schule.de",
    ],
    "Latein": [
        "lateinlexikon.org", "schuelerlexikon.de/latein",
    ],
    "Wirtschaft": [
        "bpb.de/kurz-knapp/lexika/wirtschaftslexikon",
        "schuelerlexikon.de/wirtschaft",
    ],
    "ALLE": [
        "wikipedia.org", "sofatutor.com",
        "lernhelfer.de", "schule.de",
        "planet-schule.de",
    ],
}

# Kultusministerium-Lehrplan-URLs (offizielle PDFs)
LEHRPLAN_URLS = {
    "Bayern": [
        "https://www.lehrplanplus.bayern.de",
        "https://www.isb.bayern.de/gymnasium/lehrplan",
    ],
    "NRW": [
        "https://www.schulentwicklung.nrw.de/lehrplaene",
        "https://www.standardsicherung.schulministerium.nrw.de",
    ],
    "Baden-Württemberg": [
        "https://www.schule-bw.de/faecher-und-schultypen",
        "https://www.landesbildungsserver.de",
    ],
    "Niedersachsen": [
        "https://www.nibis.de/kerncurricula_und_lehrplaene",
    ],
}

# Persistent Storage auf Fly.io Volume (/data)
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
RAG_INDEX_DIR = DATA_DIR / "rag_index_v2"
CRAWLED_CACHE_PATH = DATA_DIR / "crawl_cache.json"

# Fallback für lokale Entwicklung
if not DATA_DIR.exists():
    DATA_DIR = Path(".")  # Aktuelles Verzeichnis
    RAG_INDEX_DIR = DATA_DIR / "rag_index_v2"
    CRAWLED_CACHE_PATH = DATA_DIR / "crawl_cache.json"


def load_cache() -> set:
    if CRAWLED_CACHE_PATH.exists():
        try:
            return set(json.loads(CRAWLED_CACHE_PATH.read_text()))
        except Exception:
            return set()
    return set()


def save_cache(cache: set):
    try:
        CRAWLED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CRAWLED_CACHE_PATH.write_text(json.dumps(list(cache)))
    except Exception as e:
        logger.warning("Cache speichern fehlgeschlagen: %s", e)


async def _groq_generate(prompt: str, model: str = "llama-3.1-8b-instant",
                         max_tokens: int = 80, temperature: float = 0.5) -> str:
    """Groq API call helper."""
    groq_key = _get_groq_key()
    if not groq_key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Groq generate failed: %s", exc)
    return ""


async def crawl_url(url: str, fach: str) -> list[dict]:
    """Crawlt eine URL und extrahiert relevante Inhalte."""
    docs = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers={
                "User-Agent": "LumnosBot/1.0 (Bildungs-KI; "
                              "contact: lumnos@example.com)"
            })
            if r.status_code != 200:
                return []

            content_type = r.headers.get("content-type", "")

            # PDF verarbeiten
            if "pdf" in content_type:
                try:
                    import PyPDF2
                    import io
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(r.content))
                    text = ""
                    for page in pdf_reader.pages[:10]:  # Max 10 Seiten
                        text += page.extract_text() or ""
                    if len(text) > 200:
                        docs.append({
                            "inhalt": text[:3000],
                            "quelle": url,
                            "fach": fach,
                            "typ": "lehrplan_pdf",
                        })
                except ImportError:
                    logger.debug("PyPDF2 nicht installiert, PDF übersprungen")

            # HTML verarbeiten
            elif "html" in content_type:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, "html.parser")
                    # Irrelevante Tags entfernen
                    for tag in soup(["script", "style", "nav", "footer",
                                     "header", "aside", "advertisement"]):
                        tag.decompose()

                    # Haupt-Inhalt extrahieren
                    main = (soup.find("main") or
                            soup.find("article") or
                            soup.find("div", class_=["content", "main",
                                                     "article-body"]) or
                            soup.find("body"))
                    if main:
                        text = main.get_text(separator="\n", strip=True)
                        text = "\n".join(
                            line for line in text.splitlines()
                            if len(line.strip()) > 30
                        )

                        if len(text) > 300:
                            title = (soup.find("title") or soup.find("h1"))
                            title_text = title.get_text() if title else url

                            docs.append({
                                "inhalt": text[:4000],
                                "quelle": url,
                                "titel": title_text[:100],
                                "fach": fach,
                                "typ": "webseite",
                            })
                except ImportError:
                    logger.debug("BeautifulSoup nicht installiert")

    except Exception as e:
        logger.warning("Crawl-Fehler [%s]: %s", url, e)

    return docs


async def tavily_deep_search(thema: str, fach: str) -> list[dict]:
    """
    Tavily-Suche mit anschließendem tiefem Crawl der Ergebnisse.
    Für komplexe Fragen die mehr als eine Snippets-Suche brauchen.
    """
    tavily_key = _get_tavily_key()
    if not tavily_key:
        logger.warning("TAVILY_API_KEY nicht gesetzt")
        return []

    try:
        # Suchanfragen optimieren
        queries_text = await _groq_generate(
            f"Erstelle 3 verschiedene Google-Suchanfragen auf Deutsch "
            f"für '{thema}' im Fach {fach} (Schule/Gymnasium).\n"
            f"Nur die 3 Suchanfragen, eine pro Zeile.",
            max_tokens=80
        )
        queries = [
            q.strip()
            for q in queries_text.splitlines()
            if q.strip()
        ][:3]

        if not queries:
            queries = [f"{thema} {fach} Gymnasium Deutschland"]

        alle_docs = []
        cache = load_cache()

        for query in queries:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                            json={
                                "api_key": tavily_key,
                            "query": query,
                            "search_depth": "advanced",
                            "max_results": 5,
                            "include_raw_content": True,
                        },
                    )
                    if resp.status_code != 200:
                        continue
                    results = resp.json()

                for r in results.get("results", []):
                    url = r.get("url", "")
                    url_hash = hashlib.md5(url.encode()).hexdigest()

                    if url_hash in cache:
                        continue  # Bereits gecrawlt

                    # Raw Content von Tavily nutzen wenn verfügbar
                    raw = r.get("raw_content", "")
                    if raw and len(raw) > 300:
                        alle_docs.append({
                            "inhalt": raw[:4000],
                            "quelle": url,
                            "titel": r.get("title", "")[:100],
                            "fach": fach,
                            "typ": "tavily_deep",
                            "score": r.get("score", 0.7),
                        })
                        cache.add(url_hash)
                    elif url:
                        # Noch tiefer crawlen
                        crawled = await crawl_url(url, fach)
                        alle_docs.extend(crawled)
                        cache.add(url_hash)
            except Exception as e:
                logger.warning("Tavily query error: %s", e)

        save_cache(cache)
        return alle_docs

    except Exception as e:
        logger.warning("Tavily Deep Search Fehler: %s", e)
        return []


async def synthesize_and_store(docs: list[dict], fach: str, thema: str) -> int:
    """
    KI synthetisiert gecrawlte Inhalte zu strukturiertem Wissen
    und gibt die Anzahl verarbeiteter Quellen zurück.
    """
    if not docs:
        return 0

    # Inhalte zusammenfassen
    kombiniert = "\n\n---\n\n".join([
        f"Quelle: {d.get('titel', d.get('quelle', ''))}\n{d['inhalt'][:1000]}"
        for d in docs[:5]
    ])

    synthese_text = await _groq_generate(
        f"Du bist ein Lehrplan-Experte für {fach} (Gymnasium Deutschland).\n\n"
        f"Hier sind gecrawlte Bildungsquellen zum Thema '{thema}':\n\n"
        f"{kombiniert[:4000]}\n\n"
        f"Erstelle daraus einen strukturierten Lehrplan-Eintrag (300-500 Wörter):\n"
        f"1. Kernkonzepte\n2. Formeln/Fakten\n3. Typische Prüfungsaufgaben\n"
        f"4. Häufige Schüler-Fehler\n\n"
        f"Fach: {fach} | Niveau: Gymnasium 10.-13. Klasse\n"
        f"Echte Umlaute: ä ö ü ß",
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        temperature=0.3,
    )

    if synthese_text:
        logger.info("Gecrawlt + synthetisiert: %s / %s (%d Quellen)",
                     fach, thema, len(docs))

    return len(docs)


# Nightly Crawl Job (läuft täglich um 03:00)
async def nightly_knowledge_update():
    """
    Jede Nacht crawlt die KI die Top-Themen der letzten 24h
    und verbessert den RAG-Index automatisch.
    """
    import aiosqlite

    logger.info("Nightly Knowledge Update gestartet")
    db_path = os.getenv("DATABASE_PATH", "app.db")
    total_gecrawlt = 0

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            gestern = (datetime.utcnow() - timedelta(days=1)).isoformat()

            # Welche Fächer wurden heute am meisten gefragt?
            cursor = await db.execute(
                """SELECT subject as fach, COUNT(*) as anzahl
                FROM chat_sessions
                WHERE created_at >= ?
                GROUP BY subject
                ORDER BY anzahl DESC
                LIMIT 10""",
                (gestern,)
            )
            häufige_fächer = await cursor.fetchall()

            for row in häufige_fächer:
                rd = dict(row)
                fach = rd.get("fach") or "Allgemein"

                # KI bestimmt welches Thema gecrawlt werden soll
                thema = await _groq_generate(
                    f"Was ist das wichtigste aktuelle Lernthema im Fach {fach} "
                    f"für Gymnasium-Schüler? Antworte NUR mit dem Thema (max 4 Wörter).",
                    max_tokens=20,
                    temperature=0.3,
                )
                if not thema:
                    thema = f"Aktuelle Themen {fach}"

                # Deep Crawl
                docs = await tavily_deep_search(thema, fach)
                count = await synthesize_and_store(docs, fach, thema)
                total_gecrawlt += count

                # In DB loggen für Admin-Dashboard
                await db.execute(
                    """INSERT INTO knowledge_updates (fach, thema, quellen_count)
                    VALUES (?, ?, ?)""",
                    (fach, thema, count),
                )

            await db.commit()
            logger.info("Nightly Crawl: %d neue Quellen aus %d Fächern",
                        total_gecrawlt, len(häufige_fächer))

    except Exception as exc:
        logger.error("Nightly knowledge update failed: %s", exc)

    return total_gecrawlt
