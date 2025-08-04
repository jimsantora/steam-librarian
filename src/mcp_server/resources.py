"""MCP resources with full specification compliance including metadata and annotations"""

import json
from datetime import datetime
from typing import Any

from mcp.types import TextResourceContents
from sqlalchemy.orm import joinedload

from shared.database import (
    Category,
    Game,
    Genre,
    Tag,
    UserGame,
    UserProfile,
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


def create_resource_content(uri: str, name: str, title: str, description: str, data: dict[str, Any], priority: float = 0.5, audience: list[str] = None, mime_type: str = "application/json") -> TextResourceContents:
    """Create properly formatted resource content with metadata and annotations."""
    if audience is None:
        audience = ["user", "assistant"]

    # Annotations go in the meta field for MCP
    meta = {"audience": audience, "priority": priority, "lastModified": datetime.now().isoformat() + "Z", "name": name, "title": title, "description": description}

    return TextResourceContents(uri=uri, mimeType=mime_type, text=json.dumps(data, indent=2), _meta=meta)


def create_error_resource(uri: str, name: str, error_message: str) -> TextResourceContents:
    """Create error resource content with appropriate metadata."""
    return create_resource_content(uri=uri, name=name, title="Resource Error", description=f"Error accessing resource: {error_message}", data={"error": error_message}, priority=0.1, audience=["assistant"])


@mcp.resource("library://games/{game_id}")
def get_game_details(game_id: str) -> TextResourceContents:
    """Get comprehensive game details by ID with all available metadata."""
    uri = f"library://games/{game_id}"
    name = f"game_{game_id}"

    try:
        # Try to get default user for personalized stats
        user_steam_id = None
        user_result = resolve_user_for_tool(None, get_default_user_fallback)
        if "error" not in user_result:
            user_steam_id = user_result["steam_id"]

        with get_db() as session:
            # Load game with all relationships
            game = session.query(Game).options(joinedload(Game.genres), joinedload(Game.developers), joinedload(Game.publishers), joinedload(Game.categories), joinedload(Game.reviews), joinedload(Game.tags)).filter_by(app_id=int(game_id)).first()

            if not game:
                return create_error_resource(uri, name, f"Game with ID {game_id} not found")

            # Build comprehensive game data
            game_data = {
                "id": game.app_id,
                "name": game.name,
                "short_description": game.short_description,
                "about_the_game": game.about_the_game,
                # Release Information
                "release_date": game.release_date,
                "developers": [d.developer_name for d in game.developers],
                "publishers": [p.publisher_name for p in game.publishers],
                # Classification & Ratings
                "genres": [g.genre_name for g in game.genres],
                "categories": [c.category_name for c in game.categories],
                "tags": [t.tag_name for t in game.tags],
                "required_age": game.required_age,
                "esrb_rating": game.esrb_rating,
                "esrb_descriptors": game.esrb_descriptors,
                "pegi_rating": game.pegi_rating,
                "pegi_descriptors": game.pegi_descriptors,
                # Platform Support
                "platforms": {"windows": game.platforms_windows, "mac": game.platforms_mac, "linux": game.platforms_linux},
                "vr_support": game.vr_support,
                "controller_support": game.controller_support,
                # Scores & Reviews
                "metacritic_score": game.metacritic_score,
                "metacritic_url": game.metacritic_url,
            }

            # Add detailed review data if available
            if game.reviews:
                game_data["reviews"] = {"summary": game.reviews.review_summary, "score": game.reviews.review_score, "total_reviews": game.reviews.total_reviews, "positive_reviews": game.reviews.positive_reviews, "negative_reviews": game.reviews.negative_reviews, "positive_percentage": game.reviews.positive_percentage, "review_score_desc": game.reviews.review_score_desc}

            # Add user-specific data if available
            if user_steam_id:
                user_game = session.query(UserGame).filter_by(steam_id=user_steam_id, app_id=game.app_id).first()

                if user_game:
                    game_data["user_stats"] = {"owned": True, "playtime_forever_minutes": user_game.playtime_forever, "playtime_forever_hours": round(user_game.playtime_forever / 60, 2), "playtime_2weeks_minutes": user_game.playtime_2weeks, "playtime_2weeks_hours": round(user_game.playtime_2weeks / 60, 2), "last_played": user_game.last_played, "achievements_total": user_game.achievements_total, "achievements_unlocked": user_game.achievements_unlocked, "achievement_percentage": round((user_game.achievements_unlocked / max(user_game.achievements_total, 1)) * 100, 1) if user_game.achievements_total else 0}
                else:
                    game_data["user_stats"] = {"owned": False, "note": "Game not in user's library"}
            else:
                game_data["user_stats"] = {"note": "No user context available for personalized stats"}

            return create_resource_content(uri=uri, name=name, title=f"Game Details: {game.name}", description=f"Complete metadata for {game.name} including ratings, genres, playtime, and user statistics", data=game_data, priority=0.8, audience=["user", "assistant"])  # High priority for game details

    except Exception as e:
        return create_error_resource(uri, name, f"Failed to get game details: {str(e)}")


@mcp.resource("library://overview")
def library_overview() -> TextResourceContents:
    """Get library overview with navigation to user-specific resources."""
    uri = "library://overview"
    name = "library_overview"

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
                    default_user_info = {"persona_name": user.persona_name, "steam_id": user.steam_id, "game_count": game_count}

            # Get top genres across all games
            genres = session.query(Genre).all()
            genre_counts = []
            for genre in genres:
                count = len(genre.games)
                if count > 0:
                    genre_counts.append({"genre": genre.genre_name, "count": count})

            genre_counts.sort(key=lambda x: x["count"], reverse=True)

            overview = {"message": "Steam Library MCP Server Overview", "statistics": {"total_games": total_games, "total_users": total_users, "total_genres": total_genres}, "default_user": default_user_info, "top_genres": genre_counts[:10], "available_resources": {"users": "library://users - List all users", "user_profile": "library://users/{user_id} - Get user profile (use 'default' for default user)", "user_games": "library://users/{user_id}/games - Get user's complete game library", "user_stats": "library://users/{user_id}/stats - Get user's gaming statistics", "game_details": "library://games/{game_id} - Get detailed game information", "platform_games": "library://games/platform/{platform} - Games by platform (windows/mac/linux/vr)", "multiplayer_games": "library://games/multiplayer/{type} - Games by multiplayer type (coop/pvp/local/online)", "unplayed_games": "library://games/unplayed - Highly-rated unplayed games", "genres": "library://genres - List all genres", "games_by_genre": "library://genres/{genre_name}/games - Get games in specific genre", "tags": "library://tags - List all community tags", "games_by_tag": "library://tags/{tag_name} - Get games with specific tag"}, "tools_available": ["search_games - Natural language search with AI interpretation", "analyze_library - Deep analysis with AI-generated insights", "generate_recommendation - AI-powered game recommendations", "find_games_with_preferences - Interactive preference-based search with elicitation", "find_family_games - Age-appropriate games with ESRB/PEGI filtering", "find_quick_session_games - Smart tag-based analysis for quick sessions"]}

            return create_resource_content(uri=uri, name=name, title="Steam Library Overview", description="Complete library statistics, user information, and available resources navigation", data=overview, priority=0.9, audience=["user", "assistant"])  # Very high priority for overview

    except Exception as e:
        return create_error_resource(uri, name, f"Failed to get overview: {str(e)}")


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
            user = session.query(UserProfile).filter((UserProfile.steam_id == resolved_user_id) | (UserProfile.persona_name.ilike(resolved_user_id))).first()

            if not user:
                return json.dumps({"error": f"User '{user_id}' not found"})

            # Get game count
            game_count = session.query(UserGame).filter_by(steam_id=user.steam_id).count()

            user_data = {"steam_id": user.steam_id, "persona_name": user.persona_name, "profile_url": user.profile_url, "avatar_url": user.avatar_url, "avatarmedium": user.avatarmedium, "avatarfull": user.avatarfull, "steam_level": user.steam_level, "xp": user.xp, "time_created": user.time_created, "location": {"country": user.loccountrycode, "state": user.locstatecode}, "game_count": game_count, "last_updated": user.last_updated, "is_default": user.steam_id == config.default_user or user.persona_name == config.default_user}

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
            user = session.query(UserProfile).filter((UserProfile.steam_id == resolved_user_id) | (UserProfile.persona_name.ilike(resolved_user_id))).first()

            if not user:
                return json.dumps({"error": f"User '{user_id}' not found"})

            # Get user's games with details
            user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.developers)).filter(UserGame.steam_id == user.steam_id).all()

            games_data = []
            for ug in user_games:
                games_data.append({"app_id": ug.game.app_id, "name": ug.game.name, "playtime_forever_minutes": ug.playtime_forever, "playtime_forever_hours": ug.playtime_hours, "playtime_2weeks_minutes": ug.playtime_2weeks, "playtime_2weeks_hours": ug.playtime_2weeks_hours, "genres": [g.genre_name for g in ug.game.genres], "developers": [d.developer_name for d in ug.game.developers], "release_date": ug.game.release_date})

            # Sort by playtime descending
            games_data.sort(key=lambda x: x["playtime_forever_minutes"], reverse=True)

            library_data = {"user": user.persona_name, "steam_id": user.steam_id, "total_games": len(games_data), "games": games_data}

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
            user = session.query(UserProfile).filter((UserProfile.steam_id == resolved_user_id) | (UserProfile.persona_name.ilike(resolved_user_id))).first()

            if not user:
                return json.dumps({"error": f"User '{user_id}' not found"})

            # Get user's games with genres
            user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres)).filter(UserGame.steam_id == user.steam_id).all()

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
            top_genres = sorted([{"genre": name, "count": data["count"], "playtime_hours": round(data["playtime"] / 60, 1)} for name, data in genre_stats.items()], key=lambda x: x["playtime_hours"], reverse=True)[:10]

            stats_data = {"user": user.persona_name, "steam_id": user.steam_id, "total_games": total_games, "games_played": played_games, "games_unplayed": total_games - played_games, "completion_rate": round(played_games / max(total_games, 1) * 100, 1), "total_playtime_hours": round(total_playtime / 60, 1), "recent_playtime_hours": round(recent_playtime / 60, 1), "average_playtime_hours": round(total_playtime / 60 / max(played_games, 1), 1), "top_genres": top_genres}

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
                    genre_list.append({"name": genre.genre_name, "game_count": game_count})

            # Sort by game count
            genre_list.sort(key=lambda x: x["game_count"], reverse=True)

            genre_data = {"total_genres": len(genre_list), "genres": genre_list}
            return json.dumps(genre_data, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get genres: {str(e)}"})


@mcp.resource("library://genres/{genre_name}/games")
def get_games_by_genre(genre_name: str) -> str:
    """Get all games in a specific genre."""
    try:
        with get_db() as session:
            # Find the genre
            genre = session.query(Genre).filter(Genre.genre_name.ilike(f"%{genre_name}%")).first()

            if not genre:
                return json.dumps({"error": f"Genre '{genre_name}' not found"})

            # Get games in this genre with basic info
            games = session.query(Game).options(joinedload(Game.developers), joinedload(Game.reviews)).join(Game.genres).filter(Genre.genre_id == genre.genre_id).all()

            games_data = []
            for game in games:
                game_info = {"app_id": game.app_id, "name": game.name, "release_date": game.release_date, "developers": [d.developer_name for d in game.developers]}

                # Add review info if available
                if game.reviews and game.reviews.review_summary:
                    game_info["reviews"] = {"summary": game.reviews.review_summary, "positive_percentage": game.reviews.positive_percentage}

                games_data.append(game_info)

            # Sort by name
            games_data.sort(key=lambda x: x["name"])

            genre_games_data = {"genre": genre.genre_name, "total_games": len(games_data), "games": games_data}

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

                user_data = {"steam_id": user.steam_id, "persona_name": user.persona_name, "game_count": game_count, "steam_level": user.steam_level, "is_default": (user.steam_id == config.default_user or user.persona_name == config.default_user)}

                if user.loccountrycode:
                    user_data["location"] = user.loccountrycode
                    if user.locstatecode:
                        user_data["location"] += f"-{user.locstatecode}"

                user_list.append(user_data)

            users_data = {"total_users": len(user_list), "default_user": config.default_user, "users": user_list}
            return json.dumps(users_data, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get users: {str(e)}"})


@mcp.resource("library://tags")
def available_tags() -> str:
    """Get list of all available user-generated tags with game counts."""
    try:
        with get_db() as session:
            tags = session.query(Tag).all()

            tag_list = []
            for tag in tags:
                game_count = len(tag.games)
                if game_count > 0:  # Only include tags that have games
                    tag_list.append({"name": tag.tag_name, "game_count": game_count})

            # Sort by game count (most popular first)
            tag_list.sort(key=lambda x: x["game_count"], reverse=True)

            tag_data = {"total_tags": len(tag_list), "tags": tag_list}
            return json.dumps(tag_data, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get tags: {str(e)}"})


@mcp.resource("library://tags/{tag_name}")
def get_games_by_tag(tag_name: str) -> str:
    """Get all games that have a specific user-generated tag."""
    try:
        with get_db() as session:
            # Find tag (case-insensitive partial match)
            tag = session.query(Tag).filter(Tag.tag_name.ilike(f"%{tag_name}%")).first()

            if not tag:
                return json.dumps({"error": f"Tag '{tag_name}' not found"})

            # Get games with this tag with basic info
            games = session.query(Game).options(joinedload(Game.developers), joinedload(Game.reviews), joinedload(Game.genres)).join(Game.tags).filter(Tag.tag_id == tag.tag_id).all()

            games_data = []
            for game in games:
                game_info = {"id": game.app_id, "name": game.name, "release_date": game.release_date, "developers": [d.developer_name for d in game.developers], "genres": [g.genre_name for g in game.genres]}

                # Add review info if available
                if game.reviews and game.reviews.review_summary:
                    game_info["reviews"] = {"summary": game.reviews.review_summary, "positive_percentage": game.reviews.positive_percentage}

                games_data.append(game_info)

            # Sort by name
            games_data.sort(key=lambda x: x["name"])

            tag_games_data = {"tag": tag.tag_name, "total_games": len(games_data), "games": games_data}

            return json.dumps(tag_games_data, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get games by tag: {str(e)}"})


@mcp.resource("library://games/platform/{platform}")
def get_games_by_platform(platform: str) -> str:
    """Get games compatible with specific platform (windows, mac, linux, vr)."""
    try:
        # Use default user for personal library context
        user_result = resolve_user_for_tool(None, get_default_user_fallback)
        if "error" in user_result:
            return json.dumps({"error": f"User error: {user_result['message']}"})

        user_steam_id = user_result["steam_id"]

        # Platform mapping
        platform_field_map = {"windows": "platforms_windows", "mac": "platforms_mac", "linux": "platforms_linux", "vr": "vr_support"}

        if platform not in platform_field_map:
            return json.dumps({"error": f"Invalid platform '{platform}'. Use: windows, mac, linux, or vr"})

        with get_db() as session:
            # Get user profile for display name
            user_profile = session.query(UserProfile).filter_by(steam_id=user_steam_id).first()
            if not user_profile:
                return json.dumps({"error": f"User profile not found for steam_id: {user_steam_id}"})

            platform_field = platform_field_map[platform]

            games_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).filter(getattr(Game, platform_field) is True).order_by(UserGame.playtime_forever.desc()).limit(50)

            games_data = []
            for game, user_game in games_query:
                game_info = {"id": game.app_id, "name": game.name, "playtime_hours": round(user_game.playtime_forever / 60, 1), "controller_support": game.controller_support, "release_date": game.release_date}
                games_data.append(game_info)

            platform_data = {"platform": platform, "user": user_profile.persona_name, "total_games": len(games_data), "games": games_data}

            return json.dumps(platform_data, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get games by platform: {str(e)}"})


@mcp.resource("library://games/multiplayer/{type}")
def get_multiplayer_games(type: str) -> str:
    """Get multiplayer games by type (coop, pvp, local, online)."""
    try:
        # Use default user for personal library context
        user_result = resolve_user_for_tool(None, get_default_user_fallback)
        if "error" in user_result:
            return json.dumps({"error": f"User error: {user_result['message']}"})

        user_steam_id = user_result["steam_id"]

        # Map type to category names
        type_to_categories = {"coop": ["Co-op", "Online Co-op"], "pvp": ["PvP", "Online PvP"], "local": ["Shared/Split Screen", "Local Co-op"], "online": ["Multi-player", "Online Multi-Player", "Online Co-op", "Online PvP"]}

        if type not in type_to_categories:
            return json.dumps({"error": f"Invalid type '{type}'. Use: coop, pvp, local, or online"})

        target_categories = type_to_categories[type]

        with get_db() as session:
            # Get user profile for display name
            user_profile = session.query(UserProfile).filter_by(steam_id=user_steam_id).first()
            if not user_profile:
                return json.dumps({"error": f"User profile not found for steam_id: {user_steam_id}"})

            # Find games with specified multiplayer type
            games_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).join(Game.categories).filter(Category.category_name.in_(target_categories)).distinct().limit(30)

            games_data = []
            for game, user_game in games_query:
                # Get all multiplayer categories for this game
                mp_categories = [c.category_name for c in game.categories if "player" in c.category_name.lower() or "co-op" in c.category_name.lower() or "pvp" in c.category_name.lower()]

                game_info = {"id": game.app_id, "name": game.name, "multiplayer_modes": mp_categories, "playtime_hours": round(user_game.playtime_forever / 60, 1), "release_date": game.release_date}
                games_data.append(game_info)

            multiplayer_data = {"multiplayer_type": type, "user": user_profile.persona_name, "total_games": len(games_data), "games": games_data}

            return json.dumps(multiplayer_data, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get multiplayer games: {str(e)}"})


@mcp.resource("library://games/unplayed")
def get_unplayed_gems() -> TextResourceContents:
    """Get highly-rated unplayed games (default min_rating=75)."""
    uri = "library://games/unplayed"
    name = "unplayed_games"

    try:
        # Use default user for personal library context
        user_result = resolve_user_for_tool(None, get_default_user_fallback)
        if "error" in user_result:
            return create_error_resource(uri, name, f"User error: {user_result['message']}")

        user_steam_id = user_result["steam_id"]
        min_rating = 75  # Default rating threshold

        with get_db() as session:
            # Get user profile for display name
            user_profile = session.query(UserProfile).filter_by(steam_id=user_steam_id).first()
            if not user_profile:
                return json.dumps({"error": f"User profile not found for steam_id: {user_steam_id}"})

            # Find unplayed games with high ratings
            unplayed_games = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).filter(UserGame.playtime_forever == 0, Game.metacritic_score >= min_rating).order_by(Game.metacritic_score.desc()).limit(20)  # Never played

            games_data = []
            for game, _user_game in unplayed_games:
                genre_names = [g.genre_name for g in game.genres[:3]]

                game_info = {"id": game.app_id, "name": game.name, "metacritic_score": game.metacritic_score, "genres": genre_names, "short_description": game.short_description[:150] + "..." if game.short_description and len(game.short_description) > 150 else game.short_description, "release_date": game.release_date}
                games_data.append(game_info)

            unplayed_data = {"user": user_profile.persona_name, "min_rating": min_rating, "total_games": len(games_data), "games": games_data}

            return create_resource_content(uri=uri, name=name, title="Highly-Rated Unplayed Games", description=f"Unplayed games in your library with Metacritic score ≥{min_rating} - perfect for discovering hidden gems", data=unplayed_data, priority=0.9, audience=["user", "assistant"])  # Very high priority for recommendations

    except Exception as e:
        return create_error_resource(uri, name, f"Failed to get unplayed gems: {str(e)}")
