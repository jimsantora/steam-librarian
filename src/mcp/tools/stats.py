"""Library statistics tool"""
from typing import Annotated, Optional, Dict, Any
from sqlalchemy import func, desc

from src.core.database import get_db
from src.models import Game, UserGame, GameReview, Genre, Developer, UserProfile
from src.mcp.prompts.user_selection import select_user_prompt
from src.mcp.tools.utils import get_user_steam_id


def get_library_stats(
    user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None
) -> Dict[str, Any]:
    """Get overview statistics about the entire game library"""
    if not user_steam_id:
        # Use prompt to select user if none provided
        with get_db() as session:
            users = session.query(UserProfile).all()
            if len(users) > 1:
                return {'prompt_needed': True, 'message': select_user_prompt()}
            elif len(users) == 1:
                user_steam_id = users[0].steam_id
            else:
                user_steam_id = get_user_steam_id()  # Fallback to env var
    
    steam_id = user_steam_id
    if not steam_id:
        return {
            'total_games': 0,
            'total_hours_played': 0,
            'average_hours_per_game': 0,
            'top_genres': {},
            'top_developers': {},
            'review_distribution': {}
        }
    
    with get_db() as session:
        # Basic stats
        total_games = session.query(UserGame).filter_by(steam_id=steam_id).count()
        
        total_minutes = session.query(func.sum(UserGame.playtime_forever)).filter_by(steam_id=steam_id).scalar() or 0
        total_hours = round(total_minutes / 60, 2)
        avg_hours = round(total_hours / total_games, 2) if total_games > 0 else 0
        
        # Top genres
        genre_stats = session.query(
            Genre.genre_name,
            func.count(Genre.genre_name).label('count')
        ).join(
            Game.genres
        ).join(
            UserGame, Game.app_id == UserGame.app_id
        ).filter(
            UserGame.steam_id == steam_id
        ).group_by(Genre.genre_name).order_by(desc('count')).limit(10).all()
        
        top_genres = {genre.genre_name: genre.count for genre in genre_stats}
        
        # Top developers
        dev_stats = session.query(
            Developer.developer_name,
            func.count(Developer.developer_name).label('count')
        ).join(
            Game.developers
        ).join(
            UserGame, Game.app_id == UserGame.app_id
        ).filter(
            UserGame.steam_id == steam_id
        ).group_by(Developer.developer_name).order_by(desc('count')).limit(10).all()
        
        top_developers = {dev.developer_name: dev.count for dev in dev_stats}
        
        # Review distribution
        review_stats = session.query(
            GameReview.review_summary,
            func.count(GameReview.review_summary).label('count')
        ).join(
            UserGame, GameReview.app_id == UserGame.app_id
        ).filter(
            UserGame.steam_id == steam_id
        ).group_by(GameReview.review_summary).all()
        
        review_distribution = {review.review_summary: review.count for review in review_stats if review.review_summary}
        
        return {
            'total_games': total_games,
            'total_hours_played': total_hours,
            'average_hours_per_game': avg_hours,
            'top_genres': top_genres,
            'top_developers': top_developers,
            'review_distribution': review_distribution
        }