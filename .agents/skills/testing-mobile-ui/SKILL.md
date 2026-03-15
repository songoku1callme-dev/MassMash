# LUMNOS EduAI — Mobile UI Testing

## Overview
This skill covers how to test the LUMNOS EduAI frontend for mobile responsive layout issues.

## Devin Secrets Needed
- None required for guest mode testing (local dev server)
- For production testing: Clerk authentication credentials may be needed

## Local Development Setup

### Frontend Dev Server
```bash
cd eduai-companion/eduai-frontend
npm run dev
# Starts on http://localhost:5174 (Vite)
```

- The app starts in **guest mode** by default on localhost (no Clerk auth required)
- Production URL (https://mass-mash.vercel.app) requires Clerk authentication
- Vercel preview URLs from PRs also require auth

### Default Page
- The app defaults to the **KI-Tutor (Chat)** page, not the Dashboard
- To navigate to Dashboard: click hamburger menu (top-left) → click "Dashboard"

## Mobile Testing Approach

### Viewport Sizes
- iPhone 14: 390x844
- Samsung Galaxy S20: 412x915
- Playwright's mobile mode uses ~410px width (close to both)

### Key Pages to Test on Mobile
1. **Dashboard** — Header, stat cards, stats footer, upgrade banner
2. **Chat (KI-Tutor)** — Subject selector, chat area, input field
3. **Quiz** — Quiz cards, answer buttons
4. **Sidebar** — Slide-in animation, navigation items

### Common Mobile Layout Checks
1. **No horizontal scrolling**: `document.documentElement.scrollWidth === document.documentElement.clientWidth`
2. **Grid layouts**: Check `grid-cols-*` classes render correctly
3. **Flex stacking**: `flex-col` on mobile, `flex-row` on desktop
4. **Touch targets**: Buttons should be at least 44px (Apple HIG)
5. **Euro symbol**: Should show `€` not `\u20AC`

## Known Pitfalls

### Global CSS Grid Overrides
The file `src/index.css` contains global media query overrides that force grid layouts to single column on mobile:

```css
@media (max-width: 1023px) {
  .grid.grid-cols-2:not(.keep-2-cols) { grid-template-columns: 1fr !important; }
  .grid.grid-cols-3 { grid-template-columns: 1fr !important; }
  .grid.grid-cols-4 { grid-template-columns: repeat(2, 1fr) !important; }
}
```

- These `!important` rules override Tailwind's grid classes
- If a component needs to keep its grid layout on mobile, add the `keep-2-cols` class to opt out
- Always check `index.css` when grid layouts aren't rendering as expected

### Tailwind Breakpoints
- Default (no prefix) = mobile
- `sm:` = 640px+
- `md:` = 768px+
- `lg:` = 1024px+
- Mobile-first approach: write mobile styles first, then add breakpoint prefixes for larger screens

### Unicode Escapes in JSX
- JSX renders unicode escapes like `\u20AC` as literal text, not the symbol
- Use actual characters (`€`, `·`) or `{"\u20AC"}` in JSX expressions
- Search for remaining escapes: `rg '\\u[0-9a-fA-F]{4}' src/ --type tsx --type ts`

## Testing Workflow

1. Start frontend dev server
2. Open in browser with mobile emulation
3. Navigate through Dashboard, Chat, Quiz pages
4. Check each layout element against the expected mobile design
5. Use browser console to verify no horizontal scrolling
6. Record screen for evidence
