package web

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"

	"github.com/jimsantora/steam-librarian/internal/models"
	"github.com/jimsantora/steam-librarian/internal/services"
	"github.com/jimsantora/steam-librarian/internal/storage"
	"github.com/jimsantora/steam-librarian/internal/steam"
)

// Handlers contains all HTTP handlers for the web interface
type Handlers struct {
	repo         *storage.Repository
	steamAPI     *steam.APIService
	syncService  *services.LibrarySyncService
	syncScheduler *services.SyncScheduler
	logger       *logrus.Logger
}

// NewHandlers creates a new handlers instance
func NewHandlers(repo *storage.Repository, steamAPI *steam.APIService, syncService *services.LibrarySyncService, syncScheduler *services.SyncScheduler, logger *logrus.Logger) *Handlers {
	return &Handlers{
		repo:         repo,
		steamAPI:     steamAPI,
		syncService:  syncService,
		syncScheduler: syncScheduler,
		logger:       logger,
	}
}

// HealthCheck returns the health status of the application
func (h *Handlers) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":    "healthy",
		"timestamp": "2024-01-01T00:00:00Z", // TODO: Use actual timestamp
		"version":   "v0.1.0",               // TODO: Get from build info
	})
}

// Library Handlers

// GetLibraries returns all libraries
func (h *Handlers) GetLibraries(c *gin.Context) {
	h.logger.Debug("Getting all libraries")
	
	libraries, err := h.repo.GetAllLibraries()
	if err != nil {
		h.logger.WithError(err).Error("Failed to get libraries")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get libraries"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"libraries": libraries})
}

// CreateLibrary creates a new library
func (h *Handlers) CreateLibrary(c *gin.Context) {
	h.logger.Debug("Creating new library")
	
	var library models.Library
	if err := c.ShouldBindJSON(&library); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.repo.CreateLibrary(&library); err != nil {
		h.logger.WithError(err).Error("Failed to create library")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create library"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"library": library})
}

// GetLibrary returns a specific library by ID
func (h *Handlers) GetLibrary(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid library ID"})
		return
	}

	library, err := h.repo.GetLibraryByID(uint(id))
	if err != nil {
		h.logger.WithError(err).Error("Failed to get library")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get library"})
		return
	}

	if library == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Library not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"library": library})
}

// UpdateLibrary updates an existing library
func (h *Handlers) UpdateLibrary(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid library ID"})
		return
	}

	var library models.Library
	if err := c.ShouldBindJSON(&library); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	library.ID = uint(id)
	if err := h.repo.UpdateLibrary(&library); err != nil {
		h.logger.WithError(err).Error("Failed to update library")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update library"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"library": library})
}

// DeleteLibrary deletes a library
func (h *Handlers) DeleteLibrary(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid library ID"})
		return
	}

	if err := h.repo.DeleteLibrary(uint(id)); err != nil {
		h.logger.WithError(err).Error("Failed to delete library")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete library"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Library deleted successfully"})
}

// SyncLibrary triggers a sync for a specific library
func (h *Handlers) SyncLibrary(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid library ID"})
		return
	}

	// Get library to find Steam User ID
	library, err := h.repo.GetLibraryByID(uint(id))
	if err != nil {
		h.logger.WithError(err).Error("Failed to get library")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get library"})
		return
	}

	if library == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Library not found"})
		return
	}

	// Get sync type from query parameter (default to incremental)
	syncType := c.DefaultQuery("type", "incremental")
	var syncTypeEnum services.SyncType
	switch syncType {
	case "full":
		syncTypeEnum = services.SyncTypeFull
	case "incremental":
		syncTypeEnum = services.SyncTypeIncremental
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid sync type. Use 'full' or 'incremental'"})
		return
	}

	// Start sync
	progress, err := h.syncService.SyncLibraryAsync(library.SteamUserID, syncTypeEnum)
	if err != nil {
		h.logger.WithError(err).Error("Failed to start library sync")
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	h.logger.WithFields(logrus.Fields{
		"library_id": id,
		"steam_user_id": library.SteamUserID,
		"sync_type": syncType,
	}).Info("Library sync started")

	c.JSON(http.StatusAccepted, gin.H{
		"message": "Library sync started",
		"progress": progress,
	})
}

// Game Handlers

// GetGames returns all games
func (h *Handlers) GetGames(c *gin.Context) {
	h.logger.Debug("Getting all games")
	
	games, err := h.repo.GetAllGames()
	if err != nil {
		h.logger.WithError(err).Error("Failed to get games")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get games"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"games": games})
}

// GetGame returns a specific game by ID
func (h *Handlers) GetGame(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid game ID"})
		return
	}

	game, err := h.repo.GetGameByID(uint(id))
	if err != nil {
		h.logger.WithError(err).Error("Failed to get game")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get game"})
		return
	}

	if game == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Game not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"game": game})
}

