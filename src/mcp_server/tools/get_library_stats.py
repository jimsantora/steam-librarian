"""Library statistics and insights tool"""

import logging
from collections import Counter
from typing import Any

from sqlalchemy.orm import joinedload

from mcp_server.cache import cache, user_cache_key
from mcp_server.user_context import resolve_user_context
from mcp_server.utils.library_stats import calculate_library_overview
from mcp_server.validation import LibraryStatsInput
from shared.database import Game, UserGame, UserProfile, get_db

logger = logging.getLogger(__name__)

from mcp_server.server import mcp


@mcp.tool()
async def get_library_stats(
    user_steam_id: str | None = None,
    time_period: str = "all_time",
    include_insights: bool = True
) -> str:
    """Get comprehensive library statistics and insights for a user.
    
    Args:
        user_steam_id: Steam ID of user (optional, will auto-resolve if not provided)
        time_period: Time period for analysis - 'all_time', 'last_year', 'last_6_months', 'last_month', 'last_week'
        include_insights: Include AI-generated insights about gaming patterns
    """

    # Validate input
    try:
        input_data = LibraryStatsInput(
            user_steam_id=user_steam_id,
            time_period=time_period,
            include_insights=include_insights
        )
    except Exception as e:
        return f"Invalid input: {str(e)}"

    # Resolve user context
    user_context = await resolve_user_context(input_data.user_steam_id)
    if "error" in user_context:
        return f"User error: {user_context['message']}"

    user = user_context["user"]

    # Generate cache key
    cache_key = user_cache_key("library_stats", user.steam_id) + f"_{input_data.time_period}_{input_data.include_insights}"

    async def compute_library_stats():
        return await _generate_comprehensive_stats(user, input_data.time_period, input_data.include_insights)

    # Get library stats with caching
    stats = await cache.get_or_compute(cache_key, compute_library_stats, ttl=3600)  # 1 hour cache

    if not stats:
        return "Unable to generate library statistics. Make sure you have games in your library."

    # Format response
    stats_text = _format_library_stats(stats, user, input_data.time_period, input_data.include_insights)

    return stats_text


async def _generate_comprehensive_stats(user: UserProfile, time_period: str, include_insights: bool) -> dict[str, Any]:
    """Calculate comprehensive library statistics"""

    # Use existing utility for basic overview
    overview = calculate_library_overview(user)

    if not overview or overview["total_games"] == 0:
        return None

    # Enhance with additional analytics
    with get_db() as session:
        enhanced_stats = await _calculate_enhanced_analytics(session, user, time_period)

        # Combine basic overview with enhanced analytics
        stats = {
            **overview,
            **enhanced_stats
        }

        # Add insights if requested
        if include_insights:
            stats["insights"] = await _generate_gaming_insights(stats, user)

        return stats


async def _calculate_enhanced_analytics(session, user: UserProfile, time_period: str) -> dict[str, Any]:
    """Calculate enhanced analytics beyond basic overview"""

    # Get user games with all relationships
    user_games = session.query(UserGame).options(
        joinedload(UserGame.game).joinedload(Game.genres),
        joinedload(UserGame.game).joinedload(Game.categories),
        joinedload(UserGame.game).joinedload(Game.developers),
        joinedload(UserGame.game).joinedload(Game.publishers),
        joinedload(UserGame.game).joinedload(Game.reviews)
    ).filter(UserGame.steam_id == user.steam_id).all()

    played_games = [ug for ug in user_games if ug.playtime_forever > 0]

    if not played_games:
        return {}

    # Developer analysis
    developer_stats = _analyze_developers(played_games)

    # Publisher analysis
    publisher_stats = _analyze_publishers(played_games)

    # Playtime distribution analysis
    playtime_distribution = _analyze_playtime_distribution(played_games)

    # Gaming value analysis
    value_analysis = _analyze_gaming_value(played_games)

    # Review preference analysis
    review_preferences = _analyze_review_preferences(played_games)

    # Feature preferences
    feature_preferences = _analyze_feature_preferences(user_games)

    # Recent activity trends (if applicable)
    activity_trends = _analyze_activity_trends(played_games, time_period)

    return {
        "developer_stats": developer_stats,
        "publisher_stats": publisher_stats,
        "playtime_distribution": playtime_distribution,
        "value_analysis": value_analysis,
        "review_preferences": review_preferences,
        "feature_preferences": feature_preferences,
        "activity_trends": activity_trends
    }


