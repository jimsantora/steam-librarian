# Steam Library Database Schema

## Overview

This document describes the relational database schema for the Steam Library MCP server, which stores Steam game library data in a normalized SQLite database using SQLAlchemy ORM.

## Schema Diagram

```
Steam Library Database Schema
============================

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   user_profile  │     │      games      │     │   game_reviews  │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ steam_id (PK)   │─┐   │ app_id (PK)     │──┬──│ app_id (PK,FK)  │
│ persona_name    │ │   │ name            │  │  │ review_summary  │
│ profile_url     │ │   │ maturity_rating │  │  │ review_score    │
│ avatar_url      │ │   │ required_age    │  │  │ total_reviews   │
│ avatarmedium    │ │   │ content_desc... │  │  │ positive_reviews│
│ avatarfull      │ │   │ release_date    │  │  │ negative_reviews│
│ time_created    │ │   │ metacritic_score│  │  │ last_updated    │
│ loccountrycode  │ │   │ steam_deck_ver. │  │  └─────────────────┘
│ locstatecode    │ │   │ controller_sup. │  │
│ xp              │ │   │ vr_support      │  │
│ steam_level     │ │   │ last_updated    │  │
│ last_updated    │ │   └─────────────────┘  │
└─────────────────┘ │                        │
         │          │                        │
         │          │   ┌─────────────────┐  │
         │          └──-│   user_games    │  │
         │              ├─────────────────┤  │
         │              │ steam_id (PK,FK)│  │
         │              │ app_id (PK,FK)  │──┘
         │              │ playtime_forever│
         │              │ playtime_2weeks │
         │              └─────────────────┘
         │
         │   ┌─────────────────┐
         └──-│     friends     │
             ├─────────────────┤
             │ user_steam_id   │
             │ (PK,FK)         │
             │ friend_steam_id │
             │ (PK,FK)         │
             │ relationship    │
             │ friend_since    │
             └─────────────────┘

Many-to-Many Relationship Tables:
                        
┌─────────────────┐                    ┌─────────────────┐
│     genres      │                    │  game_genres    │
├─────────────────┤     ┌─────────────────┐     ┌─────────────────┐
│ genre_id (PK)   │────-│ app_id (PK,FK)  │     │ app_id (PK,FK)  │
│ genre_name      │     │ genre_id (PK,FK)│──-──│ genre_id (PK,FK)│
└─────────────────┘     └─────────────────┘     └─────────────────┘

┌─────────────────┐                    ┌─────────────────┐
│   developers    │                    │ game_developers │
├─────────────────┤     ┌─────────────────┐     ┌─────────────────┐
│ developer_id(PK)│──-──│ app_id (PK,FK)  │     │ app_id (PK,FK)  │
│ developer_name  │     │ developer_id    │──-──│ developer_id    │
└─────────────────┘     │ (PK,FK)         │     │ (PK,FK)         │
                        └─────────────────┘     └─────────────────┘

┌─────────────────┐                    ┌─────────────────┐
│   publishers    │                    │ game_publishers │
├─────────────────┤     ┌─────────────────┐     ┌─────────────────┐
│ publisher_id(PK)│────-│ app_id (PK,FK)  │     │ app_id (PK,FK)  │
│ publisher_name  │     │ publisher_id    │──-──│ publisher_id    │
└─────────────────┘     │ (PK,FK)         │     │ (PK,FK)         │
                        └─────────────────┘     └─────────────────┘

┌─────────────────┐                    ┌─────────────────┐
│   categories    │                    │ game_categories │
├─────────────────┤     ┌─────────────────┐     ┌─────────────────┐
│ category_id(PK) │──-──│ app_id (PK,FK)  │     │ app_id (PK,FK)  │
│ category_name   │     │ category_id     │──-──│ category_id     │
└─────────────────┘     │ (PK,FK)         │     │ (PK,FK)         │
                        └─────────────────┘     └─────────────────┘
```

## Table Descriptions

### Core Tables

#### `user_profile`
Stores Steam user account information.

| Column | Type | Description |
|--------|------|-------------|
| `steam_id` | STRING (PK) | 64-bit Steam ID |
| `persona_name` | STRING | Steam display name |
| `profile_url` | STRING | Steam profile URL |
| `avatar_url` | STRING | Small profile avatar image URL |
| `avatarmedium` | STRING | Medium profile avatar image URL |
| `avatarfull` | STRING | Full/large profile avatar image URL |
| `time_created` | INTEGER | Unix timestamp of account creation |
| `loccountrycode` | STRING | Country code (e.g., "US") if public |
| `locstatecode` | STRING | State/region code (e.g., "CA") if public |
| `xp` | INTEGER | Raw Steam XP value |
| `steam_level` | INTEGER | Steam level calculated from XP |
| `last_updated` | INTEGER | Unix timestamp of last profile update |

#### `games`
Central table storing game metadata.

| Column | Type | Description |
|--------|------|-------------|
| `app_id` | INTEGER (PK) | Steam application ID |
| `name` | STRING | Game title |
| `maturity_rating` | STRING | ESRB/age rating |
| `required_age` | INTEGER | Minimum age requirement |
| `content_descriptors` | TEXT | Content warnings/descriptors |
| `release_date` | STRING | Game release date |
| `metacritic_score` | INTEGER | Metacritic review score |
| `steam_deck_verified` | BOOLEAN | Steam Deck compatibility |
| `controller_support` | STRING | Controller support level |
| `vr_support` | BOOLEAN | VR compatibility |
| `last_updated` | INTEGER | Unix timestamp of last update |

#### `user_games`
Junction table linking users to their owned games with playtime data.

