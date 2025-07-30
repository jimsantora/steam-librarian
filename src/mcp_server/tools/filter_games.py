"""Filter games tool with intelligent presets"""

import logging
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from mcp_server.cache import cache, user_cache_key
from mcp_server.server import mcp
from mcp_server.user_context import resolve_user_context
from mcp_server.validation import FilterGamesInput
from shared.database import Game, GameReview, UserGame, UserProfile, get_db

logger = logging.getLogger(__name__)


@mcp.tool()
async def filter_games(user_steam_id: str | None = None, playtime_min: float | None = None, playtime_max: float | None = None, review_summary: list[str] | None = None, maturity_rating: str | None = None, preset: str | None = None, categories: list[str] | None = None, sort_by: str | None = None) -> str:
    """Filter user's Steam library with intelligent presets and custom criteria.

    Args:
        user_steam_id: Steam ID of user (optional, will auto-resolve if not provided)
        playtime_min: Minimum playtime in hours
        playtime_max: Maximum playtime in hours
        review_summary: Filter by review summary (e.g., ['Very Positive', 'Positive'])
        maturity_rating: Filter by maturity rating
        preset: Intelligent preset filters - 'comfort_food' (highly rated, >5h), 'hidden_gems' (positive, <2h), 'quick_session' (<1h), 'deep_dive' (>20h)
        categories: Filter by Steam categories (e.g., ['Single-player', 'Co-op'])
        sort_by: Sort results by 'playtime' (desc), 'name' (asc), 'recent' activity, or 'rating'
    """

    # Validate input
    try:
        input_data = FilterGamesInput(user_steam_id=user_steam_id, playtime_min=playtime_min, playtime_max=playtime_max, review_summary=review_summary, maturity_rating=maturity_rating, preset=preset, categories=categories, sort_by=sort_by)
    except Exception as e:
        return f"Invalid input: {str(e)}"

    # Resolve user context
    user_context = await resolve_user_context(input_data.user_steam_id)
    if "error" in user_context:
        return f"User error: {user_context['message']}"

    user = user_context["user"]

    # Generate cache key
    filter_params = {"playtime_min": playtime_min, "playtime_max": playtime_max, "review_summary": review_summary, "maturity_rating": maturity_rating, "preset": preset, "categories": categories, "sort_by": sort_by}
    cache_key = user_cache_key("filter_games", user.steam_id) + f"_{hash(str(filter_params))}"

    async def compute_filtered_games():
        return await _filter_user_games(user, input_data)

    # Get filtered games with caching
    results = await cache.get_or_compute(cache_key, compute_filtered_games, ttl=1800)  # 30 min cache

    if not results:
        return "No games found matching your criteria. Try adjusting the filters."

    # Format response
    preset_desc = ""
    if input_data.preset:
        preset_descriptions = {"comfort_food": "games you know and love (highly rated with good playtime)", "hidden_gems": "games you might have overlooked (positive reviews, minimal playtime)", "quick_session": "games perfect for short play sessions (under 1 hour)", "deep_dive": "games for extended gaming sessions (20+ hours of content)"}
        preset_desc = f"\n\n**{input_data.preset.replace('_', ' ').title()} Preset**: {preset_descriptions[input_data.preset]}"

    games_text = _format_filtered_games(results, input_data.sort_by or "playtime")

    response_text = f"**Filtered Games for {user.persona_name}** ({len(results)} games){preset_desc}\n\n{games_text}"

    return response_text


