"""User-related tools"""
from typing import Annotated, Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import func, and_, desc

from src.core.database import get_db
from src.models import Game, UserGame, UserProfile, friends_association
from src.mcp.prompts.user_selection import select_user_prompt
from src.mcp.tools.utils import get_user_steam_id


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


def get_user_info(
    user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None
) -> Optional[Dict[str, Any]]:
    """Get comprehensive user profile information including Steam level, account age, and location"""
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


def get_friends_data(
    data_type: Annotated[str, "Type of data: 'list', 'common_games', 'who_owns_game', 'library_comparison'"],
    user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None,
    friend_steam_id: Annotated[Optional[str], "Friend's Steam ID for specific queries"] = None,
    game_identifier: Annotated[Optional[str], "Game name or appid for game-specific queries"] = None
) -> Optional[Dict[str, Any]]:
    """Unified tool for all friends-related queries"""
    
    if not user_steam_id:
        # Use prompt to select user if none provided
        with get_db() as session:
            users = session.query(UserProfile).all()
            if len(users) > 1:
                return {'prompt_needed': True, 'message': select_user_prompt()}
            elif len(users) == 1:
                user_steam_id = users[0].steam_id
            else:
                return {'error': 'No users found in database'}
    
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
            
            common_games = session.query(
                Game.app_id, Game.name,
                UserGame.playtime_forever.label('user_playtime'),
                func.max(UserGame.playtime_forever).label('friend_playtime')
            ).join(
                UserGame, Game.app_id == UserGame.app_id
            ).filter(
                UserGame.steam_id.in_([user_steam_id, friend_steam_id])
            ).group_by(
                Game.app_id, Game.name
            ).having(
                func.count(UserGame.steam_id) == 2
            ).order_by(
                desc('user_playtime')
            ).all()
            
            return {
                'user_steam_id': user_steam_id,
                'friend_steam_id': friend_steam_id,
                'common_games': [
                    {
                        'appid': game.app_id,
                        'name': game.name,
                        'user_playtime_hours': round(game.user_playtime / 60, 1) if game.user_playtime else 0,
                        'friend_playtime_hours': round(game.friend_playtime / 60, 1) if game.friend_playtime else 0
                    }
                    for game in common_games
                ]
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