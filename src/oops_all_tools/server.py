"""FastMCP server instance for the tools-only Steam Librarian."""

import logging

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, text
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from oops_all_tools import SERVER_NAME
from oops_all_tools.config import config

# Configure logging
logging.basicConfig(level=logging.DEBUG if config.debug else logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastMCP instance
mcp = FastMCP(SERVER_NAME, host=config.host, port=config.port)

# Simple database connection for health checks
try:
    engine = create_engine(config.database_url)
except Exception as e:
    logger.warning(f"Database connection not available: {e}")
    engine = None


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> PlainTextResponse:
    """Basic health check endpoint."""
    try:
        if engine:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1")).fetchone()
        return PlainTextResponse("OK")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return PlainTextResponse(f"UNHEALTHY: {str(e)}", status_code=503)


@mcp.custom_route("/info", methods=["GET"])
async def info(request: Request) -> JSONResponse:
    """Server information endpoint."""
    return JSONResponse({"name": SERVER_NAME, "version": "1.0.0", "description": "Tools-only MCP server for Steam library management", "type": "tools-only", "port": config.port, "features": {"tools": True, "resources": False, "prompts": True, "completions": False, "elicitations": False, "sampling": False}, "capabilities": ["search_games", "get_game_details", "find_similar_games", "get_library_overview", "get_user_profile", "get_user_games", "get_user_stats", "get_genres", "get_games_by_genre", "get_categories", "get_games_by_category", "recommend_games", "find_family_games", "find_quick_games", "get_unplayed_games", "analyze_gaming_patterns", "get_platform_games", "get_multiplayer_games", "get_vr_games"], "database_shared": True, "companion_server": {"full_server_port": 8000, "features": "resources, completions, elicitations, sampling"}})  # Simple text examples
