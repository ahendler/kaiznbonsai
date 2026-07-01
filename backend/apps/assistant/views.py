import json
from datetime import date

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .tools import TOOL_DEFINITIONS, execute_tool

_SYSTEM_TEMPLATE = """You are an assistant for KaiznBonsai, an inventory management app for F&B brands.
You help the authenticated user understand their products, stock levels, orders, and financials.
Always use tools to retrieve current data — never guess or estimate figures.
Be concise and direct. When returning numbers, include units (e.g. "12.5 L", "$340.00").
Do not use emojis.
Do not answer questions outside of the inventory management domain.
Today's date is {today}."""

_MAX_ITERATIONS = 10


def _get_client():
    """Return an Anthropic client, or None if the API key is not configured."""
    key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not key:
        return None
    import anthropic  # deferred so missing package doesn't crash startup
    return anthropic.Anthropic(api_key=key)


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        client = _get_client()
        if client is None:
            return Response(
                {"error": "AI assistant is not configured on this server."},
                status=503,
            )

        messages = list(request.data.get("messages", []))
        system = _SYSTEM_TEMPLATE.format(today=date.today().isoformat())

        for _ in range(_MAX_ITERATIONS):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                thinking={"type": "adaptive"},
                tools=TOOL_DEFINITIONS,
                system=system,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                reply = next(
                    (block.text for block in response.content if block.type == "text"),
                    "",
                )
                return Response({"reply": reply})

            # Execute requested tools.
            # Pass response.content back verbatim (including thinking blocks) so
            # the model retains reasoning continuity across iterations.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                try:
                    result = execute_tool(block.name, block.input, user=request.user)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })
                except Exception as exc:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "is_error": True,
                        "content": str(exc),
                    })

            messages = [
                *messages,
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": tool_results},
            ]

        return Response(
            {"error": "Could not complete the request — please try again."},
            status=500,
        )
