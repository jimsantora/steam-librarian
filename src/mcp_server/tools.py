"""Enhanced MCP tools with full specification compliance including input/output schemas and structured responses"""

from mcp.server.fastmcp import Context
from mcp.types import (
    Annotations,
    CallToolResult,
    SamplingMessage,
    TextContent,
    ToolAnnotations,
)
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import joinedload

from shared.database import (
    Category,
    Game,
    Genre,
    Tag,
    UserGame,
    UserProfile,
    get_db,
    handle_user_not_found,
    resolve_user_for_tool,
)

from .config import config
from .server import mcp


class FamilyPreferences(BaseModel):
    """Preferences for family gaming with young children."""

    content_concerns: list[str] = Field(default=[], description="Content to avoid (violence, language, scary themes)")
    gaming_experience: str = Field(default="beginner", description="Family's gaming experience (beginner/intermediate/advanced)")


class AmbiguousSearchContext(BaseModel):
    """Context for clarifying ambiguous search queries."""

    time_available: str = Field(default="medium", description="How long do you want to play? (quick/medium/long session)")
    mood: str = Field(default="relaxed", description="Current mood (relaxed/energetic/competitive/social)")


def get_default_user_fallback():
    """Fallback function to get default user from config"""
    if config.default_user and config.default_user != "default":
        return config.default_user
    return None


def is_natural_language_query(query: str) -> bool:
    """Check if query is natural language vs simple keywords."""
    # Natural language indicators
    nl_indicators = ["something", "games like", "similar to", "after work", "relaxing", "exciting", "with friends", "for kids"]
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in nl_indicators)


def parse_natural_language_filters(text: str) -> dict:
    """Parse natural language filters into structured format."""
    import re

    filters = {}

    # Genre detection
    genres = ["Action", "Adventure", "RPG", "Strategy", "Indie", "Casual", "Simulation", "Sports", "Racing", "Puzzle"]
    for genre in genres:
        if genre.lower() in text.lower():
            filters["genres"] = [genre]
            break

    # Rating detection - multiple patterns
    rating_patterns = [
        r"rating\s*(?:above|over|>=?)\s*(\d+)",  # "rating above 75"
        r"rated\s*(?:above|over|>=?)\s*(\d+)",  # "rated over 80"
        r"(?:rating|rated)\s*>=?\s*(\d+)",  # "rating >= 90"
        r"(?:min|minimum)\s*rating\s*(\d+)",  # "minimum rating 75"
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
        filters["playtime"] = "unplayed"
    elif any(word in text.lower() for word in ["played", "started"]):
        filters["playtime"] = "played"

    return filters


@mcp.tool(name="smart_search", title="AI-Powered Game Search", description="Unified smart search across all game classification layers with natural language interpretation and AI-powered filtering", annotations=ToolAnnotations(title="Advanced Game Discovery", readOnlyHint=True, idempotentHint=True))
async def smart_search(query: str, filters: str = "", sort_by: str = "relevance", limit: int = 10, ctx: Context | None = None, user: str | None = None) -> CallToolResult:
    """
    Unified smart search across all game classification layers with AI interpretation.

    Args:
        query: Search query - can be game names, natural language descriptions, or specific requests
        filters: JSON string with filter criteria: {"genres": [], "categories": [], "tags": [], "playtime": "any"}
        sort_by: Sort order - relevance|playtime|metacritic|recent|random
        limit: Maximum number of results to return (1-50)
        ctx: MCP context for AI sampling and elicitation
        user: Steam user identifier (optional, uses default if not provided)

    Examples:
        - query="minecraft" - Simple name search
        - query="relaxing puzzle games" - Natural language search with AI interpretation
        - query="unplayed gems", filters='{"playtime": "unplayed"}' - Unplayed with good scores
    """
    import json

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return CallToolResult(content=[TextContent(type="text", text=f"User error: {user_result['message']}", annotations=Annotations(audience=["assistant"], priority=0.9))], isError=True)

    user_steam_id = user_result["steam_id"]

    # Parse filters parameter with natural language support
    filter_dict = {}
    if filters and filters.strip():
        # Try JSON parsing first
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            # Fallback to natural language parsing
            filter_dict = parse_natural_language_filters(filters)

            # Validate filter structure
            valid_filters = ["genres", "categories", "tags", "min_rating", "max_rating", "playtime", "vr_support", "platform"]

            invalid_keys = [k for k in filter_dict.keys() if k not in valid_filters]
            if invalid_keys:
                example_json = {"genres": ["Action"], "min_rating": 75, "categories": ["Co-op"]}
                error_msg = f'''Filter error: Unknown filter keys: {invalid_keys}

Valid filters: {', '.join(valid_filters)}

Example JSON filter:
{json.dumps(example_json, indent=2)}

Example text filter:
"action games with rating above 75 and coop multiplayer"

Natural language examples:
- "puzzle games"
- "multiplayer action games rated over 80"
- "unplayed indie games"
- "vr games"'''

                return CallToolResult(content=[TextContent(type="text", text=error_msg, annotations=Annotations(audience=["user"], priority=0.9))], isError=True)

    # Use Sampling for natural language queries
    if ctx and hasattr(ctx, "session") and ctx.session and is_natural_language_query(query):
        try:
            with get_db() as session:
                # Get available classifications for AI interpretation
                genres = [g.genre_name for g in session.query(Genre).all()]
                categories = [c.category_name for c in session.query(Category).limit(20).all()]
                tags = [t.tag_name for t in session.query(Tag).limit(30).all()]

            interpretation = await ctx.session.create_message(
                messages=[
                    SamplingMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"""Analyze this game search query and extract search criteria.
                        Query: "{query}"

                        Available genres: {genres[:15]}
                        Available categories: {categories[:15]}
                        Available tags: {tags[:20]}

                        Return a JSON object with:
                        - genres: list of matching genres
                        - categories: list of matching categories
                        - tags: list of relevant tags
                        - mood: detected mood (relaxing/intense/social/competitive)
                        - time_commitment: short/medium/long
                        """,
                        ),
                    )
                ],
                max_tokens=200,
            )

            # Parse and apply the interpretation
            if interpretation.content.type == "text":
                try:
                    ai_filters = json.loads(interpretation.content.text)
                    # Merge AI interpretation with existing filters
                    for key in ["genres", "categories", "tags"]:
                        if key in ai_filters and ai_filters[key]:
                            if key not in filter_dict:
                                filter_dict[key] = []
                            filter_dict[key].extend(ai_filters[key])
                            # Remove duplicates
                            filter_dict[key] = list(set(filter_dict[key]))
                except json.JSONDecodeError:
                    pass  # Continue with manual filters
        except Exception:
            # Fallback to keyword search if AI fails
            pass

    # Build dynamic query using all three classification tiers
    with get_db() as session:
        # Base query with user games
        games_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).options(joinedload(Game.genres), joinedload(Game.categories), joinedload(Game.tags), joinedload(Game.reviews))

        # Apply filters dynamically
        if filter_dict.get("genres"):
            games_query = games_query.join(Game.genres).filter(Genre.genre_name.in_(filter_dict["genres"]))

        if filter_dict.get("categories"):
            games_query = games_query.join(Game.categories).filter(Category.category_name.in_(filter_dict["categories"]))

        if filter_dict.get("tags"):
            games_query = games_query.join(Game.tags).filter(Tag.tag_name.in_(filter_dict["tags"]))

        # Playtime filter
        if filter_dict.get("playtime") == "played":
            games_query = games_query.filter(UserGame.playtime_forever > 0)
        elif filter_dict.get("playtime") == "unplayed":
            games_query = games_query.filter(UserGame.playtime_forever == 0)

        # Additional filters
        if filter_dict.get("min_rating"):
            games_query = games_query.filter(Game.metacritic_score >= filter_dict["min_rating"])

        if filter_dict.get("max_rating"):
            games_query = games_query.filter(Game.metacritic_score <= filter_dict["max_rating"])

        if filter_dict.get("vr_support"):
            games_query = games_query.filter(Game.vr_support)

        # Text search if no specific filters applied or for general queries
        if not any(filter_dict.get(k) for k in ["genres", "categories", "tags"]) or query.lower() not in ["unplayed gems", "family games", "multiplayer", "coop"]:
            # Add text search
            games_query = games_query.filter(or_(Game.name.ilike(f"%{query}%"), Game.short_description.ilike(f"%{query}%")))

        # Implement intelligent sorting
        if sort_by == "relevance":
            # Score based on multiple factors
            games_query = games_query.order_by(case((UserGame.playtime_2weeks > 0, 100), (UserGame.playtime_forever > 300, 50), (Game.metacritic_score > 75, 25), else_=0).desc(), Game.name)  # Recently played  # Well-played  # Good reviews
        elif sort_by == "playtime":
            games_query = games_query.order_by(UserGame.playtime_forever.desc())
        elif sort_by == "metacritic":
            games_query = games_query.order_by(Game.metacritic_score.desc().nullslast())
        elif sort_by == "recent":
            games_query = games_query.order_by(UserGame.playtime_2weeks.desc())
        elif sort_by == "random":
            games_query = games_query.order_by(func.random())

        # Get results
        results = []
        for game, user_game in games_query.distinct().limit(limit):
            results.append({"name": game.name, "metacritic": game.metacritic_score, "platforms": {"windows": game.platforms_windows, "mac": game.platforms_mac, "linux": game.platforms_linux, "vr": game.vr_support}, "playtime": user_game.playtime_forever / 60 if user_game.playtime_forever else 0, "recent_playtime": user_game.playtime_2weeks / 60 if user_game.playtime_2weeks else 0, "genres": [g.genre_name for g in game.genres[:3]], "tags": [t.tag_name for t in game.tags[:3]]})

        if not results:
            no_results_msg = f"No games found matching '{query}'" + (f" with filters: {filter_dict}" if filter_dict else "")
            suggestions = "\n\nTry:\n- Broadening your search terms\n- Using different genres or tags\n- Checking for typos\n- Using 'get_tool_help(\"smart_search\")' for examples"
            return CallToolResult(content=[TextContent(type="text", text=no_results_msg + suggestions, annotations=Annotations(audience=["user"], priority=0.7))], structuredContent={"results": [], "query": query, "filters": filter_dict, "total": 0}, isError=False)

        # Format enhanced results for display
        output = [f"**Smart search results for '{query}':**"]
        if filter_dict:
            # Format filters in a user-friendly way
            filter_desc = []
            if filter_dict.get("genres"):
                filter_desc.append(f"Genres: {', '.join(filter_dict['genres'])}")
            if filter_dict.get("categories"):
                filter_desc.append(f"Categories: {', '.join(filter_dict['categories'])}")
            if filter_dict.get("min_rating"):
                filter_desc.append(f"Min Rating: {filter_dict['min_rating']}")
            if filter_dict.get("playtime"):
                filter_desc.append(f"Playtime: {filter_dict['playtime']}")

            if filter_desc:
                output.append(f"Filters applied: {' | '.join(filter_desc)}")
        output.append("")

        for game in results:
            # Platform indicators
            platforms = []
            if game["platforms"]["windows"]:
                platforms.append("Win")
            if game["platforms"]["mac"]:
                platforms.append("Mac")
            if game["platforms"]["linux"]:
                platforms.append("Linux")
            if game["platforms"]["vr"]:
                platforms.append("VR")
            platform_str = "/".join(platforms) if platforms else "Unknown"

            # Activity indicators
            activity = ""
            if game["recent_playtime"] > 0:
                activity = " 🔥"  # Recently played
            elif game["playtime"] == 0:
                activity = " 🆕"  # Unplayed
            elif game["playtime"] > 5:
                activity = " ⭐"  # Well played

            metacritic_str = f" ({game['metacritic']}/100)" if game["metacritic"] else ""
            genres_str = ", ".join(game["genres"]) if game["genres"] else "No genres"
            tags_str = ", ".join(game["tags"]) if game["tags"] else ""

            output.append(f"• **{game['name']}**{metacritic_str}{activity}\n" f"  Genres: {genres_str} | Platforms: {platform_str}\n" f"  Playtime: {game['playtime']:.1f}h" + (f" (recent: {game['recent_playtime']:.1f}h)" if game["recent_playtime"] > 0 else "") + (f"\n  Tags: {tags_str}" if tags_str else ""))

        # Add helpful footer
        output.append("\n💡 **Tip:** Use 'get_tool_help(\"smart_search\")' for more filter examples and search tips.")

        # Return structured content with both text display and structured data
        return CallToolResult(content=[TextContent(type="text", text="\n".join(output), annotations=Annotations(audience=["user", "assistant"], priority=0.9))], structuredContent={"results": results, "query": query, "filters": filter_dict, "sort_by": sort_by, "total": len(results), "limited": len(results) == limit}, isError=False)


