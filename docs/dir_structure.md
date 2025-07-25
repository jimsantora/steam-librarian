# Steam Librarian Directory Structure Recommendations

## Current Structure Analysis

The project currently has a flat structure with all Python files in the root directory:
- `mcp_server.py` (837 lines) - Main MCP server with 8 Steam library tools
- `steam_library_fetcher.py` (816 lines) - Steam API data fetcher
- `database.py` (247 lines) - SQLAlchemy models and database management
- `migrate_csv_to_sqlite.py` (280 lines) - Migration utility

## Recommended Directory Structure

```
steam-librarian/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py          # Database connection and session management
│   │   └── config.py            # Configuration management (env vars, settings)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── game.py              # Game, Genre, Developer, Publisher models
│   │   ├── user.py              # UserProfile, UserGame models
│   │   └── review.py            # GameReview model
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── steam_client.py      # Steam API client class
│   │   └── fetcher.py           # Data fetching logic
│   │
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py            # Main MCP server
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── search.py        # search_games, filter_games tools
│   │   │   ├── details.py       # get_game_details, get_game_reviews tools
│   │   │   ├── stats.py         # get_library_stats tool
│   │   │   ├── recommendations.py # get_recommendations tool
│   │   │   └── user.py          # get_user_info, get_recently_played tools
│   │   └── prompts/
│   │       ├── __init__.py
│   │       └── user_selection.py # User selection prompt
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py           # Shared utility functions
│
├── scripts/
│   ├── __init__.py
│   ├── fetch_steam_data.py     # Renamed from steam_library_fetcher.py
│   └── migrate_csv_to_sqlite.py
│
├── config/
│   ├── claude_desktop_config.example.json
│   └── .env.example
│
├── docs/
│   ├── database-schema.md
│   └── api-reference.md         # Document the MCP tools
│
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_api.py
│   └── test_mcp_tools.py
│
├── .gitignore
├── .python-version
├── requirements.txt
├── setup.py                     # For package installation
├── README.md
└── CLAUDE.md
```

## File Splitting Recommendations

### 1. Split `database.py` into:
- **`src/core/database.py`**: Database connection, engine, session management
- **`src/models/`**: Separate files for each model group:
  - `game.py`: Game, Genre, Developer, Publisher, Category models
  - `user.py`: UserProfile, UserGame, friends_association
  - `review.py`: GameReview model

### 2. Split `mcp_server.py` into:
- **`src/mcp/server.py`**: Main FastMCP server setup and initialization
- **`src/mcp/tools/`**: Each tool category in its own file:
  - `search.py`: search_games, filter_games
  - `details.py`: get_game_details, get_game_reviews
  - `stats.py`: get_library_stats
  - `recommendations.py`: get_recommendations
  - `user.py`: get_user_info, get_recently_played, get_all_users
- **`src/mcp/prompts/user_selection.py`**: User selection prompt

### 3. Split `steam_library_fetcher.py` into:
- **`src/api/steam_client.py`**: SteamLibraryFetcher class with API methods
- **`src/api/fetcher.py`**: High-level fetching logic and orchestration
- **`scripts/fetch_steam_data.py`**: CLI entry point

### 4. Create new files:
- **`src/core/config.py`**: Centralized configuration management
- **`src/utils/helpers.py`**: Shared utilities (e.g., time formatting, data conversion)
- **`setup.py`**: Package setup for proper imports

## Benefits of This Structure

1. **Modularity**: Each component has a clear responsibility
2. **Scalability**: Easy to add new tools, models, or API integrations
3. **Testability**: Clear separation makes unit testing easier
4. **Maintainability**: Related code is grouped together
5. **Import Management**: Cleaner imports with package structure
6. **Separation of Concerns**: Business logic, data models, and API are separated

## Migration Strategy

1. Create the new directory structure
2. Move code into appropriate modules, updating imports
3. Create `__init__.py` files to expose public APIs
4. Update the main entry points (`scripts/`)
5. Test all functionality
6. Update documentation and configuration examples

## Additional Recommendations

1. **Add Type Hints**: The code already uses some type hints, but could benefit from more comprehensive typing
2. **Create Abstract Base Classes**: For tools and API clients to ensure consistency
3. **Add Logging Configuration**: Centralize logging setup in `src/core/config.py`
4. **Environment Management**: Use a Config class to manage all environment variables
5. **Error Handling**: Create custom exception classes in `src/core/exceptions.py`

This structure follows Python best practices and makes the codebase more professional and maintainable while preserving all existing functionality.