# Steam Librarian MCP Server Implementation

## Vision: Your Personal Steam Librarian

A conversational assistant that helps you rediscover your existing library, make smart gaming decisions, and connect with friends through games. Like having a knowledgeable gaming buddy who knows your library inside out.

**What we're accomplishing:** A conversational assistant that helps you rediscover your existing library, make smart gaming decisions, and connect with friends through games. Not a store browser or wishlist manager - but a curator of what you already own.

**How it feels:** Like texting a friend who has perfect memory of every game you've ever played and can instantly suggest "Hey, remember that game you bought 3 years ago? It's perfect for tonight."

## Core Resources (The Foundation)

### 1. `library://overview`
Your library at a glance - total games, playtime, recent activity. This is the "home screen" that grounds every conversation.

### 2. `library://games/{app_id}`
Deep dive into any game - combining details, reviews, and your personal history with it.

### 3. `library://activity/recent`
What you've been playing lately - crucial for avoiding repetitive suggestions and understanding current mood.

## Essential Tools (The Brain)

### 1. `search_games`
**Why:** The workhorse - handles everything from "find me an RPG" to "games like Hades"

**Parameters:**
- `query`: Natural language search
- `user_steam_id`: For personalized results

### 2. `filter_games`
**Why:** Precision filtering when you know what you want

**Parameters:**
- `playtime_min/max`: "Never played" or "comfort food games"
- `review_summary`: Quality filter
- `maturity_rating`: Family-friendly options

### 3. `get_recommendations`
**Why:** The magic - learns your patterns and suggests accordingly

**Combines:**
- Your playtime patterns
- Genre preferences
- Friend activity
- Neglected gems

### 4. `get_friends_data`
**Why:** Social gaming is half the fun

**Data types:**
- `common_games`: "What can we play together?"
- `friend_activity`: "What's everyone playing?"
- `multiplayer_compatible`: "Friday night options"

### 5. `get_library_stats`
**Why:** Self-awareness about gaming habits

**Returns:**
- Genre breakdown
- Playtime patterns
- Completion rates
- Investment analysis

## Focused Prompts (The Personality)

### 1. `rediscover_library`
**Prompt:** "Find something I already own to play"

**Uses:** `filter_games` → `get_game_details` → `get_recommendations`

**Feels like:** Browsing your bookshelf with a friend who remembers why you bought each book

### 2. `plan_multiplayer_session`
**Prompt:** "What can my friends and I play tonight?"

**Uses:** `get_friends_data` → `search_games` → `filter_games`

**Feels like:** A group chat coordinator who knows everyone's schedules and preferences

### 3. `analyze_gaming_patterns`
**Prompt:** "What kind of gamer am I?"

**Uses:** `get_library_stats` → `get_recently_played` → pattern analysis

**Feels like:** A friendly therapist for your gaming habits

## How They Work Together

### The Rediscovery Flow

**User:** "I'm bored, what should I play?"
1. System checks `library://activity/recent` (avoid suggesting what they just played)
2. Runs `get_recommendations` based on mood/time available
3. Enriches with `get_game_details` for forgotten features
4. **Result:** "You haven't touched Hollow Knight in 2 years, but based on your recent Hades sessions..."

### The Social Flow

**User:** "Planning game night with friends"
1. System uses `get_friends_data` for common libraries
2. Filters with `filter_games` for multiplayer categories
3. Cross-references with everyone's playtime
4. **Result:** "You all own Terraria but only Jake has played it. Perfect for discovery together!"

### The Insight Flow

**User:** "Am I buying too many games?"
1. System runs `get_library_stats` for the reality check
2. Uses `filter_games` to find unplayed games
3. Calculates investment vs. enjoyment
4. **Result:** "You have 47 unplayed games worth $423, but you've gotten 400 hours from just 5 games..."

## What We're NOT Including (And Why)

### Excluded:
- Market analysis tools (not about buying more)
- Achievement tracking (too granular)
- External price tracking (we focus on what you own)
- Complex curation tools (keep it conversational)

**Why:** Every excluded feature could dilute the core experience. We want someone who opens this to immediately get value from their existing library, not feel overwhelmed by options.

## The Magic Moment

The server shines when it makes connections humans miss:

