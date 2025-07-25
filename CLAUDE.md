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
python mcp_server.py

# Fetch fresh Steam library data (requires .env with STEAM_ID and STEAM_API_KEY)
python steam_library_fetcher.py
```

### Configuration
```bash
# Create configuration from example
cp claude_desktop_config.example.json claude_desktop_config.json
# Edit paths in claude_desktop_config.json to match your system
# Copy to Claude Desktop location (macOS): ~/Library/Application Support/Claude/claude_desktop_config.json
```

## Architecture & Structure

### Core Components

1. **mcp_server.py**: Fully functional MCP server with 8 Steam library tools
   - Uses SQLite database for data storage via SQLAlchemy
   - Converts playtime from minutes to hours for readability
   - Uses STDIO transport (not HTTP) for Claude Desktop integration
   - **CRITICAL**: Never print to stdout during operation as it breaks STDIO protocol

2. **steam_library_fetcher.py**: Steam API data fetcher
   - Fetches comprehensive game data from Steam API
   - Fetches user profile data including Steam level and XP
   - Requires `.env` file with `STEAM_ID` and `STEAM_API_KEY`
   - Stores data in SQLite database

3. **database.py**: SQLAlchemy models and database management
   - Defines relational data model for games, users, genres, reviews, etc.
   - Handles many-to-many relationships properly
   - Uses SQLite for efficient querying and data integrity

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

- **claude_desktop_config.example.json**: Template for users to customize
- **claude_desktop_config.json**: Personal config (gitignored)
- **.env**: Steam API credentials (gitignored)

## Important Development Notes

- **STDIO Protocol**: Never use `print()` statements in mcp_server.py as they interfere with Claude Desktop communication
- **Database**: Uses SQLite database (`steam_library.db`) with SQLAlchemy ORM
- **Error Handling**: Tools return empty lists/None for missing data rather than raising exceptions
- **Performance**: Database queries are optimized with proper indexes and relationships
- **User Profile**: Fetches Steam level, XP, and profile data from Steam's IPlayerService API

## Claude Desktop Integration

- Server name: "steam-library-mcp"
- Transport: STDIO (not HTTP/SSE)
- Config location (macOS): `~/Library/Application Support/Claude/claude_desktop_config.json`
- Requires restart of Claude Desktop after config changes