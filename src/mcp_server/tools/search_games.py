"""Natural language game search tool"""

import logging
import re
from typing import Any

from aiohttp import ClientSession
from mcp.server.fastmcp import Context
from sqlalchemy.orm import joinedload

from mcp_server.cache import cache, search_cache_key
from mcp_server.enhanced_user_context import (
    format_elicitation_error,
    resolve_user_context_with_elicitation,
)
from mcp_server.server import mcp
from mcp_server.services.feature_extractor import FeatureExtractor
from mcp_server.services.genre_translator import GenreTranslator
from mcp_server.services.mood_mapper import MoodMapper
from mcp_server.services.similarity_finder import SimilarityFinder
from mcp_server.services.time_normalizer import TimeNormalizer
from mcp_server.utils.elicitation import (
    elicit_search_refinement,
    should_elicit_for_query,
)
from mcp_server.validation import SearchGamesInput
from shared.database import Game, UserGame, get_db

logger = logging.getLogger(__name__)


@mcp.tool()
async def search_games(ctx: Context, query: str, user_steam_id: str | None = None) -> str:
    """Natural language game search across your Steam library with intelligent parsing.

    Supports mood-based searches, genre detection, similarity matching, and contextual understanding.
    Examples: 'chill puzzle games', 'games like portal', 'something relaxing for tonight'
    """

    # Validate input
    try:
        input_data = SearchGamesInput(query=query, user_steam_id=user_steam_id)
    except Exception as e:
        return f"Invalid input: {str(e)}"

    # Try enhanced user context resolution with elicitation (ctx is always available now)
    user_context = await resolve_user_context_with_elicitation(input_data.user_steam_id, ctx, allow_elicitation=True)

    if "error" in user_context:
        error_msg = format_elicitation_error(user_context)
        return f"User error: {error_msg}"

    user = user_context["user"]

    # Check if query needs refinement via elicitation
    if should_elicit_for_query(input_data.query):
        refinement = await elicit_search_refinement(ctx, input_data.query)
        if refinement:
            # Apply refinement to query - this is a simplified approach
            # In a more sophisticated implementation, we'd merge this with the AI services
            logger.info(f"Applied search refinement: {refinement}")
            # For now, we'll pass the original query but log the refinement
            # Future enhancement: modify the search intent based on refinement

    # Generate cache key
    cache_key = search_cache_key(input_data.query, user.steam_id)

    async def compute_search_results():
        return await _perform_enhanced_search(user, input_data.query)

    # Get search results with caching
    results = await cache.get_or_compute(cache_key, compute_search_results, ttl=900)  # 15 min cache

    if not results:
        return "No games found matching your search. Try different keywords or check your library."

    # Format response
    search_context = _extract_search_context(input_data.query)
    context_desc = _format_search_context(search_context)
    results_text = _format_search_results(results)

    response = f"**Search Results for {user.persona_name}**{context_desc}\n\n{results_text}"

    return response


async def _perform_enhanced_search(user, query: str) -> list[dict[str, Any]]:
    """Perform enhanced search with natural language understanding"""

    # Parse search intent using translation services
    search_intent = await parse_enhanced_intent_with_services(query)

    with get_db() as session:
        # Get user's games with all related data
        base_query = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.categories), joinedload(UserGame.game).joinedload(Game.developers), joinedload(UserGame.game).joinedload(Game.reviews)).filter(UserGame.steam_id == user.steam_id)

        # Apply filters based on search intent
        if search_intent["playtime_filter"]:
            if search_intent["playtime_filter"] == "unplayed":
                base_query = base_query.filter(UserGame.playtime_forever == 0)
            elif search_intent["playtime_filter"] == "played":
                base_query = base_query.filter(UserGame.playtime_forever > 0)
            elif search_intent["playtime_filter"] == "recent":
                base_query = base_query.filter(UserGame.playtime_2weeks > 0)

        user_games = base_query.all()

        if not user_games:
            return []

            # Score and rank games based on search intent
        scored_games = []
        for ug in user_games:
            if ug.game:
                score = _calculate_search_score(ug, search_intent, user_games)
                if score > 0.1:  # Minimum relevance threshold
                    scored_games.append({"app_id": ug.game.app_id, "name": ug.game.name, "playtime_hours": round(ug.playtime_forever / 60, 1), "recent_playtime_hours": round(ug.playtime_2weeks / 60, 1), "genres": [g.genre_name for g in ug.game.genres] if ug.game.genres else [], "categories": [c.category_name for c in ug.game.categories] if ug.game.categories else [], "developers": [d.developer_name for d in ug.game.developers] if ug.game.developers else [], "score": score, "match_reasons": _generate_match_reasons(ug.game, search_intent), "review_data": {"summary": ug.game.reviews.review_summary, "positive_percentage": ug.game.reviews.positive_percentage} if ug.game.reviews else None})

        # Sort by relevance score
        scored_games.sort(key=lambda x: x["score"], reverse=True)

        return scored_games[:15]  # Top 15 results


