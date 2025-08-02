"""MCP tools using proper database schema and ORM"""

from mcp.server.fastmcp import Context
from mcp.types import SamplingMessage, TextContent
from pydantic import BaseModel, Field
from sqlalchemy.orm import joinedload

from shared.database import (
    Game,
    UserGame,
    UserProfile,
    Genre,
    get_db,
    resolve_user_for_tool,
    handle_user_not_found,
    handle_game_not_found,
)
from .config import config
from .server import mcp


def get_default_user_fallback():
    """Fallback function to get default user from config"""
    if config.default_user and config.default_user != "default":
        return config.default_user
    return None


@mcp.tool()
async def search_games(query: str, user: str = None) -> str:
    """Search for games in user's library by name or genre."""
    # Resolve user with default fallback
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"
    
    user_steam_id = user_result["steam_id"]
    
    try:
        with get_db() as session:
            # Get user info
            user_profile = session.query(UserProfile).filter_by(steam_id=user_steam_id).first()
            if not user_profile:
                return handle_user_not_found(user_steam_id)["message"]
            
            # Search user's games with all relationships loaded
            user_games_query = session.query(UserGame).options(
                joinedload(UserGame.game).joinedload(Game.genres),
                joinedload(UserGame.game).joinedload(Game.developers),
                joinedload(UserGame.game).joinedload(Game.categories)
            ).filter(UserGame.steam_id == user_steam_id)
            
            # Search by game name
            name_matches = []
            genre_matches = []
            
            for user_game in user_games_query:
                game = user_game.game
                
                # Name search
                if query.lower() in game.name.lower():
                    name_matches.append({
                        "name": game.name,
                        "playtime": user_game.playtime_hours,
                        "genres": [g.genre_name for g in game.genres]
                    })
                
                # Genre search
                for genre in game.genres:
                    if query.lower() in genre.genre_name.lower():
                        genre_matches.append({
                            "name": game.name,
                            "playtime": user_game.playtime_hours,
                            "genres": [g.genre_name for g in game.genres]
                        })
                        break
            
            # Format results
            results = []
            if name_matches:
                results.append(f"**Games matching '{query}':**")
                for match in name_matches[:10]:
                    genres_str = ", ".join(match["genres"]) if match["genres"] else "No genres"
                    results.append(f"- {match['name']} ({match['playtime']}h played) - {genres_str}")
            
            if genre_matches:
                if results:
                    results.append("")
                results.append(f"**Games in '{query}' genre:**")
                for match in genre_matches[:10]:
                    results.append(f"- {match['name']} ({match['playtime']}h played)")
            
            if not results:
                return f"No games found for {user_profile.persona_name} matching '{query}'"
            
            return f"Search results for {user_profile.persona_name}:\n\n" + "\n".join(results)
            
    except Exception as e:
        return f"Search failed: {str(e)}"


@mcp.tool()
async def generate_recommendation(genre: str, ctx: Context) -> str:
    """Generate game recommendation using LLM sampling."""
    prompt = f"Recommend a {genre} game from Steam with a brief description"
    
    try:
        result = await ctx.session.create_message(
            messages=[
                SamplingMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt)
                )
            ],
            max_tokens=100
        )
        
        if result.content.type == "text":
            return result.content.text
        return str(result.content)
    except Exception as e:
        return f"Failed to generate recommendation: {str(e)}"


class GamePreferences(BaseModel):
    """Schema for collecting user game preferences."""
    multiplayer: bool = Field(description="Include multiplayer games?")
    max_price: float = Field(description="Maximum price in USD", default=60.0)
    time_to_beat: str = Field(description="Preferred game length", default="any")


