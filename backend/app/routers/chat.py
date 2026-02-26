"""Chat router - handles LLM conversation endpoints."""

from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatMessage, ChatRequest, ChatResponse, ToolCall, ToolResult
from app.llm import get_llm_provider

# Import tools so they auto-register in the registry
import app.tools.web_search  # noqa: F401
import app.tools.code_execution  # noqa: F401
import app.tools.file_tools  # noqa: F401
from app.tools import tool_registry, get_tool_definitions

router = APIRouter(prefix="/api/chat", tags=["chat"])

# System prompts for different modes
MODE_SYSTEM_PROMPTS: dict[str, str] = {
    "normal": (
        "Du bist ein hilfreicher Assistent. Antworte klar, freundlich und "
        "praezise auf die Fragen des Nutzers. "
        "Du hast Zugriff auf Tools (Web-Suche, Code-Ausfuehrung, Datei-Zugriff). "
        "Nutze sie wenn noetig."
    ),
    "programmer": (
        "Du bist ein erfahrener Programmier-Assistent. Hilf dem Nutzer beim "
        "Schreiben, Debuggen und Erklaeren von Code. Nutze Code-Bloecke mit "
        "Syntax-Highlighting. Erklaere deine Loesungen Schritt fuer Schritt. "
        "Du kannst den Code-Execution-Tool nutzen um Code auszufuehren."
    ),
    "document_analysis": (
        "Du bist ein Dokumenten-Analyse-Assistent. Der Nutzer wird dir Text "
        "aus Dokumenten bereitstellen. Analysiere den Inhalt gruendlich, fasse "
        "zusammen, beantworte Fragen zum Text und identifiziere Kernaussagen."
    ),
}


async def _execute_tool_calls(tool_calls: list[ToolCall]) -> list[ToolResult]:
    """Execute a list of tool calls and return their results."""
    results: list[ToolResult] = []
    for tc in tool_calls:
        tool = tool_registry.get(tc.name)
        if tool is None:
            result_text = f"Error: Unknown tool '{tc.name}'"
        else:
            try:
                result_text = await tool.execute(tc.arguments)
            except Exception as exc:
                result_text = f"Tool execution error: {exc}"

        results.append(ToolResult(
            tool_call_id=tc.id,
            name=tc.name,
            result=result_text,
        ))
    return results


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat request and return the LLM's response.

    Supports multi-turn conversation with configurable modes, system prompts,
    and automatic tool calling.
    """
    try:
        provider = get_llm_provider()

        # Ollama fallback: if Ollama is selected but unreachable, fall back to dummy
        if provider.provider_name() == "ollama":
            from app.llm.ollama_provider import ollama_health_check
            if not await ollama_health_check():
                from app.llm.dummy import DummyProvider
                provider = DummyProvider()

        # Determine system prompt: custom > mode default
        system_prompt = request.system_prompt
        if not system_prompt:
            system_prompt = MODE_SYSTEM_PROMPTS.get(request.mode, MODE_SYSTEM_PROMPTS["normal"])

        # If file context is provided, prepend it to the system prompt
        if request.file_context:
            system_prompt += (
                "\n\n--- Dokument-Kontext ---\n"
                f"{request.file_context}\n"
                "--- Ende Dokument-Kontext ---"
            )

        # ---- Tool-calling flow ----
        tool_calls: list[ToolCall] = []
        tool_results: list[ToolResult] = []

        if request.enable_tools and get_tool_definitions():
            # Ask the provider whether it wants to call a tool
            has_tool_support = hasattr(provider, "chat_with_tools")

            if has_tool_support:
                response_message, tool_calls = await provider.chat_with_tools(
                    messages=request.messages,
                    system_prompt=system_prompt,
                    tool_definitions=get_tool_definitions(),
                )

                if tool_calls:
                    # Execute the tools
                    tool_results = await _execute_tool_calls(tool_calls)

                    # Build a summary for the LLM
                    results_text = "\n\n".join(
                        f"[Tool: {r.name}]\n{r.result}" for r in tool_results
                    )

                    # Let the LLM generate a final answer incorporating results
                    has_result_support = hasattr(provider, "chat_with_tool_results")
                    if has_result_support:
                        response_message = await provider.chat_with_tool_results(
                            messages=request.messages,
                            tool_results_text=results_text,
                            system_prompt=system_prompt,
                        )
                    else:
                        # Fallback: inject tool results as an assistant message
                        augmented = list(request.messages) + [
                            ChatMessage(role="assistant", content=f"Tool-Ergebnisse:\n{results_text}")
                        ]
                        response_message = await provider.chat(augmented, system_prompt)

                if response_message is None:
                    # Safety fallback
                    response_message = await provider.chat(request.messages, system_prompt)
            else:
                response_message = await provider.chat(
                    messages=request.messages,
                    system_prompt=system_prompt,
                )
        else:
            # Tools disabled or no tools registered
            response_message = await provider.chat(
                messages=request.messages,
                system_prompt=system_prompt,
            )

        return ChatResponse(
            message=response_message,
            provider=provider.provider_name(),
            model=provider.model_name(),
            tool_calls=tool_calls,
            tool_results=tool_results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
