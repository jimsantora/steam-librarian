# Steam Library Fetcher

## Overview

The Steam Library Fetcher is a comprehensive data collection module that retrieves detailed Steam game library information using Steam's official Web API and Store API. It fetches user profile data, game metadata, reviews, and social connections, storing everything in a normalized SQLite database.

## Features

### Core Functionality
- **User Profile Management**: Fetches Steam user profiles with XP, level, and avatar data
- **Game Library Processing**: Retrieves complete game collections with detailed metadata
- **Friends Network**: Optionally fetches friend lists and their game libraries
- **Intelligent Caching**: Configurable cache system to avoid unnecessary API calls
- **Rate Limiting**: Built-in delays to respect Steam API limits
- **Robust Error Handling**: Graceful handling of API failures with fallback data

### Rich Game Metadata
The fetcher extracts comprehensive game information from Steam's APIs:

#### From Steam Store API (`appdetails`)
- **Basic Info**: Game name, description, release date
- **Media**: Header images and screenshots
- **Platform Support**: Windows, macOS, Linux compatibility
- **Ratings & Reviews**: ESRB/PEGI ratings with content descriptors
- **Social Data**: User recommendation counts
- **Accessibility**: Controller support levels, VR compatibility
- **External Links**: Metacritic scores and review URLs
- **Content Organization**: Genres, categories, developers, publishers

#### From Steam Web API (`GetOwnedGames`)
- **Ownership Data**: User's owned games list
- **Playtime Statistics**: Total and recent (2-week) playtime
- **Account Details**: Steam level, XP, profile information

#### From Steam Reviews API (`appreviews`)
- **Review Summaries**: Overall review sentiment
- **Review Statistics**: Total, positive, and negative review counts
- **Review Scores**: Numerical review ratings

## Architecture

### Class Structure

```python
class SteamLibraryFetcher:
    def __init__(self, api_key: str)
    
    # Core API Methods
    def get_owned_games(self, steam_id: str) -> list[dict]
    def get_app_details(self, appid: int) -> dict | None
    def get_app_reviews(self, appid: int) -> dict | None
    def get_player_summaries(self, steam_ids: str) -> list[dict]
    def get_player_badges(self, steam_id: str) -> dict | None
    def get_friend_list(self, steam_id: str) -> list[dict]
    
    # Data Processing
    def process_game(self, game: dict, index: int, total: int) -> dict
    def save_to_database(self, game_data: dict, steam_id: str)
    def save_user_profile(self, player_data: dict, steam_id: str, include_badges: bool)
    
    # Main Workflows
    def fetch_library_data(self, steam_id: str)
    def process_friends_data(self, user_steam_id: str, batch_size: int = 100)
```

### Data Flow

```
1. User Profile → Steam Web API → Database (user_profile table)
2. Game Library → Steam Web API → Game Processing Loop
3. For Each Game:
   ├── Game Details → Steam Store API → Parse metadata
   ├── Game Reviews → Steam Reviews API → Parse review data
   ├── Data Validation → Clean and normalize
   └── Database Storage → Save to normalized schema
4. Friends (Optional) → Batch process friend profiles and libraries
```

## Configuration

### Environment Variables
- `STEAM_ID`: Your Steam ID (required)
- `STEAM_API_KEY`: Steam Web API key (required)
- `DATABASE_URL`: Database connection string (optional, defaults to local SQLite)
- `CACHE_DAYS`: Cache threshold in days (optional, default: 7)

### Command Line Options
- `--debug`: Enable debug logging
- `--cache-days N`: Set cache threshold (overrides env var)
- `--force-refresh`: Force refresh all game data, ignoring cache
- `--skip-games`: Skip fetching game details entirely
- `--friends`: Also fetch friends list and their game libraries

## Usage

### Basic Usage
```bash
# Set environment variables in .env file
STEAM_ID=76561198020403796
STEAM_API_KEY=your_steam_api_key_here

# Run the fetcher
python src/fetcher/steam_library_fetcher.py
```

### Advanced Usage
```bash
# Force refresh all data
python src/fetcher/steam_library_fetcher.py --force-refresh

# Include friends data
python src/fetcher/steam_library_fetcher.py --friends

# Custom cache settings with debug output
python src/fetcher/steam_library_fetcher.py --cache-days 14 --debug

# Skip game details (fast profile-only update)
python src/fetcher/steam_library_fetcher.py --skip-games
```

### Docker Usage
```bash
# Via Docker Compose
docker-compose up fetcher

# Run with custom cache settings
CACHE_DAYS=14 docker-compose up fetcher

# Include friends data
docker-compose run fetcher python src/fetcher/steam_library_fetcher.py --friends
```

## Caching Strategy

### Smart Caching System
- **Game-Level Caching**: Each game tracks its last update timestamp
- **Configurable Threshold**: Skip API calls for recently fetched games
- **Force Refresh Option**: Override cache for complete data refresh
- **Selective Updates**: Only update playtime for cached games

### Cache Behavior
```python
# Default: Skip games updated within 7 days
if game.last_updated and (now - game.last_updated) < cache_threshold:
    return cached_data

# Force refresh: Always fetch fresh data
if args.force_refresh:
    fetch_fresh_data()

# Skip games: Only update playtime, no API calls
if args.skip_games:
    update_playtime_only()
```

## Rate Limiting

