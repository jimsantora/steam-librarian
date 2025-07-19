package models

import (
	"encoding/json"
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

	// Enhanced metadata fields (Phase 1.3)
	Screenshots    []string           `json:"screenshots" gorm:"serializer:json"`    // Game screenshots URLs
	MediaURLs      []string           `json:"media_urls" gorm:"serializer:json"`     // Videos and other media URLs
	SystemReqs     SystemRequirements `json:"system_requirements" gorm:"embedded"`   // Minimum and recommended specs
	PriceInfo      PriceInformation   `json:"price_info" gorm:"embedded"`            // Current pricing information
	MetacriticScore int               `json:"metacritic_score"`                      // Metacritic review score (0-100)
	MetacriticURL   string            `json:"metacritic_url"`                        // Link to Metacritic review page
	ContentFlags    []string          `json:"content_flags" gorm:"serializer:json"` // Steam content descriptors
	SteamFeatures   SteamFeatures     `json:"steam_features" gorm:"embedded"`        // Steam-specific features
	Achievements    int               `json:"achievements"`                          // Total number of achievements
	
	// Data freshness tracking
	LastSteamAPISync time.Time `json:"last_steam_api_sync"` // When we last updated from Steam API
}

// SystemRequirements represents minimum and recommended system specifications
type SystemRequirements struct {
	MinimumOS        string `json:"minimum_os" gorm:"column:min_os"`
	MinimumProcessor string `json:"minimum_processor" gorm:"column:min_processor"`
	MinimumMemory    string `json:"minimum_memory" gorm:"column:min_memory"`
	MinimumGraphics  string `json:"minimum_graphics" gorm:"column:min_graphics"`
	MinimumStorage   string `json:"minimum_storage" gorm:"column:min_storage"`
	MinimumOther     string `json:"minimum_other" gorm:"column:min_other"`
	
	RecommendedOS        string `json:"recommended_os" gorm:"column:rec_os"`
	RecommendedProcessor string `json:"recommended_processor" gorm:"column:rec_processor"`
	RecommendedMemory    string `json:"recommended_memory" gorm:"column:rec_memory"`
	RecommendedGraphics  string `json:"recommended_graphics" gorm:"column:rec_graphics"`
	RecommendedStorage   string `json:"recommended_storage" gorm:"column:rec_storage"`
	RecommendedOther     string `json:"recommended_other" gorm:"column:rec_other"`
}

// PriceInformation represents current pricing and discount information
type PriceInformation struct {
	Currency      string  `json:"currency" gorm:"column:price_currency"`           // USD, EUR, etc.
	CurrentPrice  float64 `json:"current_price" gorm:"column:current_price"`       // Current price in cents
	OriginalPrice float64 `json:"original_price" gorm:"column:original_price"`     // Original price before discount
	DiscountPct   int     `json:"discount_percent" gorm:"column:discount_percent"` // Discount percentage (0-100)
	IsFree        bool    `json:"is_free" gorm:"column:is_free"`                   // Whether the game is free
	ComingSoon    bool    `json:"coming_soon" gorm:"column:coming_soon"`           // Whether the game is unreleased
	EarlyAccess   bool    `json:"early_access" gorm:"column:early_access"`         // Whether in early access
}

// SteamFeatures represents Steam-specific features and capabilities
type SteamFeatures struct {
	HasWorkshop         bool `json:"has_workshop" gorm:"column:has_workshop"`                   // Steam Workshop support
	HasAchievements     bool `json:"has_achievements" gorm:"column:has_achievements"`           // Steam Achievements
	HasTradingCards     bool `json:"has_trading_cards" gorm:"column:has_trading_cards"`         // Steam Trading Cards
	HasCloudSave        bool `json:"has_cloud_save" gorm:"column:has_cloud_save"`               // Steam Cloud saves
	HasLeaderboards     bool `json:"has_leaderboards" gorm:"column:has_leaderboards"`           // Steam Leaderboards
	HasMultiplayer      bool `json:"has_multiplayer" gorm:"column:has_multiplayer"`             // Multiplayer support
	HasSinglePlayer     bool `json:"has_single_player" gorm:"column:has_single_player"`         // Single-player support
	HasControllerSupport bool `json:"has_controller_support" gorm:"column:has_controller_support"` // Controller support
	HasVRSupport        bool `json:"has_vr_support" gorm:"column:has_vr_support"`               // VR support
}

