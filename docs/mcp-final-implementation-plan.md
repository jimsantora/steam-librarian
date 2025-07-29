# Steam Librarian MCP Server - Final Implementation Plan

## Vision: Your Intelligent Gaming Companion

The Steam Librarian is not just another library browser - it's an intelligent companion that understands your gaming personality, respects your time, and helps you rediscover the joy in games you already own. It combines the warmth of a knowledgeable friend with the precision of data-driven insights.

### Core Philosophy

**Why This Matters:** Most gamers have extensive libraries filled with unplayed gems, forgotten favorites, and impulse purchases. The paradox of choice often leads to decision paralysis - spending more time browsing than playing. Steam Librarian solves this by being your personal gaming curator who knows your library inside and out.

**The Experience:** Imagine having a friend who:
- Remembers every game you've ever played and why you enjoyed it
- Knows your current mood and available time
- Understands what your friends are playing
- Can instantly suggest the perfect game for any situation
- Never judges your backlog but helps you enjoy it

## Architecture Overview

### Design Decisions & Reasoning

**1. Resource-First Architecture**
- **Decision:** Lead with resources over tools
- **Reasoning:** Resources provide persistent, cacheable context that grounds every conversation. They're the "home screens" users return to, while tools are the actions taken from those screens.

**2. Unified Friend Data Tool**
- **Decision:** Single `get_friends_data` tool with multiple data types
- **Reasoning:** Reduces cognitive load and tool proliferation. One tool, multiple purposes is easier to understand and maintain than many specialized tools.

**3. Context-Aware Intelligence**
- **Decision:** Every tool accepts optional context parameters
- **Reasoning:** Gaming is contextual - what's perfect for a Friday night differs from a lunch break. Context enables truly personalized recommendations.

**4. Graceful Multi-User Handling**
- **Decision:** Support multiple Steam accounts with intelligent fallbacks
- **Reasoning:** Households often share computers. The system should intelligently handle multiple users without configuration headaches.

## Core Components

### Resources (The Foundation)

Resources are the persistent views into your library that provide context and grounding for all interactions.

#### 1. `library://overview`
**Purpose:** Your gaming dashboard - the at-a-glance view that grounds every conversation.

**Implementation:**
```python
@server.read_resource()
async def handle_read_resource(uri: str) -> ResourceContents:
    if uri == "library://overview":
        # Resolve user context with intelligent fallbacks
        user_context = await resolve_user_context()
        if "error" in user_context:
            return create_error_resource(uri, user_context)
        
        # Get cached stats with TTL
        stats = await library_cache.get_or_set(
            f"overview_{user_context['user'].steam_id}",
            lambda: calculate_library_overview(user_context['user'])
        )
        
        return TextResourceContents(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(stats, indent=2)
        )
```

**Why This Design:** The overview is likely accessed frequently, so caching is critical. The multi-user resolution happens transparently.

#### 2. `library://games/{app_id}`
**Purpose:** Deep, contextual information about any game combining Steam data with personal history.

**Implementation Enhancement:**
```python
async def get_game_details(app_id: str, context: dict = None):
    """Get game details with optional context for different views"""
    
    # Validate app_id
    if not app_id.isdigit():
        return {"error": "Invalid app_id format"}
    
    # Eager load related data in single query
    game = session.query(Game).options(
        joinedload(Game.genres),
        joinedload(Game.developers),
        joinedload(Game.publishers),
        joinedload(Game.categories),
        joinedload(Game.reviews)
    ).filter_by(app_id=app_id).first()
    
    if not game:
        return {"error": "Game not found", "app_id": app_id}
    
    # Build contextual response
    details = {
        "app_id": game.app_id,
        "name": game.name,
        "metadata": extract_game_metadata(game),
        "your_history": await get_user_game_history(app_id, context),
        "social_context": await get_game_social_context(app_id, context),
        "recommendations": await get_similar_games(game, limit=5)
    }
    
    # Add context-specific information
    if context and context.get("purpose") == "multiplayer":
        details["multiplayer_info"] = await get_multiplayer_details(game)
    
    return details
```

**Why This Design:** Games aren't viewed in isolation - context matters. Multiplayer planning needs different details than solo discovery.

#### 3. Extended Resources

```python
# Genre-specific views
"library://genres/{genre_name}"

# Social resources  
"library://friends/{friend_id}/compatibility"
"library://social/groups/{group_id}"

# Insight resources
"library://insights/neglected"  # High-rated, low-playtime games
"library://insights/trending"    # What you're gravitating toward
"library://insights/completion"  # Games close to completion
```

