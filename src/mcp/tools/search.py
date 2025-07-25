"""Search and filter tools for Steam games"""
from typing import Annotated, Optional, List, Dict, Any
from sqlalchemy import func, and_, or_, desc

from src.core.database import get_db
from src.models import Game, UserGame, GameReview, Genre, Developer, Publisher, UserProfile
from src.mcp.prompts.user_selection import select_user_prompt
from src.mcp.tools.utils import get_user_steam_id


def search_games(
    query: Annotated[str, "Search term to match against game name, genre, developer, or publisher"],
    user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None
) -> List[Dict[str, Any]]:
    """Search for games by name, genre, developer, or publisher"""
    if not user_steam_id:
        # Use prompt to select user if none provided
        with get_db() as session:
            users = session.query(UserProfile).all()
            if len(users) > 1:
                return [{'prompt_needed': True, 'message': select_user_prompt()}]
            elif len(users) == 1:
                user_steam_id = users[0].steam_id
            else:
                user_steam_id = get_user_steam_id()  # Fallback to env var
    
    steam_id = user_steam_id
    if not steam_id:
        return []
    
    with get_db() as session:
        # Build the query with joins
        query_lower = f"%{query.lower()}%"
        
        results = session.query(
            Game.app_id,
            Game.name,
            func.group_concat(Genre.genre_name.distinct()).label('genres'),
            GameReview.review_summary,
            UserGame.playtime_forever
        ).join(
            UserGame, Game.app_id == UserGame.app_id
        ).outerjoin(
            GameReview, Game.app_id == GameReview.app_id
        ).outerjoin(
            Game.genres
        ).outerjoin(
            Game.developers
        ).outerjoin(
            Game.publishers
        ).filter(
            and_(
                UserGame.steam_id == steam_id,
                or_(
                    Game.name.ilike(query_lower),
                    Genre.genre_name.ilike(query_lower),
                    Developer.developer_name.ilike(query_lower),
                    Publisher.publisher_name.ilike(query_lower)
                )
            )
        ).group_by(Game.app_id).order_by(desc(UserGame.playtime_forever)).all()
        
        return [
            {
                'appid': result.app_id,
                'name': result.name,
                'genres': result.genres or '',
                'review_summary': result.review_summary or 'Unknown',
                'playtime_forever_hours': round(result.playtime_forever / 60, 1) if result.playtime_forever else 0
            }
            for result in results
        ]


def filter_games(
    playtime_min: Annotated[Optional[float], "Minimum playtime in hours"] = None,
    playtime_max: Annotated[Optional[float], "Maximum playtime in hours"] = None,
    review_summary: Annotated[Optional[str], "Review summary to filter by (e.g., 'Very Positive', 'Overwhelmingly Positive')"] = None,
    maturity_rating: Annotated[Optional[str], "Maturity rating to filter by (e.g., 'Everyone', 'Teen (13+)')"] = None,
    user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None
) -> List[Dict[str, Any]]:
    """Filter games by playtime, review summary, or maturity rating"""
    if not user_steam_id:
        # Use prompt to select user if none provided
        with get_db() as session:
            users = session.query(UserProfile).all()
            if len(users) > 1:
                return [{'prompt_needed': True, 'message': select_user_prompt()}]
            elif len(users) == 1:
                user_steam_id = users[0].steam_id
            else:
                user_steam_id = get_user_steam_id()  # Fallback to env var
    
    steam_id = user_steam_id
    if not steam_id:
        return []
    
    with get_db() as session:
        query = session.query(
            Game.app_id,
            Game.name,
            func.group_concat(Genre.genre_name.distinct()).label('genres'),
            GameReview.review_summary,
            UserGame.playtime_forever
        ).join(
            UserGame, Game.app_id == UserGame.app_id
        ).outerjoin(
            GameReview, Game.app_id == GameReview.app_id
        ).outerjoin(
            Game.genres
        ).filter(
            UserGame.steam_id == steam_id
        )
        
        # Apply filters
        if playtime_min is not None:
            query = query.filter(UserGame.playtime_forever >= playtime_min * 60)
        
        if playtime_max is not None:
            query = query.filter(UserGame.playtime_forever <= playtime_max * 60)
        
        if review_summary:
            query = query.filter(GameReview.review_summary.ilike(f"%{review_summary}%"))
        
        if maturity_rating:
            query = query.filter(Game.maturity_rating.ilike(f"%{maturity_rating}%"))
        
        results = query.group_by(Game.app_id).order_by(desc(UserGame.playtime_forever)).all()
        
        return [
            {
                'appid': result.app_id,
                'name': result.name,
                'genres': result.genres or '',
                'review_summary': result.review_summary or 'Unknown',
                'playtime_forever_hours': round(result.playtime_forever / 60, 1) if result.playtime_forever else 0
            }
            for result in results
        ]