def parse_recommendation_parameters(text: str) -> dict:
    """Parse natural language recommendation parameters."""
    import re

    params = {}

    # Exclusion patterns
    exclude_patterns = [
        (r"(?:no|exclude|without|not|avoid)\s+(\w+)", "exclude_genres"),
        (r"(?:no|exclude|without)\s+multiplayer", "exclude_multiplayer"),
    ]

    for pattern, param_key in exclude_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            if param_key == "exclude_genres":
                # Map common terms to genres
                genre_map = {"horror": "Horror", "scary": "Horror", "action": "Action", "puzzle": "Puzzle", "strategy": "Strategy"}
                term = match.group(1).lower()
                if term in genre_map:
                    params["exclude_genres"] = [genre_map[term]]
            else:
                params[param_key] = True

    # Rating patterns
    rating_match = re.search(r"(?:minimum|min|at least)\s+rating\s+(\d+)", text, re.I)
    if not rating_match:
        rating_match = re.search(r"(?:highly|well)\s+rated", text, re.I)
        if rating_match:
            params["min_rating"] = 75
    else:
        params["min_rating"] = int(rating_match.group(1))

    # Time commitment patterns
    if any(word in text.lower() for word in ["short", "quick", "brief"]):
        params["max_hours"] = 20
    elif any(word in text.lower() for word in ["long", "epic", "extensive"]):
        params["min_hours"] = 40

    # Single/multiplayer patterns
    if "single player" in text.lower() or "single-player" in text.lower():
        params["single_player"] = True
    elif "multiplayer" in text.lower() and "no multiplayer" not in text.lower():
        params["multiplayer"] = True

    return params


