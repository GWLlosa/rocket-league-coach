"""Configuration management for Rocket League Coach."""

import os
from typing import Optional
from pathlib import Path

from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Environment and Server Configuration
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Ballchasing API Configuration
    ballchasing_api_key: str
    ballchasing_base_url: str = "https://ballchasing.com/api"
    ballchasing_rate_limit_per_second: int = 2
    ballchasing_rate_limit_per_hour: int = 500
    
    # Analysis Configuration
    default_games_count: int = 10
    min_sample_size_for_correlation: int = 5
    statistical_significance_threshold: float = 0.05
    effect_size_threshold: float = 0.5
    cache_ttl_hours: int = 24
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # Database Configuration
    database_url: str = "sqlite:///./rocket_league_coach.db"
    
    # File Storage Paths
    replays_dir: Path = Path("./replays")
    analysis_cache_dir: Path = Path("./analysis_cache")
    player_data_dir: Path = Path("./player_data")
    logs_dir: Path = Path("./logs")
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "rocket_league_coach.log"
    
    # Security Configuration
    secret_key: str = "your-secret-key-here-change-in-production"
    allowed_hosts: list = ["localhost", "127.0.0.1"]
    
    # Performance Configuration
    max_concurrent_downloads: int = 3
    max_concurrent_analysis: int = 2
    request_timeout_seconds: int = 30
    analysis_timeout_seconds: int = 300
    
    # Statistical Analysis Configuration
    confidence_level_high: float = 0.01
    confidence_level_medium: float = 0.05
    correlation_threshold: float = 0.6
    
    # Web Interface Configuration
    enable_cors: bool = True
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # Monitoring and Health Checks
    health_check_interval: int = 30
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    @validator("ballchasing_api_key")
    def validate_api_key(cls, v):
        """Validate that Ballchasing API key is provided."""
        if not v or v == "your_ballchasing_api_key_here":
            raise ValueError(
                "Ballchasing API key must be provided. "
                "Get one from https://ballchasing.com/upload"
            )
        return v
    
    @validator("replays_dir", "analysis_cache_dir", "player_data_dir", "logs_dir")
    def create_directories(cls, v):
        """Ensure directories exist."""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_environments = ["development", "testing", "production"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of {valid_environments}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "testing"
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global settings
    settings = Settings()
    return settings