async def parse_enhanced_intent_with_services(query: str) -> dict[str, Any]:
    """Parse search query using AI translation services"""

    intent = {"text_terms": [], "genres": [], "moods": [], "time_constraints": None, "playtime_filter": None, "similarity_target": None, "features": [], "developers": []}

    # Create a shared session for all services
    async with ClientSession() as session:
        # Initialize services
        genre_translator = GenreTranslator(session)
        mood_mapper = MoodMapper(session)
        time_normalizer = TimeNormalizer(session)
        feature_extractor = FeatureExtractor(session)
        similarity_finder = SimilarityFinder(session)

        # Extract components using services in parallel where possible
        try:
            # Check for similarity patterns first
            similar_game = await similarity_finder.extract_game_name(query)
            if similar_game:
                intent["similarity_target"] = similar_game
                # If we found a similarity target, get genres for that game type
                related_genres = await genre_translator.find_similar_genres(similar_game)
                intent["genres"].extend(related_genres)

            # Extract genres from the query
            genres = await genre_translator.translate_to_genres(query)
            intent["genres"].extend(genres)

            # Remove duplicates
            intent["genres"] = list(set(intent["genres"]))

            # Extract features
            features = await feature_extractor.extract_features(query)
            intent["features"] = features

            # Map mood if present
            # Look for mood-like words in the query
            mood_words = ["relaxing", "chill", "intense", "exciting", "creative", "social", "nostalgic", "calm", "peaceful", "action", "adrenaline"]
            for word in mood_words:
                if word in query.lower():
                    mood = await mood_mapper.map_to_mood(word)
                    if mood not in intent["moods"]:
                        intent["moods"].append(mood)
                    break

            # Check for time constraints
            time_words = ["quick", "hour", "minutes", "short", "long", "brief", "session"]
            if any(word in query.lower() for word in time_words):
                time_dict = await time_normalizer.normalize_time(query)
                # Convert to simple constraint
                if time_dict["max"] <= 60:
                    intent["time_constraints"] = "short"
                elif time_dict["min"] >= 180:
                    intent["time_constraints"] = "long"
                else:
                    intent["time_constraints"] = "medium"

        except Exception as e:
            logger.warning(f"Service error during intent parsing: {e}")
            # Fall back to basic parsing
            return parse_enhanced_intent_fallback(query)

        # Extract playtime filters (keep existing logic)
        query_lower = query.lower()
        if any(word in query_lower for word in ["unplayed", "never played", "haven't played"]):
            intent["playtime_filter"] = "unplayed"
        elif any(word in query_lower for word in ["played", "completed", "finished"]):
            intent["playtime_filter"] = "played"
        elif any(word in query_lower for word in ["recent", "lately", "currently"]):
            intent["playtime_filter"] = "recent"

        # Extract remaining text terms
        # Remove genre, mood, and feature words from query
        text_terms = query_lower
        for genre in intent["genres"]:
            text_terms = text_terms.replace(genre.lower(), "")
        for mood in intent["moods"]:
            text_terms = text_terms.replace(mood, "")
        for feature in intent["features"]:
            text_terms = text_terms.replace(feature.lower(), "")
        if intent["similarity_target"]:
            text_terms = text_terms.replace(intent["similarity_target"].lower(), "")
            text_terms = text_terms.replace("like", "")
            text_terms = text_terms.replace("similar to", "")

        # Clean up text terms
        text_terms = " ".join(text_terms.split())
        if text_terms:
            intent["text_terms"] = [term for term in text_terms.split() if len(term) > 2]

    return intent


def parse_enhanced_intent_fallback(query: str) -> dict[str, Any]:
    """Fallback parser if services fail"""

    query_lower = query.lower()

    intent = {"text_terms": [], "genres": [], "moods": [], "time_constraints": None, "playtime_filter": None, "similarity_target": None, "features": [], "developers": []}

    # Basic genre extraction
    common_genres = ["action", "adventure", "rpg", "strategy", "simulation", "puzzle", "racing", "sports", "shooter", "platformer", "fighting", "horror", "indie", "casual", "mmo", "fps"]

    for genre in common_genres:
        if genre in query_lower:
            intent["genres"].append(genre.title())

    # Basic mood extraction
    if any(word in query_lower for word in ["chill", "relax", "calm", "peaceful"]):
        intent["moods"].append("chill")
    elif any(word in query_lower for word in ["intense", "action", "exciting"]):
        intent["moods"].append("intense")

    # Basic time constraints
    if any(word in query_lower for word in ["quick", "short", "brief"]):
        intent["time_constraints"] = "short"
    elif any(word in query_lower for word in ["long", "deep", "extended"]):
        intent["time_constraints"] = "long"

    # Extract similarity targets
    similarity_patterns = [r"like\s+([a-zA-Z0-9\s]+?)(?:\s|$)", r"similar\s+to\s+([a-zA-Z0-9\s]+?)(?:\s|$)"]

    for pattern in similarity_patterns:
        matches = re.findall(pattern, query_lower)
        if matches:
            intent["similarity_target"] = matches[0].strip()
            break

    # Extract remaining text terms
    text_terms = query_lower
    for genre in common_genres:
        text_terms = text_terms.replace(genre, "")

    text_terms = " ".join(text_terms.split())
    if text_terms:
        intent["text_terms"] = [term for term in text_terms.split() if len(term) > 2]

    return intent


