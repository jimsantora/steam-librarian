<p align="center">
  <img src="images/steam_librarian_logo_512x512.png" alt="Steam Librarian Logo" width="256" height="256">
</p>

<h1 align="center">Steam Librarian</h1>

<p align="center">
  <em><strong>Your personal game archivist and curator.</strong> They know your library inside and out, can compare collections with friends, suggest your next adventure, and share deep insights about every game on your digital shelves.</em>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11-blue.svg" alt="Python 3.11"></a>
  <a href="https://hub.docker.com/r/jimsantora/steam-librarian"><img src="https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white" alt="Docker"></a>
  <a href="https://kubernetes.io/"><img src="https://img.shields.io/badge/kubernetes-%23326ce5.svg?logo=kubernetes&logoColor=white" alt="Kubernetes"></a>
  <a href="https://github.com/anthropics/mcp"><img src="https://img.shields.io/badge/MCP-Protocol-green" alt="MCP Protocol"></a>
</p>

A powerful Model Context Protocol (MCP) server that provides intelligent access to your Steam library data through natural language processing, personalized recommendations, and advanced gaming analytics. Built with FastMCP and featuring HTTP streaming, smart caching, and comprehensive testing.

**Your Intelligent Gaming Companion** - Search games with natural language ("chill puzzle games for tonight"), get AI-powered personalized recommendations, analyze your gaming patterns with detailed insights, and discover social gaming opportunities with friends through compatibility scoring.

This repo was developed with Claude Code, and I left Claude's config in here for reference. This was built as a learning experience and comprehensive example of creating a production-ready MCP server.

<details>
<summary><strong>Table of Contents</strong></summary>

