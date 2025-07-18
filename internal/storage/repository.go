package storage

import (
	"fmt"
	"time"

	"gorm.io/gorm"
	"github.com/jimsantora/steam-librarian/internal/models"
)

// Repository provides database operations using the repository pattern
// This abstracts GORM operations and provides a clean interface for data access
type Repository struct {
	db *Database
}

// NewRepository creates a new repository instance
func NewRepository(db *Database) *Repository {
	return &Repository{db: db}
}

// GameRepository interface defines game-related database operations
type GameRepository interface {
	CreateGame(game *models.Game) error
	GetGameByID(id uint) (*models.Game, error)
	GetGameBySteamAppID(steamAppID string) (*models.Game, error)
	UpdateGame(game *models.Game) error
	DeleteGame(id uint) error
	GetAllGames() ([]models.Game, error)
	GetGamesByUserID(steamUserID string) ([]models.Game, error)
	GetGamesNeedingSync(maxAge time.Duration) ([]models.Game, error)
}

// LibraryRepository interface defines library-related database operations
type LibraryRepository interface {
	CreateLibrary(library *models.Library) error
	GetLibraryByID(id uint) (*models.Library, error)
	GetLibraryByUserID(steamUserID string) (*models.Library, error)
	UpdateLibrary(library *models.Library) error
	DeleteLibrary(id uint) error
	GetAllLibraries() ([]models.Library, error)
	GetLibrariesNeedingSync(maxAge time.Duration) ([]models.Library, error)
}

// Game Repository Methods

// CreateGame creates a new game record
func (r *Repository) CreateGame(game *models.Game) error {
	if err := r.db.Create(game).Error; err != nil {
		return fmt.Errorf("failed to create game: %w", err)
	}
	return nil
}

// GetGameByID retrieves a game by its ID
func (r *Repository) GetGameByID(id uint) (*models.Game, error) {
	var game models.Game
	if err := r.db.First(&game, id).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, nil // Return nil instead of error for not found
		}
		return nil, fmt.Errorf("failed to get game by ID: %w", err)
	}
	return &game, nil
}

// GetGameBySteamAppID retrieves a game by its Steam App ID
func (r *Repository) GetGameBySteamAppID(steamAppID string) (*models.Game, error) {
	var game models.Game
	if err := r.db.Where("steam_app_id = ?", steamAppID).First(&game).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, nil // Return nil instead of error for not found
		}
		return nil, fmt.Errorf("failed to get game by Steam App ID: %w", err)
	}
	return &game, nil
}

// UpdateGame updates an existing game record
func (r *Repository) UpdateGame(game *models.Game) error {
	if err := r.db.Save(game).Error; err != nil {
		return fmt.Errorf("failed to update game: %w", err)
	}
	return nil
}

// DeleteGame soft deletes a game record
func (r *Repository) DeleteGame(id uint) error {
	if err := r.db.Delete(&models.Game{}, id).Error; err != nil {
		return fmt.Errorf("failed to delete game: %w", err)
	}
	return nil
}

// GetAllGames retrieves all games
func (r *Repository) GetAllGames() ([]models.Game, error) {
	var games []models.Game
	if err := r.db.Find(&games).Error; err != nil {
		return nil, fmt.Errorf("failed to get all games: %w", err)
	}
	return games, nil
}

// GetGamesByUserID retrieves all games for a specific Steam user
func (r *Repository) GetGamesByUserID(steamUserID string) ([]models.Game, error) {
	var games []models.Game
	// TODO: This needs to be implemented with proper relationship between Library and Games
	// For now, we'll use a placeholder query structure
	if err := r.db.Where("steam_user_id = ?", steamUserID).Find(&games).Error; err != nil {
		return nil, fmt.Errorf("failed to get games by user ID: %w", err)
	}
	return games, nil
}

// GetGamesNeedingSync retrieves games that haven't been synced recently
func (r *Repository) GetGamesNeedingSync(maxAge time.Duration) ([]models.Game, error) {
	var games []models.Game
	cutoff := time.Now().Add(-maxAge)
	if err := r.db.Where("last_steam_api_sync < ? OR last_steam_api_sync IS NULL", cutoff).Find(&games).Error; err != nil {
		return nil, fmt.Errorf("failed to get games needing sync: %w", err)
	}
	return games, nil
}

// Library Repository Methods

// CreateLibrary creates a new library record
func (r *Repository) CreateLibrary(library *models.Library) error {
	if err := r.db.Create(library).Error; err != nil {
		return fmt.Errorf("failed to create library: %w", err)
	}
	return nil
}

// GetLibraryByID retrieves a library by its ID
func (r *Repository) GetLibraryByID(id uint) (*models.Library, error) {
	var library models.Library
	if err := r.db.Preload("Games").First(&library, id).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, nil // Return nil instead of error for not found
		}
		return nil, fmt.Errorf("failed to get library by ID: %w", err)
	}
	return &library, nil
}

// GetLibraryByUserID retrieves a library by Steam user ID
func (r *Repository) GetLibraryByUserID(steamUserID string) (*models.Library, error) {
	var library models.Library
	if err := r.db.Where("steam_user_id = ?", steamUserID).Preload("Games").First(&library).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, nil // Return nil instead of error for not found
		}
		return nil, fmt.Errorf("failed to get library by user ID: %w", err)
	}
	return &library, nil
}

// UpdateLibrary updates an existing library record
func (r *Repository) UpdateLibrary(library *models.Library) error {
	if err := r.db.Save(library).Error; err != nil {
		return fmt.Errorf("failed to update library: %w", err)
	}
	return nil
}

// DeleteLibrary soft deletes a library record
func (r *Repository) DeleteLibrary(id uint) error {
	if err := r.db.Delete(&models.Library{}, id).Error; err != nil {
		return fmt.Errorf("failed to delete library: %w", err)
	}
	return nil
}

// GetAllLibraries retrieves all libraries
func (r *Repository) GetAllLibraries() ([]models.Library, error) {
	var libraries []models.Library
	if err := r.db.Preload("Games").Find(&libraries).Error; err != nil {
		return nil, fmt.Errorf("failed to get all libraries: %w", err)
	}
	return libraries, nil
}

// GetLibrariesNeedingSync retrieves libraries that haven't been synced recently
func (r *Repository) GetLibrariesNeedingSync(maxAge time.Duration) ([]models.Library, error) {
	var libraries []models.Library
	cutoff := time.Now().Add(-maxAge)
	if err := r.db.Where("last_library_sync < ? OR last_library_sync IS NULL", cutoff).Find(&libraries).Error; err != nil {
		return nil, fmt.Errorf("failed to get libraries needing sync: %w", err)
	}
	return libraries, nil
}

// Transaction methods for complex operations

// WithTransaction executes a function within a database transaction
func (r *Repository) WithTransaction(fn func(*Repository) error) error {
	return r.db.Transaction(func(tx *gorm.DB) error {
		txRepo := &Repository{db: &Database{DB: tx, config: r.db.config}}
		return fn(txRepo)
	})
}