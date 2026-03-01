"""Quiz Topics Service - 50+ topics across 5 subjects.

Provides structured quiz topics for the topic selector UI.
Topics are tier-locked: Free gets basic topics, Pro gets more, Max gets all.
"""
from typing import Optional

# Subject mapping: internal ID -> display info
SUBJECT_MAP = {
    "math": {"name": "Mathematik", "icon": "Calculator"},
    "german": {"name": "Deutsch", "icon": "BookOpen"},
    "science": {"name": "Naturwissenschaften", "icon": "FlaskConical"},
    "english": {"name": "Englisch", "icon": "Languages"},
    "history": {"name": "Geschichte", "icon": "Clock"},
}

# 53 topics total: Mathe 15, Deutsch 12, Physik/Bio 10, Bio 8, Englisch 8
QUIZ_TOPICS = {
    "math": [
        # Free (first 5)
        {"id": "math_grundrechenarten", "name": "Grundrechenarten", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "math_bruchrechnung", "name": "Bruchrechnung", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "math_prozentrechnung", "name": "Prozentrechnung", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "math_lineare_gleichungen", "name": "Lineare Gleichungen", "tier": "free", "difficulty_range": [1, 4]},
        {"id": "math_geometrie_basics", "name": "Geometrie Grundlagen", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (next 5)
        {"id": "math_quadratische_funktionen", "name": "Quadratische Funktionen", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "math_trigonometrie", "name": "Trigonometrie", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "math_exponentialfunktionen", "name": "Exponentialfunktionen", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "math_stochastik", "name": "Stochastik & Wahrscheinlichkeit", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "math_vektoren", "name": "Vektorrechnung", "tier": "pro", "difficulty_range": [3, 5]},
        # Max (next 5)
        {"id": "math_differentialrechnung", "name": "Differentialrechnung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "math_integralrechnung", "name": "Integralrechnung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "math_lineare_algebra", "name": "Lineare Algebra & Matrizen", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "math_kurvendiskussion", "name": "Kurvendiskussion", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "math_komplexe_zahlen", "name": "Komplexe Zahlen", "tier": "max", "difficulty_range": [4, 5]},
    ],
    "german": [
        # Free (first 4)
        {"id": "de_artikel_kasus", "name": "Artikel & Kasus", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "de_konjugation", "name": "Verb-Konjugation", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "de_rechtschreibung", "name": "Rechtschreibung", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "de_plural", "name": "Plural & Deklination", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (next 4)
        {"id": "de_konjunktiv", "name": "Konjunktiv I & II", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "de_relativsaetze", "name": "Relativsätze & Nebensätze", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "de_kommasetzung", "name": "Kommasetzung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "de_passiv", "name": "Passiv & Aktiv", "tier": "pro", "difficulty_range": [2, 4]},
        # Max (next 4)
        {"id": "de_stilmittel", "name": "Stilmittel & Rhetorik", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_literaturepochen", "name": "Literaturepochen", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_textanalyse", "name": "Textanalyse & Interpretation", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_indirekte_rede", "name": "Indirekte Rede", "tier": "max", "difficulty_range": [3, 5]},
    ],
    "science": [
        # Free (first 3)
        {"id": "sci_mechanik", "name": "Mechanik (Kräfte & Bewegung)", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "sci_zellbiologie", "name": "Zellbiologie", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "sci_chemie_basics", "name": "Chemie Grundlagen", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (next 4)
        {"id": "sci_elektrizitaet", "name": "Elektrizität & Magnetismus", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "sci_optik", "name": "Optik & Licht", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "sci_genetik", "name": "Genetik & Vererbung", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "sci_periodensystem", "name": "Periodensystem & Elemente", "tier": "pro", "difficulty_range": [2, 4]},
        # Max (next 3)
        {"id": "sci_thermodynamik", "name": "Thermodynamik", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "sci_evolution", "name": "Evolution & Ökologie", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "sci_organische_chemie", "name": "Organische Chemie", "tier": "max", "difficulty_range": [3, 5]},
    ],
    "english": [
        # Free (first 3)
        {"id": "en_simple_tenses", "name": "Simple Tenses", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "en_to_be", "name": "To Be & Basics", "tier": "free", "difficulty_range": [1, 2]},
        {"id": "en_irregular_verbs", "name": "Irregular Verbs", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (next 3)
        {"id": "en_conditional", "name": "Conditional Sentences", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "en_passive_voice", "name": "Passive Voice", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "en_reported_speech", "name": "Reported Speech", "tier": "pro", "difficulty_range": [2, 4]},
        # Max (next 2)
        {"id": "en_advanced_grammar", "name": "Advanced Grammar & Inversion", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "en_idioms", "name": "Idioms & Phrasal Verbs", "tier": "max", "difficulty_range": [3, 5]},
    ],
    "history": [
        # Free (first 3)
        {"id": "hist_erster_weltkrieg", "name": "Erster Weltkrieg", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "hist_zweiter_weltkrieg", "name": "Zweiter Weltkrieg", "tier": "free", "difficulty_range": [1, 4]},
        {"id": "hist_weimarer_republik", "name": "Weimarer Republik", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (next 3)
        {"id": "hist_kalter_krieg", "name": "Kalter Krieg", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "hist_wiedervereinigung", "name": "Deutsche Wiedervereinigung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "hist_franz_revolution", "name": "Französische Revolution", "tier": "pro", "difficulty_range": [2, 5]},
        # Max (next 2)
        {"id": "hist_industrialisierung", "name": "Industrialisierung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "hist_roemisches_reich", "name": "Römisches Reich & Antike", "tier": "max", "difficulty_range": [3, 5]},
    ],
}


def get_topics_for_subject(subject: str, tier: str = "free") -> list[dict]:
    """Get available quiz topics for a subject, filtered by subscription tier.

    Args:
        subject: Subject ID (math, german, science, english, history)
        tier: Subscription tier (free, pro, max)

    Returns:
        List of topic dicts with id, name, tier, difficulty_range, locked status
    """
    tier_access = {"free": ["free"], "pro": ["free", "pro"], "max": ["free", "pro", "max"]}
    allowed_tiers = tier_access.get(tier, ["free"])
    topics = QUIZ_TOPICS.get(subject, [])

    result = []
    for topic in topics:
        result.append({
            **topic,
            "locked": topic["tier"] not in allowed_tiers,
        })
    return result


def get_all_topics(tier: str = "free") -> dict:
    """Get all quiz topics across all subjects, filtered by tier.

    Returns:
        Dict with subject keys, each containing list of topics with locked status.
    """
    result = {}
    for subject_id in QUIZ_TOPICS:
        result[subject_id] = {
            "info": SUBJECT_MAP.get(subject_id, {}),
            "topics": get_topics_for_subject(subject_id, tier),
            "total": len(QUIZ_TOPICS[subject_id]),
        }
    return result


def get_topic_count() -> dict:
    """Get total topic count per subject."""
    return {subject: len(topics) for subject, topics in QUIZ_TOPICS.items()}


def is_topic_accessible(topic_id: str, tier: str) -> bool:
    """Check if a specific topic is accessible for a given tier."""
    tier_access = {"free": ["free"], "pro": ["free", "pro"], "max": ["free", "pro", "max"]}
    allowed_tiers = tier_access.get(tier, ["free"])

    for subject_topics in QUIZ_TOPICS.values():
        for topic in subject_topics:
            if topic["id"] == topic_id:
                return topic["tier"] in allowed_tiers
    return False
