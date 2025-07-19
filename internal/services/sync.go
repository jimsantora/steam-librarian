package services

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/jimsantora/steam-librarian/internal/models"
	"github.com/jimsantora/steam-librarian/internal/storage"
	"github.com/jimsantora/steam-librarian/internal/steam"
)

// SyncType represents the type of synchronization operation
type SyncType string

const (
	SyncTypeIncremental SyncType = "incremental" // Only sync new/changed games
	SyncTypeFull        SyncType = "full"        // Complete library refresh
)

// SyncStatus represents the current status of a sync operation
type SyncStatus string

const (
	SyncStatusPending    SyncStatus = "pending"
	SyncStatusRunning    SyncStatus = "running"
	SyncStatusCompleted  SyncStatus = "completed"
	SyncStatusFailed     SyncStatus = "failed"
	SyncStatusCancelled  SyncStatus = "cancelled"
)

// SyncProgress represents the progress of a sync operation
type SyncProgress struct {
	LibraryID        uint              `json:"library_id"`
	SteamUserID      string            `json:"steam_user_id"`
	SyncType         SyncType          `json:"sync_type"`
	Status           SyncStatus        `json:"status"`
	StartTime        time.Time         `json:"start_time"`
	EndTime          *time.Time        `json:"end_time,omitempty"`
	TotalGames       int               `json:"total_games"`
	ProcessedGames   int               `json:"processed_games"`
	SuccessfulGames  int               `json:"successful_games"`
	FailedGames      int               `json:"failed_games"`
	NewGames         int               `json:"new_games"`
	UpdatedGames     int               `json:"updated_games"`
	ErrorMessages    []string          `json:"error_messages,omitempty"`
	LastActivity     time.Time         `json:"last_activity"`
	Metadata         map[string]string `json:"metadata,omitempty"`
}

// PercentComplete calculates the completion percentage
func (sp *SyncProgress) PercentComplete() float64 {
	if sp.TotalGames == 0 {
		return 0
	}
	return float64(sp.ProcessedGames) / float64(sp.TotalGames) * 100
}

// Duration returns the duration of the sync operation
func (sp *SyncProgress) Duration() time.Duration {
	if sp.EndTime != nil {
		return sp.EndTime.Sub(sp.StartTime)
	}
	return time.Since(sp.StartTime)
}

// LibrarySyncService orchestrates the synchronization of Steam libraries
type LibrarySyncService struct {
	repo             *storage.Repository
	steamAPI         *steam.APIService
	conflictResolver *ConflictResolver
	logger           *logrus.Logger
	activeSync       sync.Map // map[string]*SyncProgress - keyed by steam_user_id
	syncHistory      sync.Map // map[string][]*SyncProgress - sync history per user
	maxConcurrent    int      // Maximum concurrent sync operations
	semaphore        chan struct{}
	ctx              context.Context
	cancel           context.CancelFunc
}

// NewLibrarySyncService creates a new library synchronization service
func NewLibrarySyncService(repo *storage.Repository, steamAPI *steam.APIService, logger *logrus.Logger) *LibrarySyncService {
	ctx, cancel := context.WithCancel(context.Background())
	
	maxConcurrent := 3 // Allow up to 3 concurrent syncs
	
	// Initialize conflict resolver with default configuration
	conflictResolver := NewConflictResolver(DefaultConflictResolutionConfig(), repo, logger)
	
	return &LibrarySyncService{
		repo:             repo,
		steamAPI:         steamAPI,
		conflictResolver: conflictResolver,
		logger:           logger,
		maxConcurrent:    maxConcurrent,
		semaphore:        make(chan struct{}, maxConcurrent),
		ctx:              ctx,
		cancel:           cancel,
	}
}

