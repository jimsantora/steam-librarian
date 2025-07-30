# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Steam Librarian is an intelligent MCP (Model Context Protocol) server that provides AI-powered access to Steam game library data. Built with the official MCP Python SDK (FastMCP), it offers natural language search, personalized recommendations, social gaming analytics, and comprehensive library insights through 10 MCP tools.

## Key Commands

### Running the Server
```bash
# Run the MCP server (production mode)
python src/mcp_server/run_server.py

# Development mode with debug logging
DEBUG=true LOG_LEVEL=DEBUG python src/mcp_server/run_server.py

# Monitor server health and status
python src/mcp_server/monitor.py
```

### Data Fetching
```bash
# Fetch Steam library data (requires .env with STEAM_ID and STEAM_API_KEY)
python src/fetcher/steam_library_fetcher.py

# Fetch including friends data
python src/fetcher/steam_library_fetcher.py --friends
```

### Development & Testing
```bash
# Run ALL code quality checks before committing
make check

# Individual commands:
ruff check src                    # Linting
black src                         # Format code
make test                         # Basic import test
make test-unit                    # Run 52+ unit tests
make test-integration             # Integration tests
make test-full                    # All tests
```

### Docker & Deployment
```bash
# Docker
make build-docker
make run-docker

# Kubernetes/Helm
make helm-lint
make helm-validate
helm install steam-librarian deploy/helm/steam-librarian -f values-override.yaml

# Manual CronJob trigger in Kubernetes
kubectl create job --from=cronjob/steam-librarian-fetcher manual-fetch-$(date +%s)
```

## Architecture

### Core Components

1. **MCP Server (src/mcp_server/)**
   - `server.py`: FastMCP server instance with health endpoints
   - `run_server.py`: Production startup script with signal handling
   - `config.py`: Configuration management with validation
   - `cache.py`: Smart in-memory caching with TTL
   - `user_context.py`: Multi-user context resolution
   - HTTP transport on port 8000 with streamable responses

2. **MCP Tools (src/mcp_server/tools/)**
   - Advanced AI tools: `search_games`, `filter_games`, `get_recommendations`, `get_friends_data`, `get_library_stats`
   - Utility tools: `get_all_users`, `get_user_info`, `get_game_details`, `get_game_reviews`, `get_recently_played`
   - All tools use `@mcp.tool()` decorator from FastMCP

3. **MCP Resources (src/mcp_server/resources/)**
   - Library resources: game details, genre browsing, overview, recent activity
   - Social resources: friends overview, common games, compatibility scores
   - Insight resources: gaming patterns, personalized insights
   - Resources use `@mcp.resource()` decorator with URI templates

4. **MCP Prompts (src/mcp_server/prompts/)**
   - Library prompts: game discovery, mood-based suggestions
   - Social prompts: multiplayer recommendations, friend activity
   - Insight prompts: library analysis, gaming patterns

5. **Database (src/shared/database.py)**
   - SQLAlchemy models: UserProfile, Game, Genre, Developer, Publisher, Review, Friend, UserGame
   - SQLite database with proper relationships and indexes
   - Connection pooling and session management

## Important Technical Notes

### Event Loop Management
Resource templates require careful async/sync handling:
```python
@mcp.resource("library://games/{app_id}")
def game_details(app_id: str) -> str:
    import asyncio
    
    async def _get_game_details():
        # Async logic here
        return json.dumps(details, indent=2)
    
    # Proper event loop handling
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_game_details())
                return future.result()
        else:
            return loop.run_until_complete(_get_game_details())
    except RuntimeError:
        return asyncio.run(_get_game_details())
```

### Code Style Configuration
- Black: line-length = 999999 (effectively disabled)
- Ruff: Comprehensive linting with specific rules (see pyproject.toml)
- Always run `make check` before committing

### Testing Strategy
- No pytest dependency - tests use standard unittest
- Test files can be run directly: `python tests/test_mcp_server.py`
- Integration tests start actual server instance
- Mock Steam API responses for consistent testing

### Environment Variables
- `STEAM_ID`: Your Steam ID (required for fetcher)
- `STEAM_API_KEY`: Steam Web API key (required for fetcher)
- `DEBUG`: Enable debug mode (optional)
- `LOG_LEVEL`: Set logging level (optional)
- `CACHE_TTL`: Default cache TTL in seconds (optional)
- `CACHE_MAX_SIZE`: Maximum cache entries (optional)

### MCP Protocol Specifics
- Server name: "steam-librarian"
- Transport: HTTP with Server-Sent Events (SSE)
- Endpoints:
  - `/mcp` - MCP protocol endpoint
  - `/health` - Basic health check
  - `/health/detailed` - Component status
  - `/metrics` - Server metrics
  - `/config` - Configuration info

### Common Pitfalls to Avoid
1. Don't use async functions in resource utility functions - convert to sync
2. Always handle missing database gracefully (tools return empty results)
3. Use proper cache keys with user context for multi-user support
4. Resource templates must return JSON strings, not Python objects
5. Docker container needs rebuild after significant code changes

## Monitoring & Debugging

```bash
# Check server health
curl http://localhost:8000/health

# Detailed component status
curl http://localhost:8000/health/detailed

# Server metrics
curl http://localhost:8000/metrics

# View Docker logs
docker logs steam-librarian-mcp-server

# Interactive monitoring
python src/mcp_server/monitor.py
```