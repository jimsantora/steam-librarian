#!/usr/bin/env python3
"""Simplified startup script for Steam Librarian MCP Server"""

import logging
import signal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Import all modules to register decorators
from mcp_server import __version__
from mcp_server.config import config
from mcp_server.server import mcp


def setup_signal_handlers():
    """Setup graceful shutdown handlers"""

    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main server startup function"""
    logger = logging.getLogger(__name__)

    try:
        # Setup signal handlers
        setup_signal_handlers()

        # Print startup information
        logger.info("Steam Librarian MCP Server (Simplified) Starting...")
        logger.info(f"Version: {__version__}")
        logger.info(f"Host: {config.host}:{config.port}")
        logger.info(f"Debug Mode: {config.debug}")
        logger.info(f"Default User: {config.default_user}")
        logger.info(f"Database: {config.database_url}")

        # Start the server
        logger.info("Starting FastMCP HTTP server...")
        logger.info(f"Health check: http://{config.host}:{config.port}/health")
        logger.info(f"Detailed health: http://{config.host}:{config.port}/health/detailed")
        logger.info(f"MCP endpoint: http://{config.host}:{config.port}/mcp")

        # Run the FastMCP server synchronously
        mcp.run(transport="streamable-http")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
