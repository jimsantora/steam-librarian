"""Engaging MCP prompts that showcase Steam Librarian's AI-powered features"""

from mcp.server.fastmcp.prompts import base

from .server import mcp


@mcp.prompt(title="🧠 AI Smart Search Showcase")
def smart_search_demo(query: str = "something like Portal but family-friendly") -> str:
    """Demonstrate natural language search with AI sampling."""
    return f"""Use smart_search to find games with this natural language query: "{query}"

This showcases our AI sampling feature that interprets human language and converts it to structured game filters. Try queries like:
- "couch co-op games for date night"
- "unplayed indie gems that won't make me cry"
- "quick session puzzle games for my lunch break"
- "family games that won't bore the adults to tears"

The AI will automatically understand context, mood, and requirements!"""


@mcp.prompt(title="🎯 Intelligent Recommendations")
def recommendation_showcase() -> list[base.Message]:
    """Show off context-aware recommendations with elicitation."""
    return [base.UserMessage("I need game recommendations but I'm not sure what I want"), base.AssistantMessage("Perfect! Let me use our recommend_games tool. I can help with several contexts: family games (specify age), quick sessions (how many minutes?), games similar to ones you love, mood-based picks, or unplayed gems sitting in your library. What sounds interesting?"), base.UserMessage("Something for my 8-year-old nephew who visits on weekends"), base.AssistantMessage("Great choice! I'll use: recommend_games('family', '{\"age\": 8, \"players\": 2}') - this leverages our ESRB/PEGI rating system and family-friendly category filtering. If you don't provide the age, our elicitation system will ask for it automatically!"), base.UserMessage("What about finding games I've abandoned?"), base.AssistantMessage("Ah, the digital graveyard investigation! Use recommend_games('abandoned') - this analyzes your library for games you started but never finished. It's like archaeology, but for your gaming guilt!")]


@mcp.prompt(title="📊 Deep Library Analytics")
def library_insights_demo(analysis_type: str = "patterns") -> str:
    """Showcase comprehensive library analytics with AI interpretation."""
    return f"""Analyze my gaming habits with get_library_insights('{analysis_type}').

Our analytics engine provides several fascinating insights:

🔍 **patterns**: Discover your gaming DNA - favorite genres, developers you're loyal to, and when you actually play vs. buy games
📈 **value**: Calculate cost-per-hour for your games (prepare for buyer's remorse or pleasant surprises!)
🕳️ **gaps**: Find missing gems in your collection based on your preferences
👥 **social**: Compare your library to friends (when friends data is available)
🏆 **achievements**: Track your completion obsession (or lack thereof)
📊 **trends**: See how your gaming tastes evolved over time

The AI will interpret patterns and suggest what type of gamer you are - might be eye-opening!"""


@mcp.prompt(title="🎮 Session Planning Wizard")
def gaming_session_planner(time_available: str = "45 minutes", energy_level: str = "mentally exhausted") -> str:
    """Plan perfect gaming sessions using smart search and recommendations."""
    return f"""I have {time_available} and I'm feeling {energy_level}. Plan my gaming session!

Use our tools together for the perfect experience:
1. **smart_search** with filters like '{{"playtime": "any", "tags": ["Relaxing", "Casual"]}}' for low-energy days
2. **recommend_games** with 'quick_session' context and '{{"minutes": 45}}' parameters
3. **get_library_insights** to see your 'patterns' and avoid games that might stress you out

For {energy_level} moods, try:
- Puzzle games (engage brain without overwhelming it)
- Simulation games (zen-like, no pressure)
- Casual games (designed for quick satisfaction)
- Avoid: Competitive multiplayer, Dark Souls, anything requiring quick reflexes!"""


@mcp.prompt(title="👨‍👩‍👧‍👦 Family Gaming Coordinator")
def family_gaming_helper() -> list[base.Message]:
    """Demonstrate family-appropriate game finding with age filtering."""
    return [base.UserMessage("Help me find games for family game night - kids are 6, 10, and 14"), base.AssistantMessage("Multi-age family gaming! This is where our ESRB/PEGI filtering shines. I'll find games rated for your youngest (6-year-old) that won't bore the teenagers. Let me use smart_search with family-specific filters."), base.UserMessage("What about local multiplayer options?"), base.AssistantMessage('Perfect! Use smart_search(\'family multiplayer\', \'{"categories": ["Local Co-op", "Shared/Split Screen"], "playtime": "any"}\') - this finds games where everyone can play together on one screen. No fighting over who gets the good controller!'), base.UserMessage("Any way to avoid games with violence?"), base.AssistantMessage('Absolutely! Our system tracks ESRB descriptors. Use recommend_games(\'family\', \'{"age": 6, "content_concerns": ["violence", "scary"]}\') and our elicitation system will help you specify exactly what to avoid. Peace, love, and pizza parties!')]


@mcp.prompt(title="🕵️ Unplayed Game Detective")
def unplayed_gems_finder() -> str:
    """Find and analyze the games gathering dust in your library."""
    return """Time for some digital archaeology! Let's excavate your unplayed games:

**Step 1**: Use smart_search('unplayed gems', '{"playtime": "unplayed", "sort_by": "metacritic"}') to find highly-rated games you've never touched.

**Step 2**: Try recommend_games('unplayed_gems') for curated recommendations based on your play history.

**Step 3**: Get philosophical with get_library_insights('value') to see how much money is sitting unplayed in your library (warning: may cause existential crisis).

Fun fact: Our AI can analyze your playing patterns and predict which unplayed games you're most likely to actually enjoy, versus the ones you bought during a sale and will never touch. It's like having a crystal ball for your gaming backlog!"""


@mcp.prompt(title="🎲 Mood-Based Game Picker")
def mood_gaming() -> str:
    """Match games to your current emotional state."""
    return """What's your vibe today? Our mood-based system has you covered:

😌 **Feeling chill?** recommend_games('mood_based', '{"mood": "relaxing"}')
⚡ **Need energy?** recommend_games('mood_based', '{"mood": "energetic"}')
🏆 **Competitive spirit?** recommend_games('mood_based', '{"mood": "competitive"}')
👥 **Social but tired?** recommend_games('mood_based', '{"mood": "social"}')
🎨 **Creative itch?** recommend_games('mood_based', '{"mood": "creative"}')
📖 **Story time?** recommend_games('mood_based', '{"mood": "story"}')

Our AI analyzes your library's genres, tags, and your play patterns to suggest games that match your emotional needs. It's like having a therapist who really understands your Steam addiction!"""


@mcp.prompt(title="🔍 Library Resource Explorer")
def resource_showcase() -> str:
    """Explore all the rich data available through our resources."""
    return """Dive deep into your library data with our comprehensive resources:

📋 **Library Overview**: library://overview (your gaming life at a glance)
👤 **User Profile**: library://users/default (your Steam identity and stats)
🎮 **Game Details**: library://games/{app_id} (everything about any game)
🖥️ **Platform Games**: library://games/platform/windows (or mac/linux/vr)
👫 **Multiplayer**: library://games/multiplayer/coop (or pvp/local/online)
💎 **Unplayed Gems**: library://games/unplayed (your digital regrets waiting to be redeemed)
🎯 **Genre Deep-Dive**: library://genres/{genre_name}/games
🏷️ **Tag Explorer**: library://tags/{tag_name} (community wisdom in action)

Each resource provides rich JSON data with metadata, relationships, and insights. It's like having a data scientist for your gaming habits!"""
