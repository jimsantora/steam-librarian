package models

import (
	"time"
	"gorm.io/gorm"
)

// Game represents a Steam game with all relevant metadata
type Game struct {
	// Primary key and timestamps managed by GORM
	ID        uint           `gorm:"primarykey" json:"id"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"deleted_at,omitempty"`

	// Steam-specific identifiers
	SteamAppID string `gorm:"uniqueIndex;not null" json:"steam_app_id"` // Steam's unique app ID
	Name       string `gorm:"not null" json:"name"`                     // Game title
	
	// Foreign key to link game to library
	SteamUserID string `gorm:"index" json:"steam_user_id"` // Links to Library.SteamUserID

	// Game metadata from Steam API
	ShortDescription string    `json:"short_description"` // Brief game description
	ReleaseDate      time.Time `json:"release_date"`      // When the game was released
	Developer        string    `json:"developer"`         // Game developer
	Publisher        string    `json:"publisher"`         // Game publisher
	
	// ESRB Rating information
	ESRBRating     string `json:"esrb_rating"`     // e.g., "Everyone", "Teen", "Mature 17+"
	ESRBDescriptor string `json:"esrb_descriptor"` // Additional ESRB content descriptors

	// Steam review data
	UserReviewSummary string `json:"user_review_summary"` // e.g., "Overwhelmingly Positive", "Mostly Positive"
	ReviewScore       int    `json:"review_score"`        // Percentage score from reviews
	ReviewCount       int    `json:"review_count"`        // Total number of reviews

	// User library information
	DateAddedToLibrary time.Time `json:"date_added_to_library"` // When user acquired this game
	PlaytimeForever    int       `json:"playtime_forever"`      // Total playtime in minutes
	PlaytimeTwoWeeks   int       `json:"playtime_two_weeks"`    // Playtime in last 2 weeks (minutes)
	LastPlayed         time.Time `json:"last_played"`           // Last time the game was played

	// Game media and links
	HeaderImage   string `json:"header_image"`   // URL to game's header image
	CapsuleImage  string `json:"capsule_image"`  // URL to game's capsule image
	StoreURL      string `json:"store_url"`      // Steam store page URL
	
	// Game categories and genres (stored as JSON for flexibility)
	Categories string `json:"categories"` // JSON array of category strings
	Genres     string `json:"genres"`     // JSON array of genre strings
	Tags       string `json:"tags"`       // JSON array of user-defined tags

	// Data freshness tracking
	LastSteamAPISync time.Time `json:"last_steam_api_sync"` // When we last updated from Steam API
}

// TableName returns the table name for the Game model
func (Game) TableName() string {
	return "games"
}

// IsRecentlyUpdated checks if the game data was updated from Steam API recently
func (g *Game) IsRecentlyUpdated(within time.Duration) bool {
	return time.Since(g.LastSteamAPISync) < within
}

// GetCategories parses the categories JSON field
// TODO: Implement JSON unmarshaling for categories
func (g *Game) GetCategories() []string {
	// This will be implemented when we add JSON parsing logic
	return []string{}
}

// GetGenres parses the genres JSON field  
// TODO: Implement JSON unmarshaling for genres
func (g *Game) GetGenres() []string {
	// This will be implemented when we add JSON parsing logic
	return []string{}
}

// GetTags parses the tags JSON field
// TODO: Implement JSON unmarshaling for tags  
func (g *Game) GetTags() []string {
	// This will be implemented when we add JSON parsing logic
	return []string{}
}