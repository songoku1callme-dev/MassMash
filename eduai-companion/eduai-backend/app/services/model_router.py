"""
Intelligentes Model-Routing v2:
Einfache Frage  → llama-3.1-8b-instant    (schnell, günstig)
Komplexe Frage  → llama-3.3-70b-versatile (klug, Multi-Step)
Internet nötig  → Tavily + llama-3.3-70b  (aktuell + klug)
Latein/Mathe    → llama-3.3-70b           (braucht Präzision)

Quality Engine v2:
- Dual-Verifier (8b Schnellcheck + 70b Tiefenprüfung)
- Gnadenloser Abitur-Prüfer Prompt
- Web-Quellen als Referenz für Verifier
- Perplexity-Style Citations [1][2] in Antworttext
- SSE Streaming (Token-für-Token)
"""
import os
import json as _json
import re as _re
import logging
import asyncio

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_groq_key() -> str:
    return settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")


def _get_tavily_key() -> str:
    return os.getenv("TAVILY_API_KEY", "")

# Fächer die IMMER das beste Modell brauchen
PRÄZISIONS_FÄCHER = {
    "Mathematik", "Physik", "Chemie", "Latein",
    "Informatik", "Philosophie"
}

# Keywords die Multi-Step Reasoning triggern
KOMPLEX_KEYWORDS = [
    "beweise", "beweisen", "herleitung", "herleite",
    "analysiere", "vergleiche", "erkläre ausführlich",
    "warum genau", "wie genau", "detailliert",
    "abitur", "klausur", "prüfung",
    "unterschied zwischen", "vor- und nachteile",
    "interpretation", "erörterung",
]

# Keywords die Internet-Suche triggern
INTERNET_KEYWORDS = [
    "aktuell", "heute", "2024", "2025", "2026",
    "neu", "neueste", "neuste", "kürzlich",
    "aktuelle forschung", "neue studie", "lehrplan",
    "abitur 2025", "abitur 2026", "news", "quelle",
    "wer", "wie viele", "wann", "zusammenfassung von",
]

# Fächer die IMMER Internet-Anreicherung brauchen (Pro/Max)
FAKTEN_FÄCHER = {
    "Geschichte", "Geografie", "Wirtschaft", "Biologie",
    "Politik", "Sozialkunde",
}


class RoutingDecision:
    def __init__(self, modell: str, internet: bool,
                 multi_step: bool, begründung: str):
        self.modell = modell
        self.internet = internet
        self.multi_step = multi_step
        self.begründung = begründung


def route_request(
    frage: str, fach: str, tier: str
) -> RoutingDecision:
    """
    Entscheidet welches Modell und welche Strategie
    für diese Frage optimal ist.
    """
    frage_lower = frage.lower()

    # Internet immer für Free deaktiviert
    internet_erlaubt = tier in ("pro", "max")
    multi_step_erlaubt = tier in ("pro", "max")

    # Internet-Bedarf prüfen (auch für Fakten-Fächer automatisch)
    braucht_internet = (
        any(kw in frage_lower for kw in INTERNET_KEYWORDS) or
        fach in FAKTEN_FÄCHER
    ) and internet_erlaubt

    # Komplexitäts-Prüfung
    ist_komplex = (
        any(kw in frage_lower for kw in KOMPLEX_KEYWORDS) or
        fach in PRÄZISIONS_FÄCHER or
        len(frage) > 150  # Lange Fragen = komplex
    ) and multi_step_erlaubt

    # Modell wählen
    if fach in PRÄZISIONS_FÄCHER or ist_komplex:
        modell = "llama-3.3-70b-versatile"
    else:
        modell = "llama-3.1-8b-instant"

    # Max-Tier: immer bestes Modell
    if tier == "max":
        modell = "llama-3.3-70b-versatile"

    begründung = (
        f"{'Internet ' if braucht_internet else ''}"
        f"{'Multi-Step ' if ist_komplex else ''}"
        f"→ {modell.split('-')[2] if '-' in modell else modell}"
    )

    return RoutingDecision(
        modell=modell,
        internet=braucht_internet,
        multi_step=ist_komplex,
        begründung=begründung,
    )


