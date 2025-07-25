"""Steam Library MCP Server - Main server setup"""
import os
from fastmcp import FastMCP

# Import all tools to register them
from src.mcp.tools import (
    search, details, stats, recommendations, user
)
from src.mcp.prompts import user_selection

# Create the server instance
mcp = FastMCP("steam-librarian")

# Get Steam ID from environment (fallback for backwards compatibility)
STEAM_ID = os.environ.get('STEAM_ID', '')

# Register prompts
mcp.prompt(user_selection.select_user_prompt)

# Register all tools
mcp.tool(user.get_all_users)
mcp.tool(user.get_user_info)
mcp.tool(search.search_games)
mcp.tool(search.filter_games)
mcp.tool(details.get_game_details)
mcp.tool(details.get_game_reviews)
mcp.tool(stats.get_library_stats)
mcp.tool(user.get_recently_played)
mcp.tool(recommendations.get_recommendations)
mcp.tool(user.get_friends_data)

def main():
    """Main entry point for the MCP server"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()