// SyncLibraryAsync starts an asynchronous sync operation for a library
func (s *LibrarySyncService) SyncLibraryAsync(steamUserID string, syncType SyncType) (*SyncProgress, error) {
	// Check if sync is already running for this user
	if existing, ok := s.activeSync.Load(steamUserID); ok {
		existingProgress := existing.(*SyncProgress)
		if existingProgress.Status == SyncStatusRunning {
			return existingProgress, fmt.Errorf("sync already running for user %s", steamUserID)
		}
	}

	// Get or create library record
	library, err := s.repo.GetLibraryByUserID(steamUserID)
	if err != nil {
		return nil, fmt.Errorf("failed to get library: %w", err)
	}

	var libraryID uint
	if library == nil {
		// Create new library record
		newLibrary := &models.Library{
			SteamUserID:    steamUserID,
			SyncInProgress: true,
		}
		
		// Get user profile to populate library details
		profile, err := s.steamAPI.GetClient().GetPlayerSummary(steamUserID)
		if err != nil {
			s.logger.WithError(err).Warn("Failed to get player summary for new library")
		} else {
			newLibrary.Username = profile.PersonaName
			newLibrary.ProfileURL = profile.ProfileURL
			newLibrary.AvatarURL = profile.Avatar
		}
		
		if err := s.repo.CreateLibrary(newLibrary); err != nil {
			return nil, fmt.Errorf("failed to create library: %w", err)
		}
		libraryID = newLibrary.ID
	} else {
		libraryID = library.ID
		// Mark sync as in progress
		library.SyncInProgress = true
		if err := s.repo.UpdateLibrary(library); err != nil {
			return nil, fmt.Errorf("failed to update library: %w", err)
		}
	}

	// Create sync progress tracking
	progress := &SyncProgress{
		LibraryID:       libraryID,
		SteamUserID:     steamUserID,
		SyncType:        syncType,
		Status:          SyncStatusPending,
		StartTime:       time.Now(),
		LastActivity:    time.Now(),
		ErrorMessages:   []string{},
		Metadata:        make(map[string]string),
	}

	// Store in active syncs
	s.activeSync.Store(steamUserID, progress)

	// Start sync in background
	go s.performSync(progress)

	s.logger.WithFields(logrus.Fields{
		"steam_user_id": steamUserID,
		"library_id":    libraryID,
		"sync_type":     syncType,
	}).Info("Started library sync")

	return progress, nil
}

// GetSyncProgress returns the current sync progress for a user
func (s *LibrarySyncService) GetSyncProgress(steamUserID string) (*SyncProgress, bool) {
	if progress, ok := s.activeSync.Load(steamUserID); ok {
		return progress.(*SyncProgress), true
	}
	return nil, false
}

// GetSyncHistory returns the sync history for a user
func (s *LibrarySyncService) GetSyncHistory(steamUserID string) []*SyncProgress {
	if history, ok := s.syncHistory.Load(steamUserID); ok {
		return history.([]*SyncProgress)
	}
	return []*SyncProgress{}
}

// CancelSync cancels an active sync operation
func (s *LibrarySyncService) CancelSync(steamUserID string) error {
	progress, ok := s.activeSync.Load(steamUserID)
	if !ok {
		return fmt.Errorf("no active sync found for user %s", steamUserID)
	}

	syncProgress := progress.(*SyncProgress)
	if syncProgress.Status != SyncStatusRunning {
		return fmt.Errorf("sync is not running for user %s", steamUserID)
	}

	syncProgress.Status = SyncStatusCancelled
	now := time.Now()
	syncProgress.EndTime = &now
	syncProgress.LastActivity = now

	s.logger.WithField("steam_user_id", steamUserID).Info("Cancelled library sync")
	
	return nil
}

// GetActiveSync returns all currently active sync operations
func (s *LibrarySyncService) GetActiveSyncs() map[string]*SyncProgress {
	result := make(map[string]*SyncProgress)
	s.activeSync.Range(func(key, value interface{}) bool {
		steamUserID := key.(string)
		progress := value.(*SyncProgress)
		if progress.Status == SyncStatusRunning || progress.Status == SyncStatusPending {
			result[steamUserID] = progress
		}
		return true
	})
	return result
}

// performSync executes the actual synchronization logic
func (s *LibrarySyncService) performSync(progress *SyncProgress) {
	// Acquire semaphore to limit concurrent syncs
	select {
	case s.semaphore <- struct{}{}:
		defer func() { <-s.semaphore }()
	case <-s.ctx.Done():
		s.finalizeSyncWithError(progress, "service shutdown")
		return
	}

	// Update status to running
	progress.Status = SyncStatusRunning
	progress.LastActivity = time.Now()

	defer func() {
		// Always clean up and move to history
		s.finalizeSyncOperation(progress)
	}()

	s.logger.WithFields(logrus.Fields{
		"steam_user_id": progress.SteamUserID,
		"sync_type":     progress.SyncType,
	}).Info("Starting sync operation")

	// Perform the actual sync based on type
	var err error
	switch progress.SyncType {
	case SyncTypeIncremental:
		err = s.performIncrementalSync(progress)
	case SyncTypeFull:
		err = s.performFullSync(progress)
	default:
		err = fmt.Errorf("unknown sync type: %s", progress.SyncType)
	}

	// Update final status
	if err != nil {
		s.finalizeSyncWithError(progress, err.Error())
	} else {
		s.finalizeSyncWithSuccess(progress)
	}
}