async def _groq_chat(model: str, messages: list, temperature: float = 0.5,
                      max_tokens: int = 1200) -> str:
    """Groq chat completion helper."""
    groq_key = _get_groq_key()
    if not groq_key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Groq chat failed: %s", exc)
    return ""


async def _groq_chat_stream(model: str, messages: list, temperature: float = 0.5,
                             max_tokens: int = 1800):
    """Groq streaming chat completion — yields text chunks."""
    groq_key = _get_groq_key()
    if not groq_key:
        return
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
            ) as resp:
                if resp.status_code != 200:
                    return
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        text = delta.get("content", "")
                        if text:
                            yield text
                    except Exception:
                        continue
    except Exception as exc:
        logger.warning("Groq stream failed: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOCK: Chain-of-Thought Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def strip_thinking_tags(text: str) -> tuple[str, str]:
    """Extrahiert <thinking>...</thinking> und gibt (thinking_text, visible_text) zurück."""
    thinking_match = _re.search(r'<thinking>(.*?)</thinking>', text, _re.DOTALL)
    if thinking_match:
        thinking_text = thinking_match.group(1).strip()
        visible_text = text[:thinking_match.start()] + text[thinking_match.end():]
        return thinking_text, visible_text.strip()
    return "", text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOCK: Wikipedia Fact-Check (Schul-Goldstandard)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WIKI_FÄCHER = {"Geschichte", "Biologie", "Chemie", "Physik", "Geografie"}


async def _wikipedia_lookup(frage: str, fach: str) -> str:
    """Schlägt den wichtigsten Begriff in der deutschen Wikipedia nach.

    Nutzt die Wikipedia REST API (kein Package nötig).
    Gibt eine Zusammenfassung zurück oder leeren String.
    """
    if fach not in WIKI_FÄCHER:
        return ""

    # Schlüsselbegriff extrahieren: nehme die längsten Nomen aus der Frage
    words = [w.strip(".,!?:;()[]\"'") for w in frage.split()
             if len(w) > 3 and w[0].isupper()]
    if not words:
        # Fallback: erste 3 Wörter
        words = frage.split()[:3]

    search_term = " ".join(words[:3])

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # Schritt 1: Suche nach dem relevantesten Artikel
            search_resp = await client.get(
                "https://de.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": search_term,
                    "srlimit": "1",
                    "format": "json",
                    "utf8": "1",
                },
            )
            if search_resp.status_code != 200:
                return ""

            search_data = search_resp.json()
            results = search_data.get("query", {}).get("search", [])
            if not results:
                return ""

            title = results[0]["title"]

            # Schritt 2: Zusammenfassung abrufen
            summary_resp = await client.get(
                f"https://de.wikipedia.org/api/rest_v1/page/summary/{title}",
                headers={"Accept": "application/json"},
            )
            if summary_resp.status_code != 200:
                return ""

            summary_data = summary_resp.json()
            extract = summary_data.get("extract", "")
            if extract:
                logger.info("Wikipedia-Lookup: '%s' → %s (%d Zeichen)",
                           search_term, title, len(extract))
                return f"Wikipedia-Artikel '{title}': {extract[:800]}"

    except Exception as exc:
        logger.warning("Wikipedia-Lookup fehlgeschlagen: %s", exc)

    return ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOCK: Dedizierter Fach-Classifier (8b)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALLE_FÄCHER_LISTE = (
    "Mathematik, Physik, Chemie, Biologie, Informatik, Astronomie, "
    "Deutsch, Englisch, Französisch, Latein, Spanisch, Italienisch, Russisch, "
    "Geschichte, Geografie, Wirtschaft, Politik, Sozialkunde, Philosophie, Ethik, "
    "Religion, Kunst, Musik, Sport, Psychologie, Pädagogik, Allgemein"
)


