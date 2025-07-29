#!/usr/bin/env python3
"""Entry point for Steam Librarian MCP Server"""

import os
import sys

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from mcp_server.server import main

if __name__ == "__main__":
    asyncio.run(main())
