#!/usr/bin/env python3
"""
LUMNOS DEEP TEST v2 — KI-Qualitat + API + System
Fixed API paths/params based on actual backend routes.
"""
import requests, json, time, re, os, sys
from datetime import datetime

BASE = "http://localhost:8000"
HEADERS = {
    "Authorization": "Bearer dev-max-token-lumnos",
    "Content-Type": "application/json"
}
results = []
ki_quality_results = []

def req(name, method, endpoint, body=None, params=None,
        expected=200, check_keys=None, timeout=20):
    try:
        start = time.time()
        if method == "POST":
            r = requests.post(f"{BASE}{endpoint}", headers=HEADERS,
                              json=body, params=params, timeout=timeout)
        else:
            r = requests.get(f"{BASE}{endpoint}", headers=HEADERS,
                             params=params, timeout=timeout)
        ms = round((time.time() - start) * 1000)
        data = {}
        try: data = r.json()
        except: pass

        ok = r.status_code == expected
        missing = [k for k in (check_keys or []) if k not in str(data)]
        status = "PASS" if ok and not missing else ("WARN" if ok else "FAIL")

        result = {
            "name": name, "endpoint": f"{method} {endpoint}",
            "status": status, "http": r.status_code,
            "ms": ms, "missing_keys": missing,
            "error": str(data.get("detail",""))[:100] if not ok else ""
        }
        results.append(result)
        icon = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[status]
        print(f"[{icon}] [{ms}ms] {name}"
              + (f" -- FEHLER: {result['error']}" if result['error'] else "")
              + (f" -- FEHLENDE KEYS: {missing}" if missing else ""))
        return data, r.status_code
    except Exception as e:
        results.append({"name": name, "status": "FAIL", "error": str(e)[:100]})
        print(f"[FAIL] [ERROR] {name}: {e}")
        return {}, 0

def parse_sse_content(raw_text):
    """Parse SSE stream to extract the actual AI response content."""
    content_parts = []
    for line in raw_text.split("\n"):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if "text" in data:
                    # Skip status messages
                    if not any(s in data["text"] for s in [
                        "Analysiere", "Schreibe", "Wikipedia", "Denke nach",
                        "Suche", "Generiere", "Pruefe", "Prüfe"
                    ]):
                        content_parts.append(data["text"])
            except:
                pass
    return "".join(content_parts)

