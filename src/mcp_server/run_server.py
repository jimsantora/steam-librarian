#!/usr/bin/env python3
"""Startup script for Steam Librarian MCP Server"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from sqlalchemy import text

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.config import config_manager, settings
from mcp_server.server import mcp


def setup_signal_handlers():
    """Setup graceful shutdown handlers"""

    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def validate_environment():
    """Validate environment and configuration before starting"""
    logger = logging.getLogger(__name__)

    # Validate configuration
    validation = config_manager.validate_configuration()

    if not validation["valid"]:
        logger.error("Configuration validation failed:")
        for error in validation["errors"]:
            logger.error(f"  ERROR: {error}")
        sys.exit(1)

    if validation["warnings"]:
        logger.warning("Configuration warnings:")
        for warning in validation["warnings"]:
            logger.warning(f"  WARNING: {warning}")

    # Check database accessibility
    try:
        from shared.database import get_db

        with get_db() as session:
            session.execute(text("SELECT 1")).fetchone()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.info("Make sure to run steam_library_fetcher.py first to create the database")
        sys.exit(1)

    # Print startup information
    server_info = config_manager.get_server_info()
    feature_flags = config_manager.get_feature_flags()

    logger.info("Steam Librarian MCP Server Starting...")
    logger.info(f"Version: {server_info['version']}")
    logger.info(f"Host: {server_info['host']}:{server_info['port']}")
    logger.info(f"Debug Mode: {server_info['debug']}")
    logger.info(f"Log Level: {server_info['log_level']}")
    logger.info("Enabled Features:")
    for feature, enabled in feature_flags.items():
        status = "✓" if enabled else "✗"
        logger.info(f"  {status} {feature}")


async def main():
    """Main server startup function"""
    logger = logging.getLogger(__name__)

    try:
        # Setup signal handlers
        setup_signal_handlers()

        # Validate environment
        validate_environment()

        # Start the server
        logger.info("Starting FastMCP HTTP server...")
        logger.info(f"Health check available at: http://{settings.host}:{settings.port}/health")
        logger.info(f"Detailed health check at: http://{settings.host}:{settings.port}/health/detailed")
        logger.info(f"Configuration endpoint at: http://{settings.host}:{settings.port}/config")
        logger.info(f"Metrics endpoint at: http://{settings.host}:{settings.port}/metrics")
        logger.info(f"MCP endpoint at: http://{settings.host}:{settings.port}/mcp")

        # Run the FastMCP server
        await mcp.run_streamable_http_async()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
