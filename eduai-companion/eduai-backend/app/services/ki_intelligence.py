"""KI Intelligence Service - Lernstil-Erkennung, Emotionale Intelligenz, Feynman, Sokrates, Wissenslücken.

Phase 3 of Supreme 9.0: Makes the KI dramatically smarter.
"""
import logging
import os
from typing import Optional

from groq import Groq

logger = logging.getLogger(__name__)

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
FAST_MODEL = "llama-3.1-8b-instant"


def _get_client() -> Optional[Groq]:
    if not GROQ_KEY:
        return None
    return Groq(api_key=GROQ_KEY)


# ── 3.1 Lernstil-Erkennung ──────────────────────────────────────────

LERNSTIL_DESCRIPTIONS = {
    "visuell": "Diagramme, Tabellen, Schritt-fuer-Schritt mit Pfeilen, ASCII-Art",
    "auditiv": "Ausfuehrliche Erklaerungen, Analogien, Geschichten, als wuerdest du es erzaehlen",
    "kinesthetisch": "Sofort Uebungsaufgabe geben, 'Probiere es selbst', interaktiv",
    "lesen": "Stichpunkte, nummerierte Listen, Zusammenfassung, strukturierter Text",
}


async def detect_lernstil(chat_history: list) -> str:
    """Detect learning style from chat history after 5+ messages."""
    if len(chat_history) < 5:
        return "auditiv"  # default

    client = _get_client()
    if not client:
        return "auditiv"

    recent = [m.get("content", "")[:150] for m in chat_history[-10:] if m.get("role") == "user"]
    chat_text = "\n".join(recent)

    try:
        resp = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{
                "role": "system",
                "content": (
                    "Analysiere diese Chat-Nachrichten eines Schuelers. "
                    "Erkenne seinen Lernstil:\n"
                    "- VISUELL: Fragt nach Diagrammen, Tabellen, 'Zeig mir'\n"
                    "- AUDITIV: Fragt nach Erklaerungen, 'Erklaer mir warum'\n"
                    "- KINESTHETISCH: Will selbst ausprobieren, 'Lass mich loesen'\n"
                    "- LESEN: Will Stichpunkte, Listen, Zusammenfassungen\n\n"
                    "Antworte NUR mit einem Wort: VISUELL / AUDITIV / KINESTHETISCH / LESEN"
                ),
            }, {
                "role": "user",
                "content": chat_text,
            }],
            max_tokens=20,
            temperature=0.1,
        )
        result = resp.choices[0].message.content.strip().lower()
        if result in LERNSTIL_DESCRIPTIONS:
            return result
        for style in LERNSTIL_DESCRIPTIONS:
            if style in result:
                return style
    except Exception as e:
        logger.warning("Lernstil detection failed: %s", e)

    return "auditiv"


def get_lernstil_prompt(lernstil: str) -> str:
    """Get system prompt addition for the detected learning style."""
    desc = LERNSTIL_DESCRIPTIONS.get(lernstil, "")
    if not desc:
        return ""
    return (
        f"\nLERNSTIL DES SCHUELERS: {lernstil.upper()}\n"
        f"Passe deinen Antwort-Stil an: {desc}\n"
    )


# ── 3.2 Emotionale Intelligenz ──────────────────────────────────────

EMOTION_KEYWORDS = {
    "frustriert": [
        "verstehe nicht", "hilft nicht", "macht keinen sinn", "ugh", "argh",
        "ich hasse", "nervt", "bloed", "dumm", "klappt nicht", "falsch",
        "kapier nicht", "keine ahnung", "zu schwer",
    ],
    "gestresst": [
        "klausur morgen", "pruefung heute", "keine zeit", "hilfe",
        "morgen test", "muss heute", "deadline", "panik", "stress",
        "schaffe das nicht", "zu viel",
    ],
    "motiviert": [
        "verstanden!", "endlich", "danke", "wow", "cool", "super",
        "geschafft", "richtig!", "geil", "mega", "krass", "nice",
        "hab ich", "klar jetzt",
    ],
}

