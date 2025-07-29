"""Intelligent game recommendations tool"""

import logging
from collections import Counter
from typing import Any

from sqlalchemy.orm import joinedload

from mcp_server.cache import cache, user_cache_key
from mcp_server.server import mcp
from mcp_server.user_context import resolve_user_context
from mcp_server.validation import RecommendationsInput
from shared.database import Game, UserGame, UserProfile, get_db

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_recommendations(
    user_steam_id: str | None = None,
    context: dict | None = None
) -> str:
    """Get personalized game recommendations based on your library and preferences.
    
    Args:
        user_steam_id: Steam ID of user (optional, will auto-resolve if not provided)
        context: Context for recommendations with keys:
                - mood: 'chill', 'intense', 'creative', 'social', 'nostalgic'
                - time_available: 'quick' (<1h), 'medium' (1-3h), 'long' (3h+)
                - exclude_recent: true/false to exclude recently played games
                - with_friends: true/false to prioritize multiplayer games
    """

    # Validate input
    try:
        input_data = RecommendationsInput(
            user_steam_id=user_steam_id,
            context=context or {}
        )
    except Exception as e:
        return f"Invalid input: {str(e)}"

    # Resolve user context
    user_context = await resolve_user_context(input_data.user_steam_id)
    if "error" in user_context:
        return f"User error: {user_context['message']}"

    user = user_context["user"]
    context = input_data.context or {}

    # Generate cache key
    cache_key = user_cache_key("recommendations", user.steam_id) + f"_{hash(str(context))}"

    async def compute_recommendations():
        return await _generate_recommendations(user, context)

    # Get recommendations with caching
    recommendations = await cache.get_or_compute(cache_key, compute_recommendations, ttl=3600)  # 1 hour cache

    if not recommendations:
        return "Unable to generate recommendations. Try playing some games first to build your profile."

    # Format response
    context_desc = _format_context_description(context)
    rec_text = _format_recommendations(recommendations)

    response_text = f"**Personalized Recommendations for {user.persona_name}**{context_desc}\n\n{rec_text}"

    return response_text


async def _generate_recommendations(user: UserProfile, context: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate intelligent recommendations based on user's library and context"""

    with get_db() as session:
        # Analyze user's gaming profile
        user_profile = await _analyze_user_profile(session, user)

        if not user_profile["played_games"]:
            return []

        # Get candidate games (unplayed or minimally played)
        candidates = await _get_candidate_games(session, user, context)

        if not candidates:
            return []

        # Score and rank candidates
        scored_candidates = []
        for game in candidates:
            score = await _calculate_recommendation_score(game, user_profile, context)
            if score > 0.1:  # Minimum relevance threshold
                scored_candidates.append({
                    **game,
                    "score": score,
                    "reasons": await _generate_recommendation_reasons(game, user_profile, context)
                })

        # Sort by score and return top recommendations
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:8]  # Top 8 recommendations


async def _analyze_user_profile(session, user: UserProfile) -> dict[str, Any]:
    """Analyze user's gaming preferences from their library"""

    # Get user's games with playtime and genres
    user_games = session.query(UserGame).options(
        joinedload(UserGame.game).joinedload(Game.genres),
        joinedload(UserGame.game).joinedload(Game.categories),
        joinedload(UserGame.game).joinedload(Game.reviews)
    ).filter(UserGame.steam_id == user.steam_id).all()

    played_games = [ug for ug in user_games if ug.playtime_forever > 0]

    if not played_games:
        return {"played_games": [], "favorite_genres": [], "preferred_categories": []}

    # Calculate favorite genres (weighted by playtime)
    genre_scores = Counter()
    category_scores = Counter()
    total_playtime = sum(ug.playtime_forever for ug in played_games)

    for ug in played_games:
        if ug.game and ug.game.genres:
            weight = ug.playtime_forever / total_playtime
            for genre in ug.game.genres:
                genre_scores[genre.genre_name] += weight

        if ug.game and ug.game.categories:
            weight = ug.playtime_forever / total_playtime
            for category in ug.game.categories:
                category_scores[category.category_name] += weight

    # Get top genres and categories
    favorite_genres = [genre for genre, _ in genre_scores.most_common(5)]
    preferred_categories = [cat for cat, _ in category_scores.most_common(5)]

    # Calculate average playtime per game
    avg_playtime = total_playtime / len(played_games)

    # Identify gaming patterns
    recent_games = [ug for ug in played_games if ug.playtime_2weeks > 0]
    high_rating_games = []

    for ug in played_games:
        if ug.game and ug.game.reviews and ug.game.reviews.positive_percentage >= 80:
            high_rating_games.append(ug)

    return {
        "played_games": played_games,
        "favorite_genres": favorite_genres,
        "preferred_categories": preferred_categories,
        "avg_playtime": avg_playtime,
        "recent_games": recent_games,
        "high_rating_games": high_rating_games,
        "total_games": len(user_games),
        "completion_rate": len(played_games) / len(user_games) if user_games else 0
    }


