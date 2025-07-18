# Steam Librarian

A Go-based application for managing and serving Steam game library data with both web interface and MCP (Model Context Protocol) server capabilities.

## Features

- **Steam API Integration**: Fetch game library data from Steam Web API
- **Local Data Storage**: Store game information locally with database abstraction (SQLite, PostgreSQL, MySQL)
- **Web Interface**: RESTful API and web UI for browsing your game library
- **MCP Server**: Model Context Protocol server for AI integration
- **Game Metadata**: ESRB ratings, release dates, user reviews, descriptions, and more
- **Docker Support**: Containerized deployment with Docker and docker-compose
- **Kubernetes Ready**: Helm charts for Kubernetes deployment
- **Production Ready**: CI/CD pipelines, monitoring, and scalable architecture

## Quick Start

### Prerequisites

- Go 1.21 or later
- Steam API Key ([Get one here](https://steamcommunity.com/dev/apikey))
- Docker (optional, for containerized deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/jimsantora/steam-librarian.git
   cd steam-librarian
   ```

2. **Set up configuration**
   ```bash
   cp configs/config.yaml configs/config.local.yaml
   # Edit configs/config.local.yaml and add your Steam API key
   ```

3. **Install dependencies**
   ```bash
   go mod download
   ```

4. **Run the web server**
   ```bash
   export STEAM_API_KEY=your_steam_api_key_here
   go run cmd/web-server/main.go
   ```

5. **Run the MCP server** (in another terminal)
   ```bash
   export STEAM_API_KEY=your_steam_api_key_here
   go run cmd/mcp-server/main.go
   ```

The web interface will be available at `http://localhost:8080`.

### Docker Compose (Recommended)

1. **Set up environment**
   ```bash
   cd deployments/docker-compose
   cp .env.example .env
   # Edit .env and add your Steam API key
   ```

2. **Start all services**
   ```bash
   # For development (SQLite)
   docker-compose -f docker-compose.dev.yml up -d
   
   # For production (PostgreSQL)
   docker-compose up -d
   ```

3. **Access the application**
   - Web Interface: `http://localhost:8080`
   - Database: `localhost:5432` (PostgreSQL) or SQLite file in volume

## Configuration

Steam Librarian uses a hierarchical configuration system supporting YAML files and environment variables.

### Configuration File

Copy `configs/config.yaml` and customize:

```yaml
steam:
  api_key: "your_steam_api_key_here"
  sync_interval: "24h"

database:
  type: "sqlite"  # or "postgres", "mysql"
  file_path: "steam_librarian.db"

server:
  address: "localhost:8080"
  environment: "development"
```

### Environment Variables

Override any configuration with environment variables using the pattern `SECTION_SETTING`:

```bash
export STEAM_API_KEY=your_key_here
export DATABASE_TYPE=postgres
export DATABASE_HOST=localhost
export SERVER_ENVIRONMENT=production
```

## API Documentation

### REST API Endpoints

#### Libraries
- `GET /api/v1/libraries` - List all libraries
- `POST /api/v1/libraries` - Create a new library
- `GET /api/v1/libraries/{id}` - Get library details
- `PUT /api/v1/libraries/{id}` - Update library
- `DELETE /api/v1/libraries/{id}` - Delete library
- `POST /api/v1/libraries/{id}/sync` - Trigger library sync

#### Games
- `GET /api/v1/games` - List all games
- `GET /api/v1/games/{id}` - Get game details
- `PUT /api/v1/games/{id}` - Update game
- `DELETE /api/v1/games/{id}` - Delete game
- `POST /api/v1/games/{id}/sync` - Sync game details

#### Search
- `GET /api/v1/search/games?q=query` - Search games
- `GET /api/v1/search/libraries?q=query` - Search libraries

#### Statistics
- `GET /api/v1/stats/library/{id}` - Library statistics
- `GET /api/v1/stats/global` - Global statistics

### MCP Server

The MCP server provides AI-friendly access to Steam library data:

#### Methods
- `steam_librarian/list_libraries` - Get all libraries
- `steam_librarian/list_games` - Get all games (optionally filtered)
- `steam_librarian/get_library` - Get specific library
- `steam_librarian/get_game` - Get specific game
- `steam_librarian/sync_library` - Trigger library sync
- `steam_librarian/get_stats` - Get statistics

#### Example MCP Request
```json
{
  "jsonrpc": "2.0",
  "method": "steam_librarian/list_games",
  "params": {"library_id": "123"},
  "id": 1
}
```

## Architecture

```
┌─────────────────┐  ┌─────────────────┐
│   Web Server    │  │   MCP Server    │
│    (Gin)        │  │   (JSON-RPC)    │
└─────────┬───────┘  └─────────┬───────┘
          │                    │
          └────────┬───────────┘
                   │
        ┌─────────────────┐
        │  Storage Layer  │
        │    (GORM)       │
        └─────────┬───────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
┌─────▼───┐  ┌─────▼───┐  ┌─────▼───┐
│ SQLite  │  │ PostgreSQL │  │ MySQL   │
└─────────┘  └─────────┘  └─────────┘
```

### Key Components

- **Models**: GORM-based data models for games and libraries
- **Storage**: Database abstraction layer with repository pattern
- **Steam API**: HTTP client for Steam Web API integration
- **Web Server**: RESTful API and web interface using Gin
- **MCP Server**: JSON-RPC server for AI integration
- **Configuration**: Viper-based config management with environment override

## Deployment

### Kubernetes with Helm

1. **Add your Steam API key to values**
   ```bash
   helm upgrade --install steam-librarian deployments/helm/steam-librarian \
     --set secrets.steamApiKey.value=your_steam_api_key_here \
     --set postgresql.enabled=true
   ```

2. **For production deployment**
   ```bash
   helm upgrade --install steam-librarian deployments/helm/steam-librarian \
     --values production-values.yaml \
     --set secrets.steamApiKey.value=your_steam_api_key_here
   ```

### Docker

```bash
# Web server only
docker run -d \
  -p 8080:8080 \
  -e STEAM_API_KEY=your_key \
  -e DATABASE_TYPE=sqlite \
  -v steam_data:/data \
  ghcr.io/jimsantora/steam-librarian:latest

# Combined (web + MCP)
docker run -d \
  -p 8080:8080 \
  -e STEAM_API_KEY=your_key \
  ghcr.io/jimsantora/steam-librarian:latest-combined
```

## Development

### Project Structure

```
steam-librarian/
├── cmd/                    # Main applications
│   ├── web-server/        # Web interface server
│   └── mcp-server/        # MCP server
├── internal/              # Internal application code
│   ├── models/           # Data models
│   ├── storage/          # Database layer
│   ├── steam/            # Steam API client
│   ├── web/              # Web handlers
│   ├── mcp/              # MCP server
│   └── config/           # Configuration
├── deployments/          # Deployment configurations
│   ├── docker/           # Docker files
│   ├── docker-compose/   # Docker Compose
│   └── helm/             # Helm charts
├── web/                  # Static web assets
└── configs/              # Configuration files
```

### Building

```bash
# Build web server
go build -o web-server ./cmd/web-server

# Build MCP server
go build -o mcp-server ./cmd/mcp-server

# Build both with make
make build

# Build Docker images
docker build -f deployments/docker/Dockerfile --target web-server -t steam-librarian:web .
docker build -f deployments/docker/Dockerfile --target mcp-server -t steam-librarian:mcp .
```

### Testing

```bash
# Run tests
go test ./...

# Run tests with coverage
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out

# Run linting
golangci-lint run
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow Go best practices and idioms
- Write tests for new functionality
- Update documentation for API changes
- Use conventional commit messages
- Ensure CI passes before submitting PR

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Steam Web API](https://steamcommunity.com/dev) for game data
- [GORM](https://gorm.io/) for database abstraction
- [Gin](https://gin-gonic.com/) for web framework
- [Viper](https://github.com/spf13/viper) for configuration management

## Support

- Create an issue for bug reports or feature requests
- Check existing issues before creating new ones
- Provide detailed information for bug reports

---

**Note**: This is an independent project and is not affiliated with or endorsed by Valve Corporation or Steam.