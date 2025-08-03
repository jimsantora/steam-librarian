"""Enhanced MCP prompts with proper annotations and argument descriptions for full specification compliance"""

from mcp.server.fastmcp.prompts import base
from mcp.types import Annotations, ResourceLink, TextContent

from .server import mcp


@mcp.prompt(
    name="family_games",
    title="Find Family-Friendly Games",
    description="Get age-appropriate game recommendations with ESRB/PEGI filtering for safe family gaming"
)
def family_games(child_age: int = 8) -> list[base.Message]:
    """Get age-appropriate game recommendations for family gaming.
    
    Args:
        child_age: Age of the child in years (used for ESRB/PEGI rating filtering, default: 8)
    """
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text=f"I need games suitable for my {child_age}-year-old child. What do you recommend?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text", 
                text=f"I'll find age-appropriate games for a {child_age}-year-old using our family-safe filtering system with ESRB and PEGI ratings.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            TextContent(
                type="text",
                text=f"Use recommend_games('family', '{{\"age\": {child_age}}}') to get games rated for this age group.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]


@mcp.prompt(
    name="quick_session",
    title="Quick Gaming Session",
    description="Find games perfect for short gaming sessions based on available time"
)
def quick_session(minutes_available: int = 30) -> list[base.Message]:
    """Find games perfect for short gaming sessions.
    
    Args:
        minutes_available: Available gaming time in minutes (default: 30)
    """
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text=f"I only have {minutes_available} minutes to play. What games would work well for a quick session?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text=f"Let me find games that are perfect for {minutes_available}-minute sessions using smart tag analysis.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            TextContent(
                type="text",
                text=f"Use recommend_games('quick_session', '{{\"minutes\": {minutes_available}}}') to get games suitable for short play sessions.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]


@mcp.prompt(
    name="unplayed_gems",
    title="Discover Unplayed Games", 
    description="Find highly-rated games in your library that you haven't played yet with embedded resource data"
)
def unplayed_gems() -> list[base.Message]:
    """Find highly-rated games in your library that you haven't played yet."""
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text="I have so many games in my library but I don't know what to play. Help me find some good ones I haven't tried yet.",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text="I'll help you discover hidden gems in your library - games you own but haven't played yet. Let me show you what's available.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            ResourceLink(
                type="resource_link",
                uri="library://games/unplayed",
                name="unplayed_games",
                description="Your highly-rated unplayed games with Metacritic scores ≥75",
                mimeType="application/json"
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text="Based on your unplayed games above, I recommend using recommend_games('unplayed_gems') to get personalized suggestions from these titles.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]


@mcp.prompt(
    name="similar_games", 
    title="Games Similar To Favorite",
    description="Find games similar to one you already love by analyzing genres, developers, and gameplay features"
)
def similar_games(game_name: str = "Portal") -> list[base.Message]:
    """Find games similar to one you already love.
    
    Args:
        game_name: Name of the game you enjoyed (default: Portal)
    """
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text=f"I really enjoyed {game_name}. Can you recommend similar games from my library?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text=f"I'll find games similar to {game_name} by analyzing genres, developers, and gameplay features.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            TextContent(
                type="text", 
                text=f"Use recommend_games('similar_to', '{{\"game_name\": \"{game_name}\"}}') to find games with similar characteristics.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]


@mcp.prompt(
    name="natural_search",
    title="Natural Language Game Search", 
    description="Search your library using natural language descriptions with AI interpretation"
)
def natural_search(query: str = "relaxing puzzle games") -> list[base.Message]:
    """Search your library using natural language descriptions.
    
    Args:
        query: Natural language description of games you're looking for (default: "relaxing puzzle games")
    """
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text=f"I'm looking for {query}. Can you search my library?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text=f"I'll search your library for '{query}' using AI to interpret your request and find matching games.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            TextContent(
                type="text",
                text=f"Use smart_search('{query}') to find games matching this description.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]


@mcp.prompt(
    name="gaming_insights",
    title="Analyze Gaming Patterns",
    description="Get AI-powered insights about your gaming habits and preferences with embedded library data"
)
def gaming_insights(analysis_type: str = "patterns") -> list[base.Message]:
    """Get AI-powered insights about your gaming habits and preferences.
    
    Args:
        analysis_type: Type of analysis to perform - patterns, value, social, genres, etc. (default: "patterns")
    """
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text="I'm curious about my gaming habits. Can you analyze my library and tell me what patterns you see?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text="I'll analyze your gaming patterns and provide insights about your preferences, habits, and gaming personality. Let me start by looking at your library overview.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            ResourceLink(
                type="resource_link",
                uri="library://overview",
                name="library_overview", 
                description="Your complete library overview with statistics, top genres, and gaming insights",
                mimeType="application/json"
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text=f"Based on your library data above, use get_library_insights('{analysis_type}') to get AI-powered analysis of your gaming patterns.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]


@mcp.prompt(
    name="mood_games",
    title="Mood-Based Game Selection",
    description="Get game recommendations based on your current mood by analyzing genres, tags, and gameplay styles"
)
def mood_games(mood: str = "relaxing") -> list[base.Message]:
    """Get game recommendations based on your current mood.
    
    Args:
        mood: Your current emotional state - relaxing, energetic, challenging, social, etc. (default: "relaxing")
    """
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text=f"I'm feeling {mood} today. What games would match this mood?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text=f"I'll recommend games that match a {mood} mood by analyzing genres, tags, and gameplay styles.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            TextContent(
                type="text",
                text=f"Use recommend_games('mood_based', '{{\"mood\": \"{mood}\"}}') to get games matching this emotional state.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]


@mcp.prompt(
    name="abandoned_games",
    title="Find Abandoned Games",
    description="Rediscover games you started but never finished - perfect candidates for revisiting"
)
def abandoned_games() -> list[base.Message]:
    """Rediscover games you started but never finished."""
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text="I have a habit of starting games but not finishing them. Can you help me find games I should revisit?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text="I'll find games in your library that you started playing but haven't touched in a while - perfect candidates for revisiting.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            TextContent(
                type="text",
                text="Use recommend_games('abandoned') to find games you have some playtime in but haven't completed or played recently.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]


@mcp.prompt(
    name="explore_genre",
    title="Explore Games by Genre",
    description="Explore all games in your library by a specific genre with embedded game data"
)
def explore_genre(genre_name: str = "Puzzle") -> list[base.Message]:
    """Explore all games in your library by a specific genre.
    
    Args:
        genre_name: Genre to explore - Action, Adventure, RPG, Strategy, Puzzle, etc. (default: "Puzzle")
    """
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text=f"I'm interested in {genre_name} games. Can you show me what I have in my library?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text=f"I'll show you all the {genre_name} games in your library with their details and playtime information.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            ResourceLink(
                type="resource_link",
                uri=f"library://genres/{genre_name}/games",
                name=f"{genre_name.lower()}_games",
                description=f"All {genre_name} games in your library with developers and review scores",
                mimeType="application/json"
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text=f"Here are your {genre_name} games! You can also use smart_search('{genre_name.lower()} games') to find specific ones based on other criteria.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]


@mcp.prompt(
    name="user_profile",
    title="View User Profile & Stats",
    description="View your complete Steam profile and gaming statistics with embedded profile data"
)
def user_profile() -> list[base.Message]:
    """View your complete Steam profile and gaming statistics."""
    return [
        base.UserMessage(
            TextContent(
                type="text",
                text="Can you show me my Steam profile and gaming statistics?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text="I'll display your complete Steam profile including gaming statistics, library overview, and account details.",
                annotations=Annotations(audience=["assistant"], priority=0.8)
            )
        ),
        base.UserMessage(
            ResourceLink(
                type="resource_link",
                uri="library://users/default",
                name="user_profile",
                description="Your complete Steam profile with persona, level, XP, location, and game count",
                mimeType="application/json"
            )
        ),
        base.AssistantMessage(
            TextContent(
                type="text",
                text="Here's your profile! You can also access library://users/default/games for your complete game list or library://users/default/stats for detailed gaming statistics.",
                annotations=Annotations(audience=["assistant"], priority=0.7)
            )
        )
    ]