- "You loved Outer Wilds' exploration, and you own Subnautica but never tried it"
- "Your friend group all owns Valheim but nobody's played it together"
- "You always play for exactly 45 minutes on weeknights - here are games that fit"

---

This focused design creates a cohesive experience where every tool and resource serves the central mission: helping you enjoy the games you already own, when you want to play them, with the people you want to play with.

## Summary

I've created a comprehensive implementation plan for the Steam Librarian MCP server. This design focuses on helping users rediscover and enjoy their existing Steam library through:

### Core Features:
- **3 Resources:** Library overview, game details, and recent activity tracking
- **5 Essential Tools:** Smart search, precise filtering, AI recommendations, friend data analysis, and library statistics
- **3 Focused Prompts:** Library rediscovery, multiplayer planning, and gaming pattern analysis

### Key Implementation Details:
- Uses the official MCP Python SDK with proper async/await patterns
- Leverages SQLAlchemy for efficient database queries with eager loading
- Implements natural language understanding for search queries
- Provides intelligent caching for expensive operations
- Includes friend network analysis for social gaming

### The Magic:
- Finds neglected gems in your library based on review scores
- Suggests games that fit your available time
- Identifies what games all your friends own for group play
- Provides insights into your gaming habits and value

The server feels like chatting with a knowledgeable friend who has perfect memory of your entire game collection and can instantly suggest the perfect game for any situation.

## Core Resources

### 1. Library Overview

```python
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Resource, ResourceContents, TextResourceContents
import json

server = Server("steam-librarian")

@server.list_resources()
async def handle_list_resources():
    return [
        Resource(
            uri="library://overview",
            name="Library Overview",
            description="Your Steam library at a glance - total games, playtime, recent activity",
            mimeType="application/json"
        ),
        Resource(
            uri="library://games/{app_id}",
            name="Game Details",
            description="Deep dive into any game - details, reviews, and your personal history",
            mimeType="application/json"
        ),
        Resource(
            uri="library://activity/recent",
            name="Recent Activity",
            description="What you've been playing lately",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> ResourceContents:
    if uri == "library://overview":
        # Get library statistics
        stats = await get_library_overview()
        return TextResourceContents(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(stats, indent=2)
        )
    
    elif uri.startswith("library://games/"):
        app_id = uri.split("/")[-1]
        game_data = await get_game_details(app_id)
        return TextResourceContents(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(game_data, indent=2)
        )
    
    elif uri == "library://activity/recent":
        recent = await get_recent_activity()
        return TextResourceContents(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(recent, indent=2)
        )

async def get_library_overview():
    """Get comprehensive library statistics"""
    return {
        "total_games": 1111,
        "total_playtime_hours": 2456,
        "genres": {
            "Action": 245,
            "RPG": 189,
            "Strategy": 134
        },
        "recent_activity": {
            "last_7_days": 12.5,
            "last_30_days": 67.3
        },
        "unplayed_games": 312,
        "completion_rate": 0.28
    }
```

### 2. Game Details Resource

```python
async def get_game_details(app_id: str):
    """Get comprehensive game information"""
    # Query the database for game details
    game = session.query(Game).filter_by(app_id=app_id).first()
    
    if not game:
        return {"error": "Game not found"}
    
    # Get related data with eager loading
    reviews = session.query(GameReview).filter_by(app_id=app_id).first()
    user_game = session.query(UserGame).filter_by(
        app_id=app_id,
        steam_id=current_user_id
    ).first()
    
    return {
        "app_id": game.app_id,
        "name": game.name,
        "genres": [g.genre_name for g in game.genres],
        "developers": [d.developer_name for d in game.developers],
        "review_summary": reviews.review_summary if reviews else None,
        "your_playtime": {
            "total_hours": user_game.playtime_forever / 60 if user_game else 0,
            "recent_hours": user_game.playtime_2weeks / 60 if user_game else 0,
            "last_played": calculate_last_played(user_game)
        },
        "features": {
            "steam_deck_verified": game.steam_deck_verified,
            "controller_support": game.controller_support,
            "multiplayer": has_multiplayer_categories(game)
        }
    }
```

## Essential Tools

### 1. Search Games

