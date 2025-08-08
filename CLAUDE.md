# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Steam Librarian is an intelligent MCP (Model Context Protocol) server that provides AI-powered access to Steam game library data. Built with the official MCP Python SDK (FastMCP), it offers natural language search, personalized recommendations, and comprehensive library insights through a simplified, consolidated architecture focused on personal gaming experiences.

## Key Commands

### Running the Servers
```bash
# Run the full MCP server (production mode, port 8000)
python src/mcp_server/run_server.py

# Run as module
python -m mcp_server.run_server

# Development mode with debug logging
DEBUG=true python src/mcp_server/run_server.py

# Run the tools-only MCP server (port 8001, better client compatibility)
python src/oops_all_tools/run_server.py
make run-tools  # Alternative using Makefile

# Development mode for tools-only server
DEBUG=true python src/oops_all_tools/run_server.py
make dev-tools  # Alternative using Makefile
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
make test-unit                    # Run unit tests
make test-integration             # Integration tests
make test-functional              # Functional tests for tools
make test-full                    # All tests (unit + functional + integration)

# MCP-specific testing:
make test-mcp-tools               # Test MCP tools compliance
make test-mcp-resources           # Test MCP resources
make test-mcp-prompts             # Test MCP prompts
make test-mcp-full                # Complete MCP test suite with report

# Tools-only server testing:
make test-tools                   # Test tools-only MCP server
make health-tools                 # Check tools-only server health
```

### Docker & Deployment
```bash
# Docker - Full server
make build-docker
make run-docker
make stop-docker
make rebuild-mcp-docker           # Rebuild MCP server without cache
make rebuild-all-docker           # Rebuild all containers without cache

# Docker - Tools-only server
make build-docker-tools           # Build tools-only Docker image
make run-both-servers             # Run both MCP servers
make stop-both-servers            # Stop both servers
make rebuild-tools-docker         # Rebuild tools server

# Kubernetes/Helm
make helm-lint                    # Lint Helm chart
make helm-validate                # Validate with kubeconform
make helm-install                 # Install single server
make helm-install-both            # Install both MCP servers
make helm-upgrade-both            # Upgrade both servers
make helm-uninstall               # Uninstall release
helm install steam-librarian deploy/helm/steam-librarian -f values-override.yaml

# Manual CronJob trigger in Kubernetes
kubectl create job --from=cronjob/steam-librarian-fetcher manual-fetch-$(date +%s)
```

## Architecture

### Core Components

1. **Full MCP Server (src/mcp_server/)** - Port 8000
   - `server.py`: FastMCP server instance with health endpoints
   - `run_server.py`: Production startup script with signal handling
   - `config.py`: Simple configuration with environment variables
   - `tools.py`: **Consolidated MCP tools** (all tools in single file)
   - `resources.py`: **Consolidated MCP resources** (all resources in single file)
   - `prompts.py`: **Consolidated MCP prompts** (all prompts in single file)
   - HTTP transport with streamable responses
   - Supports all MCP features: tools, resources, prompts, completions, elicitations, sampling

2. **Tools-Only Server (src/oops_all_tools/)** - Port 8001
   - **Purpose**: Maximum compatibility with Claude Desktop/Code clients
   - `server.py`: Simplified FastMCP server
   - `tools.py`: ~20 focused tools (all functionality via tools)
   - `prompts.py`: Simple usage examples
   - `config.py`: Minimal configuration
   - No resources, completions, elicitations, or sampling
   - Better compatibility with limited MCP clients

3. **Database (src/shared/database.py)**
   - SQLAlchemy models: UserProfile, Game, Genre, Developer, Publisher, Review, Friend, UserGame
   - SQLite database with proper relationships and indexes
   - **Critical insight**: Genres (15 broad types) vs Categories (53 specific features)
   - Personal library focus with default user handling

4. **Steam Data Fetcher (src/fetcher/)**
   - `steam_library_fetcher.py`: Fetches Steam library data via Steam Web API
   - Populates SQLite database with comprehensive game metadata

## Important Technical Notes

### Recent Architectural Changes
- **Dual-server architecture**: Added tools-only server alongside full MCP server for client compatibility
- **Simplified from modular to consolidated**: Tools, resources, and prompts moved from multiple modules to single files
- **Removed complex subsystems**: Cache, monitoring, services, enhanced user context, and error handling layers removed
- **Focus on core MCP features**: Tools, resources, prompts, with planned sampling, elicitation, and completions
- **Personal library emphasis**: All tools default to user's personal Steam library

### Server Compatibility Matrix
| Client | Full Server (8000) | Tools Server (8001) |
|--------|-------------------|---------------------|
| Claude Desktop | ⚠️ Partial | ✅ Full |
| Claude Code | ⚠️ Partial | ✅ Full |
| MCP-compatible tools | ✅ Full | ✅ Tools only |
| Custom integrations | ✅ Full | ✅ Tools only |

