"""Utility functions for MCP tools"""
import os
from src.core.database import get_db
from src.models import UserProfile

# Get Steam ID from environment (fallback for backwards compatibility)
STEAM_ID = os.environ.get('STEAM_ID', '')


def get_user_steam_id() -> str:
    """Get the Steam ID for the current user (backwards compatibility)"""
    # Try to get from environment first
    if STEAM_ID:
        return STEAM_ID
    
    # Otherwise get from database (first user)
    with get_db() as session:
        user = session.query(UserProfile).first()
        if user:
            return user.steam_id
    
    return ''