def _analyze_developers(played_games: list) -> dict[str, Any]:
    """Analyze user's developer preferences"""

    developer_playtime = Counter()
    developer_count = Counter()

    for ug in played_games:
        if ug.game and ug.game.developers:
            for dev in ug.game.developers:
                developer_playtime[dev.developer_name] += ug.playtime_forever
                developer_count[dev.developer_name] += 1

    # Top developers by playtime
    top_by_playtime = []
    for dev, total_time in developer_playtime.most_common(5):
        top_by_playtime.append({
            "name": dev,
            "playtime_hours": round(total_time / 60, 1),
            "games_count": developer_count[dev]
        })

    return {
        "top_by_playtime": top_by_playtime,
        "total_developers": len(developer_count)
    }


def _analyze_publishers(played_games: list) -> dict[str, Any]:
    """Analyze user's publisher preferences"""

    publisher_playtime = Counter()
    publisher_count = Counter()

    for ug in played_games:
        if ug.game and ug.game.publishers:
            for pub in ug.game.publishers:
                publisher_playtime[pub.publisher_name] += ug.playtime_forever
                publisher_count[pub.publisher_name] += 1

    # Top publishers by playtime
    top_by_playtime = []
    for pub, total_time in publisher_playtime.most_common(5):
        top_by_playtime.append({
            "name": pub,
            "playtime_hours": round(total_time / 60, 1),
            "games_count": publisher_count[pub]
        })

    return {
        "top_by_playtime": top_by_playtime,
        "total_publishers": len(publisher_count)
    }


def _analyze_playtime_distribution(played_games: list) -> dict[str, Any]:
    """Analyze how playtime is distributed across games"""

    playtime_buckets = {
        "under_1h": 0,
        "1_5h": 0,
        "5_20h": 0,
        "20_100h": 0,
        "over_100h": 0
    }

    total_playtime = sum(ug.playtime_forever for ug in played_games)

    for ug in played_games:
        hours = ug.playtime_forever / 60

        if hours < 1:
            playtime_buckets["under_1h"] += 1
        elif hours < 5:
            playtime_buckets["1_5h"] += 1
        elif hours < 20:
            playtime_buckets["5_20h"] += 1
        elif hours < 100:
            playtime_buckets["20_100h"] += 1
        else:
            playtime_buckets["over_100h"] += 1

    # Convert to percentages
    total_played = len(played_games)
    distribution = {}
    for bucket, count in playtime_buckets.items():
        distribution[bucket] = {
            "count": count,
            "percentage": round((count / total_played) * 100, 1) if total_played > 0 else 0
        }

    # Find most played game
    most_played = max(played_games, key=lambda x: x.playtime_forever)
    most_played_info = {
        "name": most_played.game.name if most_played.game else "Unknown",
        "playtime_hours": round(most_played.playtime_forever / 60, 1)
    }

    return {
        "distribution": distribution,
        "most_played_game": most_played_info,
        "average_playtime_hours": round(total_playtime / (len(played_games) * 60), 1)
    }


def _analyze_gaming_value(played_games: list) -> dict[str, Any]:
    """Analyze gaming value and spending efficiency"""

    # Games with excellent value (high playtime per $ - approximated)
    high_value_games = []
    total_hours = sum(ug.playtime_forever / 60 for ug in played_games)

    # Find games with above-average playtime
    avg_playtime = total_hours / len(played_games)

    for ug in played_games:
        hours = ug.playtime_forever / 60
        if hours > avg_playtime * 1.5:  # 1.5x above average
            high_value_games.append({
                "name": ug.game.name if ug.game else "Unknown",
                "playtime_hours": round(hours, 1)
            })

    # Sort by playtime and take top 5
    high_value_games.sort(key=lambda x: x["playtime_hours"], reverse=True)

    return {
        "high_value_games": high_value_games[:5],
        "total_hours_played": round(total_hours, 1)
    }


def _analyze_review_preferences(played_games: list) -> dict[str, Any]:
    """Analyze user's preferences based on game reviews"""

    review_tolerance = Counter()
    total_weighted_rating = 0
    games_with_reviews = 0

    for ug in played_games:
        if ug.game and ug.game.reviews:
            review = ug.game.reviews
            weight = ug.playtime_forever  # Weight by playtime

            review_tolerance[review.review_summary] += weight
            total_weighted_rating += review.positive_percentage * weight
            games_with_reviews += 1

    if games_with_reviews == 0:
        return {"preferred_review_types": [], "average_rating_preference": 0}

    # Calculate preferred review types
    total_weight = sum(review_tolerance.values())
    preferred_types = []

    for review_type, weight in review_tolerance.most_common(3):
        percentage = (weight / total_weight) * 100
        preferred_types.append({
            "type": review_type,
            "preference_percentage": round(percentage, 1)
        })

    # Calculate average rating preference (weighted by playtime)
    avg_rating = total_weighted_rating / sum(ug.playtime_forever for ug in played_games if ug.game and ug.game.reviews)

    return {
        "preferred_review_types": preferred_types,
        "average_rating_preference": round(avg_rating, 1)
    }