### Database Architecture Intelligence
**Critical Discovery**: Steam uses a two-tier classification system:

#### Genres (15 broad categories):
- **Indie** (608 games), **Action** (580), **Adventure** (433), **RPG** (250), **Strategy** (226), **Casual** (154)
- Use for high-level game type filtering

#### Categories (53 specific features):
- **Single-player** (973 games), **Family Sharing** (969), **Multi-player** (335), **Co-op** (200), **PvP** (127)
- Use for gameplay mode, accessibility, and safety filtering

#### Smart Filtering Strategy:
- **Family-friendly detection**: Genre "Casual" + Category "Family Sharing"
- **Multiplayer intelligence**: Distinguish Co-op (friendly) vs PvP (competitive) vs Online variants
- **Age-appropriate safety**: Prefer "Single-player", avoid "Multi-player" for young children

### Default User Handling
All personal library tools use this pattern:
```python
def get_default_user_fallback():
    """Fallback function to get default user from config"""
    if config.default_user and config.default_user != "default":
        return config.default_user
    return None

# In tools:
user_result = resolve_user_for_tool(user, get_default_user_fallback)
```

### MCP Tool Implementation Pattern
```python
@mcp.tool()
async def tool_name(param: str, user: str = None) -> str:
    """Tool description."""
    # Resolve user with default fallback
    user_result = resolve_user_for_tool(user, get_default_user_fallback)
    if "error" in user_result:
        return f"User error: {user_result['message']}"
    
    user_steam_id = user_result["steam_id"]
    
    # Database query with proper relationships
    with get_db() as session:
        # Query logic here
        pass
```

### MCP Resource Implementation Pattern
```python
@mcp.resource("library://path/{param}")
def resource_name(param: str) -> str:
    """Resource description."""
    try:
        with get_db() as session:
            # Query and return JSON string
            return json.dumps(data, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed: {str(e)}"})
```

### Code Style Configuration
- Black: line-length = 999999 (effectively disabled)
- Ruff: Comprehensive linting with specific rules (see pyproject.toml)
- Always run `make check` before committing

### Testing Strategy
- No pytest dependency - tests use standard unittest
- Test files can be run directly: `python tests/test_mcp_server.py`
- Integration tests start actual server instance
- Basic import test: `make test`

### Environment Variables
- `MCP_HOST`: Server host (default: "127.0.0.1")
- `MCP_PORT`: Server port (default: "8000")
- `DEFAULT_USER`: Default Steam user for personal library mode
- `DATABASE_URL`: Database connection string (default: "sqlite:///steam_library.db")
- `DEBUG`: Enable debug mode (default: false)
- `STEAM_ID`: Your Steam ID (required for fetcher)
- `STEAM_API_KEY`: Steam Web API key (required for fetcher)

### MCP Protocol Specifics
- Server name: "steam-librarian"
- Transport: HTTP with Server-Sent Events (SSE)
- Endpoints:
  - `/mcp` - MCP protocol endpoint
  - `/health` - Basic health check

### Enhancement Plan Status
- **✅ Phase 1 Complete**: Deprecated database fields fixed, default user handling verified, database architecture analyzed
- **🚀 Phase 2 Ready**: Enhanced personal library tools with genre/category intelligence
- **🎯 Future Features**: Age-appropriate games tool, advanced filtering, sampling/elicitation/completions integration

### Common Development Patterns

#### Adding New MCP Tools
1. Add to `src/mcp_server/tools.py`
2. Use `@mcp.tool()` decorator
3. Include user parameter with default fallback
4. Use `resolve_user_for_tool(user, get_default_user_fallback)`
5. Query database with proper relationship loading

#### Adding New MCP Resources
1. Add to `src/mcp_server/resources.py`
2. Use `@mcp.resource("uri://template")` decorator
3. Return JSON strings, not Python objects
4. Handle errors gracefully with JSON error responses

#### Database Queries
- Always use `with get_db() as session:` for automatic cleanup
- Load relationships with `joinedload()` for efficiency
- Use the genre vs category intelligence for smart filtering

### Key Files to Understand
- `src/mcp_server/tools.py` - All MCP tools for full server
- `src/mcp_server/resources.py` - All MCP resources for full server
- `src/oops_all_tools/tools.py` - ~20 focused tools for compatibility server
- `src/shared/database.py` - SQLAlchemy models and database utilities
- `ai_specs/mcp_enhancement_plan_v2.md` - Comprehensive enhancement roadmap
- `ai_specs/oops_all_tools_plan.md` - Tools-only server implementation plan

### Docker Database Access
```bash
# The database is in a Docker volume, access via container:
docker exec docker-mcp-server-1 python -c "
from src.shared.database import get_db, Genre
with get_db() as session:
    genres = session.query(Genre).all()
    print([g.genre_name for g in genres])
"
```

### Monitoring & Debugging
```bash
# Check server health
curl http://localhost:8000/health

# View Docker logs
docker logs docker-mcp-server-1

# Check running containers
docker ps
```