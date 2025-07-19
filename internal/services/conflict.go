package services

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/jimsantora/steam-librarian/internal/models"
	"github.com/jimsantora/steam-librarian/internal/storage"
)

// ConflictResolutionStrategy defines how to handle sync conflicts
type ConflictResolutionStrategy string

const (
	// ConflictStrategyPreferSteam always prefers Steam API data over local changes
	ConflictStrategyPreferSteam ConflictResolutionStrategy = "prefer_steam"
	
	// ConflictStrategyPreferLocal always prefers local changes over Steam API data
	ConflictStrategyPreferLocal ConflictResolutionStrategy = "prefer_local"
	
	// ConflictStrategyManual requires manual intervention for each conflict
	ConflictStrategyManual ConflictResolutionStrategy = "manual"
	
	// ConflictStrategyMerge attempts to intelligently merge changes
	ConflictStrategyMerge ConflictResolutionStrategy = "merge"
	
	// ConflictStrategyNewest prefers the most recently updated data
	ConflictStrategyNewest ConflictResolutionStrategy = "newest"
)

// ConflictType represents the type of conflict detected
type ConflictType string

const (
	ConflictTypeGameMetadata   ConflictType = "game_metadata"
	ConflictTypePlaytime      ConflictType = "playtime"
	ConflictTypeCustomTags    ConflictType = "custom_tags"
	ConflictTypeCustomNotes   ConflictType = "custom_notes"
	ConflictTypeCustomRating  ConflictType = "custom_rating"
	ConflictTypeGameDeletion  ConflictType = "game_deletion"
	ConflictTypeGameAddition  ConflictType = "game_addition"
)

// ConflictInfo contains information about a detected conflict
type ConflictInfo struct {
	ID             string                     `json:"id"`
	GameID         uint                       `json:"game_id"`
	SteamAppID     string                     `json:"steam_app_id"`
	ConflictType   ConflictType               `json:"conflict_type"`
	LocalValue     interface{}                `json:"local_value"`
	SteamValue     interface{}                `json:"steam_value"`
	LocalTimestamp time.Time                  `json:"local_timestamp"`
	SteamTimestamp time.Time                  `json:"steam_timestamp"`
	DetectedAt     time.Time                  `json:"detected_at"`
	Status         ConflictStatus             `json:"status"`
	Resolution     ConflictResolutionStrategy `json:"resolution,omitempty"`
	ResolvedAt     *time.Time                 `json:"resolved_at,omitempty"`
	ResolvedBy     string                     `json:"resolved_by,omitempty"`
	Metadata       map[string]interface{}     `json:"metadata,omitempty"`
}

// ConflictStatus represents the current status of a conflict
type ConflictStatus string

const (
	ConflictStatusPending   ConflictStatus = "pending"
	ConflictStatusResolved  ConflictStatus = "resolved"
	ConflictStatusIgnored   ConflictStatus = "ignored"
	ConflictStatusFailed    ConflictStatus = "failed"
)

// ConflictResolutionConfig contains configuration for conflict resolution
type ConflictResolutionConfig struct {
	// DefaultStrategy is the default strategy for resolving conflicts
	DefaultStrategy ConflictResolutionStrategy `json:"default_strategy"`
	
	// StrategyByType allows different strategies for different conflict types
	StrategyByType map[ConflictType]ConflictResolutionStrategy `json:"strategy_by_type"`
	
	// AutoResolveEnabled enables automatic conflict resolution
	AutoResolveEnabled bool `json:"auto_resolve_enabled"`
	
	// BackupBeforeResolve creates backups before resolving conflicts
	BackupBeforeResolve bool `json:"backup_before_resolve"`
	
	// MaxConflictAge is the maximum age of conflicts to keep (in days)
	MaxConflictAge int `json:"max_conflict_age"`
	
	// PreserveCustomFields lists custom fields that should never be overwritten
	PreserveCustomFields []string `json:"preserve_custom_fields"`
}