EMOTION_RESPONSES = {
    "frustriert": (
        "EMOTIONAL: Der Schueler ist FRUSTRIERT. Reagiere einfuehlsam:\n"
        "- Sage 'Ich verstehe, das ist wirklich ein schwieriges Thema.'\n"
        "- Nutze die EINFACHSTE moegliche Erklaerung\n"
        "- Gib ein sehr leichtes Beispiel zuerst\n"
        "- Ermutige: 'Schritt fuer Schritt schaffen wir das!'\n"
    ),
    "gestresst": (
        "EMOTIONAL: Der Schueler ist GESTRESST (Pruefung/Zeitdruck). Reagiere supportiv:\n"
        "- Sage 'Du schaffst das! Lass uns das JETZT in 10 Minuten durchgehen.'\n"
        "- Gib NUR das Wichtigste (keine langen Erklaerungen)\n"
        "- Fokus auf Pruefungs-relevante Punkte\n"
        "- Strukturiere klar: '3 Dinge die du wissen musst:'\n"
    ),
    "motiviert": (
        "EMOTIONAL: Der Schueler ist MOTIVIERT. Nutze den Schwung:\n"
        "- Lobe: 'Super gemacht!'\n"
        "- Gib eine Herausforderungs-Aufgabe\n"
        "- Erhoehe das Niveau leicht\n"
        "- Zeige Zusammenhaenge zu fortgeschrittenen Themen\n"
    ),
}


def detect_emotion(message: str) -> str:
    """Detect student emotion from message text."""
    msg_lower = message.lower()
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(k in msg_lower for k in keywords):
            return emotion
    return "neutral"


def get_emotion_prompt(emotion: str) -> str:
    """Get system prompt addition for the detected emotion."""
    return EMOTION_RESPONSES.get(emotion, "")


# ── 3.3 Sokrates-Methode ────────────────────────────────────────────

SOKRATES_PROMPT = (
    "DU BIST SOKRATES. Statt direkt zu antworten, fuehre den Schueler durch FRAGEN zur Antwort.\n"
    "REGELN:\n"
    "1. Beginne IMMER mit einer Frage: 'Was weisst du schon ueber...?'\n"
    "2. Stelle Folgefragen basierend auf der Antwort\n"
    "3. Leite den Schueler Schritt fuer Schritt zum Verstaendnis\n"
    "4. Gib NIEMALS die komplette Antwort direkt\n"
    "5. Wenn der Schueler nah dran ist, bestaerke ihn\n"
    "6. Am Ende: Zusammenfassung was der Schueler SELBST herausgefunden hat\n"
    "Wissenschaftlich bewiesen: Selbst-Entdeckung = 3x besseres Langzeitgedaechtnis!\n"
)


# ── 3.4 Feynman-Technik ─────────────────────────────────────────────

FEYNMAN_SYSTEM_PROMPT = (
    "Der Schueler nutzt die FEYNMAN-TECHNIK. Er erklaert dir ein Thema.\n"
    "DEINE AUFGABE:\n"
    "1. Bewerte sein Verstaendnis (1-10)\n"
    "2. Zeige Luecken auf: 'Du hast X gut erklaert, aber bei Y fehlt noch...'\n"
    "3. Stelle Rueckfragen zu schwachen Stellen\n"
    "4. Gib Feedback: Was war gut, was kann besser werden\n"
    "5. Am Ende: Zusammenfassung + Note (1-10)\n"
    "Wissenschaftlich: Erklaeren = die BESTE Lernmethode!\n"
)


# ── 3.5 Wissenslücken-Scanner ───────────────────────────────────────

