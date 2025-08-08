# Steam Librarian MCP Server - Technical Deep Dive

## Overview

The Steam Librarian MCP (Model Context Protocol) Server represents an ambitious implementation of the full MCP specification, providing AI-powered access to Steam game library data through a comprehensive set of tools, resources, prompts, and advanced features. This documentation covers both our full-featured server and the "Oops All Tools!" compatibility server designed for maximum client compatibility.

### The Dual-Server Architecture (v1.6.0+)

Steam Librarian now offers two distinct server implementations:

1. **Full-Featured MCP Server** (Port 8000) - This original implementation showcases the complete power of MCP
2. **"Oops All Tools!" Compatibility Server** (Port 8001) - A pragmatic reimplementation for real-world compatibility

#### The Evolution Story

When I first built Steam Librarian, the goal was to demonstrate MCP's full potential - sampling for natural language understanding, elicitation for interactive parameter gathering, completions for discoverability, resources for structured data access, and prompts for guided interactions. It was technically impressive and pedagogically valuable.

However, reality intervened. Even Anthropic's flagship applications (Claude Desktop and Claude Code) have limited MCP support:
- ✅ **Tools**: Fully supported and reliable
- ⚠️ **Resources**: Partially supported, inconsistent behavior
- ❌ **Completions**: Not implemented in most clients
- ❌ **Elicitations**: Not yet available
- ❌ **Sampling**: Limited or no support

This led to the creation of "Oops All Tools!" - a compatibility-focused server that reimplements all functionality using only tools, ensuring perfect compatibility with current MCP clients while maintaining feature parity.

## Server Comparison

### Full-Featured MCP Server (src/mcp_server/)
| Component | Implementation | Purpose |
|-----------|---------------|----------|
| **Tools** | 3 comprehensive AI-powered tools | Complex operations with rich responses |
| **Resources** | 13 URI-based endpoints | Direct data access and filtering |
| **Prompts** | 10 interactive templates | Guided conversations with embedded data |
| **Completions** | Database-driven suggestions | Parameter discovery and autocomplete |
| **Sampling** | AI interpretation layer | Natural language to structured queries |
| **Elicitation** | Interactive parameter gathering | Smart prompting for missing inputs |

### "Oops All Tools!" Server (src/oops_all_tools/)
| Component | Implementation | Purpose |
|-----------|---------------|----------|
| **Tools** | ~20 specialized tools | Each tool handles a specific use case |
| **Resources** | None (reimplemented as tools) | Data access via dedicated tools |
| **Prompts** | Simple usage examples | Basic guidance without templates |
| **Completions** | None | No autocomplete support |
| **Sampling** | None | Direct parameter passing only |
| **Elicitation** | None | All parameters required upfront |

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

### Full-Featured Server Structure
```
src/mcp_server/
├── server.py          # FastMCP server with HTTP transport
├── run_server.py      # Production startup script
├── config.py          # Environment-based configuration
├── tools.py           # 3 comprehensive MCP tools
├── resources.py       # 13 MCP resource endpoints
├── prompts.py         # 10 interactive prompt templates
└── completions.py     # Database-driven completions
```

### Compatibility Server Structure
```
src/oops_all_tools/
├── server.py          # Simplified FastMCP server
├── run_server.py      # Production startup script
├── config.py          # Minimal configuration
├── tools.py           # ~20 specialized tools
└── prompts.py         # Simple usage examples
```

### Shared Components
```
src/shared/
├── database.py        # SQLAlchemy models (both servers)
└── utils.py           # Common utilities
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

### Starting the Servers

#### Full-Featured Server (Port 8000)
```bash
# Production mode
python src/mcp_server/run_server.py

# Development mode with debug logging
DEBUG=true python src/mcp_server/run_server.py

# Module mode
python -m mcp_server.run_server
```

#### Compatibility Server (Port 8001)
```bash
# Production mode
python src/oops_all_tools/run_server.py

# Development mode
DEBUG=true python src/oops_all_tools/run_server.py

# Using Makefile
make run-tools         # Production
make dev-tools         # Development
```

### Running Both Servers Simultaneously
```bash
# Docker Compose (recommended)
make run-both-servers

