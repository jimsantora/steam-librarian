#!/usr/bin/env python3
"""Steam Library MCP Server - Provides access to Steam game library data using SQLite"""

import os
from typing import Annotated, Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import func, and_, or_, desc
from fastmcp import FastMCP

from database import (
    get_db, Game, UserGame, Genre, Developer, Publisher, Category, 
    GameReview, UserProfile, friends_association
)

# Create the server instance
mcp = FastMCP("steam-librarian")

# Get Steam ID from environment (fallback for backwards compatibility)
STEAM_ID = os.environ.get('STEAM_ID', '')

@mcp.prompt
def select_user_prompt() -> str:
    """Prompt to select which user to use for the query"""
    with get_db() as session:
        users = session.query(UserProfile).all()
        if not users:
            return "No users found in database. Please run the fetcher first with: python steam_library_fetcher.py"
        
        user_list = "\n".join([
            f"- {user.persona_name or 'Unknown'} (Steam ID: {user.steam_id})" 
            for user in users
        ])
    
    return f"""Please select a user for this query:

{user_list}

Enter the Steam ID of the user you want to use:"""

@mcp.tool
def get_all_users() -> List[Dict[str, Any]]:
    """Get list of all available user profiles in the database"""
    with get_db() as session:
        users = session.query(UserProfile).all()
        return [
            {
                'steam_id': user.steam_id,
                'persona_name': user.persona_name or 'Unknown',
                'profile_url': user.profile_url or '',
                'steam_level': user.steam_level or 0,
                'last_updated': user.last_updated
            }
            for user in users
        ]

def resolve_user_identifier(user_identifier: Optional[str]) -> Optional[str]:
    """Resolve user identifier (Steam ID or persona name) to Steam ID"""
    if not user_identifier:
        return None
    
    # If it looks like a Steam ID (all digits), use it directly
    if user_identifier.isdigit():
        return user_identifier
    
    # Otherwise, search by persona name (case-insensitive)
    with get_db() as session:
        user = session.query(UserProfile).filter(
            func.lower(UserProfile.persona_name) == func.lower(user_identifier)
        ).first()
        if user:
            return user.steam_id
    
    return None

def get_user_steam_id() -> str:
    """Get the Steam ID for the current user (backwards compatibility)"""
    # Try to get from environment first
    if STEAM_ID:
        return STEAM_ID
    
    # Otherwise get from database (first user)
    with get_db() as session:
        user = session.query(UserProfile).first()
        if user:
            return user.steam_id
    
    return ''

