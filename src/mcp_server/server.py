#!/usr/bin/env python3
"""Steam Librarian MCP Server - HTTP Streaming Implementation"""

import logging

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from .config import config_manager, settings

# Configure logging
logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create the FastMCP server instance for HTTP streaming
mcp = FastMCP("steam-librarian", host=settings.host, port=settings.port)


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


# Import and register tools (resources and prompts registration postponed for FastMCP compatibility)
try:
    from .tools import register_tools

    # Register tools with the FastMCP server (tools are imported and registered via @mcp.tool() decorators)
    register_tools(mcp)

    logger.info("Steam Librarian MCP Server tools registered successfully")

except Exception as e:
    logger.error(f"Failed to register MCP components: {e}")
    raise