### API Limits
- **Steam Web API**: ~200 requests per 5 minutes
- **Steam Store API**: ~1 request per second (recommended)
- **Built-in Delays**: 1 second between API calls
- **Exponential Backoff**: Automatic retry with increasing delays

### Performance Optimization
```python
# Progress tracking for large libraries
logger.info(f"Processing [{index}/{total}]: {game_name}")

# Estimated completion time
if index % 10 == 0:
    estimated_time = (total - index) * rate_limit_delay
    logger.info(f"Estimated time remaining: {estimated_time:.0f} seconds")
```

## Error Handling

### Robust Error Recovery
- **API Failures**: Continue processing other games, save fallback data
- **Network Issues**: Retry with exponential backoff
- **Database Errors**: Transaction rollback and retry
- **Partial Failures**: Save what data is available, log issues

### Fallback Strategy
```python
try:
    game_data = self.process_game(game, index, total)
    self.save_to_database(game_data, steam_id)
except Exception as e:
    # Save minimal fallback data
    fallback_data = {
        "appid": game.get("appid"),
        "name": game.get("name", "Unknown"),
        "playtime_forever": game.get("playtime_forever", 0),
        # ... minimal required fields
    }
    self.save_to_database(fallback_data, steam_id)
```

## Database Integration

### Normalized Data Storage
- **User Profiles**: Steam account information and statistics
- **Games**: Comprehensive game metadata with relationships
- **Reviews**: Separate table for review data
- **Many-to-Many**: Genres, developers, publishers, categories
- **Social**: Friends relationships and their libraries

### Transaction Management
```python
with get_db_transaction() as session:
    # All database operations are atomic
    # Automatic rollback on errors
    # Proper connection management
```

## Friends Network Processing

### Batch Processing
- **Configurable Batch Size**: Default 100 friends per API call
- **Privacy Handling**: Skips private profiles automatically
- **Efficient API Usage**: Single API call for multiple friend profiles
- **Recursive Processing**: Friends' games processed with same caching logic

### Social Graph Storage
```python
# Friend relationships
friends_association = Table("friends", 
    Column("user_steam_id", String, ForeignKey("user_profile.steam_id")),
    Column("friend_steam_id", String, ForeignKey("user_profile.steam_id")),
    Column("relationship", String),
    Column("friend_since", Integer)
)
```

## Monitoring & Logging

### Comprehensive Logging
- **Progress Tracking**: Real-time processing status
- **Performance Metrics**: API response times and success rates
- **Error Reporting**: Detailed error context and recovery actions
- **Cache Statistics**: Hit/miss ratios and refresh counts

### Log Levels
```python
# INFO: Progress updates and major milestones
logger.info(f"Starting Steam Library Fetcher for Steam ID: {steam_id}")

# DEBUG: API requests and responses
logger.debug(f"Request URL: {url}")
logger.debug(f"Response: {response.json()}")

# WARNING: Recoverable issues
logger.warning(f"API returned {response.status_code}, retrying...")

# ERROR: Serious issues requiring attention
logger.error(f"Failed to process game {game_name}: {error}")
```

## Performance Characteristics

### Typical Performance
- **Small Library** (100 games): ~2-3 minutes
- **Medium Library** (500 games): ~8-10 minutes  
- **Large Library** (1000+ games): ~15-20 minutes
- **With Caching**: Subsequent runs 80-90% faster

### Optimization Features
- **Intelligent Caching**: Dramatically reduces API calls
- **Batch Processing**: Efficient friend profile fetching
- **Progress Indicators**: Real-time status updates
- **Concurrent Safe**: Multiple fetcher instances handle locking

## Version History

### v1.1.3+ (Current)
- **Enhanced Metadata**: Added detailed descriptions, recommendations, platform support
- **Official Ratings**: ESRB and PEGI rating extraction
- **Accessibility**: Controller and VR support detection
- **Media URLs**: Header images and Metacritic links
- **Improved Caching**: Game-level cache validation

### Previous Versions
- **v1.1.2**: Added friends network processing
- **v1.1.1**: Improved error handling and rate limiting
- **v1.1.0**: Initial release with basic game library fetching

## Dependencies

### Core Requirements
- `requests`: HTTP client for API calls
- `sqlalchemy`: Database ORM and connection management
- `python-dotenv`: Environment variable management

### Steam APIs Used
- **Steam Web API**: User profiles, game ownership, friends
- **Steam Store API**: Game details, metadata, media
- **Steam Reviews API**: Review summaries and statistics

## Best Practices

### API Key Security
- Store API keys in `.env` files (never commit to version control)
- Use environment variables in production
- Rotate keys periodically

### Performance Optimization
- Use caching to minimize API calls
- Run during off-peak hours for large libraries
- Monitor rate limits and adjust delays if needed

### Data Quality
- Validate API responses before database storage
- Handle missing or malformed data gracefully
- Log data quality issues for investigation

## Troubleshooting

### Common Issues
- **API Key Invalid**: Verify key is correct and active
- **Private Profile**: Ensure Steam profile is public
- **Rate Limited**: Increase delays between API calls
- **Database Locked**: Check for other running fetcher instances

### Debug Mode
```bash
# Enable detailed logging
python src/fetcher/steam_library_fetcher.py --debug

# Check API responses
DEBUG=true LOG_LEVEL=DEBUG python src/fetcher/steam_library_fetcher.py
```