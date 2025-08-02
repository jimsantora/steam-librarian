"""MCP resources using proper database schema"""

import json
from sqlalchemy.orm import joinedload

from shared.database import (
    Game,
    UserGame,
    UserProfile,
    Genre,
    get_db,
    resolve_user_for_tool,
)
from .config import config
from .server import mcp


def get_default_user_fallback():
    """Fallback function to get default user from config"""
    if config.default_user and config.default_user != "default":
        return config.default_user
    return None


@mcp.resource("library://games/{game_id}")
def get_game(game_id: str) -> str:
    """Get game details by ID."""
    try:
        with get_db() as session:
            # Load game with all relationships
            game = session.query(Game).options(
                joinedload(Game.genres),
                joinedload(Game.developers),
                joinedload(Game.publishers),
                joinedload(Game.categories),
                joinedload(Game.reviews)
            ).filter_by(app_id=int(game_id)).first()
            
            if game:
                game_data = {
                    "id": game.app_id,
                    "name": game.name,
                    "genres": [g.genre_name for g in game.genres],
                    "developers": [d.developer_name for d in game.developers],
                    "publishers": [p.publisher_name for p in game.publishers],
                    "categories": [c.category_name for c in game.categories],
                    "release_date": game.release_date,
                    "esrb_rating": game.esrb_rating,
                    "required_age": game.required_age,
                    "esrb_descriptors": game.esrb_descriptors
                }
                
                # Add review data if available
                if game.reviews:
                    game_data["reviews"] = {
                        "summary": game.reviews.review_summary,
                        "score": game.reviews.review_score,
                        "total": game.reviews.total_reviews,
                        "positive_percentage": game.reviews.positive_percentage
                    }
                
                return json.dumps(game_data, indent=2)
            else:
                return json.dumps({"error": f"Game with ID {game_id} not found"})
            
    except Exception as e:
        return json.dumps({"error": f"Failed to get game: {str(e)}"})