**Why These Additions:** These resources provide focused views for specific use cases, reducing the need for complex tool calls.

### Tools (The Intelligence)

Tools provide intelligent actions and analysis, always with proper error handling and validation.

#### 1. `search_games` - Natural Language Understanding

**Enhanced Implementation:**
```python
@handle_mcp_errors
async def search_games_handler(
    query: str, 
    user_steam_id: Optional[str] = None,
    context: Optional[dict] = None
):
    """Intelligent search with natural language understanding"""
    
    # Validate input
    validated = SearchGamesInput(query=query, user_steam_id=user_steam_id)
    
    # Parse intent with enhanced understanding
    intent = parse_enhanced_intent(validated.query)
    
    # Resolve user context
    user_context = await resolve_user_context(validated.user_steam_id)
    if "error" in user_context:
        # Continue with anonymous search
        user_id = None
    else:
        user_id = user_context["user"].steam_id
    
    # Build intelligent query
    results = await build_smart_search_query(intent, user_id, context)
    
    # Rank results by relevance
    ranked_results = await rank_search_results(results, intent, user_context)
    
    return format_search_response(validated.query, intent, ranked_results)

def parse_enhanced_intent(query: str) -> dict:
    """Parse natural language with mood, time, and difficulty understanding"""
    
    query_lower = query.lower()
    intent = {"original": query, "components": []}
    
    # Mood detection
    mood_keywords = {
        "relaxing": ["relaxing", "chill", "casual", "calm", "peaceful"],
        "intense": ["intense", "challenging", "hard", "difficult", "competitive"],
        "social": ["multiplayer", "co-op", "friends", "together"],
        "quick": ["quick", "short", "brief", "fast"],
        "deep": ["long", "deep", "immersive", "story"]
    }
    
    for mood, keywords in mood_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            intent["components"].append({"type": "mood", "value": mood})
    
    # Time-based queries
    time_patterns = {
        r"(\d+)\s*(?:hours?|hrs?)": "hours",
        r"(\d+)\s*(?:minutes?|mins?)": "minutes",
        r"lunch\s*break": "30_minutes",
        r"quick\s*session": "45_minutes",
        r"evening": "2_hours"
    }
    
    for pattern, time_type in time_patterns.items():
        match = re.search(pattern, query_lower)
        if match:
            intent["components"].append({
                "type": "time_constraint", 
                "value": match.group(0)
            })
    
    return intent
```

**Why This Design:** Natural language is how humans think about games. Understanding "something relaxing for my lunch break" is more valuable than rigid parameter matching.

#### 2. `filter_games` - Precision with Intelligence

**Enhanced Implementation:**
```python
@handle_mcp_errors
async def filter_games_handler(filters: dict):
    """Smart filtering with preset combinations"""
    
    # Validate filters
    validated = FilterGamesInput(**filters)
    
    # Check for smart filter presets
    if "preset" in filters:
        filters = apply_smart_preset(filters["preset"], filters)
    
    # Resolve user
    user_context = await resolve_user_context(filters.get("user_steam_id"))
    if "error" in user_context:
        return create_error_response(user_context["error"], "Cannot filter without user")
    
    # Build optimized query with proper joins
    query = build_optimized_filter_query(user_context["user"], validated)
    
    # Execute with timeout protection
    results = await execute_with_timeout(query, timeout_seconds=5)
    
    # Add contextual information to results
    enriched_results = await enrich_filter_results(results, user_context["user"])
    
    return format_filter_response(filters, enriched_results)

def apply_smart_preset(preset: str, base_filters: dict) -> dict:
    """Apply intelligent filter combinations"""
    
    presets = {
        "comfort_food": {
            "playtime_min": 10,  # Well-known games
            "review_summary": ["Overwhelmingly Positive", "Very Positive"],
            "sort_by": "playtime_desc"
        },
        "hidden_gems": {
            "playtime_max": 2,  # Barely touched
            "review_summary": ["Overwhelmingly Positive", "Very Positive"],
            "sort_by": "review_score_desc"
        },
        "quick_session": {
            "playtime_max": 50,  # Not too deep
            "categories": ["Casual", "Indie"],
            "sort_by": "last_played"
        }
    }
    
    if preset in presets:
        return {**presets[preset], **base_filters}
    return base_filters
```

**Why This Design:** Presets reduce cognitive load. Users think in terms of "comfort food games" not "playtime_min: 10, review_summary: positive".

