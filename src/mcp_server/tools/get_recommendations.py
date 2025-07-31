"""Intelligent game recommendations tool"""

import logging
from collections import Counter
from typing import Any

from aiohttp import ClientSession
from mcp.server.fastmcp import Context
from sqlalchemy.orm import joinedload

from mcp_server.cache import cache, user_cache_key
from mcp_server.enhanced_user_context import (
    format_elicitation_error,
    resolve_user_context_with_elicitation,
)
from mcp_server.server import mcp
from mcp_server.services.feature_extractor import FeatureExtractor
from mcp_server.services.genre_translator import GenreTranslator
from mcp_server.services.mood_mapper import MoodMapper
from mcp_server.services.time_normalizer import TimeNormalizer
from mcp_server.user_context import resolve_user_context
from shared.database import Game, UserGame, UserProfile, get_db

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_recommendations(
    steam_id: str | None = None,
    context: str | None = None,
    mood: str | None = None,
    time_constraint: str | None = None,
    genres: list[str] | None = None,
    features: list[str] | None = None,
    exclude_recent: bool = True,
    limit: int = 10,
    ctx: Context | None = None,
) -> str:
    """Get personalized game recommendations based on your library and preferences.

    Can be called two ways:
    1. Natural language: context="something relaxing for an hour"
    2. Direct params: mood="chill", time_constraint="1 hour"


    Args:
        steam_id: Steam ID of user (optional, will auto-resolve if not provided)
        context: Natural language description of what you want (e.g., "something relaxing for tonight")
        mood: Direct mood parameter ('chill', 'intense', 'creative', 'social', 'nostalgic')
        time_constraint: How long you want to play (e.g., "30 minutes", "a few hours")
        genres: List of genres to focus on
        features: List of features to look for (e.g., ["multiplayer", "co-op"])
        exclude_recent: Whether to exclude recently played games (default: True)
        limit: Maximum number of recommendations (default: 10)
    """

    # Try enhanced user context resolution with elicitation if available
    if ctx is not None:
        user_context = await resolve_user_context_with_elicitation(steam_id, ctx, allow_elicitation=True)
    else:
        # Fallback to standard resolution
        user_context = await resolve_user_context(steam_id)

    if "error" in user_context:
        error_msg = format_elicitation_error(user_context) if ctx else user_context.get("message", "Unknown error")
        return f"User error: {error_msg}"

    user = user_context["user"]

    # Parse context if provided (natural language)
    parsed_context = {}
    if context:
        parsed_context = await _parse_recommendation_context(context)

    # Merge explicit parameters with parsed context
    final_context = {
        "mood": mood or parsed_context.get("mood"),
        "time_constraint": time_constraint or parsed_context.get("time_constraint"),
        "genres": genres or parsed_context.get("genres", []),
        "features": features or parsed_context.get("features", []),
        "exclude_recent": exclude_recent,
        "limit": limit,
    }

    # Generate cache key
    cache_key = user_cache_key("recommendations", user.steam_id) + f"_{hash(str(final_context))}"

    async def compute_recommendations():
        return await _generate_recommendations(user, final_context)

    # Get recommendations with caching
    recommendations = await cache.get_or_compute(cache_key, compute_recommendations, ttl=3600)  # 1 hour cache

    if not recommendations:
        return "Unable to generate recommendations. Try playing some games first to build your profile."

    # Format response
    context_desc = _format_context_description(final_context)
    rec_text = _format_recommendations(recommendations[:limit])

    response_text = f"**Personalized Recommendations for {user.persona_name}**{context_desc}\n\n{rec_text}"

    return response_text