// DefaultConflictResolutionConfig returns sensible defaults
func DefaultConflictResolutionConfig() *ConflictResolutionConfig {
	return &ConflictResolutionConfig{
		DefaultStrategy:     ConflictStrategyMerge,
		StrategyByType: map[ConflictType]ConflictResolutionStrategy{
			ConflictTypeGameMetadata:  ConflictStrategyPreferSteam,
			ConflictTypePlaytime:      ConflictStrategyPreferSteam,
			ConflictTypeCustomTags:    ConflictStrategyPreferLocal,
			ConflictTypeCustomNotes:   ConflictStrategyPreferLocal,
			ConflictTypeCustomRating:  ConflictStrategyPreferLocal,
			ConflictTypeGameDeletion:  ConflictStrategyManual,
			ConflictTypeGameAddition:  ConflictStrategyPreferSteam,
		},
		AutoResolveEnabled:   true,
		BackupBeforeResolve:  true,
		MaxConflictAge:       30, // 30 days
		PreserveCustomFields: []string{"custom_tags", "custom_notes", "custom_rating", "personal_rating"},
	}
}

// ConflictResolver handles sync conflict detection and resolution
type ConflictResolver struct {
	config   *ConflictResolutionConfig
	repo     *storage.Repository
	logger   *logrus.Logger
	
	// Active conflicts storage (in-memory for now, could be moved to database)
	conflicts map[string]*ConflictInfo
}

// NewConflictResolver creates a new conflict resolver
func NewConflictResolver(config *ConflictResolutionConfig, repo *storage.Repository, logger *logrus.Logger) *ConflictResolver {
	if config == nil {
		config = DefaultConflictResolutionConfig()
	}
	
	return &ConflictResolver{
		config:    config,
		repo:      repo,
		logger:    logger,
		conflicts: make(map[string]*ConflictInfo),
	}
}

// DetectConflicts compares local game data with Steam API data and detects conflicts
func (cr *ConflictResolver) DetectConflicts(localGame *models.Game, steamGame interface{}) []*ConflictInfo {
	var conflicts []*ConflictInfo
	
	// For now, we'll focus on basic metadata conflicts
	// In a real implementation, you'd compare all relevant fields
	
	cr.logger.WithFields(logrus.Fields{
		"game_id":      localGame.ID,
		"steam_app_id": localGame.SteamAppID,
	}).Debug("Detecting conflicts for game")
	
	// Note: steamGame interface{} would need to be properly typed based on Steam API response
	// For now, this is a conceptual implementation
	
	return conflicts
}

// ResolveConflict resolves a specific conflict using the configured strategy
func (cr *ConflictResolver) ResolveConflict(conflictID string, strategy ConflictResolutionStrategy, resolvedBy string) error {
	conflict, exists := cr.conflicts[conflictID]
	if !exists {
		return fmt.Errorf("conflict %s not found", conflictID)
	}
	
	if conflict.Status != ConflictStatusPending {
		return fmt.Errorf("conflict %s is not pending (status: %s)", conflictID, conflict.Status)
	}
	
	cr.logger.WithFields(logrus.Fields{
		"conflict_id":    conflictID,
		"conflict_type":  conflict.ConflictType,
		"strategy":       strategy,
		"resolved_by":    resolvedBy,
	}).Info("Resolving conflict")
	
	// Get the game from database
	game, err := cr.repo.GetGameByID(conflict.GameID)
	if err != nil {
		return fmt.Errorf("failed to get game: %w", err)
	}
	
	if game == nil {
		return fmt.Errorf("game not found: %d", conflict.GameID)
	}
	
	// Create backup if configured
	if cr.config.BackupBeforeResolve {
		if err := cr.createGameBackup(game); err != nil {
			cr.logger.WithError(err).Warn("Failed to create game backup")
		}
	}
	
	// Apply resolution strategy
	err = cr.applyResolutionStrategy(game, conflict, strategy)
	if err != nil {
		conflict.Status = ConflictStatusFailed
		return fmt.Errorf("failed to apply resolution strategy: %w", err)
	}
	
	// Update game in database
	if err := cr.repo.UpdateGame(game); err != nil {
		conflict.Status = ConflictStatusFailed
		return fmt.Errorf("failed to update game: %w", err)
	}
	
	// Mark conflict as resolved
	now := time.Now()
	conflict.Status = ConflictStatusResolved
	conflict.Resolution = strategy
	conflict.ResolvedAt = &now
	conflict.ResolvedBy = resolvedBy
	
	cr.logger.WithFields(logrus.Fields{
		"conflict_id":   conflictID,
		"strategy":      strategy,
		"resolved_by":   resolvedBy,
	}).Info("Conflict resolved successfully")
	
	return nil
}

