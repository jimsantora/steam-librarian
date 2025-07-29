"""User context resolution for multi-user support"""

import logging
import os
import sys
from typing import Any

from sqlalchemy.orm import Session

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.shared.database import UserProfile, get_db

from .config import DEFAULT_STEAM_ID
from .errors import multiple_users_error, no_users_error, user_not_found_error

logger = logging.getLogger(__name__)


async def resolve_user_context(user_steam_id: str | None = None, session: Session | None = None) -> dict[str, Any]:
    """
    Resolve user context with intelligent fallbacks.

    Returns dict with either:
    - {"user": UserProfile, "source": str} on success
    - {"error": str, ...} on failure
    """

    # Use provided session or create new one
    if session is None:
        with get_db() as session:
            return await _resolve_user_internal(user_steam_id, session)
    else:
        return await _resolve_user_internal(user_steam_id, session)


async def _resolve_user_internal(user_steam_id: str | None, session: Session) -> dict[str, Any]:
    """Internal user resolution logic"""

    # Case 1: Specific user requested
    if user_steam_id:
        # Try exact Steam ID match
        user = session.query(UserProfile).filter_by(steam_id=user_steam_id).first()
        if user:
            logger.debug(f"Found user by Steam ID: {user_steam_id}")
            return {"user": user, "source": "provided"}

        # Try persona name match (case-insensitive)
        user = session.query(UserProfile).filter(UserProfile.persona_name.ilike(user_steam_id)).first()
        if user:
            logger.debug(f"Found user by persona name: {user_steam_id}")
            return {"user": user, "source": "provided_name"}

        # User not found
        logger.warning(f"User not found: {user_steam_id}")
        error = user_not_found_error(user_steam_id)
        return {"error": error.error_type.value, "message": error.message, "details": error.details}

    # Case 2: Try environment default
    if DEFAULT_STEAM_ID:
        user = session.query(UserProfile).filter_by(steam_id=DEFAULT_STEAM_ID).first()
        if user:
            logger.debug(f"Using default user: {DEFAULT_STEAM_ID}")
            return {"user": user, "source": "default"}
        else:
            logger.warning(f"Default user not found: {DEFAULT_STEAM_ID}")

    # Case 3: Auto-select single user
    users = session.query(UserProfile).all()
    user_count = len(users)

    if user_count == 1:
        logger.debug(f"Auto-selecting single user: {users[0].steam_id}")
        return {"user": users[0], "source": "auto_single"}
    elif user_count > 1:
        logger.info(f"Multiple users found ({user_count}), user selection required")
        error = multiple_users_error(users)
        return {"error": error.error_type.value, "message": error.message, "details": error.details}
    else:
        logger.warning("No users found in database")
        error = no_users_error()
        return {"error": error.error_type.value, "message": error.message, "details": error.details}


def get_user_display_name(user: UserProfile) -> str:
    """Get display-friendly name for user"""
    if user.persona_name:
        return f"{user.persona_name} ({user.steam_id})"
    return user.steam_id


def format_user_context_error(context: dict[str, Any]) -> str:
    """Format user context error for display"""
    if "error" not in context:
        return ""

    message = context.get("message", "Unknown error")
    details = context.get("details", {})

    if context["error"] == "MULTIPLE_USERS_FOUND" and "available_users" in details:
        users_list = "\n".join([f"  - {u['persona_name']} (Steam ID: {u['steam_id']})" for u in details["available_users"]])
        return f"{message}\n\nAvailable users:\n{users_list}"

    return message