@mcp.resource("library://overview")
def library_overview() -> str:
    """Get library overview with navigation to user-specific resources."""
    try:
        with get_db() as session:
            # Get basic system stats
            total_games = session.query(Game).count()
            total_users = session.query(UserProfile).count()
            total_genres = session.query(Genre).count()
            
            # Try to get default user info
            default_user_info = None
            user_result = resolve_user_for_tool(None, get_default_user_fallback)
            
            if "error" not in user_result:
                user_steam_id = user_result["steam_id"]
                user = session.query(UserProfile).filter_by(steam_id=user_steam_id).first()
                if user:
                    game_count = session.query(UserGame).filter_by(steam_id=user.steam_id).count()
                    default_user_info = {
                        "persona_name": user.persona_name,
                        "steam_id": user.steam_id,
                        "game_count": game_count
                    }
            
            # Get top genres across all games
            genres = session.query(Genre).all()
            genre_counts = []
            for genre in genres:
                count = len(genre.games)
                if count > 0:
                    genre_counts.append({"genre": genre.genre_name, "count": count})
            
            genre_counts.sort(key=lambda x: x["count"], reverse=True)
            
            overview = {
                "message": "Steam Library MCP Server Overview",
                "statistics": {
                    "total_games": total_games,
                    "total_users": total_users,
                    "total_genres": total_genres
                },
                "default_user": default_user_info,
                "top_genres": genre_counts[:10],
                "available_resources": {
                    "users": "library://users - List all users",
                    "user_profile": "library://users/{user_id} - Get user profile (use 'default' for default user)",
                    "user_games": "library://users/{user_id}/games - Get user's complete game library",
                    "user_stats": "library://users/{user_id}/stats - Get user's gaming statistics",
                    "game_details": "library://games/{game_id} - Get detailed game information",
                    "genres": "library://genres - List all genres",
                    "games_by_genre": "library://genres/{genre_name}/games - Get games in specific genre",
                    "server_config": "config://settings - Server configuration"
                },
                "tools_available": [
                    "search_games - Natural language search in user's library",
                    "analyze_library - Deep analysis of user's gaming patterns",
                    "generate_recommendation - AI-powered game recommendations",
                    "find_games_with_preferences - Interactive preference-based search",
                    "get_game_details - Detailed game information with user stats"
                ]
            }
            
            return json.dumps(overview, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Failed to get overview: {str(e)}"})




@mcp.resource("library://users/{user_id}")
def get_user_profile(user_id: str) -> str:
    """Get detailed user profile information."""
    try:
        with get_db() as session:
            # Use default user if user_id is "default" or empty
            if user_id == "default" or not user_id:
                user_result = resolve_user_for_tool(None, get_default_user_fallback)
                if "error" in user_result:
                    return json.dumps({"error": f"No default user configured: {user_result['message']}"})
                resolved_user_id = user_result["steam_id"]
            else:
                resolved_user_id = user_id
            
            # Try to resolve user_id as either steam_id or persona_name
            user = session.query(UserProfile).filter(
                (UserProfile.steam_id == resolved_user_id) | 
                (UserProfile.persona_name.ilike(resolved_user_id))
            ).first()
            
            if not user:
                return json.dumps({"error": f"User '{user_id}' not found"})
            
            # Get game count
            game_count = session.query(UserGame).filter_by(steam_id=user.steam_id).count()
            
            user_data = {
                "steam_id": user.steam_id,
                "persona_name": user.persona_name,
                "profile_url": user.profile_url,
                "avatar_url": user.avatar_url,
                "avatarmedium": user.avatarmedium,
                "avatarfull": user.avatarfull,
                "steam_level": user.steam_level,
                "xp": user.xp,
                "time_created": user.time_created,
                "location": {
                    "country": user.loccountrycode,
                    "state": user.locstatecode
                },
                "game_count": game_count,
                "last_updated": user.last_updated,
                "is_default": user.steam_id == config.default_user or user.persona_name == config.default_user
            }
            
            return json.dumps(user_data, indent=2)
            
    except Exception as e:
        return json.dumps({"error": f"Failed to get user profile: {str(e)}"})


@mcp.resource("library://users/{user_id}/games")
def get_user_games(user_id: str) -> str:
    """Get user's complete game library with playtime data."""
    try:
        with get_db() as session:
            # Use default user if user_id is "default" or empty
            if user_id == "default" or not user_id:
                user_result = resolve_user_for_tool(None, get_default_user_fallback)
                if "error" in user_result:
                    return json.dumps({"error": f"No default user configured: {user_result['message']}"})
                resolved_user_id = user_result["steam_id"]
            else:
                resolved_user_id = user_id
            
            # Resolve user
            user = session.query(UserProfile).filter(
                (UserProfile.steam_id == resolved_user_id) | 
                (UserProfile.persona_name.ilike(resolved_user_id))
            ).first()
            
            if not user:
                return json.dumps({"error": f"User '{user_id}' not found"})
            
            # Get user's games with details
            user_games = session.query(UserGame).options(
                joinedload(UserGame.game).joinedload(Game.genres),
                joinedload(UserGame.game).joinedload(Game.developers)
            ).filter(UserGame.steam_id == user.steam_id).all()
            
            games_data = []
            for ug in user_games:
                games_data.append({
                    "app_id": ug.game.app_id,
                    "name": ug.game.name,
                    "playtime_forever_minutes": ug.playtime_forever,
                    "playtime_forever_hours": ug.playtime_hours,
                    "playtime_2weeks_minutes": ug.playtime_2weeks,
                    "playtime_2weeks_hours": ug.playtime_2weeks_hours,
                    "genres": [g.genre_name for g in ug.game.genres],
                    "developers": [d.developer_name for d in ug.game.developers],
                    "release_date": ug.game.release_date
                })
            
            # Sort by playtime descending
            games_data.sort(key=lambda x: x["playtime_forever_minutes"], reverse=True)
            
            library_data = {
                "user": user.persona_name,
                "steam_id": user.steam_id,
                "total_games": len(games_data),
                "games": games_data
            }
            
            return json.dumps(library_data, indent=2)
            
    except Exception as e:
        return json.dumps({"error": f"Failed to get user games: {str(e)}"})


@mcp.resource("library://users/{user_id}/stats")
def get_user_stats(user_id: str) -> str:
    """Get user's gaming statistics and insights."""
    try:
        with get_db() as session:
            # Use default user if user_id is "default" or empty
            if user_id == "default" or not user_id:
                user_result = resolve_user_for_tool(None, get_default_user_fallback)
                if "error" in user_result:
                    return json.dumps({"error": f"No default user configured: {user_result['message']}"})
                resolved_user_id = user_result["steam_id"]
            else:
                resolved_user_id = user_id
            
            # Resolve user
            user = session.query(UserProfile).filter(
                (UserProfile.steam_id == resolved_user_id) | 
                (UserProfile.persona_name.ilike(resolved_user_id))
            ).first()
            
            if not user:
                return json.dumps({"error": f"User '{user_id}' not found"})
            
            # Get user's games with genres
            user_games = session.query(UserGame).options(
                joinedload(UserGame.game).joinedload(Game.genres)
            ).filter(UserGame.steam_id == user.steam_id).all()
            
            # Calculate stats
            total_games = len(user_games)
            total_playtime = sum(ug.playtime_forever for ug in user_games)
            played_games = sum(1 for ug in user_games if ug.playtime_forever > 0)
            recent_playtime = sum(ug.playtime_2weeks for ug in user_games)
            
            # Genre breakdown
            genre_stats = {}
            for ug in user_games:
                for genre in ug.game.genres:
                    if genre.genre_name not in genre_stats:
                        genre_stats[genre.genre_name] = {"count": 0, "playtime": 0}
                    genre_stats[genre.genre_name]["count"] += 1
                    genre_stats[genre.genre_name]["playtime"] += ug.playtime_forever
            
            # Sort genres by playtime
            top_genres = sorted(
                [{"genre": name, "count": data["count"], "playtime_hours": round(data["playtime"]/60, 1)}
                 for name, data in genre_stats.items()],
                key=lambda x: x["playtime_hours"],
                reverse=True
            )[:10]
            
            stats_data = {
                "user": user.persona_name,
                "steam_id": user.steam_id,
                "total_games": total_games,
                "games_played": played_games,
                "games_unplayed": total_games - played_games,
                "completion_rate": round(played_games / max(total_games, 1) * 100, 1),
                "total_playtime_hours": round(total_playtime / 60, 1),
                "recent_playtime_hours": round(recent_playtime / 60, 1),
                "average_playtime_hours": round(total_playtime / 60 / max(played_games, 1), 1),
                "top_genres": top_genres
            }
            
            return json.dumps(stats_data, indent=2)
            
    except Exception as e:
        return json.dumps({"error": f"Failed to get user stats: {str(e)}"})


@mcp.resource("library://genres")
def available_genres() -> str:
    """Get list of all available genres with game counts."""
    try:
        with get_db() as session:
            genres = session.query(Genre).all()
            
            genre_list = []
            for genre in genres:
                game_count = len(genre.games)
                if game_count > 0:  # Only show genres that have games
                    genre_list.append({
                        "name": genre.genre_name,
                        "game_count": game_count
                    })
            
            # Sort by game count
            genre_list.sort(key=lambda x: x["game_count"], reverse=True)
            
            genre_data = {
                "total_genres": len(genre_list),
                "genres": genre_list
            }
            return json.dumps(genre_data, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Failed to get genres: {str(e)}"})


@mcp.resource("library://genres/{genre_name}/games")
def get_games_by_genre(genre_name: str) -> str:
    """Get all games in a specific genre."""
    try:
        with get_db() as session:
            # Find the genre
            genre = session.query(Genre).filter(
                Genre.genre_name.ilike(f"%{genre_name}%")
            ).first()
            
            if not genre:
                return json.dumps({"error": f"Genre '{genre_name}' not found"})
            
            # Get games in this genre with basic info
            games = session.query(Game).options(
                joinedload(Game.developers),
                joinedload(Game.reviews)
            ).join(Game.genres).filter(Genre.genre_id == genre.genre_id).all()
            
            games_data = []
            for game in games:
                game_info = {
                    "app_id": game.app_id,
                    "name": game.name,
                    "release_date": game.release_date,
                    "developers": [d.developer_name for d in game.developers]
                }
                
                # Add review info if available
                if game.reviews and game.reviews.review_summary:
                    game_info["reviews"] = {
                        "summary": game.reviews.review_summary,
                        "positive_percentage": game.reviews.positive_percentage
                    }
                
                games_data.append(game_info)
            
            # Sort by name
            games_data.sort(key=lambda x: x["name"])
            
            genre_games_data = {
                "genre": genre.genre_name,
                "total_games": len(games_data),
                "games": games_data
            }
            
            return json.dumps(genre_games_data, indent=2)
            
    except Exception as e:
        return json.dumps({"error": f"Failed to get games by genre: {str(e)}"})


@mcp.resource("library://users")
def available_users() -> str:
    """Get list of all users in the database."""
    try:
        with get_db() as session:
            users = session.query(UserProfile).all()
            
            user_list = []
            for user in users:
                game_count = session.query(UserGame).filter_by(steam_id=user.steam_id).count()
                
                user_data = {
                    "steam_id": user.steam_id,
                    "persona_name": user.persona_name,
                    "game_count": game_count,
                    "steam_level": user.steam_level,
                    "is_default": (user.steam_id == config.default_user or 
                                 user.persona_name == config.default_user)
                }
                
                if user.loccountrycode:
                    user_data["location"] = user.loccountrycode
                    if user.locstatecode:
                        user_data["location"] += f"-{user.locstatecode}"
                
                user_list.append(user_data)
            
            users_data = {
                "total_users": len(user_list),
                "default_user": config.default_user,
                "users": user_list
            }
            return json.dumps(users_data, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Failed to get users: {str(e)}"})


@mcp.resource("config://settings")
def get_settings() -> str:
    """Get current server settings."""
    settings_data = {
        "server": "steam-librarian",
        "host": config.host,
        "port": config.port,
        "default_user": config.default_user,
        "database_type": config.database_url.split("://")[0],
        "debug": config.debug
    }
    return json.dumps(settings_data, indent=2)