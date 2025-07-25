"""Configuration management module"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration management"""
    
    # Steam API Configuration
    STEAM_ID: Optional[str] = os.getenv('STEAM_ID')
    STEAM_API_KEY: Optional[str] = os.getenv('STEAM_API_KEY')
    
    # Database Configuration
    STEAM_LIBRARY_DB: str = os.getenv('STEAM_LIBRARY_DB', 'steam_library.db')
    
    # Cache Configuration
    CACHE_DAYS: int = int(os.getenv('CACHE_DAYS', '7'))
    
    # API Rate Limiting
    RATE_LIMIT_DELAY: float = float(os.getenv('RATE_LIMIT_DELAY', '1.0'))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.STEAM_ID or not cls.STEAM_API_KEY:
            return False
        return True
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get the database URL"""
        return f"sqlite:///{cls.STEAM_LIBRARY_DB}"