@mcp.tool
def get_user_info(
    user_steam_id: Annotated[Optional[str], "Steam ID or persona name of user (leave empty for auto-selection)"] = None
) -> Optional[Dict[str, Any]]:
    """Get comprehensive user profile information including Steam level, account age, and location"""
    # Resolve user identifier (could be Steam ID or persona name)
    if user_steam_id:
        resolved_steam_id = resolve_user_identifier(user_steam_id)
        if not resolved_steam_id:
            return {'error': f'User not found: {user_steam_id}. Available users can be seen with get_all_users()'}
        user_steam_id = resolved_steam_id
    
    if not user_steam_id:
        # Auto-select user if none provided
        with get_db() as session:
            users = session.query(UserProfile).all()
            if len(users) == 1:
                user_steam_id = users[0].steam_id
            elif len(users) > 1:
                # Return list of available users for selection
                return {
                    'message': 'Multiple users found. Please specify which user by Steam ID or persona name:',
                    'available_users': [{
                        'steam_id': user.steam_id,
                        'persona_name': user.persona_name or 'Unknown'
                    } for user in users]
                }
            else:
                user_steam_id = get_user_steam_id()  # Fallback to env var
    
    steam_id = user_steam_id
    if not steam_id:
        return {
            'error': 'No Steam ID configured',
            'steam_id': '',
            'persona_name': 'Unknown',
            'profile_url': '',
            'steam_level': 0,
            'xp': 0,
            'account_age_years': 0,
            'account_created_date': '',
            'location': 'Unknown',
            'avatar_urls': {
                'small': '',
                'medium': '',
                'large': ''
            }
        }
    
    with get_db() as session:
        user = session.query(UserProfile).filter_by(steam_id=steam_id).first()
        
        if not user:
            return {
                'error': 'User profile not found. Run steam_library_fetcher.py first.',
                'steam_id': steam_id,
                'persona_name': 'Unknown',
                'profile_url': '',
                'steam_level': 0,
                'xp': 0,
                'account_age_years': 0,
                'account_created_date': '',
                'location': 'Unknown',
                'avatar_urls': {
                    'small': '',
                    'medium': '',
                    'large': ''
                }
            }
        
        # Calculate account age
        account_age_years = 0
        account_created_date = 'Unknown'
        if user.time_created and user.time_created > 0:
            account_created = datetime.fromtimestamp(user.time_created)
            account_created_date = account_created.strftime('%Y-%m-%d')
            account_age_years = round((datetime.now() - account_created).days / 365.25, 1)
        
        # Format location
        location = 'Unknown'
        if user.loccountrycode:
            location = user.loccountrycode
            if user.locstatecode:
                location += f", {user.locstatecode}"
        
        # Get total games count
        total_games = session.query(UserGame).filter_by(steam_id=steam_id).count()
        
        # Get total playtime
        total_playtime_minutes = session.query(func.sum(UserGame.playtime_forever)).filter_by(steam_id=steam_id).scalar() or 0
        total_playtime_hours = round(total_playtime_minutes / 60, 1)
        
        return {
            'steam_id': user.steam_id,
            'persona_name': user.persona_name or 'Unknown',
            'profile_url': user.profile_url or '',
            'steam_level': user.steam_level or 0,
            'xp': user.xp or 0,
            'account_age_years': account_age_years,
            'account_created_date': account_created_date,
            'location': location,
            'avatar_urls': {
                'small': user.avatar_url or '',
                'medium': user.avatarmedium or '',
                'large': user.avatarfull or ''
            },
            'library_stats': {
                'total_games': total_games,
                'total_playtime_hours': total_playtime_hours
            },
            'last_updated': datetime.fromtimestamp(user.last_updated).strftime('%Y-%m-%d %H:%M:%S') if user.last_updated else 'Never'
        }

@mcp.tool
def search_games(
    query: Annotated[str, "Search term to match against game name, genre, developer, or publisher"],
    user_steam_id: Annotated[Optional[str], "Steam ID or persona name of user (leave empty for auto-selection)"] = None
) -> List[Dict[str, Any]]:
    """Search for games by name, genre, developer, or publisher"""
    # Resolve user identifier (could be Steam ID or persona name)
    if user_steam_id:
        resolved_steam_id = resolve_user_identifier(user_steam_id)
        if not resolved_steam_id:
            return [{'error': f'User not found: {user_steam_id}. Available users can be seen with get_all_users()'}]
        user_steam_id = resolved_steam_id
    
    if not user_steam_id:
        # Auto-select user if none provided
        with get_db() as session:
            users = session.query(UserProfile).all()
            if len(users) == 1:
                user_steam_id = users[0].steam_id
            elif len(users) > 1:
                # Return list of available users for selection
                return [{
                    'message': 'Multiple users found. Please specify which user by Steam ID or persona name:',
                    'available_users': [{
                        'steam_id': user.steam_id,
                        'persona_name': user.persona_name or 'Unknown'
                    } for user in users]
                }]
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

@mcp.tool
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

@mcp.tool
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

@mcp.tool
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

@mcp.tool
def get_library_stats(
    user_steam_id: Annotated[Optional[str], "Steam ID or persona name of user (leave empty for auto-selection)"] = None
) -> Dict[str, Any]:
    """Get overview statistics about the entire game library"""
    # Resolve user identifier (could be Steam ID or persona name)
    if user_steam_id:
        resolved_steam_id = resolve_user_identifier(user_steam_id)
        if not resolved_steam_id:
            return {'error': f'User not found: {user_steam_id}. Available users can be seen with get_all_users()'}
        user_steam_id = resolved_steam_id
    
    if not user_steam_id:
        # Auto-select user if none provided
        with get_db() as session:
            users = session.query(UserProfile).all()
            if len(users) == 1:
                user_steam_id = users[0].steam_id
            elif len(users) > 1:
                # Return list of available users for selection
                return {
                    'message': 'Multiple users found. Please specify which user by Steam ID or persona name:',
                    'available_users': [{
                        'steam_id': user.steam_id,
                        'persona_name': user.persona_name or 'Unknown'
                    } for user in users]
                }
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

