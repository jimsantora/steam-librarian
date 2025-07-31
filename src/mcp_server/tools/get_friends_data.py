"""Friends and social gaming data tool"""

import logging
from collections import Counter
from typing import Any

from mcp.server.fastmcp import Context
from sqlalchemy.orm import joinedload

from mcp_server.cache import cache, user_cache_key
from mcp_server.enhanced_user_context import (
    format_elicitation_error,
    resolve_user_context_with_elicitation,
)
from mcp_server.server import mcp
from mcp_server.user_context import resolve_user_context
from mcp_server.validation import FriendsDataInput
from shared.database import Game, UserGame, UserProfile, friends_association, get_db

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_friends_data(data_type: str, user_steam_id: str | None = None, friend_steam_id: str | None = None, game_identifier: str | None = None, ctx: Context | None = None) -> str:
    """Get social gaming data including friends lists, common games, and compatibility scores.

    Args:
        data_type: Type of data to retrieve - 'common_games', 'friend_activity', 'multiplayer_compatible', 'compatibility_score'
        user_steam_id: Steam ID of user (optional, will auto-resolve if not provided)
        friend_steam_id: Steam ID of friend (required for specific friend comparisons)
        game_identifier: Game name or app_id for multiplayer compatibility checks
    """

    # Validate input
    try:
        input_data = FriendsDataInput(data_type=data_type, user_steam_id=user_steam_id, friend_steam_id=friend_steam_id, game_identifier=game_identifier)
    except Exception as e:
        return f"Invalid input: {str(e)}"

    # Try enhanced user context resolution with elicitation if available
    if ctx is not None:
        user_context = await resolve_user_context_with_elicitation(input_data.user_steam_id, ctx, allow_elicitation=True)
    else:
        # Fallback to standard resolution
        user_context = await resolve_user_context(input_data.user_steam_id)

    if "error" in user_context:
        error_msg = format_elicitation_error(user_context) if ctx else user_context.get("message", "Unknown error")
        return f"User error: {error_msg}"

    user = user_context["user"]

    # Generate cache key
    cache_key = user_cache_key("friends_data", user.steam_id) + f"_{input_data.data_type}_{input_data.friend_steam_id or 'all'}_{input_data.game_identifier or 'none'}"

    async def compute_friends_data():
        return await _get_friends_data(user, input_data)

    # Get friends data with caching
    friends_data = await cache.get_or_compute(cache_key, compute_friends_data, ttl=1800)  # 30 min cache

    if not friends_data:
        return "No friends data available. Make sure you have friends added and their libraries are accessible."

    # Format response based on data type
    response_text = _format_friends_data(friends_data, input_data.data_type, user)

    return response_text


async def _get_friends_data(user: UserProfile, input_data: FriendsDataInput) -> dict[str, Any]:
    """Get friends data based on requested type"""

    try:
        with get_db() as session:
            # Get user's friends using the association table
            friends_query = session.query(friends_association).filter(friends_association.c.user_steam_id == user.steam_id).all()

            if not friends_query:
                return {"error": "No friends found in your Steam friends list"}

            # Convert to friend steam IDs
            friend_steam_ids = [f.friend_steam_id for f in friends_query]

            if input_data.data_type == "common_games":
                return await _get_common_games(session, user, input_data.friend_steam_id, friend_steam_ids)

            elif input_data.data_type == "friend_activity":
                return await _get_friend_activity(session, user, friend_steam_ids)

            elif input_data.data_type == "multiplayer_compatible":
                return await _get_multiplayer_compatible(session, user, input_data.game_identifier, friend_steam_ids)

            elif input_data.data_type == "compatibility_score":
                return await _calculate_compatibility_scores(session, user, input_data.friend_steam_id, friend_steam_ids)

            return {"error": f"Unknown data type: {input_data.data_type}"}

    except Exception as e:
        logger.error(f"Error getting friends data: {e}")
        return {"error": f"Database error: {str(e)}"}