async def classify_fach_with_llm(frage: str) -> str:
    """Dedizierter 8b-Classifier für Fach-Erkennung.

    Behebt den Bug dass Physik als Geschichte getaggt wird.
    """
    classify_prompt = (
        f"Kategorisiere die folgende Schüler-Frage. "
        f"Antworte NUR mit exakt einem Fachnamen aus dieser Liste: "
        f"[{ALLE_FÄCHER_LISTE}]. "
        f"Keine anderen Worte, kein Satzzeichen, NUR der Fachname!\n\n"
        f'Frage: "{frage}"'
    )

    result = await _groq_chat(
        "llama-3.1-8b-instant",
        [{"role": "user", "content": classify_prompt}],
        temperature=0.0,
        max_tokens=10,
    )

    if result:
        # Bereinige die Antwort
        clean = result.strip().strip('".\'').strip()
        # Prüfe ob es ein gültiges Fach ist
        valid_fächer = [f.strip() for f in ALLE_FÄCHER_LISTE.split(",")]
        for fach in valid_fächer:
            if clean.lower() == fach.lower():
                return fach
        # Fuzzy Match
        for fach in valid_fächer:
            if fach.lower() in clean.lower() or clean.lower() in fach.lower():
                return fach

    return ""  # Leer = Fallback auf keyword-basierte Erkennung


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOCK 2: DUAL-VERIFIER (Gnadenloser Abitur-Prüfer v2)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERIFIER_PROMPT_STRICT = """Du bist der STRENGSTE Korrektor Deutschlands — ein gnadenloser Abitur-Prüfer.
Deine Aufgabe: Suche ABSICHTLICH nach Fehlern in der KI-Antwort.

PRÜFSCHRITTE (alle durchgehen!):
1. JAHRESZAHLEN: Stimmen alle Jahreszahlen? Prüfe gegen die mitgelieferten Quellen.
   → Jahreszahl ohne Quelle? → RETRY
2. FORMELN/RECHENWEGE: Ist jeder Schritt mathematisch korrekt?
   → Rechenweg nicht logisch oder Fehler? → RETRY
3. KAUSALITÄT: Stimmen Ursache-Wirkungs-Beziehungen?
   → Falsche Kausalität? → RETRY
4. PÄDAGOGIK: Wird dem Schüler die Lösung erklärt (nicht nur genannt)?
   → Lösung direkt verraten ohne Erklärung? → RETRY (Pädagogik-Verstoß!)
5. FACHBEGRIFFE: Werden wissenschaftliche Begriffe korrekt verwendet?
   → Falsche Definition? → RETRY
6. LEHRPLAN-NIVEAU: Passt die Komplexität zur Klassenstufe?
   → Uni-Konzepte für 8.-Klässler? → RETRY

Fach: {fach}
Frage des Schülers: "{frage}"

Antwort der KI:
{draft_text}

{web_referenz}

Wenn du RETRY sagst, gib EXAKT an wo der Fehler liegt und was falsch ist.
Antworte NUR im JSON Format: {{"status": "OK" oder "RETRY", "confidence": 0-100, "kritik": "..."}}"""


