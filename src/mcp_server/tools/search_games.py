"""Natural language game search tool"""

import logging
import re
from typing import Any

from sqlalchemy.orm import joinedload

from mcp_server.cache import cache, search_cache_key
from mcp_server.server import mcp
from mcp_server.user_context import resolve_user_context
from mcp_server.validation import SearchGamesInput
from shared.database import Game, UserGame, get_db

logger = logging.getLogger(__name__)


@mcp.tool()
async def search_games(query: str, user_steam_id: str | None = None) -> str:
    """Natural language game search across your Steam library with intelligent parsing.

    Supports mood-based searches, genre detection, similarity matching, and contextual understanding.
    Examples: 'chill puzzle games', 'games like portal', 'something relaxing for tonight'
    """

    # Validate input
    try:
        input_data = SearchGamesInput(query=query, user_steam_id=user_steam_id)
    except Exception as e:
        return f"Invalid input: {str(e)}"

    # Resolve user context
    user_context = await resolve_user_context(input_data.user_steam_id)
    if "error" in user_context:
        return f"User error: {user_context['message']}"

    user = user_context["user"]

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

    # Parse search intent
    search_intent = parse_enhanced_intent(query)

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
                score = _calculate_search_score(ug, search_intent)
                if score > 0.1:  # Minimum relevance threshold
                    scored_games.append({"app_id": ug.game.app_id, "name": ug.game.name, "playtime_hours": round(ug.playtime_forever / 60, 1), "recent_playtime_hours": round(ug.playtime_2weeks / 60, 1), "genres": [g.genre_name for g in ug.game.genres] if ug.game.genres else [], "categories": [c.category_name for c in ug.game.categories] if ug.game.categories else [], "developers": [d.developer_name for d in ug.game.developers] if ug.game.developers else [], "score": score, "match_reasons": _generate_match_reasons(ug.game, search_intent), "review_data": {"summary": ug.game.reviews.review_summary, "positive_percentage": ug.game.reviews.positive_percentage} if ug.game.reviews else None})

        # Sort by relevance score
        scored_games.sort(key=lambda x: x["score"], reverse=True)

        return scored_games[:15]  # Top 15 results


def parse_enhanced_intent(query: str) -> dict[str, Any]:
    """Parse search query to understand user intent"""

    query_lower = query.lower()

    intent = {"text_terms": [], "genres": [], "moods": [], "time_constraints": None, "playtime_filter": None, "similarity_target": None, "developers": []}

    # Extract mood indicators
    mood_patterns = {"chill": ["chill", "relax", "calm", "peaceful", "zen", "casual"], "intense": ["intense", "action", "adrenaline", "fast", "exciting"], "creative": ["creative", "build", "craft", "create", "design"], "story": ["story", "narrative", "plot", "tale", "adventure"], "competitive": ["competitive", "pvp", "multiplayer", "versus"]}

    for mood, keywords in mood_patterns.items():
        if any(keyword in query_lower for keyword in keywords):
            intent["moods"].append(mood)

    # Extract genre mentions
    common_genres = ["action", "adventure", "rpg", "strategy", "simulation", "puzzle", "racing", "sports", "shooter", "platformer", "fighting", "horror", "indie", "casual", "mmo", "fps"]

    for genre in common_genres:
        if genre in query_lower:
            intent["genres"].append(genre.title())

    # Extract time constraints
    if any(word in query_lower for word in ["quick", "short", "brief"]):
        intent["time_constraints"] = "short"
    elif any(word in query_lower for word in ["long", "deep", "extended"]):
        intent["time_constraints"] = "long"

    # Extract playtime filters
    if any(word in query_lower for word in ["unplayed", "never played", "haven't played"]):
        intent["playtime_filter"] = "unplayed"
    elif any(word in query_lower for word in ["played", "completed", "finished"]):
        intent["playtime_filter"] = "played"
    elif any(word in query_lower for word in ["recent", "lately", "currently"]):
        intent["playtime_filter"] = "recent"

    # Extract similarity targets ("like X", "similar to X")
    similarity_patterns = [r"like\s+([a-zA-Z0-9\s]+?)(?:\s|$)", r"similar\s+to\s+([a-zA-Z0-9\s]+?)(?:\s|$)"]

    for pattern in similarity_patterns:
        matches = re.findall(pattern, query_lower)
        if matches:
            intent["similarity_target"] = matches[0].strip()
            break

    # Extract remaining text terms (remove mood/genre words)
    text_terms = query_lower
    for mood_list in mood_patterns.values():
        for word in mood_list:
            text_terms = text_terms.replace(word, "")

    for genre in common_genres:
        text_terms = text_terms.replace(genre, "")

    # Clean up text terms
    text_terms = " ".join(text_terms.split())
    if text_terms:
        intent["text_terms"] = [term for term in text_terms.split() if len(term) > 2]

    return intent