async def _get_common_games(session, user: UserProfile, friend_steam_id: str | None, friend_steam_ids: list[str]) -> dict[str, Any]:
    """Get games in common between user and friends"""

    # Get user's games
    user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.categories)).filter(UserGame.steam_id == user.steam_id).all()

    user_game_ids = {ug.app_id for ug in user_games}

    if friend_steam_id:
        # Check specific friend
        friend = session.query(UserProfile).filter_by(steam_id=friend_steam_id).first()
        if not friend:
            return {"error": f"Friend with Steam ID {friend_steam_id} not found"}

        return await _compare_with_specific_friend(session, user, friend, user_game_ids)
    else:
        # Compare with all friends
        return await _compare_with_all_friends(session, user, friend_steam_ids, user_game_ids)


async def _compare_with_specific_friend(session, user: UserProfile, friend: UserProfile, user_game_ids: set) -> dict[str, Any]:
    """Compare games with a specific friend"""

    try:
        # Get friend's games
        friend_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.categories)).filter(UserGame.steam_id == friend.steam_id).all()

        friend_game_ids = {fg.app_id for fg in friend_games}

        # Find common games
        common_game_ids = user_game_ids & friend_game_ids

        if not common_game_ids:
            return {"friend": {"steam_id": friend.steam_id, "persona_name": friend.persona_name or "Unknown"}, "common_games": [], "total_common": 0, "recommendations": []}

        # Get detailed info for common games
        common_games = []
        user_game_map = {ug.app_id: ug for ug in session.query(UserGame).filter(UserGame.steam_id == user.steam_id, UserGame.app_id.in_(common_game_ids)).all()}

        friend_game_map = {fg.app_id: fg for fg in session.query(UserGame).filter(UserGame.steam_id == friend.steam_id, UserGame.app_id.in_(common_game_ids)).all()}

        for app_id in common_game_ids:
            user_game = user_game_map.get(app_id)
            friend_game = friend_game_map.get(app_id)

            if user_game and friend_game and user_game.game:
                total_playtime = (user_game.playtime_forever + friend_game.playtime_forever) / 60
                recent_activity = max(user_game.playtime_2weeks, friend_game.playtime_2weeks) > 0

                common_games.append({"app_id": app_id, "name": user_game.game.name or "Unknown Game", "your_playtime_hours": round(user_game.playtime_forever / 60, 1), "friend_playtime_hours": round(friend_game.playtime_forever / 60, 1), "combined_playtime_hours": round(total_playtime, 1), "recently_active": recent_activity, "genres": [g.genre_name for g in user_game.game.genres] if user_game.game.genres else [], "is_multiplayer": _is_multiplayer_game(user_game.game)})

        # Sort by combined playtime
        common_games.sort(key=lambda x: x["combined_playtime_hours"], reverse=True)

        # Generate game recommendations (games friend has that user doesn't)
        friend_only_games = friend_game_ids - user_game_ids
        recommendations = await _generate_friend_recommendations(session, friend, friend_only_games)

        return {"friend": {"steam_id": friend.steam_id, "persona_name": friend.persona_name or "Unknown"}, "common_games": common_games[:20], "total_common": len(common_games), "recommendations": recommendations[:5]}

    except Exception as e:
        logger.error(f"Error in _compare_with_specific_friend: {e}")
        return {"error": f"Failed to compare with friend: {str(e)}"}


async def _compare_with_all_friends(session, user: UserProfile, friend_steam_ids: list[str], user_game_ids: set) -> dict[str, Any]:
    """Compare games with all friends"""

    try:
        friend_comparisons = []

        for friend_steam_id in friend_steam_ids:
            friend = session.query(UserProfile).filter_by(steam_id=friend_steam_id).first()
            if not friend:
                continue

            # Get friend's games
            friend_games = session.query(UserGame).filter(UserGame.steam_id == friend.steam_id).all()
            friend_game_ids = {fg.app_id for fg in friend_games}

            # Calculate common games
            common_game_ids = user_game_ids & friend_game_ids
            common_count = len(common_game_ids)

            if common_count > 0:
                # Calculate compatibility score
                compatibility = common_count / max(len(user_game_ids), len(friend_game_ids))

                friend_comparisons.append({"friend": {"steam_id": friend.steam_id, "persona_name": friend.persona_name or "Unknown"}, "common_games_count": common_count, "compatibility_score": round(compatibility * 100, 1), "total_friend_games": len(friend_game_ids)})

        # Sort by common games count
        friend_comparisons.sort(key=lambda x: x["common_games_count"], reverse=True)

        return {"friends_comparison": friend_comparisons, "total_friends": len(friend_comparisons)}

    except Exception as e:
        logger.error(f"Error in _compare_with_all_friends: {e}")
        return {"error": f"Failed to compare with friends: {str(e)}"}