async def _get_candidate_games(session, user: UserProfile, context: dict[str, Any]) -> list[dict[str, Any]]:
    """Get candidate games for recommendations"""

    # Base query for games
    query = session.query(Game).options(
        joinedload(Game.genres),
        joinedload(Game.categories),
        joinedload(Game.reviews)
    )

    # Get user's game IDs to check ownership/playtime
    user_game_map = {}
    user_games = session.query(UserGame).filter(UserGame.steam_id == user.steam_id).all()
    for ug in user_games:
        user_game_map[ug.app_id] = ug

    # Get all games with reviews
    all_games = query.filter(Game.reviews.has()).limit(500).all()

    # Filter candidates based on ownership and playtime
    candidates = []
    for game in all_games:
        user_game = user_game_map.get(game.app_id)

        # Skip if user has significant playtime
        if user_game and user_game.playtime_forever > 300:  # 5+ hours
            continue

        # Skip recently played if requested
        if context.get("exclude_recent") and user_game and user_game.playtime_2weeks > 0:
            continue

        # Apply multiplayer filter
        if context.get("with_friends"):
            multiplayer_cats = ["Multi-player", "Co-op", "Online Co-op", "Local Co-op"]
            if not any(cat.category_name in multiplayer_cats for cat in game.categories):
                continue

        candidates.append({
            "app_id": game.app_id,
            "name": game.name,
            "genres": [g.genre_name for g in game.genres] if game.genres else [],
            "categories": [c.category_name for c in game.categories] if game.categories else [],
            "maturity_rating": game.maturity_rating,
            "review_data": {
                "summary": game.reviews.review_summary,
                "positive_percentage": game.reviews.positive_percentage,
                "total_reviews": game.reviews.total_reviews
            } if game.reviews else None,
            "features": {
                "steam_deck_verified": game.steam_deck_verified,
                "controller_support": game.controller_support,
                "vr_support": game.vr_support
            }
        })

    return candidates


async def _calculate_recommendation_score(game: dict[str, Any], user_profile: dict[str, Any], context: dict[str, Any]) -> float:
    """Calculate recommendation score for a game based on user profile and context"""

    score = 0.0

    # Genre matching (40% of score)
    genre_score = 0.0
    if game["genres"] and user_profile["favorite_genres"]:
        matching_genres = set(game["genres"]) & set(user_profile["favorite_genres"])
        genre_score = len(matching_genres) / len(user_profile["favorite_genres"])
    score += genre_score * 0.4

    # Category matching (20% of score)
    category_score = 0.0
    if game["categories"] and user_profile["preferred_categories"]:
        matching_categories = set(game["categories"]) & set(user_profile["preferred_categories"])
        category_score = len(matching_categories) / len(user_profile["preferred_categories"])
    score += category_score * 0.2

    # Review quality (25% of score)
    review_score = 0.0
    if game["review_data"]:
        positive_pct = game["review_data"]["positive_percentage"]
        total_reviews = game["review_data"]["total_reviews"]

        # Higher positive percentage = better score
        review_score = positive_pct / 100.0

        # Bonus for games with many reviews (confidence boost)
        if total_reviews > 1000:
            review_score *= 1.1
        elif total_reviews > 100:
            review_score *= 1.05
    score += review_score * 0.25

    # Context-based adjustments (15% of score)
    context_score = 0.0

    mood = context.get("mood")
    if mood:
        mood_bonus = _get_mood_bonus(game, mood)
        context_score += mood_bonus

    time_available = context.get("time_available")
    if time_available:
        time_bonus = _get_time_bonus(game, time_available, user_profile)
        context_score += time_bonus

    if context.get("with_friends"):
        multiplayer_cats = ["Multi-player", "Co-op", "Online Co-op", "Local Co-op"]
        if any(cat in game["categories"] for cat in multiplayer_cats):
            context_score += 0.3

    score += context_score * 0.15

    return min(score, 1.0)  # Cap at 1.0


def _get_mood_bonus(game: dict[str, Any], mood: str) -> float:
    """Get mood-based bonus for game recommendation"""

    mood_mappings = {
        "chill": {
            "genres": ["Simulation", "Puzzle", "Casual", "Strategy"],
            "categories": ["Single-player", "Relaxing"]
        },
        "intense": {
            "genres": ["Action", "FPS", "Fighting", "Racing"],
            "categories": ["Fast-Paced", "Difficult"]
        },
        "creative": {
            "genres": ["Simulation", "Strategy", "Indie"],
            "categories": ["Building", "Sandbox", "Level Editor"]
        },
        "social": {
            "genres": ["MMO", "Sports"],
            "categories": ["Multi-player", "Co-op", "Online Co-op"]
        },
        "nostalgic": {
            "genres": ["Retro", "Classic", "Arcade"],
            "categories": ["2D", "Pixel Graphics"]
        }
    }

    if mood not in mood_mappings:
        return 0.0

    mapping = mood_mappings[mood]
    bonus = 0.0

    # Check genre matches
    genre_matches = set(game["genres"]) & set(mapping["genres"])
    bonus += len(genre_matches) * 0.1

    # Check category matches
    category_matches = set(game["categories"]) & set(mapping["categories"])
    bonus += len(category_matches) * 0.1

    return min(bonus, 0.5)  # Cap mood bonus


