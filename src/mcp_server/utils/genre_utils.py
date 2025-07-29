"""Genre-related utilities"""

import logging
from typing import Any

from sqlalchemy.orm import joinedload

from shared.database import Game, Genre, UserGame, UserProfile, get_db

logger = logging.getLogger(__name__)


def get_games_by_genre(user: UserProfile, genre_name: str) -> list[dict[str, Any]]:
    """Get all games in user's library for a specific genre"""

    with get_db() as session:
        # Get games matching the genre
        user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.reviews)).join(UserGame.game).join(Game.genres).filter(UserGame.steam_id == user.steam_id, Genre.genre_name.ilike(f"%{genre_name}%")).all()

        # Format results
        games = []
        for ug in user_games:
            if ug.game:
                game_data = {"app_id": ug.game.app_id, "name": ug.game.name, "playtime_hours": round(ug.playtime_forever / 60, 1), "recent_playtime_hours": round(ug.playtime_2weeks / 60, 1), "genres": [g.genre_name for g in ug.game.genres], "is_unplayed": ug.playtime_forever == 0}

                # Add review data if available
                if ug.game.reviews:
                    game_data["review_summary"] = ug.game.reviews.review_summary
                    game_data["positive_percentage"] = ug.game.reviews.positive_percentage

                games.append(game_data)

        # Sort by playtime (most played first)
        games.sort(key=lambda x: x["playtime_hours"], reverse=True)

        return games
