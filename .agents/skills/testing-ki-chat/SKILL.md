# Testing KI-Chat (LUMNOS KI-Tutor)

## Overview
The KI-Chat is the core feature of the LUMNOS app. It uses Groq LLM (llama3-70b-8192) to answer educational questions in German across 40+ subjects.

## Prerequisites
- Backend running on port 8000 with `GROQ_API_KEY` env var set
- Frontend running on port 5175
- User logged in (testuser3 or similar)
- Navigate to KI-Tutor page via sidebar

## Devin Secrets Needed
- `GROQ_API_KEY` - Required for LLM responses

## Key Testing Notes

### React Input Workaround
The chat input field uses React state management. Direct browser tool `type` actions may not work reliably. Use JavaScript to set the value:
```javascript
const input = document.querySelector('input[placeholder="Stelle eine Frage..."]');
const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
nativeInputValueSetter.call(input, 'Your question here');
input.dispatchEvent(new Event('input', { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
setTimeout(() => {
  input.focus();
  input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
}, 300);
```

### Response Timing
- Groq API responses typically take 5-15 seconds
- Wait at least 15 seconds after sending a message before checking for response
- The LumnosOrb avatar shows loading animation (pulsing dots) while waiting

### What to Verify Per Response
1. AI response appears with Markdown formatting (bold, lists, paragraphs)
2. KaTeX math formulas render correctly (for math questions)
3. Zusammenfassung (summary) appears in cyan italic text below response
4. "3 Karteikarten anzeigen" button appears below summary
5. Action buttons present: Kopieren, Einfacher, Details, Aufgabe
6. Subject badge shown (e.g., "Deutsch", "Mathematik")
7. Sources/Quellen section with relevant references
8. Practice exercise ("Deine Übungsaufgabe") included

### Free Tier Limits
- Free users have 10 messages/day limit
- After ~8 messages, a yellow banner appears: "Free-Limit fast erreicht (10 Nachrichten/Tag). Upgrade auf Pro"
- Plan test questions carefully to stay within limit, or use a Pro/Max tier user

### Subject Detection
- The backend auto-detects the subject from the question content
- Subject badge may show "Deutsch" as default if detection is ambiguous
- Subject detection uses `normalize_fach()` function in chat.py

### Good Test Questions (Different Subjects)
1. **Mathematik**: "Was ist der Satz des Pythagoras?" - Tests KaTeX rendering
2. **Geschichte**: "Erkläre die Weimarer Republik" - Tests long-form content
3. **Physik**: "Was ist die Relativitätstheorie? Erkläre E=mc²" - Tests formulas
4. **Biologie**: "Was ist Photosynthese?" - Tests chemical equations
5. **Integralrechnung**: "Gib mir eine Übungsaufgabe zu Integralrechnung mit Lösung" - Tests complex math task

### UI Elements
- Chat input: `input[placeholder="Stelle eine Frage..."]`
- Subject selector: Left panel with 40+ subjects organized by category
- Tutor-Modus toggle: Button showing "Tutor AUS/AN"
- ELI5 toggle: Button showing "ELI5 AUS/AN"
- KI Personality selector: Button showing current personality (default: Mentor)
- Camera button: For Mathe-Foto upload
- Microphone button: For Spracheingabe

### Known Behaviors
- Action buttons (Einfacher, Details, Aufgabe) may be disabled for the most recent message until the next message is sent
- The input field is disabled while waiting for AI response
- Chat history appears in the left sidebar under "Letzte Chats"
- Each response includes duplicate "Quellen" sections (RAG sources + general sources) - this is expected behavior from the prompt structure
