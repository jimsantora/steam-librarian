#!/usr/bin/env python3
"""Steam Library MCP Server - Provides access to Steam game library data using SQLite"""

import os
from typing import Annotated, Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import func, and_, or_, desc
from fastmcp import FastMCP

from database import (
    get_db, Game, UserGame, Genre, Developer, Publisher, Category, 
    GameReview, UserProfile
)

# Create the server instance
mcp = FastMCP("steam-librarian")

# Get Steam ID from environment
STEAM_ID = os.environ.get('STEAM_ID', '')

def get_user_steam_id() -> str:
    """Get the Steam ID for the current user"""
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
def get_user_info() -> Optional[Dict[str, Any]]:
    """Get comprehensive user profile information including Steam level, account age, and location"""
    steam_id = get_user_steam_id()
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
    query: Annotated[str, "Search term to match against game name, genre, developer, or publisher"]
) -> List[Dict[str, Any]]:
    """Search for games by name, genre, developer, or publisher"""
    steam_id = get_user_steam_id()
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
    maturity_rating: Annotated[Optional[str], "Maturity rating to filter by (e.g., 'Everyone', 'Teen (13+)')"] = None
) -> List[Dict[str, Any]]:
    """Filter games by playtime, review summary, or maturity rating"""
    steam_id = get_user_steam_id()
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
    game_identifier: Annotated[str, "Game name or appid to get details for"]
) -> Optional[Dict[str, Any]]:
    """Get comprehensive details about a specific game"""
    steam_id = get_user_steam_id()
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
    game_identifier: Annotated[str, "Game name or appid to get review data for"]
) -> Optional[Dict[str, Any]]:
    """Get detailed review statistics for a game"""
    game = get_game_details(game_identifier)
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
def get_library_stats() -> Dict[str, Any]:
    """Get overview statistics about the entire game library"""
    steam_id = get_user_steam_id()
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
def get_recently_played() -> List[Dict[str, Any]]:
    """Get games played in the last 2 weeks"""
    steam_id = get_user_steam_id()
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
def get_recommendations() -> List[Dict[str, Any]]:
    """Get personalized game recommendations based on playtime patterns"""
    steam_id = get_user_steam_id()
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

if __name__ == "__main__":
    mcp.run()