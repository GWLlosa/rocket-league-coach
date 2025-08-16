"""Pydantic models for API responses and data structures."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class PlayerInfo(BaseModel):
    """Player information from Ballchasing API."""
    id: Dict[str, str] = Field(..., description="Player platform IDs")
    name: str = Field(..., description="Player display name")
    avatar: Optional[str] = Field(None, description="Player avatar URL")


class TeamInfo(BaseModel):
    """Team information from replay metadata."""
    name: Optional[str] = Field(None, description="Team name")
    color: Optional[str] = Field(None, description="Team color")
    
    
class GameInfo(BaseModel):
    """Game metadata from Ballchasing API."""
    id: str = Field(..., description="Unique replay ID")
    title: Optional[str] = Field(None, description="Replay title")
    created: datetime = Field(..., description="Upload timestamp")
    date: datetime = Field(..., description="Game timestamp")
    duration: int = Field(..., description="Game duration in seconds")
    
    # Map information
    map_name: Optional[str] = Field(None, alias="map", description="Map name")
    playlist_name: Optional[str] = Field(None, alias="playlist", description="Playlist/game mode")
    
    # Team information
    blue: Optional[TeamInfo] = Field(None, description="Blue team info")
    orange: Optional[TeamInfo] = Field(None, description="Orange team info")
    
    # File information
    replay_url: Optional[str] = Field(None, description="Download URL")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    
    class Config:
        allow_population_by_field_name = True


class ReplaySearchResponse(BaseModel):
    """Response from Ballchasing replay search API."""
    list: List[GameInfo] = Field(..., description="List of found replays")
    count: int = Field(..., description="Total number of results")
    
    
class PlayerStats(BaseModel):
    """Player statistics from replay."""
    player_id: str = Field(..., description="Player identifier")
    player_name: str = Field(..., description="Player display name")
    team_color: str = Field(..., description="Team color (blue/orange)")
    
    # Core stats
    score: int = Field(0, description="Total score")
    goals: int = Field(0, description="Goals scored")
    assists: int = Field(0, description="Assists")
    saves: int = Field(0, description="Saves")
    shots: int = Field(0, description="Shots taken")
    
    # Advanced stats (will be populated by Carball)
    boost_usage: Optional[float] = Field(None, description="Boost usage efficiency")
    speed_avg: Optional[float] = Field(None, description="Average speed")
    time_supersonic: Optional[float] = Field(None, description="Time at supersonic speed")
    
    
class GameResult(BaseModel):
    """Game result information."""
    replay_id: str = Field(..., description="Replay identifier")
    player_name: str = Field(..., description="Target player name")
    team_color: str = Field(..., description="Player's team color")
    team_score: int = Field(..., description="Player's team final score")
    opponent_score: int = Field(..., description="Opponent team final score")
    won: bool = Field(..., description="Whether the player won")
    duration: int = Field(..., description="Game duration in seconds")
    date: datetime = Field(..., description="Game timestamp")
    playlist: Optional[str] = Field(None, description="Game mode/playlist")
    map_name: Optional[str] = Field(None, description="Map name")
    
    @validator('won', pre=True, always=True)
    def determine_winner(cls, v, values):
        """Determine if the player won based on scores."""
        if v is not None:
            return v
        team_score = values.get('team_score', 0)
        opponent_score = values.get('opponent_score', 0)
        return team_score > opponent_score


class BallchasingError(BaseModel):
    """Error response from Ballchasing API."""
    error: str = Field(..., description="Error message")
    message: Optional[str] = Field(None, description="Detailed error message")
    status_code: Optional[int] = Field(None, description="HTTP status code")


class DownloadInfo(BaseModel):
    """Information about a replay download."""
    replay_id: str = Field(..., description="Replay identifier")
    file_path: str = Field(..., description="Local file path")
    file_size: int = Field(..., description="Downloaded file size")
    download_time: float = Field(..., description="Download duration in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Download timestamp")


class AnalysisRequest(BaseModel):
    """Request model for player analysis."""
    gamertag: str = Field(..., min_length=1, max_length=100, description="Player gamertag")
    num_games: int = Field(10, ge=1, le=50, description="Number of games to analyze")
    include_casual: bool = Field(False, description="Include casual games")
    
    @validator('gamertag')
    def validate_gamertag(cls, v):
        """Validate gamertag format."""
        if not v or not v.strip():
            raise ValueError("Gamertag cannot be empty")
        return v.strip()


class AnalysisStatus(BaseModel):
    """Status of an ongoing analysis."""
    analysis_id: str = Field(..., description="Unique analysis identifier")
    player_name: str = Field(..., description="Player being analyzed")
    status: str = Field(..., description="Current status")
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Progress percentage")
    current_step: Optional[str] = Field(None, description="Current processing step")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis start time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Results (populated when complete)
    games_found: Optional[int] = Field(None, description="Number of games found")
    games_analyzed: Optional[int] = Field(None, description="Number of games successfully analyzed")


class AnalysisResult(BaseModel):
    """Complete analysis result."""
    analysis_id: str = Field(..., description="Analysis identifier")
    player_name: str = Field(..., description="Analyzed player")
    completed_at: datetime = Field(default_factory=datetime.utcnow, description="Completion timestamp")
    
    # Game summary
    total_games: int = Field(..., description="Total games analyzed")
    wins: int = Field(..., description="Number of wins")
    losses: int = Field(..., description="Number of losses")
    
    # Insights
    rule_based_insights: List[Dict[str, Any]] = Field(default_factory=list, description="Rule-based coaching insights")
    correlation_insights: List[Dict[str, Any]] = Field(default_factory=list, description="Win/loss correlation insights")
    
    # Statistical summary
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Overall confidence in insights")
    sample_size_adequate: bool = Field(False, description="Whether sample size is adequate for correlations")
    
    # Raw data (optional, for detailed view)
    game_results: Optional[List[GameResult]] = Field(None, description="Individual game results")
    metrics_summary: Optional[Dict[str, Any]] = Field(None, description="Aggregated metrics summary")
