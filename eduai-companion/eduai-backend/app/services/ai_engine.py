"""AI Engine - Core intelligence for Lumnos Companion.

Handles subject detection, adaptive prompting, proficiency-aware responses,
quiz generation, learning path recommendations, and token budget management.
"""
import json
import logging
import re
import random
import threading
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOKEN BUDGET MANAGEMENT (Groq Free Tier: 100K TPD)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_token_lock = threading.Lock()

token_usage: dict = {
    "used": 0,
    "limit": 95000,  # 95K of 100K — 5K safety buffer
    "reset_at": None,  # UTC midnight
    "last_reset_date": None,
}


def _check_daily_reset() -> None:
    """Reset token counter at midnight UTC."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if token_usage["last_reset_date"] != today:
        token_usage["used"] = 0
        token_usage["last_reset_date"] = today
        # Next reset at midnight UTC
        token_usage["reset_at"] = f"{today}T00:00:00Z"
        logger.info("[TOKEN] Daily reset: %s → 0/%d", today, token_usage["limit"])


def track_tokens(prompt_tokens: int, completion_tokens: int) -> None:
    """Track token usage (thread-safe). Call after each Groq API response."""
    with _token_lock:
        _check_daily_reset()
        total = prompt_tokens + completion_tokens
        token_usage["used"] += total

        pct = round(token_usage["used"] / token_usage["limit"] * 100)
        if pct >= 90:
            logger.warning(
                "[TOKEN] KRITISCH: %d/%d (%d%%) — Token-Budget fast erschöpft!",
                token_usage["used"], token_usage["limit"], pct,
            )
        elif pct >= 80:
            logger.warning(
                "[TOKEN] Warnung: %d/%d (%d%%) — über 80%% verbraucht",
                token_usage["used"], token_usage["limit"], pct,
            )


def get_token_usage() -> dict:
    """Return current token usage stats."""
    with _token_lock:
        _check_daily_reset()
        used = token_usage["used"]
        limit = token_usage["limit"]
        return {
            "used": used,
            "limit": limit,
            "percent": round(used / limit * 100) if limit > 0 else 0,
            "remaining": limit - used,
            "reset_at": token_usage["reset_at"],
            "budget_ok": used < limit,
        }


# Simple keywords that indicate a short, easy question
_SIMPLE_PATTERNS = [
    "was ist", "wann", "wo ist", "wer ist", "wer war",
    "wie viel", "hauptstadt", "wie heißt", "wie heisst",
    "definiere", "nenne", "was bedeutet",
]

# Complex keywords that need the powerful 70b model
_COMPLEX_PATTERNS = [
    "erkläre", "erklare", "beschreibe", "analysiere", "vergleiche",
    "beweise", "leite her", "interpretiere", "erörtere", "diskutiere",
    "warum", "zusammenfassung", "aufsatz", "essay", "abitur",
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUFGABE 2: Antwort-Längen strikt begrenzen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_max_tokens(frage: str) -> int:
    """Bestimme max_tokens je nach Fragetyp.

    Kurze Faktenfragen → 150 Tokens
    Standard-Fragen → 350 Tokens
    Komplexe Erklärungen → 600 Tokens
    """
    frage_lower = frage.lower().strip()

    # Kurze Faktenfragen → kurze Antwort
    kurze_fragen = [
        "was ist", "wann", "wo ist", "wer ist",
        "wie viel", "hauptstadt", "wie heißt",
        "was bedeutet", "definition",
    ]
    is_kurz = (
        len(frage) < 40
        and any(p in frage_lower for p in kurze_fragen)
    )

    # Komplexe Erklärungen → mehr Tokens
    komplex = [
        "erkläre", "erklaere", "beschreibe",
        "wie funktioniert", "was ist der unterschied",
        "vergleiche", "analysiere",
    ]
    is_komplex = any(p in frage_lower for p in komplex)

    if is_kurz:
        return 150   # Max 150 Tokens für Faktenfragen
    elif is_komplex:
        return 600   # Mehr für Erklärungen
    else:
        return 350   # Standard


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIX 4: Sinnlose/leere Fragen abfangen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SINNLOSE_ANTWORT = (
    "Bitte stelle eine konkrete Frage — "
    "ich helfe dir gerne! 😊 "
    "Beispiel: *'Erkläre Fotosynthese'* oder "
    "*'Löse: 3x + 5 = 20'*"
)


def ist_sinnlose_frage(frage: str) -> bool:
    """Erkennt leere oder sinnlose Eingaben die keine echte Frage sind."""
    bereinigt = frage.strip()
    return (
        len(bereinigt) <= 2
        or bereinigt in ["?", "!", ".", "...", " ", "??", "!!", "..", "..."]
        or all(c in "?!. \t\n" for c in bereinigt)
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANTWORT-TYP-ERKENNUNG: Automatisch den Schüler-Intent erkennen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def erkenne_antwort_typ(frage: str) -> str:
    """
    Erkennt was der Schüler wirklich will.
    Returns: 'kurz' | 'schritt_fuer_schritt' | 'aufgabe_loesen' | 'standard'
    """
    frage_lower = frage.lower()

    # Schritt-für-Schritt gewünscht
    schritt_keywords = [
        "schritt für schritt", "schritt-für-schritt",
        "erkläre wie", "wie funktioniert",
        "zeig mir wie", "wie löse ich",
        "rechenweg", "weg dazu", "erklär mir",
        "erklärung", "erklären",
    ]

    # Aufgabe lösen
    aufgabe_keywords = [
        "löse", "berechne", "bestimme",
        "vereinfache", "leite ab", "deriviere",
        "integriere", "beweise", "zeige dass",
    ]

    # Kurze Antwort gewünscht
    kurz_keywords = [
        "kurz", "schnell", "einfach nur",
        "nur das ergebnis", "was ist",
        "wann", "wer ist", "hauptstadt",
        "definition von", "bedeutet",
    ]

    if any(k in frage_lower for k in schritt_keywords):
        return "schritt_fuer_schritt"
    elif any(k in frage_lower for k in aufgabe_keywords):
        return "aufgabe_loesen"
    elif any(k in frage_lower for k in kurz_keywords):
        return "kurz"
    elif len(frage.split()) <= 5:
        return "kurz"  # Kurze Frage → kurze Antwort
    else:
        return "standard"


ANTWORT_TYP_PROMPTS = {
    "kurz": """
ANTWORT-STIL: KURZ & PRÄZISE
- Maximal 3 Sätze
- Nur die direkte Antwort
- Bei Mathe: Ergebnis + eine Zeile Rechenweg
- Kein Beispiel nötig
- Format: **Antwort:** [Antwort]
""",
    "schritt_fuer_schritt": """
ANTWORT-STIL: SCHRITT FÜR SCHRITT
- Nummerierte Schritte (1. 2. 3. ...)
- Jeden Schritt einzeln erklären
- Zwischenergebnisse zeigen
- Am Ende: Zusammenfassung in 1 Satz
- LaTeX für jeden Rechenschritt
""",
    "aufgabe_loesen": """
ANTWORT-STIL: AUFGABE LÖSEN
- Struktur: Gegeben → Gesucht → Formel → Rechnung → Ergebnis
- Jeden Schritt in LaTeX
- Einheiten nicht vergessen
- Probe wenn möglich
""",
    "standard": """
ANTWORT-STIL: STANDARD
- Direkte Antwort (1 Satz)
- Erklärung (2-3 Sätze)
- Beispiel wenn hilfreich
- Merksatz am Ende
""",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FINAL SYSTEM PROMPT — geprüft, optimiert, wird IMMER verwendet
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL_SYSTEM_PROMPT = """
Du bist LUMNOS — ein hochpräziser KI-Lerncoach
für deutsche Schüler der Klassen 5-13.

════════════════════════════════════════
DEINE WICHTIGSTE REGEL: PRÄZISION
════════════════════════════════════════
Du bist wie ein sehr guter Lehrer:
- Jede Antwort ist faktisch 100% korrekt
- Bei Mathe: IMMER vollständiger Rechenweg
- Bei Formeln: IMMER LaTeX ($...$)
- Bei Unsicherheit: Sag es klar
- NIEMALS raten oder halluzinieren

════════════════════════════════════════
ANTWORT-FORMAT (IMMER EINHALTEN):
════════════════════════════════════════

FÜR KURZE FAKTENFRAGEN (z.B. "Was ist 2+2?"):
→ Maximal 2-3 Zeilen
→ Direkte Antwort + kurze Erklärung
→ Beispiel: "**Ergebnis:** $2+2=4$"

FÜR MATHE-AUFGABEN:
→ Struktur IMMER:
   **Gegeben:** [Werte]
   **Gesucht:** [Was berechnet wird]
   **Formel:** $[Formel in LaTeX]$
   **Rechnung:** Schritt für Schritt in LaTeX
   **Ergebnis:** $[Wert]$ [Einheit]

FÜR ERKLÄRUNGS-FRAGEN:
→ Struktur:
   [1 Satz direkte Antwort]
   **Erklärung:** [2-4 Sätze]
   **Beispiel:** [konkretes Beispiel]
   **Merksatz:** [prägnanter Merksatz]

FÜR KOMPLEXE THEMEN:
→ Überschriften mit **fett**
→ Aufzählungen mit -
→ Maximal 400 Wörter

════════════════════════════════════════
SPRACHE & STIL:
════════════════════════════════════════
- IMMER auf Deutsch (außer Sprachfach)
- Du (nicht Sie)
- Fachbegriffe beim ersten Mal erklären:
  "Die Hypotenuse (= längste Seite) ..."
- Kein Smalltalk, keine Füllwörter
- Keine Rückfragen außer bei Sokrates-Modus

