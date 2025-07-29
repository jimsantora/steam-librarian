"""Social gaming prompts for Steam Librarian MCP Server"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import Prompt, PromptArgument, PromptMessage

logger = logging.getLogger(__name__)


def register_social_prompts(server: Server):
    """Register social gaming prompts"""

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="plan_multiplayer_session",
                description="What can my friends and I play tonight?",
                arguments=[
                    PromptArgument(
                        name="friend_count",
                        description="How many people will be playing?",
                        required=True
                    ),
                    PromptArgument(
                        name="session_length",
                        description="How long is your gaming session?",
                        required=False
                    ),
                    PromptArgument(
                        name="game_type",
                        description="Preferred type (co-op, competitive, casual)?",
                        required=False
                    )
                ]
            )
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, Any]) -> list[PromptMessage]:
        if name == "plan_multiplayer_session":
            return await plan_multiplayer_prompt(arguments)
        return []


async def plan_multiplayer_prompt(arguments: dict[str, Any]) -> list[PromptMessage]:
    """Help coordinate multiplayer gaming sessions"""

    friend_count = arguments.get("friend_count", 1)
    session_length = arguments.get("session_length", "2-3 hours")
    game_type = arguments.get("game_type", "any")

    messages = [
        PromptMessage(
            role="user",
            content={
                "type": "text",
                "text": f"I need help planning a gaming session for {friend_count} people. We have {session_length} to play. Game type preference: {game_type}."
            }
        ),
        PromptMessage(
            role="assistant",
            content={
                "type": "text",
                "text": "I'll find the perfect games for your group. Let me check what games you all have in common and what supports your player count..."
            }
        ),
        PromptMessage(
            role="assistant",
            content={
                "type": "tool_use",
                "name": "get_friends_data",
                "arguments": {
                    "data_type": "multiplayer_compatible"
                }
            }
        )
    ]

    # Add specific search based on game type
    if game_type != "any":
        messages.append(
            PromptMessage(
                role="assistant",
                content={
                    "type": "text",
                    "text": f"Now let me search for {game_type} games specifically..."
                }
            )
        )
        messages.append(
            PromptMessage(
                role="assistant",
                content={
                    "type": "tool_use",
                    "name": "search_games",
                    "arguments": {
                        "query": f"{game_type} multiplayer games for {friend_count} players"
                    }
                }
            )
        )

    return messages
