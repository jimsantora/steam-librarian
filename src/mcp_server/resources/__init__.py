"""Resources registration for Steam Librarian MCP Server"""

from mcp.server import Server

from .insight_resources import register_insight_resources
from .library_resources import register_library_resources
from .social_resources import register_social_resources


def register_resources(server: Server):
    """Register all resources with the MCP server"""
    register_library_resources(server)
    register_social_resources(server)
    register_insight_resources(server)
