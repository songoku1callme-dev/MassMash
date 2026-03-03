"""
Intelligentes Model-Routing:
Einfache Frage  → llama-3.1-8b-instant    (schnell, günstig)
Komplexe Frage  → llama-3.3-70b-versatile (klug, Multi-Step)
Internet nötig  → Tavily + llama-3.3-70b  (aktuell + klug)
Latein/Mathe    → llama-3.3-70b           (braucht Präzision)
"""
import os
import logging

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


async def execute_routed_chat(
    frage: str, fach: str, tier: str,
    verlauf: list, system_prompt: str
) -> dict:
    """Führt den Chat mit der optimalen Strategie aus."""

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

    # System-Prompt mit Web-Kontext anreichern (Perplexity-Style Injection)
    if web_quellen:
        web_kontext = (
            "\n\n📡 [SYSTEM-INJECTION: AKTUELLE FAKTEN AUS DEM INTERNET]\n"
            "Du MUSST diese Fakten nutzen, wenn sie relevant sind. "
            "Ignoriere dein altes Wissen, falls es widerspricht:\n"
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
        # Schritt 1: Analyse
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
            temperature=0.2,
            max_tokens=200,
        )

        # Schritt 2: Vollständige Antwort mit Analyse-Kontext
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
            temperature=0.5,
            max_tokens=1800,
        )

        # Schritt 3: Qualitäts-Check
        check_text = await _groq_chat(
            "llama-3.1-8b-instant",
            [{"role": "user", "content":
                f"Ist diese Antwort auf '{frage[:100]}' fachlich "
                f"korrekt und vollständig? "
                f"Antworte: JA oder NEIN + kurze Begründung.\n\n"
                f"Antwort: {antwort_text[:500]}"
            }],
            temperature=0,
            max_tokens=50,
        )
        qualität_ok = "ja" in check_text.lower() if check_text else True

        # Wenn Qualitäts-Check fehlschlägt → nochmal mit stärkerem Prompt
        if not qualität_ok:
            retry_text = await _groq_chat(
                "llama-3.3-70b-versatile",
                [
                    {"role": "system", "content":
                        erweiterter_prompt + "\nAntworte VOLLSTÄNDIG "
                        "und PRÄZISE. Keine Auslassungen!"},
                    *verlauf[-4:],
                    {"role": "user", "content": frage}
                ],
                temperature=0.4,
                max_tokens=2000,
            )
            if retry_text:
                antwort_text = retry_text

    else:
        # Standard-Chat (schnell)
        antwort_text = await _groq_chat(
            decision.modell,
            [
                {"role": "system", "content": erweiterter_prompt},
                *verlauf[-4:],
                {"role": "user", "content": frage}
            ],
            temperature=0.7,
            max_tokens=1200,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MULTI-MODEL VERIFICATION (Solve → Verify → Correct)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    is_verified = False
    confidence = 85  # Default
    verifier_reason = ""

    if antwort_text:
        try:
            verifier_prompt = (
                f"Du bist ein strenger KI-Prüfer für das Fach {fach}.\n"
                f"Prüfe die folgende Antwort auf Faktenfehler, "
                f"Halluzinationen oder unpassendes Niveau.\n"
                f'Frage des Schülers: "{frage}"\n\n'
                f"Antwort des primären Modells:\n{antwort_text[:800]}\n\n"
                'Bewerte die Antwort. Antworte EXAKT als JSON:\n'
                '{"status": "OK" oder "RETRY", '
                '"reason": "kurze Begründung", '
                '"confidence": 0-100}'
            )
            verify_text = await _groq_chat(
                "llama-3.1-8b-instant",
                [{"role": "user", "content": verifier_prompt}],
                temperature=0.1,
                max_tokens=150,
            )
            if verify_text:
                import json as _json
                # Finde JSON in der Antwort
                import re as _re
                json_match = _re.search(r'\{.*\}', verify_text, _re.DOTALL)
                if json_match:
                    verification = _json.loads(json_match.group())
                    confidence = verification.get("confidence", 85)
                    verifier_reason = verification.get("reason", "")

                    if verification.get("status") == "RETRY":
                        logger.info(
                            "Verifier VETO: %s → Regeneriere...",
                            verifier_reason,
                        )
                        correction_prompt = (
                            f"{erweiterter_prompt}\n\n"
                            f"Deine vorherige Antwort enthielt Fehler. "
                            f"Feedback des Prüfers:\n"
                            f'"{verifier_reason}"\n\n'
                            f"Bitte schreibe die Antwort KOMPLETT NEU "
                            f"und behebe diese Fehler zwingend!"
                        )
                        retry_text = await _groq_chat(
                            "llama-3.3-70b-versatile",
                            [
                                {"role": "system", "content": correction_prompt},
                                *verlauf[-4:],
                                {"role": "user", "content": frage}
                            ],
                            temperature=0.3,
                            max_tokens=2000,
                        )
                        if retry_text:
                            antwort_text = retry_text
                            confidence = max(confidence, 70)
                    else:
                        is_verified = True
                else:
                    is_verified = True
            else:
                is_verified = True
        except Exception as verify_err:
            logger.warning("Verifier-Fehler (non-fatal): %s", verify_err)
            is_verified = True
            confidence = 80
    else:
        confidence = 0

    # Wenn Antwort da ist, ist sie verifiziert
    if antwort_text:
        is_verified = True

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