// finalizeSyncWithError marks sync as failed and logs the error
func (s *LibrarySyncService) finalizeSyncWithError(progress *SyncProgress, errorMsg string) {
	progress.Status = SyncStatusFailed
	progress.ErrorMessages = append(progress.ErrorMessages, errorMsg)
	now := time.Now()
	progress.EndTime = &now
	progress.LastActivity = now

	s.logger.WithFields(logrus.Fields{
		"steam_user_id": progress.SteamUserID,
		"error":         errorMsg,
		"duration":      progress.Duration(),
	}).Error("Library sync failed")
}

// finalizeSyncWithSuccess marks sync as completed successfully
func (s *LibrarySyncService) finalizeSyncWithSuccess(progress *SyncProgress) {
	progress.Status = SyncStatusCompleted
	now := time.Now()
	progress.EndTime = &now
	progress.LastActivity = now

	s.logger.WithFields(logrus.Fields{
		"steam_user_id":     progress.SteamUserID,
		"total_games":       progress.TotalGames,
		"new_games":         progress.NewGames,
		"updated_games":     progress.UpdatedGames,
		"successful_games":  progress.SuccessfulGames,
		"failed_games":      progress.FailedGames,
		"duration":          progress.Duration(),
	}).Info("Library sync completed successfully")
}

// finalizeSyncOperation moves sync from active to history and updates library
func (s *LibrarySyncService) finalizeSyncOperation(progress *SyncProgress) {
	// Update library sync status
	if library, err := s.repo.GetLibraryByUserID(progress.SteamUserID); err == nil && library != nil {
		library.SyncInProgress = false
		if progress.Status == SyncStatusCompleted {
			library.LastLibrarySync = time.Now()
			if progress.SyncType == SyncTypeFull {
				library.LastFullSync = time.Now()
			}
			// Update library statistics
			if games, err := s.repo.GetGamesByUserID(progress.SteamUserID); err == nil {
				library.UpdateStats(games)
			}
		}
		s.repo.UpdateLibrary(library)
	}

	// Move to history
	s.moveToHistory(progress)

	// Remove from active syncs
	s.activeSync.Delete(progress.SteamUserID)
}

// moveToHistory adds the sync progress to the user's sync history
func (s *LibrarySyncService) moveToHistory(progress *SyncProgress) {
	var history []*SyncProgress
	if existing, ok := s.syncHistory.Load(progress.SteamUserID); ok {
		history = existing.([]*SyncProgress)
	}
	
	// Add to history and keep only last 10 entries
	history = append(history, progress)
	if len(history) > 10 {
		history = history[len(history)-10:]
	}
	
	s.syncHistory.Store(progress.SteamUserID, history)
}

