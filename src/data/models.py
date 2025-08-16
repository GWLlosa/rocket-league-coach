"""Data models for the Rocket League Coach application."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class GameResult(str, Enum):
    """Game result enumeration."""
    WIN = "win"
    LOSS = "loss"


class ConfidenceLevel(str, Enum):
    """Statistical confidence level enumeration."""
    HIGH = "high"      # p < 0.01
    MEDIUM = "medium"  # p < 0.05
    LOW = "low"        # p >= 0.05


class MetricTier(str, Enum):
    """Metric tier for coaching analysis."""
    TIER_1 = "tier_1"  # High-confidence causal metrics
    TIER_2 = "tier_2"  # Medium-confidence tactical metrics
    TIER_3 = "tier_3"  # Advanced correlation metrics


class InsightType(str, Enum):
    """Type of coaching insight."""
    RULE_BASED = "rule_based"
    CORRELATION = "correlation"


class PlayerMetrics(BaseModel):
    """Player performance metrics for a single game."""
    
    # Tier 1: High-Confidence Causal Metrics
    avg_speed: float = Field(..., description="Average speed throughout game (uu/s)")
    time_supersonic_speed: float = Field(..., description="Time spent at maximum speed (seconds)")
    shooting_percentage: float = Field(..., description="Goals scored per shot taken (0-1)")
    avg_amount: float = Field(..., description="Average boost level maintained (0-100)")
    time_zero_boost: float = Field(..., description="Time spent without boost (seconds)")
    time_defensive_third: float = Field(..., description="Time spent in defensive zone (seconds)")
    
    # Tier 2: Medium-Confidence Tactical Metrics
    avg_distance_to_ball: float = Field(..., description="Average distance from ball (uu)")
    time_behind_ball: float = Field(..., description="Time spent behind ball (seconds)")
    amount_overfill: float = Field(..., description="Boost wasted through overfill")
    saves: int = Field(..., description="Total saves per game")
    
    # Tier 3: Advanced Correlation Metrics
    time_most_back: float = Field(..., description="Time spent as last defender (seconds)")
    assists: int = Field(..., description="Assists per game")
    
    # Additional context
    game_duration: float = Field(..., description="Total game duration (seconds)")
    
    @validator('shooting_percentage')
    def validate_shooting_percentage(cls, v):
        """Validate shooting percentage is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError('Shooting percentage must be between 0 and 1')
        return v
    
    @validator('avg_amount')
    def validate_avg_amount(cls, v):
        """Validate average boost amount is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError('Average boost amount must be between 0 and 100')
        return v


class GameData(BaseModel):
    """Complete game data with metrics and context."""
    
    replay_id: str = Field(..., description="Unique replay identifier")
    gamertag: str = Field(..., description="Player gamertag")
    game_date: datetime = Field(..., description="When the game was played")
    game_result: GameResult = Field(..., description="Win or loss")
    rank_tier: Optional[int] = Field(None, description="Player's rank tier")
    playlist: Optional[str] = Field(None, description="Game playlist (e.g., 'Ranked Standard')")
    duration: float = Field(..., description="Game duration in seconds")
    
    # Player metrics
    metrics: PlayerMetrics = Field(..., description="Player performance metrics")
    
    # Raw data for advanced analysis
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw carball analysis data")


class StatisticalResult(BaseModel):
    """Statistical analysis result for a metric."""
    
    metric_name: str = Field(..., description="Name of the metric analyzed")
    metric_tier: MetricTier = Field(..., description="Tier classification of the metric")
    
    # Win/Loss statistics
    win_mean: float = Field(..., description="Mean value in winning games")
    win_std: float = Field(..., description="Standard deviation in winning games")
    win_count: int = Field(..., description="Number of winning games")
    
    loss_mean: float = Field(..., description="Mean value in losing games")
    loss_std: float = Field(..., description="Standard deviation in losing games")
    loss_count: int = Field(..., description="Number of losing games")
    
    # Statistical significance
    p_value: float = Field(..., description="P-value from t-test")
    effect_size: float = Field(..., description="Cohen's d effect size")
    confidence_level: ConfidenceLevel = Field(..., description="Statistical confidence level")
    
    # Practical interpretation
    difference: float = Field(..., description="Mean difference (win - loss)")
    difference_percentage: float = Field(..., description="Percentage difference")
    is_significant: bool = Field(..., description="Whether the difference is statistically significant")
    
    @validator('p_value')
    def validate_p_value(cls, v):
        """Validate p-value is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError('P-value must be between 0 and 1')
        return v


class CoachingInsight(BaseModel):
    """Individual coaching insight or recommendation."""
    
    insight_type: InsightType = Field(..., description="Type of insight")
    metric_name: str = Field(..., description="Metric this insight is based on")
    metric_tier: MetricTier = Field(..., description="Tier of the metric")
    
    title: str = Field(..., description="Short title for the insight")
    message: str = Field(..., description="Detailed coaching message")
    priority: int = Field(..., description="Priority level (1-5, 1 being highest)")
    
    # Statistical backing (for correlation insights)
    statistical_result: Optional[StatisticalResult] = Field(None, description="Statistical analysis supporting this insight")
    
    # Context and recommendations
    current_performance: Optional[float] = Field(None, description="Current performance level")
    target_performance: Optional[float] = Field(None, description="Target performance level")
    improvement_potential: Optional[float] = Field(None, description="Potential improvement percentage")
    
    # Actionable advice
    specific_actions: List[str] = Field(default_factory=list, description="Specific actions to take")
    practice_drills: List[str] = Field(default_factory=list, description="Recommended practice drills")


