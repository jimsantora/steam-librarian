package storage

import (
	"fmt"
	"log"
	"time"

	"gorm.io/driver/mysql"
	"gorm.io/driver/postgres"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"github.com/jimsantora/steam-librarian/internal/models"
)

// DatabaseConfig holds database connection configuration
type DatabaseConfig struct {
	Type     string // "sqlite", "postgres", "mysql"
	Host     string
	Port     int
	Username string
	Password string
	Database string
	SSLMode  string // For PostgreSQL
	Timezone string // For MySQL
	
	// SQLite specific
	FilePath string
	
	// Connection pool settings
	MaxOpenConns    int
	MaxIdleConns    int
	ConnMaxLifetime time.Duration
}

// Database wraps GORM DB instance with additional functionality
type Database struct {
	*gorm.DB
	config DatabaseConfig
}

// NewDatabase creates a new database connection based on configuration
func NewDatabase(config DatabaseConfig) (*Database, error) {
	var gormDB *gorm.DB
	var err error

	// Configure GORM logger
	gormConfig := &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
		NamingStrategy: nil, // Use default naming strategy
	}

	// Connect based on database type
	switch config.Type {
	case "sqlite":
		dsn := config.FilePath
		if dsn == "" {
			dsn = "steam_librarian.db" // Default SQLite file
		}
		gormDB, err = gorm.Open(sqlite.Open(dsn), gormConfig)
		
	case "postgres":
		dsn := fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%d sslmode=%s TimeZone=UTC",
			config.Host, config.Username, config.Password, config.Database, config.Port, config.SSLMode)
		gormDB, err = gorm.Open(postgres.Open(dsn), gormConfig)
		
	case "mysql":
		dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
			config.Username, config.Password, config.Host, config.Port, config.Database)
		if config.Timezone != "" {
			dsn += "&time_zone=" + config.Timezone
		}
		gormDB, err = gorm.Open(mysql.Open(dsn), gormConfig)
		
	default:
		return nil, fmt.Errorf("unsupported database type: %s", config.Type)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to connect to %s database: %w", config.Type, err)
	}

	// Configure connection pool
	sqlDB, err := gormDB.DB()
	if err != nil {
		return nil, fmt.Errorf("failed to get underlying sql.DB: %w", err)
	}

	// Set connection pool settings
	if config.MaxOpenConns > 0 {
		sqlDB.SetMaxOpenConns(config.MaxOpenConns)
	} else {
		sqlDB.SetMaxOpenConns(25) // Default
	}

	if config.MaxIdleConns > 0 {
		sqlDB.SetMaxIdleConns(config.MaxIdleConns)
	} else {
		sqlDB.SetMaxIdleConns(5) // Default
	}

	if config.ConnMaxLifetime > 0 {
		sqlDB.SetConnMaxLifetime(config.ConnMaxLifetime)
	} else {
		sqlDB.SetConnMaxLifetime(time.Hour) // Default
	}

	// Test the connection
	if err := sqlDB.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	db := &Database{
		DB:     gormDB,
		config: config,
	}

	log.Printf("Successfully connected to %s database", config.Type)
	return db, nil
}

// AutoMigrate runs database migrations for all models
func (db *Database) AutoMigrate() error {
	log.Println("Running database migrations...")
	
	err := db.DB.AutoMigrate(
		&models.Library{},
		&models.Game{},
	)
	
	if err != nil {
		return fmt.Errorf("failed to run auto migration: %w", err)
	}
	
	// Add indexes for enhanced game metadata (Phase 1.3)
	if err := db.createGameIndexes(); err != nil {
		log.Printf("Warning: Failed to create game indexes: %v", err)
		// Don't fail the migration if index creation fails
	}
	
	log.Println("Database migrations completed successfully")
	return nil
}

