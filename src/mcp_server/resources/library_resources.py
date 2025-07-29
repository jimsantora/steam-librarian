"""Core library resources for Steam Librarian MCP Server"""

import json
import logging

from mcp_server.cache import cache, game_cache_key, user_cache_key
from mcp_server.server import mcp
from mcp_server.user_context import resolve_user_context
from mcp_server.utils.activity import get_recent_activity
from mcp_server.utils.game_details import get_game_details_with_context
from mcp_server.utils.library_stats import calculate_library_overview

logger = logging.getLogger(__name__)


@mcp.resource("library://overview")
async def library_overview() -> str:
    """Your Steam library at a glance - total games, playtime, recent activity"""

    user_context = await resolve_user_context()
    if "error" in user_context:
        return json.dumps(user_context, indent=2)

    user = user_context["user"]
    cache_key = user_cache_key("overview", user.steam_id)

    # Try cache first
    cached_stats = await cache.get(cache_key)
    if cached_stats:
        return cached_stats

    # Calculate fresh stats
    stats = calculate_library_overview(user)

    # Add context information
    stats["user"] = {"steam_id": user.steam_id, "persona_name": user.persona_name, "source": user_context["source"]}

    # Cache the result
    stats_json = json.dumps(stats, indent=2)
    await cache.set(cache_key, stats_json, ttl=1800)  # 30 minutes

    return stats_json


@mcp.resource("library://games/{app_id}")
def game_details(app_id: str) -> str:
    """Deep dive into any game - details, reviews, and your personal history"""
    import asyncio

    if not app_id.isdigit():
        error = {"error": True, "error_type": "VALIDATION_ERROR", "message": "Invalid app_id format"}
        return json.dumps(error, indent=2)

    async def _get_game_details():
        # Resolve user for personal game history
        user_context = await resolve_user_context()
        user = user_context.get("user") if "user" in user_context else None

        cache_key = game_cache_key("details", app_id)
        if user:
            cache_key += f"_{user.steam_id}"

        # Try cache first
        cached_details = await cache.get(cache_key)
        if cached_details:
            return cached_details

        # Get fresh details
        details = get_game_details_with_context(app_id, user)

        # Cache the result
        details_json = json.dumps(details, indent=2)
        await cache.set(cache_key, details_json, ttl=3600)  # 1 hour

        return details_json

    # Get or create event loop and run async function
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, need to create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_game_details())
                return future.result()
        else:
            return loop.run_until_complete(_get_game_details())
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(_get_game_details())


@mcp.resource("library://activity/recent")
async def recent_activity() -> str:
    """What you've been playing lately"""

    user_context = await resolve_user_context()
    if "error" in user_context:
        return json.dumps(user_context, indent=2)

    user = user_context["user"]
    cache_key = user_cache_key("recent_activity", user.steam_id)

    # Try cache first
    cached_activity = await cache.get(cache_key)
    if cached_activity:
        return cached_activity

    # Get fresh activity
    activity = get_recent_activity(user)

    # Cache the result
    activity_json = json.dumps(activity, indent=2)
    await cache.set(cache_key, activity_json, ttl=300)  # 5 minutes - more frequent updates

    return activity_json


@mcp.resource("library://genres/{genre_name}")
def games_by_genre(genre_name: str) -> str:
    """All games in your library for a specific genre"""
    import asyncio

    async def _get_games_by_genre():
        user_context = await resolve_user_context()
        if "error" in user_context:
            return json.dumps(user_context, indent=2)

        user = user_context["user"]
        cache_key = f"genre_{genre_name}_{user.steam_id}"

        # Try cache first
        cached_games = await cache.get(cache_key)
        if cached_games:
            return cached_games

        # Import here to avoid circular dependency
        from mcp_server.utils.genre_utils import get_games_by_genre

        # Get games by genre
        games = get_games_by_genre(user, genre_name)

        result = {"genre": genre_name, "user": {"steam_id": user.steam_id, "persona_name": user.persona_name}, "games": games, "count": len(games)}

        # Cache the result
        result_json = json.dumps(result, indent=2)
        await cache.set(cache_key, result_json, ttl=1800)  # 30 minutes

        return result_json

    # Get or create event loop and run async function
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, need to create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_games_by_genre())
                return future.result()
        else:
            return loop.run_until_complete(_get_games_by_genre())
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(_get_games_by_genre())
