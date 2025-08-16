"""Main analysis service orchestrating the complete workflow."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from ..api.ballchasing_client import BallchasingClient
from ..api.exceptions import BallchasingAPIError, ReplayNotFoundError
from ..analysis.replay_processor import ReplayProcessor
from ..analysis.metrics_extractor import MetricsExtractor
from ..analysis.statistical_analyzer import StatisticalAnalyzer
from ..analysis.coach import RocketLeagueCoach
from ..analysis.exceptions import ReplayProcessingError, AnalysisError
from ..data.cache_manager import get_cache_manager
from ..data.models import (
    AnalysisRequest, AnalysisStatus, PlayerAnalysisResult, 
    GameData, PlayerMetrics, GameResult
)
from ..config import get_settings
from ..logging_config import get_logger

logger = get_logger(__name__)


class AnalysisService:
    """Main service for orchestrating player analysis workflow."""
    
    def __init__(self):
        """Initialize the analysis service."""
        self.settings = get_settings()
        self.cache_manager = get_cache_manager()
        
        # Initialize components
        self.ballchasing_client = BallchasingClient()
        self.replay_processor = ReplayProcessor()
        self.metrics_extractor = MetricsExtractor()
        self.statistical_analyzer = StatisticalAnalyzer()
        self.coach = RocketLeagueCoach()
        
        # Track ongoing analyses
        self._active_analyses: Dict[str, AnalysisStatus] = {}
        
        logger.info("Analysis service initialized")
    
    async def analyze_player(
        self, 
        request: AnalysisRequest,
        progress_callback: Optional[callable] = None
    ) -> PlayerAnalysisResult:
        """Analyze a player's performance with complete workflow.
        
        Args:
            request: Analysis request parameters
            progress_callback: Optional callback for progress updates
            
        Returns:
            Complete player analysis result
            
        Raises:
            AnalysisError: If analysis fails
        """
        analysis_id = str(uuid.uuid4())
        gamertag = request.gamertag
        
        logger.info(
            "Starting player analysis",
            analysis_id=analysis_id,
            gamertag=gamertag,
            num_games=request.num_games
        )
        
        # Initialize progress tracking
        status = AnalysisStatus(
            analysis_id=analysis_id,
            gamertag=gamertag,
            status="starting",
            progress=0.0,
            current_step="Initializing analysis",
            total_steps=7,
            completed_steps=0,
            started_at=datetime.now()
        )
        
        self._active_analyses[analysis_id] = status
        
        try:
            # Step 1: Check cache for recent analysis
            await self._update_progress(status, 1, "Checking cache for recent analysis", progress_callback)
            
            if not request.force_refresh:
                cached_result = self._get_cached_analysis(gamertag)
                if cached_result:
                    logger.info("Returning cached analysis result", gamertag=gamertag)
                    return cached_result
            
            # Step 2: Fetch replay list from Ballchasing
            await self._update_progress(status, 2, "Fetching replay list from Ballchasing API", progress_callback)
            
            replay_list = await self._fetch_replay_list(gamertag, request.num_games)
            
            if not replay_list:
                raise AnalysisError(f"No replays found for player: {gamertag}")
            
            # Step 3: Download and process replays
            await self._update_progress(status, 3, f"Processing {len(replay_list)} replay files", progress_callback)
            
            games_data = await self._process_replays(replay_list, gamertag, status, progress_callback)
            
            if not games_data:
                raise AnalysisError(f"Failed to process any replays for player: {gamertag}")
            
            # Step 4: Perform statistical analysis
            await self._update_progress(status, 4, "Performing statistical analysis", progress_callback)
            
            statistical_results = self.statistical_analyzer.analyze_win_loss_correlations(games_data)
            
            # Step 5: Generate rule-based insights
            await self._update_progress(status, 5, "Generating rule-based coaching insights", progress_callback)
            
            rule_based_insights = self.coach.generate_rule_based_insights(games_data)
            
            # Step 6: Generate correlation insights
            await self._update_progress(status, 6, "Generating correlation-based insights", progress_callback)
            
            correlation_insights = self.coach.generate_correlation_insights(statistical_results)
            
            # Step 7: Compile final result
            await self._update_progress(status, 7, "Compiling analysis results", progress_callback)
            
            result = self._compile_analysis_result(
                gamertag=gamertag,
                games_data=games_data,
                statistical_results=statistical_results,
                rule_based_insights=rule_based_insights,
                correlation_insights=correlation_insights,
                include_raw_data=request.include_raw_data
            )
            
            # Cache the result
            self._cache_analysis_result(gamertag, result)
            
            # Mark as complete
            status.status = "completed"
            status.progress = 100.0
            status.current_step = "Analysis complete"
            status.completed_steps = status.total_steps
            
            if progress_callback:
                progress_callback(status)
            
            logger.info(
                "Player analysis completed successfully",
                analysis_id=analysis_id,
                gamertag=gamertag,
                total_games=len(games_data),
                insights_count=len(result.rule_based_insights) + len(result.correlation_insights)
            )
            
            return result
            
        except Exception as e:
            # Mark analysis as failed
            status.status = "failed"
            status.error_message = str(e)
            
            if progress_callback:
                progress_callback(status)
            
            logger.error(
                "Player analysis failed",
                analysis_id=analysis_id,
                gamertag=gamertag,
                error=str(e),
                error_type=type(e).__name__
            )
            
            raise AnalysisError(f"Analysis failed for {gamertag}: {str(e)}") from e
            
        finally:
            # Clean up active analysis tracking
            if analysis_id in self._active_analyses:
                del self._active_analyses[analysis_id]
    
    def get_analysis_status(self, analysis_id: str) -> Optional[AnalysisStatus]:
        """Get the status of an ongoing analysis.
        
        Args:
            analysis_id: Unique analysis identifier
            
        Returns:
            Analysis status or None if not found
        """
        return self._active_analyses.get(analysis_id)
    
    def get_active_analyses(self) -> List[AnalysisStatus]:
        """Get all currently active analyses.
        
        Returns:
            List of active analysis statuses
        """
        return list(self._active_analyses.values())
    
    async def _fetch_replay_list(self, gamertag: str, num_games: int) -> List[Dict]:
        """Fetch replay list from Ballchasing API.
        
        Args:
            gamertag: Player gamertag
            num_games: Number of games to fetch
            
        Returns:
            List of replay metadata
        """
        try:
            replays = await self.ballchasing_client.search_player_replays(gamertag, count=num_games)
            
            logger.info(
                "Fetched replay list",
                gamertag=gamertag,
                replays_found=len(replays),
                requested=num_games
            )
            
            return replays
            
        except BallchasingAPIError as e:
            logger.error("Failed to fetch replay list", gamertag=gamertag, error=str(e))
            raise AnalysisError(f"Failed to fetch replays for {gamertag}: {str(e)}") from e
    
    async def _process_replays(
        self, 
        replay_list: List[Dict], 
        gamertag: str,
        status: AnalysisStatus,
        progress_callback: Optional[callable] = None
    ) -> List[GameData]:
        """Process replay files and extract game data.
        
        Args:
            replay_list: List of replay metadata
            gamertag: Player gamertag
            status: Current analysis status
            progress_callback: Progress callback function
            
        Returns:
            List of processed game data
        """
        games_data = []
        
        for i, replay_metadata in enumerate(replay_list):
            replay_id = replay_metadata['id']
            
            try:
                # Update progress for this replay
                sub_progress = (i / len(replay_list)) * 100
                step_progress = f"Processing replay {i+1}/{len(replay_list)} ({sub_progress:.1f}%)"
                await self._update_progress(status, 3, step_progress, progress_callback)
                
                # Check cache first
                cached_replay_path = self.cache_manager.get_cached_replay(replay_id, gamertag)
                
                if cached_replay_path:
                    logger.debug("Using cached replay file", replay_id=replay_id)
                    replay_path = cached_replay_path
                else:
                    # Download replay file
                    replay_content = await self.ballchasing_client.download_replay(replay_id)
                    
                    # Cache the replay file
                    game_date = self._parse_replay_date(replay_metadata)
                    game_result = self.ballchasing_client.extract_game_result(replay_metadata, gamertag)
                    
                    replay_path = self.cache_manager.cache_replay_file(
                        replay_id=replay_id,
                        gamertag=gamertag,
                        file_content=replay_content,
                        game_date=game_date,
                        game_result=game_result
                    )
                
                # Process replay with carball
                game_analysis = self.replay_processor.parse_replay_file(replay_path)
                
                # Extract metrics
                metrics = self.metrics_extractor.extract_mvp_metrics(game_analysis, gamertag)
                
                # Create game data object
                game_data = GameData(
                    replay_id=replay_id,
                    gamertag=gamertag,
                    game_date=self._parse_replay_date(replay_metadata),
                    game_result=GameResult(self.ballchasing_client.extract_game_result(replay_metadata, gamertag)),
                    rank_tier=self._extract_rank_tier(replay_metadata, gamertag),
                    playlist=replay_metadata.get('playlist_name'),
                    duration=replay_metadata.get('duration', 0),
                    metrics=PlayerMetrics(**metrics),
                    raw_data=game_analysis if False else None  # Only include if requested
                )
                
                games_data.append(game_data)
                
                # Store in player history cache
                self.cache_manager.store_player_game_history(
                    gamertag=gamertag,
                    replay_id=replay_id,
                    game_date=game_data.game_date,
                    game_result=game_data.game_result.value,
                    rank_tier=game_data.rank_tier
                )
                
                logger.debug(
                    "Successfully processed replay",
                    replay_id=replay_id,
                    gamertag=gamertag,
                    result=game_data.game_result.value
                )
                
            except (ReplayProcessingError, ReplayNotFoundError) as e:
                logger.warning(
                    "Failed to process replay, skipping",
                    replay_id=replay_id,
                    gamertag=gamertag,
                    error=str(e)
                )
                continue
                
            except Exception as e:
                logger.error(
                    "Unexpected error processing replay",
                    replay_id=replay_id,
                    gamertag=gamertag,
                    error=str(e),
                    error_type=type(e).__name__
                )
                continue
        
        logger.info(
            "Replay processing completed",
            gamertag=gamertag,
            total_replays=len(replay_list),
            successful_replays=len(games_data),
            success_rate=len(games_data) / len(replay_list) * 100
        )
        
        return games_data
    
    def _compile_analysis_result(
        self,
        gamertag: str,
        games_data: List[GameData],
        statistical_results: List,
        rule_based_insights: List,
        correlation_insights: List,
        include_raw_data: bool = False
    ) -> PlayerAnalysisResult:
        """Compile the final analysis result.
        
        Args:
            gamertag: Player gamertag
            games_data: Processed game data
            statistical_results: Statistical analysis results
            rule_based_insights: Rule-based coaching insights
            correlation_insights: Correlation-based insights
            include_raw_data: Whether to include raw data
            
        Returns:
            Complete player analysis result
        """
        # Calculate basic statistics
        total_games = len(games_data)
        wins = sum(1 for game in games_data if game.game_result == GameResult.WIN)
        losses = total_games - wins
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        # Data quality assessment
        min_sample_size = 5  # Minimum games per outcome
        has_sufficient_data = wins >= min_sample_size and losses >= min_sample_size
        min_sample_size_met = total_games >= 10
        
        # Calculate confidence score based on data quality
        confidence_score = min(1.0, (total_games / 20) * 0.5 + (min(wins, losses) / 10) * 0.5)
        
        # Combine and prioritize insights
        all_insights = rule_based_insights + correlation_insights
        all_insights.sort(key=lambda x: x.priority)
        top_priority_insights = all_insights[:5]
        
        # Extract key strengths and improvement areas
        key_strengths = self._extract_key_strengths(games_data, statistical_results)
        improvement_areas = self._extract_improvement_areas(all_insights)
        
        return PlayerAnalysisResult(
            gamertag=gamertag,
            analysis_date=datetime.now(),
            total_games=total_games,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            has_sufficient_data=has_sufficient_data,
            min_sample_size_met=min_sample_size_met,
            confidence_score=confidence_score,
            rule_based_insights=rule_based_insights,
            correlation_insights=correlation_insights,
            statistical_results=statistical_results,
            top_priority_insights=top_priority_insights,
            key_strengths=key_strengths,
            improvement_areas=improvement_areas,
            recent_performance_trend=self._analyze_performance_trend(games_data)
        )
    
    def _get_cached_analysis(self, gamertag: str) -> Optional[PlayerAnalysisResult]:
        """Get cached analysis result if available and recent.
        
        Args:
            gamertag: Player gamertag
            
        Returns:
            Cached analysis result or None
        """
        try:
            cached_data = self.cache_manager.get_cached_analysis(
                gamertag=gamertag,
                analysis_type="complete_analysis",
                max_age_hours=24  # Cache for 24 hours
            )
            
            if cached_data:
                cache_key, result_data = cached_data
                return PlayerAnalysisResult(**result_data)
                
        except Exception as e:
            logger.warning("Failed to load cached analysis", gamertag=gamertag, error=str(e))
        
        return None
    
    def _cache_analysis_result(self, gamertag: str, result: PlayerAnalysisResult) -> None:
        """Cache the analysis result.
        
        Args:
            gamertag: Player gamertag
            result: Analysis result to cache
        """
        try:
            self.cache_manager.cache_analysis_result(
                gamertag=gamertag,
                analysis_type="complete_analysis",
                result_data=result.dict(),
                metadata={
                    "total_games": result.total_games,
                    "win_rate": result.win_rate,
                    "confidence_score": result.confidence_score
                },
                ttl_hours=24
            )
            
            logger.debug("Analysis result cached", gamertag=gamertag)
            
        except Exception as e:
            logger.warning("Failed to cache analysis result", gamertag=gamertag, error=str(e))
    
    async def _update_progress(
        self,
        status: AnalysisStatus,
        step: int,
        description: str,
        progress_callback: Optional[callable] = None
    ) -> None:
        """Update analysis progress.
        
        Args:
            status: Analysis status object
            step: Current step number
            description: Step description
            progress_callback: Optional progress callback
        """
        status.completed_steps = step
        status.progress = (step / status.total_steps) * 100
        status.current_step = description
        
        if progress_callback:
            progress_callback(status)
        
        # Small delay to allow for async operation
        await asyncio.sleep(0.01)
    
    def _parse_replay_date(self, replay_metadata: Dict) -> datetime:
        """Parse the replay date from metadata.
        
        Args:
            replay_metadata: Replay metadata from Ballchasing API
            
        Returns:
            Parsed datetime object
        """
        try:
            date_str = replay_metadata.get('date')
            if date_str:
                # Handle ISO format with timezone
                if 'T' in date_str:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            pass
        
        # Fallback to current time if parsing fails
        return datetime.now()
    
    def _extract_rank_tier(self, replay_metadata: Dict, gamertag: str) -> Optional[int]:
        """Extract player rank tier from replay metadata.
        
        Args:
            replay_metadata: Replay metadata from Ballchasing API
            gamertag: Player gamertag
            
        Returns:
            Rank tier or None if not available
        """
        try:
            # Look for player data in replay metadata
            if 'players' in replay_metadata:
                for player_data in replay_metadata['players']:
                    if player_data.get('name', '').lower() == gamertag.lower():
                        rank_data = player_data.get('rank', {})
                        return rank_data.get('tier')
        except (KeyError, TypeError):
            pass
        
        return None
    
    def _extract_key_strengths(self, games_data: List[GameData], statistical_results: List) -> List[str]:
        """Extract player's key strengths from analysis.
        
        Args:
            games_data: Game data list
            statistical_results: Statistical analysis results
            
        Returns:
            List of key strength descriptions
        """
        strengths = []
        
        # Analyze win rate
        wins = sum(1 for game in games_data if game.game_result == GameResult.WIN)
        win_rate = wins / len(games_data) * 100
        
        if win_rate >= 60:
            strengths.append(f"Strong win rate of {win_rate:.1f}%")
        
        # Find metrics where player performs well in wins
        for result in statistical_results:
            if hasattr(result, 'is_significant') and result.is_significant:
                if result.difference > 0:  # Better in wins
                    if result.metric_name in ['avg_speed', 'time_supersonic_speed']:
                        strengths.append("Strong mechanical speed and movement")
                    elif result.metric_name in ['shooting_percentage']:
                        strengths.append("Excellent shooting accuracy")
                    elif result.metric_name in ['avg_amount']:
                        strengths.append("Good boost management")
                    elif result.metric_name in ['saves']:
                        strengths.append("Strong defensive play")
        
        return strengths[:3]  # Return top 3 strengths
    
    def _extract_improvement_areas(self, all_insights: List) -> List[str]:
        """Extract primary improvement areas from insights.
        
        Args:
            all_insights: All coaching insights
            
        Returns:
            List of improvement area descriptions
        """
        improvement_areas = []
        
        # Group insights by metric and extract improvement themes
        priority_insights = sorted(all_insights, key=lambda x: x.priority)[:5]
        
        for insight in priority_insights:
            if insight.metric_name in ['avg_speed', 'time_supersonic_speed']:
                improvement_areas.append("Speed and mechanical execution")
            elif insight.metric_name in ['shooting_percentage']:
                improvement_areas.append("Shot accuracy and finishing")
            elif insight.metric_name in ['avg_amount', 'time_zero_boost']:
                improvement_areas.append("Boost management and efficiency")
            elif insight.metric_name in ['time_defensive_third', 'saves']:
                improvement_areas.append("Defensive positioning and awareness")
            elif insight.metric_name in ['avg_distance_to_ball', 'time_behind_ball']:
                improvement_areas.append("Positioning and rotation")
        
        # Remove duplicates while preserving order
        unique_areas = []
        for area in improvement_areas:
            if area not in unique_areas:
                unique_areas.append(area)
        
        return unique_areas[:3]  # Return top 3 improvement areas
    
    def _analyze_performance_trend(self, games_data: List[GameData]) -> Optional[str]:
        """Analyze recent performance trend.
        
        Args:
            games_data: Game data sorted by date
            
        Returns:
            Performance trend description or None
        """
        if len(games_data) < 6:
            return None
        
        # Sort by date to ensure chronological order
        sorted_games = sorted(games_data, key=lambda x: x.game_date)
        
        # Split into first half and second half
        mid_point = len(sorted_games) // 2
        first_half = sorted_games[:mid_point]
        second_half = sorted_games[mid_point:]
        
        # Calculate win rates for each half
        first_half_wins = sum(1 for game in first_half if game.game_result == GameResult.WIN)
        first_half_rate = first_half_wins / len(first_half)
        
        second_half_wins = sum(1 for game in second_half if game.game_result == GameResult.WIN)
        second_half_rate = second_half_wins / len(second_half)
        
        # Determine trend
        difference = second_half_rate - first_half_rate
        
        if difference > 0.2:
            return "improving"
        elif difference < -0.2:
            return "declining"
        else:
            return "stable"


# Singleton instance
_analysis_service: Optional[AnalysisService] = None


def get_analysis_service() -> AnalysisService:
    """Get the global analysis service instance."""
    global _analysis_service
    
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    
    return _analysis_service
