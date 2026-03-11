# Testing Lumnos Frontend (Vercel Preview)

## Overview
The Lumnos frontend is a React + Vite app deployed to Vercel. PRs automatically get Vercel preview deployments.

## Devin Secrets Needed
- No secrets required for basic web regression testing (unauthenticated)
- For authenticated testing: Clerk test account credentials would be needed

## How to Test

### 1. Find the Vercel Preview URL
- After CI passes on a PR, check the Vercel bot comment on the PR for the preview URL
- Format: `mass-mash-git-{branch-slug}-songoku1callme-devs-projects.vercel.app`

### 2. Basic Web Regression
1. Navigate to the Vercel preview URL
2. Verify the Clerk auth page loads (shows "Lumnos" + "KI-Lerncoach" + OAuth buttons)
3. Open browser DevTools console and check for JavaScript errors
4. Known pre-existing warnings (NOT bugs):
   - `manifest.webmanifest` 401 error — pre-existing, not related to new changes
   - Clerk development keys warning — expected in dev/preview deployments
   - `[DOM] Input elements should have autocomplete attributes` — browser suggestion, not an error

### 3. Capacitor Hooks (Web Regression)
If testing Capacitor-related changes:
- Run in console: `window.Capacitor.isNativePlatform()` — should return `false` on web
- Run in console: `window.Capacitor.getPlatform()` — should return `'web'`
- All Capacitor hooks are designed as no-ops on web via `Capacitor.isNativePlatform()` checks
- The OfflineBanner uses `useNetworkStatus` which falls back to `navigator.onLine` on web

### 4. Offline Banner Testing
- In DevTools Network tab, toggle "Offline" mode
- Expected: Orange banner appears at bottom: "Offline - Karteikarten und Notizen verfügbar"
- Toggle back online
- Expected: Green banner appears briefly: "Wieder online - Daten werden synchronisiert"

## Architecture Notes
- App uses Clerk for authentication (OAuth: Apple, GitHub, Google + email)
- The app is a single-page app with sidebar navigation (not URL-based routing for most pages)
- `App.tsx` renders all pages via a `currentPage` state + switch statement
- Pages are lazy-loaded via `React.lazy()`
- Backend is on Render (free tier, may have cold-start delays up to 30s)
- Backend URL configured via `VITE_API_URL` env var

## Native Testing (iOS/Android)
- Requires Android Studio (for Android) or Xcode on macOS (for iOS)
- Cannot be tested in browser — Capacitor native features only activate when `isNativePlatform()` is true
- Android build: `cd eduai-companion/eduai-frontend/android && ./gradlew assembleDebug`
- iOS build: `npx cap open ios` then build in Xcode