async def _parse_recommendation_context(context: str) -> dict[str, Any]:
    """Parse natural language context using AI services"""

    parsed = {
        "mood": None,
        "time_constraint": None,
        "genres": [],
        "features": [],
    }

    async with ClientSession() as session:
        # Initialize services
        mood_mapper = MoodMapper(session)
        time_normalizer = TimeNormalizer(session)
        genre_translator = GenreTranslator(session)
        feature_extractor = FeatureExtractor(session)

        try:
            # Extract mood from context
            mood_words = ["relaxing", "chill", "intense", "exciting", "creative", "social", "nostalgic"]
            for word in mood_words:
                if word in context.lower():
                    parsed["mood"] = await mood_mapper.map_to_mood(word)
                    break

            # Extract time constraint
            time_words = ["quick", "hour", "minutes", "short", "long", "brief"]
            if any(word in context.lower() for word in time_words):
                await time_normalizer.normalize_time(context)
                # Store the original phrase for later normalization
                parsed["time_constraint"] = context

            # Extract genres
            parsed["genres"] = await genre_translator.translate_to_genres(context)

            # Extract features
            parsed["features"] = await feature_extractor.extract_features(context)

        except Exception as e:
            logger.warning(f"Error parsing recommendation context: {e}")

    return parsed


async def _generate_recommendations(user: UserProfile, context: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate intelligent recommendations based on user's library and context"""

    with get_db() as session:
        # Analyze user's gaming profile
        user_profile = await _analyze_user_profile(session, user)

        if not user_profile["played_games"]:
            return []

        # Enhance context with genre expansion if genres provided
        enhanced_context = context.copy()
        if context.get("genres"):
            # Expand genres with similar ones
            async with ClientSession() as session_http:
                genre_translator = GenreTranslator(session_http)
                expanded_genres = set(context["genres"])
                for genre in context["genres"]:
                    similar = await genre_translator.find_similar_genres(genre)
                    expanded_genres.update(similar[:2])  # Add top 2 similar genres
                enhanced_context["genres"] = list(expanded_genres)

        # Get candidate games (unplayed or minimally played)
        candidates = await _get_candidate_games(session, user, enhanced_context)

        if not candidates:
            return []

        # Score and rank candidates
        scored_candidates = []
        for game in candidates:
            score = await _calculate_recommendation_score(game, user_profile, enhanced_context)
            if score > 0.1:  # Minimum relevance threshold
                scored_candidates.append({**game, "score": score, "reasons": await _generate_recommendation_reasons(game, user_profile, enhanced_context)})

        # Sort by score and return top recommendations
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates


async def _analyze_user_profile(session, user: UserProfile) -> dict[str, Any]:
    """Analyze user's gaming preferences from their library"""

    # Get user's games with playtime and genres
    user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.categories), joinedload(UserGame.game).joinedload(Game.reviews)).filter(UserGame.steam_id == user.steam_id).all()

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

    return {"played_games": played_games, "favorite_genres": favorite_genres, "preferred_categories": preferred_categories, "avg_playtime": avg_playtime, "recent_games": recent_games, "high_rating_games": high_rating_games, "total_games": len(user_games), "completion_rate": len(played_games) / len(user_games) if user_games else 0}


async def _get_candidate_games(session, user: UserProfile, context: dict[str, Any]) -> list[dict[str, Any]]:
    """Get candidate games for recommendations"""

    # Base query for games
    query = session.query(Game).options(joinedload(Game.genres), joinedload(Game.categories), joinedload(Game.reviews))

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

        # Apply feature filters
        if context.get("features"):
            game_categories = [c.category_name.lower() for c in game.categories]
            # Check if game has any of the requested features
            has_feature = False
            for feature in context["features"]:
                if any(feature.lower() in cat for cat in game_categories):
                    has_feature = True
                    break
            if not has_feature:
                continue

        # Apply genre filters
        if context.get("genres"):
            game_genres = [g.genre_name for g in game.genres]
            # Check if game has any of the requested genres
            if not any(genre in game_genres for genre in context["genres"]):
                continue

        candidates.append({"app_id": game.app_id, "name": game.name, "genres": [g.genre_name for g in game.genres] if game.genres else [], "categories": [c.category_name for c in game.categories] if game.categories else [], "maturity_rating": game.maturity_rating, "review_data": {"summary": game.reviews.review_summary, "positive_percentage": game.reviews.positive_percentage, "total_reviews": game.reviews.total_reviews} if game.reviews else None, "features": {"steam_deck_verified": game.steam_deck_verified, "controller_support": game.controller_support, "vr_support": game.vr_support}})

    return candidates


