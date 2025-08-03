"""Basic MCP prompts for Steam Librarian"""

from mcp.server.fastmcp.prompts import base

from .server import mcp


@mcp.prompt(title="Game Discovery")
def discover_games(genre: str = "Action", mood: str = "adventurous") -> str:
    """Help discover games based on genre and mood."""
    return f"Find me {genre} games that match a {mood} mood. I'm looking for something engaging and fun to play."


@mcp.prompt(title="Quick Recommendation")
def quick_recommendation() -> list[base.Message]:
    """Get a quick game recommendation conversation."""
    return [
        base.UserMessage("I want to play something new but don't know what"),
        base.AssistantMessage("What genre are you in the mood for? Action, RPG, Strategy, or something else?"),
        base.UserMessage("I'm feeling like something relaxing"),
        base.AssistantMessage("For relaxing games, I'd recommend checking out simulation or puzzle games. What's your preference on time commitment?")
    ]


@mcp.prompt(title="Library Analysis")
def analyze_library(focus: str = "genres") -> str:
    """Analyze game library with specific focus."""
    return f"Analyze my Steam library focusing on {focus}. Show me patterns, gaps, and recommendations based on what I already own."


@mcp.prompt(title="Gaming Session Planner")
def plan_gaming_session(time_available: str = "2 hours", players: str = "solo") -> str:
    """Plan a gaming session based on available time and players."""
    return f"I have {time_available} available for gaming with {players} player(s). What games from my library would work well for this session? Consider game length and whether I can make meaningful progress."


@mcp.prompt(title="Multiplayer Finder")
def find_multiplayer_games() -> list[base.Message]:
    """Find multiplayer games conversation."""
    return [
        base.UserMessage("I want to play games with friends online"),
        base.AssistantMessage("How many friends will be playing? And what type of multiplayer experience are you looking for - competitive, cooperative, or casual?"),
        base.UserMessage("3-4 friends, we like cooperative games"),
        base.AssistantMessage("Great! I'll look for co-op games that support 4 players. Do you prefer action games, strategy games, or are you open to different genres?")
    ]


@mcp.prompt(title="Game Completion Helper")
def completion_helper(game_name: str) -> str:
    """Get help with completing a specific game."""
    return f"I'm playing {game_name} and want to complete it fully. What should I focus on? Are there any missable achievements or content I should know about?"