@mcp.tool()
async def find_games_with_preferences(initial_genre: str, ctx: Context, user: str = None) -> str:
    """Find games with user preferences via elicitation."""
    # Resolve user with default fallback
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"
    
    user_steam_id = user_result["steam_id"]
    
    try:
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
async def analyze_library(user: str = None, focus: str = "overview") -> str:
    """Analyze user's game library with detailed insights and patterns.
    
    Focus options: overview, genres, playtime, backlog, recommendations
    """
    # Resolve user with default fallback
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"
    
    user_steam_id = user_result["steam_id"]
    
    try:
        with get_db() as session:
            # Get user profile
            user_profile = session.query(UserProfile).filter_by(steam_id=user_steam_id).first()
            if not user_profile:
                return handle_user_not_found(user_steam_id)["message"]
            
            # Get user's games with all relationships
            user_games = session.query(UserGame).options(
                joinedload(UserGame.game).joinedload(Game.genres),
                joinedload(UserGame.game).joinedload(Game.categories),
                joinedload(UserGame.game).joinedload(Game.developers)
            ).filter(UserGame.steam_id == user_steam_id).all()
            
            response = f"**Library Analysis for {user_profile.persona_name}**\n\n"
            
            if focus == "overview" or focus == "all":
                # Basic stats
                total_games = len(user_games)
                total_playtime = sum(ug.playtime_forever for ug in user_games)
                played_games = sum(1 for ug in user_games if ug.playtime_forever > 0)
                recent_playtime = sum(ug.playtime_2weeks for ug in user_games)
                
                response += "**Overview:**\n"
                response += f"- Total games: {total_games}\n"
                response += f"- Games played: {played_games} ({round(played_games/total_games*100, 1)}%)\n"
                response += f"- Total playtime: {round(total_playtime/60, 1)} hours\n"
                response += f"- Recent playtime (2 weeks): {round(recent_playtime/60, 1)} hours\n"
                response += f"- Average playtime per game: {round(total_playtime/60/max(played_games, 1), 1)} hours\n\n"
            
            if focus == "genres" or focus == "all":
                # Genre analysis
                genre_data = {}
                for ug in user_games:
                    for genre in ug.game.genres:
                        if genre.genre_name not in genre_data:
                            genre_data[genre.genre_name] = {"count": 0, "playtime": 0, "games": []}
                        genre_data[genre.genre_name]["count"] += 1
                        genre_data[genre.genre_name]["playtime"] += ug.playtime_forever
                        if ug.playtime_forever > 0:
                            genre_data[genre.genre_name]["games"].append((ug.game.name, ug.playtime_forever))
                
                response += "**Genre Analysis:**\n"
                sorted_genres = sorted(genre_data.items(), key=lambda x: x[1]["playtime"], reverse=True)[:8]
                for genre, data in sorted_genres:
                    hours = round(data["playtime"]/60, 1)
                    response += f"- {genre}: {data['count']} games, {hours}h played\n"
                    if data["games"]:
                        top_game = max(data["games"], key=lambda x: x[1])
                        response += f"  Most played: {top_game[0]} ({round(top_game[1]/60, 1)}h)\n"
                response += "\n"
            
            if focus == "playtime" or focus == "all":
                # Playtime patterns
                response += "**Playtime Patterns:**\n"
                
                # Most played games
                played = [(ug, ug.playtime_forever) for ug in user_games if ug.playtime_forever > 0]
                played.sort(key=lambda x: x[1], reverse=True)
                
                response += "Top 5 most played:\n"
                for ug, _ in played[:5]:
                    response += f"- {ug.game.name}: {ug.playtime_hours}h\n"
                
                # Recently active
                recent = [(ug, ug.playtime_2weeks) for ug in user_games if ug.playtime_2weeks > 0]
                if recent:
                    response += f"\nRecently played ({len(recent)} games):\n"
                    recent.sort(key=lambda x: x[1], reverse=True)
                    for ug, _ in recent[:5]:
                        response += f"- {ug.game.name}: {ug.playtime_2weeks_hours}h in last 2 weeks\n"
                response += "\n"
            
            if focus == "backlog" or focus == "all":
                # Backlog analysis
                unplayed = [ug for ug in user_games if ug.playtime_forever == 0]
                barely_played = [ug for ug in user_games if 0 < ug.playtime_forever < 120]  # Less than 2 hours
                
                response += "**Backlog Analysis:**\n"
                response += f"- Unplayed games: {len(unplayed)} ({round(len(unplayed)/len(user_games)*100, 1)}%)\n"
                response += f"- Barely played (<2h): {len(barely_played)}\n"
                
                if unplayed:
                    # Sample some unplayed games with interesting characteristics
                    response += "\nSome unplayed games:\n"
                    # Show games with good reviews or interesting genres
                    interesting_unplayed = []
                    for ug in unplayed[:30]:  # Check first 30
                        game = ug.game
                        # Check if has positive reviews
                        if game.reviews and game.reviews.positive_percentage > 85:
                            interesting_unplayed.append((game, game.reviews.positive_percentage))
                    
                    # Sort by review percentage
                    interesting_unplayed.sort(key=lambda x: x[1], reverse=True)
                    
                    for game, pos_pct in interesting_unplayed[:5]:
                        genres = ", ".join([g.genre_name for g in game.genres][:2])
                        response += f"- {game.name} ({pos_pct}% positive"
                        if genres:
                            response += f", {genres}"
                        response += ")\n"
                    
                    # If no highly rated unplayed games, just show some random unplayed
                    if not interesting_unplayed and unplayed:
                        response += "Random selection:\n"
                        for ug in unplayed[:5]:
                            genres = ", ".join([g.genre_name for g in ug.game.genres][:2])
                            response += f"- {ug.game.name}"
                            if genres:
                                response += f" ({genres})"
                            response += "\n"
            
            return response
            
    except Exception as e:
        return f"Failed to analyze library: {str(e)}"