async def _calculate_recommendation_score(game: dict[str, Any], user_profile: dict[str, Any], context: dict[str, Any]) -> float:
    """Calculate recommendation score for a game based on user profile and context"""

    score = 0.0

    # If specific genres requested, prioritize those (30% of score)
    if context.get("genres"):
        requested_genre_score = 0.0
        if game["genres"]:
            matching_genres = set(game["genres"]) & set(context["genres"])
            requested_genre_score = len(matching_genres) / len(context["genres"])
        score += requested_genre_score * 0.3

        # Reduce weight of profile-based genre matching
        profile_genre_weight = 0.2
    else:
        # Normal weight for profile-based matching
        profile_genre_weight = 0.35

    # Profile-based genre matching
    genre_score = 0.0
    if game["genres"] and user_profile["favorite_genres"]:
        matching_genres = set(game["genres"]) & set(user_profile["favorite_genres"])
        genre_score = len(matching_genres) / len(user_profile["favorite_genres"])
    score += genre_score * profile_genre_weight

    # Feature matching (15% of score)
    if context.get("features"):
        feature_score = 0.0
        if game["categories"]:
            game_categories_lower = [c.lower() for c in game["categories"]]
            matching_features = sum(1 for feature in context["features"] if any(feature.lower() in cat for cat in game_categories_lower))
            feature_score = matching_features / len(context["features"])
        score += feature_score * 0.15

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

    time_constraint = context.get("time_constraint")
    if time_constraint:
        time_bonus = await _get_time_bonus_async(game, time_constraint, user_profile)
        context_score += time_bonus

    score += context_score * 0.15

    return min(score, 1.0)  # Cap at 1.0


def _get_mood_bonus(game: dict[str, Any], mood: str) -> float:
    """Get mood-based bonus for game recommendation"""

    # Updated mood mappings to match our mood mapper service
    mood_mappings = {"chill": {"genres": ["Simulation", "Puzzle", "Casual", "Strategy", "Indie"], "categories": ["Single-player", "Relaxing", "Casual", "Atmospheric"]}, "intense": {"genres": ["Action", "FPS", "Fighting", "Racing", "Shooter"], "categories": ["Fast-Paced", "Difficult", "Action", "Competitive"]}, "creative": {"genres": ["Simulation", "Strategy", "Indie", "Sandbox"], "categories": ["Building", "Sandbox", "Level Editor", "Moddable", "Design"]}, "social": {"genres": ["MMO", "Sports", "Party", "Fighting"], "categories": ["Multi-player", "Co-op", "Online Co-op", "Local Co-op", "MMO"]}, "nostalgic": {"genres": ["Retro", "Classic", "Arcade", "Indie", "Platformer"], "categories": ["2D", "Pixel Graphics", "Retro", "Classic"]}}

    if mood not in mood_mappings:
        return 0.0

    mapping = mood_mappings[mood]
    bonus = 0.0

    # Check genre matches
    if game["genres"]:
        genre_matches = set(game["genres"]) & set(mapping["genres"])
        bonus += len(genre_matches) * 0.15

    # Check category matches
    if game["categories"]:
        category_matches = set(game["categories"]) & set(mapping["categories"])
        bonus += len(category_matches) * 0.1

    return min(bonus, 0.5)  # Cap mood bonus


