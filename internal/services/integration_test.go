package services

import (
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/jimsantora/steam-librarian/internal/models"
	"github.com/jimsantora/steam-librarian/internal/storage"
	"github.com/jimsantora/steam-librarian/internal/steam"
)

// TestMain sets up and tears down the test environment
func TestMain(m *testing.M) {
	code := m.Run()
	os.Exit(code)
}

// createTestDatabase creates an in-memory SQLite database for testing
func createTestDatabase(t *testing.T) *storage.Database {
	cfg := &storage.DatabaseConfig{
		Type:     "sqlite",
		Host:     ":memory:",
		Database: "test.db",
		Username: "",
		Password: "",
		Port:     0,
	}

	db, err := storage.NewDatabase(*cfg)
	require.NoError(t, err, "Failed to create test database")

	err = db.AutoMigrate()
	require.NoError(t, err, "Failed to run migrations")

	return db
}

// createTestLogger creates a logger configured for testing
func createTestLogger() *logrus.Logger {
	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel) // Reduce noise in tests
	return logger
}

// createMockSteamAPI creates a mock Steam API service that doesn't make real API calls
func createMockSteamAPI(t *testing.T) *steam.APIService {
	// Create a dummy API service with empty key for testing
	logger := createTestLogger()
	return steam.NewAPIService("", logger)
}

// Integration Tests

func TestSyncService_Integration_Lifecycle(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()

	repo := storage.NewRepository(db)
	steamAPI := createMockSteamAPI(t)
	logger := createTestLogger()

	// Create sync service
	syncService := NewLibrarySyncService(repo, steamAPI, logger)
	defer syncService.Shutdown()

	// Test service initialization
	assert.NotNil(t, syncService)
	assert.NotNil(t, syncService.GetConflictResolver())

	// Test getting active syncs (should be empty initially)
	activeSyncs := syncService.GetActiveSyncs()
	assert.Empty(t, activeSyncs)

	// Test getting sync history (should be empty initially)
	history := syncService.GetSyncHistory("test_user")
	assert.Empty(t, history)

	// Test getting sync progress for non-existent sync
	progress, exists := syncService.GetSyncProgress("test_user")
	assert.False(t, exists)
	assert.Nil(t, progress)
}

func TestSyncService_Integration_LibraryCreation(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()

	repo := storage.NewRepository(db)
	steamAPI := createMockSteamAPI(t)
	logger := createTestLogger()

	syncService := NewLibrarySyncService(repo, steamAPI, logger)
	defer syncService.Shutdown()

	// Create a test library
	testLibrary := &models.Library{
		SteamUserID:    "76561198020403796",
		Username:       "TestUser",
		ProfileURL:     "https://steamcommunity.com/id/testuser",
		AvatarURL:      "https://example.com/avatar.jpg",
		SyncInProgress: false,
	}

	err := repo.CreateLibrary(testLibrary)
	require.NoError(t, err)
	assert.Greater(t, testLibrary.ID, uint(0))

	// Verify library was created
	retrievedLibrary, err := repo.GetLibraryByUserID(testLibrary.SteamUserID)
	require.NoError(t, err)
	require.NotNil(t, retrievedLibrary)
	assert.Equal(t, testLibrary.SteamUserID, retrievedLibrary.SteamUserID)
	assert.Equal(t, testLibrary.Username, retrievedLibrary.Username)
}

func TestSyncService_Integration_GameOperations(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()

	repo := storage.NewRepository(db)
	steamAPI := createMockSteamAPI(t)
	logger := createTestLogger()

	syncService := NewLibrarySyncService(repo, steamAPI, logger)
	defer syncService.Shutdown()

	steamUserID := "76561198020403796"

	// Create test games
	testGames := []*models.Game{
		{
			SteamAppID:      "730",
			SteamUserID:     steamUserID,
			Name:            "Counter-Strike 2",
			PlaytimeForever: 1500,
			LastSteamAPISync: time.Now(),
		},
		{
			SteamAppID:      "570",
			SteamUserID:     steamUserID,
			Name:            "Dota 2",
			PlaytimeForever: 2400,
			LastSteamAPISync: time.Now(),
		},
	}

	// Create games in database
	for _, game := range testGames {
		err := repo.CreateGame(game)
		require.NoError(t, err)
		assert.Greater(t, game.ID, uint(0))
	}

	// Retrieve games by user ID
	retrievedGames, err := repo.GetGamesByUserID(steamUserID)
	require.NoError(t, err)
	assert.Len(t, retrievedGames, len(testGames))

	// Verify game data
	for i, game := range retrievedGames {
		assert.Equal(t, testGames[i].SteamAppID, game.SteamAppID)
		assert.Equal(t, testGames[i].Name, game.Name)
		assert.Equal(t, testGames[i].PlaytimeForever, game.PlaytimeForever)
	}

	// Test game updates
	updatedGame := &retrievedGames[0]
	updatedGame.PlaytimeForever = 2000
	updatedGame.LastSteamAPISync = time.Now()

	err = repo.UpdateGame(updatedGame)
	require.NoError(t, err)

	// Verify update
	retrievedGame, err := repo.GetGameByID(updatedGame.ID)
	require.NoError(t, err)
	assert.Equal(t, 2000, retrievedGame.PlaytimeForever)
}