@mcp.tool()
async def get_game_details(game_name: str, user: str = None) -> str:
    """Get detailed information for a specific game."""
    # Resolve user (optional for this tool) with default fallback
    user_steam_id = None
    if user:
        user_result = resolve_user_for_tool(user, get_default_user_fallback)
        if not user_result.get("error"):
            user_steam_id = user_result["steam_id"]
    elif config.default_user and config.default_user != "default":
        # Even if user not specified, try to use default for personalized stats
        user_result = resolve_user_for_tool(None, get_default_user_fallback)
        if not user_result.get("error"):
            user_steam_id = user_result["steam_id"]
    
    try:
        with get_db() as session:
            # Find the game with all relationships
            game = session.query(Game).options(
                joinedload(Game.genres),
                joinedload(Game.developers),
                joinedload(Game.publishers),
                joinedload(Game.categories),
                joinedload(Game.reviews)
            ).filter(Game.name.ilike(f"%{game_name}%")).first()
            
            if not game:
                return handle_game_not_found(game_name)["message"]
            
            response = f"**{game.name}**\n"
            response += f"- App ID: {game.app_id}\n"
            
            if game.release_date:
                response += f"- Release Date: {game.release_date}\n"
            
            if game.developers:
                devs = ", ".join(d.developer_name for d in game.developers)
                response += f"- Developer(s): {devs}\n"
            
            if game.publishers:
                pubs = ", ".join(p.publisher_name for p in game.publishers)
                response += f"- Publisher(s): {pubs}\n"
            
            if game.genres:
                genres = ", ".join(g.genre_name for g in game.genres)
                response += f"- Genres: {genres}\n"
            
            if game.categories:
                cats = ", ".join(c.category_name for c in game.categories[:5])
                response += f"- Categories: {cats}\n"
            
            if game.esrb_rating:
                response += f"- ESRB Rating: {game.esrb_rating}\n"
            
            if game.required_age and game.required_age > 0:
                response += f"- Required Age: {game.required_age}+\n"
            
            if game.reviews:
                review = game.reviews
                if review.review_summary:
                    response += f"- Steam Reviews: {review.review_summary}"
                    if review.positive_percentage:
                        response += f" ({review.positive_percentage}% positive)"
                    response += "\n"
                if review.total_reviews:
                    response += f"- Total Reviews: {review.total_reviews:,}\n"
            
            # User-specific data if available
            if user_steam_id:
                user_game = session.query(UserGame).filter_by(
                    steam_id=user_steam_id,
                    app_id=game.app_id
                ).first()
                
                if user_game:
                    response += f"\n**Your Stats:**\n"
                    response += f"- Total playtime: {user_game.playtime_hours} hours\n"
                    if user_game.playtime_2weeks > 0:
                        response += f"- Recent playtime: {user_game.playtime_2weeks_hours} hours\n"
            
            return response
            
    except Exception as e:
        return f"Failed to get game details: {str(e)}"


