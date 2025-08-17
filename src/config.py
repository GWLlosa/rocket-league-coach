"""Configuration management for the Rocket League Coach application."""

import os
from typing import Optional, List
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""
    
    # API Configuration
    ballchasing_api_token: str = Field(
        default="",
        description="API token for Ballchasing.com"
    )
    
    # Application Settings
    environment: str = Field(default="development", description="Environment (development/production)")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Directory Settings
    replays_dir: Path = Field(default=Path("data/replays"), description="Directory for replay files")
    analysis_cache_dir: Path = Field(default=Path("data/cache"), description="Directory for analysis cache")
    player_data_dir: Path = Field(default=Path("data/players"), description="Directory for player data")
    
    # Cache Settings
    cache_ttl_hours: int = Field(default=24, description="Cache TTL in hours")
    max_cache_size_gb: int = Field(default=5, description="Maximum cache size in GB")
    
    # Rate Limiting
    rate_limit_per_second: float = Field(default=2.0, description="API requests per second")
    rate_limit_per_hour: int = Field(default=500, description="API requests per hour")
    
    # Analysis Settings
    min_games_for_analysis: int = Field(default=5, description="Minimum games needed for analysis")
    max_games_per_analysis: int = Field(default=50, description="Maximum games per analysis")
    confidence_threshold: float = Field(default=0.05, description="P-value threshold for significance")
    
    # CORS Settings
    enable_cors: bool = Field(default=True, description="Enable CORS")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False
        
        # Define environment variable names
        fields = {
            'ballchasing_api_token': {
                'env': ['BALLCHASING_API_TOKEN', 'BALLCHASING_API_KEY']
            }
        }
    
    def __init__(self, **kwargs):
        """Initialize settings with environment variable loading."""
        super().__init__(**kwargs)
        
        # Ensure directories exist
        self.replays_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_cache_dir.mkdir(parents=True, exist_ok=True)
        self.player_data_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    def get_database_url(self) -> str:
        """Get database URL for cache database."""
        return f"sqlite:///{self.analysis_cache_dir}/cache.db"
    
    def validate_api_token(self) -> bool:
        """Validate that API token is configured."""
        return bool(self.ballchasing_api_token and self.ballchasing_api_token != "your_ballchasing_api_token_here")


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    global _settings
    _settings = None
    return get_settings()


# Convenience functions for common settings
def get_ballchasing_token() -> str:
    """Get the Ballchasing API token."""
    return get_settings().ballchasing_api_token


def get_cache_dir() -> Path:
    """Get the cache directory path."""
    return get_settings().analysis_cache_dir


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return get_settings().debug


def get_log_level() -> str:
    """Get the configured log level."""
    return get_settings().log_level