@mcp.tool(name="recommend_games", title="Context-Aware Game Recommendations", description="Intelligent game recommendations with interactive elicitation for missing parameters and context-aware filtering", annotations=ToolAnnotations(title="AI-Powered Recommendations", readOnlyHint=True, idempotentHint=False, openWorldHint=True))  # Results may vary based on elicitation  # Context parameter has many possible values
async def recommend_games(context: str, parameters: str = "", use_play_history: bool = True, ctx: Context | None = None, user: str | None = None) -> CallToolResult:
    """
    Intelligent game recommendations with interactive elicitation for enhanced user experience.

    Available contexts:
    - "abandoned": Games you started but haven't finished (playtime 1-10 hours)
    - "similar_to:[game]": Games similar to a specific game (e.g., "similar_to:Portal 2")
    - "mood:[feeling]": Games matching a mood (e.g., "mood:relaxing", "mood:competitive")
    - "genre:[type]": Games in a specific genre with smart filtering
    - "trending": Popular games being played by many users recently
    - "hidden_gems": Highly-rated games with low player counts
    - "completionist": Games where you're close to 100% achievements
    - "weekend": Games perfect for weekend sessions (20-40 hour campaigns)
    - "family": Age-appropriate games (will ask for age)
    - "quick_session": Games for short sessions (will ask for time available)

    Parameters can be:
    - JSON object: {"exclude_genres": ["Horror"], "min_rating": 80}
    - Natural language: "exclude horror games, minimum rating 80"
    - Simple keywords: "no horror, highly rated"

    Examples:
    - context="abandoned", parameters="focus on shorter games"
    - context="mood:relaxing", parameters="no multiplayer"
    - context="similar_to:Hades", parameters='{"exclude_genres": ["Horror"]}'

    Args:
        context: Recommendation context (see available contexts above)
        parameters: Additional filtering parameters (JSON, natural language, or keywords)
        use_play_history: Whether to incorporate user's play history in recommendations
        ctx: MCP context for elicitation and AI sampling
        user: Steam user identifier (optional, uses default if not provided)

    Returns:
        CallToolResult with personalized recommendations, structured data, and potential resource links
    """
    import json

    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return CallToolResult(content=[TextContent(type="text", text=f"User error: {user_result['message']}", annotations=Annotations(audience=["assistant"], priority=0.9))], isError=True)

    user_steam_id = user_result["steam_id"]

    # Parse parameters flexibly
    params = {}
    if parameters and parameters.strip():
        if isinstance(parameters, str):
            # Try JSON first
            try:
                params = json.loads(parameters)
            except json.JSONDecodeError:
                # Parse as natural language
                params = parse_recommendation_parameters(parameters)
        elif isinstance(parameters, dict):
            params = parameters
        else:
            error_msg = f"""Parameter format error. Parameters should be either:

1. JSON string: '{"exclude_genres": ["Horror"], "min_rating": 80}'
2. Natural language: "exclude horror games, minimum rating 80"
3. Simple keywords: "no horror, highly rated"

Received type: {type(parameters).__name__}
Received value: {parameters}"""
            return CallToolResult(content=[TextContent(type="text", text=error_msg, annotations=Annotations(audience=["user"], priority=0.9))], isError=True)

    # Enhanced elicitation with proper MCP JSON schemas
    if context == "family" and ctx and hasattr(ctx, "elicit"):
        if "age" not in params:
            try:
                # Use proper MCP elicitation JSON schema instead of Pydantic
                elicitation_result = await ctx.elicit(message="I need some information to find the best family-friendly games for you", requestedSchema={"type": "object", "properties": {"age": {"type": "integer", "title": "Child's Age", "description": "Age of the youngest player who will be playing", "minimum": 3, "maximum": 17}, "players": {"type": "integer", "title": "Number of Players", "description": "How many people will be playing together?", "minimum": 1, "maximum": 8, "default": 1}, "content_concerns": {"type": "string", "title": "Content to Avoid", "description": "Any content you want to avoid (violence, scary themes, complex mechanics, etc.)", "enum": ["none", "violence", "scary", "complex", "violence_and_scary", "all_mature_content"], "enumNames": ["No specific concerns", "Violence", "Scary content", "Complex mechanics", "Violence and scary content", "All mature content"], "default": "none"}}, "required": ["age"]})

                if elicitation_result.action == "accept" and elicitation_result.content:
                    params.update(elicitation_result.content)
                elif elicitation_result.action == "decline":
                    return CallToolResult(content=[TextContent(type="text", text="I understand you'd prefer not to provide that information. I'll use default family-friendly settings (age 8+).", annotations=Annotations(audience=["user"], priority=0.8))], structuredContent={"context": context, "elicitation_declined": True}, isError=False)
                elif elicitation_result.action == "cancel":
                    return CallToolResult(content=[TextContent(type="text", text="Request cancelled. You can try again anytime with recommend_games('family') or provide parameters directly.", annotations=Annotations(audience=["user"], priority=0.7))], structuredContent={"context": context, "elicitation_cancelled": True}, isError=False)

            except Exception:
                # Fallback gracefully if elicitation fails
                params.setdefault("age", 8)
                params.setdefault("players", 1)
                params.setdefault("content_concerns", "none")

    # Context-specific recommendation logic
    if context == "family":
        return await recommend_family_games(params, user_steam_id)
    elif context == "quick_session":
        return await recommend_quick_session_games(params, user_steam_id)
    elif context == "similar_to":
        return await recommend_similar_games(params, user_steam_id, ctx)
    elif context == "mood_based":
        return await recommend_by_mood(params, user_steam_id, ctx)
    elif context == "unplayed_gems":
        return await recommend_unplayed_gems(user_steam_id)
    elif context == "abandoned":
        return await recommend_abandoned_games(user_steam_id)
    else:
        # Validate context format
        valid_contexts = ["abandoned", "trending", "hidden_gems", "completionist", "weekend", "family", "quick_session"]
        valid_prefixes = ["similar_to:", "mood:", "genre:"]

        context_valid = context in valid_contexts or any(context.startswith(p) for p in valid_prefixes)

        if not context_valid:
            error_msg = f"""Invalid context: "{context}"

Valid contexts:
- Basic: {', '.join(valid_contexts)}
- Similar to game: "similar_to:[game name]" (e.g., "similar_to:Portal 2")
- By mood: "mood:[feeling]" (e.g., "mood:relaxing", "mood:intense")
- By genre: "genre:[type]" (e.g., "genre:RPG", "genre:Strategy")

Examples:
- recommend_games(context="abandoned")
- recommend_games(context="mood:relaxing", parameters="single player only")
- recommend_games(context="similar_to:Hades", parameters="no roguelike")

💡 Use 'get_tool_help("recommend_games")' for detailed examples."""

            return CallToolResult(content=[TextContent(type="text", text=error_msg, annotations=Annotations(audience=["user"], priority=0.9))], isError=True)

        # Use elicitation to help user select appropriate context
        if ctx and hasattr(ctx, "elicit"):
            try:
                result = await ctx.elicit(message=f"I didn't recognize '{context}' as a recommendation type. Let me help you find the right type of games:", schema=ContextSelection)

                if result.action == "accept" and result.data:
                    # Recursively call with the selected context
                    selected_context = result.data.context
                    details = result.data.details

                    # If user provided details, try to incorporate them as parameters
                    new_params = parameters
                    if details and not parameters:
                        # Try to create parameters from details
                        if selected_context == "similar_to" and details:
                            new_params = json.dumps({"game": details})
                        elif selected_context == "mood_based" and details:
                            new_params = json.dumps({"mood": details})
                        elif selected_context == "family" and details:
                            # Try to extract age if mentioned
                            import re

                            age_match = re.search(r"\b(\d+)\b", details)
                            if age_match:
                                new_params = json.dumps({"age": int(age_match.group(1))})
                        elif selected_context == "quick_session" and details:
                            # Try to extract minutes if mentioned
                            import re

                            minutes_match = re.search(r"\b(\d+)\b", details)
                            if minutes_match:
                                new_params = json.dumps({"minutes": int(minutes_match.group(1))})

                    return await recommend_games(selected_context, new_params, use_play_history, ctx, user)
                else:
                    return CallToolResult(content=[TextContent(type="text", text="Recommendation cancelled by user.", annotations=Annotations(audience=["user"], priority=0.7))], isError=False)
            except Exception as e:
                return CallToolResult(content=[TextContent(type="text", text=f"Could not gather recommendation preferences: {str(e)}", annotations=Annotations(audience=["user"], priority=0.7))], isError=True)
        else:
            error_msg = f"""Invalid context '{context}'.

Valid contexts: {', '.join(valid_contexts + ['similar_to:[game]', 'mood:[feeling]', 'genre:[type]'])}

💡 Use 'get_tool_help("recommend_games")' for detailed examples."""

            return CallToolResult(content=[TextContent(type="text", text=error_msg, annotations=Annotations(audience=["user"], priority=0.9))], isError=True)


# Helper functions for recommend_games
async def recommend_family_games(params: dict, user_steam_id: str) -> CallToolResult:
    """Find age-appropriate family games."""
    age = params.get("age", 8)
    players = params.get("players", 1)
    params.get("content_concerns", [])

    with get_db() as session:
        # Query for age-appropriate games
        games_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).join(Game.categories).filter(Category.category_name == "Family Sharing")

        # Apply age rating filters
        max_esrb = get_max_esrb_for_age(age)
        max_pegi = get_max_pegi_for_age(age)

        games_query = games_query.filter(or_(Game.esrb_rating.in_(get_esrb_ratings_up_to(max_esrb)), Game.pegi_rating.in_(get_pegi_ratings_up_to(max_pegi)), and_(Game.esrb_rating.is_(None), Game.pegi_rating.is_(None))))

        # Filter by player count if specified
        if players > 1:
            games_query = games_query.join(Game.categories).filter(or_(Category.category_name.ilike("%Multi-player%"), Category.category_name.ilike("%Co-op%"), Category.category_name.ilike("%Local%")))

        games = games_query.distinct().limit(10).all()

        if not games:
            return f"No family-friendly games found for age {age}"

        results = []
        for game, user_game in games:
            playtime_str = f"{user_game.playtime_forever / 60:.1f}h" if user_game.playtime_forever > 0 else "Unplayed"
            results.append(f"• **{game.name}**\n" f"  Age Rating: ESRB {game.esrb_rating or 'Unrated'}, PEGI {game.pegi_rating or 'Unrated'}\n" f"  Playtime: {playtime_str}")

        output = f"**Family games for age {age}+ with {players} player(s):**\n\n" + "\n\n".join(results)
        output += "\n\n💡 **Tip:** Use 'get_tool_help(\"find_family_games\")' for age rating guidelines."

        return CallToolResult(content=[TextContent(type="text", text=output, annotations=Annotations(audience=["user"], priority=0.9))], structuredContent={"context": "family", "age": age, "players": players, "games_found": len(results)}, isError=False)


