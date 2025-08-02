# src/mcp_server/completions.py
from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)

# Import the server instance from server.py
from .server import mcp


@mcp.completion()
async def tool_argument_completions(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion | None:
    """Provide intelligent completions for tool arguments."""

    # Handle tool-specific completions
    if hasattr(ref, 'toolName'):
        tool_name = ref.toolName

        if argument.name == "child_age" and tool_name == "find_family_games":
            return Completion(values=[
                "3", "5", "7", "10", "13", "16"
            ], hasMore=False)

        if argument.name == "type" and tool_name == "find_multiplayer_games":
            return Completion(values=[
                "coop", "pvp", "local", "online"
            ], hasMore=False)

        if argument.name == "platform" and tool_name == "find_games_by_platform":
            return Completion(values=[
                "windows", "mac", "linux", "vr"
            ], hasMore=False)

        if argument.name == "min_rating" and tool_name == "find_unplayed_gems":
            return Completion(values=[
                "60", "70", "75", "80", "85", "90"
            ], hasMore=False)

        if argument.name == "max_hours" and tool_name == "find_short_games":
            return Completion(values=[
                "0.5", "1.0", "2.0", "3.0", "5.0"
            ], hasMore=False)

    return None
