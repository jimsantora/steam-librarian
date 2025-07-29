"""Core library prompts for Steam Librarian MCP Server"""

import logging
from typing import Any

from mcp_server.server import mcp

logger = logging.getLogger(__name__)


@mcp.prompt()
async def rediscover_library(mood: str = "any", time_available: str = "any") -> str:
    """Find something you already own to play - intelligent library rediscovery"""
    
    return f"""I want to find something to play from my Steam library. 

My current mood: {mood}
Time available: {time_available}

Please help me rediscover something perfect from my library by:
1. First checking what I've been playing recently to avoid repetition (use library://activity/recent resource)
2. Then using the get_recommendations tool with context about my mood and available time
3. Focus on games I already own but might have forgotten about or haven't played in a while

Make your recommendations personal and consider both my mood and time constraints."""


@mcp.prompt()
async def gaming_therapy(feeling: str, energy_level: str = "medium") -> str:
    """Get gaming recommendations based on how you're feeling"""
    
    # Map feelings to gaming moods
    feeling_to_mood = {
        "stressed": "relaxing", "anxious": "calming", "bored": "engaging", 
        "sad": "uplifting", "angry": "cathartic", "happy": "social", "tired": "casual"
    }
    
    mood = "any"
    for key, value in feeling_to_mood.items():
        if key in feeling.lower():
            mood = value
            break
    
    return f"""I'm feeling {feeling} with {energy_level} energy. What should I play?

I understand you're feeling {feeling}. Let me find games that might help by:
1. Using the search_games tool to find {mood} games suitable for {energy_level} energy
2. Recommending games that match your emotional state and energy level
3. Suggesting games that can help you feel better or match your current mood

Please provide personalized recommendations that consider both my emotional state and energy level."""


@mcp.prompt()  
async def weekend_planner(available_hours: str, solo_or_social: str = "both") -> str:
    """Plan your weekend gaming sessions"""
    
    social_planning = ""
    if solo_or_social in ["social", "both"]:
        social_planning = """
4. Check multiplayer games using get_friends_data tool to see what games you and your friends could enjoy together"""
    
    return f"""I have {available_hours} hours for gaming this weekend. Preference: {solo_or_social}.

Help me plan an awesome gaming weekend by:
1. First checking my library stats using get_library_stats tool to understand my preferences
2. Suggesting a mix of games that fit within my {available_hours} time budget
3. Balancing different types of games (quick sessions vs longer experiences){social_planning}

Create a structured weekend gaming plan that maximizes enjoyment within my time constraints."""


@mcp.prompt()
async def backlog_therapist(commitment_level: str = "medium") -> str:
    """Get help tackling your backlog without overwhelm"""
    
    # Map commitment to approach
    commitment_approaches = {
        "light": "short games (under 10 hours) that you can finish quickly", 
        "medium": "moderately-sized games (10-50 hours) that offer good value",
        "deep": "longer games (10+ hours) that you can really sink into"
    }
    
    approach = commitment_approaches.get(commitment_level, "games that match your commitment level")
    
    return f"""Help me tackle my backlog with {commitment_level} commitment level.

Let's tackle that backlog together! Please help by:
1. Using the filter_games tool with the "hidden_gems" preset to find neglected games
2. Focusing on {approach}
3. Prioritizing games based on my preferences and the time I want to invest
4. Providing a manageable plan that won't overwhelm me

Give me actionable suggestions for which games to tackle first based on my {commitment_level} commitment level."""