def _calculate_search_score(user_game, search_intent: dict[str, Any], all_user_games) -> float:
    """Calculate relevance score for a game based on search intent"""

    score = 0.0
    game = user_game.game

    # Similarity matching (highest priority for "like X" queries)
    if search_intent["similarity_target"]:
        # For similarity queries, prioritize games with matching characteristics
        similarity_score = _calculate_similarity_score(game, search_intent["similarity_target"], all_user_games)
        score += similarity_score * 0.6  # 60% weight for similarity

        # Reduce weight of other factors for similarity queries
        text_weight = 0.1
        genre_weight = 0.2
        mood_weight = 0.1
        feature_weight = 0.05
    else:
        # Normal weighting for non-similarity queries
        text_weight = 0.3
        genre_weight = 0.3
        mood_weight = 0.2
        feature_weight = 0.1

    # Text matching
    if search_intent["text_terms"]:
        text_score = 0.0
        game_text = f"{game.name} {' '.join([g.genre_name for g in game.genres])} {' '.join([d.developer_name for d in game.developers])}".lower()

        for term in search_intent["text_terms"]:
            if term in game_text:
                text_score += 1.0 / len(search_intent["text_terms"])

        score += text_score * text_weight

    # Genre matching (enhanced with AI-translated genres)
    if search_intent["genres"] and game.genres:
        genre_names = [g.genre_name for g in game.genres]
        genre_matches = sum(1 for genre in search_intent["genres"] if genre in genre_names)
        genre_score = genre_matches / len(search_intent["genres"])
        score += genre_score * genre_weight

    # Feature matching (new!)
    if search_intent["features"] and game.categories:
        category_names = [c.category_name.lower() for c in game.categories]
        feature_matches = sum(1 for feature in search_intent["features"] if feature.lower() in category_names)
        feature_score = feature_matches / len(search_intent["features"]) if search_intent["features"] else 0
        score += feature_score * feature_weight

    # Mood matching
    if search_intent["moods"]:
        mood_score = _calculate_mood_score(game, search_intent["moods"])
        score += mood_score * mood_weight

    # Time constraint matching (10% of score)
    if search_intent["time_constraints"]:
        time_score = _calculate_time_score(user_game, search_intent["time_constraints"])
        score += time_score * 0.1

    return min(score, 1.0)  # Cap at 1.0


def _calculate_similarity_score(game, target_name: str, all_user_games) -> float:
    """Calculate similarity score based on actual game characteristics from user's library"""

    # Find the target game in user's library
    target_game = None
    target_name_lower = target_name.lower()

    for ug in all_user_games:
        if ug.game and target_name_lower in ug.game.name.lower():
            target_game = ug.game
            break

    if not target_game:
        # Target game not found in library
        return 0.0

    # Don't match the game with itself
    if game.app_id == target_game.app_id:
        return 0.0

    score = 0.0

    # Genre matching (50% of similarity score)
    if game.genres and target_game.genres:
        game_genres = {g.genre_name for g in game.genres}
        target_genres = {g.genre_name for g in target_game.genres}

        # Calculate Jaccard similarity for genres
        intersection = game_genres & target_genres
        union = game_genres | target_genres

        if union:
            genre_score = len(intersection) / len(union)
            score += genre_score * 0.5

    # Category matching (30% of similarity score)
    if game.categories and target_game.categories:
        game_categories = {c.category_name for c in game.categories}
        target_categories = {c.category_name for c in target_game.categories}

        # Calculate Jaccard similarity for categories
        intersection = game_categories & target_categories
        union = game_categories | target_categories

        if union:
            category_score = len(intersection) / len(union)
            score += category_score * 0.3

    # Developer matching (20% of similarity score)
    if game.developers and target_game.developers:
        game_devs = {d.developer_name for d in game.developers}
        target_devs = {d.developer_name for d in target_game.developers}

        if game_devs & target_devs:
            score += 0.2  # Same developer

    return score