def _analyze_feature_preferences(user_games: list) -> dict[str, Any]:
    """Analyze preferences for game features"""

    owned_with_features = 0
    features = {
        "steam_deck_verified": {"owned": 0, "played": 0},
        "controller_support": {"owned": 0, "played": 0},
        "vr_support": {"owned": 0, "played": 0}
    }

    for ug in user_games:
        if ug.game:
            owned_with_features += 1

            if ug.game.steam_deck_verified:
                features["steam_deck_verified"]["owned"] += 1
                if ug.playtime_forever > 0:
                    features["steam_deck_verified"]["played"] += 1

            if ug.game.controller_support:
                features["controller_support"]["owned"] += 1
                if ug.playtime_forever > 0:
                    features["controller_support"]["played"] += 1

            if ug.game.vr_support:
                features["vr_support"]["owned"] += 1
                if ug.playtime_forever > 0:
                    features["vr_support"]["played"] += 1

    # Calculate percentages
    feature_stats = {}
    for feature, counts in features.items():
        if counts["owned"] > 0:
            play_rate = (counts["played"] / counts["owned"]) * 100
        else:
            play_rate = 0

        feature_stats[feature] = {
            "owned_count": counts["owned"],
            "played_count": counts["played"],
            "play_rate_percentage": round(play_rate, 1)
        }

    return feature_stats


def _analyze_activity_trends(played_games: list, time_period: str) -> dict[str, Any]:
    """Analyze gaming activity trends"""

    recent_games = [ug for ug in played_games if ug.playtime_2weeks > 0]

    if not recent_games:
        return {"recent_activity": "No recent gaming activity"}

    recent_hours = sum(ug.playtime_2weeks / 60 for ug in recent_games)

    # Activity level classification
    if recent_hours > 20:
        activity_level = "Very Active"
    elif recent_hours > 10:
        activity_level = "Active"
    elif recent_hours > 5:
        activity_level = "Moderate"
    else:
        activity_level = "Light"

    # Most played recent genre
    recent_genres = Counter()
    for ug in recent_games:
        if ug.game and ug.game.genres:
            for genre in ug.game.genres:
                recent_genres[genre.genre_name] += ug.playtime_2weeks

    top_recent_genre = recent_genres.most_common(1)[0][0] if recent_genres else "None"

    return {
        "activity_level": activity_level,
        "recent_hours": round(recent_hours, 1),
        "recent_games_count": len(recent_games),
        "top_recent_genre": top_recent_genre
    }


async def _generate_gaming_insights(stats: dict[str, Any], user: UserProfile) -> list[str]:
    """Generate AI-powered insights about gaming patterns"""

    insights = []

    # Completion rate insights
    completion_rate = stats.get("completion_rate", 0)
    if completion_rate < 0.3:
        insights.append("You tend to try many games but complete fewer - consider focusing on games that really grab you")
    elif completion_rate > 0.8:
        insights.append("You're very committed to games you start - you rarely leave games unfinished")

    # Genre diversity insights
    genres = stats.get("genres", {})
    if len(genres) > 6:
        insights.append("You have diverse gaming tastes across many genres - you're an explorer!")
    elif len(genres) <= 3:
        insights.append("You have focused gaming preferences - you know what you like")

    # Playtime patterns
    playtime_dist = stats.get("playtime_distribution", {}).get("distribution", {})
    over_100h = playtime_dist.get("over_100h", {}).get("count", 0)
    if over_100h >= 3:
        insights.append("You have several games with 100+ hours - you really commit to games you love")

    under_1h = playtime_dist.get("under_1h", {}).get("count", 0)
    total_played = stats.get("played_games", 0)
    if under_1h / max(total_played, 1) > 0.4:
        insights.append("Many games in your library have minimal playtime - you might benefit from more selective purchases")

    # Developer loyalty
    dev_stats = stats.get("developer_stats", {})
    top_devs = dev_stats.get("top_by_playtime", [])
    if top_devs and len(top_devs) > 0:
        top_dev = top_devs[0]
        if top_dev["games_count"] >= 3:
            insights.append(f"You're a fan of {top_dev['name']} - you own {top_dev['games_count']} of their games")

    # Review preferences
    review_prefs = stats.get("review_preferences", {})
    avg_rating = review_prefs.get("average_rating_preference", 0)
    if avg_rating > 85:
        insights.append("You prefer highly-rated games - quality over quantity is your approach")
    elif avg_rating < 70:
        insights.append("You're willing to try games with mixed reviews - you don't let ratings stop you")

    # Recent activity patterns
    activity_trends = stats.get("activity_trends", {})
    activity_level = activity_trends.get("activity_level")
    if activity_level == "Very Active":
        insights.append("You've been very active recently - gaming is clearly a big part of your routine")
    elif activity_level == "Light":
        insights.append("Your recent activity is light - maybe it's time to revisit some favorites")

    return insights[:5]  # Limit to top 5 insights


