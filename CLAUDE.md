# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a fully functional Steam Library MCP (Model Context Protocol) server that provides access to Steam game library data through an HTTP interface. The project is built using FastMCP and provides 10 tools for interacting with Steam library data, including multi-user support and social features.

## Key Commands

### Running the Server
```bash
# Install dependencies
pip install -r requirements.txt

# Run the MCP server (uses HTTP transport)
python src/mcp_server/mcp_server.py

# Fetch fresh Steam library data (requires .env with STEAM_ID and STEAM_API_KEY)
python src/fetcher/steam_library_fetcher.py

# Fetch including friends data
python src/fetcher/steam_library_fetcher.py --friends
```

### Development Commands
```bash
# Run linting
make lint
# or directly: ruff check src

# Check code formatting
make format-check
# or directly: black --check --diff src

# Format code
make format
# or directly: black src

# Run all checks (lint, format-check, basic import test)
make check

# Run basic import test
make test

# Clean up cache files
make clean
```

### Environment Configuration
```bash
# Create .env file for Steam API credentials
cp .env.example .env
# Edit .env with your STEAM_ID and STEAM_API_KEY
```

## Architecture & Structure

### Project Layout
```
steam-librarian/
├── src/                         # All source code
│   ├── fetcher/                # Steam data fetching service
│   │   └── steam_library_fetcher.py
│   ├── mcp_server/             # MCP server implementation
│   │   └── mcp_server.py
│   └── shared/                 # Shared code between services
│       └── database.py         # SQLAlchemy models & DB utilities
├── deploy/                     # Deployment configurations
│   ├── docker/                # Docker images and compose
│   └── helm/                  # Kubernetes Helm charts
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Black & Ruff configuration
└── Makefile                  # Development & deployment commands
```

### Core Components

1. **src/mcp_server/mcp_server.py**: Fully functional MCP server with 10 Steam library tools
   - Uses SQLite database for data storage via SQLAlchemy
   - Converts playtime from minutes to hours for readability
   - Uses HTTP transport with streamable responses
   - Provides RESTful endpoints for MCP tools

2. **src/fetcher/steam_library_fetcher.py**: Steam API data fetcher
   - Fetches comprehensive game data from Steam API
   - Fetches user profile data including Steam level and XP
   - Supports `--friends` flag to fetch friends and social data
   - Requires `.env` file with `STEAM_ID` and `STEAM_API_KEY`
   - Stores data in SQLite database

3. **src/shared/database.py**: SQLAlchemy models and database management
   - Defines relational data model for games, users, genres, reviews, friends
   - Handles many-to-many relationships properly
   - Uses SQLite for efficient querying and data integrity
   - Models: User, Game, Genre, Developer, Publisher, Review, Friend, UserGame

### Implemented MCP Tools

1. **get_all_users**: List all available user profiles in the database
2. **search_games**: Case-insensitive partial search across name, genres, developers, publishers
3. **filter_games**: Filter by playtime range, review summary, maturity rating
4. **get_game_details**: Get full game details by name or appid (supports partial matching)
5. **get_game_reviews**: Get review statistics including calculated positive percentage
6. **get_library_stats**: Structured dict with totals, top genres/developers, review distribution
7. **get_recently_played**: Games with playtime_2weeks > 0, sorted by recent playtime
8. **get_recommendations**: Personalized suggestions with reasons based on favorite genres/developers
9. **get_user_info**: Get comprehensive user profile including:
   - Basic info (persona_name, steam_id, profile_url)
   - Steam level and XP
   - Account age (calculated from time_created)
   - Location (country/state if public)
   - Avatar URLs (small, medium, large)
   - Library stats (total games, total playtime hours)
10. **get_friends_data**: Access friends lists, common games between users, and social features

### Configuration Files

- **.env.example**: Template for Steam API credentials
- **.env**: Steam API credentials (gitignored)

## Important Development Notes

- **HTTP Protocol**: Server provides HTTP endpoints for MCP tool invocation
- **Database**: Uses SQLite database (`steam_library.db`) with SQLAlchemy ORM
- **Error Handling**: Tools return empty lists/None for missing data rather than raising exceptions
- **Performance**: Database queries are optimized with proper indexes and relationships
- **User Profile**: Fetches Steam level, XP, and profile data from Steam's IPlayerService API
- **Multi-User**: Supports multiple Steam users in same database; tools accept optional `user_id` parameter
- **Code Style**: Uses Black (line-length 999999) and Ruff for linting (see pyproject.toml)

## MCP Server Integration

- Server name: "steam-librarian"
- Transport: HTTP (streamable responses)
- Default port: 8000 (configurable)
- MCP endpoint: `http://0.0.0.0:8000/mcp`
- Health check endpoint: `http://0.0.0.0:8000/health`

## Deployment Options

- **Docker**: Use `make build-docker` and `make run-docker` for containerized deployment
- **Kubernetes**: Helm chart available in `deploy/helm/steam-librarian/`
- **Local**: Direct Python execution for development

## Testing Approach

- No traditional unit tests; uses basic import verification via `make test`
- Manual testing recommended through HTTP client or curl commands
- Use `make check` to run all code quality checks before committing
- Test endpoints: `curl http://localhost:8000/health`

## Manual Data Fetching

Since there's no startup job, you need to manually trigger data fetching:
- **Option 1**: Wait for the CronJob to run (daily at 2 AM)
- **Option 2**: Manually trigger the CronJob:
  ```bash
  kubectl create job --from=cronjob/steam-librarian-fetcher manual-fetch-$(date +%s)
  ```
- **Option 3**: Run the fetcher locally before deployment