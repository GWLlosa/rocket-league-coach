"""Minimal configuration management for the Rocket League Coach application."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Minimal application settings."""
    
    # Essential settings only
    ballchasing_api_token: str = ""
    environment: str = "production"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        """Initialize settings."""
        super().__init__(**kwargs)
        
        # Create directories
        for dir_name in ["data/replays", "data/cache", "data/players"]:
            Path(dir_name).mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def get_ballchasing_token() -> str:
    """Get API token."""
    return get_settings().ballchasing_api_token

def get_cache_dir() -> Path:
    """Get cache directory."""
    return Path("data/cache")

def is_debug_mode() -> bool:
    """Check debug mode."""
    return get_settings().debug

def get_log_level() -> str:
    """Get log level."""
    return get_settings().log_level
