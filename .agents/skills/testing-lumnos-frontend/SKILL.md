# Testing LUMNOS Frontend (EduAI Companion)

## Overview
The LUMNOS frontend is a React+Vite SPA with Clerk OAuth authentication. Testing requires bypassing Clerk auth to access the app UI.

## Devin Secrets Needed
- None required for local UI testing (dev bypass token is hardcoded)
- For full E2E testing with backend: Clerk test credentials or backend API access

## Auth Bypass for Local Testing

### Method 1: Dev Token (Recommended)
The authStore (`src/stores/authStore.ts`) recognizes a special dev token:
```
localStorage.setItem("lumnos_token", "dev-max-token-lumnos")
```
After setting this in browser console and reloading, the app creates a fake admin user (TestAdmin, Max-Tier) without needing any backend API call.

### Method 2: VITE_DEV_BYPASS
The `.env` file contains `VITE_DEV_BYPASS=true` which shows a "DEV BYPASS LOGIN" button on the AuthPage. However, this button calls the backend API (`/api/auth/dev-bypass`), so it only works when a backend is running.

### Method 3: Clerk Auth (Vercel Preview)
The Vercel preview at the deployment URL requires Clerk authentication (Google/GitHub/Apple OAuth or email). This is needed for full E2E testing with the production backend.

## Local Dev Server Setup
```bash
cd eduai-companion/eduai-frontend
npx vite --port 5173 --host 0.0.0.0
```
- If port 5173 is busy, Vite auto-selects the next available port (e.g., 5174)
- The dev server supports HMR and uses the `.env` file for environment variables

## App Navigation Structure
- The app uses a custom SPA router via `currentPage` state in `App.tsx`
- Default page is "chat" (ChatPage)
- Navigation is handled by the Sidebar component which dispatches page change events
- There are 38 pages total, all accessible from the sidebar
- The sidebar is scrollable and contains all navigation items

## Key Pages for Testing

### ChatPage (default)
- FachSelector: Shows 32+ subjects organized by category (Sprachen, MINT, Gesellschaft, Religion & Ethik, Kreativ, Haushalt)
- Chat-Verlauf sidebar: Opens via hamburger menu button, shows session history
- Star rating: Appears below AI responses (needs backend to generate AI responses)
- KI-Persönlichkeit selector: Dropdown for AI personality modes

### QuizPage
- 16 subject grid for selection
- Difficulty selector: Anfänger, Mittel, Schwer
- Question type selector: Gemischt, Multiple Choice, Wahr/Falsch, Lückentext, Freitext
- Question count: 5, 10, 20, 50
- "Quiz starten" button at bottom (requires scrolling to see)
- Starting a quiz requires backend API to generate questions
- Confetti animation triggers on results screen when score >= 80%
- "Zum Dashboard" button on results screen

## Testing Limitations Without Backend
- Chat streaming (SSE) cannot be tested
- Quiz gameplay (timer, answers, results) cannot be tested
- Star rating POST requests will fail silently
- FachSelector falls back to hardcoded subject list when API is unavailable
- Session history shows empty state

## Common Issues
- **devinid instability**: Browser devinids change between page renders. When clicking elements that trigger re-renders, the devinid may shift. Use coordinates as fallback.
- **Quiz starten timeout**: Clicking "Quiz starten" without a backend may cause navigation back to ChatPage due to failed API call error handling.
- **Clerk auth on Vercel**: The Vercel preview always requires Clerk auth. The dev bypass button is not visible on Vercel because the Clerk SignIn component covers the custom auth form.
- **Port conflicts**: If a previous dev server session is still running, the new one will use a different port. Check the Vite output for the actual port.

## CI Checks
- Vercel Preview Comments + Vercel Deployment (2 checks)
- No custom test suite in CI (tests are local only)
- Build check: `npm run build` in the frontend directory