def _get_time_bonus(game: dict[str, Any], time_available: str, user_profile: dict[str, Any]) -> float:
    """Get time-based bonus for game recommendation"""

    # Use user's average playtime as a baseline
    avg_playtime = user_profile.get("avg_playtime", 600)  # Default 10 hours

    if time_available == "quick":
        # Prefer games that are good for short sessions
        quick_categories = ["Casual", "Arcade", "Puzzle"]
        if any(cat in game["categories"] for cat in quick_categories):
            return 0.2
        # Penalize very long games slightly
        return 0.1 if avg_playtime < 300 else 0.0

    elif time_available == "medium":
        # Neutral bonus for medium time
        return 0.1

    elif time_available == "long":
        # Prefer deeper, longer games
        long_categories = ["RPG", "Strategy", "Open World", "Story Rich"]
        long_genres = ["RPG", "Strategy", "Simulation"]

        bonus = 0.0
        if any(cat in game["categories"] for cat in long_categories):
            bonus += 0.1
        if any(genre in game["genres"] for genre in long_genres):
            bonus += 0.1

        return bonus

    return 0.0


async def _generate_recommendation_reasons(game: dict[str, Any], user_profile: dict[str, Any], context: dict[str, Any]) -> list[str]:
    """Generate human-readable reasons for the recommendation"""

    reasons = []

    # Genre-based reasons
    matching_genres = set(game["genres"]) & set(user_profile["favorite_genres"])
    if matching_genres:
        if len(matching_genres) == 1:
            reasons.append(f"You love {list(matching_genres)[0]} games")
        else:
            reasons.append(f"Combines your favorite genres: {', '.join(list(matching_genres)[:2])}")

    # Review quality reasons
    if game["review_data"]:
        positive_pct = game["review_data"]["positive_percentage"]
        if positive_pct >= 95:
            reasons.append("Overwhelmingly positive reviews")
        elif positive_pct >= 85:
            reasons.append("Highly rated by players")
        elif positive_pct >= 75:
            reasons.append("Well-reviewed game")

    # Context-based reasons
    mood = context.get("mood")
    if mood:
        mood_reasons = {
            "chill": "Perfect for relaxing",
            "intense": "High-energy gameplay",
            "creative": "Great for expressing creativity",
            "social": "Fun to play with others",
            "nostalgic": "Classic gaming experience"
        }
        if mood in mood_reasons:
            reasons.append(mood_reasons[mood])

    if context.get("with_friends"):
        multiplayer_cats = ["Multi-player", "Co-op", "Online Co-op", "Local Co-op"]
        if any(cat in game["categories"] for cat in multiplayer_cats):
            reasons.append("Great for playing with friends")

    # Feature-based reasons
    features = game["features"]
    if features.get("steam_deck_verified"):
        reasons.append("Steam Deck verified")
    if features.get("controller_support"):
        reasons.append("Controller support")

    # Default reason if no specific matches
    if not reasons:
        reasons.append("Popular choice among similar players")

    return reasons[:3]  # Limit to top 3 reasons


def _format_context_description(context: dict[str, Any]) -> str:
    """Format context description for display"""

    if not context:
        return ""

    parts = []

    if context.get("mood"):
        parts.append(f"Mood: {context['mood']}")

    if context.get("time_available"):
        time_desc = {
            "quick": "quick session",
            "medium": "medium session",
            "long": "long session"
        }
        parts.append(f"Time: {time_desc.get(context['time_available'], context['time_available'])}")

    if context.get("with_friends"):
        parts.append("With friends")

    if context.get("exclude_recent"):
        parts.append("Excluding recent games")

    if parts:
        return f" _{', '.join(parts)}_"

    return ""


def _format_recommendations(recommendations: list[dict[str, Any]]) -> str:
    """Format recommendations for display"""

    if not recommendations:
        return "No recommendations available."

    rec_lines = []

    for i, rec in enumerate(recommendations, 1):
        # Basic info with score indicator
        confidence = "🔥" if rec["score"] > 0.8 else "⭐" if rec["score"] > 0.6 else "💡"
        line = f"{confidence} **{rec['name']}**"

        # Add genres
        if rec["genres"]:
            top_genres = rec["genres"][:2]
            line += f"\n  🎮 {', '.join(top_genres)}"

        # Add review info
        if rec["review_data"]:
            review = rec["review_data"]
            line += f"\n  ⭐ {review['summary']} ({review['positive_percentage']}% positive)"

        # Add reasons
        if rec["reasons"]:
            reasons_text = " • ".join(rec["reasons"])
            line += f"\n  💭 {reasons_text}"

        rec_lines.append(line)

    return "\n\n".join(rec_lines)
