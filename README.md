# EvolveAI - The Gamified Life OS

A habit-tracking, goal-setting, and daily planning mobile app that turns your life into an RPG. Built with React Native (Expo), Supabase, and AI coaching powered by OpenAI.

## Tech Stack

- **Frontend:** React Native + Expo (TypeScript, Managed Workflow)
- **Styling:** NativeWind (Tailwind CSS for React Native)
- **Navigation:** expo-router (file-based routing)
- **State Management:** Zustand + TanStack React Query
- **Backend:** Supabase (PostgreSQL, Auth, Edge Functions, Storage)
- **AI:** OpenAI GPT-4o-mini via Supabase Edge Functions
- **Payments:** RevenueCat SDK
- **Animations:** react-native-reanimated

## Getting Started

### Prerequisites

- Node.js 18+
- Expo CLI (`npm install -g expo-cli`)
- A [Supabase](https://supabase.com) project
- (Optional) [RevenueCat](https://www.revenuecat.com) account for payments
- (Optional) [OpenAI](https://platform.openai.com) API key for AI coaching

### Setup

1. **Clone and install:**
   ```bash
   git clone <repo-url>
   cd MassMash
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Fill in your Supabase URL, anon key, and other values
   ```

3. **Set up the database:**
   - Go to your Supabase dashboard > SQL Editor
   - Run the contents of `supabase/schema.sql`

4. **Deploy the AI Edge Function (optional):**
   ```bash
   supabase functions deploy ai-coach
   supabase secrets set OPENAI_API_KEY=sk-your-key-here
   ```

5. **Start the app:**
   ```bash
   npx expo start
   ```

## Project Structure

```
app/                    # expo-router screens
  (auth)/               # Authentication screens
  (tabs)/               # Main tab screens (Dashboard, Coach, Analytics, Settings)
  onboarding/           # Onboarding flow screens
  paywall.tsx           # Subscription paywall
src/
  components/           # Reusable UI components
  constants/            # Theme, config, app constants
  hooks/                # Custom React hooks
  lib/                  # External service clients (Supabase)
  stores/               # Zustand state stores
  types/                # TypeScript type definitions
  utils/                # Utility functions
supabase/
  functions/ai-coach/   # Supabase Edge Function for AI coaching
  schema.sql            # Database schema with RLS policies
```

## Features

- **RPG Gamification:** XP, HP, levels, streaks, and Life Score
- **AI Coach:** Personalized advice based on your habit data
- **Dark Mode UI:** Deep space theme with neon accents
- **Freemium Model:** Free tier with Pro subscription via RevenueCat
- **Haptic Feedback:** Tactile responses on interactions
- **Animations:** Smooth transitions with react-native-reanimated
- **GDPR Compliant:** Account and data deletion support

## Monetization

- **Free Tier:** Basic habit tracking, 1 AI interaction/day
- **Pro ($9.99/mo or $59.99/yr):** Unlimited AI coaching, advanced analytics, custom themes, data export
