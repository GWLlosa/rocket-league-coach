"""Data models for persistence and caching."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import json

from pydantic import BaseModel, Field


class AnalysisStatus(Enum):
    """Status of an analysis job."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class CacheEntryType(Enum):
    """Type of cached entry."""
    REPLAY_FILE = "replay_file"
    ANALYSIS_RESULT = "analysis_result"
    PLAYER_GAMES = "player_games"
    METRICS = "metrics"


@dataclass
class ReplayCacheEntry:
    """Cache entry for a replay file."""
    replay_id: str
    file_path: Path
    file_size: int
    download_time: datetime
    last_accessed: datetime
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'replay_id': self.replay_id,
            'file_path': str(self.file_path),
            'file_size': self.file_size,
            'download_time': self.download_time.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'access_count': self.access_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReplayCacheEntry':
        """Create from dictionary."""
        return cls(
            replay_id=data['replay_id'],
            file_path=Path(data['file_path']),
            file_size=data['file_size'],
            download_time=datetime.fromisoformat(data['download_time']),
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            access_count=data.get('access_count', 0)
        )


class GameResultModel(BaseModel):
    """Pydantic model for game results."""
    replay_id: str
    player_name: str
    team_color: str = Field(..., description="blue or orange")
    team_score: int
    opponent_score: int
    won: bool
    duration: int = Field(..., description="Game duration in seconds")
    date: datetime
    playlist: Optional[str] = None
    map_name: Optional[str] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlayerAnalysisModel(BaseModel):
    """Pydantic model for complete player analysis."""
    analysis_id: str
    player_name: str
    rank: str = "platinum"
    games_analyzed: int
    wins: int
    losses: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: AnalysisStatus = AnalysisStatus.PENDING
    
    # Analysis results
    average_metrics: Dict[str, float] = Field(default_factory=dict)
    rule_based_insights: List[Dict[str, Any]] = Field(default_factory=list)
    correlation_insights: List[Dict[str, Any]] = Field(default_factory=list)
    coaching_summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    confidence_score: float = 0.0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            AnalysisStatus: lambda v: v.value
        }


class CacheMetrics(BaseModel):
    """Cache performance metrics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    eviction_count: int = 0
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class PlayerGameHistory(BaseModel):
    """Model for tracking player's game history."""
    player_name: str
    games: List[GameResultModel] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    
    def add_game(self, game: GameResultModel):
        """Add a game to history."""
        # Avoid duplicates
        if not any(g.replay_id == game.replay_id for g in self.games):
            self.games.append(game)
            self.total_games = len(self.games)
            self.wins = sum(1 for g in self.games if g.won)
            self.losses = self.total_games - self.wins
            self.last_updated = datetime.utcnow()
    
    def get_recent_games(self, count: int = 10) -> List[GameResultModel]:
        """Get most recent games."""
        sorted_games = sorted(self.games, key=lambda g: g.date, reverse=True)
        return sorted_games[:count]
    
    def get_games_since(self, since: datetime) -> List[GameResultModel]:
        """Get games since a specific date."""
        return [g for g in self.games if g.date >= since]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


@dataclass
class AnalysisJobInfo:
    """Information about an analysis job."""
    job_id: str
    player_name: str
    num_games: int
    status: AnalysisStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    current_step: str = ""
    error_message: Optional[str] = None
    result_path: Optional[str] = None
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get job duration if completed."""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return datetime.utcnow() - self.started_at
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed (success or failure)."""
        return self.status in [AnalysisStatus.COMPLETED, AnalysisStatus.FAILED]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'job_id': self.job_id,
            'player_name': self.player_name,
            'num_games': self.num_games,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'current_step': self.current_step,
            'error_message': self.error_message,
            'result_path': self.result_path,
            'duration_seconds': self.duration.total_seconds() if self.duration else None
        }


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = "sqlite:///./rocket_league_coach.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    
    
class CacheConfig(BaseModel):
    """Cache configuration."""
    ttl_hours: int = 24
    max_size_gb: float = 5.0
    cleanup_interval_hours: int = 6
    max_entries: int = 10000
    
    @property
    def ttl_seconds(self) -> int:
        """TTL in seconds."""
        return self.ttl_hours * 3600
    
    @property
    def max_size_bytes(self) -> int:
        """Max size in bytes."""
        return int(self.max_size_gb * 1024 * 1024 * 1024)
    
    @property
    def cleanup_interval_seconds(self) -> int:
        """Cleanup interval in seconds."""
        return self.cleanup_interval_hours * 3600


# JSON serialization helpers
def serialize_datetime(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def deserialize_datetime(date_string: str) -> datetime:
    """Deserialize datetime from ISO string."""
    return datetime.fromisoformat(date_string)


def model_to_json(model: BaseModel) -> str:
    """Convert Pydantic model to JSON string."""
    return model.json()


def model_from_json(model_class, json_str: str):
    """Create Pydantic model from JSON string."""
    return model_class.parse_raw(json_str)