async def _get_friend_activity(session, user: UserProfile, friend_steam_ids: list[str]) -> dict[str, Any]:
    """Get recent activity information for friends"""

    try:
        active_friends = []

        for friend_steam_id in friend_steam_ids:
            friend = session.query(UserProfile).filter_by(steam_id=friend_steam_id).first()
            if not friend:
                continue

            # Get friend's recent activity
            recent_games = session.query(UserGame).options(joinedload(UserGame.game)).filter(UserGame.steam_id == friend.steam_id, UserGame.playtime_2weeks > 0).all()

            if recent_games:
                total_recent_hours = sum(rg.playtime_2weeks / 60 for rg in recent_games)

                # Find most played recent game
                most_played_recent = max(recent_games, key=lambda x: x.playtime_2weeks)

                # Get recent genres
                recent_genres = Counter()
                for rg in recent_games:
                    if rg.game and rg.game.genres:
                        for genre in rg.game.genres:
                            recent_genres[genre.genre_name] += rg.playtime_2weeks

                top_genre = recent_genres.most_common(1)[0][0] if recent_genres else "Unknown"

                active_friends.append({"friend": {"steam_id": friend.steam_id, "persona_name": friend.persona_name or "Unknown"}, "recent_hours": round(total_recent_hours, 1), "recent_games_count": len(recent_games), "most_played_recent": {"name": most_played_recent.game.name if most_played_recent.game else "Unknown", "hours": round(most_played_recent.playtime_2weeks / 60, 1)}, "top_recent_genre": top_genre})

        # Sort by recent activity
        active_friends.sort(key=lambda x: x["recent_hours"], reverse=True)

        return {"active_friends": active_friends, "total_active": len(active_friends)}

    except Exception as e:
        logger.error(f"Error in _get_friend_activity: {e}")
        return {"error": f"Failed to get friend activity: {str(e)}"}


async def _get_multiplayer_compatible(session, user: UserProfile, game_identifier: str | None, friend_steam_ids: list[str]) -> dict[str, Any]:
    """Get friends who own a specific multiplayer game"""

    if not game_identifier:
        return {"error": "Game identifier is required for multiplayer compatibility check"}

    try:
        # Find the game
        try:
            # Try as app_id first
            app_id = int(game_identifier)
            game = session.query(Game).filter_by(app_id=app_id).first()
        except ValueError:
            # Search by name
            game = session.query(Game).filter(Game.name.ilike(f"%{game_identifier}%")).first()

        if not game:
            return {"error": f"Game '{game_identifier}' not found"}

        # Check if user owns the game
        user_owns = session.query(UserGame).filter(UserGame.steam_id == user.steam_id, UserGame.app_id == game.app_id).first()

        if not user_owns:
            return {"error": f"You don't own {game.name}"}

        # Find friends who also own this game
        compatible_friends = []

        for friend_steam_id in friend_steam_ids:
            friend = session.query(UserProfile).filter_by(steam_id=friend_steam_id).first()
            if not friend:
                continue

            friend_game = session.query(UserGame).filter(UserGame.steam_id == friend.steam_id, UserGame.app_id == game.app_id).first()

            if friend_game:
                compatible_friends.append({"friend": {"steam_id": friend.steam_id, "persona_name": friend.persona_name or "Unknown"}, "playtime_hours": round(friend_game.playtime_forever / 60, 1), "recent_playtime_hours": round(friend_game.playtime_2weeks / 60, 1), "is_active": friend_game.playtime_2weeks > 0})

        # Sort by recent activity, then total playtime
        compatible_friends.sort(key=lambda x: (x["is_active"], x["recent_playtime_hours"], x["playtime_hours"]), reverse=True)

        return {"game": {"app_id": game.app_id, "name": game.name}, "your_playtime_hours": round(user_owns.playtime_forever / 60, 1), "is_multiplayer": _is_multiplayer_game(game), "compatible_friends": compatible_friends, "total_compatible": len(compatible_friends)}

    except Exception as e:
        logger.error(f"Error in _get_multiplayer_compatible: {e}")
        return {"error": f"Failed to check multiplayer compatibility: {str(e)}"}