def _format_library_stats(stats: dict[str, Any], time_period: str, include_insights: bool) -> str:
    """Format library statistics for display"""

    sections = []

    # Basic overview
    overview_text = f"""📊 **Overview**
• Total Games: {stats['total_games']}
• Games Played: {stats['played_games']} ({round((stats['played_games']/stats['total_games'])*100, 1)}%)
• Total Playtime: {stats['total_playtime_hours']} hours
• Average per Game: {stats['average_playtime_per_game']} hours"""
    sections.append(overview_text)

    # Top genres
    if stats.get("genres"):
        genre_lines = []
        for genre, data in list(stats["genres"].items())[:5]:
            genre_lines.append(f"  • {genre}: {data['count']} games, {data['playtime_hours']}h")

        genres_text = f"""🎮 **Top Genres**
{chr(10).join(genre_lines)}"""
        sections.append(genres_text)

    # Developer stats
    if stats.get("developer_stats", {}).get("top_by_playtime"):
        dev_lines = []
        for dev in stats["developer_stats"]["top_by_playtime"][:3]:
            dev_lines.append(f"  • {dev['name']}: {dev['games_count']} games, {dev['playtime_hours']}h")

        dev_text = f"""👥 **Favorite Developers**
{chr(10).join(dev_lines)}"""
        sections.append(dev_text)

    # Playtime distribution
    if stats.get("playtime_distribution", {}).get("distribution"):
        dist = stats["playtime_distribution"]["distribution"]
        most_played = stats["playtime_distribution"]["most_played_game"]

        dist_text = f"""⏱️ **Playtime Distribution**
• Under 1h: {dist['under_1h']['count']} games ({dist['under_1h']['percentage']}%)
• 1-5h: {dist['1_5h']['count']} games ({dist['1_5h']['percentage']}%)
• 5-20h: {dist['5_20h']['count']} games ({dist['5_20h']['percentage']}%)
• 20-100h: {dist['20_100h']['count']} games ({dist['20_100h']['percentage']}%)
• 100h+: {dist['over_100h']['count']} games ({dist['over_100h']['percentage']}%)

🏆 Most Played: **{most_played['name']}** ({most_played['playtime_hours']}h)"""
        sections.append(dist_text)

    # Recent activity
    if stats.get("recent_activity"):
        activity = stats["recent_activity"]
        recent_text = f"""🚀 **Recent Activity**
• Last 2 weeks: {activity['last_2_weeks']} hours
• Active games: {activity['active_games']}"""
        sections.append(recent_text)

    # Activity trends
    if stats.get("activity_trends"):
        trends = stats["activity_trends"]
        if isinstance(trends, dict) and "activity_level" in trends:
            trends_text = f"""📈 **Activity Trends**
• Activity Level: {trends['activity_level']}
• Recent Hours: {trends['recent_hours']}h
• Recent Games: {trends['recent_games_count']}
• Top Recent Genre: {trends['top_recent_genre']}"""
            sections.append(trends_text)

    # Review preferences
    if stats.get("review_preferences", {}).get("preferred_review_types"):
        review_prefs = stats["review_preferences"]
        pref_lines = []

        for pref in review_prefs["preferred_review_types"]:
            pref_lines.append(f"  • {pref['type']}: {pref['preference_percentage']}%")

        review_text = f"""⭐ **Review Preferences**
{chr(10).join(pref_lines)}
• Average Rating: {review_prefs['average_rating_preference']}%"""
        sections.append(review_text)

    # Insights
    if include_insights and stats.get("insights"):
        insights_lines = []
        for insight in stats["insights"]:
            insights_lines.append(f"• {insight}")

        insights_text = f"""💡 **Gaming Insights**
{chr(10).join(insights_lines)}"""
        sections.append(insights_text)

    return "\n\n".join(sections)
