package config

import (
	"fmt"
	"strings"
	"time"

	"github.com/spf13/viper"
	"github.com/joho/godotenv"

	"github.com/jimsantora/steam-librarian/internal/storage"
)

// Config holds all configuration for the Steam Librarian application
type Config struct {
	Server   ServerConfig          `mapstructure:"server"`
	Database storage.DatabaseConfig `mapstructure:"database"`
	Steam    SteamConfig           `mapstructure:"steam"`
	Logging  LoggingConfig         `mapstructure:"logging"`
	MCP      MCPConfig             `mapstructure:"mcp"`
}

// ServerConfig holds web server configuration
type ServerConfig struct {
	Address     string        `mapstructure:"address"`
	Port        int           `mapstructure:"port"`
	Environment string        `mapstructure:"environment"` // "development", "production"
	ReadTimeout time.Duration `mapstructure:"read_timeout"`
	WriteTimeout time.Duration `mapstructure:"write_timeout"`
	IdleTimeout time.Duration `mapstructure:"idle_timeout"`
}

// SteamConfig holds Steam API configuration
type SteamConfig struct {
	APIKey           string        `mapstructure:"api_key"`
	RateLimit        int           `mapstructure:"rate_limit"`        // Requests per minute
	RequestTimeout   time.Duration `mapstructure:"request_timeout"`
	MaxRetries       int           `mapstructure:"max_retries"`
	SyncInterval     time.Duration `mapstructure:"sync_interval"`     // How often to sync libraries
	BatchSize        int           `mapstructure:"batch_size"`        // Games to process in one batch
	EnableCaching    bool          `mapstructure:"enable_caching"`
	CacheExpiration  time.Duration `mapstructure:"cache_expiration"`
}

// LoggingConfig holds logging configuration
type LoggingConfig struct {
	Level      string `mapstructure:"level"`       // "debug", "info", "warn", "error"
	Format     string `mapstructure:"format"`      // "json", "text"
	Output     string `mapstructure:"output"`      // "stdout", "stderr", file path
	MaxSize    int    `mapstructure:"max_size"`    // Max size in MB before rotation
	MaxBackups int    `mapstructure:"max_backups"` // Max number of old log files
	MaxAge     int    `mapstructure:"max_age"`     // Max age in days to retain logs
	Compress   bool   `mapstructure:"compress"`    // Compress rotated logs
}

// MCPConfig holds MCP server configuration
type MCPConfig struct {
	Enabled         bool          `mapstructure:"enabled"`
	ServerName      string        `mapstructure:"server_name"`
	ServerVersion   string        `mapstructure:"server_version"`
	ProtocolVersion string        `mapstructure:"protocol_version"`
	Timeout         time.Duration `mapstructure:"timeout"`
	BufferSize      int           `mapstructure:"buffer_size"`
}

// LoadConfig loads configuration from various sources
func LoadConfig() (*Config, error) {
	// Load .env file if it exists (for local development)
	_ = godotenv.Load()

	// Configure Viper
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./configs")
	viper.AddConfigPath(".")

	// Set default values
	setDefaults()

	// Enable automatic env variable reading
	viper.AutomaticEnv()
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	// Read config file
	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); ok {
			// Config file not found; use defaults and environment variables
		} else {
			return nil, fmt.Errorf("error reading config file: %w", err)
		}
	}

	// Unmarshal config
	var config Config
	if err := viper.Unmarshal(&config); err != nil {
		return nil, fmt.Errorf("error unmarshaling config: %w", err)
	}

	// Validate configuration
	if err := validateConfig(&config); err != nil {
		return nil, fmt.Errorf("configuration validation failed: %w", err)
	}

	// Build full server address
	if config.Server.Port > 0 {
		config.Server.Address = fmt.Sprintf("%s:%d", extractHost(config.Server.Address), config.Server.Port)
	}

	return &config, nil
}