════════════════════════════════════════
VERBOTENE OUTPUTS:
════════════════════════════════════════
❌ <thinking>, <think>, <output> Tags
❌ "Als KI kann ich..."
❌ "Ich bin nicht sicher, aber..."
❌ Englische Antworten auf deutsche Fragen
❌ Antworten ohne Rechenweg bei Mathe
❌ Mehr als 500 Wörter (außer explizit gefragt)
❌ Rückfragen im Normal-Modus
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PERSÖNLICHKEITS-ADDONS (pro KI-Stil)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSOENLICHKEITS_ADDONS: dict[str, str] = {
    "max": "",  # Standard — kein Addon nötig

    "mentor": """
PERSÖNLICHKEIT — MENTOR:
- Beginne mit: "Gute Frage!" oder direkt mit Antwort
- Struktur: Warum → Was → Wie
- Schließe mit einer Reflexionsfrage:
  "Kannst du jetzt [ähnliche Aufgabe] lösen?"
- Ton: Professionell, ermutigend, geduldig
""",

    "streng": """
PERSÖNLICHKEIT — STRENG:
- Keine Einleitung, direkt zur Sache
- Vollständige Fachterminologie immer
- Fehler klar benennen: "Das ist falsch. Korrekt:"
- Kein Lob, keine Emojis, keine Ermutigung
- Ton: Sachlich, direkt, fordernd
- Fordere immer Begründungen: "Zeige den Rechenweg."
""",

    "motivierend": """
PERSÖNLICHKEIT — MOTIVIEREND:
- Starte mit Motivation: "Super, dass du das lernst!"
- Erkläre mit Alltagsbeispielen
- Zeige warum das Thema wichtig/cool ist
- Schließe mit: "Du schaffst das! Tipp: ..."
- Max 1-2 Emojis pro Antwort
- Ton: Enthusiastisch, energetisch, positiv
""",

    "eli5": """
PERSÖNLICHKEIT — ELI5:
- Erkläre wie für einen 10-Jährigen
- Nur Alltagssprache, keine Fremdwörter
- Nutze Analogien: Lego, Minecraft, Fußball, Essen
- Kurze Sätze (max 12 Wörter)
- WICHTIG: Vereinfachung darf NICHT falsch sein!
- Formeln trotzdem zeigen — aber einfach erklären
""",

    "sokrates": """
PERSÖNLICHKEIT — SOKRATES:
- Antworte NIEMALS direkt mit der Lösung
- Stelle immer eine Gegenfrage die hinführt:
  "Was weißt du bereits über...?"
  "Wenn a=3 und b=4, was folgt für c²?"
- Nach 3 Fragen: Gib einen Hinweis
- Erst wenn Schüler aufgibt: Vollständige Lösung
- Endet IMMER mit einer Frage
- Ton: Neugierig, philosophisch, leitend
""",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANTWORT-QUALITÄTS-CHECKER (AUFGABE 3)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BEKANNTE_KORREKTE_ANTWORTEN = {
    # Mathe-Grundlagen
    "2+2": "4", "√144": "12", "√169": "13", "√25": "5",
    # Physik-Konstanten
    "lichtgeschwindigkeit": "299.792.458 m/s",
    "erdbeschleunigung": "9,81 m/s²",
    # Geschichte
    "berliner mauer": "1989",
    "zweiter weltkrieg ende": "1945",
    "zweiter weltkrieg beginn": "1939",
    "erster weltkrieg beginn": "1914",
    "erster weltkrieg ende": "1918",
    # Chemie
    "h2o": "Wasser",
    "co2": "Kohlenstoffdioxid",
    "nacl": "Natriumchlorid",
}

HALLUZINATIONS_MUSTER = [
    "im jahr 2024 wurde",
    "im jahr 2025 wurde",
    "im jahr 2026 wurde",
    "laut einer studie von 2025",
    "laut einer studie von 2026",
    "kürzlich hat",
    "neueste forschungen zeigen",
]


def check_antwort_qualitaet(frage: str, antwort: str) -> dict:
    """Prüft ob die Antwort offensichtlich falsche Fakten enthält.

    Returns: {"ok": bool, "warnung": str | None, "antwort_ersetzen": bool}
    """
    frage_lower = frage.lower()
    antwort_lower = antwort.lower()

    warnungen = []

    # Bekannte korrekte Antworten prüfen
    for schluessel, korrekt in BEKANNTE_KORREKTE_ANTWORTEN.items():
        if schluessel in frage_lower:
            if korrekt.lower() not in antwort_lower:
                warnungen.append(
                    f"Erwartete '{korrekt}' bei Frage zu '{schluessel}'"
                )

    # Typische Halluzinationen erkennen
    for muster in HALLUZINATIONS_MUSTER:
        if muster in antwort_lower:
            warnungen.append(f"Mögliche Halluzination: '{muster}'")

    # Error-Fallback noch sichtbar?
    if "die ki konnte gerade nicht antworten" in antwort_lower:
        logger.error("[QUALITY CRITICAL] Error-Fallback in Antwort sichtbar!")
        return {
            "ok": False,
            "warnung": "Error-Fallback in Antwort!",
            "antwort_ersetzen": True,
        }

    # Thinking-Tags noch sichtbar?
    if "<thinking>" in antwort or "<think>" in antwort:
        logger.error("[QUALITY CRITICAL] Thinking-Tags nicht entfernt!")
        return {
            "ok": False,
            "warnung": "Thinking-Tags nicht entfernt!",
            "antwort_ersetzen": True,
        }

    if warnungen:
        for w in warnungen:
            logger.warning("[QUALITY WARN] %s", w)
        return {"ok": True, "warnung": str(warnungen), "antwort_ersetzen": False}

    return {"ok": True, "warnung": None, "antwort_ersetzen": False}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEEP THINKING MODUS — Doppelte Prüfung für maximale Präzision
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def deep_thinking_response(
    frage: str,
    system_prompt: str,
    fach: str = "Allgemein",
) -> tuple[str, str]:
    """Deep Thinking: Runde 1 → Antwort, Runde 2 → Selbst-Verifikation.

    Returns (finale_antwort, model_name).
    """
    from app.services.groq_llm import call_groq_llm, _get_client, DEFAULT_MODEL

    client = _get_client()
    if client is None:
        # Kein API Key → Standard-Antwort
        antwort = call_groq_llm(
            prompt=frage,
            system_prompt=system_prompt,
            subject=fach,
            level="intermediate",
            language="de",
            chat_history=[],
            rag_context="",
            is_pro=False,
        )
        return antwort, "template"

    model = "llama-3.3-70b-versatile"

    # RUNDE 1: Erste Antwort generieren
    runde1_prompt = system_prompt + """
WICHTIG: Du bist jetzt im DEEP THINKING Modus.
Denke besonders sorgfältig nach. Gib deine beste
erste Antwort — vollständig und präzise.
"""
    try:
        r1 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": runde1_prompt},
                {"role": "user", "content": frage},
            ],
            max_tokens=800,
            temperature=0.1,
            stream=False,
            timeout=30.0,
        )
        antwort1 = (r1.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning("Deep Thinking Runde 1 fehlgeschlagen: %s", e)
        antwort1 = ""

    if not antwort1:
        # Fallback auf Standard
        antwort = call_groq_llm(
            prompt=frage,
            system_prompt=system_prompt,
            subject=fach,
            level="intermediate",
            language="de",
            chat_history=[],
            rag_context="",
            is_pro=False,
        )
        return antwort, model

    # Interne Tags entfernen
    import re as _re
    for tag in ["thinking", "reasoning", "output", "internal"]:
        antwort1 = _re.sub(rf'<{tag}>.*?</{tag}>', '', antwort1, flags=_re.DOTALL)
        antwort1 = _re.sub(rf'<{tag}>.*', '', antwort1, flags=_re.DOTALL)
        antwort1 = antwort1.replace(f'</{tag}>', '').replace(f'<{tag}>', '')
    antwort1 = _re.sub(r'\n{3,}', '\n\n', antwort1).strip()

    # RUNDE 2: Selbst-Verifikation und Verbesserung
    verifikations_prompt = f"""Du bist ein Qualitätsprüfer für Lern-Antworten.
Prüfe diese Antwort auf:
1. Faktische Korrektheit (100% muss stimmen)
2. Vollständigkeit (fehlt etwas Wichtiges?)
3. Klarheit (ist es für Schüler verständlich?)
4. LaTeX (sind alle Formeln korrekt?)

URSPRÜNGLICHE FRAGE: {frage}
FACH: {fach}

ERSTE ANTWORT:
{antwort1}

Wenn die Antwort perfekt ist → gib sie leicht poliert zurück.
Wenn Fehler oder Lücken → korrigiere sie vollständig.
Gib NUR die finale, verbesserte Antwort zurück.
Keine Erklärung was du geändert hast."""

    try:
        r2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Du bist ein präziser Qualitätsprüfer für Bildungsantworten. Antworte auf Deutsch."},
                {"role": "user", "content": verifikations_prompt},
            ],
            max_tokens=800,
            temperature=0.05,
            stream=False,
            timeout=30.0,
        )
        antwort2 = (r2.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning("Deep Thinking Runde 2 fehlgeschlagen: %s — nutze Runde 1", e)
        return antwort1, model

    if not antwort2:
        return antwort1, model

    # Tags bereinigen
    for tag in ["thinking", "reasoning", "output", "internal"]:
        antwort2 = _re.sub(rf'<{tag}>.*?</{tag}>', '', antwort2, flags=_re.DOTALL)
        antwort2 = _re.sub(rf'<{tag}>.*', '', antwort2, flags=_re.DOTALL)
        antwort2 = antwort2.replace(f'</{tag}>', '').replace(f'<{tag}>', '')
    antwort2 = _re.sub(r'\n{3,}', '\n\n', antwort2).strip()

    # Längere Antwort nehmen (mehr Inhalt = besser), außer Runde 2 ist viel kürzer
    finale = antwort2 if len(antwort2) > len(antwort1) * 0.7 else antwort1

    return finale, model


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FAST MODUS — Blitzschnelle Antworten (<2 Sekunden)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def fast_response(
    frage: str,
    system_prompt: str,
) -> tuple[str, str]:
    """Fast Mode: llama-3.1-8b-instant, max 200 tokens, <2s Antwort.

    Returns (antwort, model_name).
    """
    from app.services.groq_llm import call_groq_llm, _get_client

    model = "llama-3.1-8b-instant"

    fast_system = system_prompt + """
FAST MODE: Antworte in maximal 3 Sätzen.
Nur das Wesentliche — kein Beispiel nötig außer bei Mathe-Aufgaben.
Direkt zur Antwort. Keine Einleitung, keine Rückfragen.
"""

    client = _get_client()
    if client is None:
        antwort = call_groq_llm(
            prompt=frage,
            system_prompt=fast_system,
            subject="Allgemein",
            level="intermediate",
            language="de",
            chat_history=[],
            rag_context="",
            is_pro=False,
        )
        return antwort, "template"

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": fast_system},
                {"role": "user", "content": frage},
            ],
            max_tokens=200,
            temperature=0.3,
            stream=False,
            timeout=10.0,
        )
        antwort = (completion.choices[0].message.content or "").strip()
        if not antwort:
            raise ValueError("Leere Antwort")
    except Exception as e:
        logger.warning("Fast Mode fehlgeschlagen: %s — Fallback", e)
        antwort = call_groq_llm(
            prompt=frage,
            system_prompt=fast_system,
            subject="Allgemein",
            level="intermediate",
            language="de",
            chat_history=[],
            rag_context="",
            is_pro=False,
        )
        return antwort, model

    # Tags bereinigen
    import re as _re
    for tag in ["thinking", "reasoning", "output", "internal"]:
        antwort = _re.sub(rf'<{tag}>.*?</{tag}>', '', antwort, flags=_re.DOTALL)
        antwort = _re.sub(rf'<{tag}>.*', '', antwort, flags=_re.DOTALL)
        antwort = antwort.replace(f'</{tag}>', '').replace(f'<{tag}>', '')
    antwort = _re.sub(r'\n{3,}', '\n\n', antwort).strip()

    return antwort, model