```python
from mcp.types import Tool, TextContent
from typing import Optional, List

@server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="search_games",
            description="Natural language game search across your library",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'RPG games', 'games like Dark Souls')"
                    },
                    "user_steam_id": {
                        "type": "string",
                        "description": "Steam ID for personalized results"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "search_games":
        return await search_games_handler(
            arguments["query"],
            arguments.get("user_steam_id")
        )

async def search_games_handler(query: str, user_steam_id: Optional[str]):
    """Intelligent game search with natural language understanding"""
    
    # Parse query intent
    intent = parse_search_intent(query)
    
    # Build dynamic query based on intent
    games_query = session.query(Game).join(UserGame)
    
    if intent["type"] == "genre":
        games_query = games_query.join(GameGenre).join(Genre).filter(
            Genre.genre_name.ilike(f"%{intent['value']}%")
        )
    elif intent["type"] == "similar":
        # Find games similar to the mentioned game
        reference_game = find_game_by_name(intent["value"])
        if reference_game:
            similar_games = find_similar_games(reference_game)
            games_query = games_query.filter(Game.app_id.in_(similar_games))
    else:
        # General text search
        games_query = games_query.filter(
            or_(
                Game.name.ilike(f"%{query}%"),
                Game.developers.any(Developer.developer_name.ilike(f"%{query}%"))
            )
        )
    
    # Add user context if provided
    if user_steam_id:
        games_query = games_query.filter(UserGame.steam_id == user_steam_id)
    
    results = games_query.limit(20).all()
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "query": query,
            "intent": intent,
            "results": [format_game_result(g) for g in results],
            "count": len(results)
        }, indent=2)
    )]

def parse_search_intent(query: str):
    """Parse natural language query into structured intent"""
    query_lower = query.lower()
    
    # Genre detection
    genres = ["rpg", "action", "strategy", "puzzle", "adventure"]
    for genre in genres:
        if genre in query_lower:
            return {"type": "genre", "value": genre}
    
    # Similarity detection
    if "like" in query_lower or "similar to" in query_lower:
        # Extract game name after "like" or "similar to"
        pattern = r"(?:like|similar to)\s+(.+)"
        match = re.search(pattern, query_lower)
        if match:
            return {"type": "similar", "value": match.group(1).strip()}
    
    return {"type": "general", "value": query}
```

### 2. Filter Games

```python
@server.list_tools()
async def handle_list_tools():
    return [
        # ... previous tools ...
        Tool(
            name="filter_games",
            description="Filter games by specific criteria like playtime, ratings, or features",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_steam_id": {"type": "string"},
                    "playtime_min": {
                        "type": "number",
                        "description": "Minimum playtime in hours"
                    },
                    "playtime_max": {
                        "type": "number",
                        "description": "Maximum playtime in hours"
                    },
                    "review_summary": {
                        "type": "string",
                        "enum": ["Overwhelmingly Positive", "Very Positive", "Positive", "Mixed"]
                    },
                    "maturity_rating": {
                        "type": "string",
                        "description": "ESRB rating filter"
                    }
                }
            }
        )
    ]

async def filter_games_handler(filters: dict):
    """Precision filtering for specific game criteria"""
    
    query = session.query(Game, UserGame).join(UserGame)
    
    # Apply user filter
    if filters.get("user_steam_id"):
        query = query.filter(UserGame.steam_id == filters["user_steam_id"])
    
    # Playtime filters
    if "playtime_min" in filters:
        min_minutes = filters["playtime_min"] * 60
        query = query.filter(UserGame.playtime_forever >= min_minutes)
    
    if "playtime_max" in filters:
        max_minutes = filters["playtime_max"] * 60
        query = query.filter(UserGame.playtime_forever <= max_minutes)
    
    # Review filter
    if filters.get("review_summary"):
        query = query.join(GameReview).filter(
            GameReview.review_summary == filters["review_summary"]
        )
    
    # Maturity rating filter
    if filters.get("maturity_rating"):
        query = query.filter(Game.maturity_rating == filters["maturity_rating"])
    
    results = query.limit(50).all()
    
    # Format results with context
    formatted_results = []
    for game, user_game in results:
        formatted_results.append({
            "app_id": game.app_id,
            "name": game.name,
            "playtime_hours": user_game.playtime_forever / 60,
            "last_played": calculate_days_since_played(user_game),
            "review_summary": get_review_summary(game.app_id)
        })
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "filters": filters,
            "count": len(formatted_results),
            "games": formatted_results
        }, indent=2)
    )]
```