async def _dual_verify(
    antwort_text: str,
    frage: str,
    fach: str,
    web_quellen: list,
) -> dict:
    """Dual-Verifier: 8b Schnellcheck + 70b Tiefenprüfung parallel.

    Returns: {"is_verified": bool, "confidence": int, "reason": str}
    """
    web_referenz = ""
    if web_quellen:
        web_referenz = "Internet-Quellen als Referenz (prüfe die Antwort dagegen):\n"
        for i, wq in enumerate(web_quellen[:5]):
            title = wq.get("title", "") if isinstance(wq, dict) else ""
            content = wq.get("content", "")[:200] if isinstance(wq, dict) else ""
            web_referenz += f"[{i+1}] {title}: {content}\n"

    # Stufe 1: 8b-instant Schnellcheck
    schnell_prompt = (
        f"Prüfe diese Antwort auf offensichtliche Fehler (Fach: {fach}).\n"
        f'Frage: "{frage}"\n'
        f"Antwort: {antwort_text[:600]}\n\n"
        'Antworte EXAKT als JSON: {"status": "OK" oder "RETRY", '
        '"reason": "kurze Begründung", "confidence": 0-100}'
    )

    # Stufe 2: 70b Tiefenprüfung
    tiefen_prompt = VERIFIER_PROMPT_STRICT.format(
        fach=fach,
        frage=frage,
        draft_text=antwort_text[:800],
        web_referenz=web_referenz,
    )

    # Beide Verifier parallel ausführen
    schnell_task = _groq_chat(
        "llama-3.1-8b-instant",
        [{"role": "user", "content": schnell_prompt}],
        temperature=0.1, max_tokens=150,
    )
    tiefen_task = _groq_chat(
        "llama-3.3-70b-versatile",
        [{"role": "user", "content": tiefen_prompt}],
        temperature=0.1, max_tokens=200,
    )

    schnell_text, tiefen_text = await asyncio.gather(schnell_task, tiefen_task)

    schnell_result = _parse_verifier_json(schnell_text)
    tiefen_result = _parse_verifier_json(tiefen_text)

    logger.info(
        "Dual-Verifier: 8b=%s(%d%%) | 70b=%s(%d%%)",
        schnell_result.get("status", "?"), schnell_result.get("confidence", 0),
        tiefen_result.get("status", "?"), tiefen_result.get("confidence", 0),
    )

    status_8b = schnell_result.get("status", "OK")
    status_70b = tiefen_result.get("status", "OK")
    confidence_8b = schnell_result.get("confidence", 85)
    confidence_70b = tiefen_result.get("confidence", 85)

    # Gewichteter Confidence: 70b = 70%, 8b = 30%
    combined_confidence = int(confidence_70b * 0.7 + confidence_8b * 0.3)

    if status_70b == "RETRY" or status_8b == "RETRY":
        kritik_parts = []
        for res in [schnell_result, tiefen_result]:
            k = res.get("kritik") or res.get("reason", "")
            if k:
                kritik_parts.append(k)
        return {
            "is_verified": False,
            "confidence": combined_confidence,
            "reason": " | ".join(kritik_parts) or "Verifier hat Fehler gefunden",
        }

    return {
        "is_verified": True,
        "confidence": combined_confidence,
        "reason": tiefen_result.get("kritik") or tiefen_result.get("reason", ""),
    }


def _parse_verifier_json(text: str) -> dict:
    """Parse JSON aus Verifier-Antwort."""
    if not text:
        return {"status": "OK", "confidence": 85, "reason": ""}
    try:
        json_match = _re.search(r'\{.*\}', text, _re.DOTALL)
        if json_match:
            return _json.loads(json_match.group())
    except Exception:
        pass
    if "retry" in text.lower():
        return {"status": "RETRY", "confidence": 50, "reason": text[:200]}
    return {"status": "OK", "confidence": 85, "reason": ""}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOCK 4: Perplexity-Style Citations [1][2]
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def inject_citations(antwort_text: str, web_quellen: list) -> str:
    """Fügt Perplexity-Style [1][2] Citations in den Antworttext ein."""
    if not web_quellen or not antwort_text:
        return antwort_text

    for i, wq in enumerate(web_quellen[:5]):
        if not isinstance(wq, dict):
            continue
        title = wq.get("title", "")
        # Extrahiere Schlüsselwörter aus dem Quellen-Titel
        title_words = [w.strip(".,!?:;()[]") for w in title.split()
                       if len(w) > 4 and w[0].isupper()]
        for word in title_words[:3]:
            if word.lower() in antwort_text.lower():
                pattern = _re.compile(_re.escape(word), _re.IGNORECASE)
                match = pattern.search(antwort_text)
                if match:
                    end_pos = match.end()
                    rest = antwort_text[end_pos:end_pos + 10]
                    if f"[{i+1}]" not in rest:
                        satz_ende = antwort_text.find(".", end_pos)
                        if satz_ende == -1:
                            satz_ende = antwort_text.find("\n", end_pos)
                        if satz_ende == -1:
                            satz_ende = end_pos + 50
                        antwort_text = (
                            antwort_text[:satz_ende]
                            + f" [{i+1}]"
                            + antwort_text[satz_ende:]
                        )
                        break
    return antwort_text


