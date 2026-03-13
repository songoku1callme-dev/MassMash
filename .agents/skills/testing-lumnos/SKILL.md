# LUMNOS Frontend Testing

## Auth
- Use GitHub OAuth for login (Clerk email OTP requires email access)
- Click GitHub button on Clerk sign-in → Authorize clerk → Redirects back to app
- Owner emails get "Owner" badge in sidebar + green star
- Dev-token bypass: set `auth_token=dev-max-token-lumnos` in localStorage for local testing

## Navigation
- App uses SPA navigation via Sidebar (not URL routing)
- All pages accessed via Sidebar buttons (id matches page name)
- Sidebar has 35+ items — scroll down to find items like "Schul-Lizenzen", "Admin-Panel", "Abo & Preise"

## Key Pages to Test

### SchoolPage (Schul-Lizenzen)
- Sidebar item: "Schul-Lizenzen"
- Has "Klasse erstellen" and "Klasse beitreten" toggle buttons
- "Klasse erstellen" expands a form with school name input
- Shows 3 Schul-Pakete cards (Klassen-Lizenz, Schul-Lizenz, Enterprise)
- Invite link feature: copies URL with `?join=KLASSE-XXXX` parameter
- The `?join=` param auto-fills join code on page load (useEffect in SchoolPage.tsx)

### PricingPage (Abo & Preise)
- Sidebar item: "Abo & Preise"
- Shows 4 pricing tiers: Kostenlos, Pro, Max, Eltern
- Monatlich/Jaehrlich toggle changes displayed prices
- Owner users see "Du bist Owner-Mitglied!" green banner
- "Abo verwalten" button appears for non-free tiers (Stripe Customer Portal)
- Gutschein-Code input section at the bottom

### ChatPage (KI-Tutor)
- Default page after login
- Shows Fach selector with 32 subjects in categories
- KI-Persoenlichkeit dropdown (Mentor, Streng, etc.)
- Fast/Standard/Deep mode buttons
- Owner badge visible in top-right area

## Clerk Login Issues
- Clerk Development keys have strict rate limits (429 errors)
- Cookie banner may need to be dismissed first
- If Clerk widget shows blank/loading, wait 10-40s (cold start)
- GitHub OAuth is the most reliable login method

## Devin Secrets Needed
- CLERK_TEST_EMAIL — for email-based login
- CLERK_TEST_PASSWORD — for email-based login
- GitHub account credentials (songoku1callme-dev) — for OAuth login