def test_ki_quality(frage, erwartung, fach="Allgemein", modus=None):
    """Testet KI-Antwortqualitaet mit konkreten Kriterien."""
    body = {"message": frage, "fach": fach}
    if modus: body[modus] = True

    start = time.time()
    try:
        r = requests.post(f"{BASE}/api/chat/stream",
                         headers=HEADERS, json=body, timeout=30)
        ms = round((time.time() - start) * 1000)

        raw = r.text
        # Parse SSE content
        antwort = parse_sse_content(raw)
        if not antwort:
            # Fallback: try JSON
            try:
                data = r.json()
                antwort = data.get("content", data.get("message",
                               data.get("response", str(data))))
            except:
                antwort = raw

        # Detect error/fallback messages — these are NOT real answers
        error_phrases = [
            "konnte gerade nicht antworten",
            "bitte versuche es",
            "fehler aufgetreten",
            "api key",
            "rate limit",
            "service unavailable",
        ]
        is_error_response = any(ep in antwort.lower() for ep in error_phrases)

        # Qualitaets-Checks
        checks = {
            "hat_antwort": len(antwort.strip()) > 10 and not is_error_response,
            "keine_thinking_tags": "<think>" not in antwort,
            "keine_rueckfrage": not any(p in antwort.lower() for p in [
                "koenntest du", "kannst du mir sagen", "was meinst du",
                "ich brauche mehr", "was genau", "bitte praezisiere",
                "welche zeilen", "was fuer zeilen"
            ]),
            "nicht_zu_lang": len(antwort) < 1500
                             if len(frage) < 20 else True,
            "auf_deutsch": any(w in antwort.lower() for w in [
                "ist", "sind", "wird", "hat", "die", "der", "das",
                "ein", "eine", "und", "fuer", "von"
            ]) and not is_error_response,
            "keine_output_tags": "<output>" not in antwort,
            "keine_error_fallback": not is_error_response,
        }

        # Pruefe spezifische Erwartung
        if erwartung.get("enthaelt"):
            for e in erwartung["enthaelt"]:
                checks[f"enthaelt_{e}"] = e.lower() in antwort.lower()

        if erwartung.get("enthaelt_nicht"):
            for e in erwartung["enthaelt_nicht"]:
                checks[f"nicht_{e}"] = e.lower() not in antwort.lower()

        score = sum(checks.values()) / len(checks) * 100
        status = "PASS" if score >= 80 else ("WARN" if score >= 50 else "FAIL")

        ki_result = {
            "frage": frage[:60],
            "status": status,
            "score": round(score),
            "antwort_laenge": len(antwort),
            "antwort_vorschau": antwort[:200].replace("\n", " "),
            "checks": checks,
            "ms": ms,
            "fehler": [k for k,v in checks.items() if not v]
        }
        ki_quality_results.append(ki_result)

        print(f"\n[{status}] KI-Test [{ms}ms] Score:{score:.0f}%")
        print(f"   Frage: '{frage[:50]}'")
        print(f"   Antwort ({len(antwort)} chars): '{antwort[:120]}...'")
        if ki_result["fehler"]:
            print(f"   FEHLER: {ki_result['fehler']}")
        return antwort

    except Exception as e:
        ki_quality_results.append({
            "frage": frage[:60], "status": "FAIL",
            "score": 0, "error": str(e)[:200]
        })
        print(f"[FAIL] KI-Test FEHLER: {frage[:40]} -- {e}")
        return ""

# ===================================================================
print("\n" + "="*60)
print("LUMNOS DEEP TEST v2 -- START", datetime.now().strftime("%H:%M:%S"))
print("="*60)

# -- PHASE 1: SYSTEM & AUTH ----------------------------------------
print("\n== PHASE 1: SYSTEM ==")
req("Health", "GET", "/healthz")
req("API Docs", "GET", "/docs")
me, _ = req("Auth Check", "GET", "/api/auth/me", check_keys=["id"])
print(f"   User: id={me.get('id')}, tier={me.get('tier')}, email={me.get('email')}")

# -- PHASE 2: KI-QUALITAET -- 20 VERSCHIEDENE TESTS ----------------
print("\n\n== PHASE 2: KI-QUALITAET (20 Tests) ==")
print("-"*50)

# Rate limit: Groq free tier = 12000 TPM, so we add delays between KI tests
KI_DELAY = 8  # seconds between KI tests to avoid rate limit

# 2A: Kurzfragen
test_ki_quality("2+2", {"enthaelt": ["4"]}, "Mathematik")
time.sleep(KI_DELAY)
test_ki_quality("Wurzel von 144", {"enthaelt": ["12"]}, "Mathematik")
time.sleep(KI_DELAY)
test_ki_quality("Was ist H2O?", {"enthaelt": ["Wasser"]}, "Chemie")
time.sleep(KI_DELAY)
test_ki_quality("Wann fiel die Berliner Mauer?",
    {"enthaelt": ["1989"]}, "Geschichte")
time.sleep(KI_DELAY)
test_ki_quality("Hauptstadt von Frankreich?",
    {"enthaelt": ["Paris"]}, "Geografie")
time.sleep(KI_DELAY)

# 2B: Mittlere Fragen
test_ki_quality("Was ist Fotosynthese?",
    {"enthaelt": ["Licht"]}, "Biologie")
time.sleep(KI_DELAY)
test_ki_quality("Erklaere den Pythagorischen Satz",
    {"enthaelt": ["a", "b", "c"]}, "Mathematik")
time.sleep(KI_DELAY)
test_ki_quality("Was war der Zweite Weltkrieg?",
    {"enthaelt": ["1939"]}, "Geschichte")
time.sleep(KI_DELAY)