func TestSyncService_Integration_ConflictResolver(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()

	repo := storage.NewRepository(db)
	steamAPI := createMockSteamAPI(t)
	logger := createTestLogger()

	syncService := NewLibrarySyncService(repo, steamAPI, logger)
	defer syncService.Shutdown()

	// Test conflict resolver initialization
	conflictResolver := syncService.GetConflictResolver()
	require.NotNil(t, conflictResolver)

	// Test getting statistics
	stats := conflictResolver.GetStatistics()
	require.NotNil(t, stats)
	assert.Contains(t, stats, "total_conflicts")
	assert.Contains(t, stats, "auto_resolve_enabled")
	assert.Equal(t, 0, stats["total_conflicts"])

	// Test getting conflicts (should be empty)
	conflicts := conflictResolver.GetConflicts("", "")
	assert.Empty(t, conflicts)

	// Test auto-resolution (should complete without error)
	err := conflictResolver.AutoResolveConflicts()
	assert.NoError(t, err)
}

func TestSyncService_Integration_SyncScheduler(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()

	repo := storage.NewRepository(db)
	steamAPI := createMockSteamAPI(t)
	logger := createTestLogger()

	syncService := NewLibrarySyncService(repo, steamAPI, logger)
	defer syncService.Shutdown()

	// Create scheduler with test configuration
	config := &SchedulerConfig{
		AutoSyncEnabled:          false, // Disabled for testing
		IncrementalSyncInterval:  1 * time.Hour,
		FullSyncInterval:         24 * time.Hour,
		MaxConcurrentAutoSyncs:   1,
		QuietHoursStart:          1,
		QuietHoursEnd:            6,
		OnlyScheduleIfActive:     true,
		ActivityThresholdDays:    7,
	}

	scheduler := NewSyncScheduler(config, syncService, repo, logger)
	defer scheduler.Stop()

	// Test scheduler status
	status := scheduler.GetStatus()
	require.NotNil(t, status)
	assert.Contains(t, status, "running")
	assert.Contains(t, status, "auto_sync_enabled")
	assert.False(t, status["auto_sync_enabled"].(bool))

	// Test starting scheduler (should be no-op since auto-sync is disabled)
	err := scheduler.Start()
	assert.NoError(t, err)

	// Test updating configuration
	newConfig := &SchedulerConfig{
		AutoSyncEnabled:          false, // Keep disabled for testing
		IncrementalSyncInterval:  2 * time.Hour,
		FullSyncInterval:         48 * time.Hour,
		MaxConcurrentAutoSyncs:   2,
		QuietHoursStart:          2,
		QuietHoursEnd:            7,
		OnlyScheduleIfActive:     false,
		ActivityThresholdDays:    14,
	}

	err = scheduler.UpdateConfig(newConfig)
	assert.NoError(t, err)

	// Verify configuration was updated
	updatedStatus := scheduler.GetStatus()
	assert.Equal(t, "2h0m0s", updatedStatus["incremental_interval"])
	assert.Equal(t, "48h0m0s", updatedStatus["full_interval"])
}

func TestSyncService_Integration_ErrorHandling(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()

	repo := storage.NewRepository(db)
	steamAPI := createMockSteamAPI(t)
	logger := createTestLogger()

	syncService := NewLibrarySyncService(repo, steamAPI, logger)
	defer syncService.Shutdown()

	// Test canceling non-existent sync
	err := syncService.CancelSync("nonexistent_user")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "no active sync found")

	// Test getting progress for non-existent sync
	progress, exists := syncService.GetSyncProgress("nonexistent_user")
	assert.False(t, exists)
	assert.Nil(t, progress)

	// Test getting history for user with no syncs
	history := syncService.GetSyncHistory("nonexistent_user")
	assert.Empty(t, history)
}

