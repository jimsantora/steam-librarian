package services

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/jimsantora/steam-librarian/internal/storage"
)

// Unit tests for individual components

func TestConflictResolver_Configuration(t *testing.T) {
	// Test default configuration
	config := DefaultConflictResolutionConfig()
	require.NotNil(t, config)
	
	assert.Equal(t, ConflictStrategyMerge, config.DefaultStrategy)
	assert.True(t, config.AutoResolveEnabled)
	assert.True(t, config.BackupBeforeResolve)
	assert.Equal(t, 30, config.MaxConflictAge)
	
	// Test strategy by type
	assert.Equal(t, ConflictStrategyPreferSteam, config.StrategyByType[ConflictTypeGameMetadata])
	assert.Equal(t, ConflictStrategyPreferLocal, config.StrategyByType[ConflictTypeCustomTags])
	assert.Equal(t, ConflictStrategyManual, config.StrategyByType[ConflictTypeGameDeletion])
	
	// Test preserved fields
	assert.Contains(t, config.PreserveCustomFields, "custom_tags")
	assert.Contains(t, config.PreserveCustomFields, "custom_notes")
}

func TestConflictResolver_Statistics(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()
	
	repo := storage.NewRepository(db)
	logger := createTestLogger()
	config := DefaultConflictResolutionConfig()
	
	resolver := NewConflictResolver(config, repo, logger)
	
	// Test initial statistics
	stats := resolver.GetStatistics()
	require.NotNil(t, stats)
	
	assert.Equal(t, 0, stats["total_conflicts"])
	assert.Equal(t, 0, stats["pending"])
	assert.Equal(t, 0, stats["resolved"])
	assert.Equal(t, 0, stats["failed"])
	assert.Equal(t, 0, stats["ignored"])
	assert.True(t, stats["auto_resolve_enabled"].(bool))
	assert.Equal(t, ConflictStrategyMerge, stats["default_strategy"])
}

func TestConflictResolver_ConflictOperations(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()
	
	repo := storage.NewRepository(db)
	logger := createTestLogger()
	config := DefaultConflictResolutionConfig()
	
	resolver := NewConflictResolver(config, repo, logger)
	
	// Test getting conflicts (should be empty initially)
	conflicts := resolver.GetConflicts("", "")
	assert.Empty(t, conflicts)
	
	// Test getting conflicts by status
	pendingConflicts := resolver.GetConflicts(ConflictStatusPending, "")
	assert.Empty(t, pendingConflicts)
	
	// Test getting conflicts by type
	playtimeConflicts := resolver.GetConflicts("", ConflictTypePlaytime)
	assert.Empty(t, playtimeConflicts)
	
	// Test getting non-existent conflict
	conflict, exists := resolver.GetConflictByID("nonexistent")
	assert.False(t, exists)
	assert.Nil(t, conflict)
	
	// Test auto-resolution (should succeed with no conflicts)
	err := resolver.AutoResolveConflicts()
	assert.NoError(t, err)
	
	// Test cleanup (should succeed with no conflicts)
	resolver.CleanupOldConflicts()
}

func TestSyncScheduler_Configuration(t *testing.T) {
	// Test default configuration
	config := DefaultSchedulerConfig()
	require.NotNil(t, config)
	
	assert.False(t, config.AutoSyncEnabled) // Should be disabled by default
	assert.Equal(t, 6*time.Hour, config.IncrementalSyncInterval)
	assert.Equal(t, 24*time.Hour, config.FullSyncInterval)
	assert.Equal(t, 2, config.MaxConcurrentAutoSyncs)
	assert.Equal(t, 1, config.QuietHoursStart)
	assert.Equal(t, 6, config.QuietHoursEnd)
	assert.True(t, config.OnlyScheduleIfActive)
	assert.Equal(t, 7, config.ActivityThresholdDays)
}

func TestSyncScheduler_Lifecycle(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()
	
	repo := storage.NewRepository(db)
	steamAPI := createMockSteamAPI(t)
	logger := createTestLogger()
	
	syncService := NewLibrarySyncService(repo, steamAPI, logger)
	defer syncService.Shutdown()
	
	config := DefaultSchedulerConfig()
	config.AutoSyncEnabled = false // Keep disabled for testing
	
	scheduler := NewSyncScheduler(config, syncService, repo, logger)
	
	// Test initial status
	status := scheduler.GetStatus()
	require.NotNil(t, status)
	assert.False(t, status["running"].(bool))
	assert.False(t, status["auto_sync_enabled"].(bool))
	assert.Equal(t, int64(0), status["scheduled_syncs"])
	assert.Equal(t, int64(0), status["completed_syncs"])
	assert.Equal(t, int64(0), status["failed_syncs"])
	
	// Test starting scheduler (should be no-op since disabled)
	err := scheduler.Start()
	assert.NoError(t, err)
	
	// Test stopping scheduler
	scheduler.Stop()
	
	// Status should still show not running since auto-sync is disabled
	finalStatus := scheduler.GetStatus()
	assert.False(t, finalStatus["running"].(bool))
}

