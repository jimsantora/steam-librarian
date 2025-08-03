"""Simple configuration management for Steam Librarian MCP Server"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Simple configuration with environment variable support"""

    # Server settings
    host: str = os.getenv("MCP_HOST", "127.0.0.1")
    port: int = int(os.getenv("MCP_PORT", "8000"))

    # Default user for single-user mode
    default_user: str = os.getenv("DEFAULT_USER", "default")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///steam_library.db")

    # Debug mode
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


# Global configuration instance
config = Config()
