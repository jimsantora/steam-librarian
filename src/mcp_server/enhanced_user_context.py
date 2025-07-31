"""Enhanced user context resolution with elicitation support"""

import logging
from typing import Any

from mcp.server.fastmcp import Context
from sqlalchemy.orm import Session

from shared.database import UserProfile, get_db

from .user_context import _resolve_user_internal
from .utils.elicitation import elicit_steam_account

logger = logging.getLogger(__name__)


async def resolve_user_context_with_elicitation(user_steam_id: str | None = None, ctx: Context | None = None, session: Session | None = None, allow_elicitation: bool = True) -> dict[str, Any]:
    """
    Enhanced user context resolution with elicitation support.

    Args:
        user_steam_id: Optional Steam ID to resolve
        ctx: FastMCP context for elicitation (required if allow_elicitation=True)
        session: Optional database session
        allow_elicitation: Whether to use elicitation for missing Steam IDs

    Returns:
        dict with either:
        - {"user": UserProfile, "source": str} on success
        - {"error": str, ...} on failure
    """

    # Use provided session or create new one
    if session is None:
        with get_db() as session:
            return await _resolve_user_with_elicitation_internal(user_steam_id, ctx, session, allow_elicitation)
    else:
        return await _resolve_user_with_elicitation_internal(user_steam_id, ctx, session, allow_elicitation)


async def _resolve_user_with_elicitation_internal(user_steam_id: str | None, ctx: Context | None, session: Session, allow_elicitation: bool) -> dict[str, Any]:
    """Internal enhanced user resolution logic"""

    # First, try the standard resolution
    result = await _resolve_user_internal(user_steam_id, session)

    # If successful, return immediately
    if "user" in result:
        return result

    # If we have a context and elicitation is allowed, try to elicit Steam ID
    if allow_elicitation and ctx is not None and result.get("error") in ["NO_USERS_FOUND", "USER_NOT_FOUND"]:
        logger.info("Attempting to elicit Steam account information from user")

        # Determine the reason message based on the error
        if result.get("error") == "NO_USERS_FOUND":
            reason = "to get started with Steam Librarian"
        else:
            reason = f"because '{user_steam_id}' was not found in your library"

        # Elicit Steam account information
        elicited_steam_id = await elicit_steam_account(ctx, reason)

        if elicited_steam_id:
            logger.info(f"Successfully elicited Steam ID: {elicited_steam_id}")

            # Try to resolve the elicited Steam ID
            # First check if user already exists in database
            existing_user = session.query(UserProfile).filter_by(steam_id=elicited_steam_id).first()
            if existing_user:
                logger.info(f"Found existing user for elicited Steam ID: {elicited_steam_id}")
                return {"user": existing_user, "source": "elicited_existing"}

            # User doesn't exist in database - they'll need to fetch their library first
            logger.info(f"Steam ID {elicited_steam_id} not found in database - library needs to be fetched")

            # Create a helpful error message
            error_msg = f"Steam account {elicited_steam_id} was found, but your library data isn't available yet. " "Please run the library fetcher first to import your Steam games."

            return {"error": "LIBRARY_NOT_FETCHED", "message": error_msg, "details": {"steam_id": elicited_steam_id, "suggestion": "Run: python src/fetcher/steam_library_fetcher.py"}}
        else:
            logger.info("User cancelled or failed Steam account elicitation")
            # Return the original error since elicitation didn't help
            return result

    # If no elicitation possible or not allowed, handle multiple users case
    if result.get("error") == "MULTIPLE_USERS_FOUND" and allow_elicitation and ctx is not None:
        # For multiple users, we could potentially elicit which user to select
        # For now, just return the original error with user selection info
        return result

    # Return the original error
    return result


async def get_user_with_elicitation(user_steam_id: str | None = None, ctx: Context | None = None, allow_elicitation: bool = True) -> tuple[UserProfile | None, str | None]:
    """
    Convenience function to get a user with elicitation support.

    Args:
        user_steam_id: Optional Steam ID to resolve
        ctx: FastMCP context for elicitation
        allow_elicitation: Whether to use elicitation

    Returns:
        Tuple of (UserProfile, error_message)
        - If successful: (user, None)
        - If failed: (None, error_message)
    """

    result = await resolve_user_context_with_elicitation(user_steam_id=user_steam_id, ctx=ctx, allow_elicitation=allow_elicitation)

    if "user" in result:
        return result["user"], None
    else:
        error_msg = result.get("message", "Unknown error occurred")
        return None, error_msg


def format_elicitation_error(context: dict[str, Any]) -> str:
    """Format enhanced user context errors for display"""

    if "error" not in context:
        return ""

    error_type = context["error"]
    message = context.get("message", "Unknown error")
    details = context.get("details", {})

    if error_type == "LIBRARY_NOT_FETCHED":
        suggestion = details.get("suggestion", "")
        if suggestion:
            return f"{message}\n\nTo fix this:\n  {suggestion}"
        return message

    elif error_type == "MULTIPLE_USERS_FOUND" and "available_users" in details:
        users_list = "\n".join([f"  - {u['persona_name']} (Steam ID: {u['steam_id']})" for u in details["available_users"]])
        return f"{message}\n\nAvailable users:\n{users_list}\n\nSpecify a Steam ID or username to select a user."

    elif error_type == "NO_USERS_FOUND":
        return f"{message}\n\nTo get started, please run the library fetcher to import your Steam games."

    return message
