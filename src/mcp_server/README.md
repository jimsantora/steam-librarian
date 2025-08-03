# Steam Librarian MCP Server

## Overview

The Steam Librarian MCP (Model Context Protocol) Server provides AI-powered access to Steam game library data through a comprehensive set of tools, resources, and prompts. Built with FastMCP, it offers natural language search, personalized recommendations, and detailed game insights through a simplified, consolidated architecture.

## Features

### 🛠️ MCP Tools
Intelligent tools for game discovery and library analysis:

- **`search_games`** - Natural language game search with smart mappings
- **`analyze_library`** - Comprehensive library statistics and insights  
- **`get_game_details`** - Detailed game information with user stats
- **`find_family_games`** - Age-appropriate games with ESRB/PEGI filtering
- **`find_unplayed_gems`** - Highly-rated games in backlog
- **`find_multiplayer_games`** - Games by multiplayer type (coop, pvp, local, online)
- **`find_games_by_platform`** - Platform-specific games (Windows, Mac, Linux, VR)
- **`find_quick_session_games`** - Games perfect for quick gaming sessions (5-60 minutes)
- **`generate_recommendation`** - LLM-powered game recommendations
- **`find_games_with_preferences`** - Interactive preference-based discovery

### 📊 MCP Resources
Structured data access for library exploration:

- **`library://overview`** - Library statistics and server status
- **`library://users`** - Available users in database
- **`library://users/{user_id}`** - User profile information
- **`library://users/{user_id}/games`** - User's game library
- **`library://users/{user_id}/stats`** - User gaming statistics
- **`library://games/{game_id}`** - Detailed game information
- **`library://genres`** - Available game genres with counts
- **`library://genres/{genre_name}`** - Games by genre
- **`library://tags`** - Available user-generated tags with counts
- **`library://tags/{tag_name}`** - Games by community tag

### 💬 MCP Prompts
Pre-built conversation starters:

- **Gaming Session Planner** - Get personalized game recommendations
- **Library Analysis** - Analyze gaming habits and preferences
- **Game Discovery** - Find new games based on mood and time
- **Multiplayer Game Finder** - Find games to play with friends
- **Game Completion Helper** - Get help completing specific games

## Architecture

### Simplified Structure
```
src/mcp_server/
├── server.py          # FastMCP server with HTTP transport
├── run_server.py      # Production startup script
├── config.py          # Environment-based configuration
├── tools.py           # All MCP tools (consolidated)
├── resources.py       # All MCP resources (consolidated)
├── prompts.py         # All MCP prompts (consolidated)
└── completions.py     # Intelligent argument completions
```

### Key Design Principles
- **Consolidated Architecture**: All tools, resources, and prompts in single files
- **Personal Library Focus**: Default user handling for single-user scenarios
- **Rich Game Intelligence**: Uses genres, categories, and user-generated tags
- **Database-First**: Direct SQLAlchemy ORM queries for performance
- **Error Resilience**: Graceful handling of missing users or data

## Database Intelligence

### Advanced Game Classification
The server leverages multiple data sources for intelligent game discovery:

#### Official Steam Data
- **Genres** (15 types): Action, Adventure, RPG, Strategy, Casual, Indie, etc.
- **Categories** (53 features): Single-player, Multi-player, Co-op, Family Sharing, etc.
- **ESRB/PEGI Ratings**: Age-appropriate content filtering

#### Community Data
- **User Tags**: Community-driven tags like "Roguelike", "Hero Shooter", "Class-Based"
- **Superior Classification**: Tags provide gameplay style insights beyond official categories
- **Popular Tags**: "Atmospheric", "Story Rich", "Great Soundtrack", "Puzzle", "Card Game"

### Smart Query Processing
```python
# Example: Family game detection
Genre: "Casual" + Category: "Family Sharing" = Family-friendly games

# Example: Short session games  
Tags: "Arcade", "Puzzle", "Card Game" = Quick gaming sessions

# Example: Multiplayer intelligence
Category: "Co-op" vs "PvP" = Cooperative vs competitive experiences
```

## Configuration

### Environment Variables
- `MCP_HOST`: Server host (default: "127.0.0.1")
- `MCP_PORT`: Server port (default: "8000") 
- `DEFAULT_USER`: Default Steam user for personal library mode
- `DATABASE_URL`: Database connection string (default: "sqlite:///steam_library.db")
- `DEBUG`: Enable debug mode (default: false)

### Default User Handling
All tools support automatic user resolution:
```python
# Try provided user parameter
# Fall back to single user in database  
# Use DEFAULT_USER environment variable
# Return helpful error if multiple users exist
```

## Usage

### Starting the Server
```bash
# Production mode
python src/mcp_server/run_server.py

# Development mode with debug logging
DEBUG=true python src/mcp_server/run_server.py

# Module mode
python -m mcp_server.run_server
```

### Health Endpoints
- **`/health`** - Basic health check
- **`/health/detailed`** - Detailed server status
- **`/mcp`** - MCP protocol endpoint

