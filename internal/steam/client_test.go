package steam

import (
	"testing"
	"time"

	"github.com/sirupsen/logrus"
)

// TestNewClient tests the creation of a new Steam API client
func TestNewClient(t *testing.T) {
	logger := logrus.New()
	client := NewClient("test_api_key", logger)

	if client == nil {
		t.Fatal("NewClient returned nil")
	}

	if client.apiKey != "test_api_key" {
		t.Errorf("Expected API key 'test_api_key', got '%s'", client.apiKey)
	}

	if client.baseURL != "https://api.steampowered.com" {
		t.Errorf("Expected base URL 'https://api.steampowered.com', got '%s'", client.baseURL)
	}

	if client.rateLimiter == nil {
		t.Error("Rate limiter should not be nil")
	}

	if client.cacheTTL != 5*time.Minute {
		t.Errorf("Expected cache TTL 5 minutes, got %v", client.cacheTTL)
	}
}

// TestSteamAPIError tests the SteamAPIError type
func TestSteamAPIError(t *testing.T) {
	err := &SteamAPIError{
		StatusCode: 404,
		Message:    "Not Found",
		Endpoint:   "/test/endpoint",
	}

	expected := "Steam API error (endpoint: /test/endpoint, status: 404): Not Found"
	if err.Error() != expected {
		t.Errorf("Expected error message '%s', got '%s'", expected, err.Error())
	}
}

// TestCacheEntry tests the cache entry functionality
func TestCacheEntry(t *testing.T) {
	entry := CacheEntry{
		Data:      "test_data",
		ExpiresAt: time.Now().Add(1 * time.Hour),
	}

	if entry.Data != "test_data" {
		t.Errorf("Expected cache data 'test_data', got '%v'", entry.Data)
	}

	if entry.ExpiresAt.Before(time.Now()) {
		t.Error("Cache entry should not be expired")
	}
}

// Note: Integration tests for actual Steam API calls would require:
// 1. Valid Steam API key
// 2. Valid Steam ID
// 3. Network connectivity
// These tests should be run separately as integration tests
//
// Example integration test structure:
//
// func TestGetPlayerSummaryIntegration(t *testing.T) {
//     if testing.Short() {
//         t.Skip("Skipping integration test")
//     }
//     
//     apiKey := os.Getenv("STEAM_API_KEY")
//     if apiKey == "" {
//         t.Skip("STEAM_API_KEY not set")
//     }
//     
//     client := NewClient(apiKey, logrus.New())
//     summary, err := client.GetPlayerSummary("76561197960435530")
//     
//     if err != nil {
//         t.Fatalf("GetPlayerSummary failed: %v", err)
//     }
//     
//     if summary == nil {
//         t.Fatal("Expected player summary, got nil")
//     }
//     
//     if summary.SteamID != "76561197960435530" {
//         t.Errorf("Expected Steam ID '76561197960435530', got '%s'", summary.SteamID)
//     }
// }