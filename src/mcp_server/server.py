#!/usr/bin/env python3
"""Steam Librarian MCP Server - HTTP Streaming Implementation"""

import logging

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)
from sqlalchemy import text
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from .config import config_manager, settings

# Configure logging
logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create the FastMCP server instance for HTTP streaming
mcp = FastMCP("steam-librarian", host=settings.host, port=settings.port)


@mcp.completion()
async def handle_completion(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None = None,
) -> Completion | None:
    """Provide smart completions for Steam Librarian prompts and resources."""

    # For now, we'll provide general gaming completions for any completion request
    # This gives users helpful suggestions regardless of context

    if argument.name in ["query", "search", "games"]:
        return await _get_query_completions(argument.value)
    elif argument.name in ["mood", "feeling"]:
        return _get_mood_completions(argument.value)
    elif argument.name in ["time", "duration", "time_constraint"]:
        return _get_time_completions(argument.value)
    elif argument.name in ["genre", "genres", "category"]:
        return _get_genre_completions(argument.value)
    elif argument.name in ["feature", "features", "type"]:
        return _get_feature_completions(argument.value)
    elif argument.name == "context":
        return await _get_context_completions(argument.value)

    # Default: provide query completions for any partial text that looks like a search
    if len(argument.value) > 2:
        return await _get_query_completions(argument.value)

    return None


async def _get_query_completions(partial: str) -> Completion:
    """Provide natural language query completions."""
    patterns = ["games like Portal", "games like Hades", "games like Minecraft", "games like Stardew Valley", "something relaxing", "something intense", "something quick", "something to play with friends", "puzzle games", "action games", "indie games", "multiplayer games", "single player games", "co-op games", "hidden gems in my library", "games I haven't played yet", "short games under 2 hours", "games for a quick session"]

    matching = [pattern for pattern in patterns if pattern.lower().startswith(partial.lower())]
    return Completion(values=matching, hasMore=len(matching) < len(patterns))


def _get_mood_completions(partial: str) -> Completion:
    """Provide mood completions."""
    moods = ["chill", "intense", "creative", "social", "nostalgic"]
    matching = [mood for mood in moods if mood.startswith(partial.lower())]
    return Completion(values=matching, hasMore=False)


def _get_time_completions(partial: str) -> Completion:
    """Provide time constraint completions."""
    time_options = ["30 minutes", "1 hour", "2 hours", "a few hours", "quick session", "short game", "long session", "unlimited time"]
    matching = [option for option in time_options if option.lower().startswith(partial.lower())]
    return Completion(values=matching, hasMore=False)


async def _get_context_completions(partial: str) -> Completion:
    """Provide context completions for recommendations."""
    contexts = ["something relaxing for an hour", "intense action for a quick session", "creative games for the weekend", "co-op games to play with friends", "nostalgic games from my childhood", "puzzle games for a brain workout", "story-rich games for immersion", "casual games for background play"]
    matching = [ctx for ctx in contexts if ctx.lower().startswith(partial.lower())]
    return Completion(values=matching, hasMore=False)


def _get_genre_completions(partial: str) -> Completion:
    """Provide Steam genre completions."""
    genres = ["Action", "Adventure", "Casual", "Indie", "Massively Multiplayer", "Racing", "RPG", "Simulation", "Sports", "Strategy", "Puzzle", "Shooter", "Fighting", "Platformer", "Horror", "Survival", "Open World", "Sandbox", "Roguelike", "Metroidvania"]
    matching = [genre for genre in genres if genre.lower().startswith(partial.lower())]
    return Completion(values=matching, hasMore=False)


def _get_feature_completions(partial: str) -> Completion:
    """Provide game feature completions."""
    features = ["multiplayer", "co-op", "single-player", "online", "local", "controller support", "steam deck verified", "vr support", "achievements", "trading cards", "workshop", "cloud saves"]
    matching = [feature for feature in features if feature.lower().startswith(partial.lower())]
    return Completion(values=matching, hasMore=False)


def _get_friends_data_type_completions(partial: str) -> Completion:
    """Provide friends data type completions."""
    data_types = ["common_games", "friend_activity", "multiplayer_compatible", "compatibility_score"]
    matching = [dt for dt in data_types if dt.startswith(partial.lower())]
    return Completion(values=matching, hasMore=False)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    """Health check endpoint for liveness/readiness probes"""
    try:
        # Test database connection
        from shared.database import get_db

        with get_db() as session:
            # Simple query to test DB connectivity
            session.execute(text("SELECT 1")).fetchone()

        # Test cache system
        from .cache import cache

        await cache.set("health_check", "ok", ttl=60)
        cache_status = await cache.get("health_check")

        if cache_status != "ok":
            return PlainTextResponse("UNHEALTHY: Cache not working", status_code=503)

        return PlainTextResponse("OK")

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return PlainTextResponse(f"UNHEALTHY: {str(e)}", status_code=503)