#### 3. `get_recommendations` - Contextual Intelligence

**Enhanced Implementation:**
```python
@handle_mcp_errors
async def get_recommendations_handler(
    user_steam_id: str,
    context: Optional[dict] = None
):
    """Multi-faceted recommendations with context awareness"""
    
    # Comprehensive user analysis
    user_profile = await build_comprehensive_user_profile(user_steam_id)
    
    # Time-aware recommendations
    current_context = {
        "time_of_day": get_time_period(),  # morning, afternoon, evening, night
        "day_of_week": get_day_type(),     # weekday, weekend
        "recent_sessions": await get_recent_session_patterns(user_steam_id)
    }
    
    if context:
        current_context.update(context)
    
    # Generate multi-dimensional recommendations
    recommendations = {
        "primary": await get_primary_recommendations(user_profile),
        "contextual": await get_contextual_recommendations(user_profile, current_context),
        "social": await get_social_recommendations(user_profile),
        "discovery": await get_discovery_recommendations(user_profile),
        "quick_picks": await get_quick_session_games(user_profile),
        "deep_dives": await get_immersive_recommendations(user_profile)
    }
    
    # Add explanations for each recommendation
    for category, games in recommendations.items():
        for game in games:
            game["reason"] = await generate_recommendation_reason(
                game, user_profile, category
            )
    
    return format_recommendations_response(recommendations, current_context)

async def generate_recommendation_reason(game: dict, user_profile: dict, category: str) -> str:
    """Generate human-friendly explanation for recommendation"""
    
    reasons = []
    
    # Genre match
    if game["genres"] & user_profile["favorite_genres"]:
        reasons.append(f"Matches your love of {', '.join(game['genres'] & user_profile['favorite_genres'])}")
    
    # Playtime patterns
    if category == "quick_picks" and game["avg_session_length"] < 45:
        reasons.append("Perfect for your typical 30-45 minute sessions")
    
    # Social proof
    if game["friends_playing"] > 0:
        reasons.append(f"{game['friends_playing']} friends play this")
    
    # Neglected gem
    if game["playtime"] < 2 and game["review_score"] > 90:
        reasons.append("Highly rated but you've barely tried it")
    
    return " • ".join(reasons) if reasons else "Matches your gaming profile"
```

**Why This Design:** Recommendations without explanations feel arbitrary. Users trust suggestions when they understand the reasoning.

#### 4. `get_friends_data` - Social Intelligence

**Enhanced Implementation:**
```python
@handle_mcp_errors
async def get_friends_data_handler(
    data_type: str,
    user_steam_id: Optional[str] = None,
    friend_steam_id: Optional[str] = None,
    **kwargs
):
    """Unified social data with rich insights"""
    
    # Validate data type
    if data_type not in ["common_games", "friend_activity", "multiplayer_compatible", "compatibility_score"]:
        return create_error_response("INVALID_DATA_TYPE", f"Unknown data type: {data_type}")
    
    # Resolve users
    user_context = await resolve_user_context(user_steam_id)
    if "error" in user_context:
        return create_error_response(user_context["error"], "User not found")
    
    user = user_context["user"]
    
    # Route to appropriate handler
    if data_type == "compatibility_score":
        return await calculate_friend_compatibility(user, friend_steam_id)
    elif data_type == "multiplayer_compatible":
        return await find_multiplayer_opportunities(user, **kwargs)
    # ... other data types

async def calculate_friend_compatibility(user: User, friend_id: str) -> dict:
    """Calculate gaming compatibility between users"""
    
    friend = await get_user_by_id(friend_id)
    if not friend:
        return create_error_response("FRIEND_NOT_FOUND", "Friend not found")
    
    # Get common games with playtime
    common_games = await get_common_games_with_stats(user.steam_id, friend.steam_id)
    
    # Calculate compatibility metrics
    compatibility = {
        "overall_score": 0,
        "genre_overlap": calculate_genre_overlap(user, friend),
        "playtime_similarity": calculate_playtime_patterns_similarity(user, friend),
        "game_overlap": len(common_games) / min(user.game_count, friend.game_count),
        "multiplayer_potential": calculate_multiplayer_compatibility(common_games),
        "recommendations": await get_games_to_play_together(user, friend, common_games)
    }
    
    # Calculate overall score (0-100)
    compatibility["overall_score"] = int(
        (compatibility["genre_overlap"] * 0.3 +
         compatibility["playtime_similarity"] * 0.2 +
         compatibility["game_overlap"] * 0.3 +
         compatibility["multiplayer_potential"] * 0.2) * 100
    )
    
    return compatibility
```