### 3. Get Recommendations

```python
@server.list_tools()
async def handle_list_tools():
    return [
        # ... previous tools ...
        Tool(
            name="get_recommendations",
            description="Get personalized game recommendations based on your patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_steam_id": {"type": "string"}
                }
            }
        )
    ]

async def get_recommendations_handler(user_steam_id: str):
    """Smart recommendations based on gaming patterns"""
    
    # Analyze user patterns
    patterns = await analyze_user_patterns(user_steam_id)
    
    # Get different types of recommendations
    recommendations = {
        "based_on_playtime": await recommend_by_playtime_patterns(user_steam_id, patterns),
        "neglected_gems": await find_neglected_gems(user_steam_id),
        "friend_favorites": await recommend_from_friends(user_steam_id),
        "genre_exploration": await recommend_new_genres(user_steam_id, patterns)
    }
    
    return [TextContent(
        type="text",
        text=json.dumps(recommendations, indent=2)
    )]

async def analyze_user_patterns(steam_id: str):
    """Analyze user's gaming patterns"""
    
    # Get user's games with playtime
    user_games = session.query(UserGame, Game).join(Game).filter(
        UserGame.steam_id == steam_id
    ).all()
    
    # Calculate patterns
    total_playtime = sum(ug.playtime_forever for ug, _ in user_games)
    avg_playtime = total_playtime / len(user_games) if user_games else 0
    
    # Genre preferences
    genre_playtime = {}
    for ug, game in user_games:
        for genre in game.genres:
            genre_playtime[genre.genre_name] = genre_playtime.get(genre.genre_name, 0) + ug.playtime_forever
    
    # Sort genres by playtime
    top_genres = sorted(genre_playtime.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Recent activity patterns
    recent_games = [
        (ug, g) for ug, g in user_games 
        if ug.playtime_2weeks > 0
    ]
    
    return {
        "total_games": len(user_games),
        "avg_playtime_hours": avg_playtime / 60,
        "top_genres": top_genres,
        "recent_activity_count": len(recent_games),
        "completion_tendency": calculate_completion_tendency(user_games)
    }

async def find_neglected_gems(steam_id: str):
    """Find high-quality games with low playtime"""
    
    query = session.query(Game, UserGame, GameReview).join(UserGame).join(GameReview).filter(
        UserGame.steam_id == steam_id,
        UserGame.playtime_forever < 120,  # Less than 2 hours
        GameReview.review_summary.in_(["Very Positive", "Overwhelmingly Positive"])
    ).order_by(GameReview.positive_reviews.desc()).limit(10)
    
    results = query.all()
    
    return [
        {
            "app_id": game.app_id,
            "name": game.name,
            "playtime_hours": user_game.playtime_forever / 60,
            "review_summary": review.review_summary,
            "reason": "Highly rated but barely played"
        }
        for game, user_game, review in results
    ]
```

### 4. Get Friends Data

