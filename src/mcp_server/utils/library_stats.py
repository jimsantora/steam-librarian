"""Library statistics calculation utilities"""

import logging
import os
import sys
from datetime import datetime
from typing import Any

from sqlalchemy.orm import joinedload

from shared.database import Game, UserGame, UserProfile, get_db

logger = logging.getLogger(__name__)


def calculate_library_overview(user: UserProfile) -> dict[str, Any]:
    """Calculate comprehensive library statistics for a user"""

    with get_db() as session:
        # Get all user games with related data
        user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.reviews)).filter(UserGame.steam_id == user.steam_id).all()

        if not user_games:
            return {"total_games": 0, "total_playtime_hours": 0, "genres": {}, "recent_activity": {"last_7_days": 0, "last_30_days": 0}, "unplayed_games": 0, "completion_rate": 0}

        # Calculate basic stats
        total_games = len(user_games)
        total_playtime = sum(ug.playtime_forever for ug in user_games)
        total_playtime_hours = round(total_playtime / 60, 1)

        # Calculate unplayed games
        unplayed_games = sum(1 for ug in user_games if ug.playtime_forever == 0)
        played_games = total_games - unplayed_games
        completion_rate = round(played_games / total_games, 2) if total_games > 0 else 0

        # Calculate genre distribution
        genre_playtime = {}
        genre_count = {}

        for ug in user_games:
            if ug.game and ug.game.genres:
                for genre in ug.game.genres:
                    genre_name = genre.genre_name
                    if genre_name not in genre_playtime:
                        genre_playtime[genre_name] = 0
                        genre_count[genre_name] = 0
                    genre_playtime[genre_name] += ug.playtime_forever
                    genre_count[genre_name] += 1

        # Sort genres by playtime
        top_genres = dict(sorted(genre_playtime.items(), key=lambda x: x[1], reverse=True)[:10])

        # Convert genre playtime to hours
        genres = {genre: {"count": genre_count[genre], "playtime_hours": round(playtime / 60, 1)} for genre, playtime in top_genres.items()}

        # Calculate recent activity
        recent_playtime = sum(ug.playtime_2weeks for ug in user_games)
        recent_hours = round(recent_playtime / 60, 1)

        # Find most played games
        most_played = sorted([ug for ug in user_games if ug.playtime_forever > 0], key=lambda x: x.playtime_forever, reverse=True)[:5]

        most_played_games = [{"app_id": ug.game.app_id, "name": ug.game.name, "playtime_hours": round(ug.playtime_forever / 60, 1)} for ug in most_played]

        # Calculate value metrics
        avg_playtime_per_game = round(total_playtime_hours / played_games, 1) if played_games > 0 else 0

        # Build overview
        overview = {"total_games": total_games, "total_playtime_hours": total_playtime_hours, "played_games": played_games, "unplayed_games": unplayed_games, "completion_rate": completion_rate, "genres": genres, "recent_activity": {"last_2_weeks": recent_hours, "active_games": sum(1 for ug in user_games if ug.playtime_2weeks > 0)}, "most_played_games": most_played_games, "average_playtime_per_game": avg_playtime_per_game, "last_updated": datetime.now().isoformat()}

        return overview
