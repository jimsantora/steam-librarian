package models

import (
	"time"
	"gorm.io/gorm"
)

// Library represents a user's Steam library metadata
type Library struct {
	// Primary key and timestamps managed by GORM
	ID        uint           `gorm:"primarykey" json:"id"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"deleted_at,omitempty"`

	// Steam user information
	SteamUserID string `gorm:"uniqueIndex;not null" json:"steam_user_id"` // Steam 64-bit user ID
	Username    string `json:"username"`                                  // Steam username/display name
	ProfileURL  string `json:"profile_url"`                               // Steam profile URL
	AvatarURL   string `json:"avatar_url"`                                // User's avatar image URL

	// Library statistics
	TotalGames       int `json:"total_games"`        // Total number of games in library
	TotalPlaytime    int `json:"total_playtime"`     // Total playtime across all games (minutes)
	RecentlyPlayed   int `json:"recently_played"`    // Games played in last 2 weeks
	NeverPlayed      int `json:"never_played"`       // Games never launched
	
	// Data synchronization tracking
	LastLibrarySync time.Time `json:"last_library_sync"` // When we last synced the game list
	LastFullSync    time.Time `json:"last_full_sync"`    // When we last did a complete data refresh
	SyncInProgress  bool      `json:"sync_in_progress"`  // Whether a sync is currently running

	// Steam API configuration
	SteamAPIKey    string `json:"-" gorm:"column:steam_api_key"` // User's Steam API key (not in JSON)
	LibraryPublic  bool   `json:"library_public"`                // Whether the user's library is public
	
	// Relationship to games (one-to-many)
	Games []Game `gorm:"foreignKey:SteamUserID;references:SteamUserID" json:"games,omitempty"`
}

// TableName returns the table name for the Library model
func (Library) TableName() string {
	return "libraries"
}

// NeedsSyncCheck determines if the library needs to be synced
func (l *Library) NeedsSyncCheck(maxAge time.Duration) bool {
	return time.Since(l.LastLibrarySync) > maxAge
}

// IsFullSyncDue determines if a full sync (including game details) is needed
func (l *Library) IsFullSyncDue(maxAge time.Duration) bool {
	return time.Since(l.LastFullSync) > maxAge
}

// UpdateStats recalculates library statistics based on games
// TODO: This will be implemented to calculate stats from associated games
func (l *Library) UpdateStats(games []Game) {
	l.TotalGames = len(games)
	
	totalPlaytime := 0
	recentlyPlayed := 0
	neverPlayed := 0
	
	twoWeeksAgo := time.Now().AddDate(0, 0, -14)
	
	for _, game := range games {
		totalPlaytime += game.PlaytimeForever
		
		if game.PlaytimeTwoWeeks > 0 || game.LastPlayed.After(twoWeeksAgo) {
			recentlyPlayed++
		}
		
		if game.PlaytimeForever == 0 {
			neverPlayed++
		}
	}
	
	l.TotalPlaytime = totalPlaytime
	l.RecentlyPlayed = recentlyPlayed
	l.NeverPlayed = neverPlayed
}

// LibrarySyncStatus represents the current sync status
type LibrarySyncStatus struct {
	InProgress       bool      `json:"in_progress"`
	LastSync         time.Time `json:"last_sync"`
	LastFullSync     time.Time `json:"last_full_sync"`
	GamesProcessed   int       `json:"games_processed"`
	TotalGames       int       `json:"total_games"`
	ErrorsEncountered int      `json:"errors_encountered"`
	Message          string    `json:"message"`
}

// GetSyncStatus returns the current synchronization status
func (l *Library) GetSyncStatus() LibrarySyncStatus {
	return LibrarySyncStatus{
		InProgress:   l.SyncInProgress,
		LastSync:     l.LastLibrarySync,
		LastFullSync: l.LastFullSync,
		Message:      "Ready", // This will be dynamic based on actual sync state
	}
}