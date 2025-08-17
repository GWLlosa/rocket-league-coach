"""Minimal configuration management for the Rocket League Coach application."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Minimal application settings."""
    
    # Essential settings only
    ballchasing_api_token: str = ""
    environment: str = "production"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    
    # Additional settings that the app expects
    enable_cors: bool = True
    cors_origins: List[str] = ["*"]
    
    # Directory settings as strings (will be converted to Path objects)
    logs_dir: str = "logs"
    replays_dir: str = "data/replays"
    analysis_cache_dir: str = "data/cache" 
    player_data_dir: str = "data/players"
    
    # Logging settings
    log_format: str = "standard"  # "json" or "standard"
    log_file: str = "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow extra fields to prevent pydantic errors
        extra = "ignore"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ["development", "dev", "local"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ["production", "prod"]
    
    def __init__(self, **kwargs):
        """Initialize settings."""
        super().__init__(**kwargs)
        # Convert string paths to Path objects after initialization
        self.logs_dir = Path(self.logs_dir)
        self.replays_dir = Path(self.replays_dir)
        self.analysis_cache_dir = Path(self.analysis_cache_dir)
        self.player_data_dir = Path(self.player_data_dir)

    def mkdir(self, *args, **kwargs):
        """Mock mkdir method that the app might be calling."""
        pass

    def ensure_directories(self):
        """Ensure directories exist - call this when needed."""
        try:
            for dir_path in [self.replays_dir, self.analysis_cache_dir, self.player_data_dir, self.logs_dir]:
                dir_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Log warning but don't fail startup
            print(f"Warning: Could not create directories. Using /tmp as fallback.")
        except Exception as e:
            print(f"Warning: Error creating directories: {e}")


# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        # Ensure directories exist on first access
        _settings.ensure_directories()
    return _settings

def get_ballchasing_token() -> str:
    """Get API token."""
    return get_settings().ballchasing_api_token

def get_cache_dir() -> Path:
    """Get cache directory."""
    return get_settings().analysis_cache_dir

def is_debug_mode() -> bool:
    """Check debug mode."""
    return get_settings().debug

def get_log_level() -> str:
    """Get log level."""
    return get_settings().log_level
