"""KI Live-Wissen — 3-Stufen Wissenssystem.

STUFE 1: Tavily Web-Suche (Auto-Trigger bei bestimmten Faechern)
STUFE 2: Nightly Knowledge Update (APScheduler Job um 03:00)
STUFE 3: Wikipedia Fact-Check (fuer Geschichte, Biologie, Chemie, Physik, Geographie)
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STUFE 1: Fach-Erkennung + Tavily Auto-Trigger
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Faecher die IMMER Internet-Suche benoetigen (aktuelle Infos wichtig)
FAECHER_MIT_INTERNET = [
    "Geschichte", "Politik", "Wirtschaft", "Biologie",
    "Geographie", "Sozialkunde",
]

# Faecher fuer Wikipedia Fact-Check (STUFE 3)
FAECHER_MIT_WIKIPEDIA = [
    "Geschichte", "Biologie", "Chemie", "Physik", "Geographie",
]

# Abitur-relevante Suchthemen pro Fach
ABITUR_THEMEN = {
    "Geschichte": [
        "Weimarer Republik Abitur",
        "Kalter Krieg Deutschland",
        "Deutsche Wiedervereinigung",
        "Imperialismus Abitur",
        "Nationalsozialismus Abitur",
        "Industrialisierung Deutschland",
        "Erster Weltkrieg Abitur",
        "Zweiter Weltkrieg Abitur",
        "Europaeische Integration",
        "Globalisierung Geschichte",
    ],
    "Politik": [
        "Grundgesetz Deutschland aktuell",
        "Europaeische Union aktuell",
        "Demokratie Herausforderungen",
        "Klimapolitik Deutschland",
        "Sozialpolitik aktuell",
        "Bundestagswahl aktuell",
        "NATO aktuell",
        "Menschenrechte aktuell",
        "Digitalisierung Politik",
        "Migration Deutschland",
    ],
    "Wirtschaft": [
        "Konjunktur Deutschland aktuell",
        "Inflation aktuell",
        "Arbeitsmarkt Deutschland",
        "Globalisierung Wirtschaft",
        "Nachhaltigkeit Wirtschaft",
        "Soziale Marktwirtschaft",
        "EZB Geldpolitik aktuell",
        "Energiewende Deutschland",
        "Lieferketten aktuell",
        "Digitalisierung Wirtschaft",
    ],
    "Biologie": [
        "Gentechnik aktuell",
        "Klimawandel Oekosysteme",
        "Evolution Forschung",
        "Neurobiologie Forschung",
        "Immunbiologie aktuell",
        "Biodiversitaet aktuell",
        "Stammzellenforschung",
        "Epigenetik Forschung",
        "Oekologie aktuell",
        "Virologie aktuell",
    ],
    "Geographie": [
        "Klimawandel aktuell",
        "Stadtentwicklung Deutschland",
        "Naturkatastrophen aktuell",
        "Bevoelkerungsentwicklung",
        "Nachhaltige Entwicklung",
        "Erneuerbare Energien",
        "Globalisierung Geographie",
        "Wasserknappheit aktuell",
        "Plattentektonik aktuell",
        "Raumplanung Deutschland",
    ],
}


def fach_braucht_internet(fach: str) -> bool:
    """Pruefen ob ein Fach automatisch Internet-Suche benoetigt."""
    return fach in FAECHER_MIT_INTERNET


def fach_braucht_wikipedia(fach: str) -> bool:
    """Pruefen ob ein Fach Wikipedia Fact-Check benoetigt."""
    return fach in FAECHER_MIT_WIKIPEDIA


async def tavily_suche_fuer_fach(
    frage: str,
    fach: str,
    max_results: int = 3,
) -> dict:
    """STUFE 1: Automatische Tavily-Suche fuer Faecher die aktuelle Infos brauchen.

    Returns:
        {
            "kontext": str,  # Fuer System-Prompt Injection
            "quellen": [str],  # Formatierte Quellen-Links
            "ergebnisse": [dict],
        }
    """
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if not tavily_key:
        logger.warning("TAVILY_API_KEY nicht gesetzt")
        return {"kontext": "", "quellen": [], "ergebnisse": []}

    try:
        search_query = f"{frage} {fach} Deutschland Schule Abitur"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": search_query,
                    "search_depth": "advanced",
                    "max_results": max_results,
                    "include_domains": [
                        "wikipedia.org", "bpb.de", "planet-wissen.de",
                        "spektrum.de", "zeit.de", "spiegel.de",
                        "bildungsserver.de", "studysmarter.de",
                    ],
                },
            )

            if resp.status_code != 200:
                logger.warning("Tavily Fehler: %s", resp.status_code)
                return {"kontext": "", "quellen": [], "ergebnisse": []}

            data = resp.json()
            results = data.get("results", [])[:max_results]

            ergebnisse = []
            kontext_parts = []
            quellen = []

            for idx, r in enumerate(results, 1):
                titel = r.get("title", "")
                url = r.get("url", "")
                inhalt = r.get("content", "")[:500]

                ergebnisse.append({
                    "titel": titel,
                    "url": url,
                    "inhalt": inhalt,
                })
                kontext_parts.append(f"[{idx}] {titel}: {inhalt}")
                quellen.append(f"[{idx}] [{titel}]({url})")

            kontext = (
                f"Aktuelle Information (Stand heute, {datetime.now().strftime('%d.%m.%Y')}):\n"
                + "\n".join(kontext_parts)
            ) if kontext_parts else ""

            return {
                "kontext": kontext,
                "quellen": quellen,
                "ergebnisse": ergebnisse,
            }

    except Exception as e:
        logger.warning("Tavily Fach-Suche fehlgeschlagen: %s", e)
        return {"kontext": "", "quellen": [], "ergebnisse": []}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STUFE 2: Nightly Knowledge Update (03:00 Berlin)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def update_knowledge_base() -> dict:
    """Nightly Job: Top 10 Abitur-relevante Themen abrufen, indexieren, alte entfernen.

    Runs daily at 03:00 Europe/Berlin via APScheduler.

    Returns:
        {"neue_dokumente": int, "entfernte_dokumente": int, "faecher": [str]}
    """
    import aiosqlite

    logger.info("Knowledge Update gestartet (Nightly Job)")

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if not tavily_key:
        logger.warning("TAVILY_API_KEY nicht gesetzt — Knowledge Update uebersprungen")
        return {"neue_dokumente": 0, "entfernte_dokumente": 0, "faecher": []}

    db_path = os.getenv("DATABASE_PATH", "app.db")
    neue_dokumente = 0
    entfernte_dokumente = 0
    aktualisierte_faecher = []

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Fuer jedes Fach: Top Abitur-Themen abrufen
            for fach, themen in ABITUR_THEMEN.items():
                try:
                    # Waehle 2 zufaellige Themen pro Fach pro Nacht
                    import random
                    ausgewaehlte = random.sample(themen, min(2, len(themen)))

                    for thema in ausgewaehlte:
                        async with httpx.AsyncClient(timeout=15.0) as client:
                            resp = await client.post(
                                "https://api.tavily.com/search",
                                json={
                                    "api_key": tavily_key,
                                    "query": thema,
                                    "search_depth": "advanced",
                                    "max_results": 3,
                                },
                            )

                            if resp.status_code != 200:
                                continue

                            results = resp.json().get("results", [])

                            for r in results:
                                inhalt = r.get("content", "")
                                if len(inhalt) < 100:
                                    continue

                                # In knowledge_updates Tabelle speichern
                                await db.execute(
                                    """INSERT INTO knowledge_updates
                                    (fach, thema, quellen_count, created_at)
                                    VALUES (?, ?, 1, datetime('now'))""",
                                    (fach, thema),
                                )
                                neue_dokumente += 1

                    aktualisierte_faecher.append(fach)

                except Exception as fach_err:
                    logger.warning("Knowledge Update fuer %s fehlgeschlagen: %s", fach, fach_err)

            # Alte Eintraege entfernen (>90 Tage)
            grenze = (datetime.utcnow() - timedelta(days=90)).isoformat()
            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM knowledge_updates WHERE created_at < ?",
                (grenze,),
            )
            row = await cursor.fetchone()
            entfernte_dokumente = dict(row)["cnt"] if row else 0

            if entfernte_dokumente > 0:
                await db.execute(
                    "DELETE FROM knowledge_updates WHERE created_at < ?",
                    (grenze,),
                )

            await db.commit()

    except Exception as exc:
        logger.error("Knowledge Update fehlgeschlagen: %s", exc)

    logger.info(
        "Knowledge Update abgeschlossen: %d neue, %d entfernte Dokumente, Faecher: %s",
        neue_dokumente, entfernte_dokumente, aktualisierte_faecher,
    )

    return {
        "neue_dokumente": neue_dokumente,
        "entfernte_dokumente": entfernte_dokumente,
        "faecher": aktualisierte_faecher,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STUFE 3: Wikipedia Fact-Check
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def wikipedia_fact_check(
    thema: str,
    fach: str,
    sprache: str = "de",
) -> dict:
    """Wikipedia Fact-Check fuer Geschichte, Biologie, Chemie, Physik, Geographie.

    Uses the Wikipedia REST API (no external dependency needed).

    Returns:
        {
            "gefunden": bool,
            "zusammenfassung": str,
            "url": str,
            "kontext": str,  # Fuer Prompt-Injection
        }
    """
    if not fach_braucht_wikipedia(fach):
        return {"gefunden": False, "zusammenfassung": "", "url": "", "kontext": ""}

    try:
        # Use Wikipedia REST API directly (no pip dependency needed)
        wiki_api_url = f"https://{sprache}.wikipedia.org/api/rest_v1/page/summary/{thema}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                wiki_api_url,
                headers={"User-Agent": "LumnosBot/1.0 (Bildungs-KI)"},
            )

            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                title = data.get("title", thema)
                url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

                if extract:
                    # Kuerze auf 3 Saetze
                    saetze = extract.split(". ")
                    zusammenfassung = ". ".join(saetze[:3])
                    if not zusammenfassung.endswith("."):
                        zusammenfassung += "."

                    kontext = (
                        f"Wikipedia Fakten-Check ({title}):\n{zusammenfassung}\n"
                        f"Quelle: {url}"
                    )

                    return {
                        "gefunden": True,
                        "zusammenfassung": zusammenfassung,
                        "url": url,
                        "kontext": kontext,
                    }

            # Fallback: Suche nach dem Thema
            search_url = f"https://{sprache}.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": thema,
                "format": "json",
                "srlimit": 1,
            }
            resp = await client.get(
                search_url,
                params=params,
                headers={"User-Agent": "LumnosBot/1.0 (Bildungs-KI)"},
            )

            if resp.status_code == 200:
                data = resp.json()
                results = data.get("query", {}).get("search", [])
                if results:
                    page_title = results[0].get("title", "")
                    # Erneuter Abruf mit dem gefundenen Titel
                    summary_url = f"https://{sprache}.wikipedia.org/api/rest_v1/page/summary/{page_title}"
                    resp2 = await client.get(
                        summary_url,
                        headers={"User-Agent": "LumnosBot/1.0 (Bildungs-KI)"},
                    )
                    if resp2.status_code == 200:
                        data2 = resp2.json()
                        extract2 = data2.get("extract", "")
                        url2 = data2.get("content_urls", {}).get("desktop", {}).get("page", "")

                        if extract2:
                            saetze = extract2.split(". ")
                            zusammenfassung = ". ".join(saetze[:3])
                            if not zusammenfassung.endswith("."):
                                zusammenfassung += "."

                            kontext = (
                                f"Wikipedia Fakten-Check ({page_title}):\n{zusammenfassung}\n"
                                f"Quelle: {url2}"
                            )

                            return {
                                "gefunden": True,
                                "zusammenfassung": zusammenfassung,
                                "url": url2,
                                "kontext": kontext,
                            }

    except Exception as e:
        logger.warning("Wikipedia Fact-Check fehlgeschlagen: %s", e)

    return {"gefunden": False, "zusammenfassung": "", "url": "", "kontext": ""}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Kombinierte Wissens-Anreicherung (alle 3 Stufen)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def enrich_with_live_knowledge(
    frage: str,
    fach: str,
    user_tier: str = "free",
) -> dict:
    """Kombiniert alle 3 Stufen fuer maximale Wissensanreicherung.

    Returns:
        {
            "kontext": str,  # Gesamtkontext fuer System-Prompt
            "quellen": [str],
            "stufen_genutzt": [str],  # z.B. ["tavily", "wikipedia"]
        }
    """
    kontext_parts = []
    quellen = []
    stufen_genutzt = []

    # STUFE 1: Tavily fuer Faecher die aktuelle Infos brauchen
    # (nur Pro/Max User)
    if user_tier in ("pro", "max") and fach_braucht_internet(fach):
        tavily_result = await tavily_suche_fuer_fach(frage, fach)
        if tavily_result["kontext"]:
            kontext_parts.append(tavily_result["kontext"])
            quellen.extend(tavily_result["quellen"])
            stufen_genutzt.append("tavily")

    # STUFE 3: Wikipedia Fact-Check (fuer alle User bei bestimmten Faechern)
    if fach_braucht_wikipedia(fach):
        # Extrahiere Hauptthema aus der Frage (erste 3-4 Woerter)
        woerter = frage.split()
        thema = " ".join(woerter[:4]) if len(woerter) >= 4 else frage
        wiki_result = await wikipedia_fact_check(thema, fach)
        if wiki_result["gefunden"]:
            kontext_parts.append(wiki_result["kontext"])
            if wiki_result["url"]:
                quellen.append(f"[Wikipedia] {wiki_result['url']}")
            stufen_genutzt.append("wikipedia")

    gesamt_kontext = "\n\n".join(kontext_parts) if kontext_parts else ""

    return {
        "kontext": gesamt_kontext,
        "quellen": quellen,
        "stufen_genutzt": stufen_genutzt,
    }
