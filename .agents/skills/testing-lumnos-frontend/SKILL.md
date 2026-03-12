# Testing Lumnos Frontend & PWA

## Overview
Lumnos is a React + Vite frontend with Clerk authentication, VitePWA for progressive web app features, and Capacitor for native mobile builds. The frontend is deployed on Vercel.

## URLs
- **Production:** https://mass-mash.vercel.app
- **Backend:** https://lumnos-backend.onrender.com
- **Preview deployments:** Generated automatically by Vercel for each PR branch

## Devin Secrets Needed
- No secrets required for unauthenticated testing (splash screen, manifest, SW)
- For authenticated testing: Clerk test credentials would be needed

## Testing PWA Features

### Manifest Verification
1. Navigate to the deployed URL
2. In browser console, run:
   ```js
   fetch('/manifest.webmanifest').then(r => r.json()).then(m => console.log(JSON.stringify(m, null, 2)))
   ```
3. Verify: name, short_name, theme_color, background_color, display, icons
4. **Note:** Vercel preview deployments may return 401 for manifest.webmanifest due to preview auth protection. The JS fetch workaround above bypasses this. Production URL won't have this issue.

### Service Worker Verification
1. In browser console, run:
   ```js
   navigator.serviceWorker.getRegistrations().then(regs => console.log(regs.length, 'registrations'))
   ```
2. Verify at least 1 registration is active
3. Check Cache Storage in DevTools Application tab for cache names

### Theme-Color Meta Tag
1. In browser console:
   ```js
   document.querySelector('meta[name="theme-color"]')?.content
   ```
2. Should match the manifest theme_color value

### PWA Install Banner
- The install banner (`PWAInstallBanner.tsx`) shows after 30 seconds of usage
- It requires the `beforeinstallprompt` browser event which only fires on HTTPS with valid manifest
- The banner can be dismissed and stores `lumnos_pwa_dismissed` in localStorage
- To re-test: clear localStorage item `lumnos_pwa_dismissed`
- **Note:** The embedded Playwright browser may not fire `beforeinstallprompt` — this is a browser limitation, not a code bug

### Splash Screen
- `ClerkSplash` component in App.tsx shows while Clerk SDK initializes
- Shows "Lumnos" branding with pulsing icon on dark background
- Should appear immediately on page load (no white screen)
- Very brief on fast connections — annotate recording early

## Testing Frontend Generally

### Running Locally
```bash
cd eduai-companion/eduai-frontend
npm install
npm run dev
```
The dev server runs on port 5173 with proxy to backend at localhost:8000.

### Lint Check
```bash
npm run lint
```
Note: There are many pre-existing lint warnings (unused imports) across pages. Focus on errors introduced by your changes.

### Build Check
```bash
npm run build
```

### Key Files
- `vite.config.ts` — VitePWA manifest + service worker config
- `src/App.tsx` — Main app with splash screen, auth guard, page routing
- `src/components/PWAInstallBanner.tsx` — PWA install prompt component
- `index.html` — Meta tags including theme-color
- `MOBILE_RELEASE.md` — Android APK + iOS build guide

## Common Issues
- **Vercel preview 401 on manifest:** Normal for preview deployments with auth protection. Use JS fetch to verify manifest content.
- **Clerk development keys warning:** Expected on preview/dev, not an error.
- **Backend cold start:** Render free-tier backend may take 30s+ to wake up. The app has keep-alive pings every 5 minutes.
- **White screen:** If Clerk fails to load, the ClerkSplash component prevents white screen.
