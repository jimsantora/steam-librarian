# Steam Library Data Enhancement Plan

This document outlines all the additional data we can collect from Steam's APIs to create a comprehensive game library analysis tool.

## User Account Data

### 1. User Profile Information
**API**: `ISteamUser/GetPlayerSummaries/v0002/`
- **Steam Level**: Calculate and display user's Steam level
- **Account Age**: `timecreated` - Show how long user has been on Steam
- **Online Status**: Current status (Online, Offline, In-Game, etc.)
- **Profile Visibility**: Public, Friends Only, or Private
- **Avatar URLs**: Small, medium, and large avatar images
- **Currently Playing**: Real-time info on what game is being played
- **Location Data**: Country/state if public

### 2. Friends and Social Data
**API**: `ISteamUser/GetFriendList/v0001/`
- **Total Friends Count**: Number of Steam friends
- **Friends Who Own Same Games**: Cross-reference friend libraries
- **Friend Recommendations**: Suggest games friends are playing
- **Co-op Opportunities**: Games you both own with multiplayer

## Game-Specific Data

### 3. Achievement Tracking
**API**: `ISteamUserStats/GetPlayerAchievements/v0001/`
- **Completion Percentage**: Per-game achievement progress
- **Total Achievements**: Earned vs available across library
- **Achievement Timeline**: When achievements were unlocked
- **Rarest Achievements**: Highlight most difficult accomplishments
- **Time to Complete**: Estimate based on achievement progress

### 4. Global Achievement Statistics
**API**: `ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/`
- **Rarity Scores**: How rare are your achievements globally
- **Difficulty Rankings**: Which achievements are hardest
- **Completion Comparison**: How you stack up against other players

### 5. Game News and Updates
**API**: `ISteamNews/GetNewsForApp/v0002/`
- **Latest Patches**: Recent updates for owned games
- **New Content**: DLC and expansion announcements
- **Developer Updates**: News from game developers
- **Community Events**: Special events and tournaments

### 6. Store Data (Unofficial but Valuable)
**API**: Steam Store API (store.steampowered.com)
- **Current Pricing**: Real-time price for each game
- **Discount Status**: Current sales and discount percentages
- **Historical Pricing**: Track price changes over time
- **Metacritic Scores**: Critical reception data
- **Steam Deck Verified**: Compatibility status
- **Controller Support**: Full, partial, or none
- **Multiplayer Features**: Online, local co-op, split-screen
- **VR Support**: VR-only or VR-supported
- **System Requirements**: Min/recommended specs
- **DLC Information**: Available downloadable content
- **Workshop Support**: User-generated content availability

## Calculated Metrics and Analytics

### 7. Value Analysis
- **Cost Per Hour**: Price paid ÷ hours played
- **Library Value**: Total worth at current prices
- **Sale Savings**: How much saved buying on sale
- **Backlog Value**: Worth of unplayed games

### 8. Gaming Patterns
- **Genre Preferences**: Most played genres by hours
- **Developer Loyalty**: Favorite developers/publishers
- **Play Session Analysis**: Average session length
- **Weekly/Monthly Trends**: Gaming habits over time
- **Seasonal Patterns**: When you game most

### 9. Library Health Metrics
- **Pile of Shame Score**: Percentage of unplayed games
- **Completion Rate**: Games with >50% achievements
- **Diversity Index**: Genre variety in library
- **Investment Efficiency**: High playtime vs low playtime games

### 10. Social Comparisons
- **Library Overlap**: Games in common with friends
- **Unique Games**: Games only you own among friends
- **Trending Games**: What friends are playing now
- **Recommendation Score**: Games multiple friends own that you don't

## Implementation Priority

### Phase 1 (High Priority)
1. Achievement data and completion tracking
2. User profile information
3. Current pricing and discount data

### Phase 2 (Medium Priority)
4. Friends list integration
5. Global achievement statistics
6. Gaming pattern analytics

### Phase 3 (Low Priority)
7. Game news integration
8. Advanced metrics and comparisons
9. Historical data tracking

## Data Storage Requirements

This enhanced dataset requires:
- Relational data model (users, games, achievements, friends)
- Time-series data (price history, playtime tracking)
- Caching for API rate limits
- Regular update scheduling
- Efficient querying for analytics

SQLite is recommended for:
- Complex relationships between entities
- Better performance with large datasets
- ACID compliance for data integrity
- Built-in date/time handling
- Full SQL query capabilities