**Why This Design:** Social gaming is about compatibility, not just common ownership. Understanding play styles helps suggest games both players will enjoy.

#### 5. `get_library_stats` - Deep Analytics

**Enhanced Implementation:**
```python
@handle_mcp_errors
async def get_library_stats_handler(
    user_steam_id: str,
    time_period: Optional[str] = "all_time",
    include_insights: bool = True
):
    """Comprehensive library analysis with actionable insights"""
    
    # Get user's complete gaming data
    user_data = await get_complete_user_data(user_steam_id)
    
    stats = {
        "overview": calculate_overview_stats(user_data),
        "genres": analyze_genre_preferences(user_data, time_period),
        "play_patterns": analyze_temporal_patterns(user_data),
        "value_analysis": calculate_value_metrics(user_data),
        "social_influence": analyze_social_patterns(user_data),
        "completion_analysis": analyze_completion_patterns(user_data)
    }
    
    if include_insights:
        stats["insights"] = await generate_actionable_insights(stats, user_data)
    
    return stats

async def generate_actionable_insights(stats: dict, user_data: dict) -> list:
    """Generate actionable insights from statistics"""
    
    insights = []
    
    # Backlog insight
    if stats["overview"]["unplayed_percentage"] > 0.5:
        insights.append({
            "type": "backlog_heavy",
            "severity": "medium",
            "message": f"You have {stats['overview']['unplayed_games']} unplayed games. Consider focusing on your existing library before buying more.",
            "action": "Try the 'hidden_gems' filter to find highly-rated unplayed games"
        })
    
    # Genre shift insight
    genre_shift = detect_genre_preference_shift(stats["genres"])
    if genre_shift:
        insights.append({
            "type": "taste_evolution", 
            "severity": "info",
            "message": f"Your taste is shifting from {genre_shift['from']} to {genre_shift['to']} games",
            "action": f"Explore more {genre_shift['to']} games in your library"
        })
    
    # Value insight
    if stats["value_analysis"]["cost_per_hour"] < 1.0:
        insights.append({
            "type": "excellent_value",
            "severity": "positive",
            "message": f"Your gaming provides excellent value at ${stats['value_analysis']['cost_per_hour']:.2f} per hour",
            "action": "You're getting great value from your library!"
        })
    
    # Social insight
    if stats["social_influence"]["friend_inspired_purchases"] > 0.3:
        insights.append({
            "type": "social_gamer",
            "severity": "info", 
            "message": "You often play games your friends recommend",
            "action": "Check what your friends are playing for your next game"
        })
    
    return insights
```

**Why This Design:** Statistics without insights are just numbers. Actionable insights help users make better gaming decisions.

### Prompts (The Personality)

Prompts orchestrate tools and resources into coherent workflows.

#### 1. `rediscover_library` - The Core Experience

**Implementation:**
```python
async def rediscover_library_prompt(arguments: dict):
    """The signature experience - intelligent library rediscovery"""
    
    mood = arguments.get("mood", "any")
    time_available = arguments.get("time_available", "any")
    
    # Build a conversation flow that feels natural
    messages = [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"I want to find something to play. Mood: {mood}. Time: {time_available}."
            }
        },
        {
            "role": "assistant",
            "content": {
                "type": "text",
                "text": "Let me help you rediscover something perfect from your library. First, I'll check what you've been playing recently to avoid repetition..."
            }
        },
        {
            "role": "assistant",
            "content": {
                "type": "resource",
                "resource": {"uri": "library://activity/recent"}
            }
        },
        {
            "role": "assistant",
            "content": {
                "type": "text",
                "text": "Now let me find games that match your current mood and available time..."
            }
        },
        {
            "role": "assistant",
            "content": {
                "type": "tool_use",
                "tool": "get_recommendations",
                "arguments": {
                    "context": {
                        "mood": mood,
                        "time_available": time_available,
                        "exclude_recent": True
                    }
                }
            }
        }
    ]
    
    return messages
```

**Why This Design:** The conversation flow mimics how a knowledgeable friend would help - understanding context, checking recent activity, then making thoughtful suggestions.

#### 2. Enhanced Prompts