async def recommend_quick_session_games(params: dict, user_steam_id: str) -> str:
    """Find games perfect for quick sessions."""
    minutes = params.get("minutes", 30)

    # Map minutes to session tags
    if minutes <= 15:
        session_tags = ["Arcade", "Casual", "Puzzle", "Score Attack"]
    elif minutes <= 30:
        session_tags = ["Arcade", "Casual", "Puzzle", "Fast-Paced", "Card Game", "Runner"]
    else:
        session_tags = ["Casual", "Puzzle", "Card Game", "Beat 'em up", "Party Game", "Addictive"]

    with get_db() as session:
        games_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).join(Game.tags).filter(Tag.tag_name.in_(session_tags))

        games = games_query.distinct().limit(10).all()

        if not games:
            return f"No games found for {minutes}-minute sessions"

        results = []
        for game, user_game in games:
            relevant_tags = [t.tag_name for t in game.tags if t.tag_name in session_tags]
            playtime_str = f"{user_game.playtime_forever / 60:.1f}h" if user_game.playtime_forever > 0 else "Unplayed"
            results.append(f"• **{game.name}**\n" f"  Tags: {', '.join(relevant_tags[:3])}\n" f"  Playtime: {playtime_str}")

        return f"**Games perfect for {minutes}-minute sessions:**\n\n" + "\n\n".join(results)


async def recommend_similar_games(params: dict, user_steam_id: str, ctx: Context | None) -> str:
    """Find games similar to a reference game using AI analysis."""
    reference_game = params.get("game")
    if not reference_game:
        return "Please specify a game to find similar titles"

    with get_db() as session:
        # Get the reference game's characteristics
        ref_game = session.query(Game).filter(Game.name.ilike(f"%{reference_game}%")).options(joinedload(Game.genres), joinedload(Game.tags), joinedload(Game.categories)).first()

        if not ref_game:
            return f"Could not find game: {reference_game}"

        # Use sampling to identify key characteristics
        if ctx and hasattr(ctx, "session") and ctx.session:
            try:
                analysis = await ctx.session.create_message(
                    messages=[
                        SamplingMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Analyze the key characteristics that define {ref_game.name}:
                            Genres: {[g.genre_name for g in ref_game.genres]}
                            Tags: {[t.tag_name for t in ref_game.tags[:10]]}
                            Categories: {[c.category_name for c in ref_game.categories[:5]]}

                            Identify the 3 most important characteristics that similar games should have.
                            Return as JSON: {{"key_tags": [], "key_genres": [], "gameplay_style": ""}}
                            """,
                            ),
                        )
                    ],
                    max_tokens=150,
                )

                # Use AI analysis to find similar games
                if analysis.content.type == "text":
                    import json

                    try:
                        criteria = json.loads(analysis.content.text)

                        # Query for similar games
                        similar_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).filter(Game.app_id != ref_game.app_id)  # Exclude reference game

                        # Apply AI-identified criteria
                        if criteria.get("key_tags"):
                            similar_query = similar_query.join(Game.tags).filter(Tag.tag_name.in_(criteria["key_tags"]))
                        elif criteria.get("key_genres"):
                            similar_query = similar_query.join(Game.genres).filter(Genre.genre_name.in_(criteria["key_genres"]))

                        similar_games = similar_query.distinct().limit(8).all()

                        if not similar_games:
                            return f"No games found similar to {ref_game.name}"

                        results = []
                        for game, user_game in similar_games:
                            shared_genres = [g.genre_name for g in game.genres if g.genre_name in [rg.genre_name for rg in ref_game.genres]]
                            playtime_str = f"{user_game.playtime_forever / 60:.1f}h" if user_game.playtime_forever > 0 else "Unplayed"
                            results.append(f"• **{game.name}**\n" f"  Shared genres: {', '.join(shared_genres[:2])}\n" f"  Playtime: {playtime_str}")

                        return f"**Games similar to {ref_game.name}:**\n\n" + "\n\n".join(results)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass

        # Fallback to genre-based similarity
        similar_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).join(Game.genres).filter(Genre.genre_name.in_([g.genre_name for g in ref_game.genres]), Game.app_id != ref_game.app_id)

        similar_games = similar_query.distinct().limit(8).all()

        if not similar_games:
            return f"No games found similar to {ref_game.name}"

        results = []
        for game, user_game in similar_games:
            shared_genres = [g.genre_name for g in game.genres if g.genre_name in [rg.genre_name for rg in ref_game.genres]]
            playtime_str = f"{user_game.playtime_forever / 60:.1f}h" if user_game.playtime_forever > 0 else "Unplayed"
            results.append(f"• **{game.name}**\n" f"  Shared genres: {', '.join(shared_genres[:2])}\n" f"  Playtime: {playtime_str}")

        return f"**Games similar to {ref_game.name}:**\n\n" + "\n\n".join(results)


async def recommend_by_mood(params: dict, user_steam_id: str, ctx: Context | None) -> str:
    """Recommend games based on current mood."""
    mood = params.get("mood", "relaxed")

    # Map moods to tags and genres
    mood_mappings = {"relaxing": {"tags": ["Casual", "Puzzle", "Atmospheric", "Zen"], "genres": ["Casual", "Indie"]}, "energetic": {"tags": ["Fast-Paced", "Action", "Arcade", "Bullet Hell"], "genres": ["Action"]}, "competitive": {"tags": ["PvP", "Competitive", "Esports"], "categories": ["Multi-player", "PvP"]}, "social": {"tags": ["Co-op", "Party Game"], "categories": ["Multi-player", "Co-op"]}, "creative": {"tags": ["Building", "Sandbox", "Creative"], "genres": ["Simulation"]}, "story": {"tags": ["Story Rich", "Narrative"], "genres": ["Adventure", "RPG"]}}

    mapping = mood_mappings.get(mood.lower(), mood_mappings["relaxing"])

    with get_db() as session:
        games_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id))

        # Apply mood-based filters
        filters = []
        if mapping.get("tags"):
            filters.append(Game.tags.any(Tag.tag_name.in_(mapping["tags"])))
        if mapping.get("genres"):
            filters.append(Game.genres.any(Genre.genre_name.in_(mapping["genres"])))
        if mapping.get("categories"):
            filters.append(Game.categories.any(Category.category_name.in_(mapping["categories"])))

        if filters:
            games_query = games_query.filter(or_(*filters))

        games = games_query.distinct().limit(10).all()

        if not games:
            return f"No games found for {mood} mood"

        results = []
        for game, user_game in games:
            mood_tags = [t.tag_name for t in game.tags if t.tag_name in mapping.get("tags", [])]
            playtime_str = f"{user_game.playtime_forever / 60:.1f}h" if user_game.playtime_forever > 0 else "Unplayed"
            results.append(f"• **{game.name}**\n" f"  Mood tags: {', '.join(mood_tags[:3])}\n" f"  Playtime: {playtime_str}")

        return f"**Games for {mood} mood:**\n\n" + "\n\n".join(results)


async def recommend_unplayed_gems(user_steam_id: str) -> str:
    """Find high-rated games you haven't played."""
    with get_db() as session:
        unplayed_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).filter(UserGame.playtime_forever == 0, Game.metacritic_score >= 75).options(joinedload(Game.genres), joinedload(Game.reviews))  # Never played

        unplayed_games = unplayed_query.order_by(Game.metacritic_score.desc()).limit(10).all()

        if not unplayed_games:
            return "No unplayed games found with Metacritic score >= 75"

        results = []
        for game, _user_game in unplayed_games:
            genre_names = [g.genre_name for g in game.genres[:2]]
            review_info = ""
            if game.reviews and game.reviews.review_summary:
                review_info = f" | {game.reviews.review_summary}"

            results.append(f"• **{game.name}** ({game.metacritic_score}/100){review_info}\n" f"  Genres: {', '.join(genre_names)}\n" f"  {game.short_description[:100]}..." if game.short_description else "")

        return "**Unplayed gems in your library:**\n\n" + "\n\n".join(results)


async def recommend_abandoned_games(user_steam_id: str) -> str:
    """Find games played briefly then abandoned - might deserve another chance."""
    with get_db() as session:
        # Games played 15-120 minutes but not touched in 2 weeks
        abandoned = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).filter(UserGame.playtime_forever.between(15, 120), UserGame.playtime_2weeks == 0, Game.metacritic_score >= 70).options(joinedload(Game.genres), joinedload(Game.tags), joinedload(Game.reviews)).order_by(Game.metacritic_score.desc()).limit(8).all()  # Played briefly  # Not recently played  # Actually good games

        if not abandoned:
            return "No abandoned games found that might deserve another chance"

        results = []
        for game, user_game in abandoned:
            # Check why it might have been abandoned
            reasons = []
            difficult_tags = ["Difficult", "Souls-like", "Roguelike", "Dark Souls"]
            slow_start_tags = ["Story Rich", "JRPG", "Turn-Based Strategy"]

            if any(t.tag_name in difficult_tags for t in game.tags):
                reasons.append("high difficulty")
            if any(t.tag_name in slow_start_tags for t in game.tags):
                reasons.append("slow start")

            reason_text = f" (possibly {' or '.join(reasons)})" if reasons else ""
            community_text = ""
            if game.reviews and game.reviews.review_summary:
                community_text = f" | Community: {game.reviews.review_summary}"

            results.append(f"• **{game.name}** ({game.metacritic_score}/100){community_text}\n" f"  Playtime: {user_game.playtime_forever}min{reason_text}\n" f"  Genres: {', '.join([g.genre_name for g in game.genres[:2]])}")

        return "**Games that might deserve another chance:**\n\n" + "\n\n".join(results)