### Docker Usage
```bash
# Via Docker Compose
docker-compose up mcp-server

# With environment overrides
DEFAULT_USER=76561198020403796 docker-compose up mcp-server
```

## Tool Examples

### Natural Language Search
```python
# Smart query interpretation
search_games("family games") 
# → Filters by Genre: "Casual" + Category: "Family Sharing"

search_games("something relaxing after work")
# → Uses AI to interpret and suggest calming games

search_games("coop games")
# → Filters by Category: "Co-op" or "Multi-player"
```

### Intelligent Recommendations
```python
# Age-appropriate filtering
find_family_games(child_age=8)
# → ESRB ≤ E, PEGI ≤ 7, Family Sharing category

# Platform-specific discovery
find_games_by_platform("vr")
# → Games with VR support detected from categories

# Backlog management
find_unplayed_gems(min_rating=80)
# → Unplayed games with Metacritic ≥ 80

# Quick session gaming
find_quick_session_games(session_length="short")
# → Games perfect for 5-15 minute sessions using community tags
# → Mix of played games (85%) and unplayed gems with good reviews (15%)
# → Shows 🔥 recently played, ⭐ favorites, 🆕 unplayed gems (75%+ reviews)
```

### Resource Access
```bash
# Get all available tags
curl "http://localhost:8000/mcp" -X POST \
  -d '{"method": "resources/read", "params": {"uri": "library://tags"}}'

# Find roguelike games  
curl "http://localhost:8000/mcp" -X POST \
  -d '{"method": "resources/read", "params": {"uri": "library://tags/roguelike"}}'
```

## Advanced Features

### AI Integration
- **LLM Sampling**: Generate contextual game recommendations
- **Natural Language Processing**: Interpret complex gaming requests
- **Interactive Elicitation**: Collect user preferences for personalized results

### Intelligent Completions
- **Game Name Completions**: Autocomplete with popular Steam games
- **Genre Suggestions**: Valid genre names for filtering
- **User Completions**: Available users with persona names

### Error Handling
- **Graceful Degradation**: Continue operation when data is missing
- **User Resolution**: Helpful error messages for user identification
- **Fallback Behavior**: Default to available data when queries fail

## Testing

### Running Tests
```bash
# Run basic import tests (fastest)
make test

# Run comprehensive unit tests
make test-unit

# Run integration tests (starts test server)
make test-integration

# Run all tests (unit + integration)
make test-full

# Run all code quality checks + comprehensive tests
make check-full
```

### Test Coverage
- **Unit Tests**: All critical modules, tools, and database models
- **Integration Tests**: Server startup, health endpoints, MCP protocol
- **Quality Assurance**: Linting (ruff), formatting (black), code validation

## Performance Characteristics

### Optimized Database Access
- **Relationship Loading**: Efficient `joinedload()` for related data
- **Indexed Queries**: Optimized searches on common fields
- **Session Management**: Proper connection pooling and cleanup

### Caching Strategy
- **In-Memory**: SQLAlchemy relationship caching
- **Database-Level**: Indexed lookups for frequent queries
- **Application-Level**: Reused database sessions where appropriate

## Version History

### Current (v1.1.3+)
- **User-Generated Tags**: Community tag extraction and resources
- **Consolidated Architecture**: Simplified module structure
- **Enhanced Game Intelligence**: Multi-source classification system
- **Personal Library Focus**: Default user handling
- **Rich Metadata**: ESRB/PEGI ratings, platform support, accessibility features

### Previous Versions
- **v1.1.2**: Initial MCP implementation with modular architecture
- **v1.1.1**: Basic tools and resources for game discovery
- **v1.1.0**: Core Steam library integration

## Best Practices

### Tool Implementation
- Always use `resolve_user_for_tool()` for user parameter handling
- Include helpful error messages with suggested actions
- Leverage database relationships for efficient queries
- Provide rich context in tool responses

### Resource Design
- Return structured JSON with consistent error handling
- Include metadata like counts and totals
- Support both exact and partial matching for user convenience
- Maintain consistent URI patterns

### Performance Optimization
- Use `joinedload()` for related data to avoid N+1 queries
- Limit results appropriately (typically 10-20 items)
- Sort results by relevance (playtime, ratings, popularity)
- Cache expensive computations where possible

## Troubleshooting

### Common Issues
- **Empty tool responses**: Ensure user has games in library
- **User not found**: Check DEFAULT_USER environment variable
- **Database errors**: Verify database connection and schema
- **Missing data**: Run fetcher to populate game metadata

### Debug Mode
```bash
# Enable detailed logging
DEBUG=true python src/mcp_server/run_server.py

# Check MCP registration
curl http://localhost:8000/mcp -X POST \
  -d '{"method": "tools/list"}' | jq
```

### Integration Testing
```python
# Test basic tool functionality
python -c "
from mcp_server.tools import search_games
result = search_games('action games')
print(result)
"
```