async def generate_diagnostic_questions(subject: str, grade: str) -> list:
    """Generate 20 quick diagnostic questions to scan knowledge gaps."""
    client = _get_client()
    if not client:
        return _fallback_diagnostic(subject)

    try:
        resp = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{
                "role": "system",
                "content": (
                    "Erstelle 10 kurze Diagnose-Fragen fuer einen Schueler.\n"
                    "REGELN:\n"
                    "- Fach: {subject}, Klasse: {grade}\n"
                    "- Jede Frage testet ein ANDERES Unterthema\n"
                    "- Multiple-Choice mit 4 Optionen\n"
                    "- Antwort als JSON Array\n"
                    "Format: [{\"frage\": \"...\", \"optionen\": [\"A\",\"B\",\"C\",\"D\"], "
                    "\"antwort\": 0, \"thema\": \"Unterthema\"}]\n"
                    "NUR das JSON Array, kein anderer Text."
                ).replace("{subject}", subject).replace("{grade}", grade),
            }, {
                "role": "user",
                "content": f"Erstelle 10 Diagnose-Fragen fuer {subject} Klasse {grade}",
            }],
            max_tokens=2000,
            temperature=0.5,
        )
        import json
        text = resp.choices[0].message.content.strip()
        # Try to extract JSON
        if "[" in text:
            start = text.index("[")
            end = text.rindex("]") + 1
            return json.loads(text[start:end])
    except Exception as e:
        logger.warning("Diagnostic question generation failed: %s", e)

    return _fallback_diagnostic(subject)


def _fallback_diagnostic(subject: str) -> list:
    """Fallback diagnostic questions when Groq is unavailable."""
    return [
        {"frage": f"Grundfrage 1 zu {subject}", "optionen": ["A", "B", "C", "D"], "antwort": 0, "thema": "Grundlagen"},
        {"frage": f"Grundfrage 2 zu {subject}", "optionen": ["A", "B", "C", "D"], "antwort": 1, "thema": "Vertiefung"},
    ]


def analyze_gaps(answers: list, questions: list) -> dict:
    """Analyze diagnostic answers to find knowledge gaps."""
    total = len(questions)
    correct = 0
    gaps = []
    strengths = []

    for i, q in enumerate(questions):
        if i < len(answers):
            user_ans = answers[i]
            correct_ans = q.get("antwort", 0)
            if user_ans == correct_ans:
                correct += 1
                strengths.append(q.get("thema", f"Thema {i+1}"))
            else:
                gaps.append(q.get("thema", f"Thema {i+1}"))
        else:
            gaps.append(q.get("thema", f"Thema {i+1}"))

    score = round(correct / total * 100, 1) if total > 0 else 0

    return {
        "score": score,
        "correct": correct,
        "total": total,
        "gaps": gaps,
        "strengths": strengths,
        "recommendation": _gap_recommendation(gaps, score),
    }


def _gap_recommendation(gaps: list, score: float) -> str:
    if score >= 90:
        return "Hervorragend! Du hast kaum Luecken. Fokussiere dich auf die fortgeschrittenen Themen."
    elif score >= 70:
        return f"Gutes Grundwissen! Arbeite an diesen Luecken: {', '.join(gaps[:3])}"
    elif score >= 50:
        return f"Du hast einige Luecken. Prioritaet: {', '.join(gaps[:5])}"
    else:
        return f"Viele Grundlagen fehlen noch. Starte mit: {', '.join(gaps[:3])}"


# ── 3.6 Wochen-Coach Prompt ─────────────────────────────────────────

def build_weekly_plan_prompt(user_info: dict, weak_topics: list, exams: list) -> str:
    """Build a prompt for generating a personalized weekly study plan."""
    return (
        f"Erstelle einen KONKRETEN Wochenplan (Mo-So) fuer diesen Schueler:\n\n"
        f"Klasse: {user_info.get('grade', '10')} | Schule: {user_info.get('school_type', 'Gymnasium')}\n"
        f"Schwaechen: {', '.join(weak_topics) if weak_topics else 'Keine bekannt'}\n"
        f"Kommende Klausuren: {', '.join(exams) if exams else 'Keine eingetragen'}\n"
        f"Verfuegbare Zeit: 60 Minuten/Tag\n\n"
        f"Format:\n"
        f"Montag: 30 Min Mathe - [Thema], dann 15 Min Deutsch - [Thema]\n"
        f"Dienstag: ...\n\n"
        f"Jeden Tag: konkrete Themen, Zeitangaben, Prioritaeten.\n"
        f"Klausur-Vorbereitung: In letzte 3 Tage vor Klausur einplanen.\n"
        f"Antworte auf Deutsch."
    )
