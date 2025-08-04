"""
Simple text prompts with usage examples for the tools-only MCP server.

These prompts provide clear examples of how to use each tool effectively,
replacing the complex prompt templates from the full MCP server.
"""

# Tool usage examples organized by category
PROMPTS = {
    # Search & Discovery
    "search_games_example": """
Example: search_games(query='Portal', filters='{"min_rating": 85}')
Searches for games matching 'Portal' with minimum rating of 85.
    """,

    "search_rpg_games": """
Example: search_games(query='RPG games rated above 80')
Natural language search for highly-rated RPG games in your library.
    """,

    "get_game_info": """
Example: get_game_details(game_id=440, include_reviews=True)
Get complete information about Team Fortress 2 including user reviews.
    """,

    "find_similar": """
Example: find_similar_games(game_name='Portal 2', similarity_factors=['genre', 'developer'])
Find games similar to Portal 2 based on genre and developer.
    """,

    # Library Management
    "library_overview": """
Example: get_library_overview(include_stats=True)
Get comprehensive overview of your Steam library with detailed statistics.
    """,

    "user_profile": """
Example: get_user_profile()
List all users in the database, or get_user_profile(user_id='76561198000000000') for specific user.
    """,

    "user_games_by_playtime": """
Example: get_user_games(sort_by='playtime', filter_played=True, limit=20)
Get your top 20 most-played games.
    """,

    "gaming_stats": """
Example: get_user_stats(time_range='recent')
Get detailed gaming statistics focusing on recent activity.
    """,

    # Genre & Category Discovery
    "explore_genres": """
Example: get_genres(include_counts=True)
See all genres in your library with game counts, then use get_games_by_genre(genre_name='Action').
    """,

    "action_games": """
Example: get_games_by_genre(genre_name='Action', sort_by='rating', limit=15)
Get top 15 highest-rated Action games in your library.
    """,

    "multiplayer_discovery": """
Example: get_categories(category_type='multiplayer')
First discover multiplayer categories, then get_games_by_category(category='Co-op').
    """,

    "coop_games": """
Example: get_games_by_category(category='Co-op')
Find all cooperative multiplayer games in your library.
    """,

    # Recommendations & Analytics
    "family_gaming": """
Example: find_family_games(child_age=10, content_preferences=['no violence', 'educational'])
Find age-appropriate games for a 10-year-old with content preferences.
    """,

    "quick_session": """
Example: find_quick_games(session_length='30min', genre_preference='puzzle')
Find puzzle games perfect for a 30-minute gaming session.
    """,

    "unplayed_gems": """
Example: get_unplayed_games(sort_by='rating', include_reasons=True)
Discover highly-rated games you own but haven't played yet.
    """,

    "gaming_patterns": """
Example: analyze_gaming_patterns(analysis_type='genre_trends', time_range='6months')
Analyze your gaming preferences and patterns over the last 6 months.
    """,

    # Platform & Features
    "vr_games": """
Example: get_vr_games(vr_type='room_scale')
Find VR games that support room-scale experiences.
    """,

    "steam_deck": """
Example: get_platform_games(platform='Steam Deck')
Find games verified or playable on Steam Deck.
    """,

    "controller_games": """
Example: get_games_by_category(category='Controller Support')
Find games with full controller support.
    """,

    # Advanced Workflows
    "discovery_workflow": """
Workflow: Discover new games to play
1. get_unplayed_games(sort_by='rating') - Find unplayed highly-rated games
2. get_games_by_genre(genre_name='Indie') - Explore indie games
3. find_similar_games(game_name='favorite_game') - Find similar to favorites
    """,

    "family_workflow": """
Workflow: Family gaming session
1. get_categories(category_type='multiplayer') - See multiplayer options
2. find_family_games(child_age=8) - Age-appropriate games
3. get_games_by_category(category='Local Co-op') - Local multiplayer games
    """,

    "achievement_hunting": """
Workflow: Achievement hunting
1. get_user_stats() - See achievement completion rates
2. get_user_games(sort_by='recent', filter_played=True) - Recent games
3. analyze_gaming_patterns(analysis_type='achievements') - Achievement patterns
    """,

    # Error Recovery Examples
    "missing_game_id": """
When you get "Missing game_id" error:
1. search_games(query='game name') to find the game_id
2. get_user_games() to list all games with IDs
3. Then use the game_id in your original tool call
    """,

    "missing_genre": """
When you get "Genre not found" error:
1. get_genres() to see all available genres
2. Check spelling and try again
3. Use genre name exactly as shown in the list
    """,

    "missing_user": """
When you get "User not found" error:
1. get_user_profile() to see all available users
2. Use the correct steam_id from the list
3. Or set DEFAULT_USER in environment variables
    """
}


def get_prompt_by_name(name: str) -> str:
    """Get a specific prompt by name."""
    return PROMPTS.get(name, f"Prompt '{name}' not found. Available prompts: {', '.join(PROMPTS.keys())}")


def get_all_prompts() -> dict:
    """Get all available prompts."""
    return PROMPTS


def get_prompts_by_category(category: str) -> dict:
    """Get prompts filtered by category keywords."""
    category_lower = category.lower()
    return {
        name: prompt for name, prompt in PROMPTS.items()
        if category_lower in name.lower() or category_lower in prompt.lower()
    }