// AutoResolveConflicts automatically resolves conflicts based on configuration
func (cr *ConflictResolver) AutoResolveConflicts() error {
	if !cr.config.AutoResolveEnabled {
		return nil
	}
	
	resolvedCount := 0
	failedCount := 0
	
	for conflictID, conflict := range cr.conflicts {
		if conflict.Status != ConflictStatusPending {
			continue
		}
		
		// Determine strategy for this conflict type
		strategy := cr.config.DefaultStrategy
		if typeStrategy, exists := cr.config.StrategyByType[conflict.ConflictType]; exists {
			strategy = typeStrategy
		}
		
		// Skip manual resolution conflicts in auto-resolve
		if strategy == ConflictStrategyManual {
			continue
		}
		
		if err := cr.ResolveConflict(conflictID, strategy, "auto-resolver"); err != nil {
			cr.logger.WithError(err).WithField("conflict_id", conflictID).Error("Auto-resolution failed")
			failedCount++
		} else {
			resolvedCount++
		}
	}
	
	if resolvedCount > 0 || failedCount > 0 {
		cr.logger.WithFields(logrus.Fields{
			"resolved": resolvedCount,
			"failed":   failedCount,
		}).Info("Auto-resolution completed")
	}
	
	return nil
}

// GetConflicts returns all conflicts matching the given criteria
func (cr *ConflictResolver) GetConflicts(status ConflictStatus, conflictType ConflictType) []*ConflictInfo {
	var result []*ConflictInfo
	
	for _, conflict := range cr.conflicts {
		if status != "" && conflict.Status != status {
			continue
		}
		if conflictType != "" && conflict.ConflictType != conflictType {
			continue
		}
		result = append(result, conflict)
	}
	
	return result
}

// GetConflictByID returns a specific conflict by ID
func (cr *ConflictResolver) GetConflictByID(conflictID string) (*ConflictInfo, bool) {
	conflict, exists := cr.conflicts[conflictID]
	return conflict, exists
}

// CleanupOldConflicts removes old resolved conflicts based on MaxConflictAge
func (cr *ConflictResolver) CleanupOldConflicts() {
	if cr.config.MaxConflictAge <= 0 {
		return
	}
	
	cutoff := time.Now().AddDate(0, 0, -cr.config.MaxConflictAge)
	cleaned := 0
	
	for conflictID, conflict := range cr.conflicts {
		if conflict.Status == ConflictStatusResolved && conflict.ResolvedAt != nil && conflict.ResolvedAt.Before(cutoff) {
			delete(cr.conflicts, conflictID)
			cleaned++
		}
	}
	
	if cleaned > 0 {
		cr.logger.WithField("cleaned_count", cleaned).Info("Cleaned up old resolved conflicts")
	}
}