# Or manually in separate terminals
python src/mcp_server/run_server.py &
python src/oops_all_tools/run_server.py &
```

### Health Endpoints
- **`/health`** - Basic health check
- **`/health/detailed`** - Detailed server status
- **`/mcp`** - MCP protocol endpoint

### Docker Usage
```bash
# Run full-featured server only
docker-compose up mcp-server

# Run compatibility server only
docker-compose up mcp-server-tools

# Run both servers
make run-both-servers

# With environment overrides
DEFAULT_USER=76561198020403796 docker-compose up

# Build images
make build-docker         # Full server
make build-docker-tools   # Compatibility server
```

## Tool Implementation Details

### Full-Featured Server Tools (3 Comprehensive)

#### 1. `smart_search`
- **Purpose**: Unified search with AI interpretation
- **Complexity**: High - handles multiple filter types, sorting algorithms
- **AI Features**: Natural language sampling, query interpretation
- **Response**: Rich, detailed game information with context

#### 2. `recommend_games`
- **Purpose**: Context-aware recommendations
- **Contexts**: family, quick_session, similar_to, mood_based, unplayed_gems, abandoned
- **AI Features**: Elicitation for missing parameters, mood interpretation
- **Response**: Curated lists with reasoning

#### 3. `get_library_insights`
- **Purpose**: Deep analytics and pattern analysis
- **Types**: patterns, value, social, achievements
- **AI Features**: Pattern recognition, personality insights
- **Response**: Comprehensive analytics with AI observations

### Compatibility Server Tools (~20 Specialized)

The "Oops All Tools!" server reimplements all functionality as discrete tools:

#### Search & Discovery Tools
- `search_games` - Basic game search with filters
- `search_by_genre` - Genre-specific search
- `search_by_tag` - Tag-based discovery
- `search_multiplayer` - Find multiplayer games
- `search_unplayed` - Discover unplayed games

#### Recommendation Tools
- `recommend_family_games` - Age-appropriate suggestions
- `recommend_quick_games` - Short session games
- `recommend_similar_games` - Games like your favorites
- `recommend_by_mood` - Mood-based selection
- `find_hidden_gems` - Unplayed quality games
- `find_abandoned_games` - Started but unfinished

#### Analytics Tools
- `get_library_stats` - Basic statistics
- `get_play_patterns` - Gaming habit analysis
- `get_genre_distribution` - Genre preferences
- `calculate_library_value` - Worth and cost analysis
- `compare_with_friends` - Social insights

#### Information Tools
- `get_user_info` - User profile data
- `get_game_details` - Detailed game information
- `get_recent_activity` - Recent play history
- `list_all_games` - Complete library list
- `list_users` - Available users

### Tool Migration Examples

**Full Server (single call):**
```python
smart_search("relaxing puzzle games", limit=10)
```

**Compatibility Server (specific tool):**
```python
search_by_tag("puzzle", mood="relaxing", limit=10)
```

## Tool Examples

### Full-Featured Server Examples

#### AI-Powered Smart Search
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

## Implementation Philosophy

### Full-Featured Server Design Principles

The full server follows MCP's vision of intelligent, context-aware interactions:

1. **Separation of Concerns**: Tools for actions, resources for data, prompts for guided experiences
2. **Progressive Enhancement**: Basic functionality works without advanced features
3. **AI-First Design**: Natural language is the primary interface
4. **Rich Context**: Every response includes metadata for better AI understanding

### "Oops All Tools!" Design Principles

The compatibility server embraces pragmatic simplicity:

1. **Single Interface**: Everything is a tool - no cognitive overhead
2. **Explicit Over Implicit**: Direct tool names instead of AI interpretation
3. **Predictable Behavior**: Each tool does one thing well
4. **Compatibility First**: Works everywhere, no exceptions

### Technical Trade-offs

| Aspect | Full Server | Compatibility Server |
|--------|-------------|---------------------|
| **API Surface** | Complex, feature-rich | Simple, predictable |
| **Learning Curve** | Steep | Gentle |
| **Flexibility** | High | Moderate |
| **Maintenance** | Complex | Simple |
| **Client Requirements** | Full MCP support | Basic tool support |
| **Response Time** | Variable (AI processing) | Consistent |
| **Error Handling** | Sophisticated | Straightforward |

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

### Current (v1.6.0) - "Oops All Tools!" Release
- **Dual-Server Architecture**: Added compatibility server alongside full server
- **20+ Specialized Tools**: Complete functionality reimplemented as tools-only
- **Maximum Compatibility**: Works perfectly with Claude Desktop/Code
- **Maintained Feature Parity**: All capabilities available in both servers
- **Port Separation**: Full server (8000), Compatibility server (8001)
- **Shared Database**: Both servers use the same SQLite backend

### v1.5.2 - Advanced MCP Features
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

## Choosing the Right Server

### Decision Matrix

| Use Case | Recommended Server | Reason |
|----------|-------------------|--------|
| **Claude Desktop/Code** | Compatibility (8001) | Full tool support, no compatibility issues |
| **Custom MCP Client** | Full-Featured (8000) | Access to all MCP features |
| **Production API** | Compatibility (8001) | Maximum reliability |
| **Development/Testing** | Full-Featured (8000) | Explore MCP capabilities |
| **Learning MCP** | Both | Compare implementations |

### Client Compatibility Guide

#### Known Working Configurations
- **Claude Desktop + Compatibility Server**: ✅ Perfect
- **Claude Code + Compatibility Server**: ✅ Perfect
- **Claude Desktop + Full Server**: ⚠️ Tools only work reliably
- **Custom Client + Full Server**: ✅ All features available

### Migration Path

If you're currently using the full server with limited success:

1. **Start the compatibility server:**
   ```bash
   python src/oops_all_tools/run_server.py
   ```

2. **Update your client configuration:**
   - Change port from 8000 to 8001
   - Update endpoint to `http://localhost:8001/mcp`

