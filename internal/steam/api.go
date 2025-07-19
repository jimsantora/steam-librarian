package steam

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/jimsantora/steam-librarian/internal/models"
	"github.com/sirupsen/logrus"
)

// APIService provides high-level Steam API operations
// This service layer handles the conversion between Steam API responses and our internal models
type APIService struct {
	client      *Client
	logger      *logrus.Logger
	ratingMapper *ESRBRatingMapper
}

// NewAPIService creates a new Steam API service
func NewAPIService(apiKey string, logger *logrus.Logger) *APIService {
	return &APIService{
		client:       NewClient(apiKey, logger),
		logger:       logger,
		ratingMapper: NewESRBRatingMapper(),
	}
}

// SyncLibraryGames fetches and converts a user's Steam library to our models
func (s *APIService) SyncLibraryGames(steamUserID string) ([]models.Game, error) {
	s.logger.WithField("steam_user_id", steamUserID).Info("Starting library sync")

	// Fetch owned games from Steam API
	ownedGames, err := s.client.GetOwnedGames(steamUserID, true, true)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch owned games: %w", err)
	}

	games := make([]models.Game, 0, len(ownedGames.Response.Games))
	
	// Convert Steam API response to our models
	for _, steamGame := range ownedGames.Response.Games {
		game, err := s.convertSteamGameToModel(steamGame, steamUserID)
		if err != nil {
			s.logger.WithFields(logrus.Fields{
				"app_id": steamGame.AppID,
				"name":   steamGame.Name,
				"error":  err,
			}).Warn("Failed to convert Steam game to model")
			continue
		}
		
		games = append(games, *game)
	}

	s.logger.WithFields(logrus.Fields{
		"steam_user_id": steamUserID,
		"games_count":   len(games),
	}).Info("Library sync completed")

	return games, nil
}

// EnrichGameDetails fetches detailed information for a game and updates the model
func (s *APIService) EnrichGameDetails(game *models.Game) error {
	s.logger.WithFields(logrus.Fields{
		"steam_app_id": game.SteamAppID,
		"name":         game.Name,
	}).Debug("Enriching game details")

	appID, err := strconv.Atoi(game.SteamAppID)
	if err != nil {
		return fmt.Errorf("invalid Steam App ID: %s", game.SteamAppID)
	}

	// Fetch detailed app information
	details, err := s.client.GetAppDetails(appID)
	if err != nil {
		return fmt.Errorf("failed to fetch app details: %w", err)
	}

	// Update game model with detailed information
	s.updateGameWithDetails(game, details)

	// Mark as recently synced
	game.LastSteamAPISync = time.Now()

	s.logger.WithField("steam_app_id", game.SteamAppID).Debug("Game details enriched successfully")
	return nil
}

// convertSteamGameToModel converts a Steam API game response to our internal model
func (s *APIService) convertSteamGameToModel(steamGame SteamGame, steamUserID string) (*models.Game, error) {
	game := &models.Game{
		SteamAppID:         strconv.Itoa(steamGame.AppID),
		Name:               steamGame.Name,
		PlaytimeForever:    steamGame.Playtime,
		LastSteamAPISync:   time.Now(),
		DateAddedToLibrary: time.Now(), // This will be updated with more precise data later
	}

	// TODO: Add relationship between game and user/library
	// This might require updating the model to include a foreign key reference

	return game, nil
}

