"""
Tools-only MCP server implementation.

This module contains all the tools that replace the functionality of resources,
completions, elicitations, and sampling from the full MCP server. Each tool
includes instructive error messages that guide LLMs to discover required parameters.
"""

import json
import os
import re

# Import shared database utilities
import sys

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import joinedload

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from oops_all_tools.config import config, get_default_user_fallback
from oops_all_tools.server import mcp
from shared.database import (
    Category,
    Game,
    Genre,
    UserGame,
    UserProfile,
    get_db,
    resolve_user_for_tool,
)


def is_natural_language_query(query: str) -> bool:
    """Check if query is natural language vs simple keywords."""
    nl_indicators = ["something", "games like", "similar to", "after work", "relaxing", "exciting", "with friends", "for kids"]
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in nl_indicators)


def parse_natural_language_filters(text: str) -> dict:
    """Parse natural language filters into structured format."""
    filters = {}

    # Genre detection
    genres = ["Action", "Adventure", "RPG", "Strategy", "Indie", "Casual", "Simulation", "Sports", "Racing", "Puzzle"]
    for genre in genres:
        if genre.lower() in text.lower():
            filters["genres"] = [genre]
            break

    # Rating detection
    rating_patterns = [
        r"rating\s*(?:above|over|>=?)\s*(\d+)",
        r"rated\s*(?:above|over|>=?)\s*(\d+)",
        r"(?:rating|rated)\s*>=?\s*(\d+)",
        r"(?:min|minimum)\s*rating\s*(\d+)",
    ]

    for pattern in rating_patterns:
        rating_match = re.search(pattern, text, re.I)
        if rating_match:
            filters["min_rating"] = int(rating_match.group(1))
            break

    # Multiplayer detection
    if any(word in text.lower() for word in ["coop", "co-op", "cooperative"]):
        filters["categories"] = ["Co-op"]
    elif "pvp" in text.lower():
        filters["categories"] = ["PvP"]
    elif "multiplayer" in text.lower():
        filters["categories"] = ["Multi-player"]

    # Platform detection
    if "vr" in text.lower():
        filters["vr_support"] = True

    # Playtime detection
    if any(word in text.lower() for word in ["unplayed", "never played"]):
        filters["playtime"] = 0

    return filters


# ============================================================================
# SEARCH & DISCOVERY TOOLS
# ============================================================================