3. **Adjust your queries:**
   - Instead of relying on resources, use specific tool calls
   - Replace prompt templates with direct tool invocations

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

#### Both Servers
- **Empty tool responses**: Ensure user has games in library
- **User not found**: Check DEFAULT_USER environment variable
- **Database errors**: Verify database connection and schema
- **Missing data**: Run fetcher to populate game metadata

#### Full-Featured Server Specific
- **Resources not working in Claude**: Switch to compatibility server
- **Completions not appearing**: Client doesn't support this feature
- **Elicitation not triggering**: Use compatibility server instead

#### Compatibility Server Specific
- **"Tool not found" errors**: Tool names differ from full server
- **Missing advanced features**: This is by design for compatibility
- **Port conflicts**: Ensure port 8001 is available

### Debug Mode
```bash
# Full server debug
DEBUG=true python src/mcp_server/run_server.py

# Compatibility server debug
DEBUG=true python src/oops_all_tools/run_server.py

# Check MCP registration (full server)
curl http://localhost:8000/mcp -X POST \
  -d '{"method": "tools/list"}' | jq

# Check MCP registration (compatibility)
curl http://localhost:8001/mcp -X POST \
  -d '{"method": "tools/list"}' | jq
```

### Health Checks
```bash
# Full server
curl http://localhost:8000/health

# Compatibility server
curl http://localhost:8001/health
```

### Integration Testing
```python
# Test full server
python -c "
from mcp_server.tools import smart_search
result = smart_search('action games')
print(result)
"

# Test compatibility server
python -c "
from oops_all_tools.tools import search_games
result = search_games('action')
print(result)
"
```

### Performance Comparison

Run both servers and compare response times:
```bash
# Full server (complex query with AI)
time curl -X POST http://localhost:8000/mcp \
  -d '{"method": "tools/call", "params": {"name": "smart_search", "arguments": {"query": "relaxing games"}}}'

# Compatibility server (direct tool call)
time curl -X POST http://localhost:8001/mcp \
  -d '{"method": "tools/call", "params": {"name": "search_by_tag", "arguments": {"tag": "relaxing"}}}'
```