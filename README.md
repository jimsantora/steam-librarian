<p align="center">
  <img src="images/steam_librarian_logo_512x512.png" alt="Steam Librarian Logo" width="256" height="256">
</p>

<h1 align="center">Steam Librarian</h1>

<p align="center">
  <em><strong>Your Steam collection, curated by an AI-powered librarian.</strong> Natural language search, mood-based recommendations, and social insights that actually help you pick the perfect game.</em>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11-blue.svg" alt="Python 3.11"></a>
  <a href="https://hub.docker.com/r/jimsantora/steam-librarian"><img src="https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white" alt="Docker"></a>
  <a href="https://kubernetes.io/"><img src="https://img.shields.io/badge/kubernetes-%23326ce5.svg?logo=kubernetes&logoColor=white" alt="Kubernetes"></a>
  <a href="https://github.com/anthropics/mcp"><img src="https://img.shields.io/badge/MCP-Protocol-green" alt="MCP Protocol"></a>
</p>

Steam Librarian is your digital gaming archivist - an intelligent Model Context Protocol (MCP) server that transforms how you interact with your Steam library. Our core philosophy addresses a universal gamer problem: extensive libraries filled with unplayed gems, forgotten favorites, and impulse purchases create decision paralysis where we spend more time browsing than playing. Like a knowledgeable librarian who knows every book on the shelf, Steam Librarian analyzes your gaming patterns, respects your time, and serves as your personal curator.

This AI-powered assistant leverages MCP's advanced features including sampling for natural language understanding, elicitation for interactive parameter gathering, and completions for discoverable functionality. The system tracks your play history and preferences, helps you find games that match your current mood and available time, understands what your friends are playing, and can suggest the perfect game for any situation. Built with FastMCP and featuring HTTP streaming, smart caching, comprehensive testing, and production-ready architecture, it serves as both a practical gaming tool and a comprehensive example of creating an intelligent MCP server.

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

### AI-Powered Gaming Intelligence
- **Smart Search with AI Sampling**: Natural language queries like "chill puzzle games for tonight" interpreted by AI into structured filters
- **Context-Aware Recommendations**: Personalized suggestions using elicitation to gather context (mood, time, age, preferences)
- **Intelligent Library Analytics**: Deep pattern analysis with AI interpretation of your gaming habits and trends
- **Interactive Parameter Discovery**: MCP completions help you discover available options and query patterns
- **Social Gaming Insights**: Friend library comparisons and multiplayer game matching

### Core Functionality
- **Multi-User Support**: Query multiple Steam users and seamlessly switch between libraries
- **Game Details & Reviews**: Comprehensive information including review statistics and ratings
- **Recent Activity Tracking**: Monitor what you and your friends have been playing
- **User Profile Data**: Access Steam levels, XP, account age, and profile information

### Technical Excellence
- **Advanced MCP Features**: Full implementation of sampling, elicitation, and completions for intelligent user interaction
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

The AI-powered MCP server understands natural language and provides intelligent, contextual responses:

- **AI Smart Search**: "Show me chill puzzle games for tonight" → AI sampling interprets mood and filters games
- **Context-Aware Recommendations**: "I need family games" → Elicitation asks for age and preferences  
- **Interactive Discovery**: Tab completion shows available contexts like "family", "quick_session", "mood_based"
- **Deep Analytics**: "Analyze my gaming patterns" → AI interprets data and provides insights about your habits
- **Social Gaming**: "Find multiplayer games my friends own" → Intelligent friend library analysis
- **Mood-Based Suggestions**: "Something relaxing after work" → AI maps sentiment to game recommendations

The server leverages MCP's advanced features (sampling, elicitation, completions) for truly intelligent gaming assistance.

<br>

---
# Available Tools

The server provides 3 powerful AI-enhanced tools that showcase MCP's advanced capabilities:

### **smart_search** - AI-Powered Unified Search
- **AI Sampling**: Natural language queries interpreted by AI into structured filters
- **Intelligent Filtering**: Multi-tier classification using genres, categories, and tags
- **Smart Sorting**: Multiple algorithms including relevance, playtime, ratings, and random discovery
- **Query Understanding**: Handles complex requests like "family-friendly co-op games for short sessions"

### **recommend_games** - Context-Aware Recommendations with Elicitation
- **Interactive Context Gathering**: Uses elicitation to ask for missing parameters (age, time, preferences)
- **Contextual Intelligence**: Six specialized contexts (family, quick_session, similar_to, mood_based, unplayed_gems, abandoned)
- **Play History Integration**: Analyzes your gaming patterns for personalized suggestions
- **Age-Appropriate Filtering**: ESRB/PEGI rating system integration for family-safe recommendations

### **get_library_insights** - Deep Analytics with AI Interpretation
- **Pattern Analysis**: AI interpretation of your gaming habits, preferences, and trends
- **Comprehensive Analytics**: Value analysis, genre distribution, social comparisons, achievement tracking
- **Intelligent Insights**: AI-generated observations about your gaming personality and behavior
- **Trend Recognition**: Time-based analysis of how your gaming preferences evolve

### MCP Protocol Features
- **Completions**: Tab completion for parameters, contexts, and query patterns
- **Resources**: Rich data access through URI templates (library://games, library://genres, etc.)
- **Prompts**: Interactive examples showcasing all features with humor and practical scenarios

**Legacy Utility Tools**: `get_all_users`, `get_user_info`, `get_game_details`, `get_game_reviews`, `get_recently_played`

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
- **Advanced MCP Implementation**: Full use of sampling, elicitation, and completions for intelligent user interaction
- **FastMCP Integration**: Built with official MCP Python SDK for HTTP streaming and Server-Sent Events
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
│   ├── mcp_server/               # Advanced MCP server with AI features
│   │   ├── server.py            # Main FastMCP server with health endpoints
│   │   ├── config.py            # Configuration management system
│   │   ├── run_server.py        # Production startup script
│   │   ├── tools.py             # 3 AI-powered MCP tools (consolidated)
│   │   ├── resources.py         # MCP resources (consolidated)
│   │   ├── prompts.py           # Interactive MCP prompts (consolidated)
│   │   └── completions.py       # Database-driven completions
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

The server exposes these AI-enhanced tools through the MCP protocol:

**Core AI-Powered Tools:**
- `smart_search` - AI sampling for natural language query interpretation and unified search
- `recommend_games` - Context-aware recommendations with elicitation for parameter gathering
- `get_library_insights` - Deep analytics with AI interpretation of gaming patterns

**MCP Protocol Features:**
- **Sampling**: AI interpretation of natural language queries into structured data
- **Elicitation**: Interactive parameter gathering for missing or ambiguous inputs
- **Completions**: Tab completion for parameters, contexts, and query patterns
- **Resources**: Rich data access through URI templates (library://games, library://users, etc.)
- **Prompts**: Interactive examples showcasing all features with engaging scenarios

**Legacy Utility Tools:**
- `get_all_users` - List all Steam users in the database
- `get_user_info` - Get comprehensive user profile information  
- `get_game_details` - Get detailed information about specific games
- `get_game_reviews` - Get review statistics and ratings
- `get_recently_played` - Get recently played games with activity tracking

For detailed tool documentation and examples, see [MCP Server Documentation](src/mcp_server/README.md).