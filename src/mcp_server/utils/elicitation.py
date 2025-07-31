"""Elicitation utilities for Steam Librarian MCP server"""

import logging

from aiohttp import ClientSession
from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field

from mcp_server.services.username_resolver import UsernameResolver

logger = logging.getLogger(__name__)


class SteamAccountInput(BaseModel):
    """Schema for collecting Steam account information"""

    steam_identifier: str = Field(description="Steam ID (17 digits) or Steam username/vanity URL", examples=["WeAreARobot", "76561198020403796"])


class SearchRefinementInput(BaseModel):
    """Schema for refining ambiguous search queries"""

    mood: str | None = Field(default=None, description="What mood are you in? (relaxed, excited, creative, intense, etc.)")
    time_available: str | None = Field(default=None, description="How much time do you have to play? (30 minutes, a few hours, etc.)")
    player_preference: str | None = Field(default=None, description="Playing alone or with others? (solo, local_coop, online_multiplayer, any)")
    genres: str | None = Field(default=None, description="Any specific genres you're interested in? (action, puzzle, rpg, etc.)")


async def elicit_steam_account(ctx: Context, reason: str = "to access your Steam library") -> str | None:
    """
    Use elicitation to request Steam account information from user.

    Args:
        ctx: FastMCP context for elicitation
        reason: Why we need the Steam account (for user messaging)

    Returns:
        Steam ID as string if successfully obtained and resolved, None otherwise
    """

    try:
        result = await ctx.elicit(message=f"I need your Steam account information {reason}. Please provide your Steam ID or username.", schema=SteamAccountInput)

        if result.action == "accept" and result.data:
            identifier = result.data.steam_identifier.strip()

            # Check if it's already a Steam ID
            if identifier.isdigit() and len(identifier) == 17:
                logger.info(f"User provided Steam ID: {identifier}")
                return identifier

            # Try to resolve username to Steam ID
            logger.info(f"Attempting to resolve username: {identifier}")
            async with ClientSession() as session:
                resolver = UsernameResolver(session)
                steam_id = await resolver.resolve_username(identifier)

                if steam_id:
                    logger.info(f"Successfully resolved '{identifier}' to Steam ID: {steam_id}")
                    return steam_id
                else:
                    logger.warning(f"Could not resolve username: {identifier}")
                    # Could potentially elicit again for a different identifier
                    return None
        else:
            logger.info("User cancelled Steam account elicitation")
            return None

    except Exception as e:
        logger.error(f"Error during Steam account elicitation: {e}")
        return None


async def elicit_search_refinement(ctx: Context, original_query: str) -> dict | None:
    """
    Use elicitation to refine an ambiguous search query.

    Args:
        ctx: FastMCP context for elicitation
        original_query: The original search query that needs refinement

    Returns:
        Dictionary with refined search parameters, None if cancelled
    """

    try:
        result = await ctx.elicit(message=f"Your search '{original_query}' could mean several things. Help me understand what you're looking for:", schema=SearchRefinementInput)

        if result.action == "accept" and result.data:
            refinement = {}

            if result.data.mood:
                refinement["mood"] = result.data.mood.strip()

            if result.data.time_available:
                refinement["time_available"] = result.data.time_available.strip()

            if result.data.player_preference:
                refinement["player_preference"] = result.data.player_preference.strip()

            if result.data.genres:
                # Split genres by comma and clean up
                genres = [g.strip().title() for g in result.data.genres.split(",") if g.strip()]
                if genres:
                    refinement["genres"] = genres

            logger.info(f"User provided search refinement: {refinement}")
            return refinement if refinement else None
        else:
            logger.info("User cancelled search refinement elicitation")
            return None

    except Exception as e:
        logger.error(f"Error during search refinement elicitation: {e}")
        return None


def should_elicit_for_query(query: str) -> bool:
    """
    Determine if a search query is ambiguous enough to warrant elicitation.

    Args:
        query: The search query to analyze

    Returns:
        True if the query should trigger elicitation, False otherwise
    """

    query_lower = query.lower()

    # Very short or vague queries
    if len(query.strip()) <= 5:
        return True

    # Common vague terms that could benefit from clarification
    vague_terms = ["games", "something", "anything", "fun", "good", "best", "new", "old", "play", "gaming", "steam", "library", "random", "surprise"]

    # If query is just vague terms, elicit
    words = query_lower.split()
    if all(word in vague_terms for word in words):
        return True

    # If query has no specific genre, mood, or game references
    specific_terms = [
        # Genres
        "action",
        "adventure",
        "rpg",
        "strategy",
        "puzzle",
        "racing",
        "sports",
        "shooter",
        "fighting",
        "horror",
        "indie",
        "casual",
        "simulation",
        # Moods
        "relaxing",
        "chill",
        "intense",
        "exciting",
        "creative",
        "social",
        # Game references
        "like",
        "similar",
        "portal",
        "minecraft",
        "hades",
        "witcher",
    ]

    has_specific_terms = any(term in query_lower for term in specific_terms)

    # If no specific terms and query is short, consider elicitation
    if not has_specific_terms and len(words) <= 3:
        return True

    return False
