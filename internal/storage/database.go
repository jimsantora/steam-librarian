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
	
	log.Println("Database migrations completed successfully")
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