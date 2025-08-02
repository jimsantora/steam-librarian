"""Steam Librarian MCP Server - Simplified HTTP Streaming Implementation"""

import logging
from mcp.server.fastmcp import FastMCP
from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)
from sqlalchemy import create_engine, text
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from .config import config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if config.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create the FastMCP server instance for HTTP streaming
mcp = FastMCP("steam-librarian", host=config.host, port=config.port)

# Simple database connection for health checks
engine = create_engine(config.database_url)


# Health check endpoints
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    """Basic health check endpoint for liveness/readiness probes"""
    try:
        # Test basic database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).fetchone()
        
        return PlainTextResponse("OK")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return PlainTextResponse(f"UNHEALTHY: {str(e)}", status_code=503)


@mcp.custom_route("/health/detailed", methods=["GET"])
async def health_detailed(request: Request) -> JSONResponse:
    """Detailed health check with server information"""
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).fetchone()
        
        health_info = {
            "status": "healthy",
            "server": "steam-librarian-simplified",
            "default_user": config.default_user,
            "debug": config.debug,
            "version": "1.1.2",
            "database": "connected"
        }
        
        return JSONResponse(health_info)
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        error_info = {
            "status": "unhealthy",
            "error": str(e),
            "server": "steam-librarian-simplified"
        }
        return JSONResponse(error_info, status_code=503)


# Basic completion handler
@mcp.completion()
async def handle_completion(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None = None,
) -> Completion | None:
    """Provide basic completions for Steam Librarian."""
    
    # Simple hardcoded completions
    if argument.name in ["query", "search", "game", "games"]:
        games = ["Portal", "Half-Life", "Team Fortress", "Counter-Strike", "Dota 2"]
        matching = [g for g in games if g.lower().startswith(argument.value.lower())]
        return Completion(values=matching, hasMore=False)
    
    elif argument.name in ["genre", "genres"]:
        genres = ["Action", "Adventure", "RPG", "Strategy", "Simulation", "Sports"]
        matching = [g for g in genres if g.lower().startswith(argument.value.lower())]
        return Completion(values=matching, hasMore=False)
    
    elif argument.name in ["user", "username"]:
        # Use default user as completion
        if config.default_user.startswith(argument.value):
            return Completion(values=[config.default_user], hasMore=False)
    
    return None