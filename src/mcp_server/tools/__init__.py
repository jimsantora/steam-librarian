"""Tools registration for Steam Librarian MCP Server"""

from mcp.server.fastmcp import FastMCP


def register_tools(mcp: FastMCP):
    """Register all tools with the FastMCP server"""
    # Import all tool modules to register their @mcp.tool() decorators
    from . import (
        filter_games,
        get_friends_data,
        get_library_stats,
        get_recommendations,
        search_games,
    )
