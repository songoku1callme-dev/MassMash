# Testing LUMNOS EduAI App

## Architecture
- **Frontend**: React + Vite at `eduai-companion/eduai-frontend` (default port 5175)
- **Backend**: FastAPI at `eduai-companion/eduai-backend` (default port 8000)
- **Navigation**: Custom event-based navigation (NOT react-router-dom). Uses `window.dispatchEvent(new CustomEvent("navigate", { detail: "pageName" }))` and `setCurrentPage()` in App.tsx. Do NOT use `useNavigate()` from react-router-dom — it will crash.
- **Auth**: Dev token auto-login via localStorage (`lumnos_token: dev-max-token-lumnos`)

## Starting Servers

### Backend
```bash
export GROQ_API_KEY=<secret> && cd eduai-companion/eduai-backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd eduai-companion/eduai-frontend && npm run dev -- --port 5175
```

## Common Issues
- **Port already in use**: Kill existing processes with `fuser -k 8000/tcp` or `fuser -k 5175/tcp`
- **useNavigate crash**: The app uses custom navigation, not react-router-dom. Any component using `useNavigate()` will throw `useNavigate() may be used only in the context of a <Router> component`. Fix by using `window.dispatchEvent(new CustomEvent("navigate", { detail: "pageId" }))`
- **Quiz start button offscreen**: The "Quiz starten" button may be below the fold. Use `scrollIntoView()` via JS console to reach it.
- **Sidebar scrolling**: The sidebar nav list is scrollable via `devin-scrollable="true"`. Many items like KI-Intelligenz require scrolling down.

## Devin Secrets Needed
- `GROQ_API_KEY` — Required for AI explanation features (Erklärer, ErklaerButton, Chat)

## Key Test Flows

### Erklärer Tab (KI-Intelligenz page)
1. Sidebar → scroll to "KI-Intelligenz" → click
2. Click "Erklärer" tab (rightmost)
3. Enter topic, select subject from dropdown
4. Click "Erklärung generieren"
5. Verify 3 levels: Einfach/Normal/Profi with different content

### ErklaerButton in Quiz
1. Sidebar → "Quiz" → select subject + topic
2. Scroll down → click "Quiz starten"
3. On quiz question, click "Erklär mir das" button
4. Verify popup with explanation + "Mehr Details im Chat" link

### Dev User
- ID: 999, tier: "max", email: admin@lumnos.de
- Token: `dev-max-token-lumnos` (auto-set in localStorage)