- [Features](#features)
- [Example Interactions](#example-interactions-click-the-dropdowns-to-see-responses)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Usage Examples](#usage-examples)
- [Available Tools](#available-tools)
- [Data Source](#data-source)
- [Troubleshooting](#troubleshooting)
- [Technical Details](#technical-details)
- [Project Structure](#project-structure)
- [Deployment Options](#deployment-options)
- [Using the MCP Server](#using-the-mcp-server)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Available MCP Tools](#available-mcp-tools)

</details>

<details>
<summary><strong>Additional Documentation</strong></summary>

- [MCP Server Documentation](src/mcp_server/README.md) - Detailed server implementation guide
- [Deployment Guide](deploy/README.md) - Docker and Kubernetes deployment instructions
- [Database Schema](src/shared/README.md) - Data model and database documentation

</details>

<br>

---
# Features

### Intelligent Gaming Tools
- **Natural Language Search**: Find games using natural queries like "chill puzzle games for tonight" or "games like Portal"
- **AI-Powered Recommendations**: Get personalized suggestions based on your gaming patterns, mood, and available time
- **Smart Filtering**: Use intelligent presets (comfort_food, hidden_gems, quick_session, deep_dive) or custom criteria
- **Social Gaming Analytics**: Discover friends' libraries, find common games, and calculate compatibility scores
- **Comprehensive Library Insights**: Deep analytics with AI-generated gaming insights and trend analysis

### Core Functionality
- **Multi-User Support**: Query multiple Steam users and seamlessly switch between libraries
- **Game Details & Reviews**: Comprehensive information including review statistics and ratings
- **Recent Activity Tracking**: Monitor what you and your friends have been playing
- **User Profile Data**: Access Steam levels, XP, account age, and profile information

### Technical Excellence
- **Production-Ready Architecture**: Built with FastMCP, HTTP streaming, and comprehensive error handling
- **Smart Caching System**: Intelligent caching with configurable TTL for optimal performance
- **Comprehensive Testing**: Full unit and integration test coverage with quality assurance
- **Health Monitoring**: Built-in health checks, metrics, and administration tools

<br>

## Example Interactions (Click the dropdowns to see responses)

<details>
<summary>Suggest games based on recent play history<br><img src="images/recent_games_question.png"/></summary>
<br>
<img src="images/recent_games_answer.png" />
</details>

<details>
<summary>Suggest games based on review scores and age ratings<br><img src="images/game_suggestion_question.png"/></summary>
<br>
<img src="images/game_suggestion_answer.png" />
</details>

<details>
<summary>Generate a calendar timeline following several rules of games to share over time<br><img src="images/game_sharing_calendar_question.png"/></summary>
<br>
<img src="images/game_sharing_calendar_answer.png" />
</details>

<br>

---
# Prerequisites

- Python 3.8 or higher
- A Steam account with a public game library
- Steam API key (get one from https://steamcommunity.com/dev/apikey)
- Your Steam ID

<br>

---
# Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Fetch Your Steam Library Data

First, create a `.env` file with your Steam credentials:

```bash
# .env
STEAM_ID=your_steam_id_here
STEAM_API_KEY=your_steam_api_key_here
```

Then run the data fetcher:

```bash
python src/fetcher/steam_library_fetcher.py
```

This will create a SQLite database (`steam_library.db`) with all your game data and user profile information.

**Optional**: To also fetch friends data:
```bash
python src/fetcher/steam_library_fetcher.py --friends
```

### 3. Run the MCP Server

Start the production server:

```bash
python src/mcp_server/run_server.py
```

The server will start on `http://0.0.0.0:8000/mcp` with comprehensive health checks and monitoring.

### 4. Verify the Server is Running

The server will output logs indicating it's running on `http://0.0.0.0:8000/mcp`.

You can also check the health endpoint:
```bash
curl http://localhost:8000/health
```

<br>

---
# Usage Examples

The intelligent MCP server can understand and respond to natural language queries like:

- **Natural Language Search**: "Show me chill puzzle games for tonight" or "Find games like Portal that I haven't played"  
- **Smart Recommendations**: "Suggest games based on my recent activity" or "What should I play with friends?"
- **Social Gaming**: "Which friends own Helldivers 2?" or "Show me games I have in common with Sarah"
- **Library Analytics**: "Analyze my gaming patterns" or "What genres do I play most?"
- **Activity Tracking**: "What have I been playing lately?" or "Show me my most played games"
- **Game Information**: "Tell me about Baldur's Gate 3" or "What are the reviews for this indie game?"

The server uses context understanding and AI-powered analysis to provide intelligent, personalized responses.

<br>

---
# Available Tools

The server provides 5 comprehensive tools that leverage natural language processing and AI:

### **search_games** - Natural Language Game Search
- **Natural Language Processing**: Understands queries like "chill puzzle games" or "games like Portal"
- **Mood Detection**: Recognizes gaming moods (chill, intense, creative, social, nostalgic)
- **Context Awareness**: Handles time constraints ("quick games") and playtime preferences
- **Smart Matching**: Finds similar games and handles partial/fuzzy matching

### **filter_games** - Advanced Filtering with Intelligent Presets  
- **Smart Presets**: `comfort_food` (highly-rated 5+ hour games), `hidden_gems` (positive <2 hour games)
- **Custom Filtering**: Playtime ranges, review ratings, categories, maturity ratings
- **Intelligent Sorting**: Multiple sort options with relevance scoring

### **get_recommendations** - AI-Powered Personalized Recommendations
- **Context-Aware**: Considers mood, available time, and gaming preferences
- **Algorithmic Intelligence**: Genre preferences, developer affinity, playtime patterns
- **Personalization**: Adapts to your unique gaming history and preferences

### **get_friends_data** - Social Gaming Analytics
- **Common Games Discovery**: Find games you share with friends
- **Compatibility Scoring**: AI-powered compatibility analysis based on genres and games
- **Activity Tracking**: Monitor friends' recent gaming activity
- **Multiplayer Matching**: Find friends who own specific multiplayer games

### **get_library_stats** - Comprehensive Library Analytics
- **Deep Analytics**: Playtime distribution, genre preferences, developer loyalty
- **AI-Generated Insights**: Smart observations about your gaming patterns
- **Trend Analysis**: Activity patterns and gaming behavior over time
- **Value Analysis**: Identify your highest-value games and spending efficiency

**Additional Utility Tools**: `get_all_users`, `get_user_info`, `get_game_details`, `get_game_reviews`, `get_recently_played`

For detailed documentation on each tool's capabilities and parameters, see [MCP Server Documentation](src/mcp_server/README.md).

<br>

---
# Data Source

The server uses a sophisticated relational SQLite database (`steam_library.db`) with normalized data structure:
- **Games**: Comprehensive game metadata including ratings, reviews, genres, developers, publishers
- **User Profiles**: Complete Steam user information, levels, XP, location data, account details
- **User Games**: Per-user playtime and ownership data with recent activity tracking
- **Friends**: Social relationships and friend networks for compatibility analysis
- **Reviews**: Detailed review statistics and sentiment analysis

The database is automatically created and managed by the fetcher script. For detailed schema information, see [Database Schema Documentation](src/shared/README.md).

<br>

---
# Troubleshooting

1. **Server not connecting**: Check that the server is running on the correct port
2. **Database not found**: Run `python src/fetcher/steam_library_fetcher.py` to create the SQLite database
3. **Permission errors**: Make sure Python has read/write access to the database file
4. **No data returned**: Ensure you've run the fetcher and the database contains your Steam data
5. **Multiple users**: Use `get_all_users` tool to see available users if queries ask for user selection

<br>

---
# Technical Details

### Architecture & Framework
- **FastMCP Integration**: Built with official MCP Python SDK for HTTP streaming
- **Production-Ready**: Comprehensive error handling, graceful shutdown, and signal management
- **Smart Caching**: Intelligent memory-based caching with configurable TTL and automatic invalidation
- **Multi-User Context**: Seamless user resolution with intelligent fallbacks

### Database & Performance  
- **SQLAlchemy ORM**: Efficient data modeling with proper relationships and indexing
- **SQLite Database**: Normalized relational structure for optimal query performance
- **Connection Pooling**: Configurable database pool management for scalability

### Testing & Quality Assurance
- **Comprehensive Test Suite**: 52+ unit tests and integration tests with 100% pass rate
- **Automated Quality Checks**: Linting (ruff), formatting (black), and code quality validation
- **CI/CD Ready**: Make targets for development workflow and continuous integration
- **Performance Testing**: Load testing and optimization validation

### Monitoring & Operations
- **Health Monitoring**: Built-in health checks, metrics collection, and component status
- **Administration Tools**: Monitoring script, configuration validation, and system diagnostics
- **RESTful Endpoints**: Health checks (`/health`), detailed status (`/health/detailed`), metrics (`/metrics`)

For detailed technical documentation, see [MCP Server Documentation](src/mcp_server/README.md).

<br>

---
# Project Structure

```
steam-librarian/
├── src/                           # Source code
│   ├── fetcher/                  # Steam library data fetcher service
│   │   └── steam_library_fetcher.py
│   ├── mcp_server/               # Advanced MCP server with FastMCP
│   │   ├── server.py            # Main FastMCP server with health endpoints
│   │   ├── config.py            # Configuration management system
│   │   ├── cache.py             # Smart caching with TTL
│   │   ├── run_server.py        # Production startup script
│   │   ├── monitor.py           # Administration and monitoring tool
│   │   ├── tools/               # 5 comprehensive MCP tools
│   │   │   ├── search_games.py      # Natural language search
│   │   │   ├── filter_games.py      # Smart filtering with presets
│   │   │   ├── get_recommendations.py  # AI-powered recommendations
│   │   │   ├── get_friends_data.py     # Social gaming analytics
│   │   │   └── get_library_stats.py    # Comprehensive insights
│   │   └── utils/               # Utility functions and helpers
│   └── shared/                   # Shared database and utilities
│       ├── database.py          # SQLAlchemy models and DB utilities
│       └── README.md            # Database schema documentation
├── tests/                        # Comprehensive test suite
│   ├── test_mcp_server.py       # Unit tests (52 test cases)
│   └── test_integration.py      # Integration tests with server startup
├── deploy/                       # Deployment configurations
│   ├── README.md                # Comprehensive deployment guide
│   ├── docker/                  # Docker configurations and compose files
│   └── helm/                    # Kubernetes Helm charts with values
├── Makefile                      # Development commands and testing
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

### Service Architecture

- **Fetcher Service**: Runs as a CronJob in Kubernetes, fetches Steam data via API
- **MCP Server**: Runs as a Deployment, provides MCP interface to Steam data
- **Shared Storage**: SQLite database on persistent volume shared between services

<br>

---
# Deployment Options

Steam Librarian supports multiple deployment options for different environments and use cases. For comprehensive deployment instructions, configuration options, and troubleshooting, see the **[Deployment Guide](deploy/README.md)**.

### Quick Start Options

#### Local Development
```bash
# Run production server with full monitoring
python src/mcp_server/run_server.py

# Development mode with debug logging
DEBUG=true LOG_LEVEL=DEBUG python src/mcp_server/run_server.py
```

#### Docker (Recommended)
```bash
# Build and run with Docker Compose
make build-docker
make run-docker

# Check health and endpoints
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

#### Kubernetes with Helm
```bash
# Quick install with Helm
helm install steam-librarian deploy/helm/steam-librarian -f values-override.yaml
```

For detailed instructions including:
- Complete Docker Compose setup with environment configuration
- Kubernetes deployment with custom values and scaling options  
- Production deployment best practices
- Health monitoring and troubleshooting
- Manual data fetching and maintenance

**👉 See the complete [Deployment Guide](deploy/README.md)**

<br>

---
# Using the MCP Server

This MCP server uses the Model Context Protocol, which requires an MCP client to interact with it. The server exposes tools that can be called by MCP clients such as:

- Claude Desktop (with appropriate configuration)
- MCP-compatible AI assistants
- Custom MCP clients using the MCP SDK

The server runs on port 8000 by default with the following endpoints:
- `http://0.0.0.0:8000/mcp` - MCP protocol endpoint (HTTP transport with SSE)
- `http://0.0.0.0:8000/health` - Health check endpoint for monitoring

<br>

---

### Testing & Quality Assurance

The project includes comprehensive testing capabilities:

```bash
# Run basic import tests (fastest)
make test

# Run unit tests (52 test cases with detailed output)
make test-unit

# Run integration tests with server startup
make test-integration

# Run all tests (unit + integration)
make test-full

# Run complete code quality checks + all tests
make check-full
```

<br>

---

### Available MCP Tools

The server exposes these intelligent tools through the MCP protocol:

**Advanced Intelligence Tools:**
- `search_games` - Natural language search with mood detection and context understanding
- `filter_games` - Smart filtering with intelligent presets and custom criteria  
- `get_recommendations` - AI-powered personalized recommendations with context awareness
- `get_friends_data` - Social gaming analytics with compatibility scoring
- `get_library_stats` - Comprehensive library insights with AI-generated analysis

**Utility Tools:**
- `get_all_users` - List all Steam users in the database
- `get_user_info` - Get comprehensive user profile information  
- `get_game_details` - Get detailed information about specific games
- `get_game_reviews` - Get review statistics and ratings
- `get_recently_played` - Get recently played games with activity tracking

For detailed tool documentation and examples, see [MCP Server Documentation](src/mcp_server/README.md).