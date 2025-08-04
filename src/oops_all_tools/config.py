"""Configuration for the tools-only MCP server."""

import os


class Config:
    """Simple configuration class for the tools-only server."""

    def __init__(self):
        # Server settings
        self.host: str = os.getenv("MCP_HOST", "127.0.0.1")
        self.port: int = int(os.getenv("MCP_PORT", "8001"))  # Different from main server
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"

        # Database settings (shared with main server)
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///steam_library.db")

        # Default user for personal library mode
        self.default_user: str | None = os.getenv("DEFAULT_USER", "default")
        if self.default_user == "default":
            self.default_user = None

        # Tool behavior settings
        self.default_limit: int = int(os.getenv("DEFAULT_LIMIT", "10"))
        self.search_limit: int = int(os.getenv("SEARCH_LIMIT", "25"))

        # Error message verbosity
        self.verbose_errors: bool = os.getenv("VERBOSE_ERRORS", "true").lower() == "true"


# Global config instance
config = Config()


def get_default_user_fallback() -> str | None:
    """Fallback function to get default user from config."""
    if config.default_user and config.default_user != "default":
        return config.default_user
    return None
