// Supabase Edge Function: AI Coach
// This function proxies requests to OpenAI, keeping the API key secure server-side.
// Deploy with: supabase functions deploy ai-coach

import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const OPENAI_API_KEY = Deno.env.get("OPENAI_API_KEY") ?? "";

interface CoachContext {
  display_name: string;
  life_score: number;
  level: number;
  xp: number;
  streak: number;
  goals: string[];
  habits_completed_today: number;
  total_habits: number;
  missed_habits: string[];
}

interface RequestBody {
  message: string;
  context: CoachContext;
}

const SYSTEM_PROMPT = `You are EvolveAI Coach, a motivating and insightful AI life coach inside a gamified habit-tracking app. 
You speak in a friendly, encouraging, yet direct tone. You reference RPG/gaming metaphors naturally.
You have access to the user's real habit data and should reference it to give hyper-personalized advice.
Keep responses concise (2-4 paragraphs max). Use emojis sparingly but effectively.
Never give medical advice. Always encourage professional help for serious issues.
Focus on actionable, specific suggestions based on their data.`;

function buildUserContext(ctx: CoachContext): string {
  const parts = [
    `User: ${ctx.display_name}`,
    `Level: ${ctx.level} | XP: ${ctx.xp} | Life Score: ${ctx.life_score}/100`,
    `Current Streak: ${ctx.streak} days`,
    `Goals: ${ctx.goals.join(", ")}`,
    `Today's Progress: ${ctx.habits_completed_today}/${ctx.total_habits} habits completed`,
  ];

  if (ctx.missed_habits.length > 0) {
    parts.push(`Missed habits today: ${ctx.missed_habits.join(", ")}`);
  }

  return parts.join("\n");
}

Deno.serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers":
          "authorization, x-client-info, apikey, content-type",
      },
    });
  }

  try {
    const { message, context } = (await req.json()) as RequestBody;

    if (!OPENAI_API_KEY) {
      return new Response(
        JSON.stringify({ reply: "AI Coach is not configured yet. Please set the OPENAI_API_KEY." }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }

    const userContext = buildUserContext(context);

    const openaiResponse = await fetch(
      "https://api.openai.com/v1/chat/completions",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${OPENAI_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: [
            { role: "system", content: SYSTEM_PROMPT },
            {
              role: "system",
              content: `Current user data:\n${userContext}`,
            },
            { role: "user", content: message },
          ],
          max_tokens: 500,
          temperature: 0.7,
        }),
      }
    );

    if (!openaiResponse.ok) {
      const errorText = await openaiResponse.text();
      console.error("OpenAI API error:", errorText);
      return new Response(
        JSON.stringify({
          reply: "I'm having trouble thinking right now. Please try again in a moment!",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }

    const data = await openaiResponse.json();
    const reply = data.choices?.[0]?.message?.content ?? "Sorry, I couldn't generate a response.";

    return new Response(JSON.stringify({ reply }), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (error) {
    console.error("Edge function error:", error);
    return new Response(
      JSON.stringify({
        reply: "Something went wrong. Please try again!",
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }
});
