# Steam Librarian MCP Server

A powerful Model Context Protocol (MCP) server built with FastMCP that provides intelligent access to Steam game library data through natural language processing and advanced gaming analytics.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Tools](#tools)
- [API Endpoints](#api-endpoints)
- [Running the Server](#running-the-server)
- [Testing](#testing)
- [Monitoring](#monitoring)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Overview

The Steam Librarian MCP Server is a complete rewrite of the original server, migrating from stdio-based communication to HTTP streaming using FastMCP. This server provides sophisticated tools for searching, filtering, analyzing, and getting recommendations from Steam game libraries.

### Key Improvements

- **HTTP Streaming**: Uses FastMCP for HTTP-based communication instead of stdio
- **Enhanced Configuration**: Comprehensive settings management with validation
- **Health Monitoring**: Built-in health checks and metrics endpoints
- **Smart Caching**: Intelligent caching with TTL and invalidation
- **Natural Language Processing**: Advanced search with mood detection and context understanding
- **Multi-user Support**: Seamless handling of multiple Steam users
- **Production Ready**: Graceful shutdown, signal handling, and monitoring tools

## Architecture

```
src/mcp_server/
├── server.py              # Main FastMCP server with health endpoints
├── config.py              # Configuration management and validation
├── cache.py               # Smart caching system
├── errors.py              # Error handling framework
├── user_context.py        # Multi-user context resolution
├── validation.py          # Input validation schemas
├── run_server.py          # Production server startup script
├── monitor.py             # Monitoring and administration tool
├── tools/                 # MCP tools implementation
│   ├── __init__.py
│   ├── search_games.py    # Natural language game search
│   ├── filter_games.py    # Advanced filtering with presets
│   ├── get_recommendations.py  # Intelligent recommendations
│   ├── get_friends_data.py     # Social gaming features
│   └── get_library_stats.py    # Comprehensive analytics
├── utils/                 # Utility functions
│   ├── library_stats.py
│   ├── game_details.py
│   └── activity.py
├── resources/             # MCP resources (pending FastMCP support)
└── prompts/               # MCP prompts (pending FastMCP support)
```

## Features

### Advanced Gaming Tools

1. **Natural Language Search** - Search games using natural language queries
2. **Smart Filtering** - Filter games with intelligent presets and custom criteria
3. **Personalized Recommendations** - Get game recommendations based on your preferences
4. **Social Gaming** - Analyze friends' libraries and find common games
5. **Library Analytics** - Comprehensive statistics and insights about your gaming habits

### Technical Features

- **FastMCP Framework** - HTTP streaming protocol for better performance
- **Multi-user Context** - Automatic user resolution with intelligent fallbacks
- **Smart Caching** - Memory-based caching with configurable TTL
- **Health Monitoring** - Real-time health checks and component status
- **Metrics Collection** - System and application performance metrics
- **Configuration Management** - Environment-based configuration with validation
- **Error Handling** - Comprehensive error handling with user-friendly messages

## Installation

### Prerequisites

- Python 3.8+
- Steam Library database (created by `steam_library_fetcher.py`)
- Required Python packages (see requirements.txt)

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Ensure database exists:
```bash
python src/fetcher/steam_library_fetcher.py
```

## Configuration

The server uses a comprehensive configuration system with environment variable support.

### Environment Variables

```bash
# Server Settings
HOST=0.0.0.0
PORT=8000
DEBUG=false
WORKERS=1

# Database
DATABASE_URL=sqlite:///steam_library.db
DATABASE_ECHO=false
DATABASE_POOL_SIZE=5

# Caching
CACHE_TTL=3600
CACHE_TTL_SEARCH=900
CACHE_TTL_RECOMMENDATIONS=3600
ENABLE_CACHE=true
CACHE_MAX_SIZE=1000

# Performance
MAX_SEARCH_RESULTS=50
MAX_RECOMMENDATIONS=10
REQUEST_TIMEOUT=30

# Features
ENABLE_NL_SEARCH=true
ENABLE_RECOMMENDATIONS=true
ENABLE_FRIENDS_DATA=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/steam_librarian.log
```

### Configuration Validation

The server validates configuration on startup and provides warnings/errors:

```python
from mcp_server.config import config_manager

# Validate configuration
validation = config_manager.validate_configuration()
if not validation["valid"]:
    print("Configuration errors:", validation["errors"])
```

## Tools

### 1. search_games

Natural language game search with intelligent parsing.

**Features:**
- Mood detection (chill, intense, creative, social, nostalgic)
- Genre recognition
- Similarity matching ("games like Portal")
- Time constraint understanding
- Playtime filtering

**Examples:**
```
"chill puzzle games"
"games like portal"
"unplayed rpg games"
"something relaxing for tonight"
"intense action games I haven't touched"
```

### 2. filter_games

Filter games with intelligent presets and custom criteria.

**Presets:**
- `comfort_food` - Highly rated games with good playtime (5+ hours)
- `hidden_gems` - Positive games with minimal playtime (<2 hours)
- `quick_session` - Games for short play sessions (<1 hour)
- `deep_dive` - Games with extensive content (20+ hours)

**Custom Filters:**
- Playtime range (min/max hours)
- Review ratings
- Categories (Single-player, Co-op, etc.)
- Maturity ratings
- Sorting options

### 3. get_recommendations

Personalized game recommendations based on your library and preferences.

**Context Options:**
- `mood` - Current gaming mood
- `time_available` - Available time (quick/medium/long)
- `exclude_recent` - Exclude recently played games
- `with_friends` - Prioritize multiplayer games

**Algorithm Features:**
- Genre preference analysis
- Developer affinity scoring
- Playtime pattern recognition
- Review quality weighting
- Context-aware filtering

### 4. get_friends_data

Social gaming features for multiplayer experiences.

**Data Types:**
- `common_games` - Games owned by both you and friends
- `friend_activity` - Recent gaming activity of friends
- `multiplayer_compatible` - Friends who own specific multiplayer games
- `compatibility_score` - Gaming compatibility analysis

**Features:**
- Common game discovery
- Activity tracking
- Compatibility scoring
- Game recommendations from friends

### 5. get_library_stats

Comprehensive library statistics and insights.

**Time Periods:**
- `all_time` - Complete library history
- `last_year` - Past 12 months
- `last_6_months` - Past 6 months
- `last_month` - Past 30 days
- `last_week` - Past 7 days

**Analytics:**
- Basic statistics (total games, playtime, averages)
- Genre distribution and preferences
- Developer/publisher analysis
- Playtime patterns and trends
- AI-generated gaming insights
- Completion estimates

## API Endpoints

### Health Check Endpoints

#### GET /health
Basic health check for liveness probes.

**Response:**
```
OK (200) - Server is healthy
UNHEALTHY: <reason> (503) - Server is unhealthy
```

#### GET /health/detailed
Detailed health check with component status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "server": {
    "name": "steam-librarian",
    "version": "2.0.0",
    "python_version": "3.9.0",
    "pid": 12345
  },
  "components": {
    "database": {
      "status": "healthy",
      "user_count": 5
    },
    "cache": {
      "status": "healthy"
    },
    "tools": {
      "status": "healthy",
      "count": 5,
      "available": ["search_games", "filter_games", ...]
    }
  }
}
```

### Configuration Endpoint

#### GET /config
Get current server configuration.

**Response:**
```json
{
  "server_info": {
    "name": "steam-librarian",
    "version": "2.0.0",
    "debug": false,
    "host": "0.0.0.0",
    "port": 8000
  },
  "performance": {
    "max_search_results": 50,
    "max_recommendations": 10,
    "cache_settings": {...}
  },
  "features": {
    "natural_language_search": true,
    "recommendations": true,
    "friends_data": true
  },
  "validation": {
    "valid": true,
    "warnings": [],
    "errors": []
  }
}
```

### Metrics Endpoint

#### GET /metrics
Get server metrics and performance data.

**Response:**
```json
{
  "timestamp": "2024-01-20T10:30:00Z",
  "system": {
    "cpu_percent": 15.2,
    "memory_mb": 256.5,
    "memory_percent": 3.2,
    "threads": 4,
    "uptime_seconds": 3600
  },
  "cache": {
    "size": 150,
    "max_size": 1000,
    "hit_rate": 0.85
  },
  "database": {
    "users": 5,
    "games": 1200
  }
}
```

### MCP Protocol Endpoint

#### /mcp
The main MCP protocol endpoint for tool invocation via HTTP streaming.

## Running the Server

### Production Startup

Use the provided startup script for production deployment:

```bash
python src/mcp_server/run_server.py
```

This script provides:
- Configuration validation
- Database connectivity check
- Signal handling for graceful shutdown
- Startup information logging
- Feature flag reporting

### Development Mode

For development with debug logging:

```bash
DEBUG=true LOG_LEVEL=DEBUG python src/mcp_server/run_server.py
```

### Direct Server Run

For testing or custom integration:

```python
import asyncio
from mcp_server.server import mcp

async def main():
    await mcp.run_streamable_http_async(
        host="0.0.0.0",
        port=8000
    )

asyncio.run(main())
```

## Testing

The Steam Librarian MCP Server includes a comprehensive test suite with both unit and integration tests to ensure reliability and functionality.

### Test Structure

```
tests/
├── __init__.py
├── test_mcp_server.py      # Comprehensive unit tests
└── test_integration.py     # Integration tests with server startup
```

### Running Tests

The project provides convenient Make targets for different testing scenarios:

#### Quick Tests
```bash
# Run basic import tests (fastest)
make test
```

#### Unit Tests
```bash
# Run comprehensive unit tests
make test-unit
```

#### Integration Tests
```bash
# Run integration tests (starts test server)
make test-integration
```

#### Full Test Suite
```bash
# Run all tests (unit + integration)
make test-full
```

#### Development Testing
```bash
# Run all code quality checks + comprehensive tests
make check-full
```

### Test Coverage

#### Unit Tests (52 test cases)
- **Import Testing**: All critical modules and tools
- **Configuration Management**: Server info, feature flags, validation
- **FastMCP Integration**: Server instance, tool registration, metadata
- **Database Models**: Connection, model attributes, relationships
- **Caching System**: Set/get operations, cache invalidation, get_or_compute
- **User Context Resolution**: Graceful handling of missing data
- **Input Validation**: All Pydantic schemas with proper error handling
- **Error Framework**: Decorator functionality and error classes
- **Monitoring Tools**: Script existence and executability

#### Integration Tests
- **Server Startup**: Production server launch and health checks
- **Health Endpoints**: Basic and detailed health monitoring
- **MCP Protocol**: Basic connectivity and protocol compliance

#### Tool Testing
All 5 MCP tools are validated for proper registration and functionality:
1. **search_games** - Natural language game search
2. **filter_games** - Advanced filtering with presets
3. **get_recommendations** - Personalized recommendations
4. **get_friends_data** - Social gaming features
5. **get_library_stats** - Comprehensive analytics

### Test Environment Setup

Tests are designed to work in any environment, including:
- **Empty databases** (graceful handling of missing data)
- **Missing dependencies** (`aiohttp` optional for integration tests)
- **CI/CD environments** (no external dependencies required)

### Test Results Format

Unit tests provide detailed output and progress tracking:
```
Steam Librarian MCP Server Test Suite
==================================================

Testing Imports...
✓ Import mcp_server.server
✓ Import mcp_server.config
...

Test Results Summary
✓ Passed: 52
✗ Failed: 0
Success Rate: 100.0%

All tests passed! The MCP Server is ready for production.
```

Integration tests show server startup and endpoint testing:
```
Steam Librarian MCP Server Integration Tests
==================================================
Starting test server...
✓ Test server started successfully

Testing Health Endpoints...
✓ Basic health check
✓ Detailed health check
...

Integration Test Results: 2/2 passed
All integration tests passed!
```

### Continuous Integration

For CI/CD pipelines, use the comprehensive check:
```bash
# Run linting, formatting, and all tests
make check-full
```

This ensures:
- Code follows style guidelines (ruff linting)
- Formatting is consistent (black formatting)
- All unit tests pass
- Integration tests complete successfully
- Server is production-ready

### Writing New Tests

When adding new functionality, update the test suites:

#### Adding Unit Tests
```python
# In tests/test_mcp_server.py
def test_my_new_feature(self):
    """Test description"""
    # Test implementation
    self.assert_test(condition, "Test name", "Error message")
```

#### Adding Integration Tests
```python
# In tests/test_integration.py
async def test_my_endpoint(self):
    """Test new endpoint"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{self.base_url}/my-endpoint") as response:
            assert response.status == 200
```

### Test Performance

- **Unit Tests**: ~5-10 seconds (no server startup)
- **Integration Tests**: ~15-30 seconds (includes server startup)
- **Full Suite**: ~20-40 seconds total

Tests are optimized for speed with caching and parallel execution where possible.

## Monitoring

### Monitor Tool

The `monitor.py` script provides comprehensive monitoring capabilities:

```bash
# Check server health
python src/mcp_server/monitor.py health

# Get detailed health information
python src/mcp_server/monitor.py health --detailed

# Show server configuration
python src/mcp_server/monitor.py config

# Display metrics
python src/mcp_server/monitor.py metrics

# Complete server status
python src/mcp_server/monitor.py status

# Continuous monitoring
python src/mcp_server/monitor.py monitor --interval 5

# JSON output for integration
python src/mcp_server/monitor.py monitor --format json
```

### Health Check Integration

For Kubernetes or Docker health checks:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

## Development

### Adding New Tools

1. Create a new file in `tools/`:
```python
from ..server import mcp

@mcp.tool()
async def my_new_tool(param1: str, param2: Optional[int] = None) -> str:
    """Tool description"""
    # Implementation
    return "Result"
```

2. Import in `tools/__init__.py`:
```python
from . import my_new_tool
```

### Custom Health Checks

Add custom health check components:

```python
# In server.py health check
try:
    # Your custom check
    custom_status = check_custom_component()
    health_data["components"]["custom"] = {
        "status": "healthy" if custom_status else "unhealthy"
    }
except Exception as e:
    health_data["components"]["custom"] = {
        "status": "unhealthy",
        "error": str(e)
    }
```

### Caching Strategy

The caching system uses different TTLs for different operations:

```python
# Search results - 15 minutes
cache_key = search_cache_key(query, user_id)
results = await cache.get_or_compute(cache_key, compute_fn, ttl=900)

# User data - 30 minutes
cache_key = user_cache_key("profile", user_id)
profile = await cache.get_or_compute(cache_key, compute_fn, ttl=1800)

# Recommendations - 1 hour
cache_key = user_cache_key("recommendations", user_id)
recs = await cache.get_or_compute(cache_key, compute_fn, ttl=3600)
```

### Development Testing

When developing new features, always run tests to ensure everything works:

```bash
# Before committing changes
make check-full

# During development (faster feedback)
make test-unit

# After adding new endpoints
make test-integration
```

#### Test-Driven Development

1. **Write tests first** for new tools:
```python
def test_my_new_tool(self):
    """Test my new tool functionality"""
    # Test the tool behavior
    self.assert_test(condition, "Tool works correctly")
```

2. **Run tests frequently**:
```bash
# Quick feedback loop
make test-unit
```

3. **Validate integration**:
```bash
# After implementation is complete
make test-full
```

## Troubleshooting

### Common Issues

#### Database Connection Failed
```
ERROR: Database connection failed: no such table: user_profiles
```
**Solution:** Run the fetcher to create the database:
```bash
python src/fetcher/steam_library_fetcher.py
```

#### Port Already in Use
```
ERROR: [Errno 48] Address already in use
```
**Solution:** Change the port or stop the conflicting service:
```bash
PORT=8001 python src/mcp_server/run_server.py
```

#### Import Errors
```
ImportError: attempted relative import beyond top-level package
```
**Solution:** Run from the project root directory:
```bash
cd /path/to/steam-librarian
python src/mcp_server/run_server.py
```

### Debug Mode

Enable debug mode for detailed logging:
```bash
DEBUG=true LOG_LEVEL=DEBUG python src/mcp_server/run_server.py
```

### Test Failures

#### Unit Test Import Errors
```
ImportError: attempted relative import beyond top-level package
```
**Solution:** Ensure you're running tests from the project root with proper PYTHONPATH:
```bash
# Use make targets (recommended)
make test-unit

# Or manual execution with correct path
cd /path/to/steam-librarian
PYTHONPATH=src python tests/test_mcp_server.py
```

#### Integration Test Server Startup Fails
```
Test server failed to start within timeout
```
**Solution:** Check if the port is already in use or increase timeout:
```bash
# Check for conflicting services
lsof -i :8001

# Use different port for testing
PORT=8002 make test-integration
```

#### Missing aiohttp Dependency
```
aiohttp not available - integration tests will be limited
```
**Solution:** Install aiohttp for full integration testing:
```bash
pip install aiohttp
make test-integration
```

#### Database-Related Test Failures
```
no such table: user_profile
```
**Solution:** This is expected for tests in empty environments. Tests handle this gracefully, but to test with real data:
```bash
# Create test database first
python src/fetcher/steam_library_fetcher.py
make test-unit
```

#### Cache Test Failures
```
Cache missing set/get methods
```
**Solution:** This indicates a caching system issue. Verify the cache implementation:
```bash
# Check cache module directly
python -c "from src.mcp_server.cache import cache; print(hasattr(cache, 'get'))"
```

<br>

---
# Performance Tuning

For high-load scenarios, adjust settings:
```bash
# Increase cache size
CACHE_MAX_SIZE=5000

# Increase database pool
DATABASE_POOL_SIZE=20

# Reduce cache TTLs for fresher data
CACHE_TTL_SEARCH=300
CACHE_TTL_USER=600

# Increase concurrent requests
MAX_CONCURRENT_REQUESTS=500
```

<br>

---
# Integration Examples

### Claude Desktop Integration

Add to Claude Desktop configuration:

```json
{
  "mcpServers": {
    "steam-librarian": {
      "command": "python",
      "args": ["path/to/steam-librarian/src/mcp_server/run_server.py"],
      "env": {
        "DEBUG": "false",
        "PORT": "8000"
      }
    }
  }
}
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()"

CMD ["python", "src/mcp_server/run_server.py"]
```

### API Client Example

```python
import aiohttp
import asyncio

async def search_games(query: str):
    async with aiohttp.ClientSession() as session:
        payload = {
            "method": "tools/call",
            "params": {
                "name": "search_games",
                "arguments": {
                    "query": query
                }
            }
        }
        
        async with session.post("http://localhost:8000/mcp", json=payload) as response:
            result = await response.json()
            return result

# Usage
results = asyncio.run(search_games("chill puzzle games"))
```

## Performance Considerations

- **Caching**: All expensive operations are cached with appropriate TTLs
- **Database**: Uses SQLAlchemy with connection pooling
- **Async Operations**: All I/O operations are asynchronous
- **Memory Management**: Cache has configurable size limits
- **Request Timeouts**: Configurable timeouts prevent hanging requests

<br>

---
# Security Notes

- The server binds to `0.0.0.0` by default - restrict in production
- Database credentials are hidden in configuration endpoints
- No authentication is built-in - add reverse proxy authentication if needed
- Steam API keys are optional and stored securely in environment variables

<br>

---
# Future Enhancements

- WebSocket support for real-time updates
- Redis cache backend for distributed deployments
- PostgreSQL support for better scalability
- Authentication and authorization
- Rate limiting and request throttling
- Prometheus metrics export
- OpenTelemetry tracing