package web

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"

	"github.com/jimsantora/steam-librarian/internal/models"
	"github.com/jimsantora/steam-librarian/internal/storage"
	"github.com/jimsantora/steam-librarian/internal/steam"
)

// Handlers contains all HTTP handlers for the web interface
type Handlers struct {
	repo     *storage.Repository
	steamAPI *steam.APIService
	logger   *logrus.Logger
}

// NewHandlers creates a new handlers instance
func NewHandlers(repo *storage.Repository, steamAPI *steam.APIService, logger *logrus.Logger) *Handlers {
	return &Handlers{
		repo:     repo,
		steamAPI: steamAPI,
		logger:   logger,
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

	// TODO: Implement library sync logic
	h.logger.WithField("library_id", id).Info("Library sync requested - not yet implemented")
	c.JSON(http.StatusAccepted, gin.H{"message": "Library sync started"})
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

	// TODO: Implement game sync logic
	h.logger.WithField("game_id", id).Info("Game sync requested - not yet implemented")
	c.JSON(http.StatusAccepted, gin.H{"message": "Game sync started"})
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