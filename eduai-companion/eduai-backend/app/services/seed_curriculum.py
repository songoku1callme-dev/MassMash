"""Seed script to index sample German curriculum data into the RAG store.

Run this once to populate the vector store with foundational content
for each subject. This provides immediate RAG context for student queries.

Usage:
    python -m app.services.seed_curriculum
"""
import asyncio
import logging

from app.services import rag_service

logger = logging.getLogger(__name__)

# Sample German curriculum content — curated excerpts covering
# core topics per subject for Gymnasium/Realschule levels.

CURRICULUM_DATA: list[dict] = [
    # ── Mathematik ──────────────────────────────────────────────
    {
        "doc_id": "math-quadratische-gleichungen",
        "content": (
            "Quadratische Gleichungen: Eine quadratische Gleichung hat die Form "
            "ax^2 + bx + c = 0, wobei a != 0. Die Loesungen werden mit der "
            "Mitternachtsformel (abc-Formel) berechnet: x = (-b +/- sqrt(b^2 - 4ac)) / (2a). "
            "Die Diskriminante D = b^2 - 4ac bestimmt die Anzahl der Loesungen: "
            "D > 0: zwei reelle Loesungen, D = 0: eine doppelte Loesung, D < 0: keine reelle Loesung. "
            "Beispiel: x^2 - 5x + 6 = 0. Hier ist a=1, b=-5, c=6. "
            "D = 25 - 24 = 1 > 0. x1 = (5+1)/2 = 3, x2 = (5-1)/2 = 2. "
            "Alternativ kann man quadratische Gleichungen durch Faktorisierung loesen: "
            "x^2 - 5x + 6 = (x-2)(x-3) = 0. Der Satz von Vieta besagt: "
            "x1 + x2 = -b/a und x1 * x2 = c/a."
        ),
        "metadata": {"subject": "math", "topic": "Quadratische Gleichungen", "level": "intermediate",
                      "source": "Lehrplan Mathematik, Sekundarstufe I", "language": "de"},
    },
    {
        "doc_id": "math-satz-des-pythagoras",
        "content": (
            "Der Satz des Pythagoras: In einem rechtwinkligen Dreieck gilt: "
            "a^2 + b^2 = c^2, wobei c die Hypotenuse (gegenueber dem rechten Winkel) ist "
            "und a, b die Katheten sind. Anwendung: Berechne die Laenge der Hypotenuse "
            "eines rechtwinkligen Dreiecks mit Katheten a=3 und b=4: c = sqrt(9+16) = sqrt(25) = 5. "
            "Umkehrung: Wenn a^2 + b^2 = c^2 gilt, ist das Dreieck rechtwinklig. "
            "Pythagoraeische Tripel: (3,4,5), (5,12,13), (8,15,17), (7,24,25). "
            "Anwendungen: Abstandsberechnungen, Dachneigung, Navigation."
        ),
        "metadata": {"subject": "math", "topic": "Satz des Pythagoras", "level": "beginner",
                      "source": "Lehrplan Mathematik, Klasse 8", "language": "de"},
    },
    {
        "doc_id": "math-trigonometrie",
        "content": (
            "Trigonometrie am rechtwinkligen Dreieck: "
            "sin(alpha) = Gegenkathete / Hypotenuse, "
            "cos(alpha) = Ankathete / Hypotenuse, "
            "tan(alpha) = Gegenkathete / Ankathete. "
            "Wichtige Werte: sin(30) = 0.5, cos(30) = sqrt(3)/2, tan(45) = 1. "
            "Einheitskreis: sin^2(x) + cos^2(x) = 1 fuer alle x. "
            "Bogenmas: 180 Grad = pi Radiant. "
            "Sinussatz: a/sin(A) = b/sin(B) = c/sin(C). "
            "Kosinussatz: c^2 = a^2 + b^2 - 2ab*cos(C)."
        ),
        "metadata": {"subject": "math", "topic": "Trigonometrie", "level": "intermediate",
                      "source": "Lehrplan Mathematik, Klasse 9-10", "language": "de"},
    },
    {
        "doc_id": "math-lineare-funktionen",
        "content": (
            "Lineare Funktionen: Eine lineare Funktion hat die Form f(x) = mx + b, "
            "wobei m die Steigung und b der y-Achsenabschnitt ist. "
            "Die Steigung berechnet sich als m = (y2-y1)/(x2-x1) = Deltahy/Deltax. "
            "Parallele Geraden haben gleiche Steigung. "
            "Senkrechte Geraden: m1 * m2 = -1. "
            "Nullstelle: f(x) = 0, also x = -b/m. "
            "Schnittpunkt zweier Geraden: mx+b = nx+d, Gleichsetzungsverfahren."
        ),
        "metadata": {"subject": "math", "topic": "Lineare Funktionen", "level": "beginner",
                      "source": "Lehrplan Mathematik, Klasse 7-8", "language": "de"},
    },

    # ── Physik / Science ────────────────────────────────────────
    {
        "doc_id": "science-newton-gesetze",
        "content": (
            "Newtons drei Gesetze der Mechanik: "
            "1. Gesetz (Traegheitsgesetz): Ein Koerper verharrt im Zustand der Ruhe oder "
            "der gleichfoermigen Bewegung, solange keine aeussere Kraft auf ihn wirkt. "
            "2. Gesetz (Aktionsprinzip): Kraft = Masse * Beschleunigung, F = m * a. "
            "Die Einheit der Kraft ist Newton (N): 1 N = 1 kg * m/s^2. "
            "3. Gesetz (Wechselwirkungsprinzip): Actio = Reactio. Wenn Koerper A auf "
            "Koerper B eine Kraft ausuebt, uebt B auf A eine gleichgrosse, entgegengesetzte Kraft aus. "
            "Beispiel: Ein Auto (1000 kg) beschleunigt mit 2 m/s^2. "
            "Die benoetigte Kraft ist F = 1000 * 2 = 2000 N."
        ),
        "metadata": {"subject": "science", "topic": "Newtonsche Gesetze", "level": "intermediate",
                      "source": "Lehrplan Physik, Klasse 9", "language": "de"},
    },
    {
        "doc_id": "science-energie",
        "content": (
            "Energie und Energieerhaltung: Energie kann nicht erzeugt oder vernichtet, "
            "nur umgewandelt werden (Energieerhaltungssatz). "
            "Kinetische Energie: Ekin = 0.5 * m * v^2. "
            "Potentielle Energie: Epot = m * g * h (mit g = 9.81 m/s^2). "
            "Arbeit: W = F * s (Kraft mal Weg). Leistung: P = W/t (Arbeit pro Zeit). "
            "Einheiten: Energie in Joule (J), Leistung in Watt (W). "
            "1 kWh = 3.6 * 10^6 J. "
            "Energieumwandlungen: Wasserkraftwerk (potentielle -> kinetische -> elektrische), "
            "Solarzelle (Strahlungsenergie -> elektrische), Photosynthese (Licht -> chemische)."
        ),
        "metadata": {"subject": "science", "topic": "Energie", "level": "intermediate",
                      "source": "Lehrplan Physik, Klasse 8-9", "language": "de"},
    },
    {
        "doc_id": "science-periodensystem",
        "content": (
            "Das Periodensystem der Elemente (PSE): Ordnet alle chemischen Elemente nach "
            "steigender Ordnungszahl (Protonenzahl). Perioden (Zeilen) geben die Anzahl der "
            "Elektronenschalen an. Gruppen (Spalten) bestimmen die chemischen Eigenschaften. "
            "Hauptgruppen: I (Alkalimetalle, z.B. Na, K), VII (Halogene, z.B. Cl, Br), "
            "VIII (Edelgase, z.B. He, Ne, Ar). "
            "Elektronenkonfiguration bestimmt die Reaktivitaet. "
            "Oktettregel: Atome streben 8 Valenzelektronen an. "
            "Ionenbindung: Metall gibt Elektronen ab, Nichtmetall nimmt auf (z.B. NaCl). "
            "Kovalente Bindung: Atome teilen Elektronenpaare (z.B. H2O, CO2)."
        ),
        "metadata": {"subject": "science", "topic": "Periodensystem", "level": "intermediate",
                      "source": "Lehrplan Chemie, Klasse 8-9", "language": "de"},
    },

    # ── Deutsch ─────────────────────────────────────────────────
    {
        "doc_id": "german-grammatik-kasus",
        "content": (
            "Die vier Faelle (Kasus) im Deutschen: "
            "1. Nominativ (Wer/Was?): Der Hund bellt. "
            "2. Genitiv (Wessen?): Das Buch des Lehrers. "
            "3. Dativ (Wem?): Ich gebe dem Kind ein Geschenk. "
            "4. Akkusativ (Wen/Was?): Ich sehe den Baum. "
            "Praepositionen mit Dativ: aus, bei, mit, nach, seit, von, zu. "
            "Praepositionen mit Akkusativ: durch, fuer, gegen, ohne, um. "
            "Wechselpraepositionen (Dativ bei Ort, Akkusativ bei Richtung): "
            "an, auf, hinter, in, neben, ueber, unter, vor, zwischen. "
            "Beispiel: 'Das Buch liegt auf dem Tisch' (Dativ, Ort) vs. "
            "'Ich lege das Buch auf den Tisch' (Akkusativ, Richtung)."
        ),
        "metadata": {"subject": "german", "topic": "Kasus", "level": "beginner",
                      "source": "Lehrplan Deutsch, Grammatik Grundlagen", "language": "de"},
    },
    {
        "doc_id": "german-erörterung",
        "content": (
            "Die Eroerterung (Argumentation): Eine schriftliche Auseinandersetzung mit einem Thema. "
            "Aufbau einer linearen Eroerterung: Einleitung (Thema vorstellen, Aktualitaet), "
            "Hauptteil (Argumente vom schwaechsten zum staerksten, jeweils mit Begruendung und Beispiel), "
            "Schluss (Zusammenfassung, eigene Meinung, Ausblick). "
            "Dialektische Eroerterung: Pro- und Contra-Argumente abwaegen. "
            "Aufbau: Einleitung, These, Antithese, Synthese, Schluss. "
            "Tipps: Sachlich bleiben, Konjunktionen verwenden (deshalb, darum, obwohl, dennoch), "
            "Beispiele aus dem Alltag einbringen, verschiedene Perspektiven beruecksichtigen."
        ),
        "metadata": {"subject": "german", "topic": "Erörterung", "level": "intermediate",
                      "source": "Lehrplan Deutsch, Aufsatz Klasse 9-10", "language": "de"},
    },

    # ── Englisch ────────────────────────────────────────────────
    {
        "doc_id": "english-tenses",
        "content": (
            "English Tenses Overview: "
            "Simple Present: habitual actions ('She reads every day'). "
            "Present Continuous: actions happening now ('She is reading'). "
            "Simple Past: completed actions ('She read yesterday'). "
            "Past Continuous: ongoing past actions ('She was reading when I arrived'). "
            "Present Perfect: past actions with present relevance ('She has read 5 books this year'). "
            "Past Perfect: action completed before another past action ('She had read the book before the exam'). "
            "Future: will + base form ('She will read') or going to ('She is going to read'). "
            "Signal words: always, every day (Simple Present); now, at the moment (Present Continuous); "
            "yesterday, last week (Simple Past); since, for, already, yet (Present Perfect)."
        ),
        "metadata": {"subject": "english", "topic": "Tenses", "level": "beginner",
                      "source": "Lehrplan Englisch, Grammatik Grundlagen", "language": "en"},
    },
    {
        "doc_id": "english-conditional",
        "content": (
            "Conditional Sentences (If-Clauses): "
            "Type 0 (General truth): If + Present, Present. 'If you heat water to 100C, it boils.' "
            "Type 1 (Real/likely): If + Present, will + base. 'If it rains, I will stay home.' "
            "Type 2 (Unreal/unlikely): If + Past Simple, would + base. 'If I were rich, I would travel.' "
            "Type 3 (Impossible/past): If + Past Perfect, would have + Past Participle. "
            "'If I had studied, I would have passed.' "
            "Mixed Conditionals: combine Type 2 and 3 for past condition with present result or vice versa."
        ),
        "metadata": {"subject": "english", "topic": "Conditional Sentences", "level": "intermediate",
                      "source": "Lehrplan Englisch, Klasse 9-10", "language": "en"},
    },

    # ── Geschichte ──────────────────────────────────────────────
    {
        "doc_id": "history-weimarer-republik",
        "content": (
            "Die Weimarer Republik (1918-1933): Nach dem Ende des Ersten Weltkriegs "
            "wurde am 9. November 1918 die Republik ausgerufen. Die Weimarer Verfassung "
            "vom 11. August 1919 etablierte eine parlamentarische Demokratie mit "
            "Reichspraesident, Reichskanzler und Reichstag. "
            "Herausforderungen: Versailler Vertrag (Reparationen, Gebietsabtretungen), "
            "Hyperinflation 1923, politische Instabilitaet (haeufige Regierungswechsel), "
            "Weltwirtschaftskrise ab 1929. "
            "Die 'Goldenen Zwanziger' (1924-1929): wirtschaftliche Erholung durch den Dawes-Plan, "
            "kulturelle Bluete (Bauhaus, Expressionismus, Film). "
            "Ende: Ernennung Hitlers zum Reichskanzler am 30. Januar 1933, "
            "Ermaechtigungsgesetz vom 24. Maerz 1933 beendete die Demokratie."
        ),
        "metadata": {"subject": "history", "topic": "Weimarer Republik", "level": "intermediate",
                      "source": "Lehrplan Geschichte, Klasse 9-10", "language": "de"},
    },
    {
        "doc_id": "history-industrialisierung",
        "content": (
            "Die Industrialisierung in Deutschland (ca. 1830-1900): "
            "Beginn spaeter als in England. Wichtige Faktoren: Eisenbahnbau (erste Eisenbahn "
            "Nuernberg-Fuerth 1835), Zollverein (1834), Kohle- und Stahlproduktion im Ruhrgebiet. "
            "Soziale Folgen: Urbanisierung, Entstehung der Arbeiterklasse, Kinderarbeit, "
            "schlechte Arbeitsbedingungen, Wohnungsnot. "
            "Politische Reaktionen: Arbeiterbewegung, Gruendung der SPD (1875), "
            "Bismarcks Sozialgesetzgebung (Krankenversicherung 1883, Unfallversicherung 1884, "
            "Rentenversicherung 1889). "
            "Zweite Industrielle Revolution: Elektrotechnik (Siemens), Chemie (BASF, Bayer), "
            "Automobilbau (Benz, Daimler)."
        ),
        "metadata": {"subject": "history", "topic": "Industrialisierung", "level": "intermediate",
                      "source": "Lehrplan Geschichte, Klasse 8-9", "language": "de"},
    },
]


async def seed_curriculum() -> int:
    """Index all sample curriculum documents. Returns count of documents indexed."""
    total = 0
    for doc in CURRICULUM_DATA:
        try:
            chunks = await rag_service.index_document(
                doc_id=doc["doc_id"],
                content=doc["content"],
                metadata=doc["metadata"],
            )
            logger.info("Indexed %s: %d chunks", doc["doc_id"], chunks)
            total += 1
        except Exception as err:
            logger.error("Failed to index %s: %s", doc["doc_id"], err)
    logger.info("Seeded %d / %d curriculum documents", total, len(CURRICULUM_DATA))
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_curriculum())
