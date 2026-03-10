"""Bundesland-Logik: Lehrplan-spezifische Anpassungen für 16 deutsche Bundesländer.

LUMNOS Fächer-Expansion 5.0 Block 3:
- 16 Bundesländer mit Curriculum-Kontext
- Bundesland-spezifischer System-Prompt für KI
- Schultyp-Erkennung (Gymnasium, Realschule, etc.)
"""

BUNDESLAENDER = [
    "Baden-Wuerttemberg",
    "Bayern",
    "Berlin",
    "Brandenburg",
    "Bremen",
    "Hamburg",
    "Hessen",
    "Mecklenburg-Vorpommern",
    "Niedersachsen",
    "Nordrhein-Westfalen",
    "Rheinland-Pfalz",
    "Saarland",
    "Sachsen",
    "Sachsen-Anhalt",
    "Schleswig-Holstein",
    "Thueringen",
]

SCHULTYPEN = [
    "Gymnasium",
    "Realschule",
    "Hauptschule",
    "Gesamtschule",
    "Fachoberschule",
    "Berufsschule",
]

BUNDESLAND_KONTEXT: dict[str, str] = {
    "Bayern": (
        "Gymnasium endet mit G8/G9. Abitur sehr anspruchsvoll. LehrplanPLUS. "
        "Besonderheiten: Profiloberstufe, Colloquium als muendliche Prüfung. "
        "Starker Fokus auf MINT und Sprachen."
    ),
    "Nordrhein-Westfalen": (
        "Zentralabitur NRW. Oberstufe mit Grund- und Leistungskursen. "
        "Kernlehrplaene NRW. Besonderheit: Sozialwissenschaften als eigenes Fach. "
        "G9 seit 2019 wieder Standard."
    ),
    "Berlin": (
        "ISS (Integrierte Sekundarschule) und Gymnasium. Berliner Rahmenlehrplan. "
        "Besonderheit: 5. Prüfungskomponente im Abitur (Praesentation/BLL). "
        "Ethik als Pflichtfach."
    ),
    "Baden-Wuerttemberg": (
        "Bildungsplan BW. Profiloberstufe mit Seminarkurs. "
        "Besonderheit: NwT (Naturwissenschaft und Technik) als Profilfach. "
        "G8 am Gymnasium, G9 an Gemeinschaftsschulen."
    ),
    "Niedersachsen": (
        "Kerncurriculum Niedersachsen. Werte und Normen statt Ethik. "
        "Besonderheit: P5 muendliche Prüfung im Abitur. "
        "G9 seit 2015. Seminarfach als eigenes Fach."
    ),
    "Hessen": (
        "Kerncurriculum Hessen. Landesabitur. "
        "Besonderheit: Politik und Wirtschaft als eigenes Fach. "
        "G8 und G9 parallel möglich."
    ),
    "Sachsen": (
        "Lehrplaene Sachsen. Sehr hohes Leistungsniveau. "
        "Besonderheit: Bewertung 1-6, starker MINT-Fokus. "
        "Mittelschule und Gymnasium. Informatik ab Klasse 7."
    ),
    "Hamburg": (
        "Bildungsplaene Hamburg. Stadtteilschule und Gymnasium. "
        "Besonderheit: Profiloberstufe mit Seminaren. "
        "Abitur nach 12 (G8) oder 13 (Stadtteilschule) Jahren."
    ),
    "Schleswig-Holstein": (
        "Fachanforderungen SH. G9 am Gymnasium. "
        "Besonderheit: Praesentation als 5. Prüfungskomponente. "
        "Gemeinschaftsschule als Alternative zum Gymnasium."
    ),
    "Rheinland-Pfalz": (
        "Lehrplaene RLP. MSS (Mainzer Studienstufe). "
        "Besonderheit: Leistungskurse und Grundkurse. "
        "G8, aber mit Orientierungsstufe."
    ),
    "Thueringen": (
        "Lehrplaene Thueringen. Hohes Leistungsniveau. "
        "Besonderheit: Seminarfach, starker MINT-Fokus. "
        "Regelschule und Gymnasium."
    ),
    "Brandenburg": (
        "Rahmenlehrplan Berlin-Brandenburg (gemeinsam mit Berlin). "
        "Besonderheit: WAT (Wirtschaft-Arbeit-Technik) als Pflichtfach. "
        "Gesamtschule und Gymnasium."
    ),
    "Sachsen-Anhalt": (
        "Fachlehrplaene Sachsen-Anhalt. "
        "Besonderheit: Sekundarschule und Gymnasium. "
        "Astronomie als eigenstaendiges Fach."
    ),
    "Mecklenburg-Vorpommern": (
        "Rahmenlehrplaene MV. Regionale Schule und Gymnasium. "
        "Besonderheit: Abitur nach 12 Jahren. "
        "Informatik als Pflichtfach."
    ),
    "Bremen": (
        "Bildungsplaene Bremen. Oberschule und Gymnasium. "
        "Besonderheit: E-Phase und Q-Phase. "
        "Starker Fokus auf Inklusion."
    ),
    "Saarland": (
        "Lehrplaene Saarland. G8 am Gymnasium. "
        "Besonderheit: Französisch als 1. Fremdsprache möglich. "
        "Gemeinschaftsschule als Alternative."
    ),
}


def get_bundesland_prompt(bundesland: str) -> str:
    """Generate a bundesland-specific context prompt for the AI.

    Args:
        bundesland: Name of the German federal state

    Returns:
        Context string to append to the system prompt
    """
    if not bundesland:
        return "Allgemeiner deutscher Lehrplan."

    kontext = BUNDESLAND_KONTEXT.get(bundesland, "")
    if not kontext:
        return f"Bundesland: {bundesland}. Orientiere dich am allgemeinen deutschen Lehrplan."

    return f"""
BUNDESLAND-KONTEXT: {bundesland}
{kontext}
-> Orientiere Quizfragen und Erklärungen am Lehrplan von {bundesland}.
-> Erwähne Abitur-Besonderheiten von {bundesland} wenn relevant.
-> Nutze Beispiele die zum Curriculum von {bundesland} passen.
"""


def get_schultyp_prompt(schultyp: str) -> str:
    """Generate a school type context prompt."""
    if not schultyp:
        return ""

    typ_map = {
        "Gymnasium": "Gymnasium-Niveau (Abitur-Vorbereitung). Hohes Anforderungsniveau.",
        "Realschule": "Realschul-Niveau (Mittlerer Schulabschluss). Praxisbezogene Erklärungen.",
        "Hauptschule": "Hauptschul-Niveau. Einfache, alltagsnahe Erklärungen mit vielen Beispielen.",
        "Gesamtschule": "Gesamtschul-Niveau. Differenzierte Erklärungen für verschiedene Niveaus.",
        "Fachoberschule": "FOS-Niveau. Berufsbezogene Schwerpunkte.",
        "Berufsschule": "Berufsschul-Niveau. Praxisorientierte Inhalte.",
    }

    return typ_map.get(schultyp, "")


def get_klasse_prompt(klasse: int | None) -> str:
    """Generate a grade-level context prompt."""
    if not klasse:
        return ""

    if klasse <= 6:
        return f"Klasse {klasse}: Unterstufe. Sehr einfache Sprache, viele Bilder und Beispiele."
    elif klasse <= 10:
        return f"Klasse {klasse}: Mittelstufe. Fachbegriffe mit Erklärungen, zunehmende Komplexität."
    else:
        return f"Klasse {klasse}: Oberstufe/Abitur. Wissenschaftliche Sprache, Transferaufgaben, Analyse."