// performIncrementalSync performs an incremental sync (only new/changed games)
func (s *LibrarySyncService) performIncrementalSync(progress *SyncProgress) error {
	s.logger.WithField("steam_user_id", progress.SteamUserID).Info("Starting incremental sync")

	// Get recently played games (games active in last 2 weeks)
	recentGames, err := s.steamAPI.GetClient().GetRecentlyPlayedGames(progress.SteamUserID)
	if err != nil {
		return fmt.Errorf("failed to get recently played games: %w", err)
	}

	// Also get owned games to check for new additions
	ownedGames, err := s.steamAPI.GetClient().GetOwnedGames(progress.SteamUserID, true, true)
	if err != nil {
		return fmt.Errorf("failed to get owned games: %w", err)
	}

	// Get existing games from database
	existingGames, err := s.repo.GetGamesByUserID(progress.SteamUserID)
	if err != nil {
		return fmt.Errorf("failed to get existing games: %w", err)
	}

	// Create map of existing games for quick lookup
	existingGameMap := make(map[string]*models.Game)
	for i := range existingGames {
		existingGameMap[existingGames[i].SteamAppID] = &existingGames[i]
	}

	// Determine games to sync (recently played + new games)
	gamesToSync := make(map[string]bool)
	
	// Add recently played games
	for _, game := range recentGames.Response.Games {
		gamesToSync[fmt.Sprintf("%d", game.AppID)] = true
	}

	// Add new games (not in existing database)
	for _, game := range ownedGames.Response.Games {
		steamAppID := fmt.Sprintf("%d", game.AppID)
		if _, exists := existingGameMap[steamAppID]; !exists {
			gamesToSync[steamAppID] = true
		}
	}

	progress.TotalGames = len(gamesToSync)
	
	// Sync each game
	for steamAppID := range gamesToSync {
		if progress.Status == SyncStatusCancelled {
			return fmt.Errorf("sync cancelled")
		}

		err := s.syncSingleGame(progress, steamAppID, existingGameMap[steamAppID])
		if err != nil {
			progress.FailedGames++
			progress.ErrorMessages = append(progress.ErrorMessages, fmt.Sprintf("Game %s: %v", steamAppID, err))
			s.logger.WithError(err).WithField("steam_app_id", steamAppID).Warn("Failed to sync game")
		} else {
			progress.SuccessfulGames++
			if existingGameMap[steamAppID] == nil {
				progress.NewGames++
			} else {
				progress.UpdatedGames++
			}
		}
		
		progress.ProcessedGames++
		progress.LastActivity = time.Now()
	}

	return nil
}

// performFullSync performs a complete library refresh
func (s *LibrarySyncService) performFullSync(progress *SyncProgress) error {
	s.logger.WithField("steam_user_id", progress.SteamUserID).Info("Starting full sync")

	// Get all owned games
	ownedGames, err := s.steamAPI.GetClient().GetOwnedGames(progress.SteamUserID, true, true)
	if err != nil {
		return fmt.Errorf("failed to get owned games: %w", err)
	}

	progress.TotalGames = len(ownedGames.Response.Games)

	// Get existing games from database
	existingGames, err := s.repo.GetGamesByUserID(progress.SteamUserID)
	if err != nil {
		return fmt.Errorf("failed to get existing games: %w", err)
	}

	// Create map of existing games for quick lookup
	existingGameMap := make(map[string]*models.Game)
	for i := range existingGames {
		existingGameMap[existingGames[i].SteamAppID] = &existingGames[i]
	}

	// Sync each game
	for _, steamGame := range ownedGames.Response.Games {
		if progress.Status == SyncStatusCancelled {
			return fmt.Errorf("sync cancelled")
		}

		steamAppID := fmt.Sprintf("%d", steamGame.AppID)
		existingGame := existingGameMap[steamAppID]
		
		err := s.syncSingleGame(progress, steamAppID, existingGame)
		if err != nil {
			progress.FailedGames++
			progress.ErrorMessages = append(progress.ErrorMessages, fmt.Sprintf("Game %s: %v", steamAppID, err))
			s.logger.WithError(err).WithField("steam_app_id", steamAppID).Warn("Failed to sync game")
		} else {
			progress.SuccessfulGames++
			if existingGame == nil {
				progress.NewGames++
			} else {
				progress.UpdatedGames++
			}
		}
		
		progress.ProcessedGames++
		progress.LastActivity = time.Now()

		// Small delay to be respectful to Steam API
		time.Sleep(100 * time.Millisecond)
	}

	return nil
}

