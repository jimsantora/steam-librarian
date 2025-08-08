<p align="center">
  <img src="images/steam_librarian_logo_512x512.png" alt="Steam Librarian Logo" width="256" height="256">
</p>

<h1 align="center">Steam Librarian</h1>

<p align="center">
  <em><strong>Your Steam collection, curated by an AI-powered librarian.</strong> Natural language search, mood-based recommendations, and social insights that actually help you pick the perfect game.</em>
</p>

<p align="center">
  <a href="https://github.com/jimsantora/steam-librarian/releases"><img src="https://img.shields.io/badge/version-1.6.0-blue.svg" alt="Version 1.6.0"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11-blue.svg" alt="Python 3.11"></a>
  <a href="https://hub.docker.com/r/jimsantora/steam-librarian"><img src="https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white" alt="Docker"></a>
  <a href="https://kubernetes.io/"><img src="https://img.shields.io/badge/kubernetes-%23326ce5.svg?logo=kubernetes&logoColor=white" alt="Kubernetes"></a>
  <a href="https://github.com/anthropics/mcp"><img src="https://img.shields.io/badge/MCP-Protocol-green" alt="MCP Protocol"></a>
</p>

Steam Librarian transforms your overwhelming Steam library into a curated collection. Just like a knowledgeable librarian who knows every book on the shelf, this AI assistant helps you rediscover forgotten gems, find the perfect game for your mood, and actually play those impulse purchases gathering digital dust.

**The problem we solve:** You have 500+ games but play the same 5. You spend 30 minutes browsing, then give up. You bought that bundle but forgot what's in it. Sound familiar?

**The solution:** An intelligent assistant that knows your library inside and out. Ask questions in plain English like "What should I play tonight?" or "Find me something like Portal" and get instant, personalized recommendations based on your actual gaming history, available time, and current mood.

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

### 🎮 What You Can Do

#### Natural Language Search
Ask questions like a human, get answers like a friend:
- "What should I play tonight?" → Get personalized suggestions based on your mood
- "Find me something like Portal" → Discover similar games you already own
- "Chill puzzle games for 30 minutes" → Perfect matches for your available time
- "What co-op games do my friends have?" → Find games to play together

#### Smart Recommendations
- **Mood-based**: Feeling stressed? Get relaxing games. Want a challenge? Find your next obsession.
- **Time-aware**: Only have 20 minutes? No problem. Weekend free? Here's your next 100-hour RPG.
- **Family-friendly**: Safe recommendations for kids with age-appropriate filtering
- **Hidden gems**: Rediscover those forgotten purchases and unplayed classics

#### Library Intelligence  
- See what you've been playing and what you've been ignoring
- Track your gaming patterns and preferences over time
- Compare libraries with friends to find common games
- Get insights into your gaming personality and habits

### 🚀 Two Ways to Connect

We offer two server versions to ensure compatibility with your AI assistant:

1. **Full-Featured Server (Port 8000)**: Complete MCP implementation with advanced AI features
2. **Compatibility Server (Port 8001)**: Simplified version for Claude Desktop/Code - works perfectly out of the box!

#### Why Two Servers? The "Oops All Tools!" Story
Originally, I built Steam Librarian to showcase the full power of MCP - resources, prompts, completions, elicitations, sampling - the works! It was a beautiful example of what MCP could do. Then reality hit: even Anthropic's own apps (Claude Desktop and Claude Code) only reliably support tools. Resources? Hit or miss. Completions? Nope. Elicitations? Not yet.

So, like Cap'n Crunch's "Oops! All Berries" (where a "manufacturing error" created a cereal with only the best part), I created the compatibility server - internally called "Oops All Tools!" - that strips away everything except what actually works. It's not a limitation; it's a feature! By reimplementing everything as tools (all ~20 of them), we get perfect compatibility while keeping all the functionality.

Choose based on your client:
- Using Claude Desktop or Claude Code? → Use the Compatibility Server (port 8001)
- Using advanced MCP clients? → Use the Full-Featured Server (port 8000)

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
# Quick Start (15 minutes)

### 1. Install Steam Librarian