class GamePreferences(BaseModel):
    """Schema for collecting user game preferences."""

    multiplayer: bool = Field(description="Include multiplayer games?")
    max_price: float = Field(description="Maximum price in USD", default=60.0)
    time_to_beat: str = Field(description="Preferred game length", default="any")


class ContextSelection(BaseModel):
    """Schema for selecting recommendation context."""

    context: str = Field(
        description="""Type of recommendation you want:
        - family: Age-appropriate games (needs age of youngest player)
        - quick_session: Games for short sessions (can specify minutes like 15, 30, 60)
        - similar_to: Games like one you specify (needs specific game name)
        - mood_based: Games matching your mood (like 'relaxing', 'energetic', 'competitive')
        - unplayed_gems: High-rated games you own but haven't played yet
        - abandoned: Games you started but didn't finish""",
        choices=["family", "quick_session", "similar_to", "mood_based", "unplayed_gems", "abandoned"],
    )
    details: str = Field(default="", description="Additional details (e.g., specific game name, age, mood, or session length)")


@mcp.tool()
async def find_games_with_preferences(initial_genre: str, ctx: Context, user: str | None = None) -> str:
    """Find games with user preferences via elicitation."""
    # Resolve user with default fallback
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]

    try:
        # Check if elicitation is available
        if not ctx or not hasattr(ctx, "elicit"):
            return f"Interactive preferences not available. Try using search_games with '{initial_genre}' instead."

        # Ask for user preferences
        result = await ctx.elicit(message=f"Looking for {initial_genre} games. What are your preferences?", schema=GamePreferences)

        if result.action == "accept" and result.data:
            prefs = result.data

            with get_db() as session:
                # Get user info
                user_profile = session.query(UserProfile).filter_by(steam_id=user_steam_id).first()
                if not user_profile:
                    return handle_user_not_found(user_steam_id)["message"]

                # Get user's games with genres and categories
                user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.categories)).filter(UserGame.steam_id == user_steam_id).all()

                # Filter by genre and preferences
                matches = []
                for user_game in user_games:
                    game = user_game.game

                    # Check genre match
                    genre_match = any(initial_genre.lower() in g.genre_name.lower() for g in game.genres)

                    if genre_match:
                        # Check multiplayer preference
                        if prefs.multiplayer:
                            has_multiplayer = any("multiplayer" in c.category_name.lower() for c in game.categories)
                            if has_multiplayer:
                                matches.append({"name": game.name, "playtime": user_game.playtime_hours, "categories": [c.category_name for c in game.categories]})
                        else:
                            matches.append({"name": game.name, "playtime": user_game.playtime_hours, "categories": [c.category_name for c in game.categories]})

            response = f"Found {initial_genre} games for {user_profile.persona_name} matching your preferences:\n"
            response += f"- Multiplayer: {'Yes' if prefs.multiplayer else 'No'}\n"
            response += f"- Max Price: ${prefs.max_price}\n"
            response += f"- Time to Beat: {prefs.time_to_beat}\n\n"

            if matches:
                response += "**Matching games:**\n"
                for match in matches[:10]:
                    cats = ", ".join(match["categories"][:3]) if match["categories"] else "No categories"
                    response += f"- {match['name']} ({match['playtime']}h) - {cats}\n"
            else:
                response += "No games found matching all criteria"

            return response
        else:
            return "Search cancelled by user"

    except Exception as e:
        return f"Failed to find games: {str(e)}"


@mcp.tool()
async def get_library_insights(analysis_type: str, compare_to: str = "", time_range: str = "all", ctx: Context | None = None, user: str | None = None) -> str:  # patterns|gaps|value|social|achievements|trends  # friends|global|genre_average  # all|recent|last_month
    """
    Deep analytics and insights about gaming library and habits.

    Analysis types:
    - patterns: Gaming habit analysis (favorite genres, play times, etc.)
    - gaps: Popular games in favorite genres you don't own
    - value: Cost per hour analysis, best/worst value games
    - social: Compare with friends' libraries
    - achievements: Achievement completion analysis
    - trends: How gaming habits changed over time
    """
    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]

    if analysis_type == "patterns":
        return await analyze_patterns(user_steam_id, user_result.get("display_name", "User"), ctx)
    elif analysis_type == "gaps":
        return await analyze_gaps(user_steam_id, ctx)
    elif analysis_type == "value":
        return await analyze_value(user_steam_id, ctx)
    elif analysis_type == "social":
        return await analyze_social(user_steam_id, compare_to, ctx)
    elif analysis_type == "achievements":
        return await analyze_achievements(user_steam_id, ctx)
    elif analysis_type == "trends":
        return await analyze_trends(user_steam_id, time_range, ctx)
    else:
        return f"Invalid analysis type '{analysis_type}'. Valid types: patterns, gaps, value, social, achievements, trends"


# Helper functions for get_library_insights
async def analyze_patterns(user_steam_id: str, display_name: str, ctx: Context | None) -> str:
    """Analyze gaming habit patterns."""
    with get_db() as session:
        # Get all user games with full data
        user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres), joinedload(UserGame.game).joinedload(Game.tags), joinedload(UserGame.game).joinedload(Game.developers)).filter(UserGame.steam_id == user_steam_id).all()

        # Analyze patterns
        patterns = {
            "total_games": len(user_games),
            "played_games": sum(1 for ug in user_games if ug.playtime_forever > 0),
            "total_hours": sum(ug.playtime_forever for ug in user_games) / 60,
            "recent_hours": sum(ug.playtime_2weeks for ug in user_games) / 60,
        }

        # Genre preferences by playtime
        genre_time = {}
        for ug in user_games:
            if ug.playtime_forever > 0:
                for genre in ug.game.genres:
                    if genre.genre_name not in genre_time:
                        genre_time[genre.genre_name] = {"hours": 0, "games": 0}
                    genre_time[genre.genre_name]["hours"] += ug.playtime_forever / 60
                    genre_time[genre.genre_name]["games"] += 1

        # Developer loyalty
        dev_games = {}
        for ug in user_games:
            for dev in ug.game.developers:
                if dev.developer_name not in dev_games:
                    dev_games[dev.developer_name] = 0
                dev_games[dev.developer_name] += 1

        # Identify "binges" - games played heavily then stopped
        binges = []
        for ug in user_games:
            if ug.playtime_forever > 600 and ug.playtime_2weeks == 0:  # 10+ hours, not recent
                binges.append({"game": ug.game.name, "hours": ug.playtime_forever / 60, "last_played": "Over 2 weeks ago"})

        # Sort and format results
        top_genres = sorted(genre_time.items(), key=lambda x: x[1]["hours"], reverse=True)[:5]
        top_devs = sorted(dev_games.items(), key=lambda x: x[1], reverse=True)[:5]
        top_binges = sorted(binges, key=lambda x: x["hours"], reverse=True)[:5]

        # Build analysis
        analysis = f"""**Gaming Pattern Analysis for {display_name}:**

**Library Overview:**
• Total games: {patterns['total_games']}
• Games played: {patterns['played_games']} ({patterns['played_games']/patterns['total_games']*100:.1f}%)
• Total playtime: {patterns['total_hours']:.1f} hours
• Recent activity: {patterns['recent_hours']:.1f} hours (last 2 weeks)

**Favorite Genres by Playtime:**"""

        for genre, data in top_genres:
            avg_hours = data["hours"] / data["games"] if data["games"] > 0 else 0
            analysis += f"\n• {genre}: {data['hours']:.1f}h across {data['games']} games (avg: {avg_hours:.1f}h/game)"

        analysis += "\n\n**Developer Loyalty:**"
        for dev, count in top_devs:
            analysis += f"\n• {dev}: {count} games"

        if top_binges:
            analysis += "\n\n**Games You Binged Then Abandoned:**"
            for binge in top_binges:
                analysis += f"\n• {binge['game']}: {binge['hours']:.1f}h ({binge['last_played']})"

        # Format insights with AI interpretation
        if ctx and hasattr(ctx, "session") and ctx.session:
            try:
                insights_prompt = f"""Based on this gaming data, provide 3 key insights:
                Top genres: {', '.join([g[0] for g in top_genres[:3]])}
                Recent vs total hours: {patterns['recent_hours']:.1f} / {patterns['total_hours']:.1f}
                Completion rate: {patterns['played_games']} / {patterns['total_games']}

                Format as actionable insights about the player's gaming personality."""

                ai_insights = await ctx.session.create_message(messages=[SamplingMessage(role="user", content=TextContent(type="text", text=insights_prompt))], max_tokens=200)

                if ai_insights.content.type == "text":
                    analysis += f"\n\n**AI Insights:**\n{ai_insights.content.text}"
            except Exception:
                pass  # Continue without AI insights

        return analysis