async def _calculate_compatibility_scores(session, user: UserProfile, specific_friend_id: str | None, friend_steam_ids: list[str]) -> dict[str, Any]:
    """Calculate gaming compatibility scores with friends"""

    # Get user's gaming profile
    user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres)).filter(UserGame.steam_id == user.steam_id).all()

    user_genres = Counter()
    user_total_playtime = sum(ug.playtime_forever for ug in user_games)

    for ug in user_games:
        if ug.game and ug.game.genres:
            weight = ug.playtime_forever / user_total_playtime if user_total_playtime > 0 else 0
            for genre in ug.game.genres:
                user_genres[genre.genre_name] += weight

    user_top_genres = set(dict(user_genres.most_common(5)).keys())

    compatibility_scores = []

    friends_to_check = []
    if specific_friend_id:
        friend = session.query(UserProfile).filter_by(steam_id=specific_friend_id).first()
        if friend:
            friends_to_check = [friend]
    else:
        for friend_steam_id in friend_steam_ids:
            friend = session.query(UserProfile).filter_by(steam_id=friend_steam_id).first()
            if friend:
                friends_to_check.append(friend)

    for friend in friends_to_check:
        # Get friend's gaming profile
        friend_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres)).filter(UserGame.steam_id == friend.steam_id).all()

        friend_genres = Counter()
        friend_total_playtime = sum(fg.playtime_forever for fg in friend_games)

        for fg in friend_games:
            if fg.game and fg.game.genres:
                weight = fg.playtime_forever / friend_total_playtime if friend_total_playtime > 0 else 0
                for genre in fg.game.genres:
                    friend_genres[genre.genre_name] += weight

        friend_top_genres = set(dict(friend_genres.most_common(5)).keys())

        # Calculate compatibility metrics
        user_game_ids = {ug.app_id for ug in user_games}
        friend_game_ids = {fg.app_id for fg in friend_games}

        common_games = len(user_game_ids & friend_game_ids)
        total_unique_games = len(user_game_ids | friend_game_ids)

        # Genre similarity (Jaccard index)
        genre_overlap = len(user_top_genres & friend_top_genres)
        genre_union = len(user_top_genres | friend_top_genres)
        genre_similarity = genre_overlap / genre_union if genre_union > 0 else 0

        # Game overlap ratio
        game_overlap = common_games / total_unique_games if total_unique_games > 0 else 0

        # Combined compatibility score
        compatibility = (genre_similarity * 0.6 + game_overlap * 0.4) * 100

        # Find shared interests
        shared_genres = list(user_top_genres & friend_top_genres)

        compatibility_scores.append({"friend": {"steam_id": friend.steam_id, "persona_name": friend.persona_name}, "compatibility_score": round(compatibility, 1), "common_games": common_games, "genre_similarity": round(genre_similarity * 100, 1), "shared_genres": shared_genres[:3], "recommendation_potential": "High" if compatibility > 70 else "Medium" if compatibility > 40 else "Low"})  # Top 3 shared genres

    # Sort by compatibility score
    compatibility_scores.sort(key=lambda x: x["compatibility_score"], reverse=True)

    return {"compatibility_scores": compatibility_scores, "analysis_complete": True}


