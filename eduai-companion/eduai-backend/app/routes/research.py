"""Internet Research routes - Tavily API scaffold for live curriculum sources.

Max tier only. Provides web search for Abitur-relevant content.
Falls back to mock results if no TAVILY_API_KEY is configured.
"""
import json
import logging
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.services.groq_llm import call_groq_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


def _require_max_tier(user_tier: str) -> None:
    """Raise 403 if user is not on Max tier."""
    if user_tier != "max":
        raise HTTPException(
            status_code=403,
            detail="Internet-Recherche ist nur f\u00fcr Max-Abonnenten verf\u00fcgbar. Upgrade auf Max f\u00fcr 19,99\u20ac/Monat.",
        )


async def _get_user_tier(user_id: int, db: aiosqlite.Connection) -> str:
    """Get user's subscription tier."""
    cursor = await db.execute(
        "SELECT subscription_tier FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return (dict(row).get("subscription_tier", "free") or "free") if row else "free"


async def _search_tavily(query: str, max_results: int = 10) -> list[dict]:
    """Search using Tavily API. Returns list of {title, url, content, score}."""
    if not TAVILY_API_KEY:
        logger.info("Tavily API key not configured, returning scaffold results")
        return _mock_search_results(query)

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": max_results,
                    "include_answer": True,
                    "include_domains": [
                        "lehrplanplus.bayern.de",
                        "bildungsserver.de",
                        "bildung.de",
                        "studyflix.de",
                        "serlo.org",
                        "wikipedia.org",
                        "abitur.com",
                    ],
                },
            )
            if response.status_code == 200:
                data = response.json()
                results = []
                for r in data.get("results", []):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", "")[:500],
                        "score": r.get("score", 0),
                    })
                return results
            else:
                logger.error("Tavily API error: %s %s", response.status_code, response.text)
                return _mock_search_results(query)
    except ImportError:
        logger.warning("httpx not installed, using mock results")
        return _mock_search_results(query)
    except Exception as e:
        logger.error("Tavily search error: %s", e)
        return _mock_search_results(query)


def _mock_search_results(query: str) -> list[dict]:
    """Return mock search results when Tavily is not available."""
    return [
        {
            "title": f"Lehrplan: {query}",
            "url": "https://lehrplanplus.bayern.de",
            "content": f"Lehrplaninhalte zu '{query}' - Bayerischer Lehrplan. "
                       "Hinweis: F\u00fcr echte Suchergebnisse TAVILY_API_KEY setzen.",
            "score": 0.9,
        },
        {
            "title": f"Studyflix: {query} einfach erkl\u00e4rt",
            "url": "https://studyflix.de",
            "content": f"Einfache Erkl\u00e4rung zu '{query}' mit Videos und Beispielen.",
            "score": 0.85,
        },
        {
            "title": f"Serlo: {query} - freie Lernplattform",
            "url": "https://serlo.org",
            "content": f"Kostenlose Lernmaterialien zu '{query}' auf Serlo.",
            "score": 0.8,
        },
    ]


@router.post("/search")
async def search_curriculum(
    query: str,
    subject: str = "",
    max_results: int = 10,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Search for Abitur-relevant curriculum sources online.

    Max tier only. Uses Tavily API (or mock if no key configured).
    """
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    max_results = max(1, min(20, max_results))

    # Enhance query for German education context
    enhanced_query = f"Abitur {subject} {query}" if subject else f"Abitur {query}"
    results = await _search_tavily(enhanced_query, max_results)

    # Store results
    await db.execute(
        """INSERT INTO research_results (user_id, query, results_json, source_count)
        VALUES (?, ?, ?, ?)""",
        (user_id, query, json.dumps(results, ensure_ascii=False), len(results)),
    )
    await db.commit()

    return {
        "query": query,
        "enhanced_query": enhanced_query,
        "results": results,
        "source_count": len(results),
        "tavily_enabled": bool(TAVILY_API_KEY),
    }


@router.post("/ask-with-sources")
async def ask_with_sources(
    question: str,
    subject: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Ask a question with internet research context injected into Groq.

    Max tier only. Searches online, then passes results as context to Groq LLM.
    """
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    # Search for sources
    enhanced_query = f"Abitur {subject} {question}" if subject else f"Abitur {question}"
    sources = await _search_tavily(enhanced_query, max_results=5)

    # Build context from sources
    source_context = ""
    source_urls = []
    for s in sources:
        source_context += f"Quelle: {s['title']} ({s['url']})\n{s['content']}\n\n"
        source_urls.append(f"- [{s['title']}]({s['url']})")

    # Call Groq with source context
    system_prompt = (
        "Du bist ein Abitur-Experte mit Zugang zu aktuellen Quellen.\n"
        f"AKTUELLE QUELLEN (Internet):\n{source_context}\n"
        "Beantworte die Frage des Sch\u00fclers basierend auf diesen Quellen.\n"
        "Zitiere die Quellen in deiner Antwort."
    )

    response = call_groq_llm(
        prompt=question,
        system_prompt=system_prompt,
        subject=subject or "general",
        level="advanced",
        language="de",
        is_pro=True,
    )

    # Append source list
    if source_urls:
        response += "\n\n---\n**Quellen:**\n" + "\n".join(source_urls)

    return {
        "answer": response,
        "sources": sources,
        "source_count": len(sources),
        "tavily_enabled": bool(TAVILY_API_KEY),
    }


@router.get("/history")
async def research_history(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get research history for the user."""
    user_id = current_user["id"]
    cursor = await db.execute(
        """SELECT id, query, source_count, created_at
        FROM research_results WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 20""",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return {"results": [dict(r) for r in rows]}