// setDefaults sets default configuration values
func setDefaults() {
	// Server defaults
	viper.SetDefault("server.address", "localhost:8080")
	viper.SetDefault("server.port", 8080)
	viper.SetDefault("server.environment", "development")
	viper.SetDefault("server.read_timeout", "30s")
	viper.SetDefault("server.write_timeout", "30s")
	viper.SetDefault("server.idle_timeout", "60s")

	// Database defaults
	viper.SetDefault("database.type", "sqlite")
	viper.SetDefault("database.file_path", "steam_librarian.db")
	viper.SetDefault("database.host", "localhost")
	viper.SetDefault("database.port", 5432)
	viper.SetDefault("database.database", "steam_librarian")
	viper.SetDefault("database.ssl_mode", "disable")
	viper.SetDefault("database.timezone", "UTC")
	viper.SetDefault("database.max_open_conns", 25)
	viper.SetDefault("database.max_idle_conns", 5)
	viper.SetDefault("database.conn_max_lifetime", "1h")

	// Steam API defaults
	viper.SetDefault("steam.rate_limit", 200)              // Steam allows 100,000 calls per day
	viper.SetDefault("steam.request_timeout", "30s")
	viper.SetDefault("steam.max_retries", 3)
	viper.SetDefault("steam.sync_interval", "24h")         // Sync once per day
	viper.SetDefault("steam.batch_size", 10)               // Process 10 games at a time
	viper.SetDefault("steam.enable_caching", true)
	viper.SetDefault("steam.cache_expiration", "6h")

	// Logging defaults
	viper.SetDefault("logging.level", "info")
	viper.SetDefault("logging.format", "json")
	viper.SetDefault("logging.output", "stdout")
	viper.SetDefault("logging.max_size", 100)    // 100 MB
	viper.SetDefault("logging.max_backups", 3)
	viper.SetDefault("logging.max_age", 28)      // 28 days
	viper.SetDefault("logging.compress", true)

	// MCP defaults
	viper.SetDefault("mcp.enabled", true)
	viper.SetDefault("mcp.server_name", "steam-librarian")
	viper.SetDefault("mcp.server_version", "0.1.0")
	viper.SetDefault("mcp.protocol_version", "2024-11-05")
	viper.SetDefault("mcp.timeout", "30s")
	viper.SetDefault("mcp.buffer_size", 4096)
}

// validateConfig validates the loaded configuration
func validateConfig(config *Config) error {
	// Validate server configuration
	if config.Server.Port <= 0 || config.Server.Port > 65535 {
		return fmt.Errorf("invalid server port: %d", config.Server.Port)
	}

	if config.Server.Environment != "development" && config.Server.Environment != "production" {
		return fmt.Errorf("invalid environment: %s (must be 'development' or 'production')", config.Server.Environment)
	}

	// Validate database configuration
	validDBTypes := []string{"sqlite", "postgres", "mysql"}
	isValidDBType := false
	for _, validType := range validDBTypes {
		if config.Database.Type == validType {
			isValidDBType = true
			break
		}
	}
	if !isValidDBType {
		return fmt.Errorf("invalid database type: %s (must be one of: %v)", config.Database.Type, validDBTypes)
	}

	// Validate Steam API configuration
	if config.Steam.APIKey == "" {
		return fmt.Errorf("Steam API key is required")
	}

	// Validate logging configuration
	validLogLevels := []string{"debug", "info", "warn", "error"}
	isValidLogLevel := false
	for _, validLevel := range validLogLevels {
		if config.Logging.Level == validLevel {
			isValidLogLevel = true
			break
		}
	}
	if !isValidLogLevel {
		return fmt.Errorf("invalid log level: %s (must be one of: %v)", config.Logging.Level, validLogLevels)
	}

	validLogFormats := []string{"json", "text"}
	isValidLogFormat := false
	for _, validFormat := range validLogFormats {
		if config.Logging.Format == validFormat {
			isValidLogFormat = true
			break
		}
	}
	if !isValidLogFormat {
		return fmt.Errorf("invalid log format: %s (must be one of: %v)", config.Logging.Format, validLogFormats)
	}

	return nil
}

// extractHost extracts the host part from an address string
func extractHost(address string) string {
	if strings.Contains(address, ":") {
		parts := strings.Split(address, ":")
		return parts[0]
	}
	return address
}

// GetDatabaseConfig returns the database configuration in the format expected by storage package
func (c *Config) GetDatabaseConfig() storage.DatabaseConfig {
	return c.Database
}

// IsDevelopment returns true if running in development mode
func (c *Config) IsDevelopment() bool {
	return c.Server.Environment == "development"
}

// IsProduction returns true if running in production mode
func (c *Config) IsProduction() bool {
	return c.Server.Environment == "production"
}