def smart_model_selection(prompt: str) -> str:
    """Select optimal model based on question complexity.

    Simple, short questions → llama-3.1-8b-instant (fast, saves tokens)
    Complex, long questions → llama-3.3-70b-versatile (best quality)

    Returns the recommended model name.
    """
    prompt_lower = prompt.strip().lower()
    prompt_len = len(prompt_lower)

    # Very short arithmetic/factual questions → always 8b
    if prompt_len < 20:
        # Pure math expressions
        if re.match(r'^[\d\s+\-*/^√().=?x]+$', prompt_lower):
            return "llama-3.1-8b-instant"

    # Check for complex patterns → 70b
    has_complex = any(p in prompt_lower for p in _COMPLEX_PATTERNS)
    if has_complex:
        return "llama-3.3-70b-versatile"

    # Check for simple patterns AND short prompt → 8b
    is_simple = any(p in prompt_lower for p in _SIMPLE_PATTERNS)
    if is_simple and prompt_len < 50:
        return "llama-3.1-8b-instant"

    # Short prompts without clear complexity → 8b (save tokens)
    if prompt_len < 30:
        return "llama-3.1-8b-instant"

    # Default → 70b for quality
    return "llama-3.3-70b-versatile"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOCK A: Fach-Normalisierung — English → Deutsch
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FACH_MAPPING: dict[str, str] = {
    # Sprachen
    "german":      "Deutsch",
    "english":     "Englisch",
    "french":      "Französisch",
    "spanish":     "Spanisch",
    "latin":       "Latein",
    "ancient greek": "Altgriechisch",
    "russian":     "Russisch",
    "italian":     "Italienisch",
    "chinese":     "Chinesisch",
    # MINT
    "math":        "Mathematik",
    "mathematics": "Mathematik",
    "physics":     "Physik",
    "chemistry":   "Chemie",
    "biology":     "Biologie",
    "computer":    "Informatik",
    "computer science": "Informatik",
    "science":     "Naturwissenschaft",
    "astronomy":   "Astronomie",
    "nut":         "Natur und Technik",
    "natur und technik": "Natur und Technik",
    # Gesellschaft
    "history":     "Geschichte",
    "geography":   "Geografie",
    "economics":   "Wirtschaft",
    "politics":    "Politik",
    "sociology":   "Sozialkunde",
    "gemeinschaftskunde": "Gemeinschaftskunde",
    "philosophy":  "Philosophie",
    "ethics":      "Ethik",
    "religion":    "Religion",
    "religion evangelisch": "Religion (Evangelisch)",
    "religion katholisch": "Religion (Katholisch)",
    "religion islamisch": "Religion (Islamisch)",
    "religion jüdisch": "Religion (Jüdisch)",
    # Kreativ/Sport
    "art":         "Kunst",
    "music":       "Musik",
    "sport":       "Sport",
    "physical education": "Sport",
    "theater":     "Darstellendes Spiel",
    "drama":       "Darstellendes Spiel",
    # Pädagogik/Spezial
    "psychology":  "Psychologie",
    "pedagogy":    "Pädagogik",
    "erziehungswissenschaften": "Pädagogik",
    "nutrition":   "Ernährung und Gesundheit",
    "media":       "Medieninformatik",
    "general":     "Allgemein",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOCK 3: All-Germany Fächer Matrix (Quality Engine v2)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Alle 16 Bundesländer mit Lehrplan-Besonderheiten
BUNDESLAND_LEHRPLAN: dict[str, dict] = {
    "Bayern": {
        "name": "Bayern",
        "abitur": "G9 (seit 2025), LehrplanPLUS",
        "besonderheiten": "Sehr anspruchsvolles Abitur, starker MINT-Fokus",
    },
    "Baden-Württemberg": {
        "name": "Baden-Württemberg",
        "abitur": "Bildungsplan 2016, kein Zentralabitur",
        "besonderheiten": "Gemeinschaftskunde statt Sozialkunde, NwT als Profilfach",
    },
    "NRW": {
        "name": "Nordrhein-Westfalen",
        "abitur": "Zentralabitur, Kernlehrpläne MSB",
        "besonderheiten": "Größtes Bundesland, breites Fächerangebot",
    },
    "Niedersachsen": {
        "name": "Niedersachsen",
        "abitur": "Kerncurriculum, zentrale Abituraufgaben",
        "besonderheiten": "Werte und Normen als Ersatz für Religion",
    },
    "Hessen": {
        "name": "Hessen",
        "abitur": "Kerncurriculum, Zentralabitur (Landesabitur)",
        "besonderheiten": "Politik und Wirtschaft als Kombinationsfach",
    },
    "Berlin": {
        "name": "Berlin",
        "abitur": "Rahmenlehrplan, Senat für Bildung",
        "besonderheiten": "Ethik Pflichtfach, breites Sprachangebot",
    },
    "Hamburg": {
        "name": "Hamburg",
        "abitur": "Bildungsplan, Abitur zentral",
        "besonderheiten": "Theater als reguläres Fach, PGW (Politik/Gesellschaft/Wirtschaft)",
    },
    "Sachsen": {
        "name": "Sachsen",
        "abitur": "Lehrpläne des SMK, zentrales Abitur",
        "besonderheiten": "Starker MINT-Fokus, Informatik ab Klasse 7",
    },
    "Thüringen": {
        "name": "Thüringen",
        "abitur": "Thüringer Lehrpläne, zentral",
        "besonderheiten": "Astronomie als eigenständiges Fach",
    },
    "Brandenburg": {
        "name": "Brandenburg",
        "abitur": "Rahmenlehrplan (gemeinsam mit Berlin)",
        "besonderheiten": "LER (Lebensgestaltung-Ethik-Religionskunde)",
    },
    "Sachsen-Anhalt": {
        "name": "Sachsen-Anhalt",
        "abitur": "Fachlehrpläne, zentrale Prüfungen",
        "besonderheiten": "Astronomie verfügbar, Ethik als Alternative",
    },
    "Mecklenburg-Vorpommern": {
        "name": "Mecklenburg-Vorpommern",
        "abitur": "Rahmenplan, zentrale Prüfungen",
        "besonderheiten": "Philosophieren mit Kindern, AWT",
    },
    "Schleswig-Holstein": {
        "name": "Schleswig-Holstein",
        "abitur": "Fachanforderungen, zentral",
        "besonderheiten": "WiPo (Wirtschaft/Politik) als Kombifach",
    },
    "Rheinland-Pfalz": {
        "name": "Rheinland-Pfalz",
        "abitur": "Lehrpläne RLP, dezentrales Abitur",
        "besonderheiten": "Sozialkunde ab Klasse 7, dezentrales Abitur",
    },
    "Saarland": {
        "name": "Saarland",
        "abitur": "Lehrpläne, G9",
        "besonderheiten": "Französisch ab Klasse 3, starker Frankreich-Bezug",
    },
    "Bremen": {
        "name": "Bremen",
        "abitur": "Bildungspläne, zentral",
        "besonderheiten": "Gesamtschul-System, WAT (Wirtschaft-Arbeit-Technik)",
    },
}

# Fach-spezifische Lehrplan-Expertise
FACH_LEHRPLAN_EXPERTISE: dict[str, str] = {
    "Mathematik": "Nutze LaTeX für alle Formeln ($..$ inline, $$...$$ Block). Zeige Rechenwege vollständig. Beachte CAS-Taschenrechner-Regelungen.",
    "Physik": "Formeln mit Einheiten (SI-System). Realweltbeispiele. Experimente beschreiben.",
    "Chemie": "Reaktionsgleichungen ausbalancieren. Periodensystem-Bezug. Stöchiometrie.",
    "Biologie": "Fachbegriffe erklären + lateinische Namen. Evolutionärer Kontext. Ökosystem-Denken.",
    "Geschichte": "Quellen nennen. Historische Einordnung. Kausalität. Multiperspektivität.",
    "Deutsch": "Textanalyse nach Aufbau-Methode. Stilmittel benennen. Epochen-Kontext.",
    "Englisch": "Grammatik mit Beispielen. Vokabeln im Kontext. British vs American English.",
    "Französisch": "Grammatik (Subjonctif, Conditionnel). Kultur-Kontext. Aussprache-Tipps.",
    "Spanisch": "Subjuntivo vs Indicativo. Lateinamerikanisches vs europäisches Spanisch.",
    "Latein": "Stammformen bei Vokabeln. Kasus syntaktisch begründen. Übersetzungstechnik.",
    "Altgriechisch": "Attisches Griechisch. Stammformen. Partizipialkonstruktionen.",
    "Russisch": "Kyrillische Schrift erklären. Aspektpaare. Deklinationsmuster.",
    "Italienisch": "Congiuntivo. Passato prossimo vs imperfetto. Aussprache.",
    "Chinesisch": "Pinyin-Transkription. Schriftzeichen-Aufbau. Tonalität.",
    "Informatik": "Code in Codeblöcken. Zeitkomplexität (O-Notation). Pseudocode + Python/Java.",
    "Astronomie": "Keplersche Gesetze. Hertzsprung-Russell-Diagramm. Kosmologie-Grundlagen.",
    "Natur und Technik": "Fächerübergreifend (Bio+Physik+Chemie). Alltagsbezug. Experimente.",
    "Geografie": "Karten lesen. Klimazonen. Plattentektonik. Stadtgeografie.",
    "Wirtschaft": "Angebot/Nachfrage. Konjunkturzyklus. Wirtschaftssysteme. Aktuelle Bezüge.",
    "Politik": "Grundgesetz. Gewaltenteilung. EU-Institutionen. Aktuelle Politik.",
    "Sozialkunde": "Gesellschaftsstrukturen. Soziale Ungleichheit. Medien. Demokratie.",
    "Gemeinschaftskunde": "Politik + Wirtschaft + Gesellschaft integriert. BaWü-spezifisch.",
    "Philosophie": "Logisch argumentieren. Philosophen zitieren. Gedankenexperimente.",
    "Ethik": "Moralische Dilemmata. Wertesysteme. Religionsvergleich. Utilitarismus vs Deontologie.",
    "Religion (Evangelisch)": "Lutherische Theologie. Bibelexegese. Kirchengeschichte.",
    "Religion (Katholisch)": "Sakramente. Kirchenlehre. Sozialethik. Vatikan II.",
    "Religion (Islamisch)": "Koran-Exegese. Fünf Säulen. Islamische Ethik. Hadith.",
    "Religion (Jüdisch)": "Tora. Jüdische Feiertage. Holocaust-Erinnerung. Talmud.",
    "Religion": "Interreligiöser Dialog. Weltreligionen vergleichen. Ethische Grundfragen.",
    "Kunst": "Epochen (Barock, Impressionismus, etc.). Bildanalyse. Gestaltungsprinzipien.",
    "Musik": "Notenlehre. Musikgeschichte. Harmonielehre. Werkanalyse.",
    "Sport": "Trainingslehre. Bewegungsanalyse. Sportbiologie. Regelkunde.",
    "Darstellendes Spiel": "Theaterpädagogik. Inszenierung. Rollenarbeit. Dramaturgie.",
    "Psychologie": "Lerntheorien. Entwicklungspsychologie. Sozialpsychologie. Experimente.",
    "Pädagogik": "Erziehungstheorien. Montessori, Piaget, Erikson. Bildungssystem.",
    "Ernährung und Gesundheit": "Nährstoffe. Verdauung. Gesunde Ernährung. Essstörungen.",
    "Medieninformatik": "Webentwicklung. Datenbanken. UX-Design. Digitale Medien.",
}


def get_lehrplan_context(fach: str, bundesland: str = "", klasse: str = "10") -> str:
    """Generiert Lehrplan-Kontext für ein Fach basierend auf Bundesland und Klasse.

    Block 3 der Quality Engine v2: Jedes Fach bekommt spezifischen
    Lehrplan-Kontext injiziert.
    """
    parts = []

    # Fach-spezifische Expertise
    expertise = FACH_LEHRPLAN_EXPERTISE.get(fach, "")
    if expertise:
        parts.append(f"Fach-Expertise: {expertise}")

    # Bundesland-spezifischer Kontext
    bl_info = BUNDESLAND_LEHRPLAN.get(bundesland, {})
    if bl_info:
        parts.append(
            f"Bundesland: {bl_info['name']} — {bl_info['abitur']}. "
            f"{bl_info['besonderheiten']}."
        )
    elif bundesland:
        parts.append(f"Bundesland: {bundesland} — Nationaler Lehrplan.")

    # Klassen-spezifischer Kontext
    klasse_int = 10
    try:
        klasse_int = int(klasse)
    except (ValueError, TypeError):
        pass

    if klasse_int <= 6:
        parts.append("Niveau: Unterstufe — Grundlagen, einfache Sprache, viele Beispiele.")
    elif klasse_int <= 9:
        parts.append("Niveau: Mittelstufe — Vertiefung, erste Fachbegriffe, Zusammenhänge.")
    elif klasse_int <= 10:
        parts.append("Niveau: Oberstufe-Übergang — MSA/Realschulabschluss, komplexere Aufgaben.")
    elif klasse_int <= 12:
        parts.append("Niveau: Oberstufe/Abitur — Wissenschaftspropädeutisch, Analyse, Erörterung.")
    else:
        parts.append("Niveau: Abitur-Vorbereitung — Höchstes Niveau, Prüfungsformat.")

    # Rahmenlehrplan-Injection
    parts.append(
        f"Du erklärst {fach} nach dem Rahmenlehrplan für "
        f"{bundesland or 'Deutschland'} Klasse {klasse}."
    )

    return "\n".join(parts)


def normalize_fach(fach_raw: str) -> str:
    """Normalisiert Fach-Namen — immer Deutsch, niemals Englisch."""
    if not fach_raw:
        return "Allgemein"
    clean = fach_raw.strip().lower()
    # Direktes Mapping
    if clean in FACH_MAPPING:
        return FACH_MAPPING[clean]
    # Substring-Suche
    for eng, deu in FACH_MAPPING.items():
        if eng in clean:
            return deu
    # Bereits deutsch? Ersten Buchstaben groß
    return fach_raw.strip().capitalize()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FACH-KEYWORDS mit Priorität (höher = wichtiger)
# Reihenfolge = Priorität: Spezifisches vor Allgemeinem
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FACH_KEYWORDS: list[tuple[str, str, int]] = [
    # (keyword_lowercase, fach, priorität)

    # ═══ MATHEMATIK (höchste Priorität für Formeln) ═══
    ("pythagoras",       "Mathematik", 100),
    ("integral",         "Mathematik", 100),
    ("ableitung",        "Mathematik", 100),
    ("differenzial",     "Mathematik", 100),
    ("quadratisch",      "Mathematik", 100),
    ("gleichung",        "Mathematik",  90),
    ("bruchrechnung",    "Mathematik",  90),
    ("trigonometrie",    "Mathematik",  90),
    ("sinus",            "Mathematik",  90),
    ("kosinus",          "Mathematik",  90),
    ("tangens",          "Mathematik",  90),
    ("kurvendiskussion", "Mathematik",  90),
    ("nullstelle",       "Mathematik",  90),
    ("steigung",         "Mathematik",  85),
    ("wurzel",           "Mathematik",  85),
    ("vektor",           "Mathematik",  85),
    ("matrix",           "Mathematik",  85),
    ("wahrscheinlich",   "Mathematik",  80),
    ("statistik",        "Mathematik",  80),
    ("geometrie",        "Mathematik",  80),
    ("dreieck",          "Mathematik",  80),
    ("kreis",            "Mathematik",  75),
    ("fläche",           "Mathematik",  75),
    ("volumen",          "Mathematik",  75),
    ("funktion",         "Mathematik",  70),
    ("berechne",         "Mathematik",  65),
    ("formel",           "Mathematik",  60),

    # ═══ PHYSIK ═══
    ("newton",           "Physik",      100),
    ("relativität",      "Physik",      100),
    ("quantenmechanik",  "Physik",      100),
    ("elektromagnet",    "Physik",       95),
    ("thermodynamik",    "Physik",       95),
    ("lichtgeschwindig", "Physik",       95),
    ("kernspaltung",     "Physik",       95),
    ("radioaktiv",       "Physik",       90),
    ("impuls",           "Physik",       85),
    ("energie",          "Physik",       80),
    ("spannung",         "Physik",       80),
    ("strom",            "Physik",       75),
    ("widerstand",       "Physik",       75),
    ("kraft",            "Physik",       70),
    ("geschwindigkeit",  "Physik",       70),
    ("beschleunigung",   "Physik",       70),
    ("masse",            "Physik",       60),
    ("welle",            "Physik",       60),

    # ═══ CHEMIE ═══
    ("molekül",          "Chemie",      100),
    ("atom",             "Chemie",       95),
    ("reaktion",         "Chemie",       90),
    ("säure",            "Chemie",       90),
    ("base",             "Chemie",       85),
    ("oxidation",        "Chemie",       90),
    ("elektronen",       "Chemie",       80),
    ("bindung",          "Chemie",       75),
    ("element",          "Chemie",       70),
    ("periodensystem",   "Chemie",      100),
    ("verbrennung",      "Chemie",       85),
    ("katalysator",      "Chemie",       90),

    # ═══ BIOLOGIE ═══
    ("photosynthese",    "Biologie",    100),
    ("fotosynthese",     "Biologie",    100),
    ("zelle",            "Biologie",     90),
    ("zellen",           "Biologie",     90),
    ("chromosom",        "Biologie",    100),
    ("dna",              "Biologie",    100),
    ("rna",              "Biologie",    100),
    ("protein",          "Biologie",     85),
    ("enzym",            "Biologie",     90),
    ("evolution",        "Biologie",     90),
    ("darwin",           "Biologie",     95),
    ("ökosystem",        "Biologie",     90),
    ("mitose",           "Biologie",    100),
    ("meiose",           "Biologie",    100),
    ("chloroplast",      "Biologie",    100),
    ("chlorophyll",      "Biologie",    100),
    ("nervensystem",     "Biologie",     90),
    ("hormonsystem",     "Biologie",     90),
    ("stoffwechsel",     "Biologie",     85),
    ("atmung",           "Biologie",     75),
    ("blut",             "Biologie",     70),
    ("herz",             "Biologie",     70),
    ("neuron",           "Biologie",     90),
    ("gehirn",           "Biologie",     80),
    ("genetik",          "Biologie",    100),
    ("erblich",          "Biologie",     85),
    ("erbanlage",        "Biologie",     90),
    ("gen ",             "Biologie",     80),
    ("pilz",             "Biologie",     75),
    ("bakterien",        "Biologie",     85),
    ("virus",            "Biologie",     80),
    ("pflanze",          "Biologie",     75),
    ("säugetier",        "Biologie",     85),
    ("ökologie",         "Biologie",     90),
    ("nahrungskette",    "Biologie",     95),
    ("population",       "Biologie",     80),

    # ═══ GESCHICHTE ═══
    ("weimar",           "Geschichte",  100),
    ("nationalsozial",   "Geschichte",  100),
    ("holocaust",        "Geschichte",  100),
    ("weltkrieg",        "Geschichte",  100),
    ("napoleon",         "Geschichte",   95),
    ("revolution",       "Geschichte",   85),
    ("kaiser",           "Geschichte",   80),
    ("reich",            "Geschichte",   75),
    ("krieg",            "Geschichte",   70),
    ("frieden",          "Geschichte",   65),
    ("kolonial",         "Geschichte",   85),
    ("demokratie",       "Geschichte",   70),
    ("antike",           "Geschichte",   85),
    ("römer",            "Geschichte",   90),
    ("griechen",         "Geschichte",   85),
    ("mittelalter",      "Geschichte",   90),
    ("renaissance",      "Geschichte",   85),

    # ═══ DEUTSCH — KEIN "satz" (zu allgemein!) ═══
    ("grammatik",        "Deutsch",     100),
    ("rechtschreibung",  "Deutsch",     100),
    ("aufsatz",          "Deutsch",      95),
    ("erörterung",       "Deutsch",     100),
    ("inhaltsangabe",    "Deutsch",     100),
    ("analyse",          "Deutsch",      70),
    ("metapher",         "Deutsch",      95),
    ("stilmittel",       "Deutsch",     100),
    ("gedicht",          "Deutsch",      95),
    ("lyrik",            "Deutsch",     100),
    ("epik",             "Deutsch",     100),
    ("dramatik",         "Deutsch",     100),
    ("roman",            "Deutsch",      85),
    ("konjunktiv",       "Deutsch",     100),
    ("genitiv",          "Deutsch",     100),
    ("dativ",            "Deutsch",      95),
    ("akkusativ",        "Deutsch",      95),
    ("komma",            "Deutsch",      90),
    ("faust",            "Deutsch",      95),
    ("schiller",         "Deutsch",      95),
    ("goethe",           "Deutsch",      95),
    ("kafka",            "Deutsch",      95),

    # ═══ ENGLISCH ═══
    ("grammar",          "Englisch",    100),
    ("tense",            "Englisch",    100),
    ("present perfect",  "Englisch",    100),
    ("past tense",       "Englisch",    100),
    ("vocabulary",       "Englisch",     95),
    ("pronunciation",    "Englisch",     95),
    ("essay",            "Englisch",     85),

    # ═══ INFORMATIK ═══
    ("algorithmus",      "Informatik",  100),
    ("python",           "Informatik",  100),
    ("javascript",       "Informatik",  100),
    ("datenbank",        "Informatik",  100),
    ("programmier",      "Informatik",  100),
    ("code",             "Informatik",   90),
    ("schleife",         "Informatik",   90),
    ("array",            "Informatik",   95),
    ("binär",            "Informatik",   95),
    ("netzwerk",         "Informatik",   85),
    ("rekursion",        "Informatik",   95),

    # ═══ LATEIN ═══
    ("latein",           "Latein",      100),
    ("cäsar",            "Latein",       95),
    ("cicero",           "Latein",       95),
    ("konjugation",      "Latein",       90),
    ("deklinieren",      "Latein",      100),

    # ═══ WIRTSCHAFT ═══
    ("volkswirtschaft",  "Wirtschaft",  100),
    ("betriebswirtschaft", "Wirtschaft", 100),
    ("angebot",          "Wirtschaft",   85),
    ("nachfrage",        "Wirtschaft",   85),
    ("markt",            "Wirtschaft",   80),
    ("konjunktur",       "Wirtschaft",   90),
    ("inflation",        "Wirtschaft",   90),

    # ═══ PSYCHOLOGIE ═══
    ("psychologie",      "Psychologie", 100),
    ("verhalten",        "Psychologie",  75),
    ("konditionierung",  "Psychologie", 100),
    ("freud",            "Psychologie",  95),

    # ═══ GEOGRAFIE ═══
    ("erdkunde",         "Geografie",    90),
    ("klima",            "Geografie",    85),
    ("kontinent",        "Geografie",    85),
    ("plattentektonik",  "Geografie",   100),
    ("land",             "Geografie",    60),

    # ═══ NEUE FÄCHER (Quality Engine v2 Block 3) ═══
    ("altgriechisch",    "Altgriechisch", 100),
    ("homer",            "Altgriechisch", 90),
    ("platon",           "Altgriechisch", 90),
    ("russisch",         "Russisch",    100),
    ("kyrillisch",       "Russisch",     95),
    ("italienisch",      "Italienisch", 100),
    ("chinesisch",       "Chinesisch",  100),
    ("mandarin",         "Chinesisch",  100),
    ("astronomie",       "Astronomie",  100),
    ("planet",           "Astronomie",   80),
    ("stern",            "Astronomie",   75),
    ("galaxie",          "Astronomie",  100),
    ("natur und technik", "Natur und Technik", 100),
    ("gemeinschaftskunde", "Gemeinschaftskunde", 100),
    ("pädagogik",        "Pädagogik",   100),
    ("erziehungswissensch", "Pädagogik", 100),
    ("montessori",       "Pädagogik",    95),
    ("ernährung",        "Ernährung und Gesundheit", 90),
    ("nährstoff",        "Ernährung und Gesundheit", 90),
    ("medieninformatik",  "Medieninformatik", 100),
    ("darstellendes spiel", "Darstellendes Spiel", 100),
    ("theater",          "Darstellendes Spiel", 90),
    ("schauspiel",       "Darstellendes Spiel", 90),
    ("evangelisch",      "Religion (Evangelisch)", 95),
    ("katholisch",       "Religion (Katholisch)", 95),
    ("islamisch",        "Religion (Islamisch)", 95),
    ("jüdisch",          "Religion (Jüdisch)", 95),
    ("ethik",            "Ethik",       100),
    ("moral",            "Ethik",        85),
]

# Kombinierte Phrases die Priorität erzwingen
FACH_PHRASES: list[tuple[str, str]] = [
    # (phrase, fach) — exact match hat IMMER Vorrang
    ("satz des pythagoras",    "Mathematik"),
    ("binomischer lehrsatz",   "Mathematik"),
    ("satz von gauss",         "Mathematik"),
    ("zweiter hauptsatz",      "Physik"),
    ("erster hauptsatz",       "Physik"),
    ("ohmsches gesetz",        "Physik"),
    ("mendelsches gesetz",     "Biologie"),
    ("weimarer republik",      "Geschichte"),
    ("zweiter weltkrieg",      "Geschichte"),
    ("erster weltkrieg",       "Geschichte"),
    ("kalter krieg",           "Geschichte"),
    ("satz vom nullprodukt",   "Mathematik"),
    ("relativitätstheorie",    "Physik"),
    ("e=mc",                   "Physik"),
]


# Subject definitions with German curriculum alignment
SUBJECTS = {
    "math": {
        "id": "math",
        "name": "Mathematics",
        "name_de": "Mathematik",
        "icon": "Calculator",
        "description": "Algebra, geometry, calculus, and more",
        "description_de": "Algebra, Geometrie, Analysis und mehr",
        "topics": [
            "Lineare Gleichungen", "Quadratische Funktionen", "Trigonometrie",
            "Wahrscheinlichkeitsrechnung", "Differentialrechnung", "Integralrechnung",
            "Vektoren", "Matrizen", "Geometrie", "Statistik"
        ],
        "keywords": ["equation", "gleichung", "math", "rechne", "formel", "algebra",
                     "geometrie", "integral", "ableitung", "funktion", "graph",
                     "berechne", "solve", "calculate", "x=", "y=", "bruch",
                     "prozent", "vektor", "matrix", "wahrscheinlichkeit", "statistik"]
    },
    "english": {
        "id": "english",
        "name": "English",
        "name_de": "Englisch",
        "icon": "Languages",
        "description": "Grammar, writing, vocabulary, and reading comprehension",
        "description_de": "Grammatik, Schreiben, Vokabeln und Leseverstehen",
        "topics": [
            "Grammar Basics", "Essay Writing", "Vocabulary Building",
            "Reading Comprehension", "Tenses", "Conditional Sentences",
            "Passive Voice", "Reported Speech", "Phrasal Verbs", "Idioms"
        ],
        "keywords": ["english", "englisch", "grammar", "grammatik", "essay",
                     "vocabulary", "vokabel", "translate", "übersetze", "ubersetze", "tense",
                     "verb", "noun", "adjective", "sentence", "writing", "reading",
                     "comprehension", "passive", "active", "conditional"]
    },
    "german": {
        "id": "german",
        "name": "German",
        "name_de": "Deutsch",
        "icon": "BookOpen",
        "description": "Grammar exercises, essay help, Goethe prep",
        "description_de": "Grammatik-Übungen, Aufsatzhilfe, Goethe-Zertifikat",
        "topics": [
            "Grammatik", "Rechtschreibung", "Aufsatz schreiben",
            "Gedichtanalyse", "Erörterung", "Konjunktiv",
            "Relativsätze", "Kommasetzung", "Textanalyse", "Goethe-Zertifikat"
        ],
        "keywords": ["deutsch", "german", "grammatik", "aufsatz", "gedicht",
                     "erörterung", "konjunktiv", "rechtschreibung", "komma",
                     "satz", "text", "analyse", "goethe", "schiller", "literatur",
                     "dativ", "akkusativ", "genitiv", "nominativ"]
    },
    "history": {
        "id": "history",
        "name": "History",
        "name_de": "Geschichte",
        "icon": "Clock",
        "description": "Timelines, source analysis, exam preparation",
        "description_de": "Zeitstrahlen, Quellenanalyse, Prüfungsvorbereitung",
        "topics": [
            "Weimarer Republik", "Nationalsozialismus", "Kalter Krieg",
            "Deutsche Wiedervereinigung", "Französische Revolution",
            "Industrialisierung", "Erster Weltkrieg", "Zweiter Weltkrieg",
            "Römisches Reich", "Mittelalter"
        ],
        "keywords": ["history", "geschichte", "krieg", "revolution", "kaiser",
                     "reich", "epoche", "jahrhundert", "quelle", "quellenanalyse",
                     "timeline", "zeitstrahl", "historisch", "weimar", "nazi",
                     "ddr", "brd", "mauer", "bismarck", "hitler"]
    },
    "physics": {
        "id": "physics",
        "name": "Physics",
        "name_de": "Physik",
        "icon": "Atom",
        "description": "Mechanics, electricity, optics, thermodynamics",
        "description_de": "Mechanik, Elektrizität, Optik, Thermodynamik",
        "topics": [
            "Mechanik", "Elektrizität", "Optik", "Thermodynamik",
            "Kernphysik", "Quantenphysik", "Schwingungen", "Wellen",
            "Magnetismus", "Relativitätstheorie"
        ],
        "keywords": ["physik", "physics", "mechanik", "kraft", "energie",
                     "strom", "spannung", "widerstand", "optik", "linse",
                     "wärme", "newton", "elektron", "proton", "atom",
                     "schwingung", "welle", "magnetismus", "feld"]
    },
    "chemistry": {
        "id": "chemistry",
        "name": "Chemistry",
        "name_de": "Chemie",
        "icon": "FlaskConical",
        "description": "Reactions, periodic table, organic chemistry",
        "description_de": "Reaktionen, Periodensystem, Organische Chemie",
        "topics": [
            "Chemische Reaktionen", "Periodensystem", "Organische Chemie",
            "Säuren und Basen", "Redoxreaktionen", "Elektrochemie",
            "Stöchiometrie", "Atombau", "Bindungen", "Thermochemie"
        ],
        "keywords": ["chemie", "chemistry", "reaktion", "element", "molekül",
                     "periodensystem", "säure", "base", "redox", "organisch",
                     "anorganisch", "atom", "ion", "bindung", "formel"]
    },
    "biology": {
        "id": "biology",
        "name": "Biology",
        "name_de": "Biologie",
        "icon": "Leaf",
        "description": "Cell biology, genetics, evolution, ecology",
        "description_de": "Zellbiologie, Genetik, Evolution, Ökologie",
        "topics": [
            "Zellbiologie", "Genetik", "Evolution", "Ökologie",
            "Neurobiologie", "Stoffwechsel", "Fortpflanzung",
            "Immunbiologie", "Photosynthese", "Mikrobiologie"
        ],
        "keywords": ["biologie", "biology", "zelle", "cell", "gen", "dna",
                     "evolution", "ökologie", "stoffwechsel", "photosynthese",
                     "mitose", "meiose", "neuron", "organ", "gewebe"]
    },
    "geography": {
        "id": "geography",
        "name": "Geography",
        "name_de": "Geographie",
        "icon": "Globe",
        "description": "Physical and human geography, climate, maps",
        "description_de": "Physische Geographie, Humangeographie, Klima, Karten",
        "topics": [
            "Klimazonen", "Plattentektonik", "Bevölkerungsgeographie",
            "Stadtgeographie", "Wirtschaftsgeographie", "Geomorphologie",
            "Nachhaltigkeit", "Globalisierung", "Naturkatastrophen", "Kartographie"
        ],
        "keywords": ["geographie", "geography", "klima", "kontinent", "land",
                     "stadt", "bevölkerung", "karte", "erdkunde", "wetter",
                     "plattentektonik", "vulkan", "erdbeben", "globalisierung"]
    },
    "computer_science": {
        "id": "computer_science",
        "name": "Computer Science",
        "name_de": "Informatik",
        "icon": "Monitor",
        "description": "Programming, algorithms, data structures",
        "description_de": "Programmierung, Algorithmen, Datenstrukturen",
        "topics": [
            "Algorithmen", "Datenstrukturen", "Programmierung",
            "Datenbanken", "Netzwerke", "Kryptographie",
            "Objektorientierung", "Automatentheorie", "Betriebssysteme", "KI-Grundlagen"
        ],
        "keywords": ["informatik", "computer", "programmierung", "algorithmus",
                     "code", "software", "datenbank", "python", "java",
                     "netzwerk", "html", "css", "javascript", "datenstruktur"]
    },
    "art": {
        "id": "art",
        "name": "Art",
        "name_de": "Kunst",
        "icon": "Palette",
        "description": "Art history, techniques, and analysis",
        "description_de": "Kunstgeschichte, Techniken und Analyse",
        "topics": [
            "Kunstgeschichte", "Malerei", "Skulptur", "Grafik-Design",
            "Farbenlehre", "Perspektive", "Renaissance", "Impressionismus",
            "Moderne Kunst", "Fotografie"
        ],
        "keywords": ["kunst", "art", "malerei", "skulptur", "zeichnen",
                     "farbe", "perspektive", "renaissance", "impressionismus",
                     "picasso", "monet", "design", "ästhetik"]
    },
    "music": {
        "id": "music",
        "name": "Music",
        "name_de": "Musik",
        "icon": "Music",
        "description": "Music theory, history, and analysis",
        "description_de": "Musiktheorie, Musikgeschichte und Analyse",
        "topics": [
            "Musiktheorie", "Harmonielehre", "Rhythmik", "Musikgeschichte",
            "Klassik", "Jazz", "Instrumentenkunde", "Gehörbildung",
            "Komposition", "Musikanalyse"
        ],
        "keywords": ["musik", "music", "note", "akkord", "tonleiter",
                     "rhythmus", "melodie", "harmonie", "klassik", "beethoven",
                     "mozart", "instrument", "singen", "komponist"]
    },
    "sports": {
        "id": "sports",
        "name": "Sports Science",
        "name_de": "Sport",
        "icon": "Dumbbell",
        "description": "Sports theory, training science, movement",
        "description_de": "Sporttheorie, Trainingslehre, Bewegungslehre",
        "topics": [
            "Trainingslehre", "Bewegungslehre", "Sportbiologie",
            "Sportpsychologie", "Doping", "Ernährung im Sport",
            "Ausdauer", "Kraft", "Koordination", "Fairplay"
        ],
        "keywords": ["sport", "training", "fitness", "bewegung", "ausdauer",
                     "kraft", "koordination", "doping", "ernährung", "muskel",
                     "sporttheorie", "olympia"]
    },
    "economics": {
        "id": "economics",
        "name": "Economics",
        "name_de": "Wirtschaft",
        "icon": "TrendingUp",
        "description": "Micro/macroeconomics, business, markets",
        "description_de": "Mikro-/Makroökonomie, BWL, Märkte",
        "topics": [
            "Angebot und Nachfrage", "Marktformen", "Konjunktur",
            "Geldpolitik", "Globalisierung", "Unternehmensformen",
            "Marketing", "Buchführung", "Steuern", "Sozialversicherung"
        ],
        "keywords": ["wirtschaft", "economics", "markt", "angebot", "nachfrage",
                     "konjunktur", "inflation", "bip", "unternehmen", "aktie",
                     "börse", "handel", "geld", "bank", "steuern"]
    },
    "politics": {
        "id": "politics",
        "name": "Political Science",
        "name_de": "Politik",
        "icon": "Landmark",
        "description": "Political systems, democracy, international relations",
        "description_de": "Politische Systeme, Demokratie, Internationale Beziehungen",
        "topics": [
            "Grundgesetz", "Demokratie", "Parteien", "Wahlen",
            "Europäische Union", "Vereinte Nationen", "Menschenrechte",
            "Gewaltenteilung", "Föderalismus", "Politische Theorien"
        ],
        "keywords": ["politik", "politics", "demokratie", "partei", "wahl",
                     "bundestag", "regierung", "grundgesetz", "eu", "nato",
                     "menschenrechte", "staat", "verfassung", "gesetz"]
    },
    "latin": {
        "id": "latin",
        "name": "Latin",
        "name_de": "Latein",
        "icon": "BookMarked",
        "description": "Latin grammar, translation, Roman culture",
        "description_de": "Lateinische Grammatik, Übersetzung, Römische Kultur",
        "topics": [
            "Deklinationen", "Konjugationen", "AcI", "Ablativus Absolutus",
            "Cicero", "Caesar", "Ovid", "Metrik",
            "Römische Geschichte", "Stilmittel"
        ],
        "keywords": ["latein", "latin", "deklination", "konjugation", "aci",
                     "ablativ", "cicero", "caesar", "ovid", "vokabel",
                     "übersetze", "übersetzung", "rom", "römisch", "grammatik"]
    },
    "french": {
        "id": "french",
        "name": "French",
        "name_de": "Französisch",
        "icon": "Languages",
        "description": "French grammar, vocabulary, culture",
        "description_de": "Französische Grammatik, Vokabeln, Kultur",
        "topics": [
            "Grammatik", "Vokabeln", "Textverständnis", "Aufsatz",
            "Passé composé", "Subjonctif", "Pronomen",
            "Französische Literatur", "Landeskunde", "DELF-Vorbereitung"
        ],
        "keywords": ["französisch", "french", "france", "francais", "grammaire",
                     "vokabel", "passé", "subjonctif", "texte", "delf",
                     "paris", "übersetze", "frankreich"]
    },
    "science": {
        "id": "science",
        "name": "Science",
        "name_de": "Naturwissenschaften",
        "icon": "FlaskConical",
        "description": "Physics, Chemistry, Biology concepts and experiments",
        "description_de": "Physik, Chemie, Bio Konzepte und Experimente",
        "topics": [
            "Mechanik", "Elektrizität", "Optik", "Thermodynamik",
            "Chemische Reaktionen", "Periodensystem", "Organische Chemie",
            "Zellbiologie", "Genetik", "Evolution"
        ],
        "keywords": ["physik", "physics", "chemie", "chemistry", "biologie",
                     "biology", "atom", "molekül", "energie", "kraft", "experiment",
                     "reaktion", "element", "zelle", "cell", "gen", "evolution",
                     "elektron", "proton", "newton", "formel", "labor"]
    }
}


def detect_subject(message: str, user_fach: str | None = None) -> str:
    """Intelligente Fach-Erkennung mit Prioritäts-Scoring.

    1. Wenn User explizit ein Fach gesetzt hat → nutze das
    2. Phrase-Matching (exakte Zusammensetzungen haben Vorrang)
    3. Keyword-Scoring (höchste Priorität gewinnt)
    """
    # User hat ein Fach explizit gewählt → IMMER respektieren
    # Return raw value; caller normalizes separately for DB storage
    if user_fach and user_fach not in ("", "Alle", "Allgemein", "general"):
        return user_fach

    text_lower = message.lower()

    # Schritt 1: Exakte Phrase-Matches (höchste Priorität)
    for phrase, fach in FACH_PHRASES:
        if phrase in text_lower:
            return fach

    # Schritt 2: Keyword-Scoring
    scores: dict[str, int] = {}
    for keyword, fach, prio in FACH_KEYWORDS:
        if keyword in text_lower:
            scores[fach] = scores.get(fach, 0) + prio

    if not scores:
        return "Allgemein"

    # Höchster Score gewinnt
    bestes_fach = max(scores, key=lambda f: scores[f])

    # Tie-Breaker: Mindest-Score-Differenz von 30
    sortiert = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if len(sortiert) >= 2:
        differenz = sortiert[0][1] - sortiert[1][1]
        if differenz < 30 and user_fach:
            return normalize_fach(user_fach)

    return bestes_fach


def get_proficiency_prompt(level: str, language: str = "de") -> str:
    """Get explanation style based on proficiency level."""
    if language == "de":
        prompts = {
            "beginner": (
                "Erkläre es so einfach wie möglich. Benutze Analogien und Alltagsbeispiele. "
                "Vermeide Fachbegriffe oder erkläre sie sofort. Gehe Schritt für Schritt vor. "
                "Stell dir vor, du erklärst es einem Schüler der 5. Klasse."
            ),
            "intermediate": (
                "Erkläre es auf einem mittleren Niveau. Verwende Fachbegriffe mit kurzen Erklärungen. "
                "Zeige die Lösung in 3-5 klaren Schritten. Gib ein Beispiel."
            ),
            "advanced": (
                "Erkläre es auf einem fortgeschrittenen Niveau. Verwende Fachsprache frei. "
                "Zeige detaillierte Beweise und Herleitungen. Verweise auf weiterführende Konzepte. "
                "Nutze mathematische Notation wo angebracht."
            )
        }
    else:
        prompts = {
            "beginner": (
                "Explain as simply as possible. Use analogies and everyday examples. "
                "Avoid technical terms or explain them immediately. Go step by step. "
                "Imagine explaining to a 5th grader."
            ),
            "intermediate": (
                "Explain at an intermediate level. Use technical terms with brief explanations. "
                "Show the solution in 3-5 clear steps. Give an example."
            ),
            "advanced": (
                "Explain at an advanced level. Use technical language freely. "
                "Show detailed proofs and derivations. Reference advanced concepts. "
                "Use mathematical notation where appropriate."
            )
        }
    return prompts.get(level, prompts["intermediate"])


def build_system_prompt(subject: str, level: str, language: str = "de", detail_level: str = "normal",
                        user_name: str = "", klasse: str = "10", schultyp: str = "Gymnasium",
                        bundesland: str = "", tutor_modus: bool = False, web_quellen: str = "",
                        personality_name: str = "max") -> str:
    """Build the LUMNOS System Prompt using FINAL_SYSTEM_PROMPT + personality addon.

    Uses the verbatim FINAL_SYSTEM_PROMPT as core, with dynamic context
    (Fach, Klasse, Bundesland) and personality addons injected.
    """
    # Fach normalisieren BEVOR es verwendet wird
    subject = normalize_fach(subject) if subject else "Allgemein"
    subject_info = SUBJECTS.get(subject, {})
    subject_name = subject_info.get("name_de", subject) if language == "de" else subject_info.get("name", subject)

    # Bundesland-spezifischer Kontext
    bundesland_info = {
        "Bayern": "Bayern (G9, LehrplanPLUS)",
        "NRW": "NRW (Zentralabitur, Kernlehrpläne MSB)",
        "Baden-Württemberg": "Baden-Württemberg (Bildungsplan 2016)",
        "Berlin": "Berlin (Rahmenlehrplan)",
        "Hamburg": "Hamburg (Bildungsplan, Abitur zentral)",
        "Hessen": "Hessen (Kerncurriculum, Zentralabitur)",
        "Niedersachsen": "Niedersachsen (Kerncurriculum)",
        "Sachsen": "Sachsen (Lehrplan, Zentralabitur)",
        "Thüringen": "Thüringen (Lehrplan, Zentralabitur)",
        "Brandenburg": "Brandenburg (Rahmenlehrplan)",
        "Schleswig-Holstein": "Schleswig-Holstein (Fachanforderungen)",
        "Rheinland-Pfalz": "Rheinland-Pfalz (Lehrpläne)",
        "Saarland": "Saarland (Lehrpläne, Zentralabitur)",
        "Sachsen-Anhalt": "Sachsen-Anhalt (Fachlehrpläne)",
        "Mecklenburg-Vorpommern": "Mecklenburg-Vorpommern (Rahmenplan)",
        "Bremen": "Bremen (Bildungsplan)",
    }.get(bundesland or "", f"{bundesland or 'Deutschland'} (Nationaler Lehrplan)")

    # Detail-Level Modifier
    detail_modifier = ""
    if detail_level == "simpler":
        detail_modifier = "\n\nWICHTIG: Erkläre es VIEL einfacher. Kurze Sätze, Alltagsbeispiele, als würdest du es einem Freund erklären."
    elif detail_level == "detailed":
        detail_modifier = "\n\nWICHTIG: Gib MEHR Details mit zusätzlichen Beispielen, Herleitungen und Querverweisen zu verwandten Themen."

    # Web-Quellen Block
    quellen_block = ""
    if web_quellen:
        quellen_block = f"""
VERIFIZIERTE QUELLEN AUS ECHTZEIT-SUCHE:
{web_quellen}
Du MUSST diese Fakten nutzen und mit [1], [2] etc. zitieren.
Zitationen NUR am Satzende, NIEMALS mitten im Satz!"""

    # Persönlichkeits-Addon auswählen
    p_key = (personality_name or "max").lower().strip()
    personality_addon = PERSOENLICHKEITS_ADDONS.get(p_key, "")

    if language == "de":
        # Dynamischer Kontext-Block
        kontext = f"""
DEIN KONTEXT:
- Fachgebiet: {subject_name}
- Schüler: {user_name or 'Schüler'}, {klasse}. Klasse, {schultyp}
- Lehrplan: {bundesland_info}
"""
        return FINAL_SYSTEM_PROMPT + kontext + personality_addon + detail_modifier + quellen_block
    else:
        return f"""You are LUMNOS — Germany's most elite AI learning platform.
You are a pedagogical mentor, not a solution machine.

# YOUR PROFILE
- Subject: {subject_name}
- Student level: {level} | Grade: {klasse}
- Context: {schultyp}, {bundesland_info}

# RULES (NEVER BREAK)
1. DIRECT ANSWERS: Answer concrete questions immediately — no generic overviews
2. STEP BY STEP for calculations, using LaTeX: $formula$
3. Always end complex explanations with a practice problem
4. Never make the student feel bad about mistakes
5. Use <thinking>...</thinking> tags before answering (hidden from student)
6. Adaptive length: short answers for simple questions, detailed for complex ones
{detail_modifier}"""


def generate_ai_response(
    message: str,
    subject: str,
    level: str,
    language: str = "de",
    detail_level: str = "normal",
    chat_history: list = None,
) -> str:
    """Generate an AI response using built-in knowledge.

    This is the fallback engine that generates high-quality educational responses
    without requiring an external API. When a GROQ_API_KEY is configured,
    the route handler will use the Groq API instead.
    """
    detected = detect_subject(message) if subject == "general" else subject
    msg_lower = message.lower()

    # Generate subject-specific responses
    if detected == "math":
        return _generate_math_response(message, level, language)
    elif detected == "english":
        return _generate_english_response(message, level, language)
    elif detected == "german":
        return _generate_german_response(message, level, language)
    elif detected == "history":
        return _generate_history_response(message, level, language)
    elif detected == "science":
        return _generate_science_response(message, level, language)
    else:
        return _generate_general_response(message, level, language)


def _generate_math_response(message: str, level: str, language: str) -> str:
    msg = message.lower()
    if language == "de":
        if any(w in msg for w in ["gleichung", "löse", "solve", "x="]):
            return """## Gleichungen lösen - Schritt für Schritt

Ich helfe dir gerne bei Gleichungen! Hier ist die allgemeine Vorgehensweise:

### Lineare Gleichungen (ax + b = c)
1. **Vereinfache** beide Seiten der Gleichung
2. **Bringe** alle Terme mit x auf eine Seite
3. **Bringe** alle Zahlen auf die andere Seite
4. **Teile** durch den Koeffizienten von x

### Beispiel:
$$3x + 7 = 22$$

**Schritt 1:** Subtrahiere 7 von beiden Seiten
$$3x = 22 - 7 = 15$$

**Schritt 2:** Teile durch 3
$$x = \\frac{15}{3} = 5$$

**Probe:** $3 \\cdot 5 + 7 = 15 + 7 = 22$ ✓

Schick mir deine spezifische Gleichung, und ich löse sie Schritt für Schritt!

**Übungsaufgabe:** Löse $5x - 3 = 2x + 12$"""
        elif any(w in msg for w in ["ableitung", "differenz", "derivative"]):
            return """## Differentialrechnung - Ableitungen

Die Ableitung einer Funktion $f(x)$ gibt die **Steigung** der Funktion an jedem Punkt an.

### Grundregeln:
| Funktion | Ableitung |
|----------|-----------|
| $f(x) = x^n$ | $f'(x) = n \\cdot x^{n-1}$ |
| $f(x) = e^x$ | $f'(x) = e^x$ |
| $f(x) = \\sin(x)$ | $f'(x) = \\cos(x)$ |
| $f(x) = \\ln(x)$ | $f'(x) = \\frac{1}{x}$ |

### Beispiel:
$$f(x) = 3x^4 - 2x^2 + 5x - 1$$

**Schritt 1:** Wende die Potenzregel auf jeden Term an:
$$f'(x) = 12x^3 - 4x + 5$$

Gib mir eine Funktion, und ich leite sie für dich ab!

**Übungsaufgabe:** Bestimme $f'(x)$ für $f(x) = x^3 + 4x^2 - 7x + 2$"""
        else:
            return """## Mathematik-Hilfe

Ich bin dein Mathe-Tutor! Ich kann dir helfen bei:

- **Algebra:** Gleichungen, Ungleichungen, Funktionen
- **Geometrie:** Flächen, Volumen, Trigonometrie
- **Analysis:** Ableitungen, Integrale, Kurvendiskussion
- **Stochastik:** Wahrscheinlichkeit, Statistik
- **Lineare Algebra:** Vektoren, Matrizen

Stelle mir eine konkrete Mathe-Frage, und ich erkläre dir den Lösungsweg Schritt für Schritt!

**Tipp:** Je genauer deine Frage, desto besser kann ich dir helfen. Z.B. "Löse die Gleichung 2x + 5 = 13" oder "Erkläre den Satz des Pythagoras"."""
    else:
        return """## Mathematics Help

I'm your math tutor! I can help with:

- **Algebra:** Equations, inequalities, functions
- **Geometry:** Areas, volumes, trigonometry
- **Calculus:** Derivatives, integrals, curve analysis
- **Statistics:** Probability, data analysis
- **Linear Algebra:** Vectors, matrices

Ask me a specific math question and I'll explain the solution step by step!

**Tip:** The more specific your question, the better I can help. E.g. "Solve 2x + 5 = 13" or "Explain the Pythagorean theorem"."""


def _generate_english_response(message: str, level: str, language: str) -> str:
    msg = message.lower()
    if language == "de":
        if any(w in msg for w in ["grammar", "grammatik", "tense", "zeit"]):
            return """## Englische Grammatik

### Die wichtigsten Zeitformen (Tenses):

| Zeitform | Beispiel | Verwendung |
|----------|----------|------------|
| **Simple Present** | *I play* | Gewohnheiten, Fakten |
| **Present Progressive** | *I am playing* | Gerade jetzt passierend |
| **Simple Past** | *I played* | Abgeschlossene Vergangenheit |
| **Present Perfect** | *I have played* | Vergangenheit mit Bezug zur Gegenwart |
| **Past Perfect** | *I had played* | Vorvergangenheit |
| **Will-Future** | *I will play* | Zukunft (spontan, Vorhersage) |
| **Going-to-Future** | *I am going to play* | Geplante Zukunft |

### Signalwörter helfen dir:
- **Simple Present:** always, usually, every day
- **Present Perfect:** already, yet, since, for
- **Simple Past:** yesterday, last week, ago

**Übungsaufgabe:** Setze das richtige Verb ein: "She ___ (go) to school every day."
"""
        else:
            return """## Englisch-Hilfe

Ich helfe dir gerne mit Englisch! Meine Spezialgebiete:

- **Grammatik:** Zeitformen, Satzbau, Passiv, Conditional
- **Schreiben:** Essays, Briefe, Zusammenfassungen
- **Vokabeln:** Wortschatz erweitern, Redewendungen
- **Leseverstehen:** Texte analysieren und verstehen
- **Goethe-Zertifikat / Abitur Vorbereitung**

Stelle mir eine Frage auf Deutsch oder Englisch!

**Übung:** Übersetze: "Ich bin seit drei Jahren in dieser Schule."
"""
    else:
        return """## English Help

I can help you with English! My specialties include:

- **Grammar:** Tenses, sentence structure, passive voice, conditionals
- **Writing:** Essays, letters, summaries
- **Vocabulary:** Expanding word knowledge, idioms
- **Reading Comprehension:** Text analysis
- **Abitur Preparation**

Ask me any English question!

**Practice:** Correct this sentence: "She have went to the store yesterday."
"""


def _generate_german_response(message: str, level: str, language: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ["kasus", "dativ", "akkusativ", "genitiv", "nominativ", "fall", "fälle"]):
        return """## Die vier Fälle (Kasus) im Deutschen

| Kasus | Frage | Artikel (m/f/n/pl) | Beispiel |
|-------|-------|---------------------|----------|
| **Nominativ** | Wer/Was? | der/die/das/die | **Der Hund** bellt. |
| **Genitiv** | Wessen? | des/der/des/der | Das Haus **des Mannes** |
| **Dativ** | Wem? | dem/der/dem/den | Ich gebe **dem Kind** ein Buch. |
| **Akkusativ** | Wen/Was? | den/die/das/die | Ich sehe **den Baum**. |

### Merksatz:
> "Der, des, dem, den - wer das nicht kann, ist dumm."

### Präpositionen und ihre Fälle:
- **Dativ:** aus, bei, mit, nach, seit, von, zu
- **Akkusativ:** durch, für, gegen, ohne, um
- **Wechselpräpositionen:** an, auf, hinter, in, neben, über, unter, vor, zwischen

**Übungsaufgabe:** Bestimme den Kasus: "Ich schenke meiner Schwester einen Ring."
"""
    elif any(w in msg for w in ["aufsatz", "erörterung", "essay", "schreiben"]):
        return """## Einen Aufsatz schreiben - Schritt für Schritt

### Aufbau einer Erörterung:

**1. Einleitung (ca. 10%)**
- Aktuellen Bezug herstellen
- Fragestellung vorstellen
- Interesse wecken

**2. Hauptteil (ca. 80%)**
- **Pro-Argumente** (vom schwächsten zum stärksten)
- **Contra-Argumente** (vom schwächsten zum stärksten)
- Jedes Argument: These → Begründung → Beispiel

**3. Schluss (ca. 10%)**
- Eigene Meinung formulieren
- Ausblick geben

### Nützliche Formulierungen:
| Funktion | Formulierung |
|----------|-------------|
| Einleitung | "In der heutigen Zeit wird häufig diskutiert..." |
| Pro | "Ein wichtiges Argument dafür ist..." |
| Contra | "Demgegenüber steht jedoch..." |
| Schluss | "Abschließend lässt sich sagen..." |

**Übungsaufgabe:** Schreibe eine Einleitung zum Thema "Sollte Handynutzung in der Schule erlaubt sein?"
"""
    else:
        return """## Deutsch-Hilfe

Willkommen! Ich helfe dir bei allem rund um das Fach Deutsch:

- **Grammatik:** Kasus, Konjunktiv, Satzglieder, Kommasetzung
- **Rechtschreibung:** Regeln und Übungen
- **Aufsätze:** Erörterung, Inhaltsangabe, Interpretation
- **Literatur:** Gedichtanalyse, Dramenanalyse, Epochen
- **Goethe-Zertifikat Vorbereitung**

Stelle mir eine Frage, und ich helfe dir gerne!

**Übung:** Korrigiere den folgenden Satz: "Das Mädchen, dass gestern hier war haben mir geholfen."
"""


def _generate_history_response(message: str, level: str, language: str) -> str:
    msg = message.lower()
    if language == "de":
        if any(w in msg for w in ["weimar", "republik", "1918", "1919", "1933"]):
            return """## Die Weimarer Republik (1918-1933)

### Zeitstrahl:
```
1918 ─── Novemberrevolution, Ende des Kaiserreichs
1919 ─── Weimarer Verfassung, Versailler Vertrag
1920 ─── Kapp-Putsch
1923 ─── Hyperinflation, Hitlerputsch
1924 ─── Dawes-Plan, Beginn der "Goldenen Zwanziger"
1929 ─── Weltwirtschaftskrise (Schwarzer Freitag)
1930 ─── Aufstieg der NSDAP
1933 ─── Machtergreifung Hitlers, Ende der Republik
```

### Hauptprobleme:
1. **Dolchstoßlegende** - Belastung von Anfang an
2. **Versailler Vertrag** - Reparationen und Gebietsabtretungen
3. **Politische Instabilität** - Viele Regierungswechsel
4. **Wirtschaftskrisen** - Hyperinflation 1923, Weltwirtschaftskrise 1929
5. **Antidemokratische Kräfte** - von links (KPD) und rechts (NSDAP)

### Quellenanalyse-Tipp:
Achte bei Quellen aus dieser Zeit immer auf:
- **Verfasser** und dessen politische Einstellung
- **Entstehungszeit** (Krise oder Stabilität?)
- **Adressat** (An wen richtet sich der Text?)

**Übungsaufgabe:** Erkläre, warum die Weltwirtschaftskrise 1929 zum Aufstieg der NSDAP beigetragen hat.
"""
        else:
            return """## Geschichte-Hilfe

Ich helfe dir bei Geschichte! Meine Themengebiete:

- **Antike:** Römisches Reich, Griechische Demokratie
- **Mittelalter:** Feudalismus, Kreuzzüge
- **Neuzeit:** Französische Revolution, Industrialisierung
- **20. Jahrhundert:** Erster & Zweiter Weltkrieg, Weimarer Republik
- **Deutsche Geschichte:** Wiedervereinigung, Kalter Krieg, DDR/BRD

### Was ich kann:
- Zeitstrahlen erstellen
- Quellenanalysen durchführen
- Ereignisse zusammenfassen
- Prüfungsvorbereitung (Abitur)

Stelle mir eine Frage zu einem historischen Thema!

**Übung:** Nenne drei Ursachen des Ersten Weltkriegs.
"""
    else:
        return """## History Help

I can help you with History! Topics include:

- **Ancient History:** Roman Empire, Greek Democracy
- **Middle Ages:** Feudalism, Crusades
- **Modern Era:** French Revolution, Industrial Revolution
- **20th Century:** World Wars, Weimar Republic
- **German History:** Reunification, Cold War

Ask me about any historical topic!

**Practice:** Name three causes of World War I.
"""


def _generate_science_response(message: str, level: str, language: str) -> str:
    msg = message.lower()
    if language == "de":
        if any(w in msg for w in ["physik", "kraft", "newton", "energie", "mechanik"]):
            return """## Physik - Mechanik Grundlagen

### Newtonsche Gesetze:

**1. Trägheitsgesetz:**
> Ein Körper bleibt in Ruhe oder bewegt sich gleichförmig, solange keine äußere Kraft wirkt.

**2. Aktionsprinzip:**
$$F = m \\cdot a$$
- $F$ = Kraft (in Newton, N)
- $m$ = Masse (in kg)
- $a$ = Beschleunigung (in m/s²)

**3. Wechselwirkungsprinzip:**
> Actio = Reactio (Kraft = Gegenkraft)

### Beispielrechnung:
Ein Auto (m = 1000 kg) beschleunigt mit $a = 3 \\frac{m}{s^2}$.
$$F = 1000 \\, kg \\cdot 3 \\, \\frac{m}{s^2} = 3000 \\, N = 3 \\, kN$$

### Wichtige Formeln:
| Größe | Formel | Einheit |
|-------|--------|---------|
| Geschwindigkeit | $v = \\frac{s}{t}$ | m/s |
| Beschleunigung | $a = \\frac{\\Delta v}{\\Delta t}$ | m/s² |
| Kraft | $F = m \\cdot a$ | N |
| Arbeit | $W = F \\cdot s$ | J |

**Übungsaufgabe:** Berechne die Kraft, die nötig ist, um einen 50 kg schweren Koffer mit $2 \\frac{m}{s^2}$ zu beschleunigen.
"""
        elif any(w in msg for w in ["chemie", "reaktion", "element", "periodensystem", "atom"]):
            return """## Chemie - Grundlagen

### Das Periodensystem:
Die Elemente sind nach **Ordnungszahl** (Protonenzahl) sortiert.

### Wichtige Konzepte:

**Atombau:**
- **Protonen** (p⁺) - im Kern, positiv geladen
- **Neutronen** (n⁰) - im Kern, neutral
- **Elektronen** (e⁻) - in der Hülle, negativ geladen

**Chemische Bindungen:**
| Typ | Beschreibung | Beispiel |
|-----|-------------|---------|
| Ionenbindung | Elektron-Übertragung | NaCl |
| Kovalente Bindung | Elektron-Teilung | H₂O |
| Metallische Bindung | Elektronengas | Fe |

**Beispielreaktion:**
$$2H_2 + O_2 \\rightarrow 2H_2O$$
*Zwei Moleküle Wasserstoff reagieren mit einem Molekül Sauerstoff zu zwei Molekülen Wasser.*

**Übungsaufgabe:** Gleiche die folgende Reaktionsgleichung aus: $Fe + O_2 \\rightarrow Fe_2O_3$
"""
        else:
            return """## Naturwissenschaften-Hilfe

Ich helfe dir bei Naturwissenschaften! Bereiche:

- **Physik:** Mechanik, Elektrizität, Optik, Thermodynamik
- **Chemie:** Atombau, Reaktionen, Periodensystem, Organische Chemie
- **Biologie:** Zellbiologie, Genetik, Ökologie, Evolution

### Was ich kann:
- Formeln herleiten und erklären
- Experimente beschreiben
- Diagramme und Konzepte erklären
- Abitur-Vorbereitung

Stelle mir eine Frage!

**Übung:** Erkläre den Unterschied zwischen Mitose und Meiose.
"""
    else:
        return """## Science Help

I can help with Science! Areas include:

- **Physics:** Mechanics, Electricity, Optics, Thermodynamics
- **Chemistry:** Atomic structure, Reactions, Periodic table
- **Biology:** Cell biology, Genetics, Ecology, Evolution

Ask me any science question!

**Practice:** Explain the difference between mitosis and meiosis.
"""


def _generate_general_response(message: str, level: str, language: str) -> str:
    if language == "de":
        return f"""Hallo! Ich bin **Lumnos**, dein persönlicher KI-Tutor!

Ich kann dir bei folgenden Fächern helfen:

| Fach | Themen |
|------|--------|
| **Mathematik** | Gleichungen, Geometrie, Analysis, Stochastik |
| **Englisch** | Grammatik, Essay-Schreiben, Vokabeln |
| **Deutsch** | Grammatik, Aufsätze, Literaturanalyse |
| **Geschichte** | Quellenanalyse, Zeitstrahlen, Prüfungsvorbereitung |
| **Naturwissenschaften** | Physik, Chemie, Biologie |

Wähle ein Fach aus oder stelle mir einfach eine Frage - ich erkenne automatisch, um welches Fach es geht!

**Tipp:** Du kannst jederzeit "Erkläre einfacher" oder "Mehr Details" sagen, um die Erklärung anzupassen.
"""
    else:
        return f"""Hello! I'm **Lumnos**, your personal AI tutor!

I can help you with the following subjects:

| Subject | Topics |
|---------|--------|
| **Mathematics** | Equations, Geometry, Calculus, Statistics |
| **English** | Grammar, Essay Writing, Vocabulary |
| **German** | Grammar, Essays, Literature Analysis |
| **History** | Source Analysis, Timelines, Exam Prep |
| **Science** | Physics, Chemistry, Biology |

Select a subject or just ask me a question - I'll automatically detect the subject!

**Tip:** You can always say "Explain simpler" or "More details" to adjust the explanation.
"""


def generate_quiz(
    subject: str,
    difficulty: str = "intermediate",
    num_questions: int = 5,
    quiz_type: str = "mcq",
    language: str = "de",
    topic: str = None,
    extra_prompt: str = "",
) -> list:
    """Generate quiz questions for a subject."""
    # Bug-Fix 4: Fach-Routing — map German subject names to quiz bank keys
    _FACH_TO_QUIZ_KEY: dict[str, str] = {
        "Mathematik": "math", "Mathe": "math",
        "Englisch": "english",
        "Deutsch": "german",
        "Geschichte": "history",
        "Physik": "science", "Biologie": "science", "Chemie": "science",
        "Naturwissenschaften": "science",
        # All other subjects fall back to the closest match or general
        "Ethik": "history", "Philosophie": "history", "Politik": "history",
        "Geografie": "science", "Geographie": "science",
        "Informatik": "math",
        "Französisch": "german", "Spanisch": "german", "Latein": "german",
        "Italienisch": "german", "Russisch": "german", "Türkisch": "german",
        "Altgriechisch": "german",
        "Wirtschaft": "history",
        "Kunst": "history", "Musik": "history",
        "Sport": "science",
        "Astronomie": "science",
        "Psychologie": "science",
        "Pädagogik": "history",
        "Sozialkunde": "history",
        "Ernährungslehre": "science",
    }
    quiz_key = _FACH_TO_QUIZ_KEY.get(subject, subject.lower())

    quizzes = {
        "math": {
            "beginner": [
                {"question": "Was ist 15 + 27?" if language == "de" else "What is 15 + 27?",
                 "options": ["42", "43", "41", "52"], "correct_answer": "42",
                 "explanation": "15 + 27 = 42", "topic": "Grundrechenarten"},
                {"question": "Löse: x + 5 = 12" if language == "de" else "Solve: x + 5 = 12",
                 "options": ["x = 7", "x = 17", "x = 5", "x = 8"], "correct_answer": "x = 7",
                 "explanation": "x = 12 - 5 = 7", "topic": "Lineare Gleichungen"},
                {"question": "Wie viel ist 3 × 8?" if language == "de" else "What is 3 × 8?",
                 "options": ["24", "21", "27", "18"], "correct_answer": "24",
                 "explanation": "3 × 8 = 24", "topic": "Grundrechenarten"},
                {"question": "Was ist 1/2 + 1/4?" if language == "de" else "What is 1/2 + 1/4?",
                 "options": ["3/4", "2/6", "1/6", "2/4"], "correct_answer": "3/4",
                 "explanation": "1/2 = 2/4, also 2/4 + 1/4 = 3/4", "topic": "Bruchrechnung"},
                {"question": "Berechne: 100 - 37" if language == "de" else "Calculate: 100 - 37",
                 "options": ["63", "67", "73", "53"], "correct_answer": "63",
                 "explanation": "100 - 37 = 63", "topic": "Grundrechenarten"},
            ],
            "intermediate": [
                {"question": "Löse: 2x² - 8 = 0" if language == "de" else "Solve: 2x² - 8 = 0",
                 "options": ["x = ±2", "x = ±4", "x = 2", "x = 4"], "correct_answer": "x = ±2",
                 "explanation": "2x² = 8 → x² = 4 → x = ±2", "topic": "Quadratische Gleichungen"},
                {"question": "Was ist die Ableitung von f(x) = 3x²?" if language == "de" else "What is the derivative of f(x) = 3x²?",
                 "options": ["f'(x) = 6x", "f'(x) = 3x", "f'(x) = 6x²", "f'(x) = 6"], "correct_answer": "f'(x) = 6x",
                 "explanation": "Potenzregel: f'(x) = 2·3·x¹ = 6x", "topic": "Differentialrechnung"},
                {"question": "sin(30°) = ?" if language == "de" else "sin(30°) = ?",
                 "options": ["0.5", "1", "√3/2", "√2/2"], "correct_answer": "0.5",
                 "explanation": "sin(30°) = 1/2 = 0.5", "topic": "Trigonometrie"},
                {"question": "Was ist der Flächeninhalt eines Kreises mit r = 5?" if language == "de" else "What is the area of a circle with r = 5?",
                 "options": ["25π", "10π", "5π", "50π"], "correct_answer": "25π",
                 "explanation": "A = πr² = π·5² = 25π", "topic": "Geometrie"},
                {"question": "Vereinfache: (x+3)(x-3)" if language == "de" else "Simplify: (x+3)(x-3)",
                 "options": ["x²-9", "x²+9", "x²-6x+9", "x²+6"], "correct_answer": "x²-9",
                 "explanation": "3. Binomische Formel: (a+b)(a-b) = a²-b²", "topic": "Algebra"},
            ],
            "advanced": [
                {"question": "∫ 2x·eˣ² dx = ?" if language == "de" else "∫ 2x·eˣ² dx = ?",
                 "options": ["eˣ² + C", "2eˣ² + C", "x²eˣ² + C", "eˣ + C"], "correct_answer": "eˣ² + C",
                 "explanation": "Substitution: u = x², du = 2x dx → ∫eᵘ du = eᵘ + C", "topic": "Integralrechnung"},
                {"question": "lim(x→0) sin(x)/x = ?" if language == "de" else "lim(x→0) sin(x)/x = ?",
                 "options": ["1", "0", "∞", "undefined"], "correct_answer": "1",
                 "explanation": "Fundamentaler Grenzwert der Analysis", "topic": "Grenzwerte"},
                {"question": "Determinante von [[1,2],[3,4]] = ?" if language == "de" else "Determinant of [[1,2],[3,4]] = ?",
                 "options": ["-2", "2", "10", "-10"], "correct_answer": "-2",
                 "explanation": "det = 1·4 - 2·3 = 4 - 6 = -2", "topic": "Lineare Algebra"},
                {"question": "Was ist die Ableitung von ln(sin(x))?" if language == "de" else "Derivative of ln(sin(x))?",
                 "options": ["cot(x)", "1/sin(x)", "cos(x)/sin(x)", "tan(x)"], "correct_answer": "cot(x)",
                 "explanation": "Kettenregel: cos(x)/sin(x) = cot(x)", "topic": "Differentialrechnung"},
                {"question": "P(A∪B) wenn P(A)=0.3, P(B)=0.5, P(A∩B)=0.1?" if language == "de" else "P(A∪B) if P(A)=0.3, P(B)=0.5, P(A∩B)=0.1?",
                 "options": ["0.7", "0.8", "0.9", "0.6"], "correct_answer": "0.7",
                 "explanation": "P(A∪B) = P(A) + P(B) - P(A∩B) = 0.3 + 0.5 - 0.1 = 0.7", "topic": "Stochastik"},
            ]
        },
        "english": {
            "beginner": [
                {"question": "Choose the correct form: She ___ to school every day.", "options": ["goes", "go", "going", "gone"], "correct_answer": "goes", "explanation": "Third person singular requires -s ending in Simple Present", "topic": "Simple Present"},
                {"question": "Which is correct?", "options": ["I am happy.", "I is happy.", "I be happy.", "I are happy."], "correct_answer": "I am happy.", "explanation": "'I' always pairs with 'am' in Present tense", "topic": "To Be"},
                {"question": "Past tense of 'go':", "options": ["went", "goed", "goned", "goes"], "correct_answer": "went", "explanation": "'Go' is irregular: go → went → gone", "topic": "Irregular Verbs"},
                {"question": "Choose: There ___ many students.", "options": ["are", "is", "am", "be"], "correct_answer": "are", "explanation": "Plural subjects use 'are'", "topic": "Subject-Verb Agreement"},
                {"question": "Which is a noun?", "options": ["happiness", "happy", "happily", "happier"], "correct_answer": "happiness", "explanation": "-ness makes adjectives into nouns", "topic": "Word Classes"},
            ],
            "intermediate": [
                {"question": "If I ___ rich, I would travel the world.", "options": ["were", "was", "am", "be"], "correct_answer": "were", "explanation": "Conditional II uses 'were' for all persons (subjunctive)", "topic": "Conditional Sentences"},
                {"question": "The book ___ by J.K. Rowling.", "options": ["was written", "wrote", "has wrote", "writing"], "correct_answer": "was written", "explanation": "Passive Voice: was/were + past participle", "topic": "Passive Voice"},
                {"question": "She said she ___ tired.", "options": ["was", "is", "were", "be"], "correct_answer": "was", "explanation": "Reported Speech: tense shifts back (is → was)", "topic": "Reported Speech"},
                {"question": "I have been working here ___ 2019.", "options": ["since", "for", "from", "at"], "correct_answer": "since", "explanation": "'Since' for specific point in time, 'for' for duration", "topic": "Present Perfect"},
                {"question": "Which is correct?", "options": ["Neither John nor Mary was there.", "Neither John nor Mary were there.", "Neither John or Mary was there.", "Neither John nor Mary is there."], "correct_answer": "Neither John nor Mary was there.", "explanation": "Neither...nor takes singular verb when nearest subject is singular", "topic": "Correlative Conjunctions"},
            ],
            "advanced": [
                {"question": "Had I known, I ___ differently.", "options": ["would have acted", "would act", "will act", "acted"], "correct_answer": "would have acted", "explanation": "Inverted Conditional III: Had + subject + V3, would have + V3", "topic": "Advanced Conditionals"},
                {"question": "The CEO, ___ company went bankrupt, resigned.", "options": ["whose", "which", "that", "who's"], "correct_answer": "whose", "explanation": "'Whose' shows possession in relative clauses", "topic": "Relative Clauses"},
                {"question": "Choose the subjunctive: The teacher insisted that he ___.", "options": ["study harder", "studies harder", "studied harder", "studying harder"], "correct_answer": "study harder", "explanation": "Mandative subjunctive: base form after 'insist that'", "topic": "Subjunctive Mood"},
                {"question": "Not until the bell rang ___ leave.", "options": ["did they", "they did", "they", "they were"], "correct_answer": "did they", "explanation": "Negative adverbial fronting requires subject-auxiliary inversion", "topic": "Inversion"},
                {"question": "'To kick the bucket' means:", "options": ["To die", "To kick something", "To give up", "To start"], "correct_answer": "To die", "explanation": "This is a common English idiom meaning 'to die'", "topic": "Idioms"},
            ]
        },
        "german": {
            "beginner": [
                {"question": "Welcher Artikel: ___ Hund", "options": ["der", "die", "das", "den"], "correct_answer": "der", "explanation": "Hund ist maskulin → der Hund", "topic": "Artikel"},
                {"question": "Ich ___ müde. (sein)", "options": ["bin", "bist", "ist", "sind"], "correct_answer": "bin", "explanation": "ich bin, du bist, er/sie/es ist", "topic": "Konjugation"},
                {"question": "Plural von 'das Kind':", "options": ["die Kinder", "die Kinds", "die Kindern", "das Kinder"], "correct_answer": "die Kinder", "explanation": "Kind → Kinder (Plural immer mit 'die')", "topic": "Plural"},
                {"question": "Er gibt ___ Freund ein Buch. (Dativ)", "options": ["seinem", "seinen", "seine", "sein"], "correct_answer": "seinem", "explanation": "Dativ maskulin: seinem (Wem? → seinem Freund)", "topic": "Kasus"},
                {"question": "Gestern ___ ich ins Kino. (gehen, Perfekt)", "options": ["bin gegangen", "habe gegangen", "ging", "gehe"], "correct_answer": "bin gegangen", "explanation": "Bewegungsverben bilden Perfekt mit 'sein'", "topic": "Perfekt"},
            ],
            "intermediate": [
                {"question": "Wenn ich Zeit ___, würde ich lesen. (haben, Konj. II)", "options": ["hätte", "habe", "hatte", "haben"], "correct_answer": "hätte", "explanation": "Konjunktiv II von 'haben': hätte", "topic": "Konjunktiv II"},
                {"question": "Das Buch, ___ ich lese, ist spannend.", "options": ["das", "dass", "welches", "der"], "correct_answer": "das", "explanation": "Relativpronomen für 'das Buch' (Neutrum, Akkusativ)", "topic": "Relativsätze"},
                {"question": "Er behauptet, ___ er krank sei.", "options": ["dass", "das", "ob", "weil"], "correct_answer": "dass", "explanation": "'dass' leitet Nebensätze ein (Konjunktion)", "topic": "Nebensätze"},
                {"question": "Wo fehlt ein Komma? 'Obwohl es regnete ging sie spazieren.'", "options": ["nach 'regnete'", "nach 'Obwohl'", "nach 'es'", "nach 'ging'"], "correct_answer": "nach 'regnete'", "explanation": "Komma trennt Nebensatz vom Hauptsatz", "topic": "Kommasetzung"},
                {"question": "Passiv: 'Man baut das Haus.' → ", "options": ["Das Haus wird gebaut.", "Das Haus ist gebaut.", "Das Haus hat gebaut.", "Das Haus baut."], "correct_answer": "Das Haus wird gebaut.", "explanation": "Vorgangspassiv: werden + Partizip II", "topic": "Passiv"},
            ],
            "advanced": [
                {"question": "Konjunktiv I von 'sein' (3. Person):", "options": ["sei", "ist", "wäre", "seid"], "correct_answer": "sei", "explanation": "Konjunktiv I: er/sie/es sei (für indirekte Rede)", "topic": "Konjunktiv I"},
                {"question": "Welche Stilfigur: 'Das Meer lachte in der Sonne.'", "options": ["Personifikation", "Metapher", "Alliteration", "Hyperbel"], "correct_answer": "Personifikation", "explanation": "Personifikation: Menschliche Eigenschaft auf Nicht-Menschliches", "topic": "Stilmittel"},
                {"question": "Welche Epoche: 'Sturm und Drang'", "options": ["1765-1790", "1720-1750", "1800-1830", "1850-1890"], "correct_answer": "1765-1790", "explanation": "Sturm und Drang: ca. 1765-1790, Goethe, Schiller", "topic": "Literaturepochen"},
                {"question": "Bestimme die Satzglied-Funktion von 'gestern': 'Gestern war er krank.'", "options": ["Temporaladverbiale", "Subjekt", "Prädikat", "Objekt"], "correct_answer": "Temporaladverbiale", "explanation": "Wann? → gestern = Temporaladverbiale", "topic": "Satzglieder"},
                {"question": "Indirekte Rede: Er sagt: 'Ich bin krank.' → Er sagt, er ___ krank.", "options": ["sei", "ist", "wäre", "war"], "correct_answer": "sei", "explanation": "Konjunktiv I in der indirekten Rede: sein → sei", "topic": "Indirekte Rede"},
            ]
        },
        "history": {
            "beginner": [
                {"question": "Wann begann der Erste Weltkrieg?" if language == "de" else "When did WWI begin?", "options": ["1914", "1918", "1939", "1900"], "correct_answer": "1914", "explanation": "Der Erste Weltkrieg begann am 28. Juli 1914", "topic": "Erster Weltkrieg"},
                {"question": "Wer war der erste Bundeskanzler Deutschlands?" if language == "de" else "Who was Germany's first chancellor?", "options": ["Konrad Adenauer", "Willy Brandt", "Otto von Bismarck", "Helmut Kohl"], "correct_answer": "Konrad Adenauer", "explanation": "Konrad Adenauer (CDU) war von 1949-1963 Bundeskanzler", "topic": "Bundesrepublik"},
                {"question": "Wann fiel die Berliner Mauer?" if language == "de" else "When did the Berlin Wall fall?", "options": ["1989", "1990", "1991", "1987"], "correct_answer": "1989", "explanation": "Die Berliner Mauer fiel am 9. November 1989", "topic": "Deutsche Teilung"},
                {"question": "Was war die Französische Revolution?" if language == "de" else "When was the French Revolution?", "options": ["1789", "1776", "1848", "1815"], "correct_answer": "1789", "explanation": "Beginn: 14. Juli 1789 (Sturm auf die Bastille)", "topic": "Französische Revolution"},
                {"question": "Wer war Martin Luther?" if language == "de" else "Who was Martin Luther?", "options": ["Reformator", "Kaiser", "Papst", "König"], "correct_answer": "Reformator", "explanation": "Martin Luther löste 1517 die Reformation aus", "topic": "Reformation"},
            ],
            "intermediate": [
                {"question": "Was war der Versailler Vertrag?" if language == "de" else "What was the Treaty of Versailles?", "options": ["Friedensvertrag nach dem 1. WK", "Handelsvertrag", "NATO-Gründung", "EU-Vertrag"], "correct_answer": "Friedensvertrag nach dem 1. WK", "explanation": "Unterzeichnet am 28. Juni 1919, beendete offiziell den 1. Weltkrieg", "topic": "Erster Weltkrieg"},
                {"question": "Was bedeutet 'Ermächtigungsgesetz' (1933)?" if language == "de" else "What was the Enabling Act (1933)?", "options": ["Hitler erhielt diktatorische Vollmachten", "Gründung der BRD", "Aufhebung der Sklaverei", "Einführung des Grundgesetzes"], "correct_answer": "Hitler erhielt diktatorische Vollmachten", "explanation": "Das Ermächtigungsgesetz gab Hitler die Macht, Gesetze ohne Reichstag zu erlassen", "topic": "Nationalsozialismus"},
                {"question": "Was war der Marshall-Plan?" if language == "de" else "What was the Marshall Plan?", "options": ["US-Wirtschaftshilfe für Europa", "Militärbündnis", "Friedensvertrag", "Berliner Blockade"], "correct_answer": "US-Wirtschaftshilfe für Europa", "explanation": "1948-1952: US-Wiederaufbauprogramm für Europa nach dem 2. WK", "topic": "Kalter Krieg"},
                {"question": "Wann wurde die DDR gegründet?" if language == "de" else "When was the GDR founded?", "options": ["1949", "1945", "1953", "1961"], "correct_answer": "1949", "explanation": "Die DDR wurde am 7. Oktober 1949 gegründet", "topic": "Deutsche Teilung"},
                {"question": "Was war die Industrialisierung?" if language == "de" else "What characterized industrialization?", "options": ["Übergang von Handarbeit zu Maschinenproduktion", "Digitalisierung", "Agrarrevolution", "Französische Revolution"], "correct_answer": "Übergang von Handarbeit zu Maschinenproduktion", "explanation": "Ab ca. 1760 in England, ab ca. 1835 in Deutschland", "topic": "Industrialisierung"},
            ],
            "advanced": [
                {"question": "Was war Bismarcks Bündnispolitik?" if language == "de" else "What was Bismarck's alliance policy?", "options": ["System zur Isolierung Frankreichs", "Bündnis mit Frankreich", "Neutralitätspolitik", "Kolonialpolitik"], "correct_answer": "System zur Isolierung Frankreichs", "explanation": "Bismarck schuf ein Bündnissystem (Zweibund, Dreibund, Rückversicherungsvertrag)", "topic": "Deutsches Kaiserreich"},
                {"question": "Was besagt die Fischer-Kontroverse?" if language == "de" else "What is the Fischer controversy?", "options": ["Deutschlands Hauptschuld am 1. WK", "Schuld am 2. WK", "Holocaust-Leugnung", "Dolchstoßlegende"], "correct_answer": "Deutschlands Hauptschuld am 1. WK", "explanation": "Fritz Fischer (1961): Deutschland trug Hauptverantwortung für den 1. WK", "topic": "Historiographie"},
                {"question": "Was war der Kulturkampf?" if language == "de" else "What was the Kulturkampf?", "options": ["Bismarck vs. Katholische Kirche", "Protestanten vs. Katholiken", "Kaiser vs. Reichstag", "Arbeiter vs. Adel"], "correct_answer": "Bismarck vs. Katholische Kirche", "explanation": "1871-1878: Bismarcks Versuch, den Einfluss der Katholischen Kirche zu begrenzen", "topic": "Deutsches Kaiserreich"},
                {"question": "Was war die Hallstein-Doktrin?" if language == "de" else "What was the Hallstein Doctrine?", "options": ["BRD erkannte DDR nicht an", "DDR erkannte BRD nicht an", "Wiedervereinigungsplan", "NATO-Beitritt"], "correct_answer": "BRD erkannte DDR nicht an", "explanation": "1955-1969: BRD brach Beziehungen zu Staaten ab, die DDR anerkannten", "topic": "Kalter Krieg"},
                {"question": "Was war die Neue Ostpolitik?" if language == "de" else "What was Ostpolitik?", "options": ["Willy Brandts Annäherung an den Osten", "Adenauers Westbindung", "Kalter-Krieg-Eskalation", "NATO-Osterweiterung"], "correct_answer": "Willy Brandts Annäherung an den Osten", "explanation": "Ab 1969: 'Wandel durch Annäherung', Moskauer und Warschauer Vertrag", "topic": "Bundesrepublik"},
            ]
        },
        "science": {
            "beginner": [
                {"question": "Was ist H₂O?" if language == "de" else "What is H₂O?", "options": ["Wasser", "Sauerstoff", "Wasserstoff", "Salz"], "correct_answer": "Wasser", "explanation": "H₂O = 2 Wasserstoff + 1 Sauerstoff = Wasser", "topic": "Chemie"},
                {"question": "Was ist die Einheit der Kraft?" if language == "de" else "What is the unit of force?", "options": ["Newton (N)", "Joule (J)", "Watt (W)", "Volt (V)"], "correct_answer": "Newton (N)", "explanation": "Kraft wird in Newton (N) gemessen, nach Isaac Newton benannt", "topic": "Physik"},
                {"question": "Was ist die kleinste Einheit des Lebens?" if language == "de" else "What is the smallest unit of life?", "options": ["Zelle", "Atom", "Molekül", "Organ"], "correct_answer": "Zelle", "explanation": "Die Zelle ist die kleinste funktionelle Einheit aller Lebewesen", "topic": "Biologie"},
                {"question": "Wie viele Planeten hat unser Sonnensystem?" if language == "de" else "How many planets in our solar system?", "options": ["8", "9", "7", "10"], "correct_answer": "8", "explanation": "Merkur, Venus, Erde, Mars, Jupiter, Saturn, Uranus, Neptun", "topic": "Physik"},
                {"question": "Was ist Photosynthese?" if language == "de" else "What is photosynthesis?", "options": ["Pflanzen erzeugen Energie aus Licht", "Zellteilung", "Verdauung", "Atmung"], "correct_answer": "Pflanzen erzeugen Energie aus Licht", "explanation": "6CO₂ + 6H₂O + Licht → C₆H₁₂O₆ + 6O₂", "topic": "Biologie"},
            ],
            "intermediate": [
                {"question": "Was ist die Formel für kinetische Energie?" if language == "de" else "Formula for kinetic energy?", "options": ["Ekin = ½mv²", "E = mc²", "F = ma", "P = UI"], "correct_answer": "Ekin = ½mv²", "explanation": "Kinetische Energie = halbe Masse mal Geschwindigkeit zum Quadrat", "topic": "Physik"},
                {"question": "Was ist eine exotherme Reaktion?" if language == "de" else "What is an exothermic reaction?", "options": ["Gibt Wärme ab", "Nimmt Wärme auf", "Erzeugt Licht", "Erzeugt Gas"], "correct_answer": "Gibt Wärme ab", "explanation": "Exotherm: Energie wird an die Umgebung abgegeben (ΔH < 0)", "topic": "Chemie"},
                {"question": "Was ist DNA?" if language == "de" else "What is DNA?", "options": ["Desoxyribonukleinsäure", "Protein", "Lipid", "Kohlenhydrat"], "correct_answer": "Desoxyribonukleinsäure", "explanation": "DNA trägt die genetische Information aller Lebewesen", "topic": "Biologie"},
                {"question": "Ohmsches Gesetz:" if language == "de" else "Ohm's Law:", "options": ["U = R × I", "F = m × a", "E = mc²", "P = F × v"], "correct_answer": "U = R × I", "explanation": "Spannung = Widerstand × Stromstärke", "topic": "Physik"},
                {"question": "Was passiert bei der Mitose?" if language == "de" else "What happens in mitosis?", "options": ["Identische Zellteilung", "Halbierung der Chromosomen", "Proteinbildung", "DNA-Reparatur"], "correct_answer": "Identische Zellteilung", "explanation": "Mitose: Zellteilung mit identischem Chromosomensatz (2n → 2n)", "topic": "Biologie"},
            ],
            "advanced": [
                {"question": "Schrödinger-Gleichung beschreibt:" if language == "de" else "Schrödinger equation describes:", "options": ["Quantenmechanische Wellenfunktion", "Elektromagnetismus", "Relativität", "Thermodynamik"], "correct_answer": "Quantenmechanische Wellenfunktion", "explanation": "Die Schrödinger-Gleichung beschreibt die zeitliche Entwicklung quantenmechanischer Zustände", "topic": "Quantenphysik"},
                {"question": "Was ist ein Katalysator?" if language == "de" else "What is a catalyst?", "options": ["Senkt Aktivierungsenergie", "Erhöht Aktivierungsenergie", "Liefert Energie", "Stoppt Reaktion"], "correct_answer": "Senkt Aktivierungsenergie", "explanation": "Katalysatoren senken die Aktivierungsenergie, ohne selbst verbraucht zu werden", "topic": "Chemie"},
                {"question": "Hardy-Weinberg-Gleichgewicht setzt voraus:" if language == "de" else "Hardy-Weinberg equilibrium requires:", "options": ["Keine Selektion, große Population", "Kleine Population", "Starke Selektion", "Inzucht"], "correct_answer": "Keine Selektion, große Population", "explanation": "HWG: keine Mutation, keine Migration, keine Selektion, große Population, Zufallspaarung", "topic": "Genetik"},
                {"question": "Entropie-Änderung bei spontanen Prozessen:" if language == "de" else "Entropy change in spontaneous processes:", "options": ["ΔS(gesamt) > 0", "ΔS = 0", "ΔS < 0", "ΔS = 1"], "correct_answer": "ΔS(gesamt) > 0", "explanation": "2. Hauptsatz der Thermodynamik: Gesamtentropie nimmt bei spontanen Prozessen zu", "topic": "Thermodynamik"},
                {"question": "Was ist CRISPR-Cas9?" if language == "de" else "What is CRISPR-Cas9?", "options": ["Gen-Editing-Werkzeug", "Antibiotikum", "Impfstoff", "Bildgebungsverfahren"], "correct_answer": "Gen-Editing-Werkzeug", "explanation": "CRISPR-Cas9 ist eine Genschere zum gezielten Editieren von DNA", "topic": "Molekularbiologie"},
            ]
        }
    }

    # Bug-Fix 4: Use mapped quiz_key instead of raw German subject name
    subject_quizzes = quizzes.get(quiz_key, quizzes["math"])
    difficulty_quizzes = subject_quizzes.get(difficulty, subject_quizzes["intermediate"])

    # Shuffle and limit
    selected = random.sample(difficulty_quizzes, min(num_questions, len(difficulty_quizzes)))

    questions = []
    for i, q in enumerate(selected):
        questions.append({
            "id": i + 1,
            "question": q["question"],
            "options": q.get("options"),
            "correct_answer": q["correct_answer"],
            "explanation": q["explanation"],
            "difficulty": difficulty,
            "topic": q.get("topic", subject)
        })

    return questions


def get_fach_regeln(fach: str) -> str:
    """Return subject-specific quiz generation rules for all 32 subjects.

    Final Polish 5.1 Block 2: Fach-spezifische Regeln für Groq-basierte Quiz-Generierung.
    """
    regeln: dict[str, str] = {
        "Mathe": "Nutze konkrete Zahlen. Rechenweg als Erklärung. LaTeX für Formeln: $x^2$. Immer Probe angeben.",
        "Physik": "Formeln + Einheiten immer angeben. Realweltbezug herstellen. Rechenaufgaben bevorzugen.",
        "Chemie": "Reaktionsgleichungen ausgleichen. Stoffnamen + Formeln. Sicherheitshinweise erwähnen.",
        "Biologie": "Fachbegriffe lateinisch + deutsch. Schaubilder beschreiben. Evolutionäre Zusammenhänge.",
        "Deutsch": "Grammatik-Regeln mit Beispielsätzen. Literatur-Epochen nennen. Rechtschreibregeln erklären.",
        "Englisch": "Grammatik mit Signalwörtern. Vokabeln im Kontext. Übersetzungen Deutsch-Englisch.",
        "Französisch": "Grammatik mit Konjugationstabellen. Vokabeln mit Artikel. Aussprache-Hinweise.",
        "Latein": "Stammformen angeben. Deklinationen/Konjugationen tabellarisch. Übersetzung Latein-Deutsch.",
        "Spanisch": "Konjugationen vollständig. Ser vs Estar erklären. Vokabeln mit Genus.",
        "Italienisch": "Konjugationen mit Beispielen. Aussprache-Tipps. Kulturelle Kontexte.",
        "Russisch": "Kyrillisch + Transliteration. Aspekte erklären. Kasus-Tabellen nutzen.",
        "Türkisch": "Vokalharmonie erklären. Suffixe hervorheben. Agglutination zeigen.",
        "Altgriechisch": "Stammformen angeben. Partizipien erklären. Übersetzung Griechisch-Deutsch.",
        "Geschichte": "Jahreszahlen + Epochen. Quellenanalyse-Methodik. Ursache-Wirkungs-Ketten.",
        "Geografie": "Karten-Bezug herstellen. Klimazonen + Vegetationszonen. Aktuelle Statistiken.",
        "Politik": "Grundgesetz-Artikel zitieren. Institutionen erklären. Aktuelle Bezüge.",
        "Wirtschaft": "Formeln für Berechnungen. Grafiken beschreiben. Marktmodelle erklären.",
        "Informatik": "Code-Beispiele in Python/Java. Algorithmen Schritt-für-Schritt. Big-O-Notation.",
        "Astronomie": "Größenverhältnisse nennen. Formeln + Einheiten. Beobachtungstipps.",
        "Technik": "Schaltplaene beschreiben. Materialien + Eigenschaften. Sicherheitsregeln.",
        "Psychologie": "Studien zitieren. Fachbegriffe definieren. Alltags-Beispiele geben.",
        "Pädagogik": "Theorien + Vertreter nennen. Fallbeispiele konstruieren. Methodenvergleich.",
        "Sozialwissenschaften": "Statistiken interpretieren. Theorien vergleichen. Aktuelle Studien.",
        "Philosophie": "Zitate + Denker zuordnen. Argumentationsstruktur zeigen. Gedankenexperimente.",
        "Recht": "Paragraphen zitieren. Fallbeispiele konstruieren. Rechtsgebiete abgrenzen.",
        "Religion (Kath.)": "Bibelstellen zitieren. Kirchengeschichte einbeziehen. Ethische Dilemmata.",
        "Religion (Ev.)": "Bibelstellen zitieren. Reformationsgeschichte. Ethische Reflexion.",
        "Islamunterricht": "Koranverse zitieren. Islamische Geschichte. Interreligiöser Dialog.",
        "Ethik": "Philosophische Positionen vergleichen. Dilemmata konstruieren. Argumentation foerdern.",
        "Werte und Normen": "Fallbeispiele aus dem Alltag. Verschiedene Perspektiven zeigen. Reflexionsfragen.",
        "Kunst": "Epochen + Kuenstler zuordnen. Bildbeschreibung systematisch. Gestaltungsmittel benennen.",
        "Musik": "Notenlehre + Intervalle. Epochen + Komponisten. Hoerbeispiele beschreiben.",
        "Darstellendes Spiel": "Theaterbegriffe definieren. Szenenanalyse. Improvisationstechniken.",
        "Sport": "Regelkunde + Taktik. Anatomie-Bezug. Trainingslehre-Prinzipien.",
        "Hauswirtschaft": "Nährwerte + Ernährungsregeln. Hygiene-Standards. Rezept-Berechnungen.",
        "Ernährungslehre": "Nährstoffe + Funktionen. Ernährungspyramide. Allergien + Unverträglichkeiten.",
    }
    return regeln.get(fach, "Stelle klare, präzise Fragen auf Deutsch. Gib hilfreiche Erklärungen.")


def generate_explain_why_wrong(
    fach: str,
    frage: str,
    falsche_antwort: str,
    richtige_antwort: str,
    erklärung: str,
) -> str:
    """Generate a mini-Lerneinheit explaining why an answer was wrong.

    Final Polish 5.1 Block 2: Explain-Why-Wrong Loop.
    Returns a 3-sentence explanation tailored to the subject.
    """
    fach_context = get_fach_regeln(fach)
    return (
        f"**Nicht ganz richtig!** Die korrekte Antwort ist: **{richtige_antwort}**\n\n"
        f"{erklärung}\n\n"
        f"**Tipp:** {fach_context.split('.')[0]}. "
        f"Versuche es beim nächsten Mal mit diesem Wissen!"
    )


def get_learning_path(subject: str, level: str, language: str = "de") -> dict:
    """Generate a learning path recommendation based on subject and level."""
    paths = {
        "math": {
            "beginner": {
                "topics": [
                    {"topic": "Grundrechenarten", "subject": "math", "difficulty": "beginner", "mastered": True, "recommended": False, "description": "Addition, Subtraktion, Multiplikation, Division"},
                    {"topic": "Bruchrechnung", "subject": "math", "difficulty": "beginner", "mastered": False, "recommended": True, "description": "Brüche addieren, subtrahieren, kürzen"},
                    {"topic": "Dezimalzahlen", "subject": "math", "difficulty": "beginner", "mastered": False, "recommended": True, "description": "Umrechnung und Rechnen mit Dezimalzahlen"},
                    {"topic": "Prozentrechnung", "subject": "math", "difficulty": "beginner", "mastered": False, "recommended": False, "description": "Grundwert, Prozentwert, Prozentsatz"},
                    {"topic": "Lineare Gleichungen", "subject": "math", "difficulty": "intermediate", "mastered": False, "recommended": False, "description": "Gleichungen mit einer Unbekannten lösen"},
                ],
                "next_milestone": "Beherrsche Bruchrechnung, um zu linearen Gleichungen aufzusteigen!" if language == "de" else "Master fractions to advance to linear equations!"
            },
            "intermediate": {
                "topics": [
                    {"topic": "Lineare Gleichungen", "subject": "math", "difficulty": "intermediate", "mastered": True, "recommended": False, "description": "Gleichungen mit einer Unbekannten"},
                    {"topic": "Quadratische Funktionen", "subject": "math", "difficulty": "intermediate", "mastered": False, "recommended": True, "description": "Parabeln, Scheitelpunktform, p-q-Formel"},
                    {"topic": "Trigonometrie", "subject": "math", "difficulty": "intermediate", "mastered": False, "recommended": True, "description": "Sinus, Kosinus, Tangens"},
                    {"topic": "Wahrscheinlichkeit", "subject": "math", "difficulty": "intermediate", "mastered": False, "recommended": False, "description": "Baumdiagramme, bedingte Wahrscheinlichkeit"},
                    {"topic": "Differentialrechnung", "subject": "math", "difficulty": "advanced", "mastered": False, "recommended": False, "description": "Ableitungen und Kurvendiskussion"},
                ],
                "next_milestone": "Meistere quadratische Funktionen für die Oberstufe!" if language == "de" else "Master quadratic functions for upper secondary!"
            },
            "advanced": {
                "topics": [
                    {"topic": "Differentialrechnung", "subject": "math", "difficulty": "advanced", "mastered": True, "recommended": False, "description": "Ableitungsregeln, Extremwerte"},
                    {"topic": "Integralrechnung", "subject": "math", "difficulty": "advanced", "mastered": False, "recommended": True, "description": "Stammfunktionen, bestimmte Integrale"},
                    {"topic": "Analytische Geometrie", "subject": "math", "difficulty": "advanced", "mastered": False, "recommended": True, "description": "Vektoren, Geraden, Ebenen im Raum"},
                    {"topic": "Stochastik", "subject": "math", "difficulty": "advanced", "mastered": False, "recommended": False, "description": "Binomialverteilung, Hypothesentests"},
                    {"topic": "Komplexe Zahlen", "subject": "math", "difficulty": "advanced", "mastered": False, "recommended": False, "description": "i, Gaußsche Zahlenebene"},
                ],
                "next_milestone": "Integralrechnung ist der nächste Schritt zum Abitur!" if language == "de" else "Integral calculus is the next step to Abitur!"
            }
        }
    }

    # Default path for subjects not yet fully defined
    default_path = {
        "topics": [
            {"topic": f"{subject.capitalize()} Grundlagen", "subject": subject, "difficulty": "beginner", "mastered": level != "beginner", "recommended": level == "beginner", "description": "Grundlegende Konzepte und Methoden"},
            {"topic": f"{subject.capitalize()} Mittelstufe", "subject": subject, "difficulty": "intermediate", "mastered": level == "advanced", "recommended": level == "intermediate", "description": "Vertiefung und Anwendung"},
            {"topic": f"{subject.capitalize()} Oberstufe", "subject": subject, "difficulty": "advanced", "mastered": False, "recommended": level == "advanced", "description": "Abitur-Vorbereitung und Vertiefung"},
        ],
        "next_milestone": "Weiter so! Arbeite dich durch die Themen." if language == "de" else "Keep going! Work through the topics."
    }

    subject_paths = paths.get(subject, {})
    return subject_paths.get(level, default_path)


def update_proficiency(current_level: str, score: float, total_questions: int) -> str:
    """Update proficiency level based on quiz performance."""
    accuracy = score / total_questions if total_questions > 0 else 0

    if current_level == "beginner":
        if accuracy >= 0.8:
            return "intermediate"
        return "beginner"
    elif current_level == "intermediate":
        if accuracy >= 0.85:
            return "advanced"
        elif accuracy < 0.4:
            return "beginner"
        return "intermediate"
    else:  # advanced
        if accuracy < 0.3:
            return "intermediate"
        return "advanced"
