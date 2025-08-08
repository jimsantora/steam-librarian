#!/usr/bin/env python3
"""
Production startup script for the tools-only Steam Librarian MCP server.

This script provides:
- Signal handling for graceful shutdown
- Logging configuration
- Error handling and recovery
- Environment validation
"""

import asyncio
import logging
import os
import signal
import sys

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from . import SERVER_NAME
from .config import config
from .server import mcp

# Configure logging
logging.basicConfig(level=logging.DEBUG if config.debug else logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("steam_librarian_tools.log") if not config.debug else logging.NullHandler()])

logger = logging.getLogger(SERVER_NAME)


class GracefulShutdown:
    """Handle graceful shutdown on SIGTERM and SIGINT."""

    def __init__(self):
        self.shutdown = False
        self.server_task: asyncio.Task | None = None

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        self.shutdown = True

        if self.server_task and not self.server_task.done():
            self.server_task.cancel()

    def setup_signals(self):
        """Set up signal handlers."""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)


def validate_environment():
    """Validate that the environment is properly configured."""
    issues = []

    # Check database configuration
    if not config.database_url:
        issues.append("DATABASE_URL not configured")

    # Check if database file exists (for SQLite)
    if config.database_url.startswith("sqlite"):
        db_path = config.database_url.replace("sqlite:///", "").replace("sqlite://", "")
        if not os.path.exists(db_path):
            issues.append(f"Database file not found: {db_path}")
            logger.warning(f"Database file not found: {db_path}")
            logger.warning("Run 'python src/fetcher/steam_library_fetcher.py' to create the database")

    # Check port availability
    try:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((config.host, config.port))
    except OSError as e:
        issues.append(f"Port {config.port} is not available: {e}")

    # Report issues
    if issues:
        logger.error("Environment validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")

        # Continue anyway for development, but warn
        if not config.debug:
            logger.error("Use DEBUG=true to continue with environment issues")
            return False
        else:
            logger.warning("Continuing in debug mode despite environment issues")

    return True


async def run_server():
    """Run the MCP server with proper error handling."""
    logger.info(f"Starting {SERVER_NAME} on {config.host}:{config.port}")
    logger.info(f"Debug mode: {config.debug}")
    logger.info(f"Database: {config.database_url}")
    logger.info(f"Default user: {config.default_user or 'None (will prompt)'}")

    try:
        # Import tools to register them with the server
        from . import tools  # This registers all the @mcp.tool() decorated functions

        logger.info("Tools loaded successfully")
        logger.info(f"Server capabilities: {len([name for name in dir(tools) if not name.startswith('_')])} tools available")

        # Run the FastMCP server
        await mcp.run(transport="sse", host=config.host, port=config.port, raise_exceptions=config.debug)  # Server-Sent Events transport

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        if config.debug:
            raise
        return 1

    return 0


async def main():
    """Main entry point with signal handling and error recovery."""
    shutdown_handler = GracefulShutdown()
    shutdown_handler.setup_signals()

    # Validate environment
    if not validate_environment():
        return 1

    # Run server with graceful shutdown handling
    try:
        shutdown_handler.server_task = asyncio.create_task(run_server())
        return await shutdown_handler.server_task

    except asyncio.CancelledError:
        logger.info("Server shutdown completed")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if config.debug:
            raise
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Server stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