```bash
# Clone the repository
git clone https://github.com/jimsantora/steam-librarian.git
cd steam-librarian

# Install dependencies
pip install -r requirements.txt
```

### 2. Get Your Steam Credentials

You'll need two things:
- **Steam ID**: Find yours at [steamid.io](https://steamid.io/) - just enter your Steam profile URL
- **API Key**: Get one free at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)

Create a `.env` file:
```bash
STEAM_ID=76561197960287930    # Your Steam ID
STEAM_API_KEY=XXXXXXX          # Your API key
```

### 3. Download Your Game Library

```bash
# Fetch your Steam library (takes 2-5 minutes)
python src/fetcher/steam_library_fetcher.py

# Optional: Include friends' libraries for multiplayer recommendations
python src/fetcher/steam_library_fetcher.py --friends
```

### 4. Start the Server

**For Claude Desktop/Code users (recommended):**
```bash
# Run the compatibility server on port 8001
python src/oops_all_tools/run_server.py
```

**For advanced MCP clients:**
```bash
# Run the full-featured server on port 8000
python src/mcp_server/run_server.py
```

### 5. Connect Your AI Assistant

Configure your MCP client to connect to:
- Compatibility Server: `http://localhost:8001/mcp`
- Full Server: `http://localhost:8000/mcp`

That's it! Start asking questions about your Steam library.

<br>

---
# What Can I Ask?

Just talk to your AI assistant naturally. Here are some examples to get you started:

### 🎯 Finding Games
- "What should I play tonight?"
- "I have 30 minutes to kill, what can I play?"
- "Show me games like Hades"
- "What puzzle games do I own?"
- "Find me something relaxing"

### 👥 Social Gaming
- "What multiplayer games do my friends have?"
- "Show me co-op games we can play together"
- "What's everyone been playing lately?"
- "Find games that support 4 players"

### 📊 Library Insights
- "What games have I never played?"
- "Show me my most played games"
- "What did I buy but never install?"
- "How much is my library worth?"
- "What genres do I play most?"

### 👨‍👩‍👧‍👦 Family Gaming
- "Find kid-friendly games"
- "What can I play with my 8-year-old?"
- "Show me games without violence"
- "Find educational games"

<br>

---
# How It Works

Steam Librarian provides intelligent tools that your AI assistant uses behind the scenes:

### 🔍 Smart Search
Your AI understands natural language and translates it into precise searches:
- "relaxing games" → Finds casual, puzzle, and simulation games
- "quick multiplayer" → Filters for short-session online games
- "like Dark Souls" → Discovers challenging action RPGs
- "good for streaming" → Popular games with viewer appeal

### 💡 Intelligent Recommendations  
The AI learns from your library to suggest perfect matches:
- **Mood-based**: Analyzes game atmospheres and themes
- **Time-aware**: Respects your available gaming time
- **Pattern matching**: Finds games similar to your favorites
- **Hidden gems**: Surfaces forgotten purchases worth playing

### 📈 Library Analytics
Get insights about your gaming habits:
- Total value and hours played
- Most and least played games
- Genre preferences over time
- Comparison with friends' libraries

### 🎯 Which Server Should I Use?

**Compatibility Server (Port 8001)** - Best for most users:
- ✅ Works perfectly with Claude Desktop/Code
- ✅ Simple setup, no configuration needed
- ✅ All features via ~20 specialized tools
- ❌ No advanced MCP features

**Full Server (Port 8000)** - For power users:
- ✅ Complete MCP protocol support
- ✅ Advanced AI features (sampling, elicitation)
- ✅ Resource URIs for direct data access
- ⚠️ Limited support in some clients

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

### Common Issues & Quick Fixes

**"Connection refused" or server not responding**
- Make sure you started the server (step 4 in Quick Start)
- Check you're using the right port (8001 for compatibility, 8000 for full)
- Try: `curl http://localhost:8001/health` to test the connection

**"No games found" or empty responses**
- Did you run the fetcher? (`python src/fetcher/steam_library_fetcher.py`)
- Check your Steam profile is public (Settings → Privacy → Game Details: Public)
- Verify your `.env` file has the correct Steam ID and API key

