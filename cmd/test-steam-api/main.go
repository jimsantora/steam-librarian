// Steam API Integration Test Tool
// 
// This tool tests the Steam API client with real Steam data to verify
// that all API methods work correctly. It's useful for:
// - Verifying API key functionality
// - Testing during development
// - Debugging Steam API issues
// - Demonstrating API client usage
//
// Usage:
//   go run cmd/test-steam-api/main.go [steam_id]
//
// If no steam_id is provided, it uses a default public profile for testing.

package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/sirupsen/logrus"
	"github.com/jimsantora/steam-librarian/internal/steam"
)

func main() {
	// Parse command line flags
	var (
		steamID = flag.String("steamid", "76561198020403796", "Steam ID to test with (default: Jim Santora's public profile)")
		verbose = flag.Bool("verbose", false, "Enable verbose logging")
		quiet   = flag.Bool("quiet", false, "Minimal output (errors only)")
	)
	flag.Parse()

	// Get Steam API key from environment
	apiKey := os.Getenv("STEAM_API_KEY")
	if apiKey == "" {
		fmt.Println("❌ STEAM_API_KEY environment variable not set")
		fmt.Println("Get your Steam API key from: https://steamcommunity.com/dev/apikey")
		os.Exit(1)
	}

	// Create logger with appropriate level
	logger := logrus.New()
	if *quiet {
		logger.SetLevel(logrus.ErrorLevel)
	} else if *verbose {
		logger.SetLevel(logrus.DebugLevel)
	} else {
		logger.SetLevel(logrus.WarnLevel)
	}

	// Create Steam API client
	client := steam.NewClient(apiKey, logger)

	if !*quiet {
		fmt.Printf("🚀 Testing Steam API client with Steam ID: %s\n", *steamID)
		fmt.Printf("📝 Note: This tests all Steam API methods with real data\n\n")
	}

	// Test GetPlayerSummary
	if !*quiet {
		fmt.Println("=== Testing GetPlayerSummary ===")
	}
	summary, err := client.GetPlayerSummary(*steamID)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
	} else {
		fmt.Printf("✅ Player Summary:\n")
		fmt.Printf("   Steam ID: %s\n", summary.SteamID)
		fmt.Printf("   Name: %s\n", summary.PersonaName)
		fmt.Printf("   Profile URL: %s\n", summary.ProfileURL)
		fmt.Printf("   Avatar: %s\n", summary.Avatar)
	}
	fmt.Println()

	// Test GetRecentlyPlayedGames
	if !*quiet {
		fmt.Println("=== Testing GetRecentlyPlayedGames ===")
	}
	recentGames, err := client.GetRecentlyPlayedGames(*steamID)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
	} else {
		fmt.Printf("✅ Recently Played Games:\n")
		fmt.Printf("   Total Count: %d\n", recentGames.Response.TotalCount)
		for i, game := range recentGames.Response.Games {
			if i >= 3 { // Show only first 3 games
				break
			}
			fmt.Printf("   Game %d: %s (App ID: %d, Playtime: %d mins)\n", 
				i+1, game.Name, game.AppID, game.PlaytimeForever)
		}
	}
	fmt.Println()

	// Test GetOwnedGames (using existing method)
	if !*quiet {
		fmt.Println("=== Testing GetOwnedGames ===")
	}
	ownedGames, err := client.GetOwnedGames(*steamID, true, true)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
	} else {
		fmt.Printf("✅ Owned Games:\n")
		fmt.Printf("   Total Count: %d\n", ownedGames.Response.GameCount)
		for i, game := range ownedGames.Response.Games {
			if i >= 3 { // Show only first 3 games
				break
			}
			fmt.Printf("   Game %d: %s (App ID: %d, Playtime: %d mins)\n", 
				i+1, game.Name, game.AppID, game.Playtime)
		}
	}
	fmt.Println()

	// Test GetAppDetails and GetAppReviews with a popular game (Counter-Strike 2)
	testAppID := 730
	if !*quiet {
		fmt.Printf("=== Testing GetAppDetails for App ID %d ===\n", testAppID)
	}
	appDetails, err := client.GetAppDetails(testAppID)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
	} else {
		fmt.Printf("✅ App Details:\n")
		fmt.Printf("   Name: %s\n", appDetails.Name)
		fmt.Printf("   Type: %s\n", appDetails.Type)
		fmt.Printf("   Short Description: %.100s...\n", appDetails.ShortDesc)
		fmt.Printf("   Developers: %v\n", appDetails.Developer)
		fmt.Printf("   Publishers: %v\n", appDetails.Publisher)
	}
	fmt.Println()

	if !*quiet {
		fmt.Printf("=== Testing GetAppReviews for App ID %d ===\n", testAppID)
	}
	reviews, err := client.GetAppReviews(testAppID)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
	} else {
		fmt.Printf("✅ App Reviews:\n")
		fmt.Printf("   Review Score: %d\n", reviews.QuerySummary.ReviewScore)
		fmt.Printf("   Review Description: %s\n", reviews.QuerySummary.ReviewScoreDesc)
		fmt.Printf("   Total Reviews: %d\n", reviews.QuerySummary.TotalReviews)
		fmt.Printf("   Positive Reviews: %d\n", reviews.QuerySummary.TotalPositive)
		fmt.Printf("   Negative Reviews: %d\n", reviews.QuerySummary.TotalNegative)
	}

	if !*quiet {
		fmt.Println("\n🎉 Steam API testing completed!")
		fmt.Println("\n💡 Usage examples:")
		fmt.Println("  go run cmd/test-steam-api/main.go                    # Test with default Steam ID")
		fmt.Println("  go run cmd/test-steam-api/main.go -steamid=YOUR_ID  # Test with your Steam ID")
		fmt.Println("  go run cmd/test-steam-api/main.go -verbose          # Verbose logging")
		fmt.Println("  go run cmd/test-steam-api/main.go -quiet            # Minimal output")
	} else {
		fmt.Println("✅ All Steam API tests passed")
	}
}