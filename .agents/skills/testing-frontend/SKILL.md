# LUMNOS EduAI Frontend Testing

## Overview
The LUMNOS EduAI frontend is a React + Vite + Tailwind app with 38+ pages. It uses a custom theme system based on `data-theme` attribute (NOT Tailwind's `dark:` prefix) with CSS variables.

## Quick Start
```bash
cd eduai-frontend
npm install
npm run dev  # starts on port 5173 by default
```

## Authentication
- The app uses Clerk for authentication but supports **Guest Mode** for testing without a backend
- On the AuthPage, there is a guest mode button that bypasses authentication
- Guest mode gives access to all pages but API calls will fail (expected without backend)

## Theme System
- Theme toggle is at the **bottom of the sidebar**: three buttons for Dark (moon), System (monitor), Light (sun)
- Theme is stored in `localStorage` under key `lumnos-theme`
- Uses `data-theme` attribute on `<html>` element — NOT Tailwind's `dark:` prefix
- CSS variables: `--lumnos-bg`, `--lumnos-surface`, `--gradient-bg`, `--border-color`, `--progress-bg`, `--bg-surface`, `--text-primary`, `--text-secondary`
- Utility classes: `theme-text`, `theme-text-secondary`, `theme-card`
- **IMPORTANT**: Never use Tailwind `dark:` prefix — it won't work with this project's theme approach

## Navigation
- The app uses **state-based routing** (no URL routes) — all pages are rendered via `currentPage` state in App.tsx
- Sidebar contains all 38 page links — scroll down to see all of them
- Page names in sidebar map to case values in App.tsx `renderPage()` switch statement

## Common Theme Bugs to Check
When auditing for theme issues, look for:
1. `bg-*-50` classes (light-only) — should be `bg-*-500/10` (opacity-based)
2. `text-gray-400/500/600/700` — should be `theme-text-secondary` or `theme-text`
3. `border-*-200/300` — should be `*-500/20` or `*-500/30`
4. Unstyled `<input>`, `<select>`, `<textarea>` — need `border-[var(--border-color)] bg-[var(--lumnos-surface)] theme-text`
5. `bg-gray-100/200` — should be `bg-[var(--bg-surface)]`
6. Any Tailwind `dark:` prefix usage — must be replaced with opacity-based or CSS variable approach

## Testing Procedure
1. Start dev server (`npm run dev`)
2. Enter Guest Mode on auth page
3. Toggle to Dark mode using sidebar bottom button
4. Navigate through pages checking text readability and element visibility
5. Toggle to Light mode and repeat
6. Key pages to always check: Pomodoro (has SVG timer + form select), KI-Intelligenz (tabs + cards), Gamification (leaderboard badges — needs backend data)

## Known Limitations
- Many pages require a running backend (port 8000) to display their full content
- Without backend: Gamification, Quiz, Dashboard, Stats pages show error states
- Pages with only client-side content (Pomodoro, Settings) are fully testable without backend
- Vite HMR cache can get stale after many file edits — clear with `rm -rf node_modules/.vite` and restart dev server

## Lint & Type Check
```bash
npm run lint      # ESLint
npm run typecheck # TypeScript compiler check (tsc --noEmit)
```

## Devin Secrets Needed
- No secrets required for frontend-only testing with Guest Mode
- For full testing with backend: would need database credentials and API keys (not currently configured)