def _calculate_mood_score(game, moods: list[str]) -> float:
    """Calculate how well a game matches mood requirements"""

    # Updated mood mappings based on our mood mapper service
    mood_mappings = {"chill": ["Casual", "Puzzle", "Simulation", "Strategy", "Indie"], "intense": ["Action", "FPS", "Fighting", "Racing", "Shooter"], "creative": ["Simulation", "Strategy", "Indie", "Building", "Sandbox"], "social": ["MMO", "Sports", "Racing", "Party", "Co-op"], "nostalgic": ["Retro", "Indie", "Platformer", "Arcade", "Classic"]}

    if not game.genres:
        return 0.0

    game_genres = [g.genre_name for g in game.genres]
    total_score = 0.0

    for mood in moods:
        if mood in mood_mappings:
            mood_genres = mood_mappings[mood]
            matching_genres = set(game_genres) & set(mood_genres)
            if matching_genres:
                total_score += len(matching_genres) / len(mood_genres)

    return min(total_score / len(moods), 1.0) if moods else 0.0


def _calculate_time_score(user_game, time_constraint: str) -> float:
    """Calculate score based on time constraints"""

    avg_session_time = user_game.playtime_forever / max(1, user_game.playtime_forever // 60)  # Rough estimate

    if time_constraint == "short":
        # Prefer games good for short sessions
        return 1.0 if avg_session_time < 60 else 0.5  # Under 1 hour
    elif time_constraint == "long":
        # Prefer games good for long sessions
        return 1.0 if avg_session_time > 120 else 0.5  # Over 2 hours

    return 0.5  # Neutral


def _generate_match_reasons(game, search_intent: dict[str, Any]) -> list[str]:
    """Generate human-readable reasons why this game matches the search"""

    reasons = []

    # Similarity reasons (highest priority)
    if search_intent["similarity_target"]:
        reasons.append(f"Similar to {search_intent['similarity_target'].title()}")

    if search_intent["genres"] and game.genres:
        matching_genres = {g.genre_name for g in game.genres} & set(search_intent["genres"])
        if matching_genres:
            reasons.append(f"Matches genres: {', '.join(matching_genres)}")

    if search_intent["features"] and game.categories:
        category_names = [c.category_name for c in game.categories]
        matching_features = [f for f in search_intent["features"] if any(f.lower() in cat.lower() for cat in category_names)]
        if matching_features:
            reasons.append(f"Features: {', '.join(matching_features[:2])}")

    if search_intent["moods"]:
        mood_desc = {"chill": "relaxing gameplay", "intense": "action-packed experience", "creative": "creative gameplay", "social": "great for playing with others", "nostalgic": "classic gaming experience"}

        for mood in search_intent["moods"]:
            if mood in mood_desc:
                reasons.append(f"Good for {mood_desc[mood]}")

    if search_intent["text_terms"] and not reasons:
        reasons.append("Matches search terms")

    return reasons[:3]  # Limit to top 3 reasons


def _extract_search_context(query: str) -> dict[str, Any]:
    """Extract context information from search query"""

    return {"original_query": query, "has_mood": any(word in query.lower() for word in ["chill", "relax", "intense", "creative"]), "has_genre": any(word in query.lower() for word in ["action", "puzzle", "rpg", "strategy"]), "has_similarity": "like" in query.lower() or "similar" in query.lower()}


def _format_search_context(context: dict[str, Any]) -> str:
    """Format search context for display"""

    if context["has_mood"] or context["has_genre"] or context["has_similarity"]:
        return f" _{context['original_query']}_"

    return ""


def _format_search_results(results: list[dict[str, Any]]) -> str:
    """Format search results for display"""

    if not results:
        return "No matching games found."

    result_lines = []

    for game in results:
        # Basic info with confidence indicator
        confidence = "[HIGH]" if game["score"] > 0.8 else "[MED]" if game["score"] > 0.5 else "[LOW]"
        line = f"{confidence} **{game['name']}** ({game['playtime_hours']}h played"

        # Recent activity indicator
        if game["recent_playtime_hours"] > 0:
            line += f", {game['recent_playtime_hours']}h recent"

        line += ")"

        # Add genres
        if game["genres"]:
            top_genres = game["genres"][:3]
            line += f"\n  Genres: {', '.join(top_genres)}"

        # Add match reasons
        if game["match_reasons"]:
            reasons_text = " • ".join(game["match_reasons"])
            line += f"\n  Reasons: {reasons_text}"

        # Add review info if available
        if game["review_data"]:
            review = game["review_data"]
            line += f"\n  Reviews: {review['summary']} ({review['positive_percentage']}% positive)"

        result_lines.append(line)

    result = "\n\n".join(result_lines)

    if len(results) == 15:
        result += "\n\n*Showing top 15 results. Try more specific terms to narrow down.*"

    return result
