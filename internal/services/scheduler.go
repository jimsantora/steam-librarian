package services

import (
	"context"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/jimsantora/steam-librarian/internal/models"
	"github.com/jimsantora/steam-librarian/internal/storage"
)

// SchedulerConfig contains configuration for the sync scheduler
type SchedulerConfig struct {
	// AutoSyncEnabled enables automatic background syncs
	AutoSyncEnabled bool `json:"auto_sync_enabled"`
	
	// IncrementalSyncInterval is how often to run incremental syncs
	IncrementalSyncInterval time.Duration `json:"incremental_sync_interval"`
	
	// FullSyncInterval is how often to run full syncs
	FullSyncInterval time.Duration `json:"full_sync_interval"`
	
	// MaxConcurrentAutoSyncs limits concurrent automatic syncs
	MaxConcurrentAutoSyncs int `json:"max_concurrent_auto_syncs"`
	
	// QuietHoursStart defines when to avoid automatic syncs (24-hour format)
	QuietHoursStart int `json:"quiet_hours_start"`
	
	// QuietHoursEnd defines when automatic syncs can resume (24-hour format)
	QuietHoursEnd int `json:"quiet_hours_end"`
	
	// OnlyScheduleIfActive only schedules syncs for libraries with recent activity
	OnlyScheduleIfActive bool `json:"only_schedule_if_active"`
	
	// ActivityThresholdDays defines how many days ago counts as "recent activity"
	ActivityThresholdDays int `json:"activity_threshold_days"`
}

// DefaultSchedulerConfig returns sensible defaults for the scheduler
func DefaultSchedulerConfig() *SchedulerConfig {
	return &SchedulerConfig{
		AutoSyncEnabled:          false,               // Disabled by default
		IncrementalSyncInterval:  6 * time.Hour,      // Every 6 hours
		FullSyncInterval:         24 * time.Hour,     // Once per day
		MaxConcurrentAutoSyncs:   2,                  // Maximum 2 automatic syncs at once
		QuietHoursStart:          1,                  // 1 AM
		QuietHoursEnd:            6,                  // 6 AM
		OnlyScheduleIfActive:     true,               // Only sync recently active libraries
		ActivityThresholdDays:    7,                  // Consider libraries active within 7 days
	}
}

// SyncScheduler manages automatic background sync operations
type SyncScheduler struct {
	config       *SchedulerConfig
	syncService  *LibrarySyncService
	repo         *storage.Repository
	logger       *logrus.Logger
	
	// Internal state
	ctx          context.Context
	cancel       context.CancelFunc
	ticker       *time.Ticker
	running      bool
	mu           sync.RWMutex
	
	// Statistics
	scheduledSyncs    int64
	completedSyncs    int64
	failedSyncs       int64
	lastSchedulerRun  time.Time
}

// NewSyncScheduler creates a new sync scheduler
func NewSyncScheduler(config *SchedulerConfig, syncService *LibrarySyncService, repo *storage.Repository, logger *logrus.Logger) *SyncScheduler {
	if config == nil {
		config = DefaultSchedulerConfig()
	}
	
	ctx, cancel := context.WithCancel(context.Background())
	
	return &SyncScheduler{
		config:       config,
		syncService:  syncService,
		repo:         repo,
		logger:       logger,
		ctx:          ctx,
		cancel:       cancel,
		running:      false,
	}
}

// Start begins the background sync scheduler
func (s *SyncScheduler) Start() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	
	if s.running {
		return nil // Already running
	}
	
	if !s.config.AutoSyncEnabled {
		s.logger.Info("Auto-sync is disabled, scheduler will not start")
		return nil
	}
	
	s.logger.WithFields(logrus.Fields{
		"incremental_interval": s.config.IncrementalSyncInterval,
		"full_interval":        s.config.FullSyncInterval,
		"quiet_hours":          s.formatQuietHours(),
	}).Info("Starting sync scheduler")
	
	// Use the shorter of the two intervals for the ticker
	tickerInterval := s.config.IncrementalSyncInterval
	if s.config.FullSyncInterval < tickerInterval {
		tickerInterval = s.config.FullSyncInterval
	}
	
	s.ticker = time.NewTicker(tickerInterval)
	s.running = true
	
	// Start the scheduler goroutine
	go s.schedulerLoop()
	
	return nil
}

// Stop gracefully stops the sync scheduler
func (s *SyncScheduler) Stop() {
	s.mu.Lock()
	defer s.mu.Unlock()
	
	if !s.running {
		return
	}
	
	s.logger.Info("Stopping sync scheduler")
	
	if s.ticker != nil {
		s.ticker.Stop()
	}
	
	s.cancel()
	s.running = false
	
	s.logger.WithFields(logrus.Fields{
		"scheduled_syncs":  s.scheduledSyncs,
		"completed_syncs":  s.completedSyncs,
		"failed_syncs":     s.failedSyncs,
	}).Info("Sync scheduler stopped")
}

// UpdateConfig updates the scheduler configuration
func (s *SyncScheduler) UpdateConfig(config *SchedulerConfig) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	
	oldEnabled := s.config.AutoSyncEnabled
	s.config = config
	
	s.logger.WithField("auto_sync_enabled", config.AutoSyncEnabled).Info("Scheduler configuration updated")
	
	// If auto-sync was disabled and is now enabled, start the scheduler
	if !oldEnabled && config.AutoSyncEnabled && !s.running {
		s.mu.Unlock() // Unlock before calling Start to avoid deadlock
		return s.Start()
	}
	
	// If auto-sync was enabled and is now disabled, stop the scheduler
	if oldEnabled && !config.AutoSyncEnabled && s.running {
		s.Stop()
	}
	
	return nil
}

