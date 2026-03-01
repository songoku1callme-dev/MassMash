"""Quiz Topics Service - 300+ Abitur-Themen across 16 Fächer.

Provides structured quiz topics for the topic selector UI.
Topics are tier-locked: Free gets basic topics, Pro gets more, Max gets all.
16 Subjects: Mathe, Deutsch, Englisch, Physik, Chemie, Biologie, Geschichte,
Geografie, Wirtschaft, Ethik, Informatik, Kunst, Musik, Sozialkunde, Latein, Französisch.
"""
from typing import Optional

# Subject mapping: internal ID -> display info
SUBJECT_MAP = {
    "math": {"name": "Mathematik", "icon": "Calculator", "emoji": "\U0001f522"},
    "german": {"name": "Deutsch", "icon": "BookOpen", "emoji": "\U0001f4d6"},
    "english": {"name": "Englisch", "icon": "Languages", "emoji": "\U0001f1ec\U0001f1e7"},
    "physics": {"name": "Physik", "icon": "Atom", "emoji": "\u269b\ufe0f"},
    "chemistry": {"name": "Chemie", "icon": "FlaskConical", "emoji": "\U0001f9ea"},
    "biology": {"name": "Biologie", "icon": "Dna", "emoji": "\U0001f9ec"},
    "history": {"name": "Geschichte", "icon": "Clock", "emoji": "\U0001f3db\ufe0f"},
    "geography": {"name": "Geografie", "icon": "Globe", "emoji": "\U0001f30d"},
    "economics": {"name": "Wirtschaft", "icon": "TrendingUp", "emoji": "\U0001f4c8"},
    "ethics": {"name": "Ethik", "icon": "Scale", "emoji": "\u2696\ufe0f"},
    "computer_science": {"name": "Informatik", "icon": "Monitor", "emoji": "\U0001f4bb"},
    "art": {"name": "Kunst", "icon": "Palette", "emoji": "\U0001f3a8"},
    "music": {"name": "Musik", "icon": "Music", "emoji": "\U0001f3b5"},
    "social_studies": {"name": "Sozialkunde", "icon": "Users", "emoji": "\U0001f465"},
    "latin": {"name": "Latein", "icon": "Scroll", "emoji": "\U0001f3db\ufe0f"},
    "french": {"name": "Französisch", "icon": "Languages", "emoji": "\U0001f1eb\U0001f1f7"},
}

