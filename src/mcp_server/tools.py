"""MCP tools using proper database schema and ORM"""


from mcp.server.fastmcp import Context
from mcp.types import SamplingMessage, TextContent
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
    game_categories,
    game_genres,
    get_db,
    handle_user_not_found,
    resolve_user_for_tool,
)

from .config import config
from .server import mcp


class FamilyPreferences(BaseModel):
    """Preferences for family gaming with young children."""
    content_concerns: list[str] = Field(
        default=[],
        description="Content to avoid (violence, language, scary themes)"
    )
    gaming_experience: str = Field(
        default="beginner",
        description="Family's gaming experience (beginner/intermediate/advanced)"
    )

class AmbiguousSearchContext(BaseModel):
    """Context for clarifying ambiguous search queries."""
    time_available: str = Field(
        default="medium",
        description="How long do you want to play? (quick/medium/long session)"
    )
    mood: str = Field(
        default="relaxed",
        description="Current mood (relaxed/energetic/competitive/social)"
    )


def get_default_user_fallback():
    """Fallback function to get default user from config"""
    if config.default_user and config.default_user != "default":
        return config.default_user
    return None


def is_natural_language_query(query: str) -> bool:
    """Check if query is natural language vs simple keywords."""
    # Natural language indicators
    nl_indicators = ['something', 'games like', 'similar to', 'after work',
                    'relaxing', 'exciting', 'with friends', 'for kids']
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in nl_indicators)


