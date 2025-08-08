"""
Steam Librarian - Tools-Only MCP Server

A simplified MCP server implementation that provides Steam library functionality
using only tools (no resources, completions, elicitations, or sampling).
This version is designed for maximum compatibility with LLM clients that have
limited MCP feature support.

Server runs on port 8001 (vs 8000 for the full-featured server).
"""

__version__ = "1.6.2"
__author__ = "Steam Librarian Team"
__description__ = "Tools-only MCP server for Steam library management"

# Server configuration
SERVER_NAME = "steam-librarian-tools"
DEFAULT_PORT = 8001
DEFAULT_HOST = "127.0.0.1"