// UpdateGame updates an existing game
func (h *Handlers) UpdateGame(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid game ID"})
		return
	}

	var game models.Game
	if err := c.ShouldBindJSON(&game); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	game.ID = uint(id)
	if err := h.repo.UpdateGame(&game); err != nil {
		h.logger.WithError(err).Error("Failed to update game")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update game"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"game": game})
}

// DeleteGame deletes a game
func (h *Handlers) DeleteGame(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid game ID"})
		return
	}

	if err := h.repo.DeleteGame(uint(id)); err != nil {
		h.logger.WithError(err).Error("Failed to delete game")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete game"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Game deleted successfully"})
}

// SyncGame triggers a sync for a specific game
func (h *Handlers) SyncGame(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid game ID"})
		return
	}

	// TODO: Implement individual game sync logic
	h.logger.WithField("game_id", id).Info("Game sync requested - not yet implemented")
	c.JSON(http.StatusAccepted, gin.H{"message": "Game sync started"})
}

// Sync Status Handlers

// GetSyncProgress returns the current sync progress for a library
func (h *Handlers) GetSyncProgress(c *gin.Context) {
	steamUserID := c.Query("steam_user_id")
	if steamUserID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "steam_user_id query parameter is required"})
		return
	}

	progress, exists := h.syncService.GetSyncProgress(steamUserID)
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "No active sync found for this user"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"progress": progress})
}

// GetSyncHistory returns the sync history for a library
func (h *Handlers) GetSyncHistory(c *gin.Context) {
	steamUserID := c.Query("steam_user_id")
	if steamUserID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "steam_user_id query parameter is required"})
		return
	}

	history := h.syncService.GetSyncHistory(steamUserID)
	c.JSON(http.StatusOK, gin.H{"history": history})
}

// CancelSync cancels an active sync operation
func (h *Handlers) CancelSync(c *gin.Context) {
	steamUserID := c.Query("steam_user_id")
	if steamUserID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "steam_user_id query parameter is required"})
		return
	}

	err := h.syncService.CancelSync(steamUserID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Sync cancelled successfully"})
}

// GetActiveSyncs returns all currently active sync operations
func (h *Handlers) GetActiveSyncs(c *gin.Context) {
	activeSyncs := h.syncService.GetActiveSyncs()
	c.JSON(http.StatusOK, gin.H{"active_syncs": activeSyncs})
}

// Scheduler Handlers

// GetSchedulerStatus returns the current scheduler status and statistics
func (h *Handlers) GetSchedulerStatus(c *gin.Context) {
	status := h.syncScheduler.GetStatus()
	c.JSON(http.StatusOK, gin.H{"scheduler": status})
}

// UpdateSchedulerConfig updates the scheduler configuration
func (h *Handlers) UpdateSchedulerConfig(c *gin.Context) {
	var config services.SchedulerConfig
	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.syncScheduler.UpdateConfig(&config); err != nil {
		h.logger.WithError(err).Error("Failed to update scheduler config")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update scheduler config"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Scheduler configuration updated successfully",
		"config":  config,
	})
}

// Conflict Resolution Handlers

// GetConflicts returns conflicts based on optional filters
func (h *Handlers) GetConflicts(c *gin.Context) {
	conflictResolver := h.syncService.GetConflictResolver()
	
	statusParam := c.Query("status")
	typeParam := c.Query("type")
	
	var status services.ConflictStatus
	var conflictType services.ConflictType
	
	if statusParam != "" {
		status = services.ConflictStatus(statusParam)
	}
	if typeParam != "" {
		conflictType = services.ConflictType(typeParam)
	}
	
	conflicts := conflictResolver.GetConflicts(status, conflictType)
	
	c.JSON(http.StatusOK, gin.H{
		"conflicts": conflicts,
		"count":     len(conflicts),
		"filters": gin.H{
			"status": statusParam,
			"type":   typeParam,
		},
	})
}

// GetConflict returns a specific conflict by ID
func (h *Handlers) GetConflict(c *gin.Context) {
	conflictID := c.Param("id")
	if conflictID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Conflict ID is required"})
		return
	}
	
	conflictResolver := h.syncService.GetConflictResolver()
	conflict, exists := conflictResolver.GetConflictByID(conflictID)
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "Conflict not found"})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"conflict": conflict})
}

