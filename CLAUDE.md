# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a fully functional Steam Library MCP (Model Context Protocol) server that provides access to Steam game library data through Claude Desktop. The project is built using FastMCP and provides 8 tools for interacting with Steam library data.

## Key Commands

### Running the Server
```bash
# Install dependencies
pip install -r requirements.txt

# Run the MCP server (uses STDIO transport for Claude Desktop)
python run_mcp_server.py
# Or: python -m src.mcp.server

# Fetch fresh Steam library data (requires .env with STEAM_ID and STEAM_API_KEY)
python run_fetcher.py
# Or: python scripts/fetch_steam_data.py
```

### Configuration
```bash
# Create configuration from example
cp config/claude_desktop_config.example.json claude_desktop_config.json
# Edit paths in claude_desktop_config.json to match your system
# Copy to Claude Desktop location (macOS): ~/Library/Application Support/Claude/claude_desktop_config.json
```

## Architecture & Structure

### Project Structure
```
src/
├── core/           # Core functionality (database, config)
├── models/         # SQLAlchemy models
├── api/            # Steam API client and data fetching
├── mcp/            # MCP server and tools
│   ├── tools/      # Individual MCP tool implementations
│   └── prompts/    # MCP prompts
└── utils/          # Shared utilities

scripts/            # CLI entry points
config/             # Configuration examples
```

### Core Components

1. **src/mcp/server.py**: Main MCP server setup
   - Registers all tools and prompts
   - Uses STDIO transport for Claude Desktop integration
   - **CRITICAL**: Never print to stdout during operation as it breaks STDIO protocol

2. **src/api/**: Steam API integration
   - `steam_client.py`: Low-level Steam API client
   - `fetcher.py`: High-level data orchestration
   - Fetches game data, user profiles, friends, and reviews

3. **src/models/**: SQLAlchemy data models
   - `game.py`: Game, Genre, Developer, Publisher, Category models
   - `user.py`: UserProfile, UserGame models
   - `review.py`: GameReview model
   - Handles many-to-many relationships properly

4. **src/mcp/tools/**: MCP tool implementations
   - `search.py`: search_games, filter_games
   - `details.py`: get_game_details, get_game_reviews
   - `stats.py`: get_library_stats
   - `recommendations.py`: get_recommendations
   - `user.py`: get_user_info, get_recently_played, get_friends_data

### Implemented MCP Tools

1. **search_games**: Case-insensitive partial search across name, genres, developers, publishers
2. **filter_games**: Filter by playtime range, review summary, maturity rating
3. **get_game_details**: Get full game details by name or appid (supports partial matching)
4. **get_game_reviews**: Get review statistics including calculated positive percentage
5. **get_library_stats**: Structured dict with totals, top genres/developers, review distribution
6. **get_recently_played**: Games with playtime_2weeks > 0, sorted by recent playtime
7. **get_recommendations**: Personalized suggestions with reasons based on favorite genres/developers
8. **get_user_info**: Get comprehensive user profile including:
   - Basic info (persona_name, steam_id, profile_url)
   - Steam level and XP
   - Account age (calculated from time_created)
   - Location (country/state if public)
   - Avatar URLs (small, medium, large)
   - Library stats (total games, total playtime hours)

### Configuration Files

- **config/claude_desktop_config.example.json**: Template for users to customize
- **claude_desktop_config.json**: Personal config (gitignored)
- **.env**: Steam API credentials (gitignored)
- **src/core/config.py**: Centralized configuration management

## Important Development Notes

- **STDIO Protocol**: Never use `print()` statements in src/mcp/server.py or any MCP tools as they interfere with Claude Desktop communication
- **Database**: Uses SQLite database (`steam_library.db`) with SQLAlchemy ORM
- **Error Handling**: Tools return empty lists/None for missing data rather than raising exceptions
- **Performance**: Database queries are optimized with proper indexes and relationships
- **User Profile**: Fetches Steam level, XP, and profile data from Steam's IPlayerService API

## Claude Desktop Integration

- Server name: "steam-library-mcp"
- Transport: STDIO (not HTTP/SSE)
- Config location (macOS): `~/Library/Application Support/Claude/claude_desktop_config.json`
- Requires restart of Claude Desktop after config changes