@mcp.tool
def get_recently_played(
    user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None
) -> List[Dict[str, Any]]:
    """Get games played in the last 2 weeks"""
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
        results = session.query(
            Game.app_id,
            Game.name,
            UserGame.playtime_2weeks,
            UserGame.playtime_forever
        ).join(
            UserGame, Game.app_id == UserGame.app_id
        ).filter(
            and_(
                UserGame.steam_id == steam_id,
                UserGame.playtime_2weeks > 0
            )
        ).order_by(desc(UserGame.playtime_2weeks)).all()
        
        return [
            {
                'appid': result.app_id,
                'name': result.name,
                'playtime_2weeks_hours': round(result.playtime_2weeks / 60, 1),
                'playtime_forever_hours': round(result.playtime_forever / 60, 1)
            }
            for result in results
        ]

@mcp.tool
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

@mcp.tool
def get_friends_data(
    data_type: Annotated[str, "Type of data: 'list', 'common_games', 'who_owns_game', 'library_comparison'"],
    user_steam_id: Annotated[Optional[str], "Steam ID or persona name of user (leave empty for auto-selection)"] = None,
    friend_steam_id: Annotated[Optional[str], "Friend's Steam ID or persona name for specific queries"] = None,
    game_identifier: Annotated[Optional[str], "Game name or appid for game-specific queries"] = None
) -> Optional[Dict[str, Any]]:
    """Unified tool for all friends-related queries"""
    
    # Resolve user identifier (could be Steam ID or persona name)
    if user_steam_id:
        resolved_steam_id = resolve_user_identifier(user_steam_id)
        if not resolved_steam_id:
            return {'error': f'User not found: {user_steam_id}. Available users can be seen with get_all_users()'}
        user_steam_id = resolved_steam_id
    
    if not user_steam_id:
        # Auto-select user if none provided
        with get_db() as session:
            users = session.query(UserProfile).all()
            if len(users) == 1:
                user_steam_id = users[0].steam_id
            elif len(users) > 1:
                # Return list of available users for selection
                return {
                    'message': 'Multiple users found. Please specify which user by Steam ID or persona name:',
                    'available_users': [{
                        'steam_id': user.steam_id,
                        'persona_name': user.persona_name or 'Unknown'
                    } for user in users]
                }
            else:
                return {'error': 'No users found in database'}
    
    # Also resolve friend identifier if provided
    if friend_steam_id:
        resolved_friend_id = resolve_user_identifier(friend_steam_id) 
        if not resolved_friend_id:
            return {'error': f'Friend not found: {friend_steam_id}'}
        friend_steam_id = resolved_friend_id
    
    if not user_steam_id:
        return {'error': 'No user Steam ID provided'}
    
    with get_db() as session:
        if data_type == 'list':
            # Return all friends with basic info using the association table
            friends_data = session.execute(
                friends_association.select().where(
                    friends_association.c.user_steam_id == user_steam_id
                )
            ).fetchall()
            
            # Get friend profiles
            friend_steam_ids = [friend.friend_steam_id for friend in friends_data]
            if not friend_steam_ids:
                return {'user_steam_id': user_steam_id, 'friends': []}
            
            friend_profiles = session.query(UserProfile).filter(
                UserProfile.steam_id.in_(friend_steam_ids)
            ).all()
            
            # Create lookup for profiles
            profile_lookup = {profile.steam_id: profile for profile in friend_profiles}
            
            return {
                'user_steam_id': user_steam_id,
                'friends': [
                    {
                        'steam_id': friend.friend_steam_id,
                        'persona_name': profile_lookup.get(friend.friend_steam_id).persona_name if profile_lookup.get(friend.friend_steam_id) else 'Unknown',
                        'relationship': friend.relationship,
                        'friend_since': friend.friend_since,
                        'profile_url': profile_lookup.get(friend.friend_steam_id).profile_url if profile_lookup.get(friend.friend_steam_id) else ''
                    }
                    for friend in friends_data
                ]
            }
        
        elif data_type == 'common_games':
            # Games owned by both user and specific friend
            if not friend_steam_id:
                return {'error': 'friend_steam_id required for common_games query'}
            
            # Get games that both users own by finding common app_ids
            user_games_subq = session.query(UserGame.app_id).filter_by(steam_id=user_steam_id).subquery()
            friend_games_subq = session.query(UserGame.app_id).filter_by(steam_id=friend_steam_id).subquery()
            
            # Find common app_ids
            common_app_ids = session.query(user_games_subq.c.app_id).intersect(
                session.query(friend_games_subq.c.app_id)
            ).all()
            
            if not common_app_ids:
                return {
                    'user_steam_id': user_steam_id,
                    'friend_steam_id': friend_steam_id,
                    'common_games': []
                }
            
            common_app_id_list = [app_id[0] for app_id in common_app_ids]
            
            # Get user playtime for common games
            user_playtimes = session.query(
                UserGame.app_id, UserGame.playtime_forever
            ).filter(
                and_(
                    UserGame.steam_id == user_steam_id,
                    UserGame.app_id.in_(common_app_id_list)
                )
            ).all()
            
            # Get friend playtime for common games  
            friend_playtimes = session.query(
                UserGame.app_id, UserGame.playtime_forever
            ).filter(
                and_(
                    UserGame.steam_id == friend_steam_id,
                    UserGame.app_id.in_(common_app_id_list)
                )
            ).all()
            
            # Create lookup dictionaries
            user_playtime_dict = {pt.app_id: pt.playtime_forever for pt in user_playtimes}
            friend_playtime_dict = {pt.app_id: pt.playtime_forever for pt in friend_playtimes}
            
            # Get game names
            games = session.query(Game.app_id, Game.name).filter(
                Game.app_id.in_(common_app_id_list)
            ).all()
            
            # Build result list
            common_games = []
            for game in games:
                user_playtime = user_playtime_dict.get(game.app_id, 0)
                friend_playtime = friend_playtime_dict.get(game.app_id, 0)
                common_games.append({
                    'appid': game.app_id,
                    'name': game.name,
                    'user_playtime_hours': round(user_playtime / 60, 1) if user_playtime else 0,
                    'friend_playtime_hours': round(friend_playtime / 60, 1) if friend_playtime else 0
                })
            
            # Sort by user playtime (descending)
            common_games.sort(key=lambda x: x['user_playtime_hours'], reverse=True)
            
            return {
                'user_steam_id': user_steam_id,
                'friend_steam_id': friend_steam_id,
                'common_games': common_games
            }
        
        elif data_type == 'who_owns_game':
            # Friends who own a specific game
            if not game_identifier:
                return {'error': 'game_identifier required for who_owns_game query'}
            
            # Find the game first
            game = None
            try:
                appid = int(game_identifier)
                game = session.query(Game).filter_by(app_id=appid).first()
            except ValueError:
                game = session.query(Game).filter(Game.name.ilike(f"%{game_identifier}%")).first()
            
            if not game:
                return {'error': f'Game not found: {game_identifier}'}
            
            # Find friends who own this game using association table
            friends_data = session.execute(
                friends_association.select().where(
                    friends_association.c.user_steam_id == user_steam_id
                )
            ).fetchall()
            
            friend_steam_ids = [friend.friend_steam_id for friend in friends_data]
            if not friend_steam_ids:
                return {
                    'user_steam_id': user_steam_id,
                    'game': {'appid': game.app_id, 'name': game.name},
                    'friends_with_game': []
                }
            
            # Find which friends own this game
            friends_with_game = session.query(
                UserProfile, UserGame
            ).join(
                UserGame, UserProfile.steam_id == UserGame.steam_id
            ).filter(
                and_(
                    UserProfile.steam_id.in_(friend_steam_ids),
                    UserGame.app_id == game.app_id
                )
            ).all()
            
            return {
                'user_steam_id': user_steam_id,
                'game': {
                    'appid': game.app_id,
                    'name': game.name
                },
                'friends_with_game': [
                    {
                        'steam_id': friend.UserProfile.steam_id,
                        'persona_name': friend.UserProfile.persona_name or 'Unknown',
                        'playtime_hours': round(friend.UserGame.playtime_forever / 60, 1) if friend.UserGame.playtime_forever else 0
                    }
                    for friend in friends_with_game
                ]
            }
        
        else:
            return {'error': f'Unknown data_type: {data_type}. Use: list, common_games, who_owns_game, library_comparison'}

if __name__ == "__main__":
    mcp.run()