@mcp.tool()
async def search_games(query: str, filters: str | None = None, limit: int = 25, user: str | None = None) -> str:
    """
    Search for games using natural language or structured queries.

    Args:
        query: Search text (e.g., "action RPG games" or "Portal")
        filters: Optional JSON filters or natural language (e.g., '{"genres": ["Action"], "min_rating": 80}')
        limit: Maximum results (default: 25)
        user: User ID (defaults to default user)

    Returns:
        JSON list of matching games with details
    """
    if not query or not query.strip():
        return json.dumps({"error": "Missing required parameter: query", "help": "Provide a search query like 'Portal' or 'action RPG games'", "examples": ["search_games(query='Portal')", "search_games(query='action games rated above 80')", "search_games(query='multiplayer indie games')"]}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to check available users or set DEFAULT_USER"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Build base query
            query_obj = session.query(Game).join(UserGame).filter(UserGame.user_steam_id == user_steam_id).options(joinedload(Game.genres), joinedload(Game.categories), joinedload(Game.tags))

            # Apply text search
            if query:
                search_terms = query.lower().split()
                for term in search_terms:
                    query_obj = query_obj.filter(or_(Game.name.ilike(f"%{term}%"), Game.short_description.ilike(f"%{term}%")))

            # Apply filters if provided
            if filters:
                try:
                    if filters.startswith("{"):
                        # JSON filters
                        filter_dict = json.loads(filters)
                    else:
                        # Natural language filters
                        filter_dict = parse_natural_language_filters(filters)

                    # Apply genre filters
                    if "genres" in filter_dict:
                        query_obj = query_obj.join(Game.genres).filter(Genre.genre_name.in_(filter_dict["genres"]))

                    # Apply rating filter
                    if "min_rating" in filter_dict:
                        min_rating = filter_dict["min_rating"]
                        query_obj = query_obj.filter(Game.metacritic_score >= min_rating)

                    # Apply category filters
                    if "categories" in filter_dict:
                        query_obj = query_obj.join(Game.categories).filter(Category.category_name.in_(filter_dict["categories"]))

                except json.JSONDecodeError:
                    return json.dumps({"error": "Invalid filters format", "help": 'Use JSON format like \'{"genres": ["Action"], "min_rating": 80}\' or natural language', "example": "search_games(query='Portal', filters='{\"min_rating\": 85}')"}, indent=2)

            # Execute query
            games = query_obj.limit(limit).all()

            # Format results
            results = []
            for game in games:
                user_game = next((ug for ug in game.user_games if ug.user_steam_id == user_steam_id), None)
                results.append({"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "categories": [c.category_name for c in game.categories], "rating": game.metacritic_score, "playtime": user_game.playtime_forever if user_game else 0, "short_description": game.short_description[:200] + "..." if game.short_description and len(game.short_description) > 200 else game.short_description})

            return json.dumps({"results": results, "count": len(results), "query": query, "filters_applied": filters if filters else None}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}", "help": "Try a simpler query or check if the database is accessible"}, indent=2)


@mcp.tool()
async def get_game_details(game_id: int | None = None, game_name: str | None = None, include_reviews: bool = False, include_tags: bool = True, user: str | None = None) -> str:
    """
    Get detailed information about a specific game.

    Args:
        game_id: Steam App ID (e.g., 440 for Team Fortress 2)
        game_name: Game name (alternative to game_id)
        include_reviews: Include review data
        include_tags: Include tag information
        user: User ID (defaults to default user)

    Returns:
        JSON object with complete game information
    """
    if not game_id and not game_name:
        return json.dumps({"error": "Missing required parameter: game_id or game_name", "help": "Provide either a game_id or game_name to look up", "discover_game_id": ["Use search_games(query='game name') to find the game_id", "Use get_user_games() to list all games with their IDs"], "examples": ["get_game_details(game_id=440)", "get_game_details(game_name='Portal 2')", "First: search_games(query='Portal'), then use the game_id from results"]}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to check available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Find game by ID or name
            if game_id:
                game = session.query(Game).filter(Game.appid == game_id).first()
            else:
                game = session.query(Game).filter(Game.name.ilike(f"%{game_name}%")).first()

            if not game:
                search_suggestion = f"search_games(query='{game_name or game_id}')"
                return json.dumps({"error": f"Game not found: {game_name or game_id}", "help": f"Try using {search_suggestion} to find the correct game", "alternative": "Use get_user_games() to see all available games"}, indent=2)

            # Get user-specific data
            user_game = session.query(UserGame).filter(and_(UserGame.user_steam_id == user_steam_id, UserGame.appid == game.appid)).first()

            # Build detailed response
            details = {"game_id": game.appid, "name": game.name, "short_description": game.short_description, "about_the_game": game.about_the_game, "genres": [g.genre_name for g in game.genres], "categories": [c.category_name for c in game.categories], "developers": [d.developer_name for d in game.developers], "publishers": [p.publisher_name for p in game.publishers], "release_date": game.release_date.isoformat() if game.release_date else None, "metacritic_score": game.metacritic_score, "platforms": {"windows": game.windows, "mac": game.mac, "linux": game.linux}, "price": {"initial": game.price_initial, "final": game.price_final, "discount_percent": game.discount_percent}}

            # Add user-specific data
            if user_game:
                details["user_data"] = {"owned": True, "playtime_forever": user_game.playtime_forever, "playtime_2weeks": user_game.playtime_2weeks, "last_played": user_game.last_played.isoformat() if user_game.last_played else None, "achievements_total": user_game.achievements_total, "achievements_unlocked": user_game.achievements_unlocked}
            else:
                details["user_data"] = {"owned": False}

            # Add tags if requested
            if include_tags:
                details["tags"] = [t.tag_name for t in game.tags]

            # Add reviews if requested
            if include_reviews:
                details["reviews"] = [{"author": r.author, "helpful": r.helpful, "funny": r.funny, "hours_on_record": r.hours_on_record, "review": r.review[:500] + "..." if len(r.review) > 500 else r.review} for r in game.reviews[:5]]  # Limit to 5 reviews

            return json.dumps(details, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get game details: {str(e)}", "help": "Check if the game_id is valid or try searching by name first"}, indent=2)


@mcp.tool()
async def find_similar_games(game_id: int | None = None, game_name: str | None = None, similarity_factors: list[str] = None, limit: int = 10, user: str | None = None) -> str:
    """
    Find games similar to a specified game.

    Args:
        game_id: Steam App ID of the reference game
        game_name: Name of the reference game (alternative to game_id)
        similarity_factors: What to match on (genre, tags, developer, publisher)
        limit: Maximum results (default: 10)
        user: User ID (defaults to default user)

    Returns:
        JSON list of similar games ranked by similarity
    """
    if similarity_factors is None:
        similarity_factors = ["genre", "tags", "developer"]
    if not game_id and not game_name:
        return json.dumps({"error": "Missing required parameter: game_id or game_name", "help": "Specify which game to find similar games to", "discover_game_id": ["Use search_games(query='game name') to find the game_id", "Use get_user_games() to list all your games with IDs"], "examples": ["find_similar_games(game_id=440)", "find_similar_games(game_name='Portal 2')", "find_similar_games(game_id=440, similarity_factors=['genre', 'tags'])"]}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to check available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Find reference game
            if game_id:
                ref_game = session.query(Game).filter(Game.appid == game_id).first()
            else:
                ref_game = session.query(Game).filter(Game.name.ilike(f"%{game_name}%")).first()

            if not ref_game:
                return json.dumps({"error": f"Reference game not found: {game_name or game_id}", "help": "Use search_games() to find the correct game first", "example": f"search_games(query='{game_name or game_id}')"}, indent=2)

            # Get user's games for similarity matching
            user_games_query = session.query(Game).join(UserGame).filter(UserGame.user_steam_id == user_steam_id, Game.appid != ref_game.appid).options(joinedload(Game.genres), joinedload(Game.categories), joinedload(Game.tags), joinedload(Game.developers), joinedload(Game.publishers))  # Exclude the reference game itself

            all_games = user_games_query.all()

            # Calculate similarity scores
            similar_games = []
            for game in all_games:
                score = 0
                matches = []

                # Genre similarity
                if "genre" in similarity_factors:
                    ref_genres = {g.genre_name for g in ref_game.genres}
                    game_genres = {g.genre_name for g in game.genres}
                    genre_overlap = len(ref_genres & game_genres)
                    if genre_overlap > 0:
                        score += genre_overlap * 3
                        matches.append(f"{genre_overlap} shared genres")

                # Tag similarity
                if "tags" in similarity_factors:
                    ref_tags = {t.tag_name for t in ref_game.tags}
                    game_tags = {t.tag_name for t in game.tags}
                    tag_overlap = len(ref_tags & game_tags)
                    if tag_overlap > 0:
                        score += tag_overlap
                        matches.append(f"{tag_overlap} shared tags")

                # Developer similarity
                if "developer" in similarity_factors:
                    ref_devs = {d.developer_name for d in ref_game.developers}
                    game_devs = {d.developer_name for d in game.developers}
                    if ref_devs & game_devs:
                        score += 5
                        matches.append("same developer")

                # Publisher similarity
                if "publisher" in similarity_factors:
                    ref_pubs = {p.publisher_name for p in ref_game.publishers}
                    game_pubs = {p.publisher_name for p in game.publishers}
                    if ref_pubs & game_pubs:
                        score += 2
                        matches.append("same publisher")

                if score > 0:
                    similar_games.append({"game_id": game.appid, "name": game.name, "similarity_score": score, "matches": matches, "genres": [g.genre_name for g in game.genres], "metacritic_score": game.metacritic_score, "short_description": game.short_description[:150] + "..." if game.short_description and len(game.short_description) > 150 else game.short_description})

            # Sort by similarity score and limit results
            similar_games.sort(key=lambda x: x["similarity_score"], reverse=True)
            similar_games = similar_games[:limit]

            return json.dumps({"reference_game": {"game_id": ref_game.appid, "name": ref_game.name, "genres": [g.genre_name for g in ref_game.genres]}, "similar_games": similar_games, "similarity_factors": similarity_factors, "count": len(similar_games)}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to find similar games: {str(e)}", "help": "Try with a different game or check similarity_factors"}, indent=2)


# ============================================================================
# LIBRARY OVERVIEW TOOLS
# ============================================================================


@mcp.tool()
async def get_library_overview(user: str | None = None, include_stats: bool = True) -> str:
    """
    Get a comprehensive overview of the user's Steam library.

    Args:
        user: User ID (defaults to default user)
        include_stats: Include detailed statistics

    Returns:
        JSON object with library summary and statistics
    """
    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to check available users or set DEFAULT_USER in config"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Get basic counts
            total_games = session.query(UserGame).filter(UserGame.user_steam_id == user_steam_id).count()

            # Get games with playtime
            played_games = session.query(UserGame).filter(and_(UserGame.user_steam_id == user_steam_id, UserGame.playtime_forever > 0)).count()

            unplayed_games = total_games - played_games

            # Get total playtime
            total_playtime = session.query(func.sum(UserGame.playtime_forever)).filter(UserGame.user_steam_id == user_steam_id).scalar() or 0

            # Basic overview
            overview = {"user_steam_id": user_steam_id, "total_games": total_games, "played_games": played_games, "unplayed_games": unplayed_games, "total_playtime_minutes": total_playtime, "total_playtime_hours": round(total_playtime / 60, 1), "average_playtime_per_game": round(total_playtime / total_games, 1) if total_games > 0 else 0}

            if include_stats:
                # Genre breakdown
                genre_stats = session.query(Genre.genre_name, func.count(UserGame.appid).label("count")).join(Game.genres).join(UserGame).filter(UserGame.user_steam_id == user_steam_id).group_by(Genre.genre_name).order_by(func.count(UserGame.appid).desc()).limit(10).all()

                # Top played games
                top_games = session.query(Game, UserGame).join(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.playtime_forever > 0).order_by(UserGame.playtime_forever.desc()).limit(10).all()

                # Recent achievements
                recent_achievements = session.query(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.achievements_unlocked > 0).order_by(UserGame.achievements_unlocked.desc()).limit(5).all()

                overview["statistics"] = {"genres": [{"genre": genre, "count": count} for genre, count in genre_stats], "top_played_games": [{"name": game.name, "playtime_hours": round(user_game.playtime_forever / 60, 1), "game_id": game.appid} for game, user_game in top_games], "achievement_progress": [{"game_id": ug.appid, "achievements_unlocked": ug.achievements_unlocked, "achievements_total": ug.achievements_total, "completion_percent": round((ug.achievements_unlocked / ug.achievements_total * 100), 1) if ug.achievements_total > 0 else 0} for ug in recent_achievements]}

            return json.dumps(overview, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get library overview: {str(e)}", "help": "Check if user exists and database is accessible"}, indent=2)


@mcp.tool()
async def get_user_profile(user_id: str | None = None) -> str:
    """
    Get user profile information and metadata.

    Args:
        user_id: Steam user ID (if not provided, lists all users)

    Returns:
        JSON object with user profile data
    """
    try:
        with get_db() as session:
            if user_id:
                # Get specific user
                user = session.query(UserProfile).filter(UserProfile.steam_id == user_id).first()

                if not user:
                    return json.dumps({"error": f"User not found: {user_id}", "help": "Use get_user_profile() without parameters to see all available users", "example": "get_user_profile()"}, indent=2)

                profile = {"steam_id": user.steam_id, "personaname": user.personaname, "profileurl": user.profileurl, "avatar": user.avatar, "avatarmedium": user.avatarmedium, "avatarfull": user.avatarfull, "personastate": user.personastate, "communityvisibilitystate": user.communityvisibilitystate, "profilestate": user.profilestate, "lastlogoff": user.lastlogoff.isoformat() if user.lastlogoff else None, "commentpermission": user.commentpermission, "realname": user.realname, "primaryclanid": user.primaryclanid, "timecreated": user.timecreated.isoformat() if user.timecreated else None, "loccountrycode": user.loccountrycode, "locstatecode": user.locstatecode}

                return json.dumps(profile, indent=2)

            else:
                # List all users
                users = session.query(UserProfile).all()

                if not users:
                    return json.dumps({"error": "No users found in database", "help": "Run the Steam fetcher to populate user data", "command": "python src/fetcher/steam_library_fetcher.py"}, indent=2)

                user_list = [{"steam_id": user.steam_id, "personaname": user.personaname, "profileurl": user.profileurl, "is_default": user.steam_id == config.default_user} for user in users]

                return json.dumps({"users": user_list, "count": len(user_list), "default_user": config.default_user}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get user profile: {str(e)}", "help": "Check database connection and user data availability"}, indent=2)


@mcp.tool()
async def get_user_games(user_id: str | None = None, sort_by: str = "name", filter_played: bool | None = None, limit: int = 50) -> str:
    """
    Get a user's complete game collection.

    Args:
        user_id: Steam user ID (defaults to default user)
        sort_by: Sort order (name, playtime, recent, rating)
        filter_played: True for played only, False for unplayed only, None for all
        limit: Maximum results (default: 50)

    Returns:
        JSON list of user's games
    """
    # Resolve user
    user_result = resolve_user_for_tool(user_id, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users", "example": "get_user_profile()"}, indent=2)

    user_steam_id = user_result["steam_id"]

    # Validate sort_by parameter
    valid_sorts = ["name", "playtime", "recent", "rating"]
    if sort_by not in valid_sorts:
        return json.dumps({"error": f"Invalid sort_by: {sort_by}", "help": f"Use one of: {', '.join(valid_sorts)}", "example": "get_user_games(sort_by='playtime')"}, indent=2)

    try:
        with get_db() as session:
            # Build query
            query = session.query(Game, UserGame).join(UserGame).filter(UserGame.user_steam_id == user_steam_id).options(joinedload(Game.genres), joinedload(Game.categories))

            # Apply played filter
            if filter_played is True:
                query = query.filter(UserGame.playtime_forever > 0)
            elif filter_played is False:
                query = query.filter(UserGame.playtime_forever == 0)

            # Apply sorting
            if sort_by == "name":
                query = query.order_by(Game.name)
            elif sort_by == "playtime":
                query = query.order_by(UserGame.playtime_forever.desc())
            elif sort_by == "recent":
                query = query.order_by(UserGame.last_played.desc().nullslast())
            elif sort_by == "rating":
                query = query.order_by(Game.metacritic_score.desc().nullslast())

            # Execute with limit
            results = query.limit(limit).all()

            # Format results
            games = []
            for game, user_game in results:
                games.append({"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "categories": [c.category_name for c in game.categories[:5]], "playtime_forever": user_game.playtime_forever, "playtime_hours": round(user_game.playtime_forever / 60, 1), "playtime_2weeks": user_game.playtime_2weeks, "last_played": user_game.last_played.isoformat() if user_game.last_played else None, "metacritic_score": game.metacritic_score, "achievements": {"unlocked": user_game.achievements_unlocked, "total": user_game.achievements_total, "percentage": round((user_game.achievements_unlocked / user_game.achievements_total * 100), 1) if user_game.achievements_total > 0 else 0}})  # Limit categories

            return json.dumps({"games": games, "count": len(games), "user_steam_id": user_steam_id, "sort_by": sort_by, "filter_played": filter_played, "showing": f"{len(games)} of total games"}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get user games: {str(e)}", "help": "Check if user exists and has games in the database"}, indent=2)


@mcp.tool()
async def get_user_stats(user_id: str | None = None, time_range: str = "all") -> str:
    """
    Get detailed gaming statistics for a user.

    Args:
        user_id: Steam user ID (defaults to default user)
        time_range: Time period for stats (all, recent, last_month)

    Returns:
        JSON object with gaming statistics and insights
    """
    # Resolve user
    user_result = resolve_user_for_tool(user_id, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    # Validate time_range
    valid_ranges = ["all", "recent", "last_month"]
    if time_range not in valid_ranges:
        return json.dumps({"error": f"Invalid time_range: {time_range}", "help": f"Use one of: {', '.join(valid_ranges)}", "example": "get_user_stats(time_range='recent')"}, indent=2)

    try:
        with get_db() as session:
            # Base query for user games
            base_query = session.query(UserGame).filter(UserGame.user_steam_id == user_steam_id)

            # Apply time range filters (for recent stats)
            if time_range == "recent":
                # Focus on games with 2-week playtime
                base_query.filter(UserGame.playtime_2weeks > 0)
            else:
                pass

            # Calculate comprehensive stats
            total_games = base_query.count()
            played_games = base_query.filter(UserGame.playtime_forever > 0).count()

            # Playtime statistics
            total_playtime = base_query.with_entities(func.sum(UserGame.playtime_forever)).scalar() or 0

            if time_range == "recent":
                recent_playtime = base_query.with_entities(func.sum(UserGame.playtime_2weeks)).scalar() or 0
            else:
                recent_playtime = 0

            # Achievement statistics
            achievement_stats = base_query.with_entities(func.sum(UserGame.achievements_unlocked), func.sum(UserGame.achievements_total), func.count(UserGame.appid)).first()

            achievements_unlocked = achievement_stats[0] or 0
            achievements_total = achievement_stats[1] or 0
            games_with_achievements = base_query.filter(UserGame.achievements_total > 0).count()

            # Genre preferences
            genre_playtime = session.query(Genre.genre_name, func.sum(UserGame.playtime_forever).label("total_playtime")).join(Game.genres).join(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.playtime_forever > 0).group_by(Genre.genre_name).order_by(func.sum(UserGame.playtime_forever).desc()).limit(10).all()

            # Build stats response
            stats = {"user_steam_id": user_steam_id, "time_range": time_range, "library_summary": {"total_games": total_games, "played_games": played_games, "unplayed_games": total_games - played_games, "completion_rate": round((played_games / total_games * 100), 1) if total_games > 0 else 0}, "playtime_stats": {"total_minutes": total_playtime, "total_hours": round(total_playtime / 60, 1), "total_days": round(total_playtime / (60 * 24), 1), "average_per_game": round(total_playtime / total_games, 1) if total_games > 0 else 0, "average_per_played_game": round(total_playtime / played_games, 1) if played_games > 0 else 0}, "achievement_stats": {"total_unlocked": achievements_unlocked, "total_available": achievements_total, "completion_rate": round((achievements_unlocked / achievements_total * 100), 1) if achievements_total > 0 else 0, "games_with_achievements": games_with_achievements, "average_per_game": round(achievements_unlocked / games_with_achievements, 1) if games_with_achievements > 0 else 0}, "genre_preferences": [{"genre": genre, "playtime_minutes": int(playtime), "playtime_hours": round(playtime / 60, 1), "percentage_of_total": round((playtime / total_playtime * 100), 1) if total_playtime > 0 else 0} for genre, playtime in genre_playtime]}

            # Add recent activity if requested
            if time_range == "recent" and recent_playtime > 0:
                stats["recent_activity"] = {"playtime_2weeks_minutes": recent_playtime, "playtime_2weeks_hours": round(recent_playtime / 60, 1), "daily_average": round(recent_playtime / 14, 1)}

            return json.dumps(stats, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get user stats: {str(e)}", "help": "Check if user exists and has games in the database"}, indent=2)


# ============================================================================
# GENRE & CATEGORY TOOLS
# ============================================================================


@mcp.tool()
async def get_genres(include_counts: bool = True) -> str:
    """
    Get all available genres with optional game counts.

    Args:
        include_counts: Include number of games per genre

    Returns:
        JSON list of genres with metadata
    """
    try:
        with get_db() as session:
            if include_counts:
                # Get genres with game counts
                genre_data = session.query(Genre.genre_name, func.count(Game.appid).label("game_count")).join(Game.genres).group_by(Genre.genre_name).order_by(func.count(Game.appid).desc()).all()

                genres = [{"genre": genre_name, "game_count": game_count} for genre_name, game_count in genre_data]
            else:
                # Just genre names
                genre_names = session.query(Genre.genre_name).order_by(Genre.genre_name).all()
                genres = [{"genre": name[0]} for name in genre_names]

            return json.dumps({"genres": genres, "count": len(genres), "include_counts": include_counts}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get genres: {str(e)}", "help": "Check database connection"}, indent=2)


@mcp.tool()
async def get_games_by_genre(genre_name: str | None = None, user: str | None = None, sort_by: str = "name", limit: int = 25) -> str:
    """
    Get games in a specific genre.

    Args:
        genre_name: Genre to filter by (e.g., "Action", "RPG")
        user: User ID (defaults to default user)
        sort_by: Sort order (name, playtime, rating)
        limit: Maximum results (default: 25)

    Returns:
        JSON list of games in the specified genre
    """
    if not genre_name:
        # Get available genres to help the user
        try:
            with get_db() as session:
                available_genres = [g[0] for g in session.query(Genre.genre_name).order_by(Genre.genre_name).limit(15).all()]
        except Exception:
            available_genres = ["Action", "Adventure", "RPG", "Strategy", "Indie", "Casual"]

        return json.dumps({"error": "Missing required parameter: genre_name", "help": "Specify which genre to search for", "discover_genres": "Use get_genres() to see all available genres", "common_genres": available_genres, "examples": ["get_games_by_genre(genre_name='Action')", "get_games_by_genre(genre_name='RPG', sort_by='rating')"]}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    # Validate sort_by
    valid_sorts = ["name", "playtime", "rating"]
    if sort_by not in valid_sorts:
        return json.dumps({"error": f"Invalid sort_by: {sort_by}", "help": f"Use one of: {', '.join(valid_sorts)}", "example": "get_games_by_genre(genre_name='Action', sort_by='rating')"}, indent=2)

    try:
        with get_db() as session:
            # Verify genre exists
            genre_exists = session.query(Genre).filter(Genre.genre_name.ilike(genre_name)).first()

            if not genre_exists:
                # Suggest similar genres
                similar_genres = session.query(Genre.genre_name).filter(Genre.genre_name.ilike(f"%{genre_name}%")).limit(5).all()

                return json.dumps({"error": f"Genre not found: {genre_name}", "help": "Use get_genres() to see all valid genres", "suggestions": [g[0] for g in similar_genres] if similar_genres else [], "example": "get_genres()"}, indent=2)

            # Build query
            query = session.query(Game, UserGame).join(UserGame).join(Game.genres).filter(UserGame.user_steam_id == user_steam_id, Genre.genre_name.ilike(genre_name)).options(joinedload(Game.genres), joinedload(Game.categories))

            # Apply sorting
            if sort_by == "name":
                query = query.order_by(Game.name)
            elif sort_by == "playtime":
                query = query.order_by(UserGame.playtime_forever.desc())
            elif sort_by == "rating":
                query = query.order_by(Game.metacritic_score.desc().nullslast())

            # Execute with limit
            results = query.limit(limit).all()

            # Format results
            games = []
            for game, user_game in results:
                games.append({"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "categories": [c.category_name for c in game.categories[:3]], "playtime_hours": round(user_game.playtime_forever / 60, 1), "metacritic_score": game.metacritic_score, "short_description": game.short_description[:150] + "..." if game.short_description and len(game.short_description) > 150 else game.short_description})

            return json.dumps({"genre": genre_name, "games": games, "count": len(games), "user_steam_id": user_steam_id, "sort_by": sort_by}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get games by genre: {str(e)}", "help": "Check if genre name is correct and user has games in this genre"}, indent=2)


@mcp.tool()
async def get_categories(include_counts: bool = True, category_type: str = "all") -> str:
    """
    Get all available categories/features.

    Args:
        include_counts: Include number of games per category
        category_type: Filter by type (all, multiplayer, platform, features)

    Returns:
        JSON list of categories with metadata
    """
    try:
        with get_db() as session:
            # Base query
            query = session.query(Category.category_name)

            # Apply category type filtering
            if category_type == "multiplayer":
                multiplayer_terms = ["Multi-player", "Co-op", "PvP", "Online", "LAN"]
                query = query.filter(or_(*[Category.category_name.ilike(f"%{term}%") for term in multiplayer_terms]))
            elif category_type == "platform":
                platform_terms = ["Windows", "Mac", "Linux", "VR", "Steam"]
                query = query.filter(or_(*[Category.category_name.ilike(f"%{term}%") for term in platform_terms]))
            elif category_type == "features":
                # Exclude multiplayer and platform categories
                exclude_terms = ["Multi-player", "Co-op", "PvP", "Online", "LAN", "Windows", "Mac", "Linux", "VR"]
                for term in exclude_terms:
                    query = query.filter(~Category.category_name.ilike(f"%{term}%"))

            if include_counts:
                # Get categories with game counts
                category_data = query.add_columns(func.count(Game.appid).label("game_count")).join(Game.categories).group_by(Category.category_name).order_by(func.count(Game.appid).desc()).all()

                categories = [{"category": category_name, "game_count": game_count} for category_name, game_count in category_data]
            else:
                # Just category names
                category_names = query.order_by(Category.category_name).all()
                categories = [{"category": name[0]} for name in category_names]

            return json.dumps({"categories": categories, "count": len(categories), "category_type": category_type, "include_counts": include_counts, "filter_options": ["all", "multiplayer", "platform", "features"]}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get categories: {str(e)}", "help": "Check database connection"}, indent=2)


@mcp.tool()
async def get_games_by_category(category: str | None = None, user: str | None = None, limit: int = 25) -> str:
    """
    Get games with a specific category/feature.

    Args:
        category: Category to filter by (e.g., "Co-op", "VR Support")
        user: User ID (defaults to default user)
        limit: Maximum results (default: 25)

    Returns:
        JSON list of games with the specified category
    """
    if not category:
        return json.dumps({"error": "Missing required parameter: category", "help": "Specify which category to search for", "discover_categories": ["Use get_categories() to see all available categories", "Use get_categories(category_type='multiplayer') for multiplayer options", "Use get_categories(category_type='features') for game features"], "common_categories": ["Co-op", "Multi-player", "Single-player", "VR Support", "Controller Support"], "examples": ["get_games_by_category(category='Co-op')", "get_games_by_category(category='VR Support')"]}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Verify category exists
            category_exists = session.query(Category).filter(Category.category_name.ilike(f"%{category}%")).first()

            if not category_exists:
                # Suggest similar categories
                similar_categories = session.query(Category.category_name).filter(Category.category_name.ilike(f"%{category}%")).limit(5).all()

                return json.dumps({"error": f"Category not found: {category}", "help": "Use get_categories() to see all valid categories", "suggestions": [c[0] for c in similar_categories] if similar_categories else [], "example": "get_categories()"}, indent=2)

            # Build query
            results = session.query(Game, UserGame).join(UserGame).join(Game.categories).filter(UserGame.user_steam_id == user_steam_id, Category.category_name.ilike(f"%{category}%")).options(joinedload(Game.genres), joinedload(Game.categories)).order_by(Game.name).limit(limit).all()

            # Format results
            games = []
            for game, user_game in results:
                games.append({"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "categories": [c.category_name for c in game.categories if category.lower() in c.category_name.lower()][:3], "playtime_hours": round(user_game.playtime_forever / 60, 1), "metacritic_score": game.metacritic_score, "short_description": game.short_description[:150] + "..." if game.short_description and len(game.short_description) > 150 else game.short_description})

            return json.dumps({"category": category, "games": games, "count": len(games), "user_steam_id": user_steam_id}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get games by category: {str(e)}", "help": "Check if category name is correct and user has games with this category"}, indent=2)


# ============================================================================
# RECOMMENDATION & ANALYTICS TOOLS
# ============================================================================


@mcp.tool()
async def recommend_games(context: str | None = "general", preferences: str | None = None, limit: int = 10, user: str | None = None) -> str:
    """
    Get personalized game recommendations based on context and preferences.

    Args:
        context: Gaming context (general, after_work, social, family, solo)
        preferences: JSON string with preferences or natural language
        limit: Maximum recommendations (default: 10)
        user: User ID (defaults to default user)

    Returns:
        JSON list of recommended games with reasoning
    """
    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Get user's gaming patterns for better recommendations
            top_genres = session.query(Genre.genre_name, func.sum(UserGame.playtime_forever).label("total_playtime")).join(Game.genres).join(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.playtime_forever > 0).group_by(Genre.genre_name).order_by(func.sum(UserGame.playtime_forever).desc()).limit(5).all()

            # Parse preferences if provided
            pref_filters = {}
            if preferences:
                if preferences.startswith("{"):
                    try:
                        pref_filters = json.loads(preferences)
                    except json.JSONDecodeError:
                        pass
                else:
                    pref_filters = parse_natural_language_filters(preferences)

            # Build recommendation query based on context
            base_query = session.query(Game, UserGame).join(UserGame).filter(UserGame.user_steam_id == user_steam_id).options(joinedload(Game.genres), joinedload(Game.categories))

            # Apply context-specific filtering
            if context == "after_work":
                # Relaxing, shorter games
                base_query = base_query.join(Game.categories).filter(or_(Category.category_name.ilike("%Casual%"), Category.category_name.ilike("%Relaxing%"))).filter(UserGame.playtime_forever.between(0, 300))  # Less than 5 hours total
            elif context == "social":
                # Multiplayer games
                base_query = base_query.join(Game.categories).filter(or_(Category.category_name.ilike("%Co-op%"), Category.category_name.ilike("%Multi-player%")))
            elif context == "family":
                # Family-friendly games
                base_query = base_query.join(Game.genres).filter(Genre.genre_name.in_(["Casual", "Puzzle", "Simulation"]))
            elif context == "solo":
                # Single-player focused
                base_query = base_query.join(Game.categories).filter(Category.category_name.ilike("%Single-player%"))

            # Apply preference filters
            if "genres" in pref_filters:
                base_query = base_query.join(Game.genres).filter(Genre.genre_name.in_(pref_filters["genres"]))
            if "min_rating" in pref_filters:
                base_query = base_query.filter(Game.metacritic_score >= pref_filters["min_rating"])

            # Prioritize unplayed or lightly played games
            recommendations = base_query.filter(UserGame.playtime_forever < 60).order_by(Game.metacritic_score.desc().nullslast(), UserGame.playtime_forever.asc()).limit(limit).all()  # Less than 1 hour played

            # If not enough unplayed games, include some played games
            if len(recommendations) < limit:
                additional = base_query.filter(UserGame.playtime_forever >= 60).order_by(Game.metacritic_score.desc().nullslast()).limit(limit - len(recommendations)).all()
                recommendations.extend(additional)

            # Format recommendations with reasoning
            results = []
            for game, user_game in recommendations:
                # Generate reasoning based on user patterns and context
                reasons = []

                # Genre match with user preferences
                game_genres = {g.genre_name for g in game.genres}
                user_top_genres = {g[0] for g in top_genres[:3]}
                if game_genres & user_top_genres:
                    matching_genres = game_genres & user_top_genres
                    reasons.append(f"Matches your preferred genres: {', '.join(matching_genres)}")

                # Context-specific reasoning
                if context == "after_work" and user_game.playtime_forever < 300:
                    reasons.append("Perfect for relaxing after work - not too time-consuming")
                elif context == "social" and any("Co-op" in c.category_name or "Multi-player" in c.category_name for c in game.categories):
                    reasons.append("Great for playing with friends")
                elif context == "family" and any(g.genre_name in ["Casual", "Puzzle"] for g in game.genres):
                    reasons.append("Family-friendly and easy to learn")

                # Rating-based reasoning
                if game.metacritic_score and game.metacritic_score >= 80:
                    reasons.append(f"Highly rated ({game.metacritic_score}/100)")

                # Playtime-based reasoning
                if user_game.playtime_forever == 0:
                    reasons.append("Unplayed game in your library")
                elif user_game.playtime_forever < 60:
                    reasons.append("Barely played - worth revisiting")

                results.append({"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "metacritic_score": game.metacritic_score, "playtime_hours": round(user_game.playtime_forever / 60, 1), "reasoning": reasons[:3], "short_description": game.short_description[:150] + "..." if game.short_description and len(game.short_description) > 150 else game.short_description})  # Limit to top 3 reasons

            return json.dumps({"recommendations": results, "context": context, "preferences": preferences, "user_top_genres": [g[0] for g in top_genres[:3]], "count": len(results)}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to generate recommendations: {str(e)}", "help": "Try with different context or check if user has games in library"}, indent=2)


@mcp.tool()
async def find_family_games(child_age: int | None = None, content_preferences: list[str] = None, user: str | None = None) -> str:
    """
    Find age-appropriate games for family gaming.

    Args:
        child_age: Age of child (3-18, required for safety filtering)
        content_preferences: Content preferences (family_friendly, educational, no_violence, etc.)
        user: User ID (defaults to default user)

    Returns:
        JSON list of family-appropriate games
    """
    if content_preferences is None:
        content_preferences = ["family_friendly"]
    if child_age is None:
        return json.dumps({"error": "Missing required parameter: child_age", "help": "Specify child's age (3-18) for appropriate content filtering", "safety_note": "Age is required to ensure appropriate content recommendations", "examples": ["find_family_games(child_age=8)", "find_family_games(child_age=12, content_preferences=['educational', 'no_violence'])"]}, indent=2)

    if not (3 <= child_age <= 18):
        return json.dumps({"error": f"Invalid child_age: {child_age}", "help": "Child age must be between 3 and 18 years", "example": "find_family_games(child_age=10)"}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Build age-appropriate filtering
            query = session.query(Game, UserGame).join(UserGame).filter(UserGame.user_steam_id == user_steam_id).options(joinedload(Game.genres), joinedload(Game.categories))

            # Age-based genre filtering
            if child_age <= 8:
                # Very young children - highly restrictive
                safe_genres = ["Casual", "Education", "Simulation"]
                query = query.join(Game.genres).filter(Genre.genre_name.in_(safe_genres))
            elif child_age <= 12:
                # Older children - moderate filtering
                safe_genres = ["Casual", "Education", "Simulation", "Puzzle", "Sports", "Racing"]
                query = query.join(Game.genres).filter(Genre.genre_name.in_(safe_genres))
            else:
                # Teenagers - less restrictive but still family-focused
                avoid_genres = ["Action", "Adventure", "Strategy"]  # May contain violence
                query = query.join(Game.genres).filter(~Genre.genre_name.in_(avoid_genres))

            # Content preference filtering
            if "educational" in content_preferences:
                query = query.filter(or_(Game.name.ilike("%education%"), Game.name.ilike("%learning%"), Game.short_description.ilike("%educational%")))

            # Family-friendly categories
            family_categories = ["Family Sharing", "Single-player", "Local Co-op"]
            query = query.join(Game.categories).filter(Category.category_name.in_(family_categories))

            # Execute query
            results = query.order_by(Game.metacritic_score.desc().nullslast(), Game.name).limit(20).all()

            # Format family-friendly results
            games = []
            for game, user_game in results:
                # Safety assessment
                safety_factors = []

                if any(g.genre_name in ["Casual", "Education", "Puzzle"] for g in game.genres):
                    safety_factors.append("Safe genre")

                if any("Family Sharing" in c.category_name for c in game.categories):
                    safety_factors.append("Family Sharing enabled")

                if any("Local Co-op" in c.category_name for c in game.categories):
                    safety_factors.append("Local multiplayer - play together")

                games.append({"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "age_appropriateness": "Suitable" if len(safety_factors) >= 2 else "Review recommended", "safety_factors": safety_factors, "playtime_hours": round(user_game.playtime_forever / 60, 1), "metacritic_score": game.metacritic_score, "short_description": game.short_description[:150] + "..." if game.short_description and len(game.short_description) > 150 else game.short_description})

            return json.dumps({"family_games": games, "child_age": child_age, "content_preferences": content_preferences, "safety_note": "Games filtered for age-appropriate content", "recommendation": "Always review games before allowing children to play", "count": len(games)}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to find family games: {str(e)}", "help": "Check if user has family-appropriate games in library"}, indent=2)


@mcp.tool()
async def find_quick_games(session_length: str = "short", genre_preference: str | None = None, user: str | None = None) -> str:
    """
    Find games perfect for quick gaming sessions.

    Args:
        session_length: Session duration (short=15-30min, medium=30-60min, long=60min+)
        genre_preference: Preferred genre for the session
        user: User ID (defaults to default user)

    Returns:
        JSON list of games suitable for the specified time commitment
    """
    # Validate session length
    valid_lengths = ["short", "medium", "long"]
    if session_length not in valid_lengths:
        return json.dumps({"error": f"Invalid session_length: {session_length}", "help": f"Use one of: {', '.join(valid_lengths)}", "definitions": {"short": "15-30 minutes", "medium": "30-60 minutes", "long": "60+ minutes"}, "example": "find_quick_games(session_length='short', genre_preference='Puzzle')"}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Build base query
            query = session.query(Game, UserGame).join(UserGame).filter(UserGame.user_steam_id == user_steam_id).options(joinedload(Game.genres), joinedload(Game.categories))

            # Apply session length filtering based on game characteristics
            if session_length == "short":
                # Quick session games - casual, puzzle, arcade
                quick_genres = ["Casual", "Puzzle", "Racing", "Sports"]
                query = query.join(Game.genres).filter(Genre.genre_name.in_(quick_genres))
            elif session_length == "medium":
                # Medium session games - action, indie, simulation
                medium_genres = ["Action", "Indie", "Simulation", "Platformer"]
                query = query.join(Game.genres).filter(Genre.genre_name.in_(medium_genres))
            else:  # long
                # Long session games - RPG, strategy, adventure
                long_genres = ["RPG", "Strategy", "Adventure", "Survival"]
                query = query.join(Game.genres).filter(Genre.genre_name.in_(long_genres))

            # Apply genre preference if specified
            if genre_preference:
                # Verify genre exists
                genre_exists = session.query(Genre).filter(Genre.genre_name.ilike(genre_preference)).first()

                if not genre_exists:
                    return json.dumps({"error": f"Genre not found: {genre_preference}", "help": "Use get_genres() to see all available genres", "example": "get_genres()"}, indent=2)

                query = query.filter(Genre.genre_name.ilike(genre_preference))

            # Prioritize games the user can jump into quickly
            results = (
                query.order_by(
                    # Prefer games with some playtime (familiar mechanics)
                    case((UserGame.playtime_forever.between(60, 600), 1), else_=2).asc(),  # 1-10 hours
                    Game.metacritic_score.desc().nullslast(),
                    Game.name,
                )
                .limit(15)
                .all()
            )

            # Format results with session suitability info
            games = []
            for game, user_game in results:
                # Determine session suitability
                suitability_factors = []

                game_genres = [g.genre_name for g in game.genres]
                if session_length == "short" and any(g in ["Casual", "Puzzle", "Racing"] for g in game_genres):
                    suitability_factors.append("Quick to pick up and play")
                elif session_length == "medium" and any(g in ["Action", "Indie"] for g in game_genres):
                    suitability_factors.append("Perfect for medium sessions")
                elif session_length == "long" and any(g in ["RPG", "Strategy"] for g in game_genres):
                    suitability_factors.append("Deep gameplay for longer sessions")

                if 60 <= user_game.playtime_forever <= 600:  # 1-10 hours
                    suitability_factors.append("Familiar - easy to jump back in")
                elif user_game.playtime_forever == 0:
                    suitability_factors.append("New experience to try")

                games.append({"game_id": game.appid, "name": game.name, "genres": game_genres, "session_suitability": suitability_factors, "playtime_hours": round(user_game.playtime_forever / 60, 1), "metacritic_score": game.metacritic_score, "estimated_session_time": {"short": "15-30 min", "medium": "30-60 min", "long": "60+ min"}[session_length], "short_description": game.short_description[:120] + "..." if game.short_description and len(game.short_description) > 120 else game.short_description})

            return json.dumps({"quick_games": games, "session_length": session_length, "genre_preference": genre_preference, "count": len(games), "session_tips": {"short": "Perfect for breaks, commutes, or quick entertainment", "medium": "Good for evening relaxation or weekend gaming", "long": "Great for deep dives and immersive experiences"}[session_length]}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to find quick games: {str(e)}", "help": "Check session_length parameter and user's library"}, indent=2)


@mcp.tool()
async def get_unplayed_games(user: str | None = None, sort_by: str = "rating", include_reasons: bool = True) -> str:
    """
    Get games in library that haven't been played yet.

    Args:
        user: User ID (defaults to default user)
        sort_by: Sort order (rating, name, recent_purchase)
        include_reasons: Include reasons why these games might be good to try

    Returns:
        JSON list of unplayed games with recommendations
    """
    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    # Validate sort_by
    valid_sorts = ["rating", "name", "recent_purchase"]
    if sort_by not in valid_sorts:
        return json.dumps({"error": f"Invalid sort_by: {sort_by}", "help": f"Use one of: {', '.join(valid_sorts)}", "example": "get_unplayed_games(sort_by='rating')"}, indent=2)

    try:
        with get_db() as session:
            # Get unplayed games (0 playtime)
            query = session.query(Game, UserGame).join(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.playtime_forever == 0).options(joinedload(Game.genres), joinedload(Game.categories))

            # Apply sorting
            if sort_by == "rating":
                query = query.order_by(Game.metacritic_score.desc().nullslast(), Game.name)
            elif sort_by == "name":
                query = query.order_by(Game.name)
            # Note: recent_purchase would need purchase date data

            # Execute query
            results = query.limit(30).all()

            if not results:
                return json.dumps({"message": "No unplayed games found!", "achievement": "You've tried all your games - impressive!", "suggestion": "Consider getting some new games or revisiting old favorites", "alternative": "Use get_user_games(filter_played=True, sort_by='playtime') to find lightly played games"}, indent=2)

            # Get user's genre preferences for recommendations
            if include_reasons:
                top_genres = session.query(Genre.genre_name, func.sum(UserGame.playtime_forever).label("total_playtime")).join(Game.genres).join(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.playtime_forever > 0).group_by(Genre.genre_name).order_by(func.sum(UserGame.playtime_forever).desc()).limit(5).all()

                user_preferred_genres = {g[0] for g in top_genres}

            # Format results
            games = []
            for game, _user_game in results:
                game_entry = {"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "metacritic_score": game.metacritic_score, "categories": [c.category_name for c in game.categories[:3]], "short_description": game.short_description[:150] + "..." if game.short_description and len(game.short_description) > 150 else game.short_description}

                # Add reasons to try this game
                if include_reasons:
                    reasons = []

                    # Genre match with user preferences
                    game_genres = {g.genre_name for g in game.genres}
                    if game_genres & user_preferred_genres:
                        matching = game_genres & user_preferred_genres
                        reasons.append(f"Matches your favorite genres: {', '.join(matching)}")

                    # High rating
                    if game.metacritic_score and game.metacritic_score >= 80:
                        reasons.append(f"Highly rated ({game.metacritic_score}/100)")
                    elif game.metacritic_score and game.metacritic_score >= 70:
                        reasons.append(f"Well reviewed ({game.metacritic_score}/100)")

                    # Interesting categories
                    interesting_categories = ["Co-op", "VR Support", "Local Co-op", "Online Co-op"]
                    game_categories = [c.category_name for c in game.categories]
                    matching_categories = [c for c in game_categories if c in interesting_categories]
                    if matching_categories:
                        reasons.append(f"Has {matching_categories[0]} support")

                    # Default encouragement
                    if not reasons:
                        reasons.append("Hidden gem waiting to be discovered")

                    game_entry["reasons_to_try"] = reasons[:3]

                games.append(game_entry)

            return json.dumps({"unplayed_games": games, "count": len(games), "user_steam_id": user_steam_id, "sort_by": sort_by, "backlog_size": len(games), "encouragement": "Your gaming backlog is a treasure trove of experiences!", "tip": "Try starting with highly-rated games in your favorite genres"}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get unplayed games: {str(e)}", "help": "Check if user has games in library"}, indent=2)


# ============================================================================
# PLATFORM & FEATURE TOOLS
# ============================================================================


@mcp.tool()
async def get_platform_games(platform: str | None = None, user: str | None = None) -> str:
    """
    Get games available on a specific platform.

    Args:
        platform: Platform name (windows, mac, linux, steam_deck, vr)
        user: User ID (defaults to default user)

    Returns:
        JSON list of games available on the specified platform
    """
    if not platform:
        return json.dumps({"error": "Missing required parameter: platform", "help": "Specify which platform to search for", "available_platforms": ["windows", "mac", "linux", "steam_deck", "vr"], "examples": ["get_platform_games(platform='mac')", "get_platform_games(platform='steam_deck')"]}, indent=2)

    # Normalize platform name
    platform_lower = platform.lower()
    valid_platforms = ["windows", "mac", "linux", "steam_deck", "vr"]

    if platform_lower not in valid_platforms:
        return json.dumps({"error": f"Invalid platform: {platform}", "help": f"Use one of: {', '.join(valid_platforms)}", "example": "get_platform_games(platform='windows')"}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Build platform-specific query
            query = session.query(Game, UserGame).join(UserGame).filter(UserGame.user_steam_id == user_steam_id).options(joinedload(Game.genres), joinedload(Game.categories))

            # Apply platform filtering
            if platform_lower == "windows":
                query = query.filter(Game.windows is True)
            elif platform_lower == "mac":
                query = query.filter(Game.mac is True)
            elif platform_lower == "linux":
                query = query.filter(Game.linux is True)
            elif platform_lower == "steam_deck":
                # Steam Deck games - use categories for now
                query = query.join(Game.categories).filter(or_(Category.category_name.ilike("%Steam Deck%"), Category.category_name.ilike("%Deck Verified%"), Category.category_name.ilike("%Great on Deck%")))
            elif platform_lower == "vr":
                # VR games
                query = query.join(Game.categories).filter(Category.category_name.ilike("%VR%"))

            # Execute query
            results = query.order_by(Game.name).limit(50).all()

            # Format results
            games = []
            for game, user_game in results:
                # Platform compatibility info
                compatibility = {"windows": game.windows, "mac": game.mac, "linux": game.linux}

                # Special handling for VR and Steam Deck
                categories = [c.category_name for c in game.categories]
                if platform_lower == "vr":
                    vr_categories = [c for c in categories if "VR" in c]
                    compatibility["vr_support"] = vr_categories
                elif platform_lower == "steam_deck":
                    deck_categories = [c for c in categories if any(keyword in c for keyword in ["Steam Deck", "Deck", "Great on Deck"])]
                    compatibility["steam_deck_status"] = deck_categories

                games.append({"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "platform_compatibility": compatibility, "playtime_hours": round(user_game.playtime_forever / 60, 1), "metacritic_score": game.metacritic_score, "short_description": game.short_description[:150] + "..." if game.short_description and len(game.short_description) > 150 else game.short_description})

            platform_display = platform.replace("_", " ").title()
            return json.dumps({"platform": platform_display, "games": games, "count": len(games), "user_steam_id": user_steam_id, "compatibility_note": f"Games verified or compatible with {platform_display}"}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get platform games: {str(e)}", "help": "Check if platform name is correct"}, indent=2)


@mcp.tool()
async def get_multiplayer_games(multiplayer_type: str | None = None, user: str | None = None) -> str:
    """
    Get multiplayer games by type.

    Args:
        multiplayer_type: Type of multiplayer (co-op, pvp, online, local, lan)
        user: User ID (defaults to default user)

    Returns:
        JSON list of multiplayer games of the specified type
    """
    if not multiplayer_type:
        return json.dumps({"error": "Missing required parameter: multiplayer_type", "help": "Specify type of multiplayer games to find", "discover_multiplayer_types": "Use get_categories(category_type='multiplayer') to see all multiplayer options", "common_types": ["co-op", "pvp", "online", "local", "lan"], "examples": ["get_multiplayer_games(multiplayer_type='co-op')", "get_multiplayer_games(multiplayer_type='local')"]}, indent=2)

    # Normalize multiplayer type
    mp_type = multiplayer_type.lower()

    # Map user-friendly names to category patterns
    type_mapping = {"co-op": ["Co-op", "Online Co-op", "Local Co-op"], "coop": ["Co-op", "Online Co-op", "Local Co-op"], "pvp": ["PvP"], "online": ["Online", "Online Multi-Player", "Online Co-op", "Online PvP"], "local": ["Local Co-op", "Local Multi-Player", "Shared/Split Screen"], "lan": ["LAN"], "multiplayer": ["Multi-player", "Online Multi-Player"]}

    if mp_type not in type_mapping:
        return json.dumps({"error": f"Invalid multiplayer_type: {multiplayer_type}", "help": f"Use one of: {', '.join(type_mapping.keys())}", "discover": "Use get_categories(category_type='multiplayer') for all options", "example": "get_multiplayer_games(multiplayer_type='co-op')"}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Get category patterns for this multiplayer type
            category_patterns = type_mapping[mp_type]

            # Build query
            query = session.query(Game, UserGame).join(UserGame).join(Game.categories).filter(UserGame.user_steam_id == user_steam_id, or_(*[Category.category_name.ilike(f"%{pattern}%") for pattern in category_patterns])).options(joinedload(Game.genres), joinedload(Game.categories)).distinct()

            # Execute query
            results = query.order_by(Game.metacritic_score.desc().nullslast(), Game.name).limit(30).all()

            # Format results
            games = []
            for game, user_game in results:
                # Identify specific multiplayer features
                game_categories = [c.category_name for c in game.categories]
                multiplayer_features = []

                for category in game_categories:
                    if any(pattern.lower() in category.lower() for pattern in category_patterns):
                        multiplayer_features.append(category)

                games.append({"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "multiplayer_features": multiplayer_features, "playtime_hours": round(user_game.playtime_forever / 60, 1), "metacritic_score": game.metacritic_score, "social_recommendation": {"co-op": "Great for playing with friends cooperatively", "pvp": "Competitive multiplayer experience", "online": "Connect with players worldwide", "local": "Perfect for couch gaming with friends", "lan": "Ideal for LAN parties"}.get(mp_type, "Multiplayer gaming experience"), "short_description": game.short_description[:150] + "..." if game.short_description and len(game.short_description) > 150 else game.short_description})

            return json.dumps({"multiplayer_type": multiplayer_type, "games": games, "count": len(games), "user_steam_id": user_steam_id, "category_patterns": category_patterns, "social_gaming_tip": {"co-op": "Cooperative games are great for building teamwork", "pvp": "Competitive games can be intense - remember to have fun!", "local": "Local multiplayer is perfect for parties and gatherings"}.get(mp_type, "Multiplayer games are more fun with friends!")}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get multiplayer games: {str(e)}", "help": "Check if multiplayer_type is correct"}, indent=2)


@mcp.tool()
async def get_vr_games(vr_type: str = "any", user: str | None = None) -> str:
    """
    Get VR-compatible games.

    Args:
        vr_type: Type of VR experience (any, seated, room_scale, motion_controllers)
        user: User ID (defaults to default user)

    Returns:
        JSON list of VR games with requirements and recommendations
    """
    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    # Validate VR type
    valid_vr_types = ["any", "seated", "room_scale", "motion_controllers"]
    if vr_type not in valid_vr_types:
        return json.dumps({"error": f"Invalid vr_type: {vr_type}", "help": f"Use one of: {', '.join(valid_vr_types)}", "definitions": {"any": "All VR games", "seated": "Games playable while sitting", "room_scale": "Games requiring room-scale movement", "motion_controllers": "Games requiring hand controllers"}, "example": "get_vr_games(vr_type='seated')"}, indent=2)

    try:
        with get_db() as session:
            # Find VR games
            query = session.query(Game, UserGame).join(UserGame).join(Game.categories).filter(UserGame.user_steam_id == user_steam_id, Category.category_name.ilike("%VR%")).options(joinedload(Game.genres), joinedload(Game.categories)).distinct()

            # Apply VR type filtering based on categories
            if vr_type == "seated":
                # Look for seated VR indicators
                query = query.filter(or_(Category.category_name.ilike("%Seated%"), Category.category_name.ilike("%VR Supported%")))  # Usually seated-friendly
            elif vr_type == "room_scale":
                # Look for room-scale indicators
                query = query.filter(Category.category_name.ilike("%Room%"))
            elif vr_type == "motion_controllers":
                # Look for motion controller requirements
                query = query.filter(or_(Category.category_name.ilike("%Motion%"), Category.category_name.ilike("%Controllers%")))

            # Execute query
            results = query.order_by(Game.metacritic_score.desc().nullslast(), Game.name).limit(25).all()

            if not results:
                return json.dumps({"message": "No VR games found in your library", "suggestion": "Consider purchasing VR games from the Steam VR section", "alternative": "Use get_games_by_category(category='VR Support') to see all VR-related games", "vr_type": vr_type}, indent=2)

            # Format VR results
            games = []
            for game, user_game in results:
                # Analyze VR features
                game_categories = [c.category_name for c in game.categories]
                vr_features = [c for c in game_categories if "VR" in c or any(keyword in c for keyword in ["Seated", "Room", "Motion", "Controllers"])]

                # VR recommendations based on categories
                vr_recommendations = []
                if any("Seated" in cat for cat in vr_features):
                    vr_recommendations.append("Comfortable for long sessions")
                if any("Room" in cat for cat in vr_features):
                    vr_recommendations.append("Requires room-scale setup")
                if any("Motion" in cat or "Controllers" in cat for cat in vr_features):
                    vr_recommendations.append("Motion controllers enhance experience")

                games.append({"game_id": game.appid, "name": game.name, "genres": [g.genre_name for g in game.genres], "vr_features": vr_features, "vr_recommendations": vr_recommendations, "playtime_hours": round(user_game.playtime_forever / 60, 1), "metacritic_score": game.metacritic_score, "vr_comfort_level": {"seated": "High - comfortable for all users", "room_scale": "Medium - requires space and movement", "motion_controllers": "Medium - requires hand coordination", "any": "Varies by game"}[vr_type], "short_description": game.short_description[:120] + "..." if game.short_description and len(game.short_description) > 120 else game.short_description})

            return json.dumps({"vr_games": games, "vr_type": vr_type, "count": len(games), "user_steam_id": user_steam_id, "vr_tips": {"any": "Make sure your VR headset is properly set up", "seated": "Perfect for longer gaming sessions without fatigue", "room_scale": "Ensure you have adequate play space cleared", "motion_controllers": "Check controller battery levels before playing"}[vr_type], "safety_reminder": "Take breaks every 30-60 minutes when playing VR games"}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get VR games: {str(e)}", "help": "Check if user has VR games in library"}, indent=2)


@mcp.tool()
async def analyze_gaming_patterns(analysis_type: str = "overview", time_range: str = "all", user: str | None = None) -> str:
    """
    Analyze gaming patterns and provide insights.

    Args:
        analysis_type: Type of analysis (overview, genre_trends, achievements, playtime)
        time_range: Time period (all, recent, 6months, 1year)
        user: User ID (defaults to default user)

    Returns:
        JSON object with gaming pattern analysis and insights
    """
    # Validate parameters
    valid_analyses = ["overview", "genre_trends", "achievements", "playtime"]
    valid_ranges = ["all", "recent", "6months", "1year"]

    if analysis_type not in valid_analyses:
        return json.dumps({"error": f"Invalid analysis_type: {analysis_type}", "help": f"Use one of: {', '.join(valid_analyses)}", "descriptions": {"overview": "General gaming pattern overview", "genre_trends": "Genre preference analysis", "achievements": "Achievement hunting patterns", "playtime": "Playtime distribution analysis"}, "example": "analyze_gaming_patterns(analysis_type='genre_trends')"}, indent=2)

    if time_range not in valid_ranges:
        return json.dumps({"error": f"Invalid time_range: {time_range}", "help": f"Use one of: {', '.join(valid_ranges)}", "example": "analyze_gaming_patterns(analysis_type='overview', time_range='recent')"}, indent=2)

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return json.dumps({"error": f"User error: {user_result['message']}", "help": "Use get_user_profile() to see available users"}, indent=2)

    user_steam_id = user_result["steam_id"]

    try:
        with get_db() as session:
            # Base analysis data
            analysis = {"analysis_type": analysis_type, "time_range": time_range, "user_steam_id": user_steam_id, "generated_at": "now"}

            if analysis_type == "overview":
                # General gaming overview
                total_games = session.query(UserGame).filter(UserGame.user_steam_id == user_steam_id).count()
                played_games = session.query(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.playtime_forever > 0).count()

                total_playtime = session.query(func.sum(UserGame.playtime_forever)).filter(UserGame.user_steam_id == user_steam_id).scalar() or 0

                # Gaming habits
                analysis["overview"] = {"total_games": total_games, "played_games": played_games, "completion_rate": round(played_games / total_games * 100, 1) if total_games > 0 else 0, "total_hours": round(total_playtime / 60, 1), "average_per_game": round(total_playtime / total_games, 1) if total_games > 0 else 0, "gaming_style": "Completionist" if played_games / total_games > 0.7 else "Collector" if total_games > 100 else "Focused Gamer"}

            elif analysis_type == "genre_trends":
                # Genre preference analysis
                genre_data = session.query(Genre.genre_name, func.count(UserGame.appid).label("game_count"), func.sum(UserGame.playtime_forever).label("total_playtime"), func.avg(UserGame.playtime_forever).label("avg_playtime")).join(Game.genres).join(UserGame).filter(UserGame.user_steam_id == user_steam_id).group_by(Genre.genre_name).order_by(func.sum(UserGame.playtime_forever).desc()).all()

                analysis["genre_trends"] = [{"genre": genre, "games_owned": int(count), "total_hours": round(playtime / 60, 1), "average_hours_per_game": round(avg_playtime / 60, 1), "preference_score": round((playtime / 60) / count, 1) if count > 0 else 0} for genre, count, playtime, avg_playtime in genre_data[:10]]

            elif analysis_type == "achievements":
                # Achievement pattern analysis
                achievement_data = session.query(func.sum(UserGame.achievements_unlocked).label("total_unlocked"), func.sum(UserGame.achievements_total).label("total_available"), func.count(UserGame.appid).label("games_with_achievements")).filter(UserGame.user_steam_id == user_steam_id, UserGame.achievements_total > 0).first()

                # Top achievement games
                top_achievement_games = session.query(Game.name, UserGame.achievements_unlocked, UserGame.achievements_total).join(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.achievements_total > 0).order_by(UserGame.achievements_unlocked.desc()).limit(10).all()

                analysis["achievement_patterns"] = {"total_unlocked": achievement_data.total_unlocked or 0, "total_available": achievement_data.total_available or 0, "completion_rate": round((achievement_data.total_unlocked or 0) / (achievement_data.total_available or 1) * 100, 1), "games_with_achievements": achievement_data.games_with_achievements or 0, "hunter_level": "Achievement Hunter" if (achievement_data.total_unlocked or 0) > 500 else "Casual" if (achievement_data.total_unlocked or 0) > 100 else "Beginner", "top_games": [{"game": name, "unlocked": unlocked, "total": total, "percentage": round(unlocked / total * 100, 1) if total > 0 else 0} for name, unlocked, total in top_achievement_games]}

            elif analysis_type == "playtime":
                # Playtime distribution analysis
                playtime_brackets = [("Unplayed", 0, 0), ("Tried (< 1hr)", 1, 59), ("Short (1-5hrs)", 60, 299), ("Medium (5-20hrs)", 300, 1199), ("Long (20-50hrs)", 1200, 2999), ("Epic (50+ hrs)", 3000, float("inf"))]

                playtime_distribution = []
                for bracket_name, min_time, max_time in playtime_brackets:
                    if max_time == float("inf"):
                        count = session.query(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.playtime_forever >= min_time).count()
                    else:
                        count = session.query(UserGame).filter(UserGame.user_steam_id == user_steam_id, UserGame.playtime_forever.between(min_time, max_time)).count()

                    playtime_distribution.append({"bracket": bracket_name, "count": count, "range": f"{min_time//60}h - {max_time//60 if max_time != float('inf') else '∞'}h"})

                analysis["playtime_distribution"] = playtime_distribution

            return json.dumps(analysis, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to analyze gaming patterns: {str(e)}", "help": "Check analysis parameters and user data availability"}, indent=2)
