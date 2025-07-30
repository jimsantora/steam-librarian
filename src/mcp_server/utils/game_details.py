"""Game details retrieval utilities"""

import logging
from typing import Any

from sqlalchemy.orm import joinedload

from shared.database import Game, UserGame, UserProfile, get_db

logger = logging.getLogger(__name__)


def get_game_details_with_context(app_id: str, user: UserProfile | None = None) -> dict[str, Any]:
    """Get comprehensive game details with optional user context"""

    with get_db() as session:
        # Get game with all related data
        game = session.query(Game).options(joinedload(Game.genres), joinedload(Game.developers), joinedload(Game.publishers), joinedload(Game.categories), joinedload(Game.reviews)).filter_by(app_id=int(app_id)).first()

        if not game:
            return {"error": "Game not found", "app_id": app_id}

        # Build basic game details
        details = {"app_id": game.app_id, "name": game.name, "metadata": {"maturity_rating": game.maturity_rating, "required_age": game.required_age, "content_descriptors": game.content_descriptors, "release_date": game.release_date, "metacritic_score": game.metacritic_score}, "genres": [g.genre_name for g in game.genres], "developers": [d.developer_name for d in game.developers], "publishers": [p.publisher_name for p in game.publishers], "categories": [c.category_name for c in game.categories], "features": {"steam_deck_verified": game.steam_deck_verified, "controller_support": game.controller_support, "vr_support": game.vr_support}}

        # Add review data if available
        if game.reviews:
            details["reviews"] = {"summary": game.reviews.review_summary, "score": game.reviews.review_score, "total": game.reviews.total_reviews, "positive": game.reviews.positive_reviews, "negative": game.reviews.negative_reviews, "positive_percentage": game.reviews.positive_percentage}

        # Add user-specific data if user provided
        if user:
            user_game = session.query(UserGame).filter_by(steam_id=user.steam_id, app_id=game.app_id).first()

            if user_game:
                details["your_history"] = {"owned": True, "playtime_hours": round(user_game.playtime_forever / 60, 1), "recent_playtime_hours": round(user_game.playtime_2weeks / 60, 1), "last_played": "Recently" if user_game.playtime_2weeks > 0 else "Not recently"}
            else:
                details["your_history"] = {"owned": False, "playtime_hours": 0, "recent_playtime_hours": 0, "last_played": "Never"}

        # Add multiplayer info for categories
        multiplayer_categories = ["Multi-player", "Co-op", "Online Co-op", "Local Co-op"]
        is_multiplayer = any(cat.category_name in multiplayer_categories for cat in game.categories)

        details["multiplayer_info"] = {"is_multiplayer": is_multiplayer, "types": [cat.category_name for cat in game.categories if cat.category_name in multiplayer_categories]}

        return details