async def _get_time_bonus_async(game: dict[str, Any], time_constraint: str, user_profile: dict[str, Any]) -> float:
    """Get time-based bonus for game recommendation"""

    # Normalize the time constraint if it's a natural language phrase
    time_category = "medium"  # default

    if time_constraint:
        try:
            async with ClientSession() as session:
                time_normalizer = TimeNormalizer(session)
                time_dict = await time_normalizer.normalize_time(time_constraint)

                # Categorize based on max time
                if time_dict["max"] <= 60:
                    time_category = "quick"
                elif time_dict["max"] <= 180:
                    time_category = "medium"
                else:
                    time_category = "long"
        except Exception:
            # Fallback to simple keyword matching
            if any(word in time_constraint.lower() for word in ["quick", "short", "brief"]):
                time_category = "quick"
            elif any(word in time_constraint.lower() for word in ["long", "extended", "deep"]):
                time_category = "long"

    # Use user's average playtime as a baseline
    avg_playtime = user_profile.get("avg_playtime", 600)  # Default 10 hours

    if time_category == "quick":
        # Prefer games that are good for short sessions
        quick_categories = ["Casual", "Arcade", "Puzzle", "Party"]
        if any(cat in game["categories"] for cat in quick_categories):
            return 0.3
        # Penalize very long games slightly
        return 0.1 if avg_playtime < 300 else 0.0

    elif time_category == "medium":
        # Neutral bonus for medium time
        return 0.1

    elif time_category == "long":
        # Prefer deeper, longer games
        long_categories = ["RPG", "Strategy", "Open World", "Story Rich", "Simulation"]
        long_genres = ["RPG", "Strategy", "Simulation", "Adventure"]

        bonus = 0.0
        if any(cat in game["categories"] for cat in long_categories):
            bonus += 0.15
        if any(genre in game["genres"] for genre in long_genres):
            bonus += 0.15

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

    # Requested genre reasons
    if context.get("genres"):
        matching_requested = set(game["genres"]) & set(context["genres"])
        if matching_requested:
            reasons.append(f"Matches requested: {', '.join(list(matching_requested)[:2])}")

    # Feature-based reasons
    if context.get("features") and game["categories"]:
        game_categories_lower = [c.lower() for c in game["categories"]]
        matching_features = [f for f in context["features"] if any(f.lower() in cat for cat in game_categories_lower)]
        if matching_features:
            reasons.append(f"Has {', '.join(matching_features[:2])}")

    # Context-based reasons
    mood = context.get("mood")
    if mood:
        mood_reasons = {"chill": "Perfect for relaxing", "intense": "High-energy gameplay", "creative": "Great for expressing creativity", "social": "Fun to play with others", "nostalgic": "Classic gaming experience"}
        if mood in mood_reasons:
            reasons.append(mood_reasons[mood])

    # Time-based reasons
    if context.get("time_constraint"):
        quick_categories = ["Casual", "Arcade", "Puzzle", "Party"]
        long_categories = ["RPG", "Strategy", "Open World", "Story Rich"]

        if any(cat in game["categories"] for cat in quick_categories):
            reasons.append("Good for quick sessions")
        elif any(cat in game["categories"] for cat in long_categories):
            reasons.append("Deep, engaging experience")

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

    if context.get("time_constraint"):
        parts.append(f"Time: {context['time_constraint']}")

    if context.get("genres"):
        parts.append(f"Genres: {', '.join(context['genres'][:3])}")

    if context.get("features"):
        parts.append(f"Features: {', '.join(context['features'][:2])}")

    if context.get("exclude_recent") is False:
        parts.append("Including recent games")

    if parts:
        return f" _{', '.join(parts)}_"

    return ""


def _format_recommendations(recommendations: list[dict[str, Any]]) -> str:
    """Format recommendations for display"""

    if not recommendations:
        return "No recommendations available."

    rec_lines = []

    for _i, rec in enumerate(recommendations, 1):
        # Basic info with score indicator
        confidence = "[HIGH]" if rec["score"] > 0.8 else "[MED]" if rec["score"] > 0.6 else "[LOW]"
        line = f"{confidence} **{rec['name']}**"

        # Add genres
        if rec["genres"]:
            top_genres = rec["genres"][:2]
            line += f"\n  Genres: {', '.join(top_genres)}"

        # Add review info
        if rec["review_data"]:
            review = rec["review_data"]
            line += f"\n  Reviews: {review['summary']} ({review['positive_percentage']}% positive)"

        # Add reasons
        if rec["reasons"]:
            reasons_text = " • ".join(rec["reasons"])
            line += f"\n  Reasons: {reasons_text}"

        rec_lines.append(line)

    return "\n\n".join(rec_lines)
