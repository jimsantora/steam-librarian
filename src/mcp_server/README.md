# Steam Librarian MCP Server

## Overview

The Steam Librarian MCP (Model Context Protocol) Server provides AI-powered access to Steam game library data through a comprehensive set of tools, resources, and prompts. Built with FastMCP, it offers natural language search, personalized recommendations, and detailed game insights through a simplified, consolidated architecture.

## Features

### 🛠️ MCP Tools
Three powerful AI-enhanced tools that showcase advanced MCP capabilities:

- **`smart_search`** - AI-powered unified search with natural language interpretation and intelligent filtering
- **`recommend_games`** - Context-aware recommendations with interactive elicitation for parameter gathering
- **`get_library_insights`** - Deep analytics with AI interpretation of gaming patterns and comprehensive insights

### 📊 MCP Resources
Structured data access for library exploration and simple filtering:

**Library Navigation:**
- **`library://overview`** - Library statistics and server status
- **`library://users`** - Available users in database
- **`library://users/{user_id}`** - User profile information
- **`library://users/{user_id}/games`** - User's game library
- **`library://users/{user_id}/stats`** - User gaming statistics

**Game Information:**
- **`library://games/{game_id}`** - Comprehensive game details with all metadata and user stats
  - Complete descriptions, release info, classification (genres/categories/tags)
  - Platform support, ratings (ESRB/PEGI), review statistics
  - User-specific data: playtime, achievements, ownership status
- **`library://games/platform/{platform}`** - Games by platform (windows, mac, linux, vr)
- **`library://games/multiplayer/{type}`** - Games by multiplayer type (coop, pvp, local, online)
- **`library://games/unplayed`** - Highly-rated unplayed games (metacritic ≥75)

**Classification & Discovery:**
- **`library://genres`** - Available game genres with counts
- **`library://genres/{genre_name}`** - Games by genre
- **`library://tags`** - Available user-generated tags with counts
- **`library://tags/{tag_name}`** - Games by community tag

### 💬 MCP Prompts
User-initiated conversation templates with embedded resources:

- **Find Family-Friendly Games** - Age-appropriate recommendations with customizable parameters
- **Quick Gaming Session** - Time-based game suggestions for short play sessions
- **Discover Unplayed Games** - Find unplayed gems with embedded resource data
- **Games Similar To Favorite** - Recommendations based on games you love
- **Natural Language Game Search** - AI-powered search using natural descriptions
- **Analyze Gaming Patterns** - Library insights with embedded overview data
- **Mood-Based Game Selection** - Emotional state matching for game recommendations
- **Find Abandoned Games** - Rediscover started but unfinished games
- **Explore Games by Genre** - Genre-specific exploration with embedded game lists
- **View User Profile & Stats** - Complete profile display with embedded user data

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
- **Advanced MCP Implementation**: Full use of sampling, elicitation, and completions for intelligent interaction
- **Consolidated Architecture**: All tools, resources, and prompts in single files
- **Embedded Resources**: Prompts leverage server-side data for rich conversation context
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

### AI-Powered Smart Search
```python
# Natural language interpretation with AI sampling
smart_search("family games for tonight")
# → AI interprets query and filters by family-friendly criteria

smart_search("something relaxing after work", filters='{"sort_by": "random"}')
# → Uses AI to map "relaxing" to appropriate genres and tags

smart_search("quick puzzle games", limit=5)
# → AI identifies puzzle games suitable for short sessions
```

### Context-Aware Recommendations
```python
# Interactive elicitation for family games
recommend_games("family", '{"age": 8}')
# → ESRB/PEGI appropriate games, uses elicitation if age not provided

# Mood-based recommendations with AI interpretation
recommend_games("mood_based", '{"mood": "relaxing"}')
# → AI maps emotional state to appropriate game characteristics

# Discover unplayed gems
recommend_games("unplayed_gems")
# → Analyzes play history to suggest owned but unplayed games
```

### Deep Library Analytics
```python
# AI-powered pattern analysis
get_library_insights("patterns")
# → AI interprets gaming habits and generates personality insights

# Value analysis with intelligent observations
get_library_insights("value")
# → Calculates cost-per-hour and identifies high-value games

# Social comparison insights
get_library_insights("social", compare_to="friends")
# → Analyzes library overlap and compatibility with friends
```

### Resource Access
```bash
# Get all available tags
curl "http://localhost:8000/mcp" -X POST \
  -d '{"method": "resources/read", "params": {"uri": "library://tags"}}'

# Find roguelike games  
curl "http://localhost:8000/mcp" -X POST \
  -d '{"method": "resources/read", "params": {"uri": "library://tags/roguelike"}}'

# Get VR games
curl "http://localhost:8000/mcp" -X POST \
  -d '{"method": "resources/read", "params": {"uri": "library://games/platform/vr"}}'

# Get cooperative games
curl "http://localhost:8000/mcp" -X POST \
  -d '{"method": "resources/read", "params": {"uri": "library://games/multiplayer/coop"}}'

# Get unplayed gems
curl "http://localhost:8000/mcp" -X POST \
  -d '{"method": "resources/read", "params": {"uri": "library://games/unplayed"}}'

# Get comprehensive game details (example: Team Fortress 2)
curl "http://localhost:8000/mcp" -X POST \
  -d '{"method": "resources/read", "params": {"uri": "library://games/440"}}'
```

## Advanced Features

### MCP Protocol Features
- **AI Sampling**: Natural language queries interpreted by AI into structured database filters
- **Interactive Elicitation**: Smart parameter gathering for missing or ambiguous user inputs
- **Database-Driven Completions**: Tab completion for parameters, contexts, and query patterns
- **Embedded Resources**: Prompts include actual library data for rich conversation context

### AI Integration
- **Context-Aware Recommendations**: Six specialized contexts (family, quick_session, similar_to, mood_based, unplayed_gems, abandoned)
- **Natural Language Processing**: Interpret complex gaming requests and emotional states
- **Pattern Analysis**: AI interpretation of gaming habits, preferences, and trends

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

### Current (v1.5.2)
- **Advanced MCP Implementation**: Full sampling, elicitation, and completions support
- **AI-Powered Tools**: Three consolidated tools with natural language processing
- **Embedded Resource Prompts**: User-initiated templates with actual library data
- **Context-Aware Recommendations**: Six specialized recommendation contexts
- **Pattern Analysis**: AI interpretation of gaming habits and preferences

### Previous (v1.5.0)
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