```python
# Smart prompt registration
prompts = [
    Prompt(
        name="gaming_therapy",
        description="Get gaming recommendations based on how you're feeling",
        arguments=[
            PromptArgument(name="feeling", description="How are you feeling today?", required=True),
            PromptArgument(name="energy_level", description="Low, medium, or high energy?", required=False)
        ]
    ),
    Prompt(
        name="weekend_planner", 
        description="Plan your weekend gaming sessions",
        arguments=[
            PromptArgument(name="available_hours", description="How many hours for gaming?", required=True),
            PromptArgument(name="solo_or_social", description="Solo, friends, or both?", required=False)
        ]
    ),
    Prompt(
        name="backlog_therapist",
        description="Get help tackling your backlog without overwhelm", 
        arguments=[
            PromptArgument(name="commitment_level", description="Light, medium, or deep commitment?", required=False)
        ]
    )
]
```

**Why These Additions:** Different life situations call for different gaming approaches. These prompts address emotional and practical needs.

## Error Handling & Resilience

### Unified Error Handling

```python
from enum import Enum
from typing import Optional, Dict, Any
import logging

class ErrorType(Enum):
    USER_NOT_FOUND = "USER_NOT_FOUND"
    GAME_NOT_FOUND = "GAME_NOT_FOUND" 
    DATABASE_ERROR = "DATABASE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"

class MCPError(Exception):
    def __init__(self, error_type: ErrorType, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

def create_error_response(error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> dict:
    """Create standardized error response"""
    response = {
        "error": True,
        "error_type": error_type,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        response["details"] = details
    return response

@handle_mcp_errors
async def any_tool_handler():
    """All tools wrapped with error handling"""
    pass
```

**Why This Design:** Consistent error handling improves debugging and user experience. Users get helpful messages, not stack traces.

### Graceful Degradation

```python
async def get_recommendations_with_fallback(user_id: str, context: dict) -> dict:
    """Recommendations with graceful degradation"""
    
    recommendations = {}
    
    # Try primary recommendation engine
    try:
        recommendations["primary"] = await get_ml_recommendations(user_id, context)
    except Exception as e:
        logging.warning(f"ML recommendations failed: {e}")
        # Fall back to rule-based
        recommendations["primary"] = await get_rule_based_recommendations(user_id, context)
    
    # Try social recommendations (non-critical)
    try:
        recommendations["social"] = await get_social_recommendations(user_id)
    except Exception as e:
        logging.info(f"Social recommendations unavailable: {e}")
        recommendations["social"] = []
    
    return recommendations
```

**Why This Design:** Some features are nice-to-have. The system should degrade gracefully when non-critical components fail.

## Performance Optimization

### Intelligent Caching Strategy

```python
from functools import lru_cache
import hashlib

class SmartCache:
    """Multi-tier caching with TTL and invalidation"""
    
    def __init__(self):
        self.memory_cache = {}  # Hot cache in memory
        self.disk_cache = DiskCache("./cache")  # Persistent cache
        
    async def get_or_compute(self, key: str, compute_func, ttl: int = 3600):
        # Check memory cache first
        if key in self.memory_cache:
            value, timestamp = self.memory_cache[key]
            if time.time() - timestamp < ttl:
                return value
        
        # Check disk cache
        disk_value = await self.disk_cache.get(key)
        if disk_value and not self._is_expired(disk_value, ttl):
            # Promote to memory cache
            self.memory_cache[key] = (disk_value["value"], time.time())
            return disk_value["value"]
        
        # Compute and cache
        value = await compute_func()
        await self._cache_value(key, value, ttl)
        return value
    
    def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        pattern = f"*{user_id}*"
        self._invalidate_pattern(pattern)

# Usage
cache = SmartCache()

@server.call_tool()
async def handle_library_stats(user_id: str):
    return await cache.get_or_compute(
        f"library_stats_{user_id}",
        lambda: calculate_library_stats(user_id),
        ttl=1800  # 30 minutes
    )
```

**Why This Design:** Multi-tier caching balances memory usage with performance. Hot data stays in memory, cold data persists to disk.

### Database Query Optimization

```python
# Optimized query patterns
def get_user_games_optimized(user_id: str):
    """Single query with all needed joins"""
    return session.query(UserGame).options(
        joinedload(UserGame.game)
        .joinedload(Game.genres)
        .joinedload(Game.developers),
        joinedload(UserGame.game)
        .joinedload(Game.categories),
        joinedload(UserGame.game)
        .joinedload(Game.reviews)
    ).filter(UserGame.steam_id == user_id).all()

# Connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600    # Recycle connections after 1 hour
)
```

**Why This Design:** Database queries are often the bottleneck. Optimized queries with proper joins reduce round trips.

## Security & Validation

### Input Validation Layer