// createGameIndexes creates database indexes for improved query performance
func (db *Database) createGameIndexes() error {
	log.Println("Creating database indexes for enhanced game metadata...")
	
	// Index for Metacritic scores (for sorting by rating)
	if err := db.DB.Exec("CREATE INDEX IF NOT EXISTS idx_games_metacritic_score ON games(metacritic_score)").Error; err != nil {
		return fmt.Errorf("failed to create metacritic_score index: %w", err)
	}
	
	// Index for price information (for sorting by price)
	if err := db.DB.Exec("CREATE INDEX IF NOT EXISTS idx_games_current_price ON games(current_price)").Error; err != nil {
		return fmt.Errorf("failed to create current_price index: %w", err)
	}
	
	// Index for discount percentage (for finding games on sale)
	if err := db.DB.Exec("CREATE INDEX IF NOT EXISTS idx_games_discount_percent ON games(discount_percent)").Error; err != nil {
		return fmt.Errorf("failed to create discount_percent index: %w", err)
	}
	
	// Index for free games
	if err := db.DB.Exec("CREATE INDEX IF NOT EXISTS idx_games_is_free ON games(is_free)").Error; err != nil {
		return fmt.Errorf("failed to create is_free index: %w", err)
	}
	
	// Index for early access games
	if err := db.DB.Exec("CREATE INDEX IF NOT EXISTS idx_games_early_access ON games(early_access)").Error; err != nil {
		return fmt.Errorf("failed to create early_access index: %w", err)
	}
	
	// Index for achievements count
	if err := db.DB.Exec("CREATE INDEX IF NOT EXISTS idx_games_achievements ON games(achievements)").Error; err != nil {
		return fmt.Errorf("failed to create achievements index: %w", err)
	}
	
	// Composite index for Steam features (commonly queried together)
	if err := db.DB.Exec("CREATE INDEX IF NOT EXISTS idx_games_steam_features ON games(has_workshop, has_achievements, has_multiplayer)").Error; err != nil {
		return fmt.Errorf("failed to create steam_features index: %w", err)
	}
	
	log.Println("Database indexes created successfully")
	return nil
}

// MigrateGameMetadata performs a one-time migration to populate enhanced metadata
// This can be used to update existing games with new metadata fields
func (db *Database) MigrateGameMetadata() error {
	log.Println("Migrating existing game metadata...")
	
	// Set default values for new fields where they are null/empty
	updates := map[string]interface{}{
		"metacritic_score": 0,
		"achievements":     0,
		"is_free":          false,
		"coming_soon":      false,
		"early_access":     false,
		"current_price":    0.0,
		"original_price":   0.0,
		"discount_percent": 0,
		"price_currency":   "USD",
	}
	
	// Update games that don't have the new metadata fields set
	result := db.DB.Model(&models.Game{}).
		Where("metacritic_score IS NULL OR metacritic_score = 0").
		Updates(updates)
	
	if result.Error != nil {
		return fmt.Errorf("failed to migrate game metadata: %w", result.Error)
	}
	
	log.Printf("Migrated metadata for %d games", result.RowsAffected)
	return nil
}

// Close closes the database connection
func (db *Database) Close() error {
	sqlDB, err := db.DB.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}

// GetConfig returns the database configuration
func (db *Database) GetConfig() DatabaseConfig {
	return db.config
}

// HealthCheck performs a basic health check on the database
func (db *Database) HealthCheck() error {
	sqlDB, err := db.DB.DB()
	if err != nil {
		return fmt.Errorf("failed to get underlying sql.DB: %w", err)
	}
	
	if err := sqlDB.Ping(); err != nil {
		return fmt.Errorf("database ping failed: %w", err)
	}
	
	return nil
}

// GetStats returns database connection statistics
func (db *Database) GetStats() map[string]interface{} {
	sqlDB, err := db.DB.DB()
	if err != nil {
		return map[string]interface{}{
			"error": err.Error(),
		}
	}
	
	stats := sqlDB.Stats()
	return map[string]interface{}{
		"open_connections":     stats.OpenConnections,
		"in_use":              stats.InUse,
		"idle":                stats.Idle,
		"wait_count":          stats.WaitCount,
		"wait_duration":       stats.WaitDuration.String(),
		"max_idle_closed":     stats.MaxIdleClosed,
		"max_idle_time_closed": stats.MaxIdleTimeClosed,
		"max_lifetime_closed": stats.MaxLifetimeClosed,
	}
}