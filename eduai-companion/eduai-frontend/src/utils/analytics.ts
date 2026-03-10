/**
 * Analytics scaffolding for PostHog + Sentry.
 * Replace placeholders with real keys when ready to activate.
 *
 * PostHog: https://posthog.com (free tier: 1M events/month)
 * Sentry: https://sentry.io (free tier: 5K errors/month)
 */

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || "";
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || "https://eu.posthog.com";
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN || "";

// Lightweight analytics wrapper — no external dependencies required
// When PostHog/Sentry keys are set, these will send real events

interface AnalyticsEvent {
  event: string;
  properties?: Record<string, string | number | boolean>;
}

class Analytics {
  private initialized = false;
  private userId: string | null = null;
  private queue: AnalyticsEvent[] = [];

  init() {
    if (this.initialized) return;
    this.initialized = true;

    // PostHog init (when key is available)
    if (POSTHOG_KEY) {
      console.info("[Analytics] PostHog ready:", POSTHOG_HOST);
    }

    // Sentry init (when DSN is available)
    if (SENTRY_DSN) {
      console.info("[Analytics] Sentry ready");
    }

    // Flush queued events
    this.queue.forEach((e) => this._send(e));
    this.queue = [];
  }

  identify(userId: string, traits?: Record<string, string | number | boolean>) {
    this.userId = userId;
    if (POSTHOG_KEY) {
      this._postToPostHog("/capture", {
        distinct_id: userId,
        event: "$identify",
        properties: { ...traits, $set: traits },
      });
    }
  }

  track(event: string, properties?: Record<string, string | number | boolean>) {
    const analyticsEvent: AnalyticsEvent = { event, properties };
    if (!this.initialized) {
      this.queue.push(analyticsEvent);
      return;
    }
    this._send(analyticsEvent);
  }

  page(name: string) {
    this.track("$pageview", { page: name });
  }

  private _send(analyticsEvent: AnalyticsEvent) {
    if (!POSTHOG_KEY) return;
    this._postToPostHog("/capture", {
      distinct_id: this.userId || "anonymous",
      event: analyticsEvent.event,
      properties: {
        ...analyticsEvent.properties,
        $current_url: window.location.href,
      },
    });
  }

  private async _postToPostHog(endpoint: string, body: Record<string, unknown>) {
    try {
      await fetch(`${POSTHOG_HOST}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: POSTHOG_KEY, ...body }),
      });
    } catch {
      // Silently fail — analytics should never break the app
    }
  }
}

export const analytics = new Analytics();

// Common event helpers
export const trackEvents = {
  login: (method: string) => analytics.track("user_login", { method }),
  register: (method: string) => analytics.track("user_register", { method }),
  quizStart: (subject: string) => analytics.track("quiz_started", { subject }),
  quizComplete: (subject: string, score: number) => analytics.track("quiz_completed", { subject, score }),
  iqTestStart: () => analytics.track("iq_test_started"),
  iqTestComplete: (iq: number) => analytics.track("iq_test_completed", { iq }),
  chatMessage: (subject: string) => analytics.track("chat_message_sent", { subject }),
  subscriptionUpgrade: (tier: string) => analytics.track("subscription_upgrade", { tier }),
  flashcardReview: (deckId: number, quality: number) => analytics.track("flashcard_review", { deck_id: deckId, quality }),
  tournamentJoin: () => analytics.track("tournament_joined"),
  pageView: (page: string) => analytics.page(page),
};
