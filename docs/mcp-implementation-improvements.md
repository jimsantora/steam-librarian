# MCP Implementation Improvements

This document outlines key areas that are **missing** or could be **improved** in the Steam Librarian MCP implementation while staying in scope.

## Missing Critical Components

### 1. **Error Handling & Resilience**
- No error handling patterns for database failures, missing games, or invalid user IDs
- Missing graceful degradation when friends data is unavailable
- No timeout handling for long-running queries

### 2. **User Context Management**
- No multi-user session handling - the code assumes a single current user
- Missing user identification/authentication flow
- No fallback when `user_steam_id` is not provided

### 3. **Performance Considerations**
- No caching strategy implementation (mentioned but not coded)
- Missing database connection pooling
- No query optimization examples (eager loading, indexing)

### 4. **Data Validation**
- Missing input validation for tool parameters
- No sanitization of search queries
- Missing validation for Steam IDs, app IDs

## Improvements Within Scope

### 1. **Enhanced Search Intelligence**
```python
# Add more sophisticated intent parsing
def parse_search_intent(query: str):
    """Could include mood detection, time-based queries, difficulty preferences"""
    # "easy games", "hard games", "relaxing", "challenging"
    # "short games", "long games", "quick session"
```

### 2. **Better Recommendation Context**
```python
# Add context-aware recommendations
async def get_recommendations_handler(user_steam_id: str, context: dict = None):
    """Include time of day, recent activity, friend activity in recommendations"""
```

### 3. **Richer Friend Analysis**
```python
# Add friend compatibility scoring
async def get_friend_compatibility_score(user_id: str, friend_id: str):
    """Calculate compatibility based on shared genres, playtime patterns"""
```

### 4. **Time-Aware Features**
```python
# Add temporal analysis
def analyze_gaming_schedule(user_games):
    """Identify when user typically plays certain types of games"""
```

### 5. **Missing Helper Functions**
The implementation references several functions that aren't defined:
- `calculate_last_played(user_game)`
- `has_multiplayer_categories(game)`
- `format_game_result(g)`
- `calculate_completion_tendency(user_games)`
- `get_multiplayer_types(game)`

### 6. **Resource Template Expansion**
```python
# Add more granular resources
"library://genres/{genre_name}"  # Games by genre
"library://friends/{friend_id}/common"  # Common games with specific friend
"library://insights/neglected"  # Neglected gems resource
```

### 7. **Better Prompt Workflows**
```python
# Add conditional tool chaining in prompts
async def rediscover_library_prompt(arguments: dict):
    """Chain tools based on user mood and available time"""
    # If mood="relaxing" -> filter by specific categories
    # If time="30min" -> filter by average session length
```

### 8. **Enhanced Library Stats**
```python
def calculate_advanced_stats(user_games):
    return {
        "gaming_velocity": calculate_games_per_month(),
        "genre_evolution": track_genre_preferences_over_time(),
        "completion_patterns": analyze_what_games_get_finished(),
        "social_influence": measure_friend_impact_on_purchases()
    }
```

### 9. **Contextual Game Details**
```python
async def get_game_details_with_context(app_id: str, context: str = None):
    """Provide different details based on context (discovery, multiplayer, etc.)"""
```

### 10. **Smart Filtering**
```python
# Add intelligent filter combinations
async def filter_games_smart(user_id: str, intent: str):
    """Apply common filter combinations based on user intent"""
    # "comfort food" -> high playtime + positive reviews + favorite genres
    # "discovery" -> low playtime + good reviews + different genres
```

## Production-Ready Enhancements

### Error Handling Pattern
```python
from functools import wraps
import logging

def handle_mcp_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except DatabaseError as e:
            logging.error(f"Database error in {func.__name__}: {e}")
            return create_error_response("DATABASE_ERROR", "Unable to access library data")
        except ValidationError as e:
            logging.warning(f"Validation error in {func.__name__}: {e}")
            return create_error_response("INVALID_INPUT", str(e))
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {e}")
            return create_error_response("INTERNAL_ERROR", "An unexpected error occurred")
    return wrapper
```

### User Context Resolution
```python
async def resolve_user_context(user_steam_id: Optional[str] = None) -> dict:
    """Resolve user context with fallbacks"""
    if user_steam_id:
        # Validate and return specific user
        user = await get_user_by_id(user_steam_id)
        if user:
            return {"user": user, "source": "provided"}
    
    # Try environment fallback
    default_user = os.getenv("DEFAULT_STEAM_ID")
    if default_user:
        user = await get_user_by_id(default_user)
        if user:
            return {"user": user, "source": "default"}
    
    # Try single user fallback
    users = await get_all_users()
    if len(users) == 1:
        return {"user": users[0], "source": "auto_single"}
    elif len(users) > 1:
        return {"error": "MULTIPLE_USERS", "users": users}
    else:
        return {"error": "NO_USERS", "message": "No users found in database"}
```