// updateGameWithDetails updates a game model with detailed information from Steam store API
func (s *APIService) updateGameWithDetails(game *models.Game, details *GameDetails) {
	// Basic information
	game.ShortDescription = details.ShortDesc
	game.HeaderImage = details.HeaderImage
	game.CapsuleImage = details.CapsuleImage
	game.StoreURL = fmt.Sprintf("https://store.steampowered.com/app/%s/", game.SteamAppID)

	// Developer and publisher (join multiple values)
	if len(details.Developer) > 0 {
		game.Developer = strings.Join(details.Developer, ", ")
	}
	if len(details.Publisher) > 0 {
		game.Publisher = strings.Join(details.Publisher, ", ")
	}

	// Release date parsing
	if !details.ReleaseDate.ComingSoon && details.ReleaseDate.Date != "" {
		if releaseDate, err := s.parseReleaseDate(details.ReleaseDate.Date); err == nil {
			game.ReleaseDate = releaseDate
		} else {
			s.logger.WithFields(logrus.Fields{
				"steam_app_id": game.SteamAppID,
				"date_string":  details.ReleaseDate.Date,
				"error":        err,
			}).Warn("Failed to parse release date")
		}
	}

	// Categories (convert to JSON string)
	if len(details.Categories) > 0 {
		categories := make([]string, len(details.Categories))
		for i, cat := range details.Categories {
			categories[i] = cat.Description
		}
		if err := game.SetCategories(categories); err != nil {
			s.logger.WithFields(logrus.Fields{
				"steam_app_id": game.SteamAppID,
				"error":        err,
			}).Warn("Failed to set categories JSON")
		}
	}

	// Genres (convert to JSON string)
	if len(details.Genres) > 0 {
		genres := make([]string, len(details.Genres))
		for i, genre := range details.Genres {
			genres[i] = genre.Description
		}
		if err := game.SetGenres(genres); err != nil {
			s.logger.WithFields(logrus.Fields{
				"steam_app_id": game.SteamAppID,
				"error":        err,
			}).Warn("Failed to set genres JSON")
		}
	}

	// Enhanced metadata parsing (Phase 1.3)
	s.parseEnhancedMetadata(game, details)

	// Content descriptors for ESRB-like information
	if details.ContentDescriptors.Notes != "" {
		game.ESRBDescriptor = details.ContentDescriptors.Notes
	}
	
	// Content flags from content descriptors using the rating mapper
	if len(details.ContentDescriptors.IDs) > 0 {
		contentFlags := s.ratingMapper.MapContentDescriptors(details.ContentDescriptors.IDs)
		game.ContentFlags = contentFlags
	}

	// ESRB rating mapping based on content descriptors
	rating := s.ratingMapper.DetermineESRBRating(details.ContentDescriptors.IDs, details.ContentDescriptors.Notes)
	game.ESRBRating = string(rating)

	// TODO: Implement review data fetching (requires separate API call)
}

// parseEnhancedMetadata extracts enhanced metadata from Steam API GameDetails (Phase 1.3)
func (s *APIService) parseEnhancedMetadata(game *models.Game, details *GameDetails) {
	// Parse screenshots URLs
	if len(details.Screenshots) > 0 {
		screenshots := make([]string, len(details.Screenshots))
		for i, screenshot := range details.Screenshots {
			screenshots[i] = screenshot.PathFull
		}
		game.Screenshots = screenshots
	}

	// Parse pricing information
	if details.PriceOverview.Currency != "" {
		game.PriceInfo.Currency = details.PriceOverview.Currency
		game.PriceInfo.CurrentPrice = float64(details.PriceOverview.Final) / 100.0 // Convert cents to dollars
		game.PriceInfo.OriginalPrice = float64(details.PriceOverview.Initial) / 100.0
		game.PriceInfo.DiscountPct = details.PriceOverview.DiscountPercent
		game.PriceInfo.IsFree = details.IsFree
	} else {
		// Game might be free
		game.PriceInfo.IsFree = details.IsFree
		game.PriceInfo.Currency = "USD"
	}

	// Parse release date flags
	game.PriceInfo.ComingSoon = details.ReleaseDate.ComingSoon
	
	// Parse Metacritic information
	if details.Metacritic.Score > 0 {
		game.MetacriticScore = details.Metacritic.Score
		game.MetacriticURL = details.Metacritic.URL
	}

	// Parse Steam features
	s.parseSteamFeatures(game, details)
	
	// Parse system requirements
	s.parseSystemRequirements(game, details)

	// Add media URLs (videos, etc.)
	if len(details.Movies) > 0 {
		mediaURLs := make([]string, len(details.Movies))
		for i, movie := range details.Movies {
			mediaURLs[i] = movie.MP4.Max
		}
		game.MediaURLs = mediaURLs
	}
	
	// Parse user-defined tags
	if len(details.Tags) > 0 {
		tags := make([]string, len(details.Tags))
		for i, tag := range details.Tags {
			tags[i] = tag.Name
		}
		if err := game.SetTags(tags); err != nil {
			s.logger.WithFields(logrus.Fields{
				"steam_app_id": game.SteamAppID,
				"error":        err,
			}).Warn("Failed to set tags JSON")
		}
	}
}

