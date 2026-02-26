"""Web search tool -- uses a search API (SerpAPI / Tavily) when configured,
otherwise returns a realistic placeholder result."""

from typing import Any

import httpx

from app.config import settings
from app.tools.base import Tool
from app.tools.registry import tool_registry


class WebSearchTool(Tool):
    """Search the web and return a concise summary of results."""

    def name(self) -> str:
        return "web_search"

    def description(self) -> str:
        return (
            "Search the web for current information. "
            "Use this when the user asks about recent events, weather, "
            "news, prices, or anything that requires up-to-date data."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the web.",
                },
            },
            "required": ["query"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        query = arguments.get("query", "")
        if not query:
            return "Error: No search query provided."

        # If a real search API key is configured, use it
        if settings.SEARCH_API_KEY:
            return await self._real_search(query)

        # Otherwise return a placeholder result
        return self._placeholder_search(query)

    async def _real_search(self, query: str) -> str:
        """Call the Tavily search API (or compatible endpoint)."""
        url = settings.SEARCH_API_URL
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": settings.SEARCH_API_KEY,
            "query": query,
            "max_results": 5,
            "include_answer": True,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            # Tavily returns an "answer" field plus "results"
            answer = data.get("answer", "")
            results = data.get("results", [])

            parts: list[str] = []
            if answer:
                parts.append(f"Answer: {answer}\n")

            for i, r in enumerate(results[:5], 1):
                title = r.get("title", "")
                snippet = r.get("content", r.get("snippet", ""))
                link = r.get("url", "")
                parts.append(f"{i}. {title}\n   {snippet}\n   {link}")

            return "\n".join(parts) if parts else "No results found."
        except Exception as exc:
            return f"Search API error: {exc}"

    @staticmethod
    def _placeholder_search(query: str) -> str:
        """Return a helpful placeholder when no API key is set."""
        return (
            f"[Web-Suche Platzhalter] Suchergebnisse fuer: \"{query}\"\n\n"
            f"1. Wikipedia - {query}\n"
            f"   Umfassender Artikel ueber {query} mit aktuellen Informationen.\n"
            f"   https://de.wikipedia.org/wiki/{query.replace(' ', '_')}\n\n"
            f"2. Aktuelle Nachrichten zu {query}\n"
            f"   Die neuesten Entwicklungen und Berichte.\n"
            f"   https://news.google.com/search?q={query.replace(' ', '+')}\n\n"
            "Hinweis: Dies sind Platzhalter-Ergebnisse. "
            "Konfiguriere SEARCH_API_KEY in den Einstellungen fuer echte Suchergebnisse."
        )


# Auto-register
tool_registry.register(WebSearchTool())