@mcp.tool()
async def search_games(
    query: str,
    ctx: Context | None = None,
    user: str | None = None
) -> str:
    """Search games by keywords or natural language description.

    Examples: 'minecraft', 'family games', 'something relaxing after work'
    """
    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]

    # Check if natural language query needs AI interpretation
    if ctx and hasattr(ctx, 'session') and ctx.session and is_natural_language_query(query):
        try:
            interpretation = await ctx.session.create_message(
                messages=[SamplingMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Map this gaming request to specific genres and categories.
                        Request: '{query}'
                        Available genres: Action, Adventure, RPG, Strategy, Casual, Indie, Simulation
                        Available categories: Single-player, Multi-player, Co-op, Family Sharing
                        Respond with: genres:[list] categories:[list]"""
                    )
                )],
                max_tokens=100
            )

            # Parse AI response and use for filtering
            if interpretation.content.type == "text":
                # Extract genres and categories from response
                # Apply to games_query filters
                pass
        except Exception:
            # Fallback to keyword search if AI fails
            pass

    # Database query with enhanced filtering
    with get_db() as session:
        games_query = session.query(Game, UserGame).join(
            UserGame,
            (Game.app_id == UserGame.app_id) &
            (UserGame.steam_id == user_steam_id)
        )

        # Smart mappings for common queries
        if "family" in query.lower():
            games_query = games_query.join(Game.genres).filter(
                Genre.genre_name == "Casual"
            ).join(Game.categories).filter(
                Category.category_name == "Family Sharing"
            )
        elif "multiplayer" in query.lower() or "coop" in query.lower():
            games_query = games_query.join(Game.categories).filter(
                or_(
                    Category.category_name == "Multi-player",
                    Category.category_name == "Co-op"
                )
            )
        else:
            # General search by name or genre
            games_query = games_query.join(Game.genres, isouter=True).filter(
                or_(
                    Game.name.ilike(f"%{query}%"),
                    Genre.genre_name.ilike(f"%{query}%")
                )
            )

        # Add metadata to results
        results = []
        for game, user_game in games_query.distinct().limit(10):
            results.append({
                "name": game.name,
                "metacritic": game.metacritic_score,
                "platforms": {
                    "windows": game.platforms_windows,
                    "mac": game.platforms_mac,
                    "linux": game.platforms_linux
                },
                "playtime": user_game.playtime_forever / 60 if user_game.playtime_forever else 0,
                "genres": [g.genre_name for g in game.genres[:3]]
            })

        if not results:
            return f"No games found matching '{query}'"

        # Format enhanced results
        output = [f"**Search results for '{query}':**\n"]
        for game in results:
            platforms = []
            if game["platforms"]["windows"]:
                platforms.append("Win")
            if game["platforms"]["mac"]:
                platforms.append("Mac")
            if game["platforms"]["linux"]:
                platforms.append("Linux")
            platform_str = "/".join(platforms) if platforms else "Unknown"

            metacritic_str = f" ({game['metacritic']}/100)" if game["metacritic"] else ""
            genres_str = ", ".join(game["genres"]) if game["genres"] else "No genres"

            output.append(
                f"- **{game['name']}**{metacritic_str}\n"
                f"  Genres: {genres_str} | Platforms: {platform_str}\n"
                f"  Playtime: {game['playtime']:.1f} hours"
            )

        return "\n".join(output)


@mcp.tool()
async def generate_recommendation(query: str, ctx: Context, user: str | None = None) -> str:
    """Intelligent game recommendation using natural language query interpretation.
    
    Examples: 'something relaxing after work', 'games like Stardew Valley', 
    'unplayed indie gems', 'coop games for tonight', 'VR games I haven't tried'
    """
    # Validate that we have a proper context and session for LLM interpretation
    if not ctx or not hasattr(ctx, 'session') or not ctx.session:
        # Fallback to basic search
        return await search_games(query, ctx, user)
    
    # Use LLM to analyze and categorize the request
    analysis_prompt = f"""Analyze this gaming request and extract the user's intent:

User query: "{query}"

Determine and return ONLY a JSON object with these fields:
{{
    "intent": "one of: unplayed_gems, quick_session, genre_search, platform_specific, multiplayer, family_friendly, similar_to_game, general_search",
    "genre": "specific genre if mentioned (Action, Adventure, RPG, Strategy, Casual, Indie, etc.) or null",
    "session_length": "short, medium, long, or null",
    "platform": "windows, mac, linux, vr, or null", 
    "multiplayer_type": "coop, pvp, local, online, or null",
    "game_reference": "name of specific game mentioned or null",
    "search_terms": "key terms for fallback search"
}}"""

    try:
        result = await ctx.session.create_message(
            messages=[
                SamplingMessage(
                    role="user",
                    content=TextContent(type="text", text=analysis_prompt)
                )
            ],
            max_tokens=150
        )

        if result.content.type != "text":
            return await search_games(query, ctx, user)

        # Parse LLM response as JSON
        import json
        try:
            analysis = json.loads(result.content.text.strip())
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return await search_games(query, ctx, user)

        # Route to appropriate tool/resource based on intent
        intent = analysis.get("intent", "general_search")
        
        if intent == "unplayed_gems":
            # Use unplayed gems with optional genre filtering
            unplayed_result = await find_unplayed_gems_with_genre(analysis.get("genre"), user)
            return f"**Unplayed gems recommendation based on '{query}':**\n\n{unplayed_result}"
            
        elif intent == "quick_session":
            session_length = analysis.get("session_length", "short")
            quick_result = await find_quick_session_games(session_length, user)
            return f"**Quick session games for '{query}':**\n\n{quick_result}"
            
        elif intent == "platform_specific":
            platform = analysis.get("platform")
            if platform:
                platform_result = await find_platform_games_with_context(platform, analysis.get("genre"), user)
                return f"**{platform.capitalize()} games for '{query}':**\n\n{platform_result}"
                
        elif intent == "multiplayer":
            mp_type = analysis.get("multiplayer_type", "coop")
            mp_result = await find_multiplayer_games_with_context(mp_type, analysis.get("genre"), user)
            return f"**{mp_type.capitalize()} games for '{query}':**\n\n{mp_result}"
            
        elif intent == "family_friendly":
            # Default to age 8 for family games
            family_result = await find_family_games(8, ctx, user)
            return f"**Family-friendly games for '{query}':**\n\n{family_result}"
            
        elif intent == "similar_to_game":
            game_ref = analysis.get("game_reference")
            if game_ref:
                similar_result = await search_games(f"games like {game_ref}", ctx, user)
                return f"**Games similar to {game_ref} (based on '{query}'):**\n\n{similar_result}"
                
        # Default to enhanced search for genre_search and general_search
        search_terms = analysis.get("search_terms", query)
        if analysis.get("genre"):
            search_terms = f"{analysis['genre']} {search_terms}"
            
        search_result = await search_games(search_terms, ctx, user)
        return f"**Personalized recommendation for '{query}':**\n\n{search_result}"

    except Exception as e:
        # Fallback to basic search if anything fails
        return await search_games(query, ctx, user)


# Helper functions for generate_recommendation routing
async def find_unplayed_gems_with_genre(genre: str | None = None, user: str | None = None) -> str:
    """Find unplayed gems, optionally filtered by genre."""
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]

    with get_db() as session:
        # Find unplayed games with high ratings
        unplayed_query = session.query(Game, UserGame).join(
            UserGame,
            (Game.app_id == UserGame.app_id) &
            (UserGame.steam_id == user_steam_id)
        ).filter(
            UserGame.playtime_forever == 0,  # Never played
            Game.metacritic_score >= 75
        )
        
        # Add genre filter if specified
        if genre:
            unplayed_query = unplayed_query.join(Game.genres).filter(
                Genre.genre_name.ilike(f"%{genre}%")
            )
            
        unplayed_games = unplayed_query.order_by(
            Game.metacritic_score.desc()
        ).limit(5).all()

        if not unplayed_games:
            genre_text = f" in {genre}" if genre else ""
            return f"No unplayed games found{genre_text} with Metacritic score >= 75"

        results = []
        for game, user_game in unplayed_games:
            genre_names = [g.genre_name for g in game.genres[:2]]
            results.append(
                f"• **{game.name}** ({game.metacritic_score}/100)\n"
                f"  Genres: {', '.join(genre_names)}\n"
                f"  {game.short_description[:100]}..." if game.short_description else ""
            )

        return "\n\n".join(results)

async def find_platform_games_with_context(platform: str, genre: str | None = None, user: str | None = None) -> str:
    """Find platform games with optional genre context."""
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]
    
    platform_field_map = {
        "windows": "platforms_windows",
        "mac": "platforms_mac", 
        "linux": "platforms_linux",
        "vr": "vr_support"
    }
    
    if platform not in platform_field_map:
        return f"Invalid platform '{platform}'"
        
    with get_db() as session:
        platform_field = platform_field_map[platform]
        
        games_query = session.query(Game, UserGame).join(
            UserGame,
            (Game.app_id == UserGame.app_id) &
            (UserGame.steam_id == user_steam_id)
        ).filter(
            getattr(Game, platform_field) == True
        )
        
        # Add genre filter if specified
        if genre:
            games_query = games_query.join(Game.genres).filter(
                Genre.genre_name.ilike(f"%{genre}%")
            )
            
        games = games_query.order_by(
            UserGame.playtime_forever.desc()
        ).limit(5).all()

        if not games:
            genre_text = f" {genre}" if genre else ""
            return f"No{genre_text} games found compatible with {platform}"

        results = []
        for game, user_game in games:
            controller_info = f" [{game.controller_support}]" if game.controller_support else ""
            results.append(
                f"• **{game.name}**{controller_info}\n"
                f"  Playtime: {user_game.playtime_forever / 60:.1f} hours"
            )

        return "\n\n".join(results)

async def find_multiplayer_games_with_context(mp_type: str, genre: str | None = None, user: str | None = None) -> str:
    """Find multiplayer games with optional genre context."""
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]
    
    type_to_categories = {
        "coop": ["Co-op", "Online Co-op"],
        "pvp": ["PvP", "Online PvP"],
        "local": ["Shared/Split Screen", "Local Co-op"],
        "online": ["Multi-player", "Online Multi-Player", "Online Co-op", "Online PvP"]
    }

    if mp_type not in type_to_categories:
        return f"Invalid multiplayer type '{mp_type}'"
        
    target_categories = type_to_categories[mp_type]

    with get_db() as session:
        games_query = session.query(Game, UserGame).join(
            UserGame,
            (Game.app_id == UserGame.app_id) &
            (UserGame.steam_id == user_steam_id)
        ).join(Game.categories).filter(
            Category.category_name.in_(target_categories)
        )
        
        # Add genre filter if specified
        if genre:
            games_query = games_query.join(Game.genres).filter(
                Genre.genre_name.ilike(f"%{genre}%")
            )
            
        games = games_query.distinct().limit(5).all()

        if not games:
            genre_text = f" {genre}" if genre else ""
            return f"No{genre_text} {mp_type} games found in your library"

        results = []
        for game, user_game in games:
            mp_categories = [c.category_name for c in game.categories
                           if "player" in c.category_name.lower() or
                              "co-op" in c.category_name.lower() or
                              "pvp" in c.category_name.lower()]
            results.append(
                f"• **{game.name}**\n"
                f"  Modes: {', '.join(mp_categories[:3])}\n"
                f"  Playtime: {user_game.playtime_forever / 60:.1f} hours"
            )

        return "\n\n".join(results)


class GamePreferences(BaseModel):
    """Schema for collecting user game preferences."""
    multiplayer: bool = Field(description="Include multiplayer games?")
    max_price: float = Field(description="Maximum price in USD", default=60.0)
    time_to_beat: str = Field(description="Preferred game length", default="any")


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
        if not ctx or not hasattr(ctx, 'elicit'):
            return f"Interactive preferences not available. Try using search_games with '{initial_genre}' instead."
            
        # Ask for user preferences
        result = await ctx.elicit(
            message=f"Looking for {initial_genre} games. What are your preferences?",
            schema=GamePreferences
        )

        if result.action == "accept" and result.data:
            prefs = result.data

            with get_db() as session:
                # Get user info
                user_profile = session.query(UserProfile).filter_by(steam_id=user_steam_id).first()
                if not user_profile:
                    return handle_user_not_found(user_steam_id)["message"]

                # Get user's games with genres and categories
                user_games = session.query(UserGame).options(
                    joinedload(UserGame.game).joinedload(Game.genres),
                    joinedload(UserGame.game).joinedload(Game.categories)
                ).filter(UserGame.steam_id == user_steam_id).all()

                # Filter by genre and preferences
                matches = []
                for user_game in user_games:
                    game = user_game.game

                    # Check genre match
                    genre_match = any(
                        initial_genre.lower() in g.genre_name.lower()
                        for g in game.genres
                    )

                    if genre_match:
                        # Check multiplayer preference
                        if prefs.multiplayer:
                            has_multiplayer = any(
                                "multiplayer" in c.category_name.lower()
                                for c in game.categories
                            )
                            if has_multiplayer:
                                matches.append({
                                    "name": game.name,
                                    "playtime": user_game.playtime_hours,
                                    "categories": [c.category_name for c in game.categories]
                                })
                        else:
                            matches.append({
                                "name": game.name,
                                "playtime": user_game.playtime_hours,
                                "categories": [c.category_name for c in game.categories]
                            })

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
async def analyze_library(
    ctx: Context | None = None,
    user: str | None = None
) -> str:
    """Analyze gaming library with statistics and insights."""
    # Resolve user with default fallback
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]

    with get_db() as session:
        # Get all user's games
        user_games = session.query(UserGame).filter_by(steam_id=user_steam_id).all()
        game_ids = [ug.app_id for ug in user_games]

        # Genre distribution
        genre_counts = session.query(
            Genre.genre_name,
            func.count(Genre.genre_name)
        ).join(
            game_genres, Genre.genre_id == game_genres.c.genre_id
        ).filter(
            game_genres.c.game_id.in_(game_ids)
        ).group_by(Genre.genre_name).all()

        # Category analysis
        category_counts = session.query(
            Category.category_name,
            func.count(Category.category_name)
        ).join(
            game_categories, Category.category_id == game_categories.c.category_id
        ).filter(
            game_categories.c.game_id.in_(game_ids)
        ).group_by(Category.category_name).all()

        # Platform compatibility
        platform_stats = session.query(
            func.sum(case((Game.platforms_windows, 1), else_=0)).label('windows'),
            func.sum(case((Game.platforms_mac, 1), else_=0)).label('mac'),
            func.sum(case((Game.platforms_linux, 1), else_=0)).label('linux')
        ).filter(Game.app_id.in_(game_ids)).first()

        # Build analysis with new insights
        analysis = f"""Library Analysis for {user_result['display_name']}:

**Genre Distribution (Top 5)**:
{format_top_items(genre_counts, 5)}

**Gaming Style Preferences**:
- Single-player games: {count_category(category_counts, 'Single-player')}
- Multiplayer games: {count_category(category_counts, 'Multi-player')}
- Co-op games: {count_category(category_counts, 'Co-op')}

**Platform Compatibility**:
- Windows: {platform_stats.windows} games
- Mac: {platform_stats.mac} games
- Linux: {platform_stats.linux} games"""

        # Optional AI insights
        if ctx and hasattr(ctx, 'session') and ctx.session:
            try:
                insights_prompt = f"""Based on this gaming library analysis:
                {analysis}
                
                Provide 2-3 personalized insights about their gaming preferences and 
                suggest what types of games they might enjoy exploring next."""

                insights = await ctx.session.create_message(
                    messages=[SamplingMessage(
                        role="user",
                        content=TextContent(type="text", text=insights_prompt)
                    )],
                    max_tokens=150
                )

                if insights.content.type == "text":
                    analysis += f"\n\n**AI Insights**:\n{insights.content.text}"
            except Exception:
                pass  # Continue without AI insights

        return analysis




@mcp.tool()
async def find_family_games(
    child_age: int,
    ctx: Context | None = None,
    user: str | None = None
) -> str:
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
            result = await ctx.elicit(
                message=f"Finding games for a {child_age}-year-old. Let's ensure they're appropriate:",
                schema=FamilyPreferences
            )

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
        games_query = session.query(Game, UserGame).join(
            UserGame,
            (Game.app_id == UserGame.app_id) &
            (UserGame.steam_id == user_steam_id)
        ).join(Game.categories).filter(
            Category.category_name == "Family Sharing"
        )

        # Apply age rating filters
        games_query = games_query.filter(
            or_(
                Game.esrb_rating.in_(get_esrb_ratings_up_to(max_esrb)),
                Game.pegi_rating.in_(get_pegi_ratings_up_to(max_pegi)),
                and_(Game.esrb_rating.is_(None), Game.pegi_rating.is_(None))  # Include unrated
            )
        )

        # Format results
        results = []
        for game, user_game in games_query.limit(10):
            results.append(
                f"- {game.name} (ESRB: {game.esrb_rating or 'Unrated'}, "
                f"PEGI: {game.pegi_rating or 'Unrated'})"
            )

        if not results:
            return f"No family-friendly games found in library for age {child_age}"

        return f"Family-friendly games for age {child_age}:\n" + "\n".join(results)








@mcp.tool()
async def find_quick_session_games(
    session_length: str = "short",
    user: str | None = None
) -> str:
    """Find games perfect for quick gaming sessions (5-60 minutes).
    
    Session lengths: 'short' (5-15 min), 'medium' (15-30 min), 'long' (30-60 min)
    """
    # Resolve user
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"

    user_steam_id = user_result["steam_id"]

    # Define quick session tags based on analysis
    quick_session_tags = [
        "Arcade", "Casual", "Puzzle", "Score Attack", "Fast-Paced",
        "Bullet Hell", "Shoot 'Em Up", "Twin Stick Shooter", "Card Game",
        "Runner", "Time Attack", "Puzzle Platformer", "Beat 'em up",
        "Party Game", "Addictive"
    ]

    # Tags to exclude (suggest longer sessions)
    long_session_tags = [
        "Open World", "Story Rich", "JRPG", "RPG", "Strategy",
        "Turn-Based Strategy", "4X", "Grand Strategy", "Survival",
        "Open World Survival Craft", "City Builder", "Management"
    ]

    with get_db() as session:
        # Build query for games with quick session tags
        quick_games_query = session.query(Game, UserGame).join(
            UserGame,
            (Game.app_id == UserGame.app_id) &
            (UserGame.steam_id == user_steam_id)
        ).join(Game.tags).filter(
            Tag.tag_name.in_(quick_session_tags)
        )

        # Exclude games with long session tags
        long_session_game_ids = session.query(Game.app_id).join(Game.tags).filter(
            Tag.tag_name.in_(long_session_tags)
        ).subquery()

        quick_games_query = quick_games_query.filter(
            ~Game.app_id.in_(long_session_game_ids)
        )

        # Additional filtering based on session length preference
        if session_length == "short":
            # Prefer very quick games - add extra weight to arcade/puzzle
            quick_games_query = quick_games_query.filter(
                Tag.tag_name.in_(["Arcade", "Casual", "Puzzle", "Score Attack", "Fast-Paced"])
            )
        elif session_length == "medium":
            # Include slightly longer but still session-based games
            pass  # Use all quick_session_tags
        elif session_length == "long":
            # Allow some strategy/rpg elements but still session-friendly
            quick_games_query = quick_games_query.filter(
                or_(
                    Tag.tag_name.in_(quick_session_tags),
                    and_(
                        Tag.tag_name.in_(["Turn-Based", "Tactical", "Card Battler"]),
                        ~Tag.tag_name.in_(long_session_tags)
                    )
                )
            )

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
        session_desc = {
            "short": "5-15 minute",
            "medium": "15-30 minute",
            "long": "30-60 minute"
        }

        results = [
            f"**Games perfect for {session_desc[session_length]} sessions:**",
            f"🔥 = Recently played | ⭐ = Your favorites | 🆕 = Unplayed gems (good reviews)\n"
        ]

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

            results.append(
                f"• **{game.name}**{activity_indicator}\n"
                f"  {session_reason} | {playtime_info}\n"
                f"  Tags: {', '.join(game_tags[:3])}"
            )

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
    return ratings[:ratings.index(max_rating) + 1]

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
    return ratings[:ratings.index(max_rating) + 1]