func TestSyncService_Integration_DatabaseOperations(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()

	repo := storage.NewRepository(db)

	// Test library operations
	t.Run("Library Operations", func(t *testing.T) {
		// Create library
		library := &models.Library{
			SteamUserID: "test_user_123",
			Username:    "TestUser",
			ProfileURL:  "https://example.com/profile",
		}

		err := repo.CreateLibrary(library)
		require.NoError(t, err)
		assert.Greater(t, library.ID, uint(0))

		// Get library by ID
		retrievedLibrary, err := repo.GetLibraryByID(library.ID)
		require.NoError(t, err)
		assert.Equal(t, library.SteamUserID, retrievedLibrary.SteamUserID)

		// Get library by user ID
		libraryByUser, err := repo.GetLibraryByUserID(library.SteamUserID)
		require.NoError(t, err)
		assert.Equal(t, library.ID, libraryByUser.ID)

		// Update library
		library.Username = "UpdatedUser"
		err = repo.UpdateLibrary(library)
		require.NoError(t, err)

		// Verify update
		updatedLibrary, err := repo.GetLibraryByID(library.ID)
		require.NoError(t, err)
		assert.Equal(t, "UpdatedUser", updatedLibrary.Username)

		// Get all libraries
		allLibraries, err := repo.GetAllLibraries()
		require.NoError(t, err)
		assert.GreaterOrEqual(t, len(allLibraries), 1)

		// Delete library
		err = repo.DeleteLibrary(library.ID)
		assert.NoError(t, err)

		// Verify deletion
		deletedLibrary, err := repo.GetLibraryByID(library.ID)
		assert.NoError(t, err) // GORM doesn't return error for not found
		assert.Nil(t, deletedLibrary)
	})

	t.Run("Game Operations", func(t *testing.T) {
		// Create game
		game := &models.Game{
			SteamAppID:       "123456",
			SteamUserID:      "test_user_456",
			Name:             "Test Game",
			PlaytimeForever:  100,
			LastSteamAPISync: time.Now(),
		}

		err := repo.CreateGame(game)
		require.NoError(t, err)
		assert.Greater(t, game.ID, uint(0))

		// Get game by ID
		retrievedGame, err := repo.GetGameByID(game.ID)
		require.NoError(t, err)
		assert.Equal(t, game.Name, retrievedGame.Name)

		// Get games by user ID
		userGames, err := repo.GetGamesByUserID(game.SteamUserID)
		require.NoError(t, err)
		assert.Len(t, userGames, 1)
		assert.Equal(t, game.ID, userGames[0].ID)

		// Update game
		game.PlaytimeForever = 200
		err = repo.UpdateGame(game)
		require.NoError(t, err)

		// Verify update
		updatedGame, err := repo.GetGameByID(game.ID)
		require.NoError(t, err)
		assert.Equal(t, 200, updatedGame.PlaytimeForever)

		// Get all games
		allGames, err := repo.GetAllGames()
		require.NoError(t, err)
		assert.GreaterOrEqual(t, len(allGames), 1)

		// Delete game
		err = repo.DeleteGame(game.ID)
		assert.NoError(t, err)

		// Verify deletion
		deletedGame, err := repo.GetGameByID(game.ID)
		assert.NoError(t, err)
		assert.Nil(t, deletedGame)
	})
}

// Benchmark tests

func BenchmarkSyncService_CreateLibrary(b *testing.B) {
	db := createTestDatabaseForBench(b)
	defer db.Close()
	repo := storage.NewRepository(db)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		library := &models.Library{
			SteamUserID: fmt.Sprintf("user_%d", i),
			Username:    fmt.Sprintf("User %d", i),
		}
		repo.CreateLibrary(library)
	}
}

func BenchmarkSyncService_CreateGame(b *testing.B) {
	db := createTestDatabaseForBench(b)
	defer db.Close()
	repo := storage.NewRepository(db)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		game := &models.Game{
			SteamAppID:       fmt.Sprintf("%d", i),
			SteamUserID:      "test_user",
			Name:             fmt.Sprintf("Game %d", i),
			PlaytimeForever:  i * 10,
			LastSteamAPISync: time.Now(),
		}
		repo.CreateGame(game)
	}
}

// Helper function to create test database for benchmarks
func createTestDatabaseForBench(tb testing.TB) *storage.Database {
	cfg := &storage.DatabaseConfig{
		Type:     "sqlite",
		Host:     ":memory:",
		Database: "test.db",
		Username: "",
		Password: "",
		Port:     0,
	}

	db, err := storage.NewDatabase(*cfg)
	if err != nil {
		tb.Fatalf("Failed to create test database: %v", err)
	}

	err = db.AutoMigrate()
	if err != nil {
		tb.Fatalf("Failed to run migrations: %v", err)
	}

	return db
}