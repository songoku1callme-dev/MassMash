"""KI Live-Wissen — 3-Stufen Wissenssystem.

STUFE 1: Tavily Web-Suche (Auto-Trigger bei bestimmten Fächern)
STUFE 2: Nightly Knowledge Update (APScheduler Job um 03:00)
STUFE 3: Wikipedia Fact-Check (für Geschichte, Biologie, Chemie, Physik, Geographie)
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

# Fächer die IMMER Internet-Suche benötigen (aktuelle Infos wichtig)
FAECHER_MIT_INTERNET = [
    "Geschichte", "Politik", "Wirtschaft", "Biologie",
    "Geographie", "Sozialkunde",
]

# Fächer für Wikipedia Fact-Check (STUFE 3)
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
    """Prüfen ob ein Fach automatisch Internet-Suche benötigt."""
    return fach in FAECHER_MIT_INTERNET


def fach_braucht_wikipedia(fach: str) -> bool:
    """Prüfen ob ein Fach Wikipedia Fact-Check benötigt."""
    return fach in FAECHER_MIT_WIKIPEDIA


async def tavily_suche_für_fach(
    frage: str,
    fach: str,
    max_results: int = 3,
) -> dict:
    """STUFE 1: Automatische Tavily-Suche für Fächer die aktuelle Infos brauchen.

    Returns:
        {
            "kontext": str,  # Für System-Prompt Injection
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

            # Für jedes Fach: Top Abitur-Themen abrufen
            for fach, themen in ABITUR_THEMEN.items():
                try:
                    # Wähle 2 zufällige Themen pro Fach pro Nacht
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
                    logger.warning("Knowledge Update für %s fehlgeschlagen: %s", fach, fach_err)

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
        "Knowledge Update abgeschlossen: %d neue, %d entfernte Dokumente, Fächer: %s",
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
    """Wikipedia Fact-Check für Geschichte, Biologie, Chemie, Physik, Geographie.

    Uses the Wikipedia REST API (no external dependency needed).

    Returns:
        {
            "gefunden": bool,
            "zusammenfassung": str,
            "url": str,
            "kontext": str,  # Für Prompt-Injection
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
    """Kombiniert alle 3 Stufen für maximale Wissensanreicherung.

    Returns:
        {
            "kontext": str,  # Gesamtkontext für System-Prompt
            "quellen": [str],
            "stufen_genutzt": [str],  # z.B. ["tavily", "wikipedia"]
        }
    """
    kontext_parts = []
    quellen = []
    stufen_genutzt = []

    # STUFE 1: Tavily für Fächer die aktuelle Infos brauchen
    # (nur Pro/Max User)
    if user_tier in ("pro", "max") and fach_braucht_internet(fach):
        tavily_result = await tavily_suche_für_fach(frage, fach)
        if tavily_result["kontext"]:
            kontext_parts.append(tavily_result["kontext"])
            quellen.extend(tavily_result["quellen"])
            stufen_genutzt.append("tavily")

    # STUFE 3: Wikipedia Fact-Check (für alle User bei bestimmten Fächern)
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PR #52 — AUFGABE 2A: Daily Knowledge Update (alle 16 Fächer)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Alle 16 Fächer mit Abitur-Suchbegriffen
ALLE_FAECHER_THEMEN = {
    "Mathematik": [
        "Analysis Abitur", "Stochastik Abitur", "Lineare Algebra Abitur",
        "Integralrechnung Gymnasium", "Vektorrechnung Abitur",
    ],
    "Deutsch": [
        "Lyrikanalyse Abitur", "Dramenanalyse Abitur", "Erörterung Gymnasium",
        "Epochen deutscher Literatur", "Sprachanalyse Abitur",
    ],
    "Englisch": [
        "English Literature Abitur", "Mediation Abitur Englisch",
        "Essay Writing Gymnasium", "British American Culture",
    ],
    "Physik": [
        "Quantenphysik Abitur", "Elektrodynamik Gymnasium",
        "Mechanik Abitur", "Optik Gymnasium",
    ],
    "Chemie": [
        "Organische Chemie Abitur", "Elektrochemie Gymnasium",
        "Thermodynamik Chemie", "Saeure-Base Abitur",
    ],
    "Biologie": [
        "Genetik Abitur", "Oekologie Abitur",
        "Neurobiologie Gymnasium", "Evolution Abitur",
    ],
    "Geschichte": [
        "Weimarer Republik Abitur", "Kalter Krieg Abitur",
        "Nationalsozialismus Abitur", "Deutsche Wiedervereinigung",
    ],
    "Geografie": [
        "Klimawandel Geografie Abitur", "Stadtentwicklung Deutschland",
        "Globalisierung Geografie", "Nachhaltigkeit Abitur",
    ],
    "Wirtschaft": [
        "Soziale Marktwirtschaft Abitur", "Konjunktur Deutschland",
        "Globalisierung Wirtschaft", "Geldpolitik EZB",
    ],
    "Ethik": [
        "Utilitarismus Ethik Abitur", "Menschenwürde Grundgesetz",
        "Gerechtigkeit Philosophie", "Bioethik aktuell",
    ],
    "Informatik": [
        "Algorithmen Datenstrukturen Abitur", "Objektorientierung Informatik",
        "Datenbanken SQL Gymnasium", "Kryptografie Informatik",
    ],
    "Kunst": [
        "Kunstgeschichte Epochen Abitur", "Bildanalyse Gymnasium",
        "Moderne Kunst Abitur", "Architektur Analyse",
    ],
    "Musik": [
        "Musiktheorie Abitur", "Musikgeschichte Epochen",
        "Werkanalyse Musik Gymnasium", "Jazz Blues Geschichte",
    ],
    "Sozialkunde": [
        "Demokratie Deutschland Abitur", "Europaeische Union aktuell",
        "Sozialstaat Deutschland", "Grundrechte Grundgesetz",
    ],
    "Latein": [
        "Caesar Bellum Gallicum", "Cicero Reden Latein",
        "Ovid Metamorphosen", "Vergil Aeneis",
    ],
    "Franzoesisch": [
        "France Culture Abitur", "Grammatik Franzoesisch Gymnasium",
        "Francophonie aktuell", "Literatur Franzoesisch Abitur",
    ],
}


async def update_knowledge_base_all_subjects() -> dict:
    """AUFGABE 2A: Tägliche Tavily-Suche für alle 16 Fächer.
    Indexiert Top 3 Ergebnisse pro Fach, loescht Eintraege > 30 Tage.

    Returns:
        {"faecher_aktualisiert": int, "neue_dokumente": int,
         "entfernte_dokumente": int}
    """
    import aiosqlite

    logger.info("Job: update_knowledge_base_all_subjects gestartet")

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if not tavily_key:
        logger.warning("TAVILY_API_KEY nicht gesetzt — Knowledge Update uebersprungen")
        return {"faecher_aktualisiert": 0, "neue_dokumente": 0, "entfernte_dokumente": 0}

    db_path = os.getenv("DATABASE_PATH", "app.db")
    neue_dokumente = 0
    faecher_aktualisiert = 0

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            import random

            for fach, themen in ALLE_FAECHER_THEMEN.items():
                try:
                    # 1 zufälliges Thema pro Fach pro Tag
                    thema = random.choice(themen)

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

                        results = resp.json().get("results", [])[:3]

                        for r in results:
                            inhalt = r.get("content", "")
                            titel = r.get("title", "")
                            url = r.get("url", "")
                            if len(inhalt) < 100:
                                continue

                            await db.execute(
                                """INSERT INTO knowledge_updates
                                (fach, thema, quellen_count, inhalt, titel, url, created_at)
                                VALUES (?, ?, 1, ?, ?, ?, datetime('now'))""",
                                (fach, thema, inhalt[:2000], titel[:200], url[:500]),
                            )
                            neue_dokumente += 1

                    faecher_aktualisiert += 1

                except Exception as fach_err:
                    logger.warning("Knowledge Update für %s fehlgeschlagen: %s", fach, fach_err)

            # Eintraege aelter als 30 Tage loeschen
            grenze = (datetime.utcnow() - timedelta(days=30)).isoformat()
            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM knowledge_updates WHERE created_at < ?",
                (grenze,),
            )
            row = await cursor.fetchone()
            entfernte = dict(row)["cnt"] if row else 0

            if entfernte > 0:
                await db.execute(
                    "DELETE FROM knowledge_updates WHERE created_at < ?",
                    (grenze,),
                )

            await db.commit()

    except Exception as exc:
        logger.error("update_knowledge_base_all_subjects fehlgeschlagen: %s", exc)
        return {"faecher_aktualisiert": 0, "neue_dokumente": 0, "entfernte_dokumente": 0}

    logger.info(
        "Knowledge Update (alle Fächer): %d Fächer, %d neue, %d entfernte Dokumente",
        faecher_aktualisiert, neue_dokumente, entfernte,
    )
    return {
        "faecher_aktualisiert": faecher_aktualisiert,
        "neue_dokumente": neue_dokumente,
        "entfernte_dokumente": entfernte,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PR #52 — AUFGABE 2B: Wikipedia Sync (Montag 02:00)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 300+ Quiz-Themen für Wikipedia-Sync (Auswahl der wichtigsten)
WIKIPEDIA_SYNC_THEMEN = {
    "Mathematik": [
        "Differentialrechnung", "Integralrechnung", "Vektorraum",
        "Wahrscheinlichkeitstheorie", "Kurvendiskussion", "Logarithmus",
        "Trigonometrie", "Matrizenrechnung", "Stochastik", "Folge_(Mathematik)",
    ],
    "Physik": [
        "Newtonsche_Gesetze", "Thermodynamik", "Elektromagnetismus",
        "Quantenmechanik", "Relativitaetstheorie", "Optik",
        "Kernphysik", "Schwingung", "Welle_(Physik)", "Halbleiter",
    ],
    "Chemie": [
        "Periodensystem", "Organische_Chemie", "Elektrochemie",
        "Saeure-Base-Reaktion", "Redoxreaktion", "Thermodynamik_(Chemie)",
        "Kunststoff", "Katalyse", "Chemisches_Gleichgewicht", "Atombindung",
    ],
    "Biologie": [
        "Genetik", "Evolution", "Oekologie", "Neurobiologie",
        "Fotosynthese", "Zellatmung", "Immunsystem", "DNA",
        "Mitose", "Meiose",
    ],
    "Geschichte": [
        "Weimarer_Republik", "Nationalsozialismus", "Kalter_Krieg",
        "Deutsche_Wiedervereinigung", "Industrielle_Revolution",
        "Erster_Weltkrieg", "Zweiter_Weltkrieg", "Imperialismus",
        "Franzoesische_Revolution", "Roemisches_Reich",
    ],
    "Deutsch": [
        "Sturm_und_Drang", "Romantik", "Expressionismus_(Literatur)",
        "Johann_Wolfgang_von_Goethe", "Friedrich_Schiller",
        "Franz_Kafka", "Episches_Theater", "Erörterung",
        "Stilmittel", "Neue_Sachlichkeit",
    ],
    "Englisch": [
        "Shakespeare", "American_Dream", "British_Empire",
        "Globalisation", "Industrial_Revolution",
    ],
    "Geografie": [
        "Klimawandel", "Plattentektonik", "Globalisierung",
        "Nachhaltige_Entwicklung", "Stadtgeographie",
    ],
    "Wirtschaft": [
        "Soziale_Marktwirtschaft", "Konjunktur", "Inflation",
        "Europaeische_Zentralbank", "Globalisierung",
    ],
    "Informatik": [
        "Algorithmus", "Datenstruktur", "Objektorientierte_Programmierung",
        "Kryptographie", "Datenbank",
    ],
    "Ethik": [
        "Utilitarismus", "Kategorischer_Imperativ", "Menschenwürde",
        "Gerechtigkeit", "Bioethik",
    ],
    "Kunst": [
        "Impressionismus", "Expressionismus", "Bauhaus",
        "Renaissance", "Pop_Art",
    ],
    "Musik": [
        "Sonate", "Sinfonie", "Jazz", "Barock_(Musik)", "Romantik_(Musik)",
    ],
    "Sozialkunde": [
        "Demokratie", "Grundgesetz_(Deutschland)", "Europaeische_Union",
        "Sozialstaat", "Gewaltenteilung",
    ],
    "Latein": [
        "Gaius_Iulius_Caesar", "Marcus_Tullius_Cicero", "Ovid",
        "Vergil", "Seneca",
    ],
    "Franzoesisch": [
        "Frankreich", "Francophonie", "Franzoesische_Revolution",
        "Victor_Hugo", "Albert_Camus",
    ],
}


async def wikipedia_sync_all_topics() -> dict:
    """AUFGABE 2B: Wöchentliche Wikipedia-Sync für 300+ Quiz-Themen.
    Fetcht Wikipedia-Zusammenfassungen und indexiert sie im RAG.

    Returns:
        {"themen_verarbeitet": int, "erfolgreich": int, "fehlgeschlagen": int}
    """
    import aiosqlite

    logger.info("Job: wikipedia_sync_all_topics gestartet")
    db_path = os.getenv("DATABASE_PATH", "app.db")
    themen_total = 0
    erfolgreich = 0
    fehlgeschlagen = 0

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            for fach, themen in WIKIPEDIA_SYNC_THEMEN.items():
                for thema in themen:
                    themen_total += 1
                    try:
                        wiki_url = f"https://de.wikipedia.org/api/rest_v1/page/summary/{thema}"
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            resp = await client.get(
                                wiki_url,
                                headers={"User-Agent": "LumnosBot/1.0 (Bildungs-KI)"},
                            )

                            if resp.status_code != 200:
                                fehlgeschlagen += 1
                                continue

                            data = resp.json()
                            extract = data.get("extract", "")
                            title = data.get("title", thema)
                            url = data.get("content_urls", {}).get(
                                "desktop", {}
                            ).get("page", "")

                            if not extract or len(extract) < 50:
                                fehlgeschlagen += 1
                                continue

                            # In knowledge_updates speichern
                            await db.execute(
                                """INSERT INTO knowledge_updates
                                (fach, thema, quellen_count, inhalt, titel, url,
                                 quelle_typ, created_at)
                                VALUES (?, ?, 1, ?, ?, ?, 'wikipedia',
                                        datetime('now'))""",
                                (fach, title, extract[:3000], title, url or ""),
                            )
                            erfolgreich += 1

                    except Exception as thema_err:
                        logger.debug("Wikipedia Sync %s/%s: %s", fach, thema, thema_err)
                        fehlgeschlagen += 1

            await db.commit()

    except Exception as exc:
        logger.error("wikipedia_sync_all_topics fehlgeschlagen: %s", exc)

    logger.info(
        "Wikipedia Sync: %d Themen, %d erfolgreich, %d fehlgeschlagen",
        themen_total, erfolgreich, fehlgeschlagen,
    )
    return {
        "themen_verarbeitet": themen_total,
        "erfolgreich": erfolgreich,
        "fehlgeschlagen": fehlgeschlagen,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PR #52 — AUFGABE 2C: Lehrplan Updates (1. des Monats 01:00)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BUNDESLAENDER = [
    "Bayern", "NRW", "Baden-Württemberg", "Niedersachsen",
    "Hessen", "Sachsen", "Berlin", "Brandenburg",
    "Schleswig-Holstein", "Hamburg", "Rheinland-Pfalz",
    "Saarland", "Thüringen", "Sachsen-Anhalt",
    "Mecklenburg-Vorpommern", "Bremen",
]

LEHRPLAN_SUCHBEGRIFFE = [
    "Abitur Anforderungen {land} {year}",
    "Lehrplan Gymnasium {land} aktuell",
    "Kerncurriculum {land} Oberstufe",
    "Prüfungsaufgaben Abitur {land}",
]


async def update_lehrplan_content() -> dict:
    """AUFGABE 2C: Monatliche Lehrplan-Updates.
    Prueft via Tavily auf neue Abitur-Anforderungen pro Bundesland.

    Returns:
        {"bundeslaender_geprueft": int, "neue_updates": int}
    """
    import aiosqlite

    logger.info("Job: update_lehrplan_content gestartet")

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if not tavily_key:
        logger.warning("TAVILY_API_KEY nicht gesetzt — Lehrplan Update uebersprungen")
        return {"bundeslaender_geprueft": 0, "neue_updates": 0}

    db_path = os.getenv("DATABASE_PATH", "app.db")
    bundeslaender_geprueft = 0
    neue_updates = 0
    current_year = datetime.now().year

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            import random

            for land in BUNDESLAENDER:
                try:
                    # Zufaelligen Suchbegriff wählen
                    template = random.choice(LEHRPLAN_SUCHBEGRIFFE)
                    query = template.replace("{land}", land).replace(
                        "{year}", str(current_year)
                    )

                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(
                            "https://api.tavily.com/search",
                            json={
                                "api_key": tavily_key,
                                "query": query,
                                "search_depth": "basic",
                                "max_results": 2,
                            },
                        )

                        if resp.status_code != 200:
                            continue

                        results = resp.json().get("results", [])[:2]

                        for r in results:
                            inhalt = r.get("content", "")
                            titel = r.get("title", "")
                            url = r.get("url", "")

                            if len(inhalt) < 80:
                                continue

                            await db.execute(
                                """INSERT INTO lehrplan_updates
                                (bundesland, titel, inhalt, url, jahr, created_at)
                                VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                                (land, titel[:200], inhalt[:2000], url[:500],
                                 current_year),
                            )
                            neue_updates += 1

                    bundeslaender_geprueft += 1

                except Exception as land_err:
                    logger.warning("Lehrplan Update %s fehlgeschlagen: %s", land, land_err)

            await db.commit()

    except Exception as exc:
        logger.error("update_lehrplan_content fehlgeschlagen: %s", exc)

    logger.info(
        "Lehrplan Update: %d Bundeslaender geprueft, %d neue Updates",
        bundeslaender_geprueft, neue_updates,
    )
    return {
        "bundeslaender_geprueft": bundeslaender_geprueft,
        "neue_updates": neue_updates,
    }