**"User not found" errors**
- Set the `DEFAULT_USER` environment variable to your Steam ID
- Or ask your AI: "What users are available?" to see who's in the database

**Claude Desktop/Code not working**
- Use the compatibility server on port 8001 (not 8000)
- Run: `python src/oops_all_tools/run_server.py`
- Configure Claude to connect to `http://localhost:8001/mcp`

**Need more help?**
- Check the [detailed troubleshooting guide](deploy/README.md#troubleshooting)
- Open an issue on [GitHub](https://github.com/jimsantora/steam-librarian/issues)

<br>

---
# Technical Details

### Built With
- **Python 3.8+** with FastMCP (official MCP SDK)
- **SQLite** database with SQLAlchemy ORM
- **Docker** & **Kubernetes** ready for production
- **Comprehensive testing** with 50+ test cases

### Two-Server Architecture
We maintain two servers to maximize compatibility:

| Feature | Full Server | Compatibility Server |
|---------|------------|---------------------|
| **Port** | 8000 | 8001 |
| **Best For** | Advanced MCP clients | Claude Desktop/Code |
| **Tools** | 6 comprehensive | 20+ specialized |
| **Resources** | 13 endpoints | None (via tools) |
| **Advanced MCP** | Full support | Tools only |

### Performance
- Caches frequently accessed data for instant responses
- Handles large libraries (1000+ games) efficiently
- Lightweight SQLite database (~10-50MB typical)
- Fast startup (<2 seconds)

### Security & Privacy
- Your data stays local - no external services
- Steam API key never leaves your machine
- Read-only access to Steam data
- No telemetry or tracking

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
# Advanced Deployment

### 🐳 Docker (Easiest for Production)

Run everything in containers with a single command:

```bash
# Build and start both servers
make build-docker
make run-both-servers

# Or run just the compatibility server
make run-docker
```

Your servers will be available at:
- Compatibility: `http://localhost:8001/mcp`
- Full-featured: `http://localhost:8000/mcp`

### ☸️ Kubernetes with Helm

Deploy to your cluster with automatic data fetching:

```bash
# Install both servers
make helm-install-both

# Or just one server
helm install steam-librarian deploy/helm/steam-librarian \
  --set steam.steamId=YOUR_ID \
  --set steam.apiKey=YOUR_KEY
```

Features:
- Automatic daily library updates via CronJob
- Persistent storage for your game database
- Health monitoring and auto-restart
- Easy scaling and updates

### 🔧 Configuration Options

Set these environment variables to customize your setup:

```bash
DEFAULT_USER=your_steam_id     # Skip user selection prompts
MCP_PORT=8001                  # Change server port
DEBUG=true                      # Enable debug logging
DATABASE_URL=sqlite:///my.db   # Custom database location
```

**Need more details?** Check the [Deployment Guide](deploy/README.md) for complete instructions.

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

### Testing & Development

For developers and contributors:

```bash
# Quick checks before committing
make check                # Lint and format check

# Run tests
make test                 # Basic import test
make test-full           # Complete test suite

# Test specific servers
make test-tools          # Test compatibility server
make test-mcp-full       # Test full MCP server

# Development mode
DEBUG=true python src/oops_all_tools/run_server.py
```

<br>

---

### Contributing & Support

**Found a bug?** [Open an issue](https://github.com/jimsantora/steam-librarian/issues)

**Want to contribute?** Pull requests are welcome! Check out:
- [Development setup](src/mcp_server/README.md)
- [Database schema](src/shared/README.md)
- [Testing guide](#testing--development)

**Need help?**
- Read the [FAQ](#troubleshooting)
- Check the [Deployment Guide](deploy/README.md)
- Ask in [Discussions](https://github.com/jimsantora/steam-librarian/discussions)

### License

MIT License - See [LICENSE](LICENSE) file for details.

### Acknowledgments

Built with:
- [Anthropic MCP SDK](https://github.com/anthropics/mcp)
- [Steam Web API](https://steamcommunity.com/dev)
- [FastMCP](https://github.com/anthropics/fastmcp)
- The amazing Steam community