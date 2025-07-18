package steam

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-resty/resty/v2"
	"github.com/sirupsen/logrus"
)

// Client represents a Steam API client
type Client struct {
	apiKey     string
	httpClient *resty.Client
	logger     *logrus.Logger
	baseURL    string
}

// NewClient creates a new Steam API client
func NewClient(apiKey string, logger *logrus.Logger) *Client {
	if logger == nil {
		logger = logrus.New()
	}

	client := resty.New()
	client.SetTimeout(30 * time.Second)
	client.SetRetryCount(3)
	client.SetRetryWaitTime(1 * time.Second)
	client.SetRetryMaxWaitTime(5 * time.Second)

	return &Client{
		apiKey:     apiKey,
		httpClient: client,
		logger:     logger,
		baseURL:    "https://api.steampowered.com",
	}
}

// SteamGame represents basic game information from Steam API
type SteamGame struct {
	AppID    int    `json:"appid"`
	Name     string `json:"name"`
	Playtime int    `json:"playtime_forever"`
}

// GetOwnedGamesResponse represents the response from GetOwnedGames API
type GetOwnedGamesResponse struct {
	Response struct {
		GameCount int         `json:"game_count"`
		Games     []SteamGame `json:"games"`
	} `json:"response"`
}

// GameDetails represents detailed game information from Steam API
type GameDetails struct {
	AppID        int    `json:"steam_appid"`
	Name         string `json:"name"`
	Type         string `json:"type"`
	IsFree       bool   `json:"is_free"`
	ShortDesc    string `json:"short_description"`
	HeaderImage  string `json:"header_image"`
	CapsuleImage string `json:"capsule_image"`
	Website      string `json:"website"`
	Developer    []string `json:"developers"`
	Publisher    []string `json:"publishers"`
	
	// Release date information
	ReleaseDate struct {
		ComingSoon bool   `json:"coming_soon"`
		Date       string `json:"date"`
	} `json:"release_date"`
	
	// Categories and genres
	Categories []struct {
		ID          int    `json:"id"`
		Description string `json:"description"`
	} `json:"categories"`
	
	Genres []struct {
		ID          string `json:"id"`
		Description string `json:"description"`
	} `json:"genres"`
	
	// Content descriptors and ratings
	ContentDescriptors struct {
		IDs   []int  `json:"ids"`
		Notes string `json:"notes"`
	} `json:"content_descriptors"`
}

// GetAppDetailsResponse represents the response from Steam store API
type GetAppDetailsResponse map[string]struct {
	Success bool        `json:"success"`
	Data    GameDetails `json:"data"`
}

// UserStats represents user's game statistics
type UserStats struct {
	SteamID    string `json:"steamid"`
	GameName   string `json:"gameName"`
	Playtime   int    `json:"playtime_forever"`
	PlaytimeQt int    `json:"playtime_2weeks,omitempty"`
}

// GetOwnedGames retrieves the list of games owned by a Steam user
func (c *Client) GetOwnedGames(steamID string, includeAppInfo bool, includeFreeGames bool) (*GetOwnedGamesResponse, error) {
	c.logger.WithFields(logrus.Fields{
		"steam_id": steamID,
		"include_app_info": includeAppInfo,
		"include_free_games": includeFreeGames,
	}).Debug("Fetching owned games from Steam API")

	url := fmt.Sprintf("%s/IPlayerService/GetOwnedGames/v0001/", c.baseURL)
	
	resp, err := c.httpClient.R().
		SetQueryParams(map[string]string{
			"key":                c.apiKey,
			"steamid":           steamID,
			"format":            "json",
			"include_appinfo":   fmt.Sprintf("%t", includeAppInfo),
			"include_played_free_games": fmt.Sprintf("%t", includeFreeGames),
		}).
		SetResult(&GetOwnedGamesResponse{}).
		Get(url)

	if err != nil {
		return nil, fmt.Errorf("failed to fetch owned games: %w", err)
	}

	if resp.StatusCode() != 200 {
		return nil, fmt.Errorf("Steam API returned status %d", resp.StatusCode())
	}

	result := resp.Result().(*GetOwnedGamesResponse)
	c.logger.WithField("game_count", result.Response.GameCount).Info("Successfully fetched owned games")
	
	return result, nil
}