# 2C: Kritische Tests -- Rueckfragen verboten!
test_ki_quality("V=?",
    {"enthaelt_nicht": ["was meinst"]},
    "Mathematik")
time.sleep(KI_DELAY)
test_ki_quality("Zeile 1 Zeile 2 Zeile 3 Zeile 4",
    {"enthaelt_nicht": ["koenntest du", "was meinst", "bitte sag"]})
time.sleep(KI_DELAY)
test_ki_quality("Erklaere das",
    {"enthaelt_nicht": ["was genau", "welches thema", "bitte praezisiere"]})
time.sleep(KI_DELAY)
test_ki_quality("?", {"enthaelt_nicht": ["koennte", "unklar"]})
time.sleep(KI_DELAY)

# 2D: Fach-spezifische Qualitaet
test_ki_quality("Deriviere f(x) = x^3 + 2x",
    {"enthaelt": ["3x", "2"]}, "Mathematik")
time.sleep(KI_DELAY)
test_ki_quality("Erklaere Oxidation und Reduktion",
    {"enthaelt": ["Elektronen"]}, "Chemie")
time.sleep(KI_DELAY)
test_ki_quality("Was ist der Unterschied zwischen Dativ und Akkusativ?",
    {"enthaelt": ["Wem", "Wen"]}, "Deutsch")
time.sleep(KI_DELAY)

# 2E: Komplexe Frage
test_ki_quality(
    "Erklaere mir Quantenmechanik mit den wichtigsten Konzepten",
    {"enthaelt": []}, "Physik"
)
time.sleep(KI_DELAY)

# 2F: Modus-Tests
test_ki_quality("Was ist Fotosynthese?",
    {"enthaelt_nicht": []},
    "Biologie", modus="tutor_modus")
time.sleep(KI_DELAY)
test_ki_quality("Was ist ein Algorithmus?",
    {"enthaelt": []}, "Informatik", modus="eli5")
time.sleep(KI_DELAY)

# 2G: Sprache & Format
test_ki_quality("What is photosynthesis?",
    {"enthaelt": []}, "Biologie")
time.sleep(KI_DELAY)
test_ki_quality("Berechne die Ableitung von sin(x)",
    {"enthaelt": ["cos"]}, "Mathematik")

# -- PHASE 3: ALLE API ENDPOINTS -----------------------------------
print("\n\n== PHASE 3: API ENDPOINTS ==")
print("-"*50)

# Quiz (correct: subject, topic, difficulty, num_questions, quiz_type)
print("\n-- Quiz --")
qd, _ = req("Quiz generieren -- Mathe/Pythagoras", "POST",
    "/api/quiz/generate",
    {"subject":"Mathematik","topic":"Pythagoras","difficulty":"intermediate","num_questions":3,"quiz_type":"mcq"},
    check_keys=["questions"])
req("Quiz generieren -- Biologie/Fotosynthese", "POST",
    "/api/quiz/generate",
    {"subject":"Biologie","topic":"Fotosynthese","difficulty":"beginner","num_questions":3,"quiz_type":"mcq"})
# Get quiz_id and first question_id from generated quiz for check-answer
quiz_id_for_test = qd.get("quiz_id", qd.get("id", "1"))
quiz_questions = qd.get("questions", qd.get("fragen", []))
first_q_id = quiz_questions[0].get("id", 1) if quiz_questions else 1
req("Quiz Check-Answer", "POST", "/api/quiz/check-answer",
    {"quiz_id": str(quiz_id_for_test),
     "question_id": first_q_id,
     "user_answer":"Pythagoras"})
req("Quiz Erklaerung", "POST", "/api/erklaerung/quiz",
    {"frage":"Was ist 2+2?","richtige_antwort":"4",
     "schueler_antwort":"5","fach":"Mathematik","war_richtig":False})
req("Quiz History", "GET", "/api/quiz/history")
req("Quiz Topics", "GET", "/api/quiz/topics")
req("Quiz Personalities", "GET", "/api/quiz/personalities")
req("Quiz Blind-Spots", "GET", "/api/quiz/blind-spots")