def _calculate_search_score(user_game, search_intent: dict[str, Any]) -> float:
    """Calculate relevance score for a game based on search intent"""

    score = 0.0
    game = user_game.game

    # Text matching (40% of score)
    if search_intent["text_terms"]:
        text_score = 0.0
        game_text = f"{game.name} {' '.join([g.genre_name for g in game.genres])} {' '.join([d.developer_name for d in game.developers])}".lower()

        for term in search_intent["text_terms"]:
            if term in game_text:
                text_score += 1.0 / len(search_intent["text_terms"])

        score += text_score * 0.4

    # Genre matching (30% of score)
    if search_intent["genres"] and game.genres:
        genre_names = [g.genre_name.lower() for g in game.genres]
        genre_matches = sum(1 for genre in search_intent["genres"] if genre.lower() in genre_names)
        genre_score = genre_matches / len(search_intent["genres"])
        score += genre_score * 0.3

    # Mood matching (20% of score)
    if search_intent["moods"]:
        mood_score = _calculate_mood_score(game, search_intent["moods"])
        score += mood_score * 0.2

    # Time constraint matching (10% of score)
    if search_intent["time_constraints"]:
        time_score = _calculate_time_score(user_game, search_intent["time_constraints"])
        score += time_score * 0.1

    return min(score, 1.0)  # Cap at 1.0


def _calculate_mood_score(game, moods: list[str]) -> float:
    """Calculate how well a game matches mood requirements"""

    mood_mappings = {"chill": ["Casual", "Puzzle", "Simulation", "Strategy"], "intense": ["Action", "FPS", "Fighting", "Racing"], "creative": ["Simulation", "Strategy", "Indie", "Building"], "story": ["Adventure", "RPG", "Indie", "Story Rich"], "competitive": ["Action", "Sports", "Racing", "Strategy"]}

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

    if search_intent["genres"] and game.genres:
        matching_genres = {g.genre_name for g in game.genres} & set(search_intent["genres"])
        if matching_genres:
            reasons.append(f"Matches genres: {', '.join(matching_genres)}")

    if search_intent["moods"]:
        mood_desc = {"chill": "relaxing gameplay", "intense": "action-packed experience", "creative": "creative gameplay", "story": "rich narrative", "competitive": "competitive gameplay"}

        for mood in search_intent["moods"]:
            if mood in mood_desc:
                reasons.append(f"Good for {mood_desc[mood]}")

    if search_intent["text_terms"]:
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
        confidence = "🔥" if game["score"] > 0.8 else "⭐" if game["score"] > 0.5 else "💡"
        line = f"{confidence} **{game['name']}** ({game['playtime_hours']}h played"

        # Recent activity indicator
        if game["recent_playtime_hours"] > 0:
            line += f", {game['recent_playtime_hours']}h recent"

        line += ")"

        # Add genres
        if game["genres"]:
            top_genres = game["genres"][:3]
            line += f"\n  🎮 {', '.join(top_genres)}"

        # Add match reasons
        if game["match_reasons"]:
            reasons_text = " • ".join(game["match_reasons"])
            line += f"\n  💭 {reasons_text}"

        # Add review info if available
        if game["review_data"]:
            review = game["review_data"]
            line += f"\n  ⭐ {review['summary']} ({review['positive_percentage']}% positive)"

        result_lines.append(line)

    result = "\n\n".join(result_lines)

    if len(results) == 15:
        result += "\n\n💡 *Showing top 15 results. Try more specific terms to narrow down.*"

    return result
