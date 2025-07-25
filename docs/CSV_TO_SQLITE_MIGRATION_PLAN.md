# CSV to SQLite Migration Plan

This document outlines the migration strategy from CSV-based storage to SQLite for the Steam Library MCP server.

## Why SQLite?

### Current CSV Limitations
- Single flat table structure
- No relationships between data
- Difficult to update individual records
- No query optimization
- Limited data types
- Poor handling of missing data
- No transaction support

### SQLite Benefits
- Relational data model with foreign keys
- ACID compliance for data integrity
- Efficient indexes for fast queries
- Native datetime handling
- Better NULL value support
- Concurrent read access
- Built-in aggregation functions
- Prepared statements prevent SQL injection

## Database Schema Design

### Core Tables

```sql
-- User profile information
CREATE TABLE user_profile (
    steam_id TEXT PRIMARY KEY,
    persona_name TEXT,
    profile_url TEXT,
    avatar_url TEXT,
    account_created INTEGER,
    steam_level INTEGER,
    last_updated INTEGER
);

-- Games library
CREATE TABLE games (
    app_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    maturity_rating TEXT,
    required_age INTEGER,
    content_descriptors TEXT,
    release_date TEXT,
    metacritic_score INTEGER,
    steam_deck_verified BOOLEAN,
    controller_support TEXT,
    vr_support BOOLEAN,
    last_updated INTEGER
);

-- User's game ownership and playtime
CREATE TABLE user_games (
    steam_id TEXT,
    app_id INTEGER,
    playtime_forever INTEGER DEFAULT 0,
    playtime_2weeks INTEGER DEFAULT 0,
    last_played INTEGER,
    purchase_date INTEGER,
    purchase_price REAL,
    PRIMARY KEY (steam_id, app_id),
    FOREIGN KEY (steam_id) REFERENCES user_profile(steam_id),
    FOREIGN KEY (app_id) REFERENCES games(app_id)
);

-- Game metadata (many-to-many relationships)
CREATE TABLE genres (
    genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_name TEXT UNIQUE NOT NULL
);

CREATE TABLE game_genres (
    app_id INTEGER,
    genre_id INTEGER,
    PRIMARY KEY (app_id, genre_id),
    FOREIGN KEY (app_id) REFERENCES games(app_id),
    FOREIGN KEY (genre_id) REFERENCES genres(genre_id)
);

CREATE TABLE developers (
    developer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_name TEXT UNIQUE NOT NULL
);

CREATE TABLE game_developers (
    app_id INTEGER,
    developer_id INTEGER,
    PRIMARY KEY (app_id, developer_id),
    FOREIGN KEY (app_id) REFERENCES games(app_id),
    FOREIGN KEY (developer_id) REFERENCES developers(developer_id)
);

CREATE TABLE publishers (
    publisher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    publisher_name TEXT UNIQUE NOT NULL
);

CREATE TABLE game_publishers (
    app_id INTEGER,
    publisher_id INTEGER,
    PRIMARY KEY (app_id, publisher_id),
    FOREIGN KEY (app_id) REFERENCES games(app_id),
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id)
);

-- Reviews and ratings
CREATE TABLE game_reviews (
    app_id INTEGER PRIMARY KEY,
    review_summary TEXT,
    review_score INTEGER,
    total_reviews INTEGER,
    positive_reviews INTEGER,
    negative_reviews INTEGER,
    last_updated INTEGER,
    FOREIGN KEY (app_id) REFERENCES games(app_id)
);

-- Categories (Single-player, Multiplayer, etc.)
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT UNIQUE NOT NULL
);

CREATE TABLE game_categories (
    app_id INTEGER,
    category_id INTEGER,
    PRIMARY KEY (app_id, category_id),
    FOREIGN KEY (app_id) REFERENCES games(app_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- Indexes for performance
CREATE INDEX idx_user_games_playtime ON user_games(playtime_forever DESC);
CREATE INDEX idx_user_games_recent ON user_games(playtime_2weeks DESC);
CREATE INDEX idx_games_name ON games(name);
CREATE INDEX idx_game_reviews_summary ON game_reviews(review_summary);
```

## Migration Steps

### Phase 1: Database Setup
1. **Create SQLite database file** (`steam_library.db`)
2. **Execute schema creation** scripts
3. **Add database connection** to both fetcher and server