# IQ Test
print("\n-- IQ-Test --")
iq, _ = req("IQ generieren", "POST", "/api/iq/generieren",
             check_keys=["questions"])
req("IQ Cooldown", "GET", "/api/iq/cooldown")
# Build proper IQ test submission with test_id and structured answers
iq_test_id = iq.get("test_id", iq.get("id", 1))
iq_questions = iq.get("questions", iq.get("fragen", []))
iq_answers = [{"question_id": q.get("id", i+1), "answer": 0, "time_seconds": 30.0}
              for i, q in enumerate(iq_questions[:15])]
if not iq_answers:
    iq_answers = [{"question_id": i+1, "answer": 0, "time_seconds": 30.0} for i in range(15)]
req("IQ berechnen", "POST", "/api/iq/berechnen",
    {"test_id": iq_test_id, "answers": iq_answers})
req("IQ Ergebnis", "GET", "/api/iq/ergebnis")

# Abitur (uses query params!)
print("\n-- Abitur --")
ab, _ = req("Abitur starten", "POST", "/api/abitur/start",
    params={"subject":"Mathematik","num_questions":3},
    check_keys=["simulation_id"])
if ab.get("simulation_id"):
    sid = ab["simulation_id"]
    req("Abitur Pause", "POST", "/api/abitur/pause",
        params={"simulation_id": sid})
    req("Abitur Resume", "POST", "/api/abitur/resume",
        params={"simulation_id": sid})
    req("Abitur Submit", "POST", "/api/abitur/submit",
        params={"simulation_id": sid},
        body=[])
req("Abitur History", "GET", "/api/abitur/history")

# Gamification
print("\n-- Gamification --")
req("XP hinzufuegen", "POST", "/api/gamification/add-xp",
    {"action":"quiz_richtig","fach":"Mathematik"})
req("Gamification Profil", "GET", "/api/gamification/profile",
    check_keys=["xp","level"])
req("Leaderboard", "GET", "/api/gamification/leaderboard")

# Battle Pass (uses query params!)
print("\n-- Battle Pass --")
req("BP Status", "GET", "/api/battle-pass/status",
    check_keys=["level","xp"])

# Quests & Challenges
print("\n-- Quests & Challenges --")
req("Quests heute", "GET", "/api/quests/today",
    check_keys=["quests"])
req("Quest progress", "POST", "/api/quests/progress/quest_chat")
req("Challenge erstellen", "POST", "/api/challenges/create",
    params={"title":"Test","description":"Test Challenge",
            "subject":"Mathematik","target_score":80,
            "xp_reward":100,"deadline_days":7})
req("Challenge Liste", "GET", "/api/challenges/list")

# Multiplayer
print("\n-- Multiplayer --")
room, _ = req("Raum erstellen", "POST", "/api/multiplayer/create-room",
              {"fach":"Mathematik"}, check_keys=["room_code"])
req("WS Ticket", "POST", "/api/ws/ticket")
req("Turnier aktuell", "GET", "/api/turnier/aktuell")
req("Turnier Rangliste", "GET", "/api/turnier/rangliste",
    params={"tournament_id": 1})

# Karteikarten
print("\n-- Karteikarten --")
req("Decks Liste", "GET", "/api/flashcards/decks")
deck, _ = req("Deck erstellen", "POST", "/api/flashcards/decks",
    {"name":"Test-Deck","subject":"Geschichte","description":"Test"})
req("KI Karten generieren", "POST", "/api/flashcards/ai-generate",
    {"topic":"Berliner Mauer","subject":"Geschichte","count":3})

# Notizen
print("\n-- Notizen --")
note, _ = req("Note erstellen", "POST", "/api/notes/",
    {"title":"Test Note","content":"Test Inhalt","subject":"general"},
    check_keys=["id"])
req("Notes Liste", "GET", "/api/notes/")

# Shop
print("\n-- Shop --")
req("Shop Items", "GET", "/api/shop/items", check_keys=["items"])
# Get actual shop items first
shop_data, _ = req("Shop Items Detail", "GET", "/api/shop/items")
shop_item_id = "boost_streak_schutz"
if isinstance(shop_data, dict) and shop_data.get("items"):
    first_item = shop_data["items"][0]
    shop_item_id = first_item.get("id", first_item.get("item_id", shop_item_id))