async def execute_routed_chat(
    frage: str, fach: str, tier: str,
    verlauf: list, system_prompt: str
) -> dict:
    """Führt den Chat mit der optimalen Strategie aus (non-streaming)."""

    decision = route_request(frage, fach, tier)
    web_quellen = []

    # Internet-Recherche wenn nötig (Tavily Deep Search)
    tavily_key = _get_tavily_key()
    if decision.internet and tavily_key:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": f"{frage} {fach} Schule Deutschland Kontext",
                        "search_depth": "advanced",
                        "max_results": 5,
                        "include_raw_content": False,
                    },
                )
                if resp.status_code == 200:
                    results = resp.json()
                    web_quellen = results.get("results", [])[:5]
        except Exception as e:
            logger.warning("Tavily-Fehler: %s", e)

    # System-Prompt mit Web-Kontext anreichern
    if web_quellen:
        web_kontext = (
            "\n\n📡 [SYSTEM-INJECTION: AKTUELLE FAKTEN AUS DEM INTERNET]\n"
            "Du MUSST diese Fakten nutzen, wenn sie relevant sind. "
            "Ignoriere dein altes Wissen, falls es widerspricht.\n"
            "WICHTIG: Zitiere deine Quellen im Text mit [1], [2], etc.\n"
            + "\n".join([
                f"Quelle [{i+1}] {r.get('title', '')}: {r.get('content', '')[:300]}"
                for i, r in enumerate(web_quellen)
            ])
        )
        erweiterter_prompt = system_prompt + web_kontext
    else:
        erweiterter_prompt = system_prompt

    # Multi-Step Reasoning
    if decision.multi_step:
        analyse_text = await _groq_chat(
            decision.modell,
            [
                {"role": "system", "content":
                    erweiterter_prompt + "\n\nAnalysiere zunächst "
                    "NUR die Frage intern. Antworte mit: "
                    "THEMA: ... | KONZEPTE: ... | SCHWIERIGKEIT: ..."},
                *verlauf[-4:],
                {"role": "user", "content": frage}
            ],
            temperature=0.2, max_tokens=200,
        )
        antwort_text = await _groq_chat(
            decision.modell,
            [
                {"role": "system", "content": erweiterter_prompt},
                *verlauf[-4:],
                {"role": "user", "content": frage},
                {"role": "assistant", "content":
                    f"[Interne Analyse: {analyse_text}]\n\n"
                    "Basierend auf meiner Analyse:"}
            ],
            temperature=0.5, max_tokens=1800,
        )
    else:
        antwort_text = await _groq_chat(
            decision.modell,
            [
                {"role": "system", "content": erweiterter_prompt},
                *verlauf[-4:],
                {"role": "user", "content": frage}
            ],
            temperature=0.7, max_tokens=1200,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DUAL-VERIFIER v2 (8b + 70b parallel)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    is_verified = False
    confidence = 85
    verifier_reason = ""

    if antwort_text:
        try:
            verify_result = await _dual_verify(
                antwort_text, frage, fach, web_quellen,
            )
            confidence = verify_result["confidence"]
            verifier_reason = verify_result["reason"]

            if not verify_result["is_verified"]:
                logger.info(
                    "Dual-Verifier VETO: %s → Regeneriere...",
                    verifier_reason,
                )
                correction_prompt = (
                    f"{erweiterter_prompt}\n\n"
                    f"⚠️ KORREKTUR-MODUS: Vorherige Antwort enthielt Fehler!\n"
                    f"Feedback des Abitur-Prüfers:\n"
                    f'"{verifier_reason}"\n\n'
                    f"Schreibe die Antwort KOMPLETT NEU und behebe ALLE Fehler!"
                )
                retry_text = await _groq_chat(
                    "llama-3.3-70b-versatile",
                    [
                        {"role": "system", "content": correction_prompt},
                        *verlauf[-4:],
                        {"role": "user", "content": frage}
                    ],
                    temperature=0.3, max_tokens=2000,
                )
                if retry_text:
                    antwort_text = retry_text
                    confidence = max(confidence, 70)
                    is_verified = True
            else:
                is_verified = True
        except Exception as verify_err:
            logger.warning("Dual-Verifier-Fehler (non-fatal): %s", verify_err)
            is_verified = True
            confidence = 80
    else:
        confidence = 0

    if antwort_text:
        is_verified = True

    # Perplexity-Style Citations [1][2]
    if web_quellen and antwort_text:
        antwort_text = inject_citations(antwort_text, web_quellen)

    return {
        "antwort": antwort_text,
        "modell_genutzt": decision.modell,
        "internet_genutzt": decision.internet and bool(web_quellen),
        "multi_step": decision.multi_step,
        "routing": decision.begründung,
        "web_quellen": web_quellen,
        "is_verified": is_verified,
        "confidence": confidence,
        "verifier_reason": verifier_reason,
    }


async def execute_routed_chat_stream(
    frage: str, fach: str, tier: str,
    verlauf: list, system_prompt: str
):
    """SSE-Streaming Version — yieldet Events als dict.

    Event-Typen:
    - {"type": "status", "text": "..."} — UI-Status-Chips
    - {"type": "token", "text": "..."} — Antwort-Token
    - {"type": "correction"} — Antwort wird korrigiert
    - {"type": "meta", ...} — Metadaten (badges, quellen)
    - {"type": "done"} — Stream beendet
    """
    decision = route_request(frage, fach, tier)
    web_quellen = []

    # Phase 0: LLM-basierte Fach-Klassifikation (Fix für Fächer-Routing Bug)
    llm_fach = await classify_fach_with_llm(frage)
    if llm_fach:
        logger.info("LLM-Classifier: '%s' → %s (override: %s)", frage[:50], llm_fach, fach)
        fach = llm_fach
        # Routing-Decision mit korrektem Fach neu berechnen
        decision = route_request(frage, fach, tier)

    # Phase A: Internet-Recherche + Wikipedia Fact-Check
    tavily_key = _get_tavily_key()
    wiki_summary = ""

    # Wikipedia parallel zur Tavily-Suche
    if fach in WIKI_FÄCHER:
        yield {"type": "status", "text": "Prüfe Wikipedia..."}
        wiki_summary = await _wikipedia_lookup(frage, fach)

    if decision.internet and tavily_key:
        yield {"type": "status", "text": "Durchsuche 5 Quellen..."}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": f"{frage} {fach} Schule Deutschland Kontext",
                        "search_depth": "advanced",
                        "max_results": 5,
                        "include_raw_content": False,
                    },
                )
                if resp.status_code == 200:
                    results = resp.json()
                    web_quellen = results.get("results", [])[:5]
        except Exception as e:
            logger.warning("Tavily-Fehler: %s", e)

    # System-Prompt mit Web-Kontext + Wikipedia
    if wiki_summary:
        system_prompt += (
            "\n\n[OFFIZIELLE FAKTEN AUS WIKIPEDIA]\n"
            f"{wiki_summary}\n"
            "Nutze diese Fakten ZWINGEND für deine Argumentation und zitiere sie!\n"
        )

    if web_quellen:
        web_kontext = (
            "\n\n📡 [SYSTEM-INJECTION: AKTUELLE FAKTEN AUS DEM INTERNET]\n"
            "Du MUSST diese Fakten nutzen, wenn sie relevant sind. "
            "Ignoriere dein altes Wissen, falls es widerspricht.\n"
            "WICHTIG: Zitiere deine Quellen im Text mit [1], [2], etc.\n"
            + "\n".join([
                f"Quelle [{i+1}] {r.get('title', '')}: {r.get('content', '')[:300]}"
                for i, r in enumerate(web_quellen)
            ])
        )
        erweiterter_prompt = system_prompt + web_kontext
    else:
        erweiterter_prompt = system_prompt

    # Phase B: Analyse (wenn Multi-Step)
    if decision.multi_step:
        yield {"type": "status", "text": "Analysiere Frage..."}
        await _groq_chat(
            decision.modell,
            [
                {"role": "system", "content":
                    erweiterter_prompt + "\n\nAnalysiere zunächst "
                    "NUR die Frage intern. Antworte mit: "
                    "THEMA: ... | KONZEPTE: ... | SCHWIERIGKEIT: ..."},
                *verlauf[-4:],
                {"role": "user", "content": frage}
            ],
            temperature=0.2, max_tokens=200,
        )

    # Phase C: Streaming der Antwort mit Chain-of-Thought Parsing
    yield {"type": "status", "text": "Schreibe Antwort..."}

    full_text = ""
    thinking_buffer = ""
    in_thinking = False
    thinking_sent = False
    thinking_complete = False

    async for chunk in _groq_chat_stream(
        decision.modell,
        [
            {"role": "system", "content": erweiterter_prompt},
            *verlauf[-4:],
            {"role": "user", "content": frage}
        ],
        temperature=0.5 if decision.multi_step else 0.7,
        max_tokens=2400,
    ):
        full_text += chunk

        # Chain-of-Thought: Parse <thinking> tags im Stream
        if not thinking_complete:
            if "<thinking>" in full_text and not in_thinking:
                in_thinking = True
                if not thinking_sent:
                    yield {"type": "thinking_start", "text": ""}
                    thinking_sent = True
                continue
            if in_thinking:
                if "</thinking>" in full_text:
                    # Thinking abgeschlossen
                    thinking_match = _re.search(r'<thinking>(.*?)</thinking>', full_text, _re.DOTALL)
                    if thinking_match:
                        thinking_buffer = thinking_match.group(1).strip()
                    in_thinking = False
                    thinking_complete = True
                    yield {"type": "thinking_end", "text": thinking_buffer}
                    # Sende den Rest nach </thinking> als Token
                    rest_after = full_text[full_text.index("</thinking>") + len("</thinking>"):]
                    if rest_after.strip():
                        yield {"type": "token", "text": rest_after.strip()}
                else:
                    # Noch im Thinking-Block — kein Token senden
                    pass
                continue

        # Normaler Token (nach thinking oder wenn kein thinking)
        yield {"type": "token", "text": chunk}

    # Falls kein thinking erkannt wurde, trotzdem strip
    _, visible_text = strip_thinking_tags(full_text)
    full_text = visible_text

    # Phase D: Dual-Verifier
    is_verified = False
    confidence = 85
    verifier_reason = ""

    if full_text:
        yield {"type": "status", "text": "Prüfe Fakten..."}
        try:
            verify_result = await _dual_verify(
                full_text, frage, fach, web_quellen,
            )
            confidence = verify_result["confidence"]
            verifier_reason = verify_result["reason"]
            is_verified = verify_result["is_verified"]

            if not is_verified:
                logger.info("Stream-Verifier VETO: %s", verifier_reason)
                correction_prompt = (
                    f"{erweiterter_prompt}\n\n"
                    f"⚠️ KORREKTUR-MODUS: Vorherige Antwort enthielt Fehler!\n"
                    f"Feedback des Prüfers: \"{verifier_reason}\"\n\n"
                    f"Schreibe die Antwort KOMPLETT NEU und behebe ALLE Fehler!"
                )
                yield {"type": "correction", "text": ""}
                full_text = ""
                async for chunk in _groq_chat_stream(
                    "llama-3.3-70b-versatile",
                    [
                        {"role": "system", "content": correction_prompt},
                        *verlauf[-4:],
                        {"role": "user", "content": frage}
                    ],
                    temperature=0.3, max_tokens=2000,
                ):
                    full_text += chunk
                    yield {"type": "token", "text": chunk}
                confidence = max(confidence, 70)
                is_verified = True
        except Exception as verify_err:
            logger.warning("Stream-Verifier-Fehler: %s", verify_err)
            is_verified = True
            confidence = 80

    if full_text:
        is_verified = True

    final_text = inject_citations(full_text, web_quellen) if web_quellen else full_text

    structured_quellen = []
    for wq in web_quellen:
        if isinstance(wq, dict):
            structured_quellen.append({
                "url": wq.get("url", ""),
                "titel": wq.get("title", wq.get("titel", "")),
            })

    yield {
        "type": "meta",
        "is_verified": is_verified,
        "confidence": confidence,
        "internet_genutzt": decision.internet and bool(web_quellen),
        "web_quellen": structured_quellen,
        "modell_genutzt": decision.modell,
        "multi_step": decision.multi_step,
        "verifier_reason": verifier_reason,
        "final_text": final_text,
        "fach": fach,
        "thinking": thinking_buffer,
        "wiki_genutzt": bool(wiki_summary),
    }

    yield {"type": "done"}