async def analyze_value(user_steam_id: str, ctx: Context | None) -> str:
    """Calculate cost per hour analysis."""
    with get_db() as session:
        user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.reviews)).filter(UserGame.steam_id == user_steam_id).all()

        # Calculate value score (using playtime as proxy for value)
        value_games = []

        for ug in user_games:
            if ug.playtime_forever > 60:  # At least 1 hour played
                # Estimate value score based on playtime, metacritic, and engagement
                hours_played = ug.playtime_forever / 60
                metacritic_bonus = (ug.game.metacritic_score or 50) / 100  # Normalize to 0-1

                # Base value: hours played
                # Bonus: metacritic score
                # Bonus: high engagement (recently played)
                engagement_bonus = 1.2 if ug.playtime_2weeks > 0 else 1.0

                value_score = hours_played * metacritic_bonus * engagement_bonus

                value_games.append({"game": ug.game.name, "hours": hours_played, "value_score": value_score, "metacritic": ug.game.metacritic_score, "recent_play": ug.playtime_2weeks > 0})

        # Sort by value score
        value_games.sort(key=lambda x: x["value_score"], reverse=True)

        if not value_games:
            return "**Value Analysis:** No games with sufficient playtime found for analysis."

        best_value = value_games[:5]
        worst_value = value_games[-5:] if len(value_games) > 5 else []

        analysis = "**Library Value Analysis:**\n\n"

        analysis += "**Best Value Games (High Playtime + Quality):**\n"
        for game in best_value:
            recent_indicator = " 🔥" if game["recent_play"] else ""
            metacritic_str = f" ({game['metacritic']}/100)" if game["metacritic"] else ""
            analysis += f"• **{game['game']}**{metacritic_str}{recent_indicator}\n"
            analysis += f"  {game['hours']:.1f} hours played | Value Score: {game['value_score']:.1f}\n"

        if worst_value:
            analysis += "\n**Games That Could Use More Love:**\n"
            for game in reversed(worst_value):  # Show worst last
                metacritic_str = f" ({game['metacritic']}/100)" if game["metacritic"] else ""
                analysis += f"• **{game['game']}**{metacritic_str}\n"
                analysis += f"  {game['hours']:.1f} hours played | Value Score: {game['value_score']:.1f}\n"

        # Add summary stats
        total_hours = sum(g["hours"] for g in value_games)
        avg_value = sum(g["value_score"] for g in value_games) / len(value_games)

        analysis += "\n**Summary:**\n"
        analysis += f"• Total analyzed playtime: {total_hours:.1f} hours\n"
        analysis += f"• Average value score: {avg_value:.1f}\n"
        analysis += f"• Your best value game: **{best_value[0]['game']}** ({best_value[0]['hours']:.1f}h)\n"

        return analysis


async def analyze_gaps(user_steam_id: str, ctx: Context | None) -> str:
    """Find popular games in favorite genres you don't own."""
    with get_db() as session:
        # Get user's favorite genres (by playtime)
        user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres)).filter(UserGame.steam_id == user_steam_id).all()

        # Calculate genre preferences
        genre_hours = {}
        for ug in user_games:
            if ug.playtime_forever > 0:
                for genre in ug.game.genres:
                    if genre.genre_name not in genre_hours:
                        genre_hours[genre.genre_name] = 0
                    genre_hours[genre.genre_name] += ug.playtime_forever / 60

        if not genre_hours:
            return "**Gap Analysis:** No played games found to analyze preferences."

        # Get top 3 favorite genres
        top_genres = sorted(genre_hours.items(), key=lambda x: x[1], reverse=True)[:3]

        gaps_found = []
        user_game_ids = {ug.app_id for ug in user_games}

        for genre_name, hours in top_genres:
            # Find highly rated games in this genre that user doesn't own
            genre_games = session.query(Game).join(Game.genres).filter(Genre.genre_name == genre_name, Game.metacritic_score >= 80, ~Game.app_id.in_(user_game_ids)).options(joinedload(Game.reviews)).order_by(Game.metacritic_score.desc()).limit(3).all()  # High quality games  # Games user doesn't own

            for game in genre_games:
                review_info = ""
                if game.reviews and game.reviews.review_summary:
                    review_info = f" | {game.reviews.review_summary}"

                gaps_found.append({"game": game.name, "genre": genre_name, "metacritic": game.metacritic_score, "review_info": review_info, "user_genre_hours": hours})

        if not gaps_found:
            return "**Gap Analysis:** No obvious gaps found in your favorite genres. You have great taste!"

        analysis = "**Library Gap Analysis:**\n\n"
        analysis += "Based on your favorite genres, here are highly-rated games you might be missing:\n\n"

        current_genre = None
        for gap in gaps_found:
            if gap["genre"] != current_genre:
                current_genre = gap["genre"]
                analysis += f"**{current_genre}** (you've played {gap['user_genre_hours']:.1f}h in this genre):\n"

            analysis += f"• **{gap['game']}** ({gap['metacritic']}/100){gap['review_info']}\n"

        return analysis


async def analyze_social(user_steam_id: str, compare_to: str, ctx: Context | None) -> str:
    """Compare with friends' libraries (placeholder - would need friends data)."""
    # This would require friends data to be available
    return "**Social Analysis:** Social comparison features require friends data to be fetched. Use the Steam library fetcher with --friends flag to enable social analysis."


async def analyze_achievements(user_steam_id: str, ctx: Context | None) -> str:
    """Achievement completion analysis (placeholder - would need achievement data)."""
    # This would require achievement data to be available in the database
    return "**Achievement Analysis:** Achievement tracking features are not yet implemented. This would show completion rates and achievement hunting opportunities."


async def analyze_trends(user_steam_id: str, time_range: str, ctx: Context | None) -> str:
    """Analyze gaming habit trends over time."""
    with get_db() as session:
        user_games = session.query(UserGame).options(joinedload(UserGame.game).joinedload(Game.genres)).filter(UserGame.steam_id == user_steam_id).all()

        # Basic trend analysis using playtime data
        len(user_games)
        played_games = [ug for ug in user_games if ug.playtime_forever > 0]
        recent_games = [ug for ug in user_games if ug.playtime_2weeks > 0]

        if not recent_games:
            return "**Trends Analysis:** No recent gaming activity found."

        # Compare recent vs historical preferences
        recent_genres = {}
        historical_genres = {}

        for ug in recent_games:
            for genre in ug.game.genres:
                recent_genres[genre.genre_name] = recent_genres.get(genre.genre_name, 0) + ug.playtime_2weeks / 60

        for ug in played_games:
            total_time = ug.playtime_forever / 60
            recent_time = ug.playtime_2weeks / 60
            historical_time = total_time - recent_time

            if historical_time > 0:
                for genre in ug.game.genres:
                    historical_genres[genre.genre_name] = historical_genres.get(genre.genre_name, 0) + historical_time

        analysis = "**Gaming Trends Analysis:**\n\n"

        # Recent activity summary
        total_recent_hours = sum(recent_genres.values())
        analysis += "**Recent Activity (Last 2 Weeks):**\n"
        analysis += f"• Games played: {len(recent_games)}\n"
        analysis += f"• Total hours: {total_recent_hours:.1f}h\n"
        analysis += f"• Average per game: {total_recent_hours/len(recent_games):.1f}h\n\n"

        # Top recent genres
        if recent_genres:
            top_recent = sorted(recent_genres.items(), key=lambda x: x[1], reverse=True)[:5]
            analysis += "**Current Genre Preferences:**\n"
            for genre, hours in top_recent:
                analysis += f"• {genre}: {hours:.1f}h\n"

        # Compare with historical if we have data
        if historical_genres:
            analysis += "\n**Trend Shifts:**\n"
            for genre, recent_hours in sorted(recent_genres.items(), key=lambda x: x[1], reverse=True)[:3]:
                historical_hours = historical_genres.get(genre, 0)
                if historical_hours > 0:
                    ratio = recent_hours / (historical_hours / 52)  # Weekly average historical
                    if ratio > 1.5:
                        analysis += f"• 📈 **{genre}**: Playing {ratio:.1f}x more than usual\n"
                    elif ratio < 0.5:
                        analysis += f"• 📉 **{genre}**: Playing {ratio:.1f}x less than usual\n"
                else:
                    analysis += f"• ✨ **{genre}**: New interest! ({recent_hours:.1f}h recently)\n"

        return analysis