| Column | Type | Description |
|--------|------|-------------|
| `steam_id` | STRING (PK, FK) | References `user_profile.steam_id` |
| `app_id` | INTEGER (PK, FK) | References `games.app_id` |
| `playtime_forever` | INTEGER | Total playtime in minutes |
| `playtime_2weeks` | INTEGER | Recent playtime in minutes |

#### `game_reviews`
Review and rating data for games (one-to-one with games).

| Column | Type | Description |
|--------|------|-------------|
| `app_id` | INTEGER (PK, FK) | References `games.app_id` |
| `review_summary` | STRING | Text summary (e.g., "Very Positive") |
| `review_score` | INTEGER | Numeric review score |
| `total_reviews` | INTEGER | Total number of reviews |
| `positive_reviews` | INTEGER | Count of positive reviews |
| `negative_reviews` | INTEGER | Count of negative reviews |
| `last_updated` | INTEGER | Unix timestamp of last update |

### Metadata Tables (Many-to-Many)

#### `genres` & `game_genres`
Game genre classifications.

| Table | Column | Type | Description |
|-------|--------|------|-------------|
| `genres` | `genre_id` | INTEGER (PK) | Auto-incrementing ID |
| `genres` | `genre_name` | STRING | Genre name (e.g., "Action", "RPG") |
| `game_genres` | `app_id` | INTEGER (PK, FK) | References `games.app_id` |
| `game_genres` | `genre_id` | INTEGER (PK, FK) | References `genres.genre_id` |

#### `developers` & `game_developers`
Game development companies.

| Table | Column | Type | Description |
|-------|--------|------|-------------|
| `developers` | `developer_id` | INTEGER (PK) | Auto-incrementing ID |
| `developers` | `developer_name` | STRING | Developer name |
| `game_developers` | `app_id` | INTEGER (PK, FK) | References `games.app_id` |
| `game_developers` | `developer_id` | INTEGER (PK, FK) | References `developers.developer_id` |

#### `publishers` & `game_publishers`
Game publishing companies.

| Table | Column | Type | Description |
|-------|--------|------|-------------|
| `publishers` | `publisher_id` | INTEGER (PK) | Auto-incrementing ID |
| `publishers` | `publisher_name` | STRING | Publisher name |
| `game_publishers` | `app_id` | INTEGER (PK, FK) | References `games.app_id` |
| `game_publishers` | `publisher_id` | INTEGER (PK, FK) | References `publishers.publisher_id` |

#### `categories` & `game_categories`
Steam categories (Single-player, Multiplayer, etc.).

| Table | Column | Type | Description |
|-------|--------|------|-------------|
| `categories` | `category_id` | INTEGER (PK) | Auto-incrementing ID |
| `categories` | `category_name` | STRING | Category name |
| `game_categories` | `app_id` | INTEGER (PK, FK) | References `games.app_id` |
| `game_categories` | `category_id` | INTEGER (PK, FK) | References `categories.category_id` |

### `friends`
Association table for user friendships.

| Column | Type | Description |
|--------|------|-------------|
| `user_steam_id` | STRING (PK, FK) | References `user_profile.steam_id` |
| `friend_steam_id` | STRING (PK, FK) | References `user_profile.steam_id` |
| `relationship` | STRING | Relationship type (e.g., "friend", "all") |
| `friend_since` | INTEGER | Unix timestamp when friendship began |

## Relationships

### Key Relationships
- **user_profile ──< user_games >── games**: Many-to-Many through user_games junction table
- **user_profile ──< friends >── user_profile**: Many-to-Many self-referencing friendship table
- **games ──< game_reviews**: One-to-One relationship
- **games ──< game_genres >── genres**: Many-to-Many relationship
- **games ──< game_developers >── developers**: Many-to-Many relationship  
- **games ──< game_publishers >── publishers**: Many-to-Many relationship
- **games ──< game_categories >── categories**: Many-to-Many relationship

### Legend
- **PK** = Primary Key
- **FK** = Foreign Key
- **──<** = One-to-Many relationship
- **>──** = Many-to-One relationship
- **>──<** = Many-to-Many relationship

## Indexes

The following indexes are automatically created for performance optimization:

```sql
-- Game indexes
CREATE INDEX idx_games_name ON games(name);
CREATE INDEX idx_games_maturity_rating ON games(maturity_rating);

-- User games indexes
CREATE INDEX idx_user_games_steam_id ON user_games(steam_id);
CREATE INDEX idx_user_games_app_id ON user_games(app_id);
CREATE INDEX idx_user_games_playtime_forever ON user_games(playtime_forever);
CREATE INDEX idx_user_games_playtime_2weeks ON user_games(playtime_2weeks);

-- Friends indexes
CREATE INDEX idx_friends_user_steam_id ON friends(user_steam_id);
CREATE INDEX idx_friends_friend_steam_id ON friends(friend_steam_id);
```

## Current Data Volume

Based on the migrated data:
- **Games**: 1,111
- **Genres**: 19
- **Developers**: 845
- **Publishers**: 574
- **User Games**: 1,111 (for current user)

## Design Benefits

### 1. **Eliminates Redundancy**
- No duplicate genre/developer names across games
- Normalized metadata reduces storage requirements

### 2. **Enforces Data Integrity**
- Foreign key relationships prevent orphaned records
- ACID compliance ensures consistent data state

### 3. **Enables Complex Queries**
- Easy to find games by multiple criteria
- Efficient joins for comprehensive game data

### 4. **Supports Multiple Users**
- Can track multiple Steam accounts
- User-specific playtime and ownership data

### 5. **Optimized for Performance**
- Proper indexing on frequently queried fields
- Efficient many-to-many relationships

### 6. **Future Extensibility**
- Easy to add new game metadata
- Support for additional user data
- Historical tracking capabilities