```python
@server.list_tools()
async def handle_list_tools():
    return [
        # ... previous tools ...
        Tool(
            name="get_friends_data",
            description="Unified tool for all friends-related queries",
            inputSchema={
                "type": "object",
                "properties": {
                    "data_type": {
                        "type": "string",
                        "enum": ["common_games", "friend_activity", "multiplayer_compatible"],
                        "description": "Type of friend data to retrieve"
                    },
                    "user_steam_id": {"type": "string"},
                    "friend_steam_id": {"type": "string"},
                    "game_identifier": {"type": "string"}
                },
                "required": ["data_type"]
            }
        )
    ]

async def get_friends_data_handler(data_type: str, **kwargs):
    """Handle various friend-related data queries"""
    
    if data_type == "common_games":
        return await get_common_games(
            kwargs.get("user_steam_id"),
            kwargs.get("friend_steam_id")
        )
    
    elif data_type == "friend_activity":
        return await get_friend_activity(kwargs.get("user_steam_id"))
    
    elif data_type == "multiplayer_compatible":
        return await get_multiplayer_options(kwargs.get("user_steam_id"))

async def get_common_games(user_id: str, friend_id: Optional[str] = None):
    """Find games owned by multiple users"""
    
    if friend_id:
        # Common games between two users
        user_games = set(
            g.app_id for g in session.query(UserGame).filter_by(steam_id=user_id).all()
        )
        friend_games = set(
            g.app_id for g in session.query(UserGame).filter_by(steam_id=friend_id).all()
        )
        
        common_app_ids = user_games.intersection(friend_games)
        
        # Get game details for common games
        common_games = session.query(Game).filter(
            Game.app_id.in_(common_app_ids)
        ).all()
        
        return format_common_games_response(common_games, user_id, friend_id)
    
    else:
        # Common games among all friends
        friends = session.query(Friend).filter_by(user_steam_id=user_id).all()
        
        # Find games owned by multiple friends
        game_ownership = {}
        for friend in friends:
            friend_games = session.query(UserGame).filter_by(
                steam_id=friend.friend_steam_id
            ).all()
            
            for game in friend_games:
                if game.app_id not in game_ownership:
                    game_ownership[game.app_id] = []
                game_ownership[game.app_id].append(friend.friend_steam_id)
        
        # Filter for games owned by multiple friends
        popular_games = {
            app_id: owners 
            for app_id, owners in game_ownership.items() 
            if len(owners) >= 2
        }
        
        return format_friend_popular_games(popular_games)

async def get_multiplayer_options(user_id: str):
    """Find multiplayer games suitable for group play"""
    
    # Get user's friends
    friends = session.query(Friend).filter_by(user_steam_id=user_id).all()
    friend_ids = [f.friend_steam_id for f in friends]
    
    # Find multiplayer games owned by user
    multiplayer_categories = ["Multi-player", "Co-op", "Online Co-op", "Local Co-op"]
    
    user_multiplayer = session.query(Game, UserGame).join(UserGame).join(
        GameCategory
    ).join(Category).filter(
        UserGame.steam_id == user_id,
        Category.category_name.in_(multiplayer_categories)
    ).all()
    
    # Check which friends own each game
    multiplayer_options = []
    for game, user_game in user_multiplayer:
        # Count how many friends own this game
        friend_ownership = session.query(UserGame).filter(
            UserGame.app_id == game.app_id,
            UserGame.steam_id.in_(friend_ids)
        ).count()
        
        if friend_ownership > 0:
            multiplayer_options.append({
                "app_id": game.app_id,
                "name": game.name,
                "friends_who_own": friend_ownership,
                "total_friends": len(friend_ids),
                "your_playtime": user_game.playtime_forever / 60,
                "multiplayer_types": get_multiplayer_types(game)
            })
    
    # Sort by number of friends who own
    multiplayer_options.sort(key=lambda x: x["friends_who_own"], reverse=True)
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "multiplayer_games": multiplayer_options[:20],
            "total_options": len(multiplayer_options)
        }, indent=2)
    )]
```

### 5. Get Library Stats