async def _filter_user_games(user: UserProfile, filters: FilterGamesInput) -> list[dict[str, Any]]:
    """Filter user's games based on criteria"""

    with get_db() as session:
        # Base query with all related data
        query = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.categories), joinedload(UserGame.game).joinedload(Game.reviews)).filter(UserGame.steam_id == user.steam_id)

        conditions = []

        # Apply preset filters first
        if filters.preset:
            preset_conditions = _get_preset_conditions(filters.preset)
            conditions.extend(preset_conditions)

        # Apply custom filters
        if filters.playtime_min is not None:
            conditions.append(UserGame.playtime_forever >= filters.playtime_min * 60)

        if filters.playtime_max is not None:
            conditions.append(UserGame.playtime_forever <= filters.playtime_max * 60)

        if filters.review_summary:
            review_conditions = []
            for summary in filters.review_summary:
                review_conditions.append(Game.reviews.has(GameReview.review_summary == summary))
            conditions.append(or_(*review_conditions))

        if filters.maturity_rating:
            conditions.append(Game.maturity_rating == filters.maturity_rating)

        if filters.categories:
            for category in filters.categories:
                conditions.append(Game.categories.any(category_name=category))

        # Apply all conditions
        if conditions:
            query = query.join(Game).filter(and_(*conditions))
        else:
            query = query.join(Game)

        user_games = query.all()

        # Convert to result format
        results = []
        for ug in user_games:
            if ug.game:
                game_data = {"app_id": ug.game.app_id, "name": ug.game.name, "playtime_hours": round(ug.playtime_forever / 60, 1), "recent_playtime_hours": round(ug.playtime_2weeks / 60, 1), "genres": [g.genre_name for g in ug.game.genres] if ug.game.genres else [], "categories": [c.category_name for c in ug.game.categories] if ug.game.categories else [], "maturity_rating": ug.game.maturity_rating, "review_data": None}

                if ug.game.reviews:
                    game_data["review_data"] = {"summary": ug.game.reviews.review_summary, "score": ug.game.reviews.review_score, "positive_percentage": ug.game.reviews.positive_percentage}

                results.append(game_data)

        return results


def _get_preset_conditions(preset: str) -> list:
    """Get database conditions for preset filters"""

    if preset == "comfort_food":
        # Highly rated games with decent playtime (5+ hours)
        return [UserGame.playtime_forever >= 300, or_(Game.reviews.has(GameReview.review_summary.in_(["Very Positive", "Overwhelmingly Positive"])), Game.reviews.has(GameReview.positive_percentage >= 85))]  # 5+ hours

    elif preset == "hidden_gems":
        # Positive games with minimal playtime (under 2 hours)
        return [UserGame.playtime_forever < 120, UserGame.playtime_forever > 0, or_(Game.reviews.has(GameReview.review_summary.in_(["Positive", "Very Positive", "Mostly Positive"])), Game.reviews.has(GameReview.positive_percentage >= 70))]  # Under 2 hours  # But some playtime

    elif preset == "quick_session":
        # Games perfect for short sessions (under 1 hour total playtime)
        return [UserGame.playtime_forever < 60]  # Under 1 hour

    elif preset == "deep_dive":
        # Games with lots of content (20+ hours)
        return [UserGame.playtime_forever >= 1200]  # 20+ hours

    return []


def _format_filtered_games(games: list[dict[str, Any]], sort_by: str) -> str:
    """Format filtered games for display"""

    # Sort games
    if sort_by == "playtime":
        games.sort(key=lambda g: g["playtime_hours"], reverse=True)
    elif sort_by == "name":
        games.sort(key=lambda g: g["name"].lower())
    elif sort_by == "recent":
        games.sort(key=lambda g: g["recent_playtime_hours"], reverse=True)
    elif sort_by == "rating" and any(g["review_data"] for g in games):
        games.sort(key=lambda g: g["review_data"]["positive_percentage"] if g["review_data"] else 0, reverse=True)

    game_lines = []
    for game in games[:20]:  # Limit to top 20 results
        # Basic info
        line = f"**{game['name']}** ({game['playtime_hours']}h played"

        # Recent activity
        if game["recent_playtime_hours"] > 0:
            line += f", {game['recent_playtime_hours']}h recent"

        line += ")"

        # Add genres
        if game["genres"]:
            top_genres = game["genres"][:3]  # Show top 3 genres
            line += f"\n  Genres: {', '.join(top_genres)}"

        # Add review info
        if game["review_data"]:
            review = game["review_data"]
            line += f"\n  Reviews: {review['summary']} ({review['positive_percentage']}% positive)"

        # Add maturity rating if present
        if game["maturity_rating"]:
            line += f"\n  Rating: {game['maturity_rating']}"

        game_lines.append(line)

    result = "\n\n".join(game_lines)

    if len(games) > 20:
        result += f"\n\n... and {len(games) - 20} more games"

    return result