req("Shop Kaufen", "POST", "/api/shop/buy",
    params={"item_id": shop_item_id})

# KI-Intelligenz (correct: /api/intelligence/*)
print("\n-- KI-Intelligenz --")
req("Lernstil", "GET", "/api/intelligence/lernstil")
req("Feynman", "POST", "/api/intelligence/feynman",
    params={"thema":"Fotosynthese","erklärung":"Pflanzen machen Zucker"})
req("Sokrates", "POST", "/api/intelligence/sokrates",
    params={"frage":"Was ist Gerechtigkeit?"})
req("Wissens-Scan", "GET", "/api/intelligence/wissensscan/start",
    params={"fach":"Mathematik"})
req("Wochenplan", "GET", "/api/intelligence/weekly-plan")

# Erklaerung
print("\n-- Erklaerung --")
req("Schnell-Erklaerung", "POST", "/api/erklaerung/schnell",
    {"thema":"Fotosynthese","fach":"Biologie","tiefe":"kurz"})
req("Stufenweise", "POST", "/api/erklaerung/stufenweise",
    {"thema":"Pythagoras","fach":"Mathematik"})
req("Quiz-Erklaerung", "POST", "/api/erklaerung/quiz",
    {"frage":"Was ist Fotosynthese?","richtige_antwort":"Umwandlung von Lichtenergie",
     "schueler_antwort":"Pflanzen essen Licht","fach":"Biologie","war_richtig":False})

# Voice & OCR
print("\n-- Voice & OCR --")
req("TTS", "POST", "/api/voice/tts", {"text":"Hallo Welt","lang":"de"})
req("OCR Text", "POST", "/api/ocr/solve-text",
    {"equation":"3x + 12 = 27"})

# Research (uses query params!)
print("\n-- Research --")
req("Internet-Recherche", "POST", "/api/research/search",
    params={"query":"Fotosynthese Definition"})
req("Research History", "GET", "/api/research/history")

# Infrastruktur
print("\n-- Infrastruktur --")
req("Stats Overview", "GET", "/api/stats/overview")
req("Stats Per Subject", "GET", "/api/stats/per-subject")
req("Stats Weekly", "GET", "/api/stats/weekly")
req("Stats XP History", "GET", "/api/stats/xp-history")
req("Stats Fach-Radar", "GET", "/api/stats/fach-radar")
req("Notifications", "GET", "/api/notifications/bell")
req("Admin Stats", "GET", "/api/admin/stats")
req("Stripe Config", "GET", "/api/stripe/config")
req("RAG Stats", "GET", "/api/rag/stats")
req("Pomodoro Stats", "GET", "/api/pomodoro/stats")
req("Calendar Exams", "GET", "/api/calendar/exams")
req("Learning Path Mathe", "GET", "/api/learning-path/Mathematik")
req("Profile", "GET", "/api/profile")
req("Progress", "GET", "/api/progress")
req("Subjects", "GET", "/api/subjects")

# Memory System
print("\n-- Memory System --")
req("Memory Profile", "GET", "/api/memory/profile")
req("Memory Stats", "GET", "/api/memory/stats")
req("Memory Weak Topics", "GET", "/api/memory/weak-topics")
req("Adaptive Prompt", "GET", "/api/memory/adaptive-prompt",
    params={"subject":"Mathematik"})

# Groups
print("\n-- Gruppen --")
req("Gruppen Liste", "GET", "/api/groups/list")

# Events
print("\n-- Events --")
req("Active Events", "GET", "/api/events/active")
req("All Events", "GET", "/api/events/all")

# Adaptive
print("\n-- Adaptive --")
req("Adaptive Profile", "GET", "/api/adaptive/profile")
req("Adaptive Difficulty", "GET", "/api/adaptive/difficulty")

