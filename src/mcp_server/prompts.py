"""MCP prompts that provide actionable conversation templates with embedded resources"""

from mcp.server.fastmcp.prompts import base
from mcp.types import EmbeddedResource

from .server import mcp


@mcp.prompt(title="Find Family-Friendly Games")
def family_games(child_age: int = 8) -> list[base.Message]:
    """Get age-appropriate game recommendations for family gaming."""
    return [
        base.UserMessage(f"I need games suitable for my {child_age}-year-old child. What do you recommend?"),
        base.AssistantMessage(f"I'll find age-appropriate games for a {child_age}-year-old using our family-safe filtering system."),
        base.UserMessage(f"Use recommend_games('family', '{{\"age\": {child_age}}}') to get games rated for this age group.")
    ]


@mcp.prompt(title="Quick Gaming Session")
def quick_session(minutes_available: int = 30) -> list[base.Message]:
    """Find games perfect for short gaming sessions."""
    return [
        base.UserMessage(f"I only have {minutes_available} minutes to play. What games would work well for a quick session?"),
        base.AssistantMessage(f"Let me find games that are perfect for {minutes_available}-minute sessions."),
        base.UserMessage(f"Use recommend_games('quick_session', '{{\"minutes\": {minutes_available}}}') to get games suitable for short play sessions.")
    ]


@mcp.prompt(title="Discover Unplayed Games")
def unplayed_gems() -> list[base.Message]:
    """Find highly-rated games in your library that you haven't played yet."""
    return [
        base.UserMessage("I have so many games in my library but I don't know what to play. Help me find some good ones I haven't tried yet."),
        base.AssistantMessage("I'll help you discover hidden gems in your library - games you own but haven't played yet. Let me show you what's available."),
        base.UserMessage(
            EmbeddedResource(
                uri="library://games/unplayed",
                name="unplayed_games",
                description="Your highly-rated unplayed games",
                mimeType="application/json"
            )
        ),
        base.AssistantMessage("Based on your unplayed games above, I recommend using recommend_games('unplayed_gems') to get personalized suggestions from these titles.")
    ]


@mcp.prompt(title="Games Similar To Favorite")
def similar_games(game_name: str = "Portal") -> list[base.Message]:
    """Find games similar to one you already love."""
    return [
        base.UserMessage(f"I really enjoyed {game_name}. Can you recommend similar games from my library?"),
        base.AssistantMessage(f"I'll find games similar to {game_name} by analyzing genres, developers, and gameplay features."),
        base.UserMessage(f"Use recommend_games('similar_to', '{{\"game_name\": \"{game_name}\"}}') to find games with similar characteristics.")
    ]


@mcp.prompt(title="Natural Language Game Search")
def natural_search(query: str = "relaxing puzzle games") -> list[base.Message]:
    """Search your library using natural language descriptions."""
    return [
        base.UserMessage(f"I'm looking for {query}. Can you search my library?"),
        base.AssistantMessage(f"I'll search your library for '{query}' using AI to interpret your request and find matching games."),
        base.UserMessage(f"Use smart_search('{query}') to find games matching this description.")
    ]


@mcp.prompt(title="Analyze Gaming Patterns")
def gaming_insights(analysis_type: str = "patterns") -> list[base.Message]:
    """Get AI-powered insights about your gaming habits and preferences."""
    return [
        base.UserMessage("I'm curious about my gaming habits. Can you analyze my library and tell me what patterns you see?"),
        base.AssistantMessage("I'll analyze your gaming patterns and provide insights about your preferences, habits, and gaming personality. Let me start by looking at your library overview."),
        base.UserMessage(
            EmbeddedResource(
                uri="library://overview",
                name="library_overview",
                description="Your complete library overview and statistics",
                mimeType="application/json"
            )
        ),
        base.AssistantMessage(f"Based on your library data above, use get_library_insights('{analysis_type}') to get AI-powered analysis of your gaming patterns.")
    ]


@mcp.prompt(title="Mood-Based Game Selection")
def mood_games(mood: str = "relaxing") -> list[base.Message]:
    """Get game recommendations based on your current mood."""
    return [
        base.UserMessage(f"I'm feeling {mood} today. What games would match this mood?"),
        base.AssistantMessage(f"I'll recommend games that match a {mood} mood by analyzing genres, tags, and gameplay styles."),
        base.UserMessage(f"Use recommend_games('mood_based', '{{\"mood\": \"{mood}\"}}') to get games matching this emotional state.")
    ]


@mcp.prompt(title="Find Abandoned Games")
def abandoned_games() -> list[base.Message]:
    """Rediscover games you started but never finished."""
    return [
        base.UserMessage("I have a habit of starting games but not finishing them. Can you help me find games I should revisit?"),
        base.AssistantMessage("I'll find games in your library that you started playing but haven't touched in a while - perfect candidates for revisiting."),
        base.UserMessage("Use recommend_games('abandoned') to find games you have some playtime in but haven't completed or played recently.")
    ]


@mcp.prompt(title="Explore Games by Genre")
def explore_genre(genre_name: str = "Puzzle") -> list[base.Message]:
    """Explore all games in your library by a specific genre."""
    return [
        base.UserMessage(f"I'm interested in {genre_name} games. Can you show me what I have in my library?"),
        base.AssistantMessage(f"I'll show you all the {genre_name} games in your library with their details and playtime information."),
        base.UserMessage(
            EmbeddedResource(
                uri=f"library://genres/{genre_name}/games",
                name=f"{genre_name.lower()}_games",
                description=f"All {genre_name} games in your library",
                mimeType="application/json"
            )
        ),
        base.AssistantMessage(f"Here are your {genre_name} games! You can also use smart_search('{genre_name.lower()} games') to find specific ones based on other criteria.")
    ]


@mcp.prompt(title="View User Profile & Stats")
def user_profile() -> list[base.Message]:
    """View your complete Steam profile and gaming statistics."""
    return [
        base.UserMessage("Can you show me my Steam profile and gaming statistics?"),
        base.AssistantMessage("I'll display your complete Steam profile including gaming statistics, library overview, and account details."),
        base.UserMessage(
            EmbeddedResource(
                uri="library://users/default",
                name="user_profile",
                description="Your complete Steam profile and statistics",
                mimeType="application/json"
            )
        ),
        base.AssistantMessage("Here's your profile! You can also access library://users/default/games for your complete game list or library://users/default/stats for detailed gaming statistics.")
    ]
