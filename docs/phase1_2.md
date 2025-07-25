# Phase 1.2: Friends and Social Data Implementation Plan

## Overview
Implement friends list functionality with shared game analysis, maintaining the existing many-to-many relationship between users and games. The system will support multiple users with dynamic perspective switching via MCP prompts.

## Current Status
- ✅ Friend model added to database schema
- ✅ Cache control logic implemented in fetcher
- ✅ Command-line arguments added for cache control
- ✅ Basic friends API integration started
- ⏳ Need to complete friends fetching functionality
- ⏳ Need to implement MCP prompt-based user selection

## Database Architecture

### Completed Changes
```python
class Friend(Base):
    __tablename__ = 'friends'
    
    user_steam_id = Column(String, ForeignKey('user_profile.steam_id'), primary_key=True)
    friend_steam_id = Column(String, ForeignKey('user_profile.steam_id'), primary_key=True)
    relationship = Column(String)  # 'friend' or 'all'
    friend_since = Column(Integer)  # Unix timestamp
    
    # Relationships
    user = relationship("UserProfile", foreign_keys=[user_steam_id], back_populates="friends")
    friend_profile = relationship("UserProfile", foreign_keys=[friend_steam_id], back_populates="friend_of")
```

### Key Design Decisions
- **No "main user" flag in database** - keeps data flexible
- **Many-to-many user-game relationships** - no game duplication
- **Friend relationships are directional** - user A -> friend B
- **All users stored in same UserProfile table** - unified data model

## Fetcher Updates

### Completed Features
1. **Cache Control**
   - `--cache-days N`: Only re-fetch games older than N days
   - `--force-refresh`: Ignore cache, fetch everything fresh
   - `--skip-games`: Don't fetch any game details at all
   - `--friends`: Also fetch friends list and their game libraries

2. **API Methods Added**
   - `get_friend_list(steam_id)`: Fetch friends from Steam API
   - `get_player_summaries(steam_ids)`: Batch fetch user profiles (supports single or multiple IDs)
   - `_is_game_cached(app_id)`: Check if game data is fresh enough to skip API calls

### Still Need to Implement
3. **Friends Processing**
   ```python
   def process_friends_data(self, user_steam_id: str):
       """Fetch and process friends list and their games"""
       # 1. Get friend list via Steam API
       # 2. Save friend relationships to database
       # 3. Batch fetch friend profiles (100 at a time)
       # 4. For each friend with public profile:
       #    - Save their UserProfile
       #    - Fetch their games using existing logic
       #    - Apply same caching rules as main user
   ```

4. **Refactored User Profile Handling**
   ```python
   def save_user_profile(self, player_data: Dict, steam_id: str):
       """Save or update a user profile (reusable for friends and main user)"""
       # Replace duplicate code in fetch_library_data()
   ```

## MCP Server Updates

### Multi-User Architecture
The MCP server will support multiple users stored in the same database with dynamic perspective switching:

1. **User Selection Prompt**
   ```python
   @mcp.prompt
   def select_user_prompt() -> str:
       """Prompt to select which user to use for the query"""
       with get_db() as session:
           users = session.query(UserProfile).all()
           user_list = "\n".join([
               f"- {user.persona_name} ({user.steam_id})" 
               for user in users
           ])
       
       return f"""Please select a user for this query:

   {user_list}

   Enter the Steam ID of the user you want to use:"""
   ```

2. **Updated Tool Pattern**
   ```python
   @mcp.tool
   def get_friends_data(
       data_type: Annotated[str, "Type: 'list', 'common_games', 'who_owns_game', 'library_comparison'"],
       user_steam_id: Annotated[Optional[str], "Steam ID of user (leave empty to be prompted)"] = None,
       friend_steam_id: Annotated[Optional[str], "Friend's Steam ID for specific queries"] = None,
       game_identifier: Annotated[Optional[str], "Game name or appid for game-specific queries"] = None
   ) -> Union[List[Dict], Dict[str, Any]]:
       if not user_steam_id:
           user_steam_id = select_user_prompt()
       
       # Execute query from that user's perspective
   ```

### New Tools to Implement
1. **get_all_users()** - List available user profiles
2. **get_friends_data()** - Unified friends tool with multiple data types:
   - `list`: Return all friends with basic info
   - `common_games`: Games owned by both user and specific friend
   - `who_owns_game`: Friends who own a specific game
   - `library_comparison`: Detailed comparison with a friend

### Existing Tools to Update
All existing tools need optional `user_steam_id` parameter with prompt fallback:
- `search_games()`
- `filter_games()`
- `get_game_details()`
- `get_library_stats()`
- `get_recently_played()`
- `get_recommendations()`
- `get_user_info()`

## Implementation Steps

### Phase 1: Complete Fetcher
1. ✅ Add Friend model and relationships
2. ✅ Implement cache control logic
3. ⏳ Add `process_friends_data()` method
4. ⏳ Add `save_user_profile()` method
5. ⏳ Update `fetch_library_data()` to use refactored profile saving
6. ⏳ Test friends fetching with various profile visibility settings

### Phase 2: Update MCP Server
1. ⏳ Add user selection prompt
2. ⏳ Implement `get_all_users()` tool
3. ⏳ Implement `get_friends_data()` tool
4. ⏳ Update all existing tools to support multi-user
5. ⏳ Test prompt-based user selection

### Phase 3: Testing & Polish
1. ⏳ Test with multiple users in database
2. ⏳ Test friends with various privacy settings
3. ⏳ Verify cache control works correctly for friends
4. ⏳ Performance testing with large friend lists
5. ⏳ Documentation updates

## Usage Examples

### Fetching Data
```bash
# Fetch main user + friends with 3-day cache
python steam_library_fetcher.py --friends --cache-days 3

# Force refresh everything including friends
python steam_library_fetcher.py --friends --force-refresh

# Skip game details, just get user profiles and relationships
python steam_library_fetcher.py --friends --skip-games
```

### MCP Queries
```
User: "Show me games that my friends own that I don't"
Assistant: I'll need to know which user profile to use. Let me get the available users...
[MCP prompt shows list of users]
User: "76561197960435530"
Assistant: [Returns games owned by friends but not by specified user]
```

## Key Benefits

1. **Flexible Multi-User Support**: One database serves multiple Steam users
2. **Dynamic Perspective Switching**: Client can change viewpoint during conversation
3. **Efficient Caching**: Minimize API calls through intelligent cache management
4. **Privacy Aware**: Gracefully handles private friend profiles
5. **Scalable**: Batch processing for large friend lists
6. **Backwards Compatible**: Existing functionality unchanged

## Technical Considerations

- **Rate Limiting**: Steam API allows 100,000 requests/day - batch calls help stay under limits
- **Privacy**: Only processes friends with public profiles (communityvisibilitystate = 3)
- **Data Integrity**: Friend relationships are stored bidirectionally when both users are in database
- **Performance**: Games table remains normalized - no duplication even with many users
- **Error Handling**: Graceful degradation when friends have private profiles or API calls fail