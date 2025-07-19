package steam

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/go-resty/resty/v2"
	"github.com/sirupsen/logrus"
	"golang.org/x/time/rate"
)

// SteamAPIError represents an error from the Steam API
type SteamAPIError struct {
	StatusCode int
	Message    string
	Endpoint   string
}

func (e *SteamAPIError) Error() string {
	return fmt.Sprintf("Steam API error (endpoint: %s, status: %d): %s", e.Endpoint, e.StatusCode, e.Message)
}

// Client represents a Steam API client with rate limiting and caching
type Client struct {
	apiKey      string
	httpClient  *resty.Client
	logger      *logrus.Logger
	baseURL     string
	rateLimiter *rate.Limiter
	cache       sync.Map // Simple in-memory cache
	cacheTTL    time.Duration
}

// CacheEntry represents a cached API response
type CacheEntry struct {
	Data      interface{}
	ExpiresAt time.Time
}

// NewClient creates a new Steam API client with rate limiting and caching
func NewClient(apiKey string, logger *logrus.Logger) *Client {
	if logger == nil {
		logger = logrus.New()
	}

	client := resty.New()
	client.SetTimeout(30 * time.Second)
	client.SetRetryCount(3)
	client.SetRetryWaitTime(1 * time.Second)
	client.SetRetryMaxWaitTime(5 * time.Second)

	// Steam allows 100,000 requests per day, so we limit to ~1 request per second to be safe
	// This equals about 86,400 requests per day with some buffer
	rateLimiter := rate.NewLimiter(rate.Every(time.Second), 5) // 5 requests per second burst

	return &Client{
		apiKey:      apiKey,
		httpClient:  client,
		logger:      logger,
		baseURL:     "https://api.steampowered.com",
		rateLimiter: rateLimiter,
		cacheTTL:    5 * time.Minute, // Default cache TTL
	}
}

