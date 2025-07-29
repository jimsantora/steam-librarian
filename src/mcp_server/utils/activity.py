"""Recent activity tracking utilities"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import joinedload

from ...shared.database import Game, UserGame, UserProfile, get_db

logger = logging.getLogger(__name__)


def get_recent_activity(user: UserProfile) -> dict[str, Any]:
    """Get recent gaming activity for a user"""

    with get_db() as session:
        # Get games with recent playtime
        recent_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.categories)).filter(UserGame.steam_id == user.steam_id, UserGame.playtime_2weeks > 0).order_by(UserGame.playtime_2weeks.desc()).all()

        # Format recent games
        recent_activity = []
        total_recent_playtime = 0

        for ug in recent_games:
            if ug.game:
                activity = {"app_id": ug.game.app_id, "name": ug.game.name, "recent_playtime_hours": round(ug.playtime_2weeks / 60, 1), "total_playtime_hours": round(ug.playtime_forever / 60, 1), "genres": [g.genre_name for g in ug.game.genres]}
                recent_activity.append(activity)
                total_recent_playtime += ug.playtime_2weeks

        # Get all-time most played for comparison
        most_played_alltime = session.query(UserGame).options(joinedload(UserGame.game)).filter(UserGame.steam_id == user.steam_id, UserGame.playtime_forever > 0).order_by(UserGame.playtime_forever.desc()).limit(10).all()

        most_played = [{"app_id": ug.game.app_id, "name": ug.game.name, "playtime_hours": round(ug.playtime_forever / 60, 1), "is_recent": ug.playtime_2weeks > 0} for ug in most_played_alltime if ug.game]

        # Calculate activity summary
        summary = {"total_recent_hours": round(total_recent_playtime / 60, 1), "active_games_count": len(recent_games), "average_session_estimate": round(total_recent_playtime / (14 * len(recent_games)), 1) if recent_games else 0, "timestamp": datetime.now().isoformat()}

        return {"recent_games": recent_activity, "most_played_alltime": most_played, "summary": summary}