```python
from pydantic import BaseModel, validator, ValidationError
import re

class SteamIDValidator:
    @staticmethod
    def validate(steam_id: str) -> str:
        """Validate Steam ID format"""
        if not steam_id:
            raise ValueError("Steam ID cannot be empty")
        
        # Check if it's a valid Steam64 ID
        if re.match(r"^\d{17}$", steam_id):
            return steam_id
        
        # Check if it's a valid Steam3 ID
        if re.match(r"^\[U:1:\d+\]$", steam_id):
            return convert_to_steam64(steam_id)
        
        raise ValueError(f"Invalid Steam ID format: {steam_id}")

class QuerySanitizer:
    @staticmethod
    def sanitize(query: str) -> str:
        """Sanitize search queries"""
        # Remove SQL injection attempts
        dangerous_patterns = [
            r";\s*DROP",
            r";\s*DELETE", 
            r"UNION\s+SELECT",
            r"OR\s+1=1"
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError("Invalid query detected")
        
        # Limit length
        if len(query) > 200:
            query = query[:200]
        
        # Clean up whitespace
        query = " ".join(query.split())
        
        return query
```

**Why This Design:** Input validation prevents both security issues and confusing errors. Clean data in, clean data out.

## Configuration & Deployment

### Environment Configuration

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///steam_library.db"
    
    # Caching
    cache_ttl: int = 3600
    enable_cache: bool = True
    cache_backend: str = "memory"  # memory, redis, disk
    
    # Performance
    query_timeout: int = 5
    max_results: int = 100
    
    # Steam API (optional)
    steam_api_key: Optional[str] = None
    
    # User defaults
    default_steam_id: Optional[str] = None
    
    # Feature flags
    enable_ml_recommendations: bool = False
    enable_social_features: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

**Why This Design:** Configuration should be flexible and environment-aware. Feature flags allow gradual rollout of new features.

### Health Monitoring

```python
@server.health_check()
async def health_check() -> dict:
    """Comprehensive health check"""
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Database check
    try:
        db_start = time.time()
        user_count = session.query(User).count()
        db_latency = time.time() - db_start
        health["checks"]["database"] = {
            "status": "healthy",
            "latency_ms": int(db_latency * 1000),
            "user_count": user_count
        }
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Cache check
    try:
        cache_working = await cache.get_or_compute("health_check", lambda: "ok", ttl=60)
        health["checks"]["cache"] = {"status": "healthy"}
    except Exception as e:
        health["checks"]["cache"] = {"status": "degraded", "error": str(e)}
    
    return health
```

**Why This Design:** Health checks enable proactive monitoring and graceful degradation when issues arise.

## Usage Patterns & Examples

### The Rediscovery Experience
```
User: "I'm bored and have about an hour"
Assistant: *Checks recent activity - sees user played action games all week*
Assistant: "You've been playing intense action games lately. For a change of pace, 
           you might enjoy 'A Short Hike' - a relaxing exploration game you bought
           but never tried. It's perfect for an hour session and has overwhelmingly
           positive reviews."
```

### The Social Planner
```
User: "Setting up game night with 3 friends"
Assistant: *Analyzes friend libraries and playtime*
Assistant: "Found 3 great options:
           1. Deep Rock Galactic - You all own it, supports 4 players, everyone has 
              similar skill levels
           2. Terraria - Fresh for everyone except Tom, great for discovery together
           3. Left 4 Dead 2 - Classic choice, you've all played before and enjoyed it"
```

### The Insight Seeker
```
User: "How's my gaming habit?"
Assistant: *Runs comprehensive analysis*
Assistant: "You're a variety gamer with excellent value habits:
           - 487 games owned, 68% played (well above average!)
           - $0.87 per hour of entertainment (fantastic value)
           - You tend to play RPGs on weekends and quick indie games on weekdays
           - Suggestion: You have 12 highly-rated RPGs under 2 hours playtime - 
             perfect for your weekend sessions"
```

## Conclusion

This Steam Librarian implementation creates an intelligent, contextual, and resilient MCP server that truly understands gamers' needs. By combining thoughtful architecture, smart error handling, performance optimization, and human-centered design, it transforms a simple library browser into an indispensable gaming companion.

The key innovation is treating games not as a static list but as a dynamic, contextual experience that adapts to mood, time, social situations, and personal gaming evolution. Every design decision prioritizes the user experience while maintaining technical excellence.

With this implementation, users don't just browse their library - they rediscover the joy of gaming through intelligent curation and insightful recommendations.