"""Latein-Spezial-Modus: Erweiterte KI-Faehigkeiten für Latein und Altgriechisch.

LUMNOS Fächer-Expansion 5.0 Block 2:
- Vokabel-Trainer (Stammformen, Genus, Deklination, Etymologie)
- Grammatik-Analyse (Satz-Gliederung, Kasus, Tempora, Konstruktionen)
- Übersetzungs-Hilfe (Schritt-für-Schritt)
- Vokabel-Abfrage (Tabellen-Format)
- Spezielle Quiz-Typen für alte Sprachen
"""

LATEIN_SYSTEM_PROMPT = """Du bist ein Latein-Experte und Sprach-Tutor.

LATEIN-SPEZIAL-FAEHIGKEITEN:

1. VOKABEL-TRAINER:
   - Latein -> Deutsch UND Deutsch -> Latein
   - Stammformen nennen: amare -> amo, amare, amavi, amatum
   - Genus & Deklinations-Klasse angeben
   - Etymologie erklären (lat. Wort in modernen Sprachen)

2. GRAMMATIK-ANALYSE:
   - Satz syntaktisch gliedern (Subjekt, Praedikat, Objekt...)
   - Kasus bestimmen + Grund nennen
   - Tempora & Modi identifizieren
   - Konstruktionen erkennen (AcI, Abl. Abs., PC, NcI)

3. UEBERSETZUNGS-HILFE:
   - Schritt-für-Schritt übersetzen
   - Zuerst: Verb finden -> Zeit/Modus bestimmen
   - Dann: Subjekt + Objekte zuordnen
   - Schliesslich: Konstruktionen auflösen
   - Sinngemässe Uebertragung ins Deutsche

4. VOKABEL-ABFRAGE (auf Anfrage):
   Format: "Nenne mir 10 Vokabeln zu [Thema]"
   -> Tabelle: Latein | Stammformen | Deutsch | Deklination/Konjugation

IMMER: Grammatikregeln mit Beispielen erklären.
Bei Fehlern: Freundlich korrigieren und den Fehler erklären.
Verwende Markdown-Tabellen für übersichtliche Darstellung.
Biete am Ende immer eine Übungsaufgabe an.
"""

ALTGRIECHISCH_SYSTEM_PROMPT = """Du bist ein Altgriechisch-Experte und Sprach-Tutor.

ALTGRIECHISCH-SPEZIAL-FAEHIGKEITEN:

1. VOKABEL-TRAINER:
   - Altgriechisch -> Deutsch UND Deutsch -> Altgriechisch
   - Stammformen nennen (Praesens, Futur, Aorist, Perfekt, Perfekt Passiv, Aorist Passiv)
   - Genus & Deklinations-Klasse angeben
   - Etymologie in modernen Sprachen

2. GRAMMATIK-ANALYSE:
   - Satz syntaktisch gliedern
   - Kasus bestimmen + Grund nennen
   - Tempora, Modi & Genera Verbi identifizieren
   - Partizipien bestimmen (Tempus, Kasus, Bezugswort)
   - Konstruktionen erkennen (AcI, AcP, Gen. Abs.)

3. UEBERSETZUNGS-HILFE:
   - Schritt-für-Schritt übersetzen
   - Verb finden -> Tempus/Modus/Genus Verbi bestimmen
   - Subjekt + Objekte zuordnen
   - Partizipien und Infinitivkonstruktionen auflösen
   - Sinngemässe Uebertragung ins Deutsche

4. VOKABEL-ABFRAGE:
   -> Tabelle: Griechisch | Stammformen | Deutsch | Deklination/Konjugation

IMMER: Akzente und Spiritus beachten.
Grammatikregeln mit Beispielen aus bekannten Texten (Homer, Platon).
"""

# Quiz-Typen speziell für alte Sprachen
LATEIN_QUIZ_TYPEN = [
    "vokabeln",          # Latein -> Deutsch / Deutsch -> Latein
    "stammformen",       # Ergaenze die Stammformen
    "kasuserkennung",    # Welchen Kasus hat dieses Wort?
    "konjugation",       # Konjugiere dieses Verb
    "konstruktionen",    # Erkenne die Konstruktion (AcI, Abl. Abs., PC)
    "übersetzung",      # Uebersetze diesen Satz
]

# Verteilung der Quiz-Typen
LATEIN_QUIZ_VERTEILUNG = {
    "vokabeln": 0.30,       # 30%
    "grammatik": 0.30,      # 30% (kasuserkennung + konjugation)
    "stammformen": 0.20,    # 20%
    "konstruktionen": 0.20, # 20%
}