// parseSteamFeatures extracts Steam-specific features from game details
func (s *APIService) parseSteamFeatures(game *models.Game, details *GameDetails) {
	// Initialize with defaults
	game.SteamFeatures = models.SteamFeatures{}

	// Parse categories to determine features
	for _, category := range details.Categories {
		switch category.ID {
		case 1: // Multi-player
			game.SteamFeatures.HasMultiplayer = true
		case 2: // Single-player
			game.SteamFeatures.HasSinglePlayer = true
		case 22: // Steam Achievements
			game.SteamFeatures.HasAchievements = true
		case 23: // Steam Cloud
			game.SteamFeatures.HasCloudSave = true
		case 25: // Steam Leaderboards
			game.SteamFeatures.HasLeaderboards = true
		case 29: // Steam Trading Cards
			game.SteamFeatures.HasTradingCards = true
		case 30: // Steam Workshop
			game.SteamFeatures.HasWorkshop = true
		case 28: // Full controller support
			game.SteamFeatures.HasControllerSupport = true
		case 401: // VR Support
			game.SteamFeatures.HasVRSupport = true
		}
	}

	// Set achievements count if available
	if details.Achievements.Total > 0 {
		game.Achievements = details.Achievements.Total
	}
}

// parseSystemRequirements extracts system requirements from game details
func (s *APIService) parseSystemRequirements(game *models.Game, details *GameDetails) {
	// Parse PC requirements (Windows)
	if details.PCRequirements.Minimum != "" {
		s.parseRequirementString(details.PCRequirements.Minimum, &game.SystemReqs, true)
	}
	if details.PCRequirements.Recommended != "" {
		s.parseRequirementString(details.PCRequirements.Recommended, &game.SystemReqs, false)
	}
}

// parseRequirementString parses HTML-formatted system requirements
func (s *APIService) parseRequirementString(reqHTML string, systemReqs *models.SystemRequirements, isMinimum bool) {
	// This is a simplified parser - Steam provides HTML-formatted requirements
	// In a full implementation, you'd want a proper HTML parser
	
	// For now, just clean up the HTML and store the raw text
	cleaned := strings.ReplaceAll(reqHTML, "<br>", "\n")
	cleaned = strings.ReplaceAll(cleaned, "<strong>", "")
	cleaned = strings.ReplaceAll(cleaned, "</strong>", "")
	cleaned = strings.ReplaceAll(cleaned, "<ul>", "")
	cleaned = strings.ReplaceAll(cleaned, "</ul>", "")
	cleaned = strings.ReplaceAll(cleaned, "<li>", "• ")
	cleaned = strings.ReplaceAll(cleaned, "</li>", "\n")
	
	if isMinimum {
		systemReqs.MinimumOther = cleaned
	} else {
		systemReqs.RecommendedOther = cleaned
	}
	
	// TODO: Parse specific components (OS, Processor, Memory, Graphics, Storage)
	// This would require more sophisticated parsing of the HTML content
}


// parseReleaseDate attempts to parse Steam's various release date formats
func (s *APIService) parseReleaseDate(dateStr string) (time.Time, error) {
	// Steam uses different date formats, try common ones
	formats := []string{
		"2 Jan, 2006",
		"Jan 2, 2006", 
		"2006",
		"Jan 2006",
		"2 Jan 2006",
	}

	for _, format := range formats {
		if t, err := time.Parse(format, dateStr); err == nil {
			return t, nil
		}
	}

	return time.Time{}, fmt.Errorf("unable to parse date: %s", dateStr)
}

// GetLibraryStats calculates statistics for a user's library
func (s *APIService) GetLibraryStats(games []models.Game) map[string]interface{} {
	stats := map[string]interface{}{
		"total_games":     len(games),
		"total_playtime":  0,
		"never_played":    0,
		"recently_played": 0,
		"most_played":     "",
	}

	if len(games) == 0 {
		return stats
	}

	totalPlaytime := 0
	neverPlayed := 0
	recentlyPlayed := 0
	var mostPlayedGame models.Game

	twoWeeksAgo := time.Now().AddDate(0, 0, -14)

	for _, game := range games {
		totalPlaytime += game.PlaytimeForever

		if game.PlaytimeForever == 0 {
			neverPlayed++
		}

		if game.PlaytimeTwoWeeks > 0 || game.LastPlayed.After(twoWeeksAgo) {
			recentlyPlayed++
		}

		if game.PlaytimeForever > mostPlayedGame.PlaytimeForever {
			mostPlayedGame = game
		}
	}

	stats["total_playtime"] = totalPlaytime
	stats["never_played"] = neverPlayed
	stats["recently_played"] = recentlyPlayed
	if mostPlayedGame.Name != "" {
		stats["most_played"] = mostPlayedGame.Name
	}

	return stats
}

// ValidateAPIKey validates the Steam API key
func (s *APIService) ValidateAPIKey() error {
	return s.client.ValidateAPIKey()
}

// GetClient returns the underlying client for direct access to Steam API methods
func (s *APIService) GetClient() *Client {
	return s.client
}