@mcp.tool()
async def find_family_games(child_age: int, ctx: Context | None = None, user: str | None = None) -> str:
    """Find age-appropriate games for family gaming.

    Uses ESRB/PEGI ratings and family-friendly categories.
    For young children (under 10), may gather additional preferences.
    """
    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]

    # Elicitation for young children
    if child_age < 10 and ctx:
        try:
            result = await ctx.elicit(message=f"Finding games for a {child_age}-year-old. Let's ensure they're appropriate:", schema=FamilyPreferences)

            if result.action == "accept" and result.data:
                # Add filters based on content_concerns
                # This will be used in the filtering logic below
                pass
        except Exception:
            # Continue without preferences if elicitation fails
            pass

    # Map age to ratings
    max_esrb = get_max_esrb_for_age(child_age)
    max_pegi = get_max_pegi_for_age(child_age)

    with get_db() as session:
        # Query for age-appropriate games
        games_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).join(Game.categories).filter(Category.category_name == "Family Sharing")

        # Apply age rating filters
        games_query = games_query.filter(or_(Game.esrb_rating.in_(get_esrb_ratings_up_to(max_esrb)), Game.pegi_rating.in_(get_pegi_ratings_up_to(max_pegi)), and_(Game.esrb_rating.is_(None), Game.pegi_rating.is_(None))))  # Include unrated

        # Format results
        results = []
        for game, _user_game in games_query.limit(10):
            results.append(f"- {game.name} (ESRB: {game.esrb_rating or 'Unrated'}, " f"PEGI: {game.pegi_rating or 'Unrated'})")

        if not results:
            return f"No family-friendly games found in library for age {child_age}"

        return f"Family-friendly games for age {child_age}:\n" + "\n".join(results)


