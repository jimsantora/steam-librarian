"""Enhanced MCP prompts with proper annotations and argument descriptions for full specification compliance"""

from mcp.server.fastmcp.prompts import base
from mcp.types import (
    Annotations,
    ResourceLink,
    TextContent,
)

from .server import mcp


@mcp.prompt(name="family_games", title="Find Family-Friendly Games", description="Get age-appropriate game recommendations with ESRB/PEGI filtering for safe family gaming")
def family_games(child_age: int = 8) -> list[base.Message]:
    """Get age-appropriate game recommendations for family gaming.

    Args:
        child_age: Age of the child in years (used for ESRB/PEGI rating filtering, default: 8)
    """
    return [base.UserMessage(TextContent(type="text", text=f"I need games suitable for my {child_age}-year-old child. What do you recommend?", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text=f"I'll find age-appropriate games for a {child_age}-year-old using our family-safe filtering system with ESRB and PEGI ratings.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(TextContent(type="text", text=f"Use recommend_games('family', '{{\"age\": {child_age}}}') to get games rated for this age group.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="quick_session", title="Quick Gaming Session", description="Find games perfect for short gaming sessions based on available time")
def quick_session(minutes_available: int = 30) -> list[base.Message]:
    """Find games perfect for short gaming sessions.

    Args:
        minutes_available: Available gaming time in minutes (default: 30)
    """
    return [base.UserMessage(TextContent(type="text", text=f"I only have {minutes_available} minutes to play. What games would work well for a quick session?", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text=f"Let me find games that are perfect for {minutes_available}-minute sessions using smart tag analysis.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(TextContent(type="text", text=f"Use recommend_games('quick_session', '{{\"minutes\": {minutes_available}}}') to get games suitable for short play sessions.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="unplayed_gems", title="Discover Unplayed Games", description="Find highly-rated games in your library that you haven't played yet with embedded resource data")
def unplayed_gems() -> list[base.Message]:
    """Find highly-rated games in your library that you haven't played yet."""
    return [base.UserMessage(TextContent(type="text", text="I have so many games in my library but I don't know what to play. Help me find some good ones I haven't tried yet.", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text="I'll help you discover hidden gems in your library - games you own but haven't played yet. Let me show you what's available.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(ResourceLink(type="resource_link", uri="library://games/unplayed", name="unplayed_games", description="Your highly-rated unplayed games with Metacritic scores ≥75", mimeType="application/json")), base.AssistantMessage(TextContent(type="text", text="Based on your unplayed games above, I recommend using recommend_games('unplayed_gems') to get personalized suggestions from these titles.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="similar_games", title="Games Similar To Favorite", description="Find games similar to one you already love by analyzing genres, developers, and gameplay features")
def similar_games(game_name: str = "Portal") -> list[base.Message]:
    """Find games similar to one you already love.

    Args:
        game_name: Name of the game you enjoyed (default: Portal)
    """
    return [base.UserMessage(TextContent(type="text", text=f"I really enjoyed {game_name}. Can you recommend similar games from my library?", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text=f"I'll find games similar to {game_name} by analyzing genres, developers, and gameplay features.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(TextContent(type="text", text=f"Use recommend_games('similar_to', '{{\"game_name\": \"{game_name}\"}}') to find games with similar characteristics.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="natural_search", title="Natural Language Game Search", description="Search your library using natural language descriptions with AI interpretation")
def natural_search(query: str = "relaxing puzzle games") -> list[base.Message]:
    """Search your library using natural language descriptions.

    Args:
        query: Natural language description of games you're looking for (default: "relaxing puzzle games")
    """
    return [base.UserMessage(TextContent(type="text", text=f"I'm looking for {query}. Can you search my library?", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text=f"I'll search your library for '{query}' using AI to interpret your request and find matching games.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(TextContent(type="text", text=f"Use smart_search('{query}') to find games matching this description.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="gaming_insights", title="Analyze Gaming Patterns", description="Get AI-powered insights about your gaming habits and preferences with embedded library data")
def gaming_insights(analysis_type: str = "patterns") -> list[base.Message]:
    """Get AI-powered insights about your gaming habits and preferences.

    Args:
        analysis_type: Type of analysis to perform - patterns, value, social, genres, etc. (default: "patterns")
    """
    return [base.UserMessage(TextContent(type="text", text="I'm curious about my gaming habits. Can you analyze my library and tell me what patterns you see?", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text="I'll analyze your gaming patterns and provide insights about your preferences, habits, and gaming personality. Let me start by looking at your library overview.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(ResourceLink(type="resource_link", uri="library://overview", name="library_overview", description="Your complete library overview with statistics, top genres, and gaming insights", mimeType="application/json")), base.AssistantMessage(TextContent(type="text", text=f"Based on your library data above, use get_library_insights('{analysis_type}') to get AI-powered analysis of your gaming patterns.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="mood_games", title="Mood-Based Game Selection", description="Get game recommendations based on your current mood by analyzing genres, tags, and gameplay styles")
def mood_games(mood: str = "relaxing") -> list[base.Message]:
    """Get game recommendations based on your current mood.

    Args:
        mood: Your current emotional state - relaxing, energetic, challenging, social, etc. (default: "relaxing")
    """
    return [base.UserMessage(TextContent(type="text", text=f"I'm feeling {mood} today. What games would match this mood?", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text=f"I'll recommend games that match a {mood} mood by analyzing genres, tags, and gameplay styles.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(TextContent(type="text", text=f"Use recommend_games('mood_based', '{{\"mood\": \"{mood}\"}}') to get games matching this emotional state.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="abandoned_games", title="Find Abandoned Games", description="Rediscover games you started but never finished - perfect candidates for revisiting")
def abandoned_games() -> list[base.Message]:
    """Rediscover games you started but never finished."""
    return [base.UserMessage(TextContent(type="text", text="I have a habit of starting games but not finishing them. Can you help me find games I should revisit?", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text="I'll find games in your library that you started playing but haven't touched in a while - perfect candidates for revisiting.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(TextContent(type="text", text="Use recommend_games('abandoned') to find games you have some playtime in but haven't completed or played recently.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="explore_genre", title="Explore Games by Genre", description="Explore all games in your library by a specific genre with embedded game data")
def explore_genre(genre_name: str = "Puzzle") -> list[base.Message]:
    """Explore all games in your library by a specific genre.

    Args:
        genre_name: Genre to explore - Action, Adventure, RPG, Strategy, Puzzle, etc. (default: "Puzzle")
    """
    return [base.UserMessage(TextContent(type="text", text=f"I'm interested in {genre_name} games. Can you show me what I have in my library?", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text=f"I'll show you all the {genre_name} games in your library with their details and playtime information.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(ResourceLink(type="resource_link", uri=f"library://genres/{genre_name}/games", name=f"{genre_name.lower()}_games", description=f"All {genre_name} games in your library with developers and review scores", mimeType="application/json")), base.AssistantMessage(TextContent(type="text", text=f"Here are your {genre_name} games! You can also use smart_search('{genre_name.lower()} games') to find specific ones based on other criteria.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="user_profile", title="View User Profile & Stats", description="View your complete Steam profile and gaming statistics with embedded profile data")
def user_profile() -> list[base.Message]:
    """View your complete Steam profile and gaming statistics."""
    return [base.UserMessage(TextContent(type="text", text="Can you show me my Steam profile and gaming statistics?", annotations=Annotations(audience=["user"], priority=0.9))), base.AssistantMessage(TextContent(type="text", text="I'll display your complete Steam profile including gaming statistics, library overview, and account details.", annotations=Annotations(audience=["assistant"], priority=0.8))), base.UserMessage(ResourceLink(type="resource_link", uri="library://users/default", name="user_profile", description="Your complete Steam profile with persona, level, XP, location, and game count", mimeType="application/json")), base.AssistantMessage(TextContent(type="text", text="Here's your profile! You can also access library://users/default/games for your complete game list or library://users/default/stats for detailed gaming statistics.", annotations=Annotations(audience=["assistant"], priority=0.7)))]


@mcp.prompt(name="elicitation_guide", title="Understanding Preference Elicitation", description="Explains how preference elicitation works in Steam Librarian tools with interactive examples")
def elicitation_guide(tool_name: str = None) -> list[base.Message]:
    """Generate guide for understanding elicitation mechanisms.

    Args:
        tool_name: Specific tool to explain elicitation for (default: general guide)
    """

    if tool_name == "find_games_with_preferences":
        return [
            base.UserMessage(TextContent(
                type="text",
                text="How does the preference elicitation work in find_games_with_preferences?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )),
            base.AssistantMessage(TextContent(
                type="text",
                text="""# Elicitation Guide: find_games_with_preferences

## Overview
This tool uses multi-step preference gathering to understand exactly what you want.

## Elicitation Flow
1. You specify an initial genre (e.g., "RPG")
2. Tool asks about sub-preferences (e.g., single vs multiplayer)
3. Tool asks about time commitment preferences
4. Tool asks about difficulty preferences
5. Returns personalized recommendations

## Example Session
```
User: find_games_with_preferences(initial_genre="RPG")
Tool: "Do you prefer single-player story-driven RPGs or multiplayer RPGs?"
User: "Single-player with good story"
Tool: "Do you prefer shorter experiences (20-40 hours) or epic adventures (60+ hours)?"
User: "Shorter experiences"
Tool: "Challenge level preference: Casual, Moderate, or Hardcore?"
User: "Moderate"
Tool: [Returns 5-10 games matching all preferences]
```

## Tips
- Answer preferences honestly for best results
- You can skip questions by saying "no preference"
- The tool remembers preferences within the session""",
                annotations=Annotations(audience=["user"], priority=0.9)
            ))
        ]
    elif tool_name == "recommend_games":
        return [
            base.UserMessage(TextContent(
                type="text",
                text="How does elicitation work in recommend_games?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )),
            base.AssistantMessage(TextContent(
                type="text",
                text="""# Elicitation Guide: recommend_games

## Overview
Uses context-aware elicitation for refinement and clarification.

## Elicitation Flow
1. Analyzes initial context
2. May ask clarifying questions if context is ambiguous
3. Returns recommendations with explanation

## Example Session
```
User: recommend_games(context="mood:relaxing")
Tool: "For relaxing games, do you prefer: puzzle/strategy (mental relaxation) or exploration/building (creative relaxation)?"
User: "Creative relaxation"
Tool: [Returns building/crafting/exploration games]
```

## When Elicitation Happens
- **Family context**: Always asks for child's age if not provided
- **Ambiguous contexts**: Clarifies what you mean
- **Invalid contexts**: Helps you choose the right context
- **Missing parameters**: Asks for critical missing information

## Tips
- Provide context and parameters upfront to minimize questions
- Be specific with contexts like "mood:relaxing" vs just "relaxing"
- Use get_tool_help("recommend_games") to see all valid contexts""",
                annotations=Annotations(audience=["user"], priority=0.9)
            ))
        ]
    else:
        return [
            base.UserMessage(TextContent(
                type="text",
                text="What is preference elicitation and how does it work?",
                annotations=Annotations(audience=["user"], priority=0.9)
            )),
            base.AssistantMessage(TextContent(
                type="text",
                text="""# Preference Elicitation in Steam Librarian

## What is Elicitation?
Elicitation is an interactive process where tools ask follow-up questions to better understand your preferences and provide more accurate recommendations.

## Tools with Elicitation
1. **find_games_with_preferences**: Multi-step preference gathering
2. **recommend_games**: Context-aware clarification
3. **find_family_games**: Age-appropriate content verification

## How It Works
1. You provide initial parameters
2. Tool analyzes and identifies ambiguities
3. Tool asks clarifying questions
4. You provide additional preferences
5. Tool returns personalized results

## Benefits
- More accurate recommendations
- Discovers preferences you might not have considered
- Reduces trial and error
- Saves time finding the right games

## Example Flow
```
User: recommend_games("family")
Tool: "I need some information to find the best family-friendly games:
       - Child's age (for rating appropriateness)
       - Number of players
       - Any content concerns?"
User: [Provides age: 8, players: 2, concerns: violence]
Tool: [Returns age-appropriate cooperative games without violence]
```

## Tips for Better Elicitation
- Be honest about your preferences
- Provide as much context upfront as possible
- You can always say "no preference" to skip questions
- Use get_tool_help() to understand what information tools need

Use elicitation_guide(tool_name="[specific_tool]") for detailed examples.""",
                annotations=Annotations(audience=["user"], priority=0.9)
            ))
        ]


@mcp.prompt(name="tool_usage_patterns", title="Common Tool Usage Patterns", description="Examples of effective tool usage patterns and workflows for different gaming scenarios")
def tool_usage_patterns(scenario: str = "discovery") -> list[base.Message]:
    """Show common usage patterns for different gaming scenarios.

    Args:
        scenario: Usage scenario - discovery, analysis, family, quick_play, etc.
    """

    patterns = {
        "discovery": {
            "title": "Game Discovery Workflow",
            "description": "Best practices for discovering new games to play",
            "steps": [
                "1. Start with get_library_insights('patterns') to understand your preferences",
                "2. Use recommend_games('unplayed_gems') to find owned but unplayed games",
                "3. Try smart_search() with natural language for specific moods",
                "4. Use recommend_games('abandoned') to revisit started games"
            ],
            "example": "get_library_insights('patterns') → recommend_games('unplayed_gems') → smart_search('relaxing puzzle games')"
        },
        "family": {
            "title": "Family Gaming Workflow",
            "description": "Finding appropriate games for family play sessions",
            "steps": [
                "1. Use find_family_games(child_age=X) for age-appropriate filtering",
                "2. Try recommend_games('family') with elicitation for detailed preferences",
                "3. Use smart_search() with filters like 'coop family games'",
                "4. Check individual games with library://games/{id} resources"
            ],
            "example": "find_family_games(8) → recommend_games('family') → smart_search('cooperative games', filters='no violence')"
        },
        "quick_play": {
            "title": "Quick Session Workflow",
            "description": "Finding games for limited time availability",
            "steps": [
                "1. Use find_quick_session_games(session_length='short/medium/long')",
                "2. Try recommend_games('quick_session') with time parameters",
                "3. Use smart_search() with 'arcade' or 'casual' filters",
                "4. Sort by recent playtime to find familiar quick games"
            ],
            "example": "find_quick_session_games('short') → smart_search('arcade games', sort_by='recent')"
        }
    }

    if scenario in patterns:
        pattern = patterns[scenario]
        content = f"""# {pattern['title']}

## Description
{pattern['description']}

## Recommended Steps
{chr(10).join(pattern['steps'])}

## Example Workflow
{pattern['example']}

## Tips
- Each step builds on the previous one
- Use get_tool_help() if you need parameter guidance
- Tools work better when you provide context upfront
- Combine structured and natural language approaches"""
    else:
        available = ', '.join(patterns.keys())
        content = f"""# Tool Usage Patterns

Available scenarios: {available}

## General Principles
1. **Start broad, then narrow**: Use insights before specific searches
2. **Combine tools**: Each tool has different strengths
3. **Use natural language**: Most tools accept text descriptions
4. **Leverage elicitation**: Let tools ask questions for better results
5. **Check resources**: Use library:// resources for detailed data

Use tool_usage_patterns(scenario='[name]') for specific workflows."""

    return [
        base.UserMessage(TextContent(
            type="text",
            text=f"Show me effective usage patterns for {scenario} scenarios",
            annotations=Annotations(audience=["user"], priority=0.9)
        )),
        base.AssistantMessage(TextContent(
            type="text",
            text=content,
            annotations=Annotations(audience=["user"], priority=0.9)
        ))
    ]