### Caching Implementation
```python
from functools import lru_cache
import asyncio
from datetime import datetime, timedelta

class AsyncTTLCache:
    def __init__(self, ttl_seconds=3600):
        self.cache = {}
        self.ttl = ttl_seconds
    
    async def get_or_set(self, key: str, factory_func):
        now = datetime.now()
        
        if key in self.cache:
            value, timestamp = self.cache[key]
            if now - timestamp < timedelta(seconds=self.ttl):
                return value
        
        # Cache miss or expired
        value = await factory_func()
        self.cache[key] = (value, now)
        return value

# Usage
library_cache = AsyncTTLCache(ttl_seconds=1800)  # 30 minutes

async def get_library_stats_cached(user_steam_id: str):
    return await library_cache.get_or_set(
        f"library_stats_{user_steam_id}",
        lambda: get_library_stats_handler(user_steam_id)
    )
```

### Input Validation
```python
from pydantic import BaseModel, validator
from typing import Optional

class SearchGamesInput(BaseModel):
    query: str
    user_steam_id: Optional[str] = None
    
    @validator('query')
    def query_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        if len(v) > 200:
            raise ValueError('Query too long (max 200 characters)')
        return v.strip()
    
    @validator('user_steam_id')
    def validate_steam_id(cls, v):
        if v and not v.isdigit():
            raise ValueError('Steam ID must be numeric')
        return v

class FilterGamesInput(BaseModel):
    user_steam_id: Optional[str] = None
    playtime_min: Optional[float] = None
    playtime_max: Optional[float] = None
    
    @validator('playtime_min', 'playtime_max')
    def validate_playtime(cls, v):
        if v is not None and v < 0:
            raise ValueError('Playtime cannot be negative')
        return v
```

### Advanced Context-Aware Recommendations
```python
async def get_contextual_recommendations(
    user_steam_id: str, 
    context: dict = None
) -> dict:
    """Generate recommendations based on rich context"""
    
    base_patterns = await analyze_user_patterns(user_steam_id)
    
    recommendations = {
        "primary": [],
        "contextual": [],
        "discovery": [],
        "social": []
    }
    
    # Time-based context
    if context and "time_available" in context:
        time_mins = parse_time_to_minutes(context["time_available"])
        if time_mins <= 30:
            # Quick session games
            recommendations["contextual"].extend(
                await find_quick_session_games(user_steam_id, time_mins)
            )
        elif time_mins >= 120:
            # Deep dive games
            recommendations["contextual"].extend(
                await find_immersive_games(user_steam_id)
            )
    
    # Mood-based context
    if context and "mood" in context:
        mood = context["mood"].lower()
        if mood in ["relaxing", "chill", "casual"]:
            recommendations["contextual"].extend(
                await find_relaxing_games(user_steam_id)
            )
        elif mood in ["challenging", "competitive", "difficult"]:
            recommendations["contextual"].extend(
                await find_challenging_games(user_steam_id)
            )
    
    # Social context
    if context and "with_friends" in context:
        recommendations["social"].extend(
            await find_friend_compatible_games(user_steam_id)
        )
    
    return recommendations
```

### Smart Resource Templates
```python
@server.list_resources()
async def handle_list_resources():
    return [
        # Core resources
        Resource(uri="library://overview", ...),
        Resource(uri="library://games/{app_id}", ...),
        Resource(uri="library://activity/recent", ...),
        
        # Extended resources
        Resource(
            uri="library://genres/{genre_name}",
            name="Games by Genre",
            description="All games in your library for a specific genre"
        ),
        Resource(
            uri="library://insights/neglected",
            name="Neglected Gems",
            description="High-quality games you own but barely played"
        ),
        Resource(
            uri="library://social/compatible/{friend_id}",
            name="Friend Compatibility",
            description="Games and compatibility analysis with a specific friend"
        ),
        Resource(
            uri="library://trends/recent",
            name="Recent Trends",
            description="What you've been gravitating toward lately"
        )
    ]
```

## Summary

The current implementation provides a solid foundation but lacks several **production-ready components** and **advanced features** that would make it truly shine as a personal Steam librarian. The biggest gaps are around:

1. **Error handling and resilience**
2. **User context management**
3. **Performance optimization**
4. **Advanced contextual intelligence**

Adding these improvements would transform the basic library browsing tool into a sophisticated, intelligent gaming companion that understands user context, handles edge cases gracefully, and provides truly personalized recommendations.