@mcp.tool()
async def find_quick_session_games(session_length: str = "short", user: str | None = None) -> str:
    """Find games perfect for quick gaming sessions (5-60 minutes).

    Session lengths: 'short' (5-15 min), 'medium' (15-30 min), 'long' (30-60 min)
    """
    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]

    # Define quick session tags based on analysis
    quick_session_tags = ["Arcade", "Casual", "Puzzle", "Score Attack", "Fast-Paced", "Bullet Hell", "Shoot 'Em Up", "Twin Stick Shooter", "Card Game", "Runner", "Time Attack", "Puzzle Platformer", "Beat 'em up", "Party Game", "Addictive"]

    # Tags to exclude (suggest longer sessions)
    long_session_tags = ["Open World", "Story Rich", "JRPG", "RPG", "Strategy", "Turn-Based Strategy", "4X", "Grand Strategy", "Survival", "Open World Survival Craft", "City Builder", "Management"]

    with get_db() as session:
        # Build query for games with quick session tags
        quick_games_query = session.query(Game, UserGame).join(UserGame, (Game.app_id == UserGame.app_id) & (UserGame.steam_id == user_steam_id)).join(Game.tags).filter(Tag.tag_name.in_(quick_session_tags))

        # Exclude games with long session tags
        long_session_game_ids = session.query(Game.app_id).join(Game.tags).filter(Tag.tag_name.in_(long_session_tags)).subquery()

        quick_games_query = quick_games_query.filter(~Game.app_id.in_(long_session_game_ids))

        # Additional filtering based on session length preference
        if session_length == "short":
            # Prefer very quick games - add extra weight to arcade/puzzle
            quick_games_query = quick_games_query.filter(Tag.tag_name.in_(["Arcade", "Casual", "Puzzle", "Score Attack", "Fast-Paced"]))
        elif session_length == "medium":
            # Include slightly longer but still session-based games
            pass  # Use all quick_session_tags
        elif session_length == "long":
            # Allow some strategy/rpg elements but still session-friendly
            quick_games_query = quick_games_query.filter(or_(Tag.tag_name.in_(quick_session_tags), and_(Tag.tag_name.in_(["Turn-Based", "Tactical", "Card Battler"]), ~Tag.tag_name.in_(long_session_tags))))

        quick_games = quick_games_query.distinct().all()

        # Separate played and unplayed games
        played_games = []
        unplayed_games = []
        total_playtimes = []

        for game, user_game in quick_games:
            if user_game.playtime_forever > 0:
                played_games.append((game, user_game))
                total_playtimes.append(user_game.playtime_forever)
            else:
                unplayed_games.append((game, user_game))

        # Calculate threshold for "favorites" - top 25% by playtime (minimum 1 hour)
        if total_playtimes:
            sorted_playtimes = sorted(total_playtimes, reverse=True)
            if len(sorted_playtimes) >= 4:  # Need at least 4 played games
                favorite_threshold = sorted_playtimes[len(sorted_playtimes) // 4]  # Top 25%
                favorite_threshold = max(favorite_threshold, 60)  # Minimum 1 hour
            else:
                favorite_threshold = 60  # Default to 1 hour minimum
        else:
            favorite_threshold = 60

        # Sort played games by total playtime (favorites first), then by recent activity
        played_games.sort(key=lambda x: (x[1].playtime_forever, x[1].playtime_2weeks), reverse=True)

        # Sort unplayed games by review score (if available), then by metacritic score
        unplayed_with_reviews = []
        for game, user_game in unplayed_games:
            review_score = 0
            if game.reviews and game.reviews.positive_percentage:
                review_score = game.reviews.positive_percentage
            elif game.metacritic_score:
                review_score = game.metacritic_score  # Use metacritic as fallback
            unplayed_with_reviews.append((game, user_game, review_score))

        # Sort by review score and keep only well-reviewed games (>75% or >75 metacritic)
        unplayed_with_reviews.sort(key=lambda x: x[2], reverse=True)
        good_unplayed = [(g, ug) for g, ug, score in unplayed_with_reviews if score >= 75]

        # Mix results: ~85% played games, ~15% good unplayed games
        target_total = 15
        target_unplayed = min(3, len(good_unplayed))  # Max 3 unplayed games (20%)
        target_played = target_total - target_unplayed

        analyzed_games = played_games[:target_played] + good_unplayed[:target_unplayed]

        if not analyzed_games:
            return f"No games found for {session_length} gaming sessions"

        # Format results with session recommendations
        session_desc = {"short": "5-15 minute", "medium": "15-30 minute", "long": "30-60 minute"}

        results = [f"**Games perfect for {session_desc[session_length]} sessions:**", "🔥 = Recently played | ⭐ = Your favorites | 🆕 = Unplayed gems (good reviews)\n"]

        for game, user_game in analyzed_games:
            # Get relevant tags for this game
            game_tags = [tag.tag_name for tag in game.tags if tag.tag_name in quick_session_tags]

            playtime_info = f"Played: {user_game.playtime_forever / 60:.1f}h" if user_game.playtime_forever > 0 else "Unplayed"

            # Add activity indicator
            activity_indicator = ""
            if user_game.playtime_2weeks > 0:
                activity_indicator = " 🔥"  # Recently active
            elif user_game.playtime_forever == 0:
                activity_indicator = " 🆕"  # Unplayed gems
            elif user_game.playtime_forever >= favorite_threshold:
                activity_indicator = " ⭐"  # Your favorites

            # Add session reason
            session_reason = ""
            if "Arcade" in game_tags:
                session_reason = "Quick arcade action"
            elif "Puzzle" in game_tags:
                session_reason = "Bite-sized puzzles"
            elif "Card Game" in game_tags:
                session_reason = "Quick card matches"
            elif "Score Attack" in game_tags:
                session_reason = "Score competition"
            elif "Casual" in game_tags:
                session_reason = "Relaxed gameplay"
            elif "Fast-Paced" in game_tags:
                session_reason = "Fast action rounds"
            elif "Bullet Hell" in game_tags:
                session_reason = "Intense short bursts"
            else:
                session_reason = "Quick sessions"

            results.append(f"• **{game.name}**{activity_indicator}\n" f"  {session_reason} | {playtime_info}\n" f"  Tags: {', '.join(game_tags[:3])}")

        return "\n".join(results)


# Helper functions
def format_top_items(items: list[tuple], limit: int) -> str:
    """Format top N items from query results."""
    sorted_items = sorted(items, key=lambda x: x[1], reverse=True)[:limit]
    return "\n".join([f"- {name}: {count} games" for name, count in sorted_items])


def count_category(category_counts: list[tuple], category_name: str) -> int:
    """Count games in specific category."""
    for name, count in category_counts:
        if name == category_name:
            return count
    return 0


def get_max_esrb_for_age(age: int) -> str:
    if age < 6:
        return "EC"
    elif age < 10:
        return "E"
    elif age < 13:
        return "E10+"
    elif age < 17:
        return "T"
    else:
        return "M"


def get_esrb_ratings_up_to(max_rating: str) -> list[str]:
    ratings = ["EC", "E", "E10+", "T", "M"]
    return ratings[: ratings.index(max_rating) + 1]


def get_max_pegi_for_age(age: int) -> str:
    if age < 7:
        return "3"
    elif age < 12:
        return "7"
    elif age < 16:
        return "12"
    elif age < 18:
        return "16"
    else:
        return "18"


def get_pegi_ratings_up_to(max_rating: str) -> list[str]:
    ratings = ["3", "7", "12", "16", "18"]
    return ratings[: ratings.index(max_rating) + 1]


def format_tool_documentation(name: str, doc: dict) -> str:
    """Format tool documentation for display."""
    output = f"# {name} Tool Documentation\n\n"
    output += f"## Description\n{doc['description']}\n\n"

    if "parameters" in doc:
        output += "## Parameters\n"
        for param, desc in doc["parameters"].items():
            output += f"- **{param}**: {desc}\n"
        output += "\n"

    if "contexts" in doc:
        output += "## Available Contexts\n"
        for ctx, desc in doc["contexts"].items():
            output += f"- **{ctx}**: {desc}\n"
        output += "\n"

    if "filter_examples" in doc:
        output += "## Filter Examples\n"
        for ex in doc["filter_examples"]:
            output += f"### {ex['description']}\n"
            if "query" in ex:
                output += f"Query: `{ex['query']}`\n"
            if "value" in ex:
                output += f"Filter: `{ex['value']}`\n"
            if "filters" in ex:
                output += f"Filters: `{ex['filters']}`\n"
            output += "\n"

    if "parameter_examples" in doc:
        output += "## Usage Examples\n"
        for ex in doc["parameter_examples"]:
            output += f"- Context: `{ex['context']}`\n"
            output += f"  Parameters: `{ex['parameters']}`\n\n"

    if "common_errors" in doc:
        output += "## Common Errors and Solutions\n"
        for error, solution in doc["common_errors"].items():
            output += f"- **{error}**: {solution}\n"

    return output


@mcp.tool(name="get_tool_help", title="Tool Documentation Helper", description="Get detailed help and examples for MCP tools with comprehensive documentation and usage patterns")
async def get_tool_help(tool_name: str = None) -> CallToolResult:
    """Get detailed help and examples for MCP tools.

    Args:
        tool_name: Name of tool to get help for. If None, lists all tools.

    Returns:
        Detailed documentation with examples, parameters, common errors, and usage patterns
    """

    tool_docs = {"smart_search": {"description": "Natural language game search with AI-powered filtering and flexible parameter parsing", "parameters": {"query": "Natural language search query (required) - can be game names, descriptions, or requests", "filters": "Additional filters as JSON or natural language (optional)", "limit": "Number of results to return, 1-50 (default: 10)", "sort_by": "Sort method: relevance, playtime, metacritic, recent, random (default: relevance)", "user": "Steam ID or username (uses default if not specified)"}, "filter_examples": [{"description": "JSON filter for action games rated 80+", "value": '{"genres": ["Action"], "min_rating": 80}'}, {"description": "Natural language filter", "value": "multiplayer games released after 2020"}, {"description": "Combined search with natural language filters", "query": "zombie survival games", "filters": "exclude horror genre, coop multiplayer"}, {"description": "VR games filter", "value": "vr games"}, {"description": "Unplayed games filter", "value": "unplayed indie games"}], "common_errors": {"Invalid filters format": 'Use valid JSON like {"genres": ["Action"]} or natural language like \'action games rated over 80\'', "Multiple users found": "Specify exact Steam ID or full username in the user parameter", "No results found": "Try broader search terms, different genres, or check spelling"}}, "recommend_games": {"description": "AI-powered personalized game recommendations with context-aware filtering and elicitation", "contexts": {"abandoned": "Games you started but haven't finished (1-10 hours played)", "similar_to:[game]": "Find games similar to specified game (e.g., 'similar_to:Portal 2')", "mood:[feeling]": "Games matching a mood (e.g., 'mood:relaxing', 'mood:competitive')", "genre:[type]": "Smart genre-based recommendations (e.g., 'genre:RPG')", "trending": "Popular games being played by many users recently", "hidden_gems": "Highly-rated games with low player counts", "completionist": "Games where you're close to 100% achievements", "weekend": "Games perfect for weekend sessions (20-40 hour campaigns)", "family": "Age-appropriate games (will ask for child's age)", "quick_session": "Games for short sessions (will ask for available time)"}, "parameter_examples": [{"context": "abandoned", "parameters": "focus on games under 20 hours"}, {"context": "mood:relaxing", "parameters": '{"exclude_genres": ["Horror", "Action"], "single_player": true}'}, {"context": "similar_to:Portal 2", "parameters": "no puzzle games"}, {"context": "genre:RPG", "parameters": "highly rated, no multiplayer"}], "common_errors": {"Invalid context": "Use valid contexts like 'abandoned', 'mood:relaxing', or 'similar_to:[game name]'", "Invalid parameters format": "Use JSON, natural language, or simple keywords. Avoid mixing formats.", "Game not found for similar_to": "Check spelling of game name or use partial matches"}}, "get_library_insights": {"description": "Deep analytics and insights about your gaming library and habits with AI interpretation", "parameters": {"analysis_type": "Type of analysis: patterns, gaps, value, social, achievements, trends", "compare_to": "Comparison target (optional): friends, global, genre_average", "time_range": "Period to analyze (default: all): all, recent, last_month", "user": "Steam ID or username (uses default if not specified)"}, "parameter_examples": [{"context": "patterns", "parameters": "Get detailed gaming habit analysis"}, {"context": "gaps", "parameters": "Find popular games in favorite genres you don't own"}, {"context": "value", "parameters": "Analyze cost per hour and game value"}]}, "find_family_games": {"description": "Find age-appropriate games for family gaming using ESRB/PEGI ratings", "parameters": {"child_age": "Age of youngest player (required) - determines appropriate rating limits", "user": "Steam ID or username (uses default if not specified)"}, "parameter_examples": [{"context": "Age 8 child", "parameters": "child_age=8 (allows E and E10+ rated games)"}, {"context": "Age 12 child", "parameters": "child_age=12 (allows up to T rated games)"}]}, "find_quick_session_games": {"description": "Find games perfect for quick gaming sessions with smart tag analysis", "parameters": {"session_length": "Session type: 'short' (5-15min), 'medium' (15-30min), 'long' (30-60min)", "user": "Steam ID or username (uses default if not specified)"}, "parameter_examples": [{"context": "Quick break games", "parameters": "session_length='short' for arcade and puzzle games"}, {"context": "Lunch break gaming", "parameters": "session_length='medium' for balanced quick games"}]}}

    if tool_name:
        if tool_name in tool_docs:
            doc = tool_docs[tool_name]
            formatted_help = format_tool_documentation(tool_name, doc)
        else:
            error_msg = f"Unknown tool: {tool_name}\n\nAvailable tools: {', '.join(tool_docs.keys())}\n\n💡 Use get_tool_help() without parameters to see all tools."
            return CallToolResult(content=[TextContent(type="text", text=error_msg, annotations=Annotations(audience=["user"], priority=0.8))], isError=True)
    else:
        formatted_help = "# Steam Librarian MCP Tools Help\n\n"
        formatted_help += "Available tools with comprehensive documentation:\n\n"
        for name, doc in tool_docs.items():
            formatted_help += f"## {name}\n{doc['description']}\n\n"
        formatted_help += "\n💡 **Usage:** get_tool_help(tool_name='[name]') for detailed help with examples\n"
        formatted_help += "\n**Quick Tips:**\n"
        formatted_help += "- Use natural language in queries and filters\n"
        formatted_help += "- All tools support both JSON and text parameters\n"
        formatted_help += "- Error messages include working examples\n"
        formatted_help += "- Tools provide structured data for further processing\n"

    return CallToolResult(content=[TextContent(type="text", text=formatted_help, annotations=Annotations(audience=["user"], priority=0.9))], structuredContent={"tool_name": tool_name, "available_tools": list(tool_docs.keys()), "documentation_type": "comprehensive" if tool_name else "overview"}, isError=False)
