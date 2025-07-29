"""Core library prompts for Steam Librarian MCP Server"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import Prompt, PromptArgument, PromptMessage

logger = logging.getLogger(__name__)


def register_library_prompts(server: Server):
    """Register library-focused prompts"""

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [Prompt(name="rediscover_library", description="Find something you already own to play", arguments=[PromptArgument(name="mood", description="What kind of gaming mood are you in? (e.g., relaxing, intense, social)", required=False), PromptArgument(name="time_available", description="How much time do you have? (e.g., '30 minutes', '2 hours')", required=False)]), Prompt(name="gaming_therapy", description="Get gaming recommendations based on how you're feeling", arguments=[PromptArgument(name="feeling", description="How are you feeling today?", required=True), PromptArgument(name="energy_level", description="Low, medium, or high energy?", required=False)]), Prompt(name="weekend_planner", description="Plan your weekend gaming sessions", arguments=[PromptArgument(name="available_hours", description="How many hours for gaming?", required=True), PromptArgument(name="solo_or_social", description="Solo, friends, or both?", required=False)]), Prompt(name="backlog_therapist", description="Get help tackling your backlog without overwhelm", arguments=[PromptArgument(name="commitment_level", description="Light, medium, or deep commitment?", required=False)])]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, Any]) -> list[PromptMessage]:
        if name == "rediscover_library":
            return await rediscover_library_prompt(arguments)
        elif name == "gaming_therapy":
            return await gaming_therapy_prompt(arguments)
        elif name == "weekend_planner":
            return await weekend_planner_prompt(arguments)
        elif name == "backlog_therapist":
            return await backlog_therapist_prompt(arguments)
        return []


async def rediscover_library_prompt(arguments: dict[str, Any]) -> list[PromptMessage]:
    """The signature experience - intelligent library rediscovery"""

    mood = arguments.get("mood", "any")
    time_available = arguments.get("time_available", "any")

    messages = [PromptMessage(role="user", content={"type": "text", "text": f"I want to find something to play from my Steam library. Mood: {mood}. Time available: {time_available}."}), PromptMessage(role="assistant", content={"type": "text", "text": "Let me help you rediscover something perfect from your library. First, I'll check what you've been playing recently to avoid repetition..."}), PromptMessage(role="assistant", content={"type": "resource", "resource": {"uri": "library://activity/recent", "text": "Checking recent activity"}}), PromptMessage(role="assistant", content={"type": "text", "text": "Now let me find games that match your current mood and available time..."}), PromptMessage(role="assistant", content={"type": "tool_use", "name": "get_recommendations", "arguments": {"context": {"mood": mood, "time_available": time_available, "exclude_recent": True}}})]

    return messages


async def gaming_therapy_prompt(arguments: dict[str, Any]) -> list[PromptMessage]:
    """Get gaming recommendations based on emotional state"""

    feeling = arguments.get("feeling", "")
    energy_level = arguments.get("energy_level", "medium")

    # Map feelings to gaming moods
    feeling_to_mood = {"stressed": "relaxing", "anxious": "calming", "bored": "engaging", "sad": "uplifting", "angry": "cathartic", "happy": "social", "tired": "casual"}

    mood = "any"
    for key, value in feeling_to_mood.items():
        if key in feeling.lower():
            mood = value
            break

    messages = [PromptMessage(role="user", content={"type": "text", "text": f"I'm feeling {feeling} with {energy_level} energy. What should I play?"}), PromptMessage(role="assistant", content={"type": "text", "text": f"I understand you're feeling {feeling}. Let me find games that might help..."}), PromptMessage(role="assistant", content={"type": "tool_use", "name": "search_games", "arguments": {"query": f"{mood} games for {energy_level} energy"}})]

    return messages


async def weekend_planner_prompt(arguments: dict[str, Any]) -> list[PromptMessage]:
    """Plan weekend gaming sessions"""

    available_hours = arguments.get("available_hours", "")
    solo_or_social = arguments.get("solo_or_social", "both")

    messages = [PromptMessage(role="user", content={"type": "text", "text": f"I have {available_hours} hours for gaming this weekend. Preference: {solo_or_social}."}), PromptMessage(role="assistant", content={"type": "text", "text": "Let me help you plan an awesome gaming weekend! First, let me check your library stats to understand your preferences..."}), PromptMessage(role="assistant", content={"type": "tool_use", "name": "get_library_stats", "arguments": {"include_insights": True}})]

    if solo_or_social in ["social", "both"]:
        messages.append(PromptMessage(role="assistant", content={"type": "text", "text": "Now let me check what multiplayer games you and your friends could enjoy..."}))
        messages.append(PromptMessage(role="assistant", content={"type": "tool_use", "name": "get_friends_data", "arguments": {"data_type": "multiplayer_compatible"}}))

    return messages


async def backlog_therapist_prompt(arguments: dict[str, Any]) -> list[PromptMessage]:
    """Help tackle gaming backlog"""

    commitment_level = arguments.get("commitment_level", "medium")

    # Map commitment to playtime ranges
    commitment_to_playtime = {"light": {"max": 10}, "medium": {"min": 0, "max": 50}, "deep": {"min": 10}}

    playtime_filter = commitment_to_playtime.get(commitment_level, {})

    messages = [PromptMessage(role="user", content={"type": "text", "text": f"Help me tackle my backlog with {commitment_level} commitment level."}), PromptMessage(role="assistant", content={"type": "text", "text": "Let's tackle that backlog together! First, let me see what hidden gems you've been neglecting..."}), PromptMessage(role="assistant", content={"type": "tool_use", "name": "filter_games", "arguments": {"preset": "hidden_gems", **playtime_filter}})]

    return messages