@mcp.custom_route("/health/detailed", methods=["GET"])
async def detailed_health_check(request: Request):
    """Detailed health check with component status"""
    import os
    import sys
    from datetime import datetime

    from starlette.responses import JSONResponse

    health_data = {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "server": {"name": mcp.name, "version": "2.0.0", "python_version": sys.version, "pid": os.getpid()}, "components": {}}

    # Test database
    try:
        from shared.database import get_db

        with get_db() as session:
            result = session.execute(text("SELECT COUNT(*) FROM user_profile")).scalar()
            health_data["components"]["database"] = {"status": "healthy", "user_count": result}
    except Exception as e:
        health_data["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_data["status"] = "unhealthy"

    # Test cache
    try:
        from .cache import cache

        await cache.set("health_detailed", "test", ttl=60)
        cache_result = await cache.get("health_detailed")
        health_data["components"]["cache"] = {"status": "healthy" if cache_result == "test" else "unhealthy"}
    except Exception as e:
        health_data["components"]["cache"] = {"status": "unhealthy", "error": str(e)}
        health_data["status"] = "unhealthy"

    # Test tools
    try:
        tools = await mcp.list_tools()
        health_data["components"]["tools"] = {"status": "healthy", "count": len(tools), "available": [tool.name for tool in tools]}
    except Exception as e:
        health_data["components"]["tools"] = {"status": "unhealthy", "error": str(e)}
        health_data["status"] = "unhealthy"

    status_code = 200 if health_data["status"] == "healthy" else 503
    return JSONResponse(health_data, status_code=status_code)


@mcp.custom_route("/config", methods=["GET"])
async def get_configuration(request: Request):
    """Get current server configuration"""
    from starlette.responses import JSONResponse

    config_data = {"server_info": config_manager.get_server_info(), "performance": config_manager.get_performance_config(), "features": config_manager.get_feature_flags(), "validation": config_manager.validate_configuration()}

    return JSONResponse(config_data)


@mcp.custom_route("/metrics", methods=["GET"])
async def get_metrics(request: Request):
    """Get basic server metrics"""
    import os
    from datetime import datetime

    import psutil
    from starlette.responses import JSONResponse

    try:
        # System metrics
        process = psutil.Process(os.getpid())

        metrics_data = {"timestamp": datetime.utcnow().isoformat(), "system": {"cpu_percent": process.cpu_percent(), "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2), "memory_percent": process.memory_percent(), "threads": process.num_threads(), "uptime_seconds": round((datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds())}, "server": {"name": mcp.name, "version": "2.0.0", "pid": os.getpid()}}

        # Add cache metrics if available
        try:
            from .cache import cache

            if hasattr(cache, "_cache"):
                metrics_data["cache"] = {"size": len(cache._cache), "max_size": settings.cache_max_size, "hit_rate": getattr(cache, "_hit_rate", 0.0)}
        except Exception:
            pass

        # Add database metrics if available
        try:
            from shared.database import get_db

            with get_db() as session:
                user_count = session.execute(text("SELECT COUNT(*) FROM user_profile")).scalar()
                game_count = session.execute(text("SELECT COUNT(*) FROM games")).scalar()
                metrics_data["database"] = {"users": user_count, "games": game_count}
        except Exception:
            pass

        return JSONResponse(metrics_data)

    except ImportError:
        # psutil not available
        basic_metrics = {"timestamp": datetime.utcnow().isoformat(), "server": {"name": mcp.name, "version": "2.0.0", "pid": os.getpid()}, "note": "Install psutil for detailed system metrics"}
        return JSONResponse(basic_metrics)
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Import and register all MCP components
try:
    from .tools import register_tools

    # Register tools with the FastMCP server (tools are imported and registered via @mcp.tool() decorators)
    register_tools(mcp)

    # Import resources and prompts to register their decorators
    from . import prompts, resources  # noqa: F401

    logger.info("Steam Librarian MCP Server tools, resources, and prompts registered successfully")

except Exception as e:
    logger.error(f"Failed to register MCP components: {e}")
    raise
