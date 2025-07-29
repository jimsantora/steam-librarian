"""Prompts registration for Steam Librarian MCP Server"""

from mcp.server import Server
from mcp.types import Prompt, PromptArgument

from .insight_prompts import register_insight_prompts
from .library_prompts import register_library_prompts
from .social_prompts import register_social_prompts


def register_prompts(server: Server):
    """Register all prompts with the MCP server"""
    register_library_prompts(server)
    register_social_prompts(server)
    register_insight_prompts(server)