// makeRequest makes a rate-limited HTTP request with caching support
func (c *Client) makeRequest(endpoint string, params map[string]string, result interface{}, cacheKey string) error {
	// Check cache first if cache key is provided
	if cacheKey != "" {
		if entry, ok := c.cache.Load(cacheKey); ok {
			cacheEntry := entry.(CacheEntry)
			if time.Now().Before(cacheEntry.ExpiresAt) {
				c.logger.WithField("cache_key", cacheKey).Debug("Using cached response")
				// Copy cached data to result
				if result != nil {
					switch v := result.(type) {
					case *GetOwnedGamesResponse:
						*v = cacheEntry.Data.(GetOwnedGamesResponse)
					case *GetPlayerSummariesResponse:
						*v = cacheEntry.Data.(GetPlayerSummariesResponse)
					case *GetRecentlyPlayedGamesResponse:
						*v = cacheEntry.Data.(GetRecentlyPlayedGamesResponse)
					case *AppReviews:
						*v = cacheEntry.Data.(AppReviews)
					case *GetAppDetailsResponse:
						*v = cacheEntry.Data.(GetAppDetailsResponse)
					}
				}
				return nil
			} else {
				// Expired cache entry, remove it
				c.cache.Delete(cacheKey)
			}
		}
	}

	// Wait for rate limiter
	err := c.rateLimiter.Wait(context.Background())
	if err != nil {
		return fmt.Errorf("rate limiter error: %w", err)
	}

	c.logger.WithFields(logrus.Fields{
		"endpoint": endpoint,
		"params":   params,
	}).Debug("Making Steam API request")

	resp, err := c.httpClient.R().
		SetQueryParams(params).
		SetResult(result).
		Get(endpoint)

	if err != nil {
		return fmt.Errorf("HTTP request failed: %w", err)
	}

	if resp.StatusCode() != 200 {
		return &SteamAPIError{
			StatusCode: resp.StatusCode(),
			Message:    fmt.Sprintf("HTTP %d", resp.StatusCode()),
			Endpoint:   endpoint,
		}
	}

	// Cache the result if cache key is provided
	if cacheKey != "" && result != nil {
		var dataToCache interface{}
		switch v := result.(type) {
		case *GetOwnedGamesResponse:
			dataToCache = *v
		case *GetPlayerSummariesResponse:
			dataToCache = *v
		case *GetRecentlyPlayedGamesResponse:
			dataToCache = *v
		case *AppReviews:
			dataToCache = *v
		case *GetAppDetailsResponse:
			dataToCache = *v
		}
		
		if dataToCache != nil {
			c.cache.Store(cacheKey, CacheEntry{
				Data:      dataToCache,
				ExpiresAt: time.Now().Add(c.cacheTTL),
			})
		}
	}

	return nil
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
	
	// Enhanced metadata (Phase 1.3)
	Screenshots []struct {
		ID       int    `json:"id"`
		PathThumbnail string `json:"path_thumbnail"`
		PathFull string `json:"path_full"`
	} `json:"screenshots"`
	
	Movies []struct {
		ID int `json:"id"`
		Name string `json:"name"`
		Thumbnail string `json:"thumbnail"`
		WebM struct {
			Low string `json:"480"`
			Max string `json:"max"`
		} `json:"webm"`
		MP4 struct {
			Low string `json:"480"`
			Max string `json:"max"`
		} `json:"mp4"`
		Highlight bool `json:"highlight"`
	} `json:"movies"`
	
	PriceOverview struct {
		Currency string `json:"currency"`
		Initial  int    `json:"initial"`
		Final    int    `json:"final"`
		DiscountPercent int `json:"discount_percent"`
		InitialFormatted string `json:"initial_formatted"`
		FinalFormatted   string `json:"final_formatted"`
	} `json:"price_overview"`
	
	Metacritic struct {
		Score int    `json:"score"`
		URL   string `json:"url"`
	} `json:"metacritic"`
	
	Achievements struct {
		Total       int `json:"total"`
		Highlighted []struct {
			Name string `json:"name"`
			Path string `json:"path"`
		} `json:"highlighted"`
	} `json:"achievements"`
	
	PCRequirements struct {
		Minimum     string `json:"minimum"`
		Recommended string `json:"recommended"`
	} `json:"pc_requirements"`
	
	MacRequirements struct {
		Minimum     string `json:"minimum"`
		Recommended string `json:"recommended"`
	} `json:"mac_requirements"`
	
	LinuxRequirements struct {
		Minimum     string `json:"minimum"`
		Recommended string `json:"recommended"`
	} `json:"linux_requirements"`
	
	// User-defined tags (not always available in store API)
	Tags []struct {
		ID   int    `json:"tagid"`
		Name string `json:"name"`
	} `json:"tags"`
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

// PlayerSummary represents player profile information from Steam API
type PlayerSummary struct {
	SteamID                  string `json:"steamid"`
	CommunityVisibilityState int    `json:"communityvisibilitystate"`
	ProfileState             int    `json:"profilestate"`
	PersonaName              string `json:"personaname"`
	ProfileURL               string `json:"profileurl"`
	Avatar                   string `json:"avatar"`
	AvatarMedium             string `json:"avatarmedium"`
	AvatarFull               string `json:"avatarfull"`
	AvatarHash               string `json:"avatarhash"`
	LastLogoff               int64  `json:"lastlogoff"`
	PersonaState             int    `json:"personastate"`
	RealName                 string `json:"realname"`
	PrimaryClanID            string `json:"primaryclanid"`
	TimeCreated              int64  `json:"timecreated"`
	PersonaStateFlags        int    `json:"personastateflags"`
	GameExtraInfo            string `json:"gameextrainfo"`
	GameID                   string `json:"gameid"`
	LoccountryCode           string `json:"loccountrycode"`
	LocStateCode             string `json:"locstatecode"`
	LocCityID                int    `json:"loccityid"`
}

// GetPlayerSummariesResponse represents the response from GetPlayerSummaries API
type GetPlayerSummariesResponse struct {
	Response struct {
		Players []PlayerSummary `json:"players"`
	} `json:"response"`
}

// GetPlayerSummary retrieves basic profile information for a Steam user
func (c *Client) GetPlayerSummary(steamID string) (*PlayerSummary, error) {
	c.logger.WithField("steam_id", steamID).Debug("Fetching player summary from Steam API")

	url := fmt.Sprintf("%s/ISteamUser/GetPlayerSummaries/v0002/", c.baseURL)
	
	resp, err := c.httpClient.R().
		SetQueryParams(map[string]string{
			"key":      c.apiKey,
			"steamids": steamID,
			"format":   "json",
		}).
		SetResult(&GetPlayerSummariesResponse{}).
		Get(url)

	if err != nil {
		return nil, fmt.Errorf("failed to fetch player summary: %w", err)
	}

	if resp.StatusCode() != 200 {
		return nil, fmt.Errorf("Steam API returned status %d", resp.StatusCode())
	}

	result := resp.Result().(*GetPlayerSummariesResponse)
	if len(result.Response.Players) == 0 {
		return nil, fmt.Errorf("no player found with Steam ID %s", steamID)
	}

	player := result.Response.Players[0]
	c.logger.WithFields(map[string]interface{}{
		"steam_id":     steamID,
		"persona_name": player.PersonaName,
	}).Debug("Successfully fetched player summary")
	
	return &player, nil
}

// RecentlyPlayedGame represents a recently played game from Steam API
type RecentlyPlayedGame struct {
	AppID           int    `json:"appid"`
	Name            string `json:"name"`
	Playtime2Weeks  int    `json:"playtime_2weeks"`
	PlaytimeForever int    `json:"playtime_forever"`
	ImgIconURL      string `json:"img_icon_url"`
	ImgLogoURL      string `json:"img_logo_url"`
}

// GetRecentlyPlayedGamesResponse represents the response from GetRecentlyPlayedGames API
type GetRecentlyPlayedGamesResponse struct {
	Response struct {
		TotalCount int                  `json:"total_count"`
		Games      []RecentlyPlayedGame `json:"games"`
	} `json:"response"`
}

// GetRecentlyPlayedGames retrieves games played in the last 2 weeks
func (c *Client) GetRecentlyPlayedGames(steamID string) (*GetRecentlyPlayedGamesResponse, error) {
	c.logger.WithField("steam_id", steamID).Debug("Fetching recently played games from Steam API")

	url := fmt.Sprintf("%s/IPlayerService/GetRecentlyPlayedGames/v0001/", c.baseURL)
	
	resp, err := c.httpClient.R().
		SetQueryParams(map[string]string{
			"key":     c.apiKey,
			"steamid": steamID,
			"format":  "json",
			"count":   "0", // 0 means return all recently played games
		}).
		SetResult(&GetRecentlyPlayedGamesResponse{}).
		Get(url)

	if err != nil {
		return nil, fmt.Errorf("failed to fetch recently played games: %w", err)
	}

	if resp.StatusCode() != 200 {
		return nil, fmt.Errorf("Steam API returned status %d", resp.StatusCode())
	}

	result := resp.Result().(*GetRecentlyPlayedGamesResponse)
	c.logger.WithFields(map[string]interface{}{
		"steam_id":    steamID,
		"game_count":  result.Response.TotalCount,
	}).Debug("Successfully fetched recently played games")
	
	return result, nil
}

// AppReviews represents review summary data for a Steam app
type AppReviews struct {
	Success      int `json:"success"`
	QuerySummary struct {
		NumReviews      int    `json:"num_reviews"`
		ReviewScore     int    `json:"review_score"`
		ReviewScoreDesc string `json:"review_score_desc"`
		TotalPositive   int    `json:"total_positive"`
		TotalNegative   int    `json:"total_negative"`
		TotalReviews    int    `json:"total_reviews"`
	} `json:"query_summary"`
}

// GetAppReviews retrieves user review summary for a specific app
func (c *Client) GetAppReviews(appID int) (*AppReviews, error) {
	c.logger.WithField("app_id", appID).Debug("Fetching app reviews from Steam API")

	url := "https://store.steampowered.com/appreviews/" + fmt.Sprintf("%d", appID)
	
	resp, err := c.httpClient.R().
		SetQueryParams(map[string]string{
			"json":              "1",
			"language":          "english",
			"review_type":       "all",
			"purchase_type":     "all",
			"num_per_page":      "0", // We only want the summary
			"filter_offtopic_activity": "0",
		}).
		Get(url)

	if err != nil {
		return nil, fmt.Errorf("failed to fetch app reviews: %w", err)
	}

	if resp.StatusCode() != 200 {
		return nil, fmt.Errorf("Steam store API returned status %d", resp.StatusCode())
	}

	var reviews AppReviews
	if err := json.Unmarshal(resp.Body(), &reviews); err != nil {
		return nil, fmt.Errorf("failed to parse app reviews response: %w", err)
	}

	if reviews.Success != 1 {
		return nil, fmt.Errorf("Steam API reported failure for app %d reviews", appID)
	}

	c.logger.WithFields(map[string]interface{}{
		"app_id":           appID,
		"review_score":     reviews.QuerySummary.ReviewScore,
		"review_score_desc": reviews.QuerySummary.ReviewScoreDesc,
		"total_reviews":    reviews.QuerySummary.TotalReviews,
	}).Debug("Successfully fetched app reviews")
	
	return &reviews, nil
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