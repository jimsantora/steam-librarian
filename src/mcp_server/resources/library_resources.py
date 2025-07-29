"""Core library resources for Steam Librarian MCP Server"""

import json
import logging

from mcp.server import Server
from mcp.types import Resource, ResourceContents, TextResourceContents

from ..cache import cache, game_cache_key, user_cache_key
from ..errors import create_error_response, handle_mcp_errors
from ..user_context import resolve_user_context
from ..utils.activity import get_recent_activity
from ..utils.game_details import get_game_details_with_context
from ..utils.library_stats import calculate_library_overview

logger = logging.getLogger(__name__)


def register_library_resources(server: Server):
    """Register core library resources"""

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        """List available library resources"""
        return [Resource(uri="library://overview", name="Library Overview", description="Your Steam library at a glance - total games, playtime, recent activity", mimeType="application/json"), Resource(uri="library://games/{app_id}", name="Game Details", description="Deep dive into any game - details, reviews, and your personal history", mimeType="application/json"), Resource(uri="library://activity/recent", name="Recent Activity", description="What you've been playing lately", mimeType="application/json"), Resource(uri="library://genres/{genre_name}", name="Games by Genre", description="All games in your library for a specific genre", mimeType="application/json")]

    @server.read_resource()
    @handle_mcp_errors
    async def handle_read_resource(uri: str) -> ResourceContents:
        """Handle resource read requests"""

        if uri == "library://overview":
            return await read_library_overview()

        elif uri.startswith("library://games/"):
            app_id = uri.split("/")[-1]
            return await read_game_details(app_id)

        elif uri == "library://activity/recent":
            return await read_recent_activity()

        elif uri.startswith("library://genres/"):
            genre_name = uri.split("/")[-1]
            return await read_genre_games(genre_name)

        else:
            error = create_error_response("INVALID_RESOURCE", f"Unknown resource: {uri}")
            return TextResourceContents(uri=uri, mimeType="application/json", text=json.dumps(error, indent=2))


async def read_library_overview() -> ResourceContents:
    """Read library overview resource"""
    # Resolve user context
    user_context = await resolve_user_context()

    if "error" in user_context:
        return TextResourceContents(uri="library://overview", mimeType="application/json", text=json.dumps(user_context, indent=2))

    user = user_context["user"]
    cache_key = user_cache_key("overview", user.steam_id)

    # Get cached or compute stats
    stats = await cache.get_or_compute(cache_key, lambda: calculate_library_overview(user), ttl=1800)  # 30 minutes

    # Add context information
    stats["user"] = {"steam_id": user.steam_id, "persona_name": user.persona_name, "source": user_context["source"]}

    return TextResourceContents(uri="library://overview", mimeType="application/json", text=json.dumps(stats, indent=2))


async def read_game_details(app_id: str) -> ResourceContents:
    """Read game details resource"""
    # Validate app_id
    if not app_id.isdigit():
        error = create_error_response("VALIDATION_ERROR", "Invalid app_id format")
        return TextResourceContents(uri=f"library://games/{app_id}", mimeType="application/json", text=json.dumps(error, indent=2))

    # Resolve user for personal game history
    user_context = await resolve_user_context()
    user = user_context.get("user") if "user" in user_context else None

    cache_key = game_cache_key("details", app_id)
    if user:
        cache_key += f"_{user.steam_id}"

    # Get game details
    details = await cache.get_or_compute(cache_key, lambda: get_game_details_with_context(app_id, user), ttl=3600)  # 1 hour

    if "error" in details:
        return TextResourceContents(uri=f"library://games/{app_id}", mimeType="application/json", text=json.dumps(details, indent=2))

    return TextResourceContents(uri=f"library://games/{app_id}", mimeType="application/json", text=json.dumps(details, indent=2))


async def read_recent_activity() -> ResourceContents:
    """Read recent activity resource"""
    # Resolve user context
    user_context = await resolve_user_context()

    if "error" in user_context:
        return TextResourceContents(uri="library://activity/recent", mimeType="application/json", text=json.dumps(user_context, indent=2))

    user = user_context["user"]
    cache_key = user_cache_key("recent_activity", user.steam_id)

    # Get recent activity
    activity = await cache.get_or_compute(cache_key, lambda: get_recent_activity(user), ttl=300)  # 5 minutes - more frequent updates

    return TextResourceContents(uri="library://activity/recent", mimeType="application/json", text=json.dumps(activity, indent=2))


async def read_genre_games(genre_name: str) -> ResourceContents:
    """Read games by genre resource"""
    # Resolve user context
    user_context = await resolve_user_context()

    if "error" in user_context:
        return TextResourceContents(uri=f"library://genres/{genre_name}", mimeType="application/json", text=json.dumps(user_context, indent=2))

    user = user_context["user"]
    cache_key = f"genre_{genre_name}_{user.steam_id}"

    # Import here to avoid circular dependency
    from ..utils.genre_utils import get_games_by_genre

    # Get games by genre
    games = await cache.get_or_compute(cache_key, lambda: get_games_by_genre(user, genre_name), ttl=1800)  # 30 minutes

    result = {"genre": genre_name, "user": {"steam_id": user.steam_id, "persona_name": user.persona_name}, "games": games, "count": len(games)}

    return TextResourceContents(uri=f"library://genres/{genre_name}", mimeType="application/json", text=json.dumps(result, indent=2))
