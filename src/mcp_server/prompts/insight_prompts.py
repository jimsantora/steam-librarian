"""Insight and analysis prompts for Steam Librarian MCP Server"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import Prompt, PromptArgument, PromptMessage

logger = logging.getLogger(__name__)


def register_insight_prompts(server: Server):
    """Register insight and analysis prompts"""

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="analyze_gaming_patterns",
                description="What kind of gamer am I?",
                arguments=[
                    PromptArgument(
                        name="time_period",
                        description="Analyze patterns for what period? (e.g., 'all time', 'last year')",
                        required=False
                    ),
                    PromptArgument(
                        name="focus_area",
                        description="Specific aspect to analyze (genres, playtime, completion)?",
                        required=False
                    )
                ]
            )
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, Any]) -> list[PromptMessage]:
        if name == "analyze_gaming_patterns":
            return await analyze_patterns_prompt(arguments)
        return []


async def analyze_patterns_prompt(arguments: dict[str, Any]) -> list[PromptMessage]:
    """Provide insights into gaming habits"""

    time_period = arguments.get("time_period", "all time")
    focus_area = arguments.get("focus_area", "comprehensive")

    messages = [
        PromptMessage(
            role="user",
            content={
                "type": "text",
                "text": f"I want to understand my gaming patterns. Analyze my {time_period} gaming habits, focusing on {focus_area}."
            }
        ),
        PromptMessage(
            role="assistant",
            content={
                "type": "text",
                "text": "I'll analyze your gaming patterns and provide insights into your habits. This will include your genre preferences, playtime patterns, and gaming tendencies..."
            }
        ),
        PromptMessage(
            role="assistant",
            content={
                "type": "tool_use",
                "name": "get_library_stats",
                "arguments": {
                    "time_period": time_period,
                    "include_insights": True
                }
            }
        )
    ]

    # Add specific analysis based on focus area
    if focus_area == "genres":
        messages.append(
            PromptMessage(
                role="assistant",
                content={
                    "type": "text",
                    "text": "Let me also check your library overview for genre distribution..."
                }
            )
        )
        messages.append(
            PromptMessage(
                role="assistant",
                content={
                    "type": "resource",
                    "resource": {
                        "uri": "library://overview",
                        "text": "Analyzing genre preferences"
                    }
                }
            )
        )
    elif focus_area == "completion":
        messages.append(
            PromptMessage(
                role="assistant",
                content={
                    "type": "text",
                    "text": "Let me find games you're close to completing..."
                }
            )
        )
        messages.append(
            PromptMessage(
                role="assistant",
                content={
                    "type": "tool_use",
                    "name": "filter_games",
                    "arguments": {
                        "playtime_min": 5,
                        "playtime_max": 50,
                        "sort_by": "playtime_desc"
                    }
                }
            )
        )

    return messages