// GetStatus returns the current scheduler status and statistics
func (s *SyncScheduler) GetStatus() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()
	
	return map[string]interface{}{
		"running":              s.running,
		"auto_sync_enabled":    s.config.AutoSyncEnabled,
		"scheduled_syncs":      s.scheduledSyncs,
		"completed_syncs":      s.completedSyncs,
		"failed_syncs":         s.failedSyncs,
		"last_scheduler_run":   s.lastSchedulerRun,
		"incremental_interval": s.config.IncrementalSyncInterval.String(),
		"full_interval":        s.config.FullSyncInterval.String(),
		"quiet_hours":          s.formatQuietHours(),
	}
}

// schedulerLoop runs the main scheduler logic
func (s *SyncScheduler) schedulerLoop() {
	for {
		select {
		case <-s.ctx.Done():
			s.logger.Debug("Scheduler context cancelled, exiting loop")
			return
		case <-s.ticker.C:
			s.runScheduledSyncs()
		}
	}
}

// runScheduledSyncs checks for and runs any scheduled sync operations
func (s *SyncScheduler) runScheduledSyncs() {
	s.mu.Lock()
	s.lastSchedulerRun = time.Now()
	s.mu.Unlock()
	
	// Check if we're in quiet hours
	if s.isQuietHours() {
		s.logger.Debug("Skipping scheduled syncs during quiet hours")
		return
	}
	
	s.logger.Debug("Running scheduled sync check")
	
	// Get all libraries
	libraries, err := s.repo.GetAllLibraries()
	if err != nil {
		s.logger.WithError(err).Error("Failed to get libraries for scheduled sync")
		return
	}
	
	// Check each library for sync needs
	for _, library := range libraries {
		if s.shouldScheduleSync(&library) {
			s.scheduleLibrarySync(&library)
		}
	}
}

// shouldScheduleSync determines if a library needs to be synced
func (s *SyncScheduler) shouldScheduleSync(library *models.Library) bool {
	now := time.Now()
	
	// Skip if sync is already in progress
	if library.SyncInProgress {
		return false
	}
	
	// Check if there's already an active sync for this user
	if _, hasActiveSync := s.syncService.GetSyncProgress(library.SteamUserID); hasActiveSync {
		return false
	}
	
	// Check activity threshold if configured
	if s.config.OnlyScheduleIfActive {
		threshold := now.AddDate(0, 0, -s.config.ActivityThresholdDays)
		if library.LastLibrarySync.Before(threshold) && library.UpdatedAt.Before(threshold) {
			s.logger.WithFields(logrus.Fields{
				"library_id":    library.ID,
				"steam_user_id": library.SteamUserID,
				"last_sync":     library.LastLibrarySync,
				"threshold":     threshold,
			}).Debug("Skipping inactive library")
			return false
		}
	}
	
	// Check if incremental sync is due
	if now.Sub(library.LastLibrarySync) >= s.config.IncrementalSyncInterval {
		return true
	}
	
	// Check if full sync is due
	if now.Sub(library.LastFullSync) >= s.config.FullSyncInterval {
		return true
	}
	
	return false
}

// scheduleLibrarySync schedules a sync for the given library
func (s *SyncScheduler) scheduleLibrarySync(library *models.Library) {
	now := time.Now()
	
	// Determine sync type
	syncType := SyncTypeIncremental
	if now.Sub(library.LastFullSync) >= s.config.FullSyncInterval {
		syncType = SyncTypeFull
	}
	
	s.logger.WithFields(logrus.Fields{
		"library_id":    library.ID,
		"steam_user_id": library.SteamUserID,
		"sync_type":     syncType,
	}).Info("Scheduling automatic library sync")
	
	// Start the sync
	progress, err := s.syncService.SyncLibraryAsync(library.SteamUserID, syncType)
	if err != nil {
		s.logger.WithError(err).WithFields(logrus.Fields{
			"library_id":    library.ID,
			"steam_user_id": library.SteamUserID,
		}).Error("Failed to schedule automatic sync")
		
		s.mu.Lock()
		s.failedSyncs++
		s.mu.Unlock()
		return
	}
	
	s.mu.Lock()
	s.scheduledSyncs++
	s.mu.Unlock()
	
	s.logger.WithFields(logrus.Fields{
		"library_id":    library.ID,
		"steam_user_id": library.SteamUserID,
		"sync_type":     syncType,
		"progress_id":   progress.LibraryID,
	}).Info("Automatic sync scheduled successfully")
}

// isQuietHours checks if current time is within configured quiet hours
func (s *SyncScheduler) isQuietHours() bool {
	if s.config.QuietHoursStart == s.config.QuietHoursEnd {
		return false // No quiet hours configured
	}
	
	now := time.Now()
	currentHour := now.Hour()
	
	start := s.config.QuietHoursStart
	end := s.config.QuietHoursEnd
	
	// Handle overnight quiet hours (e.g., 23:00 to 06:00)
	if start > end {
		return currentHour >= start || currentHour < end
	}
	
	// Handle same-day quiet hours (e.g., 01:00 to 06:00)
	return currentHour >= start && currentHour < end
}

// formatQuietHours returns a human-readable string for quiet hours
func (s *SyncScheduler) formatQuietHours() string {
	if s.config.QuietHoursStart == s.config.QuietHoursEnd {
		return "disabled"
	}
	return time.Time{}.Add(time.Duration(s.config.QuietHoursStart) * time.Hour).Format("15:04") + 
		" - " + 
		time.Time{}.Add(time.Duration(s.config.QuietHoursEnd) * time.Hour).Format("15:04")
}