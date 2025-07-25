"""Tools for getting detailed game and review information"""
from typing import Annotated, Optional, Dict, Any

from src.core.database import get_db
from src.models import Game, UserGame, GameReview, UserProfile
from src.mcp.prompts.user_selection import select_user_prompt
from src.mcp.tools.utils import get_user_steam_id


def get_game_details(
    game_identifier: Annotated[str, "Game name or appid to get details for"],
    user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None
) -> Optional[Dict[str, Any]]:
    """Get comprehensive details about a specific game"""
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
        return None
    
    with get_db() as session:
        # Try to match by appid first (if it's a number)
        game = None
        try:
            appid = int(game_identifier)
            game = session.query(Game).filter_by(app_id=appid).first()
        except ValueError:
            # Otherwise search by name (case-insensitive exact match first)
            game = session.query(Game).filter(Game.name.ilike(game_identifier)).first()
            
            # If no exact match, try partial match
            if not game:
                game = session.query(Game).filter(Game.name.ilike(f"%{game_identifier}%")).first()
        
        if not game:
            return None
        
        # Get user game data
        user_game = session.query(UserGame).filter_by(
            steam_id=steam_id, 
            app_id=game.app_id
        ).first()
        
        # Get review data
        review = session.query(GameReview).filter_by(app_id=game.app_id).first()
        
        # Build result
        result = {
            'appid': game.app_id,
            'name': game.name,
            'maturity_rating': game.maturity_rating,
            'required_age': game.required_age,
            'content_descriptors': game.content_descriptors,
            'release_date': game.release_date,
            'genres': ', '.join([g.genre_name for g in game.genres]),
            'categories': ', '.join([c.category_name for c in game.categories]),
            'developers': ', '.join([d.developer_name for d in game.developers]),
            'publishers': ', '.join([p.publisher_name for p in game.publishers]),
            'playtime_forever': user_game.playtime_forever if user_game else 0,
            'playtime_2weeks': user_game.playtime_2weeks if user_game else 0,
            'playtime_forever_hours': round(user_game.playtime_forever / 60, 1) if user_game and user_game.playtime_forever else 0,
            'playtime_2weeks_hours': round(user_game.playtime_2weeks / 60, 1) if user_game and user_game.playtime_2weeks else 0,
        }
        
        # Add review data if available
        if review:
            result.update({
                'review_summary': review.review_summary,
                'review_score': review.review_score,
                'total_reviews': review.total_reviews,
                'positive_reviews': review.positive_reviews,
                'negative_reviews': review.negative_reviews,
            })
        else:
            result.update({
                'review_summary': 'Unknown',
                'review_score': 0,
                'total_reviews': 0,
                'positive_reviews': 0,
                'negative_reviews': 0,
            })
        
        return result


def get_game_reviews(
    game_identifier: Annotated[str, "Game name or appid to get review data for"],
    user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None
) -> Optional[Dict[str, Any]]:
    """Get detailed review statistics for a game"""
    game = get_game_details(game_identifier, user_steam_id)
    if not game:
        return None
    
    positive_percentage = 0
    if game['total_reviews'] > 0:
        positive_percentage = round((game['positive_reviews'] / game['total_reviews']) * 100, 1)
    
    return {
        'name': game['name'],
        'appid': game['appid'],
        'review_summary': game['review_summary'],
        'review_score': game['review_score'],
        'total_reviews': game['total_reviews'],
        'positive_reviews': game['positive_reviews'],
        'negative_reviews': game['negative_reviews'],
        'positive_percentage': positive_percentage
    }