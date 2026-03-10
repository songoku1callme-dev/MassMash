"""Internet-KI — Tavily-Integration für Echtzeit-Websuche.

Entscheidet intelligent, ob eine Frage Internet-Recherche braucht,
und liefert aktuelle Web-Quellen für Pro/Max-Nutzer.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Signalwörter die Internet-Suche auslösen
INTERNET_TRIGGER = [
    "aktuell", "heute", "2024", "2025", "2026",
    "neueste", "kürzlich", "news", "nachrichten",
    "forschung", "studie", "statistik",
    "vergleich", "ranking", "trend",
    "wie viele", "wie hoch", "wie teuer",
    "preis", "kosten",
]

# Wörter die GEGEN Internet sprechen (rein schulisch)
KEIN_INTERNET = [
    "berechne", "löse", "vereinfache",
    "ableitung", "integral", "gleichung",
    "2+2", "wurzel", "bruch",
    "konjugiere", "dekliniere",
    "was ist ein", "definiere",
    "erkläre den unterschied",
]

# Bildungs-Domains für Tavily-Suche
BILDUNGS_DOMAINS = [
    "wikipedia.org",
    "lehrplanplus.bayern.de",
    "bildungsserver.de",
    "planet-wissen.de",
    "spektrum.de",
    "geo.de",
    "zeit.de/wissen",
    "bpb.de",
    "studysmarter.de",
    "simpleclub.com",
]


def braucht_internet(frage: str) -> bool:
    """Entscheidet ob eine Frage Internet-Recherche braucht.

    Returns True wenn:
    - Aktualitäts-Keywords vorhanden (z.B. "aktuell", "2025", "Forschung")
    - UND keine reinen Rechen-Keywords vorhanden

    Returns False wenn:
    - Reine Mathe/Grammatik-Frage
    - Definition die das LLM kennt
    """
    text = frage.lower()

    # Erst prüfen: Ist es eine reine Rechen/Grammatik-Frage?
    for keyword in KEIN_INTERNET:
        if keyword in text:
            return False

    # Dann prüfen: Braucht es aktuelle Infos?
    for trigger in INTERNET_TRIGGER:
        if trigger in text:
            return True

    return False


async def suche_internet(
    frage: str,
    fach: str = "Allgemein",
    max_results: int = 3,
) -> dict:
    """Durchsucht das Internet via Tavily API.

    Returns:
        {
            "ergebnisse": [{"titel": ..., "url": ..., "inhalt": ...}],
            "kontext": str,  # Für System-Prompt
            "quellen": [str],  # Formatierte Quellen-Links
        }
    """
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if not tavily_key:
        logger.warning("TAVILY_API_KEY nicht gesetzt — Internet-Suche deaktiviert")
        return {"ergebnisse": [], "kontext": "", "quellen": []}

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Suchquery optimieren für Bildungskontext
            search_query = f"{frage} {fach} Deutschland Schule Gymnasium"

            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": search_query,
                    "search_depth": "advanced",
                    "max_results": max_results,
                    "include_domains": BILDUNGS_DOMAINS,
                },
            )

            if resp.status_code != 200:
                logger.warning("Tavily API Fehler: %s", resp.status_code)
                return {"ergebnisse": [], "kontext": "", "quellen": []}

            data = resp.json()
            results = data.get("results", [])[:max_results]

            ergebnisse = []
            kontext_parts = []
            quellen = []

            for idx, r in enumerate(results, 1):
                titel = r.get("title", "")
                url = r.get("url", "")
                inhalt = r.get("content", "")[:400]

                ergebnisse.append({
                    "titel": titel,
                    "url": url,
                    "inhalt": inhalt,
                })
                kontext_parts.append(f"[{idx}] {titel}: {inhalt}")
                quellen.append(f"[{idx}] [{titel}]({url})")

            kontext = "\n".join(kontext_parts)

            return {
                "ergebnisse": ergebnisse,
                "kontext": kontext,
                "quellen": quellen,
            }

    except Exception as e:
        logger.warning("Internet-Suche fehlgeschlagen: %s", e)
        return {"ergebnisse": [], "kontext": "", "quellen": []}


async def chat_mit_internet(
    frage: str,
    fach: str = "Allgemein",
    user_tier: str = "free",
) -> dict:
    """Hauptfunktion: Chat mit optionaler Internet-Recherche.

    Returns:
        {
            "internet_genutzt": bool,
            "web_kontext": str,  # Für System-Prompt
            "web_quellen": [str],  # Formatierte Quellen
        }
    """
    # Nur Pro/Max bekommen Internet-Suche
    if user_tier not in ("pro", "max"):
        return {
            "internet_genutzt": False,
            "web_kontext": "",
            "web_quellen": [],
        }

    # Prüfe ob Internet nötig ist
    if not braucht_internet(frage):
        return {
            "internet_genutzt": False,
            "web_kontext": "",
            "web_quellen": [],
        }

    # Internet-Suche durchführen
    result = await suche_internet(frage, fach)

    return {
        "internet_genutzt": bool(result["ergebnisse"]),
        "web_kontext": result["kontext"],
        "web_quellen": result["quellen"],
    }