// ResolveConflict resolves a specific conflict
func (h *Handlers) ResolveConflict(c *gin.Context) {
	conflictID := c.Param("id")
	if conflictID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Conflict ID is required"})
		return
	}
	
	var request struct {
		Strategy   services.ConflictResolutionStrategy `json:"strategy"`
		ResolvedBy string                              `json:"resolved_by"`
	}
	
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	if request.ResolvedBy == "" {
		request.ResolvedBy = "web-user" // Default value
	}
	
	conflictResolver := h.syncService.GetConflictResolver()
	if err := conflictResolver.ResolveConflict(conflictID, request.Strategy, request.ResolvedBy); err != nil {
		h.logger.WithError(err).Error("Failed to resolve conflict")
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"message":     "Conflict resolved successfully",
		"conflict_id": conflictID,
		"strategy":    request.Strategy,
		"resolved_by": request.ResolvedBy,
	})
}

// AutoResolveConflicts triggers automatic conflict resolution
func (h *Handlers) AutoResolveConflicts(c *gin.Context) {
	conflictResolver := h.syncService.GetConflictResolver()
	
	if err := conflictResolver.AutoResolveConflicts(); err != nil {
		h.logger.WithError(err).Error("Auto-resolution failed")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Auto-resolution failed"})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"message": "Auto-resolution completed"})
}

// GetConflictStatistics returns conflict resolution statistics
func (h *Handlers) GetConflictStatistics(c *gin.Context) {
	conflictResolver := h.syncService.GetConflictResolver()
	stats := conflictResolver.GetStatistics()
	
	c.JSON(http.StatusOK, gin.H{"statistics": stats})
}

// Search Handlers

// SearchGames searches for games
func (h *Handlers) SearchGames(c *gin.Context) {
	query := c.Query("q")
	if query == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Search query is required"})
		return
	}

	// TODO: Implement game search logic
	h.logger.WithField("query", query).Info("Game search requested - not yet implemented")
	c.JSON(http.StatusOK, gin.H{"games": []models.Game{}, "query": query})
}

// SearchLibraries searches for libraries
func (h *Handlers) SearchLibraries(c *gin.Context) {
	query := c.Query("q")
	if query == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Search query is required"})
		return
	}

	// TODO: Implement library search logic
	h.logger.WithField("query", query).Info("Library search requested - not yet implemented")
	c.JSON(http.StatusOK, gin.H{"libraries": []models.Library{}, "query": query})
}

// Statistics Handlers

// GetLibraryStats returns statistics for a specific library
func (h *Handlers) GetLibraryStats(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid library ID"})
		return
	}

	// TODO: Implement library statistics calculation
	h.logger.WithField("library_id", id).Info("Library stats requested - not yet implemented")
	c.JSON(http.StatusOK, gin.H{
		"library_id":     id,
		"total_games":    0,
		"total_playtime": 0,
		"stats":          "Not yet implemented",
	})
}

// GetGlobalStats returns global statistics
func (h *Handlers) GetGlobalStats(c *gin.Context) {
	// TODO: Implement global statistics calculation
	h.logger.Info("Global stats requested - not yet implemented")
	c.JSON(http.StatusOK, gin.H{
		"total_libraries": 0,
		"total_games":     0,
		"stats":           "Not yet implemented",
	})
}

// Web UI Handlers (placeholder implementations)

// IndexPage renders the home page
func (h *Handlers) IndexPage(c *gin.Context) {
	c.HTML(http.StatusOK, "index.html", gin.H{"title": "Steam Librarian"})
}

// LibrariesPage renders the libraries page
func (h *Handlers) LibrariesPage(c *gin.Context) {
	c.HTML(http.StatusOK, "libraries.html", gin.H{"title": "Libraries"})
}

// LibraryPage renders a specific library page
func (h *Handlers) LibraryPage(c *gin.Context) {
	id := c.Param("id")
	c.HTML(http.StatusOK, "library.html", gin.H{"title": "Library", "id": id})
}

// GamesPage renders the games page
func (h *Handlers) GamesPage(c *gin.Context) {
	c.HTML(http.StatusOK, "games.html", gin.H{"title": "Games"})
}

// GamePage renders a specific game page
func (h *Handlers) GamePage(c *gin.Context) {
	id := c.Param("id")
	c.HTML(http.StatusOK, "game.html", gin.H{"title": "Game", "id": id})
}

// SettingsPage renders the settings page
func (h *Handlers) SettingsPage(c *gin.Context) {
	c.HTML(http.StatusOK, "settings.html", gin.H{"title": "Settings"})
}

// Debug Handlers

// GetDatabaseStats returns database statistics
func (h *Handlers) GetDatabaseStats(c *gin.Context) {
	// TODO: Implement database statistics
	c.JSON(http.StatusOK, gin.H{"stats": "Database stats not yet implemented"})
}

// GetConfig returns current configuration (sanitized)
func (h *Handlers) GetConfig(c *gin.Context) {
	// TODO: Implement configuration display (without sensitive data)
	c.JSON(http.StatusOK, gin.H{"config": "Configuration display not yet implemented"})
}