class PlayerAnalysisResult(BaseModel):
    """Complete analysis result for a player."""
    
    # Player information
    gamertag: str = Field(..., description="Player gamertag")
    analysis_date: datetime = Field(..., description="When the analysis was performed")
    
    # Game data summary
    total_games: int = Field(..., description="Total number of games analyzed")
    wins: int = Field(..., description="Number of wins")
    losses: int = Field(..., description="Number of losses")
    win_rate: float = Field(..., description="Win rate percentage (0-100)")
    
    # Data quality indicators
    has_sufficient_data: bool = Field(..., description="Whether there's enough data for reliable analysis")
    min_sample_size_met: bool = Field(..., description="Whether minimum sample size is met")
    confidence_score: float = Field(..., description="Overall confidence in analysis (0-1)")
    
    # Insights categorized by type
    rule_based_insights: List[CoachingInsight] = Field(default_factory=list, description="Rule-based coaching insights")
    correlation_insights: List[CoachingInsight] = Field(default_factory=list, description="Win/loss correlation insights")
    
    # Statistical analysis results
    statistical_results: List[StatisticalResult] = Field(default_factory=list, description="Detailed statistical analysis")
    
    # Summary and priorities
    top_priority_insights: List[CoachingInsight] = Field(default_factory=list, description="Top 3-5 most important insights")
    key_strengths: List[str] = Field(default_factory=list, description="Player's key strengths")
    improvement_areas: List[str] = Field(default_factory=list, description="Primary areas for improvement")
    
    # Performance trends
    recent_performance_trend: Optional[str] = Field(None, description="Recent performance trend (improving/declining/stable)")
    
    @validator('win_rate')
    def validate_win_rate(cls, v):
        """Validate win rate is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError('Win rate must be between 0 and 100')
        return v
    
    @validator('confidence_score')
    def validate_confidence_score(cls, v):
        """Validate confidence score is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError('Confidence score must be between 0 and 1')
        return v


class AnalysisRequest(BaseModel):
    """Request for player analysis."""
    
    gamertag: str = Field(..., description="Player gamertag to analyze")
    num_games: int = Field(default=10, description="Number of recent games to analyze")
    force_refresh: bool = Field(default=False, description="Force refresh of cached data")
    include_raw_data: bool = Field(default=False, description="Include raw analysis data in response")
    
    @validator('num_games')
    def validate_num_games(cls, v):
        """Validate number of games is reasonable."""
        if not 1 <= v <= 50:
            raise ValueError('Number of games must be between 1 and 50')
        return v


class AnalysisStatus(BaseModel):
    """Status of an ongoing analysis."""
    
    analysis_id: str = Field(..., description="Unique analysis identifier")
    gamertag: str = Field(..., description="Player being analyzed")
    status: str = Field(..., description="Current status")
    progress: float = Field(..., description="Progress percentage (0-100)")
    
    # Status details
    current_step: str = Field(..., description="Current processing step")
    total_steps: int = Field(..., description="Total number of steps")
    completed_steps: int = Field(..., description="Number of completed steps")
    
    # Timing information
    started_at: datetime = Field(..., description="When analysis started")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if analysis failed")
    
    @validator('progress')
    def validate_progress(cls, v):
        """Validate progress is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError('Progress must be between 0 and 100')
        return v


class CacheStats(BaseModel):
    """Cache statistics and health information."""
    
    replay_cache: Dict[str, Union[int, float]] = Field(..., description="Replay cache statistics")
    analysis_cache: Dict[str, Union[int, float]] = Field(..., description="Analysis cache statistics")
    player_history: Dict[str, Union[int, float]] = Field(..., description="Player history statistics")
    total_cache_size: int = Field(..., description="Total cache size in bytes")
    
    # Health indicators
    cache_hit_rate: Optional[float] = Field(None, description="Cache hit rate percentage")
    average_analysis_time: Optional[float] = Field(None, description="Average analysis time in seconds")
    
    # Cleanup information
    last_cleanup: Optional[datetime] = Field(None, description="Last cache cleanup time")
    next_cleanup: Optional[datetime] = Field(None, description="Next scheduled cleanup time")


class HealthCheck(BaseModel):
    """Application health check response."""
    
    status: str = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    
    # Component health
    components: Dict[str, str] = Field(default_factory=dict, description="Individual component health")
    
    # Performance metrics
    uptime_seconds: Optional[float] = Field(None, description="Uptime in seconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cache_status: Optional[str] = Field(None, description="Cache system status")
    
    # Dependencies
    ballchasing_api_status: Optional[str] = Field(None, description="Ballchasing API connectivity")
    carball_status: Optional[str] = Field(None, description="Carball library status")


class ErrorResponse(BaseModel):
    """Standardized error response."""
    
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    error_code: Optional[str] = Field(None, description="Application-specific error code")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the error occurred")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")


# Type aliases for complex types
GamesData = List[GameData]
MetricsData = Dict[str, List[float]]  # metric_name -> list of values
WinLossData = Dict[GameResult, List[float]]  # win/loss -> list of metric values
