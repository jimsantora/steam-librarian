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


        if argument.name == "session_length" and tool_name == "find_quick_session_games":
            return Completion(values=[
                "short", "medium", "long"
            ], hasMore=False)

    return None