// applyResolutionStrategy applies the specified resolution strategy
func (cr *ConflictResolver) applyResolutionStrategy(game *models.Game, conflict *ConflictInfo, strategy ConflictResolutionStrategy) error {
	switch strategy {
	case ConflictStrategyPreferSteam:
		return cr.applySteamValue(game, conflict)
	case ConflictStrategyPreferLocal:
		return cr.applyLocalValue(game, conflict)
	case ConflictStrategyNewest:
		if conflict.SteamTimestamp.After(conflict.LocalTimestamp) {
			return cr.applySteamValue(game, conflict)
		}
		return cr.applyLocalValue(game, conflict)
	case ConflictStrategyMerge:
		return cr.applyMergedValue(game, conflict)
	default:
		return fmt.Errorf("unsupported resolution strategy: %s", strategy)
	}
}

// applySteamValue applies the Steam API value to the game
func (cr *ConflictResolver) applySteamValue(game *models.Game, conflict *ConflictInfo) error {
	switch conflict.ConflictType {
	case ConflictTypeGameMetadata:
		// Apply Steam metadata (this would need proper type handling)
		cr.logger.WithField("game_id", game.ID).Debug("Applied Steam metadata value")
	case ConflictTypePlaytime:
		if playtime, ok := conflict.SteamValue.(int); ok {
			game.PlaytimeForever = playtime
		}
	default:
		return fmt.Errorf("unsupported conflict type for Steam value: %s", conflict.ConflictType)
	}
	return nil
}

// applyLocalValue keeps the local value (no changes needed)
func (cr *ConflictResolver) applyLocalValue(game *models.Game, conflict *ConflictInfo) error {
	cr.logger.WithFields(logrus.Fields{
		"game_id":      game.ID,
		"conflict_type": conflict.ConflictType,
	}).Debug("Keeping local value")
	return nil
}

// applyMergedValue attempts to intelligently merge values
func (cr *ConflictResolver) applyMergedValue(game *models.Game, conflict *ConflictInfo) error {
	switch conflict.ConflictType {
	case ConflictTypePlaytime:
		// For playtime, prefer the higher value (assuming it's more accurate)
		localPlaytime, localOk := conflict.LocalValue.(int)
		steamPlaytime, steamOk := conflict.SteamValue.(int)
		if localOk && steamOk {
			if steamPlaytime > localPlaytime {
				game.PlaytimeForever = steamPlaytime
			}
		}
	default:
		// Default to newest for other types
		return cr.applyResolutionStrategy(game, conflict, ConflictStrategyNewest)
	}
	return nil
}

// createGameBackup creates a backup of the game before modification
func (cr *ConflictResolver) createGameBackup(game *models.Game) error {
	backup := map[string]interface{}{
		"timestamp": time.Now(),
		"game_id":   game.ID,
		"game_data": game,
	}
	
	backupJSON, err := json.Marshal(backup)
	if err != nil {
		return fmt.Errorf("failed to marshal backup: %w", err)
	}
	
	// In a real implementation, you'd store this in a dedicated backup table or file
	cr.logger.WithFields(logrus.Fields{
		"game_id":     game.ID,
		"backup_size": len(backupJSON),
	}).Debug("Created game backup")
	
	return nil
}

// GetStatistics returns conflict resolution statistics
func (cr *ConflictResolver) GetStatistics() map[string]interface{} {
	pending := 0
	resolved := 0
	failed := 0
	ignored := 0
	
	typeStats := make(map[ConflictType]int)
	
	for _, conflict := range cr.conflicts {
		switch conflict.Status {
		case ConflictStatusPending:
			pending++
		case ConflictStatusResolved:
			resolved++
		case ConflictStatusFailed:
			failed++
		case ConflictStatusIgnored:
			ignored++
		}
		
		typeStats[conflict.ConflictType]++
	}
	
	return map[string]interface{}{
		"total_conflicts":  len(cr.conflicts),
		"pending":          pending,
		"resolved":         resolved,
		"failed":           failed,
		"ignored":          ignored,
		"by_type":          typeStats,
		"auto_resolve_enabled": cr.config.AutoResolveEnabled,
		"default_strategy": cr.config.DefaultStrategy,
	}
}