// syncSingleGame synchronizes a single game's data
func (s *LibrarySyncService) syncSingleGame(progress *SyncProgress, steamAppID string, existingGame *models.Game) error {
	// Convert steamAppID to int for API calls
	var appID int
	if _, err := fmt.Sscanf(steamAppID, "%d", &appID); err != nil {
		return fmt.Errorf("invalid steam app ID: %s", steamAppID)
	}

	// Get basic game info from owned games list
	ownedGames, err := s.steamAPI.GetClient().GetOwnedGames(progress.SteamUserID, true, true)
	if err != nil {
		return fmt.Errorf("failed to get owned games: %w", err)
	}

	var steamGame *steam.SteamGame
	for _, game := range ownedGames.Response.Games {
		if game.AppID == appID {
			steamGame = &game
			break
		}
	}

	if steamGame == nil {
		return fmt.Errorf("game not found in owned games")
	}

	// Create or update game model
	var game *models.Game
	if existingGame != nil {
		game = existingGame
	} else {
		game = &models.Game{
			SteamAppID:         steamAppID,
			SteamUserID:        progress.SteamUserID,
			DateAddedToLibrary: time.Now(), // Approximate, Steam doesn't provide exact date
		}
	}

	// Update basic fields from owned games data
	game.Name = steamGame.Name
	game.PlaytimeForever = steamGame.Playtime
	game.LastSteamAPISync = time.Now()

	// Try to get detailed app information (this might fail for some games)
	if appDetails, err := s.steamAPI.GetClient().GetAppDetails(appID); err == nil {
		s.updateGameWithAppDetails(game, appDetails)
	} else {
		s.logger.WithError(err).WithField("steam_app_id", steamAppID).Debug("Failed to get app details")
	}

	// Try to get review information
	if reviews, err := s.steamAPI.GetClient().GetAppReviews(appID); err == nil {
		game.UserReviewSummary = reviews.QuerySummary.ReviewScoreDesc
		game.ReviewScore = reviews.QuerySummary.ReviewScore
		game.ReviewCount = reviews.QuerySummary.TotalReviews
	} else {
		s.logger.WithError(err).WithField("steam_app_id", steamAppID).Debug("Failed to get app reviews")
	}

	// Save to database
	if existingGame != nil {
		return s.repo.UpdateGame(game)
	} else {
		return s.repo.CreateGame(game)
	}
}

// updateGameWithAppDetails updates a game model with detailed app information
func (s *LibrarySyncService) updateGameWithAppDetails(game *models.Game, details *steam.GameDetails) {
	game.ShortDescription = details.ShortDesc
	game.HeaderImage = details.HeaderImage
	game.CapsuleImage = details.CapsuleImage
	game.StoreURL = fmt.Sprintf("https://store.steampowered.com/app/%s/", game.SteamAppID)

	// Developer and publisher (join multiple values)
	if len(details.Developer) > 0 {
		game.Developer = details.Developer[0] // Take first developer
	}
	if len(details.Publisher) > 0 {
		game.Publisher = details.Publisher[0] // Take first publisher
	}

	// Release date parsing (simplified)
	if !details.ReleaseDate.ComingSoon && details.ReleaseDate.Date != "" {
		// Try to parse the release date - Steam uses various formats
		formats := []string{
			"2 Jan, 2006",
			"Jan 2, 2006",
			"2006",
			"Jan 2006",
		}
		
		for _, format := range formats {
			if releaseDate, err := time.Parse(format, details.ReleaseDate.Date); err == nil {
				game.ReleaseDate = releaseDate
				break
			}
		}
	}

	// Categories and genres (simplified - store as comma-separated for now)
	if len(details.Categories) > 0 {
		categories := make([]string, len(details.Categories))
		for i, cat := range details.Categories {
			categories[i] = cat.Description
		}
		game.Categories = fmt.Sprintf(`["%s"]`, details.Categories[0].Description) // JSON-like format
	}

	if len(details.Genres) > 0 {
		genres := make([]string, len(details.Genres))
		for i, genre := range details.Genres {
			genres[i] = genre.Description
		}
		game.Genres = fmt.Sprintf(`["%s"]`, details.Genres[0].Description) // JSON-like format
	}
}

// GetConflictResolver returns the conflict resolver instance
func (s *LibrarySyncService) GetConflictResolver() *ConflictResolver {
	return s.conflictResolver
}

// Shutdown gracefully shuts down the sync service
func (s *LibrarySyncService) Shutdown() {
	s.logger.Info("Shutting down library sync service")
	s.cancel()
	
	// Cleanup old conflicts before shutdown
	s.conflictResolver.CleanupOldConflicts()
	
	// Wait for active syncs to complete or timeout after 30 seconds
	timeout := time.NewTimer(30 * time.Second)
	defer timeout.Stop()
	
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	
	for {
		activeSyncs := s.GetActiveSyncs()
		if len(activeSyncs) == 0 {
			break
		}
		
		select {
		case <-timeout.C:
			s.logger.Warn("Timeout waiting for syncs to complete, forcing shutdown")
			return
		case <-ticker.C:
			continue
		}
	}
	
	s.logger.Info("Library sync service shutdown complete")
}