def get_latein_quiz_prompt(quiz_typ: str, thema: str = "", num_questions: int = 10) -> str:
    """Generate a specialized quiz prompt for Latin/Ancient Greek."""
    if quiz_typ == "vokabeln":
        return f"""Erstelle {num_questions} Vokabel-Quizfragen (Latein <-> Deutsch).
Thema: {thema or 'Allgemein'}

Mische:
- 50% Latein -> Deutsch (Multiple Choice mit 4 Optionen)
- 50% Deutsch -> Latein (Multiple Choice mit 4 Optionen)

Bei jeder Frage: Nenne auch die Stammformen in der Erklärung.
FORMAT: JSON Array mit question, options (Array), correct_answer, explanation"""

    elif quiz_typ == "stammformen":
        return f"""Erstelle {num_questions} Stammformen-Quizfragen.
Thema: {thema or 'Wichtige Verben'}

Format jeder Frage:
"Ergaenze die Stammformen: [Verb] - ?, ?, ?, ?"
4 Optionen: 1 richtige Stammformen-Reihe + 3 falsche

FORMAT: JSON Array mit question, options (Array), correct_answer, explanation"""

    elif quiz_typ == "kasuserkennung":
        return f"""Erstelle {num_questions} Kasus-Erkennungsfragen.
Thema: {thema or 'Kasusbestimmung'}

Format: Gib einen lateinischen Satz und frage nach dem Kasus eines markierten Wortes.
Optionen: Nominativ, Genitiv, Dativ, Akkusativ, Ablativ, Vokativ
Erklärung: Warum dieser Kasus? (Funktion im Satz)

FORMAT: JSON Array mit question, options (Array), correct_answer, explanation"""

    elif quiz_typ == "konjugation":
        return f"""Erstelle {num_questions} Konjugations-Quizfragen.
Thema: {thema or 'Verb-Konjugation'}

Mische:
- Bestimme Person/Numerus/Tempus/Modus einer Form
- Bilde die richtige Form (z.B. "3. Pers. Sg. Perfekt Aktiv von amare")
4 Optionen pro Frage.

FORMAT: JSON Array mit question, options (Array), correct_answer, explanation"""

    elif quiz_typ == "konstruktionen":
        return f"""Erstelle {num_questions} Konstruktions-Erkennungsfragen.
Thema: {thema or 'Lateinische Konstruktionen'}

Gib lateinische Sätze mit folgenden Konstruktionen:
- AcI (Accusativus cum Infinitivo)
- Ablativus Absolutus
- Participium Coniunctum
- NcI (Nominativus cum Infinitivo)
- Gerundium/Gerundivum

Frage: "Welche Konstruktion liegt vor?" mit 4 Optionen.
Erklärung: Wie erkennt man sie? Wie übersetzt man sie?

FORMAT: JSON Array mit question, options (Array), correct_answer, explanation"""

    elif quiz_typ == "übersetzung":
        return f"""Erstelle {num_questions} Übersetzungs-Quizfragen.
Thema: {thema or 'Übersetzung'}

Gib kurze lateinische Sätze (1-2 Zeilen) und frage nach der korrekten Übersetzung.
4 Optionen: 1 korrekte, 3 fehlerhafte Übersetzungen (typische Schüler-Fehler).
Erklärung: Schritt-für-Schritt Übersetzungsweg.

FORMAT: JSON Array mit question, options (Array), correct_answer, explanation"""

    else:
        return f"""Erstelle {num_questions} gemischte Latein-Quizfragen.
Thema: {thema or 'Gemischt'}
Mische: Vokabeln (30%), Grammatik (30%), Stammformen (20%), Konstruktionen (20%).
FORMAT: JSON Array mit question, options (Array), correct_answer, explanation"""


def get_spezial_system_prompt(fach: str) -> str:
    """Get the special system prompt for Latin or Ancient Greek."""
    if fach in ("Latein", "latin"):
        return LATEIN_SYSTEM_PROMPT
    elif fach in ("Altgriechisch", "ancient_greek"):
        return ALTGRIECHISCH_SYSTEM_PROMPT
    return ""


def is_latein_modus_fach(fach: str) -> bool:
    """Check if a subject should use the Latin special mode."""
    return fach in ("Latein", "latin", "Altgriechisch", "ancient_greek")