// GetAppDetails retrieves detailed information about a specific Steam app
func (c *Client) GetAppDetails(appID int) (*GameDetails, error) {
	c.logger.WithField("app_id", appID).Debug("Fetching app details from Steam store API")

	url := "https://store.steampowered.com/api/appdetails"
	
	resp, err := c.httpClient.R().
		SetQueryParams(map[string]string{
			"appids": fmt.Sprintf("%d", appID),
		}).
		Get(url)

	if err != nil {
		return nil, fmt.Errorf("failed to fetch app details: %w", err)
	}

	if resp.StatusCode() != 200 {
		return nil, fmt.Errorf("Steam store API returned status %d", resp.StatusCode())
	}

	var response GetAppDetailsResponse
	if err := json.Unmarshal(resp.Body(), &response); err != nil {
		return nil, fmt.Errorf("failed to parse app details response: %w", err)
	}

	appIDStr := fmt.Sprintf("%d", appID)
	appData, exists := response[appIDStr]
	if !exists {
		return nil, fmt.Errorf("app %d not found in response", appID)
	}

	if !appData.Success {
		return nil, fmt.Errorf("Steam API reported failure for app %d", appID)
	}

	c.logger.WithField("app_id", appID).Debug("Successfully fetched app details")
	return &appData.Data, nil
}

// GetPlayerSummary retrieves basic profile information for a Steam user
// TODO: Implement this method to get user profile data
func (c *Client) GetPlayerSummary(steamID string) error {
	// This will be implemented to fetch user profile information
	// including username, avatar, profile URL, etc.
	c.logger.WithField("steam_id", steamID).Debug("GetPlayerSummary not yet implemented")
	return fmt.Errorf("GetPlayerSummary not yet implemented")
}

// GetRecentlyPlayedGames retrieves games played in the last 2 weeks
// TODO: Implement this method to get recently played games
func (c *Client) GetRecentlyPlayedGames(steamID string) error {
	// This will be implemented to fetch recently played games
	c.logger.WithField("steam_id", steamID).Debug("GetRecentlyPlayedGames not yet implemented")
	return fmt.Errorf("GetRecentlyPlayedGames not yet implemented")
}

// GetAppReviews retrieves user reviews for a specific app
// TODO: Implement this method to get review summary data
func (c *Client) GetAppReviews(appID int) error {
	// This will be implemented to fetch review summary information
	// like "Overwhelmingly Positive", review percentages, etc.
	c.logger.WithField("app_id", appID).Debug("GetAppReviews not yet implemented")
	return fmt.Errorf("GetAppReviews not yet implemented")
}

// ValidateAPIKey checks if the provided API key is valid
func (c *Client) ValidateAPIKey() error {
	c.logger.Debug("Validating Steam API key")
	
	// Use a simple API call to test the key
	url := fmt.Sprintf("%s/ISteamUser/GetPlayerSummaries/v0002/", c.baseURL)
	
	resp, err := c.httpClient.R().
		SetQueryParams(map[string]string{
			"key":      c.apiKey,
			"steamids": "76561197960435530", // Use a known valid Steam ID for testing
		}).
		Get(url)

	if err != nil {
		return fmt.Errorf("failed to validate API key: %w", err)
	}

	if resp.StatusCode() == 403 {
		return fmt.Errorf("invalid Steam API key")
	}

	if resp.StatusCode() != 200 {
		return fmt.Errorf("unexpected response status: %d", resp.StatusCode())
	}

	c.logger.Info("Steam API key validated successfully")
	return nil
}