# Legal
print("\n-- Legal --")
req("Datenschutz", "GET", "/api/legal/datenschutz")
req("Impressum", "GET", "/api/legal/impressum")

# -- PHASE 4: DATENBANK & ENVIRONMENT ------------------------------
print("\n\n== PHASE 4: DATENBANK & ENVIRONMENT ==")
print("-"*50)

import sqlite3, glob

# Check the main DB used by the backend
db_path = "eduai-companion/eduai-backend/app.db"
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        ic = cur.fetchone()[0]
        cur.execute("PRAGMA foreign_key_check")
        fk = cur.fetchall()
        cur.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cur.fetchone()[0]
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [r[0] for r in cur.fetchall()]
        conn.close()

        s = "PASS" if ic == "ok" and table_count > 5 else "WARN"
        results.append({
            "name": f"SQLite ({db_path})",
            "status": s,
            "error": "" if s == "PASS" else f"Nur {table_count} Tabellen"
        })
        print(f"[{s}] DB: {db_path} | Integritaet:{ic} | "
              f"{table_count} Tabellen | FK-Fehler:{len(fk)}")
        print(f"   Tabellen: {', '.join(table_names[:20])}")
    except Exception as e:
        print(f"[FAIL] DB Fehler: {e}")
        results.append({"name": f"SQLite ({db_path})", "status": "FAIL",
                        "error": str(e)[:100]})
else:
    print(f"[WARN] {db_path} nicht gefunden")

# Check other DBs
for other_db in ["eduai-companion/eduai-backend/lumnos.db",
                  "eduai-companion/eduai-backend/rag.db"]:
    if os.path.exists(other_db):
        try:
            conn = sqlite3.connect(other_db)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            tc = cur.fetchone()[0]
            conn.close()
            print(f"[INFO] {other_db}: {tc} Tabellen")
        except Exception as e:
            print(f"[WARN] {other_db}: {e}")

# Environment Keys
print("\n== Environment Keys ==")
required_keys = {
    "GROQ_API_KEY": "KRITISCH -- KI funktioniert nicht ohne",
    "TAVILY_API_KEY": "Internet-Recherche",
    "RESEND_API_KEY": "Email-Versand",
    "STRIPE_SECRET_KEY": "Zahlungen",
    "STRIPE_PUBLISHABLE_KEY": "Stripe Frontend",
    "CLERK_SECRET_KEY": "OAuth Login",
    "SECRET_KEY": "JWT Signing",
    "SENTRY_DSN": "Error Tracking",
    "POSTHOG_API_KEY": "Analytics"
}
env_pass = 0
env_fail = 0
for key, beschreibung in required_keys.items():
    val = os.getenv(key, "")
    s = "PASS" if val else "INFO"
    masked = f"{val[:8]}..." if val else "NICHT GESETZT"
    if val:
        env_pass += 1
    else:
        env_fail += 1
    # Only mark truly critical keys as FAIL
    if not val and key == "GROQ_API_KEY":
        s = "FAIL"
        results.append({"name": f"Key:{key}", "status": "FAIL",
                        "error": beschreibung})
    elif not val:
        # Optional keys - just info
        pass
    else:
        results.append({"name": f"Key:{key}", "status": "PASS", "error": ""})
    print(f"[{s}] {key}: {masked}"
          + (f" [{beschreibung}]" if not val else ""))

print(f"\n   Keys gesetzt: {env_pass}/{len(required_keys)}")
print(f"   (Nicht gesetzte optionale Keys sind normal in dev)")

# -- PHASE 5: FRONTEND CHECKS --------------------------------------
print("\n\n== PHASE 5: FRONTEND CHECKS ==")
print("-"*50)

frontend_files = glob.glob("eduai-companion/eduai-frontend/src/**/*.tsx",
                           recursive=True)
print(f"Frontend-Dateien: {len(frontend_files)}")

issues = []

for filepath in frontend_files:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        fname = filepath.split("/")[-1]

        # Pruefe auf localhost-Hardcoding
        if "localhost:8000" in content or "127.0.0.1:8000" in content:
            issues.append(f"[WARN] {fname}: Hardcoded localhost:8000!")

        # Pruefe auf fehlende Error-Boundaries
        if "fetch(" in content and "catch" not in content:
            issues.append(f"[WARN] {fname}: fetch() ohne Error-Handling")

    except: pass