async def _generate_friend_recommendations(session, friend: UserProfile, friend_only_games: set) -> list[dict[str, Any]]:
    """Generate game recommendations based on what friend owns"""

    if not friend_only_games:
        return []

    # Get friend's games with playtime
    friend_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.reviews)).filter(UserGame.steam_id == friend.steam_id, UserGame.app_id.in_(friend_only_games), UserGame.playtime_forever > 60).all()  # At least 1 hour played

    recommendations = []

    for fg in friend_games:
        if fg.game:
            # Calculate recommendation score based on friend's playtime and game reviews
            playtime_score = min(fg.playtime_forever / 600, 1.0)  # Normalize to 10 hours max
            review_score = fg.game.reviews.positive_percentage / 100 if fg.game.reviews else 0.5

            total_score = playtime_score * 0.6 + review_score * 0.4

            if total_score > 0.3:  # Minimum threshold
                recommendations.append({"app_id": fg.game.app_id, "name": fg.game.name, "friend_playtime_hours": round(fg.playtime_forever / 60, 1), "genres": [g.genre_name for g in fg.game.genres] if fg.game.genres else [], "review_score": round(review_score * 100, 1), "recommendation_score": round(total_score * 100, 1), "reason": f"{friend.persona_name} has {round(fg.playtime_forever / 60, 1)} hours"})

    # Sort by recommendation score
    recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)

    return recommendations


def _is_multiplayer_game(game: Game) -> bool:
    """Check if a game supports multiplayer"""
    if not game.categories:
        return False

    multiplayer_categories = ["Multi-player", "Co-op", "Online Co-op", "Local Co-op", "Shared/Split Screen"]
    return any(cat.category_name in multiplayer_categories for cat in game.categories)