func TestSyncScheduler_ConfigurationUpdate(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()
	
	repo := storage.NewRepository(db)
	steamAPI := createMockSteamAPI(t)
	logger := createTestLogger()
	
	syncService := NewLibrarySyncService(repo, steamAPI, logger)
	defer syncService.Shutdown()
	
	config := DefaultSchedulerConfig()
	scheduler := NewSyncScheduler(config, syncService, repo, logger)
	defer scheduler.Stop()
	
	// Test updating configuration
	newConfig := &SchedulerConfig{
		AutoSyncEnabled:          false, // Keep disabled
		IncrementalSyncInterval:  2 * time.Hour,
		FullSyncInterval:         48 * time.Hour,
		MaxConcurrentAutoSyncs:   3,
		QuietHoursStart:          2,
		QuietHoursEnd:            7,
		OnlyScheduleIfActive:     false,
		ActivityThresholdDays:    14,
	}
	
	err := scheduler.UpdateConfig(newConfig)
	assert.NoError(t, err)
	
	// Verify configuration was updated
	status := scheduler.GetStatus()
	assert.Equal(t, "2h0m0s", status["incremental_interval"])
	assert.Equal(t, "48h0m0s", status["full_interval"])
	assert.Equal(t, "02:00 - 07:00", status["quiet_hours"])
}

func TestSyncScheduler_QuietHours(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()
	
	repo := storage.NewRepository(db)
	steamAPI := createMockSteamAPI(t)
	logger := createTestLogger()
	
	syncService := NewLibrarySyncService(repo, steamAPI, logger)
	defer syncService.Shutdown()
	
	// Test different quiet hour configurations
	testCases := []struct {
		name      string
		start     int
		end       int
		expected  string
	}{
		{"Normal hours", 1, 6, "01:00 - 06:00"},
		{"Overnight hours", 23, 6, "23:00 - 06:00"},
		{"Disabled", 0, 0, "disabled"},
		{"Same hour", 5, 5, "disabled"},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			config := DefaultSchedulerConfig()
			config.QuietHoursStart = tc.start
			config.QuietHoursEnd = tc.end
			
			scheduler := NewSyncScheduler(config, syncService, repo, logger)
			defer scheduler.Stop()
			
			status := scheduler.GetStatus()
			assert.Equal(t, tc.expected, status["quiet_hours"])
		})
	}
}

func TestSyncProgress_Methods(t *testing.T) {
	// Test SyncProgress helper methods
	progress := &SyncProgress{
		TotalGames:     100,
		ProcessedGames: 50,
		StartTime:      time.Now().Add(-30 * time.Minute),
		EndTime:        nil, // Still running
	}
	
	// Test PercentComplete
	percent := progress.PercentComplete()
	assert.Equal(t, 50.0, percent)
	
	// Test Duration (still running)
	duration := progress.Duration()
	assert.Greater(t, duration, 25*time.Minute)
	assert.Less(t, duration, 35*time.Minute)
	
	// Test with zero total games
	progress.TotalGames = 0
	percent = progress.PercentComplete()
	assert.Equal(t, 0.0, percent)
	
	// Test with completed sync
	endTime := time.Now()
	progress.EndTime = &endTime
	progress.TotalGames = 100
	
	completedDuration := progress.Duration()
	assert.Greater(t, completedDuration, 25*time.Minute)
	assert.Less(t, completedDuration, 35*time.Minute)
	
	// Test 100% completion
	progress.ProcessedGames = 100
	percent = progress.PercentComplete()
	assert.Equal(t, 100.0, percent)
}

func TestConflictTypes_Constants(t *testing.T) {
	// Test that all conflict types are defined
	conflictTypes := []ConflictType{
		ConflictTypeGameMetadata,
		ConflictTypePlaytime,
		ConflictTypeCustomTags,
		ConflictTypeCustomNotes,
		ConflictTypeCustomRating,
		ConflictTypeGameDeletion,
		ConflictTypeGameAddition,
	}
	
	for _, conflictType := range conflictTypes {
		assert.NotEmpty(t, string(conflictType))
	}
}

func TestConflictResolutionStrategies_Constants(t *testing.T) {
	// Test that all resolution strategies are defined
	strategies := []ConflictResolutionStrategy{
		ConflictStrategyPreferSteam,
		ConflictStrategyPreferLocal,
		ConflictStrategyManual,
		ConflictStrategyMerge,
		ConflictStrategyNewest,
	}
	
	for _, strategy := range strategies {
		assert.NotEmpty(t, string(strategy))
	}
}

func TestSyncTypes_Constants(t *testing.T) {
	// Test that sync types are defined correctly
	assert.Equal(t, SyncType("incremental"), SyncTypeIncremental)
	assert.Equal(t, SyncType("full"), SyncTypeFull)
}

func TestSyncStatus_Constants(t *testing.T) {
	// Test that sync statuses are defined correctly
	statuses := []SyncStatus{
		SyncStatusPending,
		SyncStatusRunning,
		SyncStatusCompleted,
		SyncStatusFailed,
		SyncStatusCancelled,
	}
	
	for _, status := range statuses {
		assert.NotEmpty(t, string(status))
	}
}

// Error handling unit tests

func TestConflictResolver_ErrorHandling(t *testing.T) {
	// Setup
	db := createTestDatabase(t)
	defer db.Close()
	
	repo := storage.NewRepository(db)
	logger := createTestLogger()
	config := DefaultConflictResolutionConfig()
	
	resolver := NewConflictResolver(config, repo, logger)
	
	// Test resolving non-existent conflict
	err := resolver.ResolveConflict("nonexistent", ConflictStrategyPreferSteam, "test_user")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "conflict nonexistent not found")
}

// Performance tests

func BenchmarkSyncProgress_PercentComplete(b *testing.B) {
	progress := &SyncProgress{
		TotalGames:     1000,
		ProcessedGames: 500,
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		progress.PercentComplete()
	}
}

func BenchmarkConflictResolver_GetStatistics(b *testing.B) {
	db := createTestDatabaseForBench(b)
	defer db.Close()
	
	repo := storage.NewRepository(db)
	logger := createTestLogger()
	config := DefaultConflictResolutionConfig()
	
	resolver := NewConflictResolver(config, repo, logger)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		resolver.GetStatistics()
	}
}