if issues:
    print(f"\n[WARN] Frontend Issues gefunden: {len(issues)}")
    for issue in issues[:15]:
        print(f"  {issue}")
else:
    print("[PASS] Keine kritischen Frontend-Issues gefunden")

# ===================================================================
# FINAL REPORT
# ===================================================================
gruen = [r for r in results if r.get("status","") == "PASS"]
gelb =  [r for r in results if r.get("status","") == "WARN"]
rot =   [r for r in results if r.get("status","") == "FAIL"]
ki_gut =   [r for r in ki_quality_results if r.get("status","") == "PASS"]
ki_mittel= [r for r in ki_quality_results if r.get("status","") == "WARN"]
ki_schlecht=[r for r in ki_quality_results if r.get("status","") == "FAIL"]

total_tests = len(results) + len(ki_quality_results)
total_pass = len(gruen) + len(ki_gut)
gesamtscore = round(total_pass / total_tests * 100) if total_tests > 0 else 0

print("\n\n" + "="*60)
print("FINALER DEEP-TEST BERICHT")
print("="*60)

print(f"""
+-------------------------------------------+
|  API ENDPOINTS:                           |
|  PASS:  {len(gruen):>3} funktionieren perfekt     |
|  WARN:  {len(gelb):>3} haben Probleme            |
|  FAIL:  {len(rot):>3} kaputt                     |
|  Total: {len(results):>3} Tests                   |
|                                           |
|  KI-QUALITAET:                            |
|  Gut:      {len(ki_gut):>3}/20 Tests (>=80%)      |
|  Mittel:   {len(ki_mittel):>3}/20 Tests (50-79%)  |
|  Schlecht: {len(ki_schlecht):>3}/20 Tests (<50%)   |
|                                           |
|  GESAMTSCORE: {gesamtscore:>3}% funktionsfaehig    |
+-------------------------------------------+
""")

if rot:
    print("KRITISCHE BUGS (sofort fixen):")
    for r in rot:
        print(f"  [FAIL] {r['name']}")
        if r.get('error'): print(f"     -> {r['error']}")

if ki_schlecht:
    print("\nKI VERSAGT BEI:")
    for r in ki_schlecht:
        print(f"  [FAIL] Frage: '{r['frage']}'")
        print(f"     Vorschau: '{r.get('antwort_vorschau','')[:80]}'")
        if r.get('fehler'):
            print(f"     Probleme: {r['fehler']}")

if ki_mittel:
    print("\nKI SCHWAECHEN:")
    for r in ki_mittel:
        print(f"  [WARN] '{r['frage']}' -- Score: {r.get('score',0)}%")
        if r.get('fehler'):
            print(f"     Probleme: {r['fehler']}")

if gelb:
    print("\nWARNUNGEN:")
    for r in gelb:
        print(f"  [WARN] {r['name']}")
        if r.get('error'): print(f"     -> {r['error']}")

# Geschwindigkeit
slow = [r for r in results if r.get("ms",0) > 3000]
if slow:
    print(f"\nLANGSAME ENDPOINTS (>3s):")
    for r in slow:
        print(f"  {r['name']}: {r['ms']}ms")

# Speichere vollstaendigen Report
report = {
    "timestamp": datetime.now().isoformat(),
    "summary": {
        "api_pass": len(gruen), "api_warn": len(gelb),
        "api_fail": len(rot), "api_total": len(results),
        "ki_gut": len(ki_gut), "ki_mittel": len(ki_mittel),
        "ki_schlecht": len(ki_schlecht),
        "ki_total": len(ki_quality_results),
        "gesamtscore": gesamtscore
    },
    "api_results": results,
    "ki_quality": ki_quality_results,
    "frontend_issues": issues
}
with open("deep_test_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\nVollstaendiger Report gespeichert: deep_test_report.json")
print("="*60)
