"""Configuration management for Steam Librarian MCP Server"""

import logging
import os
from typing import Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Server settings
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")

    # Database
    database_url: str = Field(default="sqlite:///steam_library.db", env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")

    # Caching
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    cache_ttl_search: int = Field(default=900, env="CACHE_TTL_SEARCH")  # 15 minutes
    cache_ttl_user: int = Field(default=1800, env="CACHE_TTL_USER")  # 30 minutes
    cache_ttl_recommendations: int = Field(default=3600, env="CACHE_TTL_RECOMMENDATIONS")  # 1 hour
    cache_ttl_stats: int = Field(default=1800, env="CACHE_TTL_STATS")  # 30 minutes
    enable_cache: bool = Field(default=True, env="ENABLE_CACHE")
    cache_backend: str = Field(default="memory", env="CACHE_BACKEND")  # memory, redis, disk
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")

    # Performance
    query_timeout: int = Field(default=5, env="QUERY_TIMEOUT")
    max_results: int = Field(default=100, env="MAX_RESULTS")
    max_search_results: int = Field(default=50, env="MAX_SEARCH_RESULTS")
    max_recommendations: int = Field(default=10, env="MAX_RECOMMENDATIONS")
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")  # seconds

    # Steam API (optional)
    steam_api_key: str | None = Field(default=None, env="STEAM_API_KEY")

    # User defaults
    default_steam_id: str | None = Field(default=None, env="DEFAULT_STEAM_ID")

    # Feature flags
    enable_ml_recommendations: bool = Field(default=False, env="ENABLE_ML_RECOMMENDATIONS")
    enable_social_features: bool = Field(default=True, env="ENABLE_SOCIAL_FEATURES")
    enable_natural_language_search: bool = Field(default=True, env="ENABLE_NL_SEARCH")
    enable_recommendations: bool = Field(default=True, env="ENABLE_RECOMMENDATIONS")
    enable_friends_data: bool = Field(default=True, env="ENABLE_FRIENDS_DATA")

    # Logging
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    log_file: str | None = Field(default=None, env="LOG_FILE")

    # Health monitoring
    health_check_interval: int = Field(default=60, env="HEALTH_CHECK_INTERVAL")  # seconds
    enable_detailed_health: bool = Field(default=True, env="ENABLE_DETAILED_HEALTH")

    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @validator("database_url")
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("database_url cannot be empty")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


class ConfigManager:
    """Enhanced configuration manager with runtime updates and monitoring"""

    def __init__(self):
        self._settings = Settings()
        self._logger = logging.getLogger(__name__)
        self._configure_logging()

    @property
    def settings(self) -> Settings:
        return self._settings

    def _configure_logging(self):
        """Configure logging based on settings"""
        level = getattr(logging, self._settings.log_level)

        # Configure root logger
        logging.basicConfig(level=level, format=self._settings.log_format, filename=self._settings.log_file, filemode="a" if self._settings.log_file else None)

        # Set specific loggers
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO if self._settings.database_echo else logging.WARNING)

        self._logger.info(f"Logging configured - Level: {self._settings.log_level}")

    def get_performance_config(self) -> dict[str, Any]:
        """Get performance-related configuration"""
        return {"max_search_results": self._settings.max_search_results, "max_recommendations": self._settings.max_recommendations, "max_concurrent_requests": self._settings.max_concurrent_requests, "request_timeout": self._settings.request_timeout, "database_pool_size": self._settings.database_pool_size, "cache_settings": {"enabled": self._settings.enable_cache, "max_size": self._settings.cache_max_size, "default_ttl": self._settings.cache_ttl, "search_ttl": self._settings.cache_ttl_search, "user_ttl": self._settings.cache_ttl_user, "recommendations_ttl": self._settings.cache_ttl_recommendations, "stats_ttl": self._settings.cache_ttl_stats}}

    def get_feature_flags(self) -> dict[str, bool]:
        """Get current feature flags"""
        return {"natural_language_search": self._settings.enable_natural_language_search, "recommendations": self._settings.enable_recommendations, "friends_data": self._settings.enable_friends_data, "caching": self._settings.enable_cache, "detailed_health": self._settings.enable_detailed_health, "social_features": self._settings.enable_social_features, "ml_recommendations": self._settings.enable_ml_recommendations}

    def get_server_info(self) -> dict[str, Any]:
        """Get server information"""
        return {"name": "steam-librarian", "version": "2.0.0", "debug": self._settings.debug, "host": self._settings.host, "port": self._settings.port, "workers": self._settings.workers, "database_url": self._settings.database_url.split("://", 1)[0] + "://***", "log_level": self._settings.log_level}  # Hide credentials

    def validate_configuration(self) -> dict[str, Any]:
        """Validate current configuration and return status"""
        validation_results = {"valid": True, "warnings": [], "errors": []}

        # Check database URL
        if "sqlite://" not in self._settings.database_url and "postgresql://" not in self._settings.database_url:
            validation_results["warnings"].append("Database URL format may not be supported")

        # Check performance settings
        if self._settings.max_concurrent_requests > 1000:
            validation_results["warnings"].append("High max_concurrent_requests may impact performance")

        if self._settings.cache_max_size > 10000:
            validation_results["warnings"].append("Large cache size may consume significant memory")

        # Check Steam API settings
        if not self._settings.steam_api_key:
            validation_results["warnings"].append("STEAM_API_KEY not set - some features may be limited")

        if not self._settings.default_steam_id:
            validation_results["warnings"].append("DEFAULT_STEAM_ID not set - will use database users")

        # Check file permissions for log file
        if self._settings.log_file:
            try:
                log_dir = os.path.dirname(self._settings.log_file)
                if log_dir and not os.path.exists(log_dir):
                    validation_results["warnings"].append(f"Log directory does not exist: {log_dir}")
                elif not os.access(log_dir or ".", os.W_OK):
                    validation_results["errors"].append(f"Cannot write to log directory: {log_dir or '.'}")
                    validation_results["valid"] = False
            except Exception as e:
                validation_results["warnings"].append(f"Could not validate log file path: {e}")

        return validation_results


# Global configuration manager instance
config_manager = ConfigManager()
settings = config_manager.settings

# Export commonly used values for backward compatibility
DATABASE_URL = settings.database_url
DEFAULT_STEAM_ID = settings.default_steam_id
CACHE_TTL = settings.cache_ttl
DEBUG = settings.debug