### Phase 2: Data Migration Script
1. **Read existing CSV** data
2. **Parse and normalize** data:
   - Split comma-separated genres, developers, publishers
   - Convert date formats
   - Handle NULL/empty values
3. **Insert into SQLite**:
   - Use transactions for atomicity
   - Batch inserts for performance
   - Handle duplicates gracefully

### Phase 3: Update Fetcher
1. **Replace CSV writing** with database inserts
2. **Use transactions** for each game update
3. **Implement upsert logic** for updates
4. **Add error handling** and rollback

### Phase 4: Update MCP Server
1. **Replace pandas DataFrame** with SQLite queries
2. **Rewrite each tool** to use SQL
3. **Add connection pooling** for performance
4. **Implement query builders** for complex filters

### Phase 5: Testing & Validation
1. **Data integrity checks**:
   - Verify all CSV data migrated
   - Check foreign key constraints
   - Validate data types
2. **Performance testing**:
   - Query response times
   - Memory usage comparison
3. **Feature parity**:
   - All MCP tools work identically
   - No regressions in functionality

## Implementation Files

### New Files to Create
1. `database.py` - Database schema and connection management
2. `migrate_csv_to_sqlite.py` - One-time migration script
3. `models.py` - SQLAlchemy models (optional, for ORM approach)

### Files to Modify
1. `steam_library_fetcher.py` - Write to SQLite instead of CSV
2. `mcp_server.py` - Query SQLite instead of pandas DataFrame
3. `requirements.txt` - Add sqlite3 (built-in) or SQLAlchemy

## Code Examples

### Database Connection
```python
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('steam_library.db')
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
    finally:
        conn.close()
```

### Fetcher Update Example
```python
def save_game_to_db(game_data: Dict):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Insert or update game
        cursor.execute("""
            INSERT OR REPLACE INTO games 
            (app_id, name, maturity_rating, required_age, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (game_data['appid'], game_data['name'], 
              game_data['maturity_rating'], game_data['required_age'],
              int(time.time())))
        
        # Handle genres (many-to-many)
        for genre in game_data['genres'].split(', '):
            cursor.execute(
                "INSERT OR IGNORE INTO genres (genre_name) VALUES (?)", 
                (genre.strip(),)
            )
            # Link game to genre
            cursor.execute("""
                INSERT OR IGNORE INTO game_genres (app_id, genre_id)
                SELECT ?, genre_id FROM genres WHERE genre_name = ?
            """, (game_data['appid'], genre.strip()))
        
        conn.commit()
```

### MCP Server Query Example
```python
@mcp.tool
def search_games(query: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        results = cursor.execute("""
            SELECT DISTINCT g.app_id, g.name, 
                   GROUP_CONCAT(DISTINCT gn.genre_name) as genres,
                   r.review_summary,
                   ug.playtime_forever / 60.0 as playtime_hours
            FROM games g
            LEFT JOIN user_games ug ON g.app_id = ug.app_id
            LEFT JOIN game_reviews r ON g.app_id = r.app_id
            LEFT JOIN game_genres gg ON g.app_id = gg.app_id
            LEFT JOIN genres gn ON gg.genre_id = gn.genre_id
            WHERE g.name LIKE ? OR gn.genre_name LIKE ?
            GROUP BY g.app_id
            ORDER BY ug.playtime_forever DESC
        """, (f'%{query}%', f'%{query}%'))
        
        return [dict(row) for row in results]
```

## Migration Timeline

1. **Day 1**: Create database schema and migration script
2. **Day 2**: Update fetcher to write to SQLite
3. **Day 3**: Update MCP server to read from SQLite
4. **Day 4**: Testing and validation
5. **Day 5**: Deploy and monitor

## Rollback Plan

1. Keep CSV export functionality temporarily
2. Maintain CSV compatibility mode flag
3. Daily SQLite backups
4. Test migration on sample data first

## Future Enhancements Enabled by SQLite

1. **Historical tracking**: Store price/playtime history
2. **Multi-user support**: Multiple Steam accounts
3. **Achievement tracking**: New tables for achievement data
4. **Friends integration**: Friend relationships and shared games
5. **Custom tags**: User-defined game categories
6. **Play session tracking**: Start/end times if available
7. **Wishlist management**: Track wanted games
8. **Statistics views**: Pre-calculated analytics tables