def _format_friends_data(data: dict[str, Any], data_type: str, user: UserProfile) -> str:
    """Format friends data for display"""

    # Add error handling for missing data
    if not data or "error" in data:
        error_msg = data.get("error", "Unknown error occurred") if data else "No data available"
        return f"Error: {error_msg}"

    if data_type == "common_games":
        if "friend" in data:
            # Specific friend comparison
            friend = data.get("friend", {})
            common_games = data.get("common_games", [])
            total_common = data.get("total_common", 0)
            recommendations = data.get("recommendations", [])

            friend_name = friend.get("persona_name", "Unknown Friend") if friend else "Unknown Friend"
            result = f"**Common Games with {friend_name}**\n\n"
            result += f"**{total_common} games in common**\n\n"

            if common_games:
                game_lines = []
                for game in common_games[:10]:  # Top 10
                    multiplayer_prefix = "[MP]" if game["is_multiplayer"] else "[SP]"
                    recent_prefix = "[ACTIVE]" if game["recently_active"] else ""

                    line = f"{multiplayer_prefix}{recent_prefix} **{game['name']}**"
                    line += f"\n  • You: {game['your_playtime_hours']}h | {friend['persona_name']}: {game['friend_playtime_hours']}h"

                    if game["genres"]:
                        line += f"\n  • {', '.join(game['genres'][:2])}"

                    game_lines.append(line)

                result += "\n\n".join(game_lines)

            if recommendations:
                result += f"\n\n**Games {friend['persona_name']} recommends:**\n"
                rec_lines = []
                for rec in recommendations:
                    rec_lines.append(f"• **{rec['name']}** ({rec['friend_playtime_hours']}h played, {rec['review_score']}% positive)")
                result += "\n".join(rec_lines)

            return result

        else:
            # All friends comparison - fix the key error
            friends_comparison = data.get("friends_comparison", [])
            total_friends = data.get("total_friends", 0)

            result = f"**Gaming Compatibility with Friends** ({total_friends} friends)\n\n"

            if friends_comparison:
                friend_lines = []
                for friend_data in friends_comparison[:10]:  # Top 10
                    friend = friend_data["friend"]
                    score_label = "[HIGH]" if friend_data["compatibility_score"] > 50 else "[MED]" if friend_data["compatibility_score"] > 25 else "[LOW]"

                    line = f"{score_label} **{friend['persona_name']}**"
                    line += f"\n  • {friend_data['common_games_count']} common games ({friend_data['compatibility_score']}% compatible)"
                    line += f"\n  • Total library: {friend_data['total_friend_games']} games"

                    friend_lines.append(line)

                result += "\n\n".join(friend_lines)

            return result

    elif data_type == "friend_activity":
        active_friends = data.get("active_friends", [])
        total_active = data.get("total_active", 0)

        result = f"**Recent Friend Activity** ({total_active} active friends)\n\n"

        if active_friends:
            activity_lines = []
            for friend_data in active_friends:
                friend = friend_data["friend"]
                activity_label = "[HIGH]" if friend_data["recent_hours"] > 10 else "[MED]" if friend_data["recent_hours"] > 5 else "[LOW]"

                line = f"{activity_label} **{friend['persona_name']}**"
                line += f"\n  • {friend_data['recent_hours']}h in last 2 weeks ({friend_data['recent_games_count']} games)"
                line += f"\n  • Currently playing: {friend_data['most_played_recent']['name']} ({friend_data['most_played_recent']['hours']}h recent)"
                line += f"\n  • Favorite genre: {friend_data['top_recent_genre']}"

                activity_lines.append(line)

            result += "\n\n".join(activity_lines)

        return result

    elif data_type == "multiplayer_compatible":
        # Fix the 'game' key error
        game_info = data.get("game", {})
        compatible_friends = data.get("compatible_friends", [])
        total_compatible = data.get("total_compatible", 0)
        is_multiplayer = data.get("is_multiplayer", False)
        your_playtime = data.get("your_playtime_hours", 0)

        game_name = game_info.get("name", "Unknown Game") if game_info else "Unknown Game"
        multiplayer_status = "✅ Multiplayer" if is_multiplayer else "❌ Single-player only"

        result = f"**Multiplayer Compatibility: {game_name}**\n\n"
        result += f"{multiplayer_status}\n"
        result += f"Your playtime: {your_playtime}h\n\n"
        result += f"**{total_compatible} friends own this game:**\n\n"

        if compatible_friends:
            friend_lines = []
            for friend_data in compatible_friends:
                friend = friend_data["friend"]
                activity_status = "[ACTIVE]" if friend_data["is_active"] else "[INACTIVE]"

                line = f"{activity_status} **{friend['persona_name']}**"
                line += f"\n  • {friend_data['playtime_hours']}h total"

                if friend_data["recent_playtime_hours"] > 0:
                    line += f" | {friend_data['recent_playtime_hours']}h recent"

                friend_lines.append(line)

            result += "\n\n".join(friend_lines)

        return result

    elif data_type == "compatibility_score":
        compatibility_scores = data.get("compatibility_scores", [])

        result = f"**Gaming Compatibility Analysis for {user.persona_name}**\n\n"

        if compatibility_scores:
            score_lines = []
            for score_data in compatibility_scores:
                friend = score_data["friend"]
                score = score_data["compatibility_score"]

                if score > 70:
                    compatibility_label = "[EXCELLENT]"
                    compatibility_desc = "Excellent match"
                elif score > 50:
                    compatibility_label = "[GOOD]"
                    compatibility_desc = "Good compatibility"
                elif score > 30:
                    compatibility_label = "[SOME]"
                    compatibility_desc = "Some shared interests"
                else:
                    compatibility_label = "[DIFFERENT]"
                    compatibility_desc = "Different gaming styles"

                line = f"{compatibility_label} **{friend['persona_name']}** ({score}% compatible)"
                line += f"\n  • {compatibility_desc}"
                line += f"\n  • {score_data['common_games']} games in common"
                line += f"\n  • Genre similarity: {score_data['genre_similarity']}%"

                if score_data["shared_genres"]:
                    line += f"\n  • Shared interests: {', '.join(score_data['shared_genres'])}"

                line += f"\n  • Recommendation potential: {score_data['recommendation_potential']}"

                score_lines.append(line)

            result += "\n\n".join(score_lines)

        return result

    return "Unknown data type requested."