# 300+ topics across 16 subjects
QUIZ_TOPICS = {
    # === MATHEMATIK (30 Themen) ===
    "math": [
        # Free (10)
        {"id": "math_grundrechenarten", "name": "Grundrechenarten", "tier": "free", "difficulty_range": [1, 2]},
        {"id": "math_bruchrechnung", "name": "Bruchrechnung", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "math_prozentrechnung", "name": "Prozentrechnung", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "math_lineare_gleichungen", "name": "Lineare Gleichungen", "tier": "free", "difficulty_range": [1, 4]},
        {"id": "math_geometrie_basics", "name": "Geometrie Grundlagen", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "math_dreisatz", "name": "Dreisatz & Proportionalit\u00e4t", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "math_terme_vereinfachen", "name": "Terme & Vereinfachung", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "math_potenzen", "name": "Potenzen & Wurzeln", "tier": "free", "difficulty_range": [2, 4]},
        {"id": "math_flaechen_volumen", "name": "Fl\u00e4chen & Volumen", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "math_gleichungssysteme", "name": "Gleichungssysteme", "tier": "free", "difficulty_range": [2, 4]},
        # Pro (10)
        {"id": "math_quadratische_funktionen", "name": "Quadratische Funktionen", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "math_polynomdivision", "name": "Polynomdivision", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "math_logarithmen", "name": "Logarithmen", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "math_trigonometrie", "name": "Trigonometrie", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "math_exponentialfunktionen", "name": "Exponentialfunktionen", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "math_stochastik", "name": "Stochastik & Wahrscheinlichkeit", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "math_statistik", "name": "Statistik & Datenanalyse", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "math_analytische_geometrie", "name": "Analytische Geometrie", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "math_vektoren", "name": "Vektorrechnung", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "math_folgen_reihen", "name": "Folgen & Reihen", "tier": "pro", "difficulty_range": [3, 5]},
        # Max (10)
        {"id": "math_differentialrechnung", "name": "Differentialrechnung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "math_integralrechnung", "name": "Integralrechnung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "math_lineare_algebra", "name": "Lineare Algebra & Matrizen", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "math_kurvendiskussion", "name": "Kurvendiskussion", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "math_komplexe_zahlen", "name": "Komplexe Zahlen", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "math_abitur_musterklausuren", "name": "Abitur-Musterklausuren", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "math_mathe_olympiade", "name": "Mathe-Olympiade Aufgaben", "tier": "max", "difficulty_range": [5, 5]},
        {"id": "math_grenzwerte", "name": "Grenzwerte & Stetigkeit", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "math_wahrscheinlichkeitsverteilungen", "name": "Wahrscheinlichkeitsverteilungen", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "math_ebenengleichungen", "name": "Ebenengleichungen & Abst\u00e4nde", "tier": "max", "difficulty_range": [4, 5]},
    ],
    # === DEUTSCH (25 Themen) ===
    "german": [
        # Free (8)
        {"id": "de_nomen_deklination", "name": "Nomen-Deklination", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "de_adjektiv_deklination", "name": "Adjektiv-Deklination", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "de_konjugation_praesens", "name": "Konjugation Pr\u00e4sens", "tier": "free", "difficulty_range": [1, 2]},
        {"id": "de_perfekt_plusquamperfekt", "name": "Perfekt/Plusquamperfekt", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "de_rechtschreibung", "name": "Rechtschreibung", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "de_plural", "name": "Plural & Deklination", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "de_artikel_kasus", "name": "Artikel & Kasus", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "de_satzbau", "name": "Satzbau & Wortstellung", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (9)
        {"id": "de_passivformen", "name": "Passivformen", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "de_konjunktiv_i", "name": "Konjunktiv I", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "de_konjunktiv_ii", "name": "Konjunktiv II", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "de_partizip", "name": "Partizip I/II", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "de_aufsatz_argumentieren", "name": "Aufsatz Argumentieren", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "de_aufsatz_beschreiben", "name": "Aufsatz Beschreiben", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "de_aufsatz_eroertern", "name": "Aufsatz Er\u00f6rtern", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "de_kommasetzung", "name": "Kommasetzung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "de_indirekte_rede", "name": "Indirekte Rede", "tier": "pro", "difficulty_range": [2, 4]},
        # Max (8)
        {"id": "de_lyrikanalyse", "name": "Lyrikanalyse", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_dramenanalyse", "name": "Dramenanalyse", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_epoche_barock", "name": "Epoche Barock", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_sturm_drang", "name": "Sturm & Drang", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_romantik", "name": "Romantik", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_realismus", "name": "Realismus", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_stilmittel", "name": "Stilmittel & Rhetorik", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "de_abitur_deutsch", "name": "Abitur-Deutsch", "tier": "max", "difficulty_range": [4, 5]},
    ],
    # === ENGLISCH (20 Themen) ===
    "english": [
        # Free (6)
        {"id": "en_simple_tenses", "name": "Simple Tenses", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "en_to_be", "name": "To Be & Basics", "tier": "free", "difficulty_range": [1, 2]},
        {"id": "en_irregular_verbs", "name": "Irregular Verbs", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "en_present_perfect", "name": "Present Perfect", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "en_comparisons", "name": "Comparisons & Adjectives", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "en_prepositions", "name": "Prepositions", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (8)
        {"id": "en_conditional", "name": "Conditional Sentences", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "en_passive_voice", "name": "Passive Voice", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "en_reported_speech", "name": "Reported Speech", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "en_relative_clauses", "name": "Relative Clauses", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "en_gerund_infinitive", "name": "Gerund vs Infinitive", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "en_modals", "name": "Modal Verbs", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "en_essay_writing", "name": "Essay Writing", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "en_reading_comprehension", "name": "Reading Comprehension", "tier": "pro", "difficulty_range": [2, 5]},
        # Max (6)
        {"id": "en_advanced_grammar", "name": "Advanced Grammar & Inversion", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "en_idioms", "name": "Idioms & Phrasal Verbs", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "en_literary_analysis", "name": "Literary Analysis", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "en_mediation", "name": "Mediation/Sprachmittlung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "en_speaking_discussion", "name": "Speaking & Discussion", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "en_abitur_englisch", "name": "Abitur-Englisch", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "en_vocabulary_b2", "name": "Vocabulary B2 Level", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "en_collocations", "name": "Collocations & Word Formation", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "en_listening", "name": "Listening Comprehension", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "en_american_british", "name": "American vs British English", "tier": "free", "difficulty_range": [1, 3]},
    ],
    # === PHYSIK (20 Themen) ===
    "physics": [
        # Free (6)
        {"id": "phy_kinematik", "name": "Kinematik", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "phy_newtons_axiome", "name": "Newtons Axiome", "tier": "free", "difficulty_range": [1, 4]},
        {"id": "phy_dynamik", "name": "Dynamik", "tier": "free", "difficulty_range": [2, 4]},
        {"id": "phy_arbeit_energie", "name": "Arbeit & Energie", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "phy_leistung", "name": "Leistung", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "phy_druck_auftrieb", "name": "Druck & Auftrieb", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (8)
        {"id": "phy_elektrostatik", "name": "Elektrostatik", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "phy_stromkreise", "name": "Stromkreise", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "phy_magnetismus", "name": "Magnetismus", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "phy_optik_wellen", "name": "Optik & Wellen", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "phy_schwingungen", "name": "Schwingungen", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "phy_akustik", "name": "Akustik", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "phy_waermelehre", "name": "W\u00e4rmelehre", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "phy_induktion", "name": "Elektromagnetische Induktion", "tier": "pro", "difficulty_range": [3, 5]},
        # Max (6)
        {"id": "phy_thermodynamik", "name": "Thermodynamik 1. Hauptsatz", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "phy_quantenphysik", "name": "Quantenphysik Einf\u00fchrung", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "phy_relativitaet", "name": "Spezielle Relativit\u00e4tstheorie", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "phy_kernphysik", "name": "Kern- & Atomphysik", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "phy_halbleiter", "name": "Halbleiterphysik", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "phy_abitur_physik", "name": "Abitur-Physik", "tier": "max", "difficulty_range": [4, 5]},
    ],
    # === CHEMIE (18 Themen) ===
    "chemistry": [
        # Free (5)
        {"id": "che_periodensystem", "name": "Periodensystem", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "che_atombau", "name": "Atombau & Elektronenh\u00fclle", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "che_chemische_bindung", "name": "Chemische Bindung", "tier": "free", "difficulty_range": [1, 4]},
        {"id": "che_aggregatzustaende", "name": "Aggregatzust\u00e4nde", "tier": "free", "difficulty_range": [1, 2]},
        {"id": "che_stoffgemische", "name": "Stoffgemische & Trennverfahren", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (7)
        {"id": "che_saeure_base", "name": "S\u00e4ure-Base-Theorie", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "che_redox", "name": "Redox-Reaktionen", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "che_stoichiometrie", "name": "St\u00f6chiometrie", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "che_loesungen", "name": "L\u00f6sungen & Konzentration", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "che_elektrochemie", "name": "Elektrochemie", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "che_reaktionskinetik", "name": "Reaktionskinetik", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "che_gleichgewicht", "name": "Chemisches Gleichgewicht", "tier": "pro", "difficulty_range": [3, 5]},
        # Max (6)
        {"id": "che_alkane", "name": "Organische Chemie: Alkane", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "che_alkene", "name": "Organische Chemie: Alkene", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "che_alkohole", "name": "Alkohole & Ether", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "che_carbonsaeuren", "name": "Carbons\u00e4uren & Ester", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "che_kunststoffe", "name": "Kunststoffe & Polymere", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "che_abitur_chemie", "name": "Abitur-Chemie", "tier": "max", "difficulty_range": [4, 5]},
    ],
    # === BIOLOGIE (20 Themen) ===
    "biology": [
        # Free (6)
        {"id": "bio_zellbiologie", "name": "Zellbiologie", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "bio_pflanzenkunde", "name": "Pflanzenkunde", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "bio_oekosysteme", "name": "\u00d6kosysteme", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "bio_menschlicher_koerper", "name": "Menschlicher K\u00f6rper", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "bio_sinnesorgane", "name": "Sinnesorgane", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "bio_ernaehrung", "name": "Ern\u00e4hrung & Verdauung", "tier": "free", "difficulty_range": [1, 3]},
        # Pro (8)
        {"id": "bio_dna_replikation", "name": "DNA-Replikation", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "bio_proteinbiosynthese", "name": "Proteinbiosynthese", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "bio_genetik_mendel", "name": "Genetik: Mendel'sche Regeln", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "bio_immunsystem", "name": "Immunsystem", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "bio_nervensystem", "name": "Nervensystem", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "bio_photosynthese", "name": "Photosynthese", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "bio_atmung", "name": "Zellatmung", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "bio_hormonsystem", "name": "Hormonsystem", "tier": "pro", "difficulty_range": [2, 4]},
        # Max (6)
        {"id": "bio_evolution_darwin", "name": "Evolution: Darwin", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "bio_humangenetik", "name": "Humangenetik", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "bio_gentechnik", "name": "Gentechnik & Bioethik", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "bio_neurobiologie", "name": "Neurobiologie", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "bio_verhaltensbiologie", "name": "Verhaltensbiologie", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "bio_abitur_bio", "name": "Abitur-Biologie", "tier": "max", "difficulty_range": [4, 5]},
    ],
    # === GESCHICHTE (25 Themen) ===
    "history": [
        # Free (8)
        {"id": "hist_antikes_griechenland", "name": "Antikes Griechenland", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "hist_roemische_kaiserzeit", "name": "R\u00f6mische Kaiserzeit", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "hist_mittelalter", "name": "Mittelalter & Feudalismus", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "hist_reformation", "name": "Reformation", "tier": "free", "difficulty_range": [2, 4]},
        {"id": "hist_erster_weltkrieg", "name": "Erster Weltkrieg", "tier": "free", "difficulty_range": [1, 4]},
        {"id": "hist_zweiter_weltkrieg", "name": "Zweiter Weltkrieg", "tier": "free", "difficulty_range": [1, 4]},
        {"id": "hist_weimarer_republik", "name": "Weimarer Republik", "tier": "free", "difficulty_range": [1, 4]},
        {"id": "hist_nationalsozialismus", "name": "Nationalsozialismus", "tier": "free", "difficulty_range": [2, 5]},
        # Pro (9)
        {"id": "hist_absolutismus", "name": "Absolutismus", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "hist_franz_revolution", "name": "Franz\u00f6sische Revolution", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "hist_industrialisierung", "name": "Industrialisierung", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "hist_kalter_krieg", "name": "Kalter Krieg", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "hist_wiedervereinigung", "name": "Deutsche Wiedervereinigung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "hist_imperialismus", "name": "Imperialismus & Kolonialismus", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "hist_deutsches_kaiserreich", "name": "Deutsches Kaiserreich", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "hist_aufklaerung", "name": "Aufkl\u00e4rung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "hist_revolution_1848", "name": "Revolution 1848/49", "tier": "pro", "difficulty_range": [3, 5]},
        # Max (8)
        {"id": "hist_nachkriegszeit", "name": "Nachkriegszeit 1945-1949", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "hist_brd_ddr", "name": "BRD & DDR im Vergleich", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "hist_europaeische_integration", "name": "Europ\u00e4ische Integration", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "hist_nahostkonflikt", "name": "Nahostkonflikt", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "hist_globalisierung", "name": "Globalisierung & Zeitgeschichte", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "hist_geschichtstheorie", "name": "Geschichtstheorie & Methodik", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "hist_quellenanalyse", "name": "Quellenanalyse", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "hist_abitur_geschichte", "name": "Abitur-Geschichte", "tier": "max", "difficulty_range": [4, 5]},
    ],
    # === GEOGRAFIE (15 Themen) ===
    "geography": [
        {"id": "geo_klimazonen", "name": "Klimazonen", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "geo_plattentektonik", "name": "Plattentektonik", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "geo_deutschland", "name": "Deutschland Wirtschaftsr\u00e4ume", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "geo_europa", "name": "Europa Topografie", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "geo_wetter", "name": "Wetter & Klima", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "geo_bevoelkerung", "name": "Bev\u00f6lkerungspyramiden", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "geo_urbanisierung", "name": "Urbanisierung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "geo_klimaerwaermung", "name": "Klimaerw\u00e4rmung", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "geo_nachhaltigkeit", "name": "Nachhaltigkeit", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "geo_globalisierung", "name": "Globalisierung", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "geo_entwicklungslaender", "name": "Entwicklungsl\u00e4nder", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "geo_ressourcen", "name": "Ressourcen & Energie", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "geo_stadtgeographie", "name": "Stadtgeographie", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "geo_geomorphologie", "name": "Geomorphologie", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "geo_abitur_geo", "name": "Abitur-Geografie", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "geo_landwirtschaft", "name": "Landwirtschaft & Ern\u00e4hrung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "geo_tourismus", "name": "Tourismus & Raumplanung", "tier": "pro", "difficulty_range": [2, 4]},
    ],
    # === WIRTSCHAFT (15 Themen) ===
    "economics": [
        {"id": "eco_angebot_nachfrage", "name": "Angebot & Nachfrage", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "eco_geld_inflation", "name": "Geld & Inflation", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "eco_marktformen", "name": "Marktformen", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "eco_unternehmen", "name": "Unternehmensformen", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "eco_steuern", "name": "Steuern & Abgaben", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "eco_konjunktur", "name": "Konjunkturzyklen", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "eco_wirtschaftspolitik", "name": "Wirtschaftspolitik", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "eco_aussenhandel", "name": "Au\u00dfenhandel & EU", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "eco_arbeitsmarkt", "name": "Arbeitsmarkt", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "eco_sozialversicherung", "name": "Sozialversicherung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "eco_bip_volkswirtschaft", "name": "BIP & Volkswirtschaft", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "eco_globale_maerkte", "name": "Globale Finanzm\u00e4rkte", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "eco_nachhaltiges_wirtschaften", "name": "Nachhaltiges Wirtschaften", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "eco_wirtschaftsethik", "name": "Wirtschaftsethik", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "eco_abitur_wirtschaft", "name": "Abitur-Wirtschaft", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "eco_marketing", "name": "Marketing & Werbung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "eco_buchfuehrung", "name": "Buchf\u00fchrung & Bilanz", "tier": "pro", "difficulty_range": [2, 4]},
    ],
    # === ETHIK (15 Themen) ===
    "ethics": [
        {"id": "eth_grundbegriffe", "name": "Ethik Grundbegriffe", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "eth_menschenrechte", "name": "Menschenrechte", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "eth_gerechtigkeit", "name": "Gerechtigkeit & Fairness", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "eth_verantwortung", "name": "Verantwortung & Freiheit", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "eth_utilitarismus", "name": "Utilitarismus", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "eth_kant", "name": "Kants Ethik", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "eth_medienethik", "name": "Medienethik & Datenschutz", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "eth_umweltethik", "name": "Umweltethik", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "eth_bioethik", "name": "Bioethik", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "eth_technikethik", "name": "Technik- & KI-Ethik", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "eth_religionsphilosophie", "name": "Religionsphilosophie", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "eth_abitur_ethik", "name": "Abitur-Ethik", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "eth_tugendethik", "name": "Tugendethik (Aristoteles)", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "eth_sterbehilfe", "name": "Sterbehilfe-Debatte", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "eth_tierethik", "name": "Tierethik", "tier": "pro", "difficulty_range": [2, 4]},
    ],
    # === INFORMATIK (18 Themen) ===
    "computer_science": [
        {"id": "inf_grundlagen", "name": "Informatik Grundlagen", "tier": "free", "difficulty_range": [1, 2]},
        {"id": "inf_binaersystem", "name": "Bin\u00e4r- & Hexadezimalsystem", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "inf_algorithmen_basics", "name": "Algorithmen Grundlagen", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "inf_html_css", "name": "HTML & CSS", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "inf_netzwerke", "name": "Netzwerke Basics", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "inf_python", "name": "Python Programmierung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "inf_datenstrukturen", "name": "Datenstrukturen", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "inf_datenbanken", "name": "Datenbanken & SQL", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "inf_objektorientierung", "name": "Objektorientierung", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "inf_kryptographie", "name": "Kryptographie", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "inf_automaten", "name": "Automaten & Formale Sprachen", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "inf_ki_basics", "name": "K\u00fcnstliche Intelligenz", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "inf_sortieralgorithmen", "name": "Sortier- & Suchalgorithmen", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "inf_softwareentwicklung", "name": "Softwareentwicklung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "inf_abitur_informatik", "name": "Abitur-Informatik", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "inf_rekursion", "name": "Rekursion", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "inf_graphen", "name": "Graphen & B\u00e4ume", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "inf_betriebssysteme", "name": "Betriebssysteme", "tier": "pro", "difficulty_range": [2, 4]},
    ],
    # === KUNST (13 Themen) ===
    "art": [
        {"id": "art_farblehre", "name": "Farblehre & Farbtheorie", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "art_perspektive", "name": "Perspektive & Komposition", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "art_kunstgeschichte_basics", "name": "Kunstgeschichte \u00dcberblick", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "art_renaissance", "name": "Renaissance & Barock", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "art_impressionismus", "name": "Impressionismus", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "art_expressionismus", "name": "Expressionismus", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "art_design", "name": "Design & Gestaltung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "art_moderne", "name": "Moderne & Zeitgen\u00f6ssische Kunst", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "art_bildanalyse", "name": "Bildanalyse & Interpretation", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "art_abitur_kunst", "name": "Abitur-Kunst", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "art_fotografie", "name": "Fotografie & Bildmedien", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "art_architektur", "name": "Architektur & Raumgestaltung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "art_skulptur", "name": "Plastik & Skulptur", "tier": "pro", "difficulty_range": [2, 4]},
    ],
    # === MUSIK (13 Themen) ===
    "music": [
        {"id": "mus_notenlehre", "name": "Notenlehre & Tonleitern", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "mus_rhythmus", "name": "Rhythmus & Takt", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "mus_instrumente", "name": "Instrumentenkunde", "tier": "free", "difficulty_range": [1, 2]},
        {"id": "mus_musikgeschichte", "name": "Musikgeschichte Epochen", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "mus_harmonielehre", "name": "Harmonielehre", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "mus_formenlehre", "name": "Formenlehre", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "mus_pop_rock", "name": "Pop & Rock Analyse", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "mus_werkanalyse", "name": "Werkanalyse", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "mus_filmmusik", "name": "Filmmusik & Medien", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "mus_abitur_musik", "name": "Abitur-Musik", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "mus_klassik", "name": "Klassik: Mozart, Beethoven", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "mus_jazz", "name": "Jazz & Improvisation", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "mus_elektronisch", "name": "Elektronische Musik", "tier": "pro", "difficulty_range": [2, 4]},
    ],
    # === SOZIALKUNDE (15 Themen) ===
    "social_studies": [
        {"id": "soz_demokratie", "name": "Demokratie & Grundgesetz", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "soz_bundestag", "name": "Bundestag & Bundesrat", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "soz_wahlen", "name": "Wahlen & Parteien", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "soz_grundrechte", "name": "Grundrechte", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "soz_eu", "name": "Europ\u00e4ische Union", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "soz_medien", "name": "Medien & Meinungsbildung", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "soz_soziale_ungleichheit", "name": "Soziale Ungleichheit", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "soz_migration", "name": "Migration & Integration", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "soz_internationale_politik", "name": "Internationale Politik", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "soz_friedenssicherung", "name": "Friedenssicherung & UNO", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "soz_rechtsordnung", "name": "Deutsche Rechtsordnung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "soz_abitur_sozialkunde", "name": "Abitur-Sozialkunde", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "soz_lobbyismus", "name": "Lobbyismus & Interessengruppen", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "soz_populismus", "name": "Populismus & Extremismus", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "soz_digitalisierung", "name": "Digitalisierung & Gesellschaft", "tier": "pro", "difficulty_range": [2, 4]},
    ],
    # === LATEIN (15 Themen) ===
    "latin": [
        {"id": "lat_deklinationen", "name": "Deklinationen (a/o/kons)", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "lat_konjugationen", "name": "Konjugationen (a/e/i/kons)", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "lat_vokabeln_basics", "name": "Grundwortschatz", "tier": "free", "difficulty_range": [1, 2]},
        {"id": "lat_satzglieder", "name": "Satzglieder & AcI", "tier": "free", "difficulty_range": [1, 4]},
        {"id": "lat_partizipien", "name": "Partizipien (PPP/PPA/PFA)", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "lat_konjunktiv", "name": "Konjunktiv & Nebens\u00e4tze", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "lat_ablativus_absolutus", "name": "Ablativus Absolutus", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "lat_uebersetzung", "name": "\u00dcbersetzungstechnik", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "lat_caesar", "name": "Caesar: De Bello Gallico", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "lat_ovid", "name": "Ovid: Metamorphosen", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "lat_cicero", "name": "Cicero: Reden", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "lat_abitur_latein", "name": "Abitur-Latein", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "lat_seneca", "name": "Seneca: Epistulae morales", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "lat_vergil", "name": "Vergil: Aeneis", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "lat_gerundium", "name": "Gerundium & Gerundivum", "tier": "pro", "difficulty_range": [3, 5]},
    ],
    # === FRANZÖSISCH (15 Themen) ===
    "french": [
        {"id": "fr_present", "name": "Pr\u00e9sent & Verbes r\u00e9guliers", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "fr_articles", "name": "Articles & Pronoms", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "fr_vocabulaire", "name": "Vocabulaire de base", "tier": "free", "difficulty_range": [1, 2]},
        {"id": "fr_negation", "name": "N\u00e9gation & Questions", "tier": "free", "difficulty_range": [1, 3]},
        {"id": "fr_passe_compose", "name": "Pass\u00e9 compos\u00e9 & Imparfait", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "fr_subjonctif", "name": "Subjonctif", "tier": "pro", "difficulty_range": [3, 5]},
        {"id": "fr_conditionnel", "name": "Conditionnel", "tier": "pro", "difficulty_range": [2, 5]},
        {"id": "fr_pronoms_relatifs", "name": "Pronoms relatifs", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "fr_texte_production", "name": "Production de texte", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "fr_mediation", "name": "M\u00e9diation/Sprachmittlung", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "fr_litterature", "name": "Litt\u00e9rature fran\u00e7aise", "tier": "max", "difficulty_range": [3, 5]},
        {"id": "fr_abitur_franzoesisch", "name": "Abitur-Franz\u00f6sisch", "tier": "max", "difficulty_range": [4, 5]},
        {"id": "fr_plus_que_parfait", "name": "Plus-que-parfait", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "fr_futur", "name": "Futur simple & Futur ant\u00e9rieur", "tier": "pro", "difficulty_range": [2, 4]},
        {"id": "fr_discours_indirect", "name": "Discours indirect", "tier": "max", "difficulty_range": [3, 5]},
    ],
}


def get_topics_for_subject(subject: str, tier: str = "free") -> list[dict]:
    """Get available quiz topics for a subject, filtered by subscription tier.

    Args:
        subject: Subject ID (math, german, physics, chemistry, etc.)
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


def get_total_topic_count() -> int:
    """Get grand total of all topics across all subjects."""
    return sum(len(topics) for topics in QUIZ_TOPICS.values())


def is_topic_accessible(topic_id: str, tier: str) -> bool:
    """Check if a specific topic is accessible for a given tier."""
    tier_access = {"free": ["free"], "pro": ["free", "pro"], "max": ["free", "pro", "max"]}
    allowed_tiers = tier_access.get(tier, ["free"])

    for subject_topics in QUIZ_TOPICS.values():
        for topic in subject_topics:
            if topic["id"] == topic_id:
                return topic["tier"] in allowed_tiers
    return False


def get_subject_list() -> list[dict]:
    """Get list of all available subjects with their info."""
    return [
        {"id": subject_id, **info}
        for subject_id, info in SUBJECT_MAP.items()
    ]