// TableName returns the table name for the Game model
func (Game) TableName() string {
	return "games"
}

// IsRecentlyUpdated checks if the game data was updated from Steam API recently
func (g *Game) IsRecentlyUpdated(within time.Duration) bool {
	return time.Since(g.LastSteamAPISync) < within
}

// GetCategories parses the categories JSON field and returns a slice of category names
func (g *Game) GetCategories() []string {
	if g.Categories == "" {
		return []string{}
	}
	
	var categories []string
	if err := json.Unmarshal([]byte(g.Categories), &categories); err != nil {
		return []string{}
	}
	return categories
}

// GetGenres parses the genres JSON field and returns a slice of genre names
func (g *Game) GetGenres() []string {
	if g.Genres == "" {
		return []string{}
	}
	
	var genres []string
	if err := json.Unmarshal([]byte(g.Genres), &genres); err != nil {
		return []string{}
	}
	return genres
}

// GetTags parses the tags JSON field and returns a slice of tag names
func (g *Game) GetTags() []string {
	if g.Tags == "" {
		return []string{}
	}
	
	var tags []string
	if err := json.Unmarshal([]byte(g.Tags), &tags); err != nil {
		return []string{}
	}
	return tags
}

// SetCategories marshals a slice of categories to JSON and stores it
func (g *Game) SetCategories(categories []string) error {
	if categories == nil {
		g.Categories = ""
		return nil
	}
	
	data, err := json.Marshal(categories)
	if err != nil {
		return err
	}
	g.Categories = string(data)
	return nil
}

// SetGenres marshals a slice of genres to JSON and stores it
func (g *Game) SetGenres(genres []string) error {
	if genres == nil {
		g.Genres = ""
		return nil
	}
	
	data, err := json.Marshal(genres)
	if err != nil {
		return err
	}
	g.Genres = string(data)
	return nil
}

// SetTags marshals a slice of tags to JSON and stores it
func (g *Game) SetTags(tags []string) error {
	if tags == nil {
		g.Tags = ""
		return nil
	}
	
	data, err := json.Marshal(tags)
	if err != nil {
		return err
	}
	g.Tags = string(data)
	return nil
}

// HasFeature checks if the game has a specific Steam feature
func (g *Game) HasFeature(feature string) bool {
	switch feature {
	case "workshop":
		return g.SteamFeatures.HasWorkshop
	case "achievements":
		return g.SteamFeatures.HasAchievements
	case "trading_cards":
		return g.SteamFeatures.HasTradingCards
	case "cloud_save":
		return g.SteamFeatures.HasCloudSave
	case "leaderboards":
		return g.SteamFeatures.HasLeaderboards
	case "multiplayer":
		return g.SteamFeatures.HasMultiplayer
	case "single_player":
		return g.SteamFeatures.HasSinglePlayer
	case "controller_support":
		return g.SteamFeatures.HasControllerSupport
	case "vr_support":
		return g.SteamFeatures.HasVRSupport
	default:
		return false
	}
}

// IsOnSale returns true if the game is currently discounted
func (g *Game) IsOnSale() bool {
	return g.PriceInfo.DiscountPct > 0 && g.PriceInfo.CurrentPrice < g.PriceInfo.OriginalPrice
}

// GetDiscountedPrice returns the final price after discount
func (g *Game) GetDiscountedPrice() float64 {
	if g.PriceInfo.IsFree {
		return 0.0
	}
	return g.PriceInfo.CurrentPrice
}

// HasMinimumSystemRequirements checks if minimum system requirements are specified
func (g *Game) HasMinimumSystemRequirements() bool {
	return g.SystemReqs.MinimumOS != "" || g.SystemReqs.MinimumProcessor != "" ||
		   g.SystemReqs.MinimumMemory != "" || g.SystemReqs.MinimumGraphics != ""
}

// HasRecommendedSystemRequirements checks if recommended system requirements are specified
func (g *Game) HasRecommendedSystemRequirements() bool {
	return g.SystemReqs.RecommendedOS != "" || g.SystemReqs.RecommendedProcessor != "" ||
		   g.SystemReqs.RecommendedMemory != "" || g.SystemReqs.RecommendedGraphics != ""
}