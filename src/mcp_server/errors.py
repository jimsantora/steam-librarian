"""Error handling and validation framework for Steam Librarian MCP Server"""

import logging
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any

from mcp.types import TextContent

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Standardized error types for consistent handling"""

    USER_NOT_FOUND = "USER_NOT_FOUND"
    GAME_NOT_FOUND = "GAME_NOT_FOUND"
    DATABASE_ERROR = "DATABASE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    MULTIPLE_USERS_FOUND = "MULTIPLE_USERS_FOUND"
    NO_USERS_FOUND = "NO_USERS_FOUND"


class MCPError(Exception):
    """Base exception for MCP server errors"""

    def __init__(self, error_type: ErrorType, message: str, details: dict[str, Any] | None = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


def create_error_response(error_type: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create standardized error response"""
    response = {"error": True, "error_type": error_type, "message": message, "timestamp": datetime.now().isoformat()}
    if details:
        response["details"] = details
    return response


def create_error_content(error_type: str, message: str, details: dict[str, Any] | None = None) -> list[TextContent]:
    """Create error response as TextContent for MCP tools"""
    error_response = create_error_response(error_type, message, details)
    return [TextContent(type="text", text=f"Error: {message}\n\nDetails: {error_response}")]


def handle_mcp_errors(func):
    """Decorator for consistent error handling across all MCP handlers"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MCPError as e:
            logger.error(f"MCP error in {func.__name__}: {e.error_type.value} - {e.message}")
            return create_error_content(e.error_type.value, e.message, e.details)
        except ValueError as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            return create_error_content(ErrorType.VALIDATION_ERROR.value, str(e))
        except TimeoutError as e:
            logger.error(f"Timeout in {func.__name__}: {e}")
            return create_error_content(ErrorType.TIMEOUT_ERROR.value, "Operation timed out")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return create_error_content(ErrorType.DATABASE_ERROR.value, "An unexpected error occurred", {"error": str(e)})

    return wrapper


# Specific error helpers
def user_not_found_error(user_identifier: str) -> MCPError:
    """Create user not found error"""
    return MCPError(ErrorType.USER_NOT_FOUND, f"User not found: {user_identifier}", {"user_identifier": user_identifier, "suggestion": "Use get_all_users() to see available users"})


def game_not_found_error(game_identifier: str) -> MCPError:
    """Create game not found error"""
    return MCPError(ErrorType.GAME_NOT_FOUND, f"Game not found: {game_identifier}", {"game_identifier": game_identifier})


def multiple_users_error(users: list) -> MCPError:
    """Create multiple users found error"""
    return MCPError(ErrorType.MULTIPLE_USERS_FOUND, "Multiple users found. Please specify which user by Steam ID", {"available_users": [{"steam_id": user.steam_id, "persona_name": user.persona_name} for user in users]})


def no_users_error() -> MCPError:
    """Create no users found error"""
    return MCPError(ErrorType.NO_USERS_FOUND, "No users found in database. Please fetch Steam library data first.", {})
