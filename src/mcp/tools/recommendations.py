"""Game recommendation tool"""
from typing import Annotated, Optional, List, Dict, Any
from sqlalchemy import func, and_, or_, desc

from src.core.database import get_db
from src.models import Game, UserGame, GameReview, Genre, Developer, UserProfile
from src.mcp.prompts.user_selection import select_user_prompt
from src.mcp.tools.utils import get_user_steam_id


def get_recommendations(
    user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None
) -> List[Dict[str, Any]]:
    """Get personalized game recommendations based on playtime patterns"""
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
        recommendations = []
        
        # Get user's top genres by playtime
        played_games = session.query(UserGame).filter(
            and_(
                UserGame.steam_id == steam_id,
                UserGame.playtime_forever > 0
            )
        ).count()
        
        if played_games == 0:
            # If no games played, recommend highest rated games
            top_rated = session.query(Game).join(
                GameReview, Game.app_id == GameReview.app_id
            ).join(
                UserGame, Game.app_id == UserGame.app_id
            ).filter(
                and_(
                    UserGame.steam_id == steam_id,
                    UserGame.playtime_forever == 0,
                    GameReview.review_summary.in_(['Overwhelmingly Positive', 'Very Positive'])
                )
            ).limit(5).all()
            
            for game in top_rated:
                review = session.query(GameReview).filter_by(app_id=game.app_id).first()
                recommendations.append({
                    'appid': game.app_id,
                    'name': game.name,
                    'reason': f"Highly rated game ({review.review_summary if review else 'Unknown'}) you haven't played yet"
                })
            return recommendations
        
        # Find favorite genres by total playtime
        genre_playtime = session.query(
            Genre.genre_name,
            func.sum(UserGame.playtime_forever).label('total_playtime')
        ).join(
            Game.genres
        ).join(
            UserGame, Game.app_id == UserGame.app_id
        ).filter(
            and_(
                UserGame.steam_id == steam_id,
                UserGame.playtime_forever > 0
            )
        ).group_by(Genre.genre_name).order_by(desc('total_playtime')).limit(3).all()
        
        # Find unplayed games in favorite genres
        for genre_data in genre_playtime:
            genre_games = session.query(Game).join(
                Game.genres
            ).join(
                UserGame, Game.app_id == UserGame.app_id
            ).outerjoin(
                GameReview, Game.app_id == GameReview.app_id
            ).filter(
                and_(
                    UserGame.steam_id == steam_id,
                    UserGame.playtime_forever == 0,
                    Genre.genre_name == genre_data.genre_name,
                    or_(
                        GameReview.review_summary.in_(['Overwhelmingly Positive', 'Very Positive']),
                        GameReview.review_summary.is_(None)
                    )
                )
            ).limit(2).all()
            
            hours = round(genre_data.total_playtime / 60, 1)
            for game in genre_games:
                recommendations.append({
                    'appid': game.app_id,
                    'name': game.name,
                    'reason': f"Similar genre ({genre_data.genre_name}) to games you've played {hours} hours"
                })
        
        # Find games from favorite developers
        dev_playtime = session.query(
            Developer.developer_name,
            func.sum(UserGame.playtime_forever).label('total_playtime')
        ).join(
            Game.developers
        ).join(
            UserGame, Game.app_id == UserGame.app_id
        ).filter(
            and_(
                UserGame.steam_id == steam_id,
                UserGame.playtime_forever > 0
            )
        ).group_by(Developer.developer_name).order_by(desc('total_playtime')).limit(3).all()
        
        for dev_data in dev_playtime:
            dev_games = session.query(Game).join(
                Game.developers
            ).join(
                UserGame, Game.app_id == UserGame.app_id
            ).filter(
                and_(
                    UserGame.steam_id == steam_id,
                    UserGame.playtime_forever == 0,
                    Developer.developer_name == dev_data.developer_name
                )
            ).limit(1).all()
            
            hours = round(dev_data.total_playtime / 60, 1)
            for game in dev_games:
                recommendations.append({
                    'appid': game.app_id,
                    'name': game.name,
                    'reason': f"From {dev_data.developer_name} who made games you've played {hours} hours"
                })
        
        # Remove duplicates
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec['appid'] not in seen:
                seen.add(rec['appid'])
                unique_recs.append(rec)
        
        return unique_recs[:10]  # Limit to 10 recommendations