```python
@server.list_tools()
async def handle_list_tools():
    return [
        # ... previous tools ...
        Tool(
            name="get_library_stats",
            description="Get comprehensive statistics about your game library",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_steam_id": {"type": "string"}
                }
            }
        )
    ]

async def get_library_stats_handler(user_steam_id: str):
    """Comprehensive library analysis"""
    
    # Get all user games
    user_games = session.query(UserGame, Game).join(Game).filter(
        UserGame.steam_id == user_steam_id
    ).all()
    
    # Calculate statistics
    stats = {
        "overview": calculate_overview_stats(user_games),
        "genre_distribution": calculate_genre_distribution(user_games),
        "playtime_analysis": analyze_playtime_patterns(user_games),
        "investment_analysis": calculate_investment_metrics(user_games),
        "social_stats": calculate_social_stats(user_steam_id)
    }
    
    return [TextContent(
        type="text",
        text=json.dumps(stats, indent=2)
    )]

def calculate_overview_stats(user_games):
    """Calculate basic library statistics"""
    total_games = len(user_games)
    total_playtime = sum(ug.playtime_forever for ug, _ in user_games)
    
    played_games = [ug for ug, _ in user_games if ug.playtime_forever > 0]
    unplayed_games = total_games - len(played_games)
    
    # Games by playtime brackets
    playtime_brackets = {
        "0_hours": 0,
        "0_2_hours": 0,
        "2_10_hours": 0,
        "10_50_hours": 0,
        "50_plus_hours": 0
    }
    
    for ug, _ in user_games:
        hours = ug.playtime_forever / 60
        if hours == 0:
            playtime_brackets["0_hours"] += 1
        elif hours < 2:
            playtime_brackets["0_2_hours"] += 1
        elif hours < 10:
            playtime_brackets["2_10_hours"] += 1
        elif hours < 50:
            playtime_brackets["10_50_hours"] += 1
        else:
            playtime_brackets["50_plus_hours"] += 1
    
    return {
        "total_games": total_games,
        "total_playtime_hours": total_playtime / 60,
        "played_games": len(played_games),
        "unplayed_games": unplayed_games,
        "completion_rate": len(played_games) / total_games if total_games > 0 else 0,
        "playtime_brackets": playtime_brackets,
        "average_playtime_per_game": (total_playtime / 60) / len(played_games) if played_games else 0
    }

def calculate_genre_distribution(user_games):
    """Analyze genre preferences by playtime"""
    genre_stats = {}
    
    for ug, game in user_games:
        for genre in game.genres:
            if genre.genre_name not in genre_stats:
                genre_stats[genre.genre_name] = {
                    "count": 0,
                    "total_playtime": 0,
                    "games": []
                }
            
            genre_stats[genre.genre_name]["count"] += 1
            genre_stats[genre.genre_name]["total_playtime"] += ug.playtime_forever
            genre_stats[genre.genre_name]["games"].append({
                "name": game.name,
                "playtime": ug.playtime_forever / 60
            })
    
    # Sort by playtime and limit game lists
    for genre in genre_stats.values():
        genre["total_playtime_hours"] = genre["total_playtime"] / 60
        genre["games"] = sorted(
            genre["games"], 
            key=lambda x: x["playtime"], 
            reverse=True
        )[:5]  # Top 5 games per genre
        del genre["total_playtime"]  # Remove redundant field
    
    return dict(sorted(
        genre_stats.items(), 
        key=lambda x: x[1]["total_playtime_hours"], 
        reverse=True
    ))
```

## Focused Prompts

### 1. Rediscover Library Prompt

```python
from mcp.types import Prompt, PromptArgument

@server.list_prompts()
async def handle_list_prompts():
    return [
        Prompt(
            name="rediscover_library",
            description="Find something you already own to play",
            arguments=[
                PromptArgument(
                    name="mood",
                    description="What kind of gaming mood are you in?",
                    required=False
                ),
                PromptArgument(
                    name="time_available",
                    description="How much time do you have? (e.g., '30 minutes', '2 hours')",
                    required=False
                )
            ]
        )
    ]

@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict):
    if name == "rediscover_library":
        return await rediscover_library_prompt(arguments)

async def rediscover_library_prompt(arguments: dict):
    """Help user rediscover games in their library"""
    
    mood = arguments.get("mood", "any")
    time_available = arguments.get("time_available", "any")
    
    # Build the prompt message
    messages = []
    
    # Add context about recent activity
    messages.append({
        "role": "user",
        "content": {
            "type": "text",
            "text": f"I want to find something to play from my Steam library. Mood: {mood}. Time available: {time_available}."
        }
    })
    
    # Include recent activity as context
    messages.append({
        "role": "assistant", 
        "content": {
            "type": "text",
            "text": "I'll help you rediscover some great games in your library. Let me check what you've been playing recently to avoid suggesting those..."
        }
    })
    
    # Add resource reference
    messages.append({
        "role": "user",
        "content": {
            "type": "resource",
            "resource": {
                "uri": "library://activity/recent",
                "text": "Check my recent activity first"
            }
        }
    })
    
    return messages
```

### 2. Plan Multiplayer Session Prompt

```python
@server.list_prompts()
async def handle_list_prompts():
    return [
        # ... previous prompts ...
        Prompt(
            name="plan_multiplayer_session",
            description="What can my friends and I play tonight?",
            arguments=[
                PromptArgument(
                    name="friend_count",
                    description="How many people will be playing?",
                    required=True
                ),
                PromptArgument(
                    name="session_length",
                    description="How long is your gaming session?",
                    required=False
                ),
                PromptArgument(
                    name="game_type",
                    description="Preferred type (co-op, competitive, casual)?",
                    required=False
                )
            ]
        )
    ]

async def plan_multiplayer_prompt(arguments: dict):
    """Help coordinate multiplayer gaming sessions"""
    
    friend_count = arguments["friend_count"]
    session_length = arguments.get("session_length", "2-3 hours")
    game_type = arguments.get("game_type", "any")
    
    messages = [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"I need help planning a gaming session for {friend_count} people. We have {session_length} to play. Game type preference: {game_type}."
            }
        },
        {
            "role": "assistant",
            "content": {
                "type": "text", 
                "text": "I'll find the perfect games for your group. Let me check what games you all have in common and what supports your player count..."
            }
        },
        {
            "role": "assistant",
            "content": {
                "type": "tool_use",
                "tool": "get_friends_data",
                "arguments": {
                    "data_type": "multiplayer_compatible"
                }
            }
        }
    ]
    
    return messages
```

### 3. Analyze Gaming Patterns Prompt

```python
@server.list_prompts()
async def handle_list_prompts():
    return [
        # ... previous prompts ...
        Prompt(
            name="analyze_gaming_patterns", 
            description="What kind of gamer am I?",
            arguments=[
                PromptArgument(
                    name="time_period",
                    description="Analyze patterns for what period? (e.g., 'all time', 'last year')",
                    required=False
                ),
                PromptArgument(
                    name="focus_area",
                    description="Specific aspect to analyze (genres, playtime, completion)?",
                    required=False
                )
            ]
        )
    ]

async def analyze_patterns_prompt(arguments: dict):
    """Provide insights into gaming habits"""
    
    time_period = arguments.get("time_period", "all time")
    focus_area = arguments.get("focus_area", "comprehensive")
    
    messages = [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"I want to understand my gaming patterns. Analyze my {time_period} gaming habits, focusing on {focus_area}."
            }
        },
        {
            "role": "assistant",
            "content": {
                "type": "text",
                "text": "I'll analyze your gaming patterns and provide insights into your habits. This will include your genre preferences, playtime patterns, and gaming tendencies..."
            }
        },
        {
            "role": "assistant", 
            "content": {
                "type": "tool_use",
                "tool": "get_library_stats",
                "arguments": {}
            }
        }
    ]
    
    return messages
```

## Initialization and Main Loop

```python
import asyncio
from mcp.server.stdio import stdio_server

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="steam-librarian",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

```python
# config.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///steam_library.db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# User configuration
DEFAULT_USER_ID = os.getenv("DEFAULT_STEAM_ID")

# Cache configuration
CACHE_TTL = 3600  # 1 hour
ENABLE_CACHE = True

# API configuration
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
```

## Installation

```bash
# Install dependencies
pip install mcp sqlalchemy

# Set environment variables
export DATABASE_URL="sqlite:///steam_library.db"
export DEFAULT_STEAM_ID="your_steam_id"

# Run the server
python steam_librarian_server.py
```

## Usage Examples

### Example 1: Finding Something to Play
```
User: "I'm bored, what should I play?"
Assistant: *checks recent activity*
Assistant: "You haven't touched Hollow Knight in 2 years, but based on your recent 
           Hades sessions, you might enjoy returning to it. It has similar tight 
           combat and progression systems."
```

### Example 2: Planning Game Night
```
User: "Planning game night with 3 friends"
Assistant: *analyzes friend libraries*
Assistant: "You all own Terraria but only Jake has played it - perfect for 
           discovery together! Also, everyone has Deep Rock Galactic with 
           good playtime, so you'd all be comfortable with it."
```

### Example 3: Self-Reflection
```
User: "Am I buying too many games?"
Assistant: *runs library analysis*
Assistant: "You have 47 unplayed games worth approximately $423, but you've 
           gotten 400 hours from just your top 5 games. Your cost per hour 
           of entertainment is actually quite good at $1.06/hour."
```

This implementation creates a focused, cohesive MCP server that helps users truly enjoy their existing Steam library through intelligent recommendations, social features, and insightful analysis.