# src/mcp_server/completions.py
from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)

from shared.database import Game, UserGame, get_db

# Import the server instance from server.py
from .server import mcp


@mcp.completion()
async def tool_argument_completions(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion | None:
    """Provide intelligent completions for tool arguments."""

    # Handle tool-specific completions
    if hasattr(ref, "toolName"):
        tool_name = ref.toolName

        # Smart search completions
        if tool_name == "smart_search":
            if argument.name == "query":
                # Provide popular searches and game names from database
                try:
                    with get_db() as session:
                        # Get top 5 games by playtime
                        top_games = session.query(Game.name).join(UserGame).order_by(UserGame.playtime_forever.desc()).limit(5).all()

                        suggestions = [g[0] for g in top_games]
                        suggestions.extend(["unplayed gems", "family games", "quick session", "relaxing", "action", "indie"])

                        matching = [s for s in suggestions if s.lower().startswith(argument.value.lower())]
                        return Completion(values=matching[:10], hasMore=len(matching) > 10)
                except Exception:
                    pass  # Fallback to basic suggestions

                return Completion(values=["unplayed gems", "family games", "multiplayer", "coop", "puzzle", "action"], hasMore=False)

            elif argument.name == "filters":
                # Provide filter templates
                templates = ['{"genres": ["Action"], "categories": ["Single-player"]}', '{"tags": ["Roguelike"], "playtime": "played"}', '{"categories": ["Co-op", "Multi-player"]}', '{"playtime": "unplayed", "tags": ["Indie"]}', '{"genres": ["Puzzle", "Casual"], "playtime": "any"}']
                return Completion(values=templates, hasMore=False)

            elif argument.name == "sort_by":
                options = ["relevance", "playtime", "metacritic", "recent", "random"]
                matching = [o for o in options if o.startswith(argument.value.lower())]
                return Completion(values=matching, hasMore=False)

        # Recommendation engine completions
        elif tool_name == "recommend_games":
            if argument.name == "context":
                contexts = ["family", "quick_session", "similar_to", "mood_based", "unplayed_gems", "abandoned"]
                matching = [c for c in contexts if c.startswith(argument.value.lower())]
                return Completion(values=matching, hasMore=False)

            elif argument.name == "parameters":
                # Context-specific parameter templates
                if "family" in argument.value.lower():
                    return Completion(values=['{"age": 8, "players": 1}', '{"age": 12, "players": 2, "content_concerns": ["violence"]}', '{"age": 5, "content_concerns": ["scary", "complex"]}'], hasMore=False)
                elif "quick_session" in argument.value.lower():
                    return Completion(values=['{"minutes": 15}', '{"minutes": 30}', '{"minutes": 60}'], hasMore=False)
                elif "similar_to" in argument.value.lower():
                    try:
                        with get_db() as session:
                            # Get popular game names for similar_to
                            popular_games = session.query(Game.name).join(UserGame).filter(UserGame.playtime_forever > 300).order_by(UserGame.playtime_forever.desc()).limit(8).all()  # 5+ hours

                            game_templates = [f'{{"game": "{g[0]}"}}' for g in popular_games]
                            return Completion(values=game_templates, hasMore=False)
                    except Exception:
                        pass
                    return Completion(values=['{"game": "Portal"}', '{"game": "Stardew Valley"}', '{"game": "Terraria"}'], hasMore=False)
                elif "mood_based" in argument.value.lower():
                    return Completion(values=['{"mood": "relaxing"}', '{"mood": "energetic"}', '{"mood": "competitive"}', '{"mood": "social"}', '{"mood": "creative"}', '{"mood": "story"}'], hasMore=False)

        # Library insights completions
        elif tool_name == "get_library_insights":
            if argument.name == "analysis_type":
                types = ["patterns", "gaps", "value", "social", "achievements", "trends"]
                matching = [t for t in types if t.startswith(argument.value.lower())]
                return Completion(values=matching, hasMore=False)

            elif argument.name == "compare_to":
                options = ["friends", "global", "genre_average"]
                matching = [o for o in options if o.startswith(argument.value.lower())]
                return Completion(values=matching, hasMore=False)

            elif argument.name == "time_range":
                ranges = ["all", "recent", "last_month"]
                matching = [r for r in ranges if r.startswith(argument.value.lower())]
                return Completion(values=matching, hasMore=False)

        # Legacy tool completions (kept for backwards compatibility)
        elif argument.name == "child_age" and tool_name == "find_family_games":
            return Completion(values=["3", "5", "7", "10", "13", "16"], hasMore=False)

        elif argument.name == "session_length" and tool_name == "find_quick_session_games":
            return Completion(values=["short", "medium", "long"], hasMore=False)

        # Generic user completions for all tools
        elif argument.name == "user":
            try:
                with get_db() as session:
                    from shared.database import UserProfile

                    users = session.query(UserProfile).all()

                    user_suggestions = []
                    for user in users:
                        # Add both steam_id and persona_name as options
                        user_suggestions.append(user.steam_id)
                        if user.persona_name:
                            user_suggestions.append(user.persona_name)

                    matching = [u for u in user_suggestions if u.lower().startswith(argument.value.lower())]
                    return Completion(values=matching[:10], hasMore=len(matching) > 10)
            except Exception:
                pass  # Fall back to no suggestions

    return None
