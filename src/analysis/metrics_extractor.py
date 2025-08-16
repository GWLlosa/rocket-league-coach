"""Metrics extraction from Rocket League replays using carball analysis."""

import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path

from carball.generated.api.game_pb2 import Game as ProtoGame
from carball.generated.api.player_pb2 import Player

from ..logging_config import get_logger, log_performance, LoggingMixin
from .exceptions import (
    MetricsExtractionException,
    PlayerNotFoundException,
    InvalidMetricException,
)
from .metrics_definitions import (
    get_all_metric_names,
    get_metric_definition,
    is_valid_metric,
    METRIC_DEFINITIONS,
)


class MetricsExtractor(LoggingMixin):
    """Extract performance metrics from carball protobuf game data."""
    
    def __init__(self):
        self.supported_metrics = get_all_metric_names()
    
    def extract_mvp_metrics(self, proto_game: ProtoGame, player_name: str) -> Dict[str, float]:
        """Extract all 12 MVP metrics for a specific player."""
        with log_performance(f"extract_metrics_{player_name}"):
            try:
                # Find the target player
                player = self._find_player(proto_game, player_name)
                if not player:
                    raise PlayerNotFoundException(player_name)
                
                # Extract all metrics
                metrics = {}
                
                # Game duration for percentage calculations
                game_duration = self._get_game_duration(proto_game)
                
                # Tier 1 Metrics (High Confidence)
                metrics.update(self._extract_tier_1_metrics(proto_game, player, game_duration))
                
                # Tier 2 Metrics (Medium Confidence)
                metrics.update(self._extract_tier_2_metrics(proto_game, player, game_duration))
                
                # Tier 3 Metrics (Correlation Only)
                metrics.update(self._extract_tier_3_metrics(proto_game, player, game_duration))
                
                # Validate all metrics were extracted
                missing_metrics = set(self.supported_metrics) - set(metrics.keys())
                if missing_metrics:
                    self.logger.warning(
                        "Some metrics could not be extracted",
                        player=player_name,
                        missing=list(missing_metrics)
                    )
                
                # Clean and validate metric values
                cleaned_metrics = self._clean_metric_values(metrics)
                
                self.logger.info(
                    "Metrics extraction completed",
                    player=player_name,
                    metrics_count=len(cleaned_metrics),
                    game_duration=game_duration
                )
                
                return cleaned_metrics
            
            except Exception as e:
                if isinstance(e, (PlayerNotFoundException, MetricsExtractionException)):
                    raise
                
                self.logger.error(
                    "Metrics extraction failed",
                    player=player_name,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise MetricsExtractionException(
                    f"Failed to extract metrics for {player_name}: {e}"
                )
    
    def _find_player(self, proto_game: ProtoGame, player_name: str) -> Optional[Player]:
        """Find player in game data."""
        if not proto_game.players:
            return None
        
        normalized_target = player_name.lower().strip()
        
        for player in proto_game.players:
            if not player.name:
                continue
            
            normalized_player = player.name.lower().strip()
            
            if normalized_player == normalized_target:
                return player
            
            # Partial match for platform names
            if normalized_target in normalized_player or normalized_player in normalized_target:
                return player
        
        return None
    
    def _get_game_duration(self, proto_game: ProtoGame) -> float:
        """Get game duration in seconds."""
        try:
            if hasattr(proto_game, 'game_info') and proto_game.game_info:
                return float(getattr(proto_game.game_info, 'length', 0))
            return 0.0
        except:
            return 0.0
    
    def _extract_tier_1_metrics(self, proto_game: ProtoGame, player: Player, game_duration: float) -> Dict[str, float]:
        """Extract Tier 1 (high confidence) metrics."""
        metrics = {}
        
        try:
            # avg_speed: Average movement speed
            if hasattr(player, 'stats') and hasattr(player.stats, 'speed'):
                speed_stats = player.stats.speed
                if hasattr(speed_stats, 'average_speed'):
                    metrics['avg_speed'] = float(speed_stats.average_speed)
                else:
                    metrics['avg_speed'] = 0.0
            else:
                metrics['avg_speed'] = 0.0
            
            # time_supersonic_speed: Time at maximum speed (2300 uu/s)
            if hasattr(player, 'stats') and hasattr(player.stats, 'speed'):
                speed_stats = player.stats.speed
                if hasattr(speed_stats, 'time_at_supersonic'):
                    metrics['time_supersonic_speed'] = float(speed_stats.time_at_supersonic)
                else:
                    metrics['time_supersonic_speed'] = 0.0
            else:
                metrics['time_supersonic_speed'] = 0.0
            
            # shooting_percentage: Goals per shot
            goals = float(getattr(player, 'goals', 0))
            shots = float(getattr(player, 'shots', 0))
            if shots > 0:
                metrics['shooting_percentage'] = (goals / shots) * 100
            else:
                metrics['shooting_percentage'] = 0.0
            
            # avg_amount: Average boost level
            if hasattr(player, 'stats') and hasattr(player.stats, 'boost'):
                boost_stats = player.stats.boost
                if hasattr(boost_stats, 'average_boost_level'):
                    metrics['avg_amount'] = float(boost_stats.average_boost_level)
                else:
                    metrics['avg_amount'] = 0.0
            else:
                metrics['avg_amount'] = 0.0
            
            # time_zero_boost: Time spent at 0 boost
            if hasattr(player, 'stats') and hasattr(player.stats, 'boost'):
                boost_stats = player.stats.boost
                if hasattr(boost_stats, 'time_zero_boost'):
                    metrics['time_zero_boost'] = float(boost_stats.time_zero_boost)
                else:
                    metrics['time_zero_boost'] = 0.0
            else:
                metrics['time_zero_boost'] = 0.0
            
            # time_defensive_third: Time in defensive zone
            if hasattr(player, 'stats') and hasattr(player.stats, 'positioning'):
                pos_stats = player.stats.positioning
                if hasattr(pos_stats, 'time_defensive_third'):
                    metrics['time_defensive_third'] = float(pos_stats.time_defensive_third)
                else:
                    metrics['time_defensive_third'] = 0.0
            else:
                metrics['time_defensive_third'] = 0.0
            
        except Exception as e:
            self.logger.warning(
                "Error extracting Tier 1 metrics",
                error=str(e),
                player=player.name if player else "unknown"
            )
        
        return metrics
    
    def _extract_tier_2_metrics(self, proto_game: ProtoGame, player: Player, game_duration: float) -> Dict[str, float]:
        """Extract Tier 2 (medium confidence) metrics."""
        metrics = {}
        
        try:
            # avg_distance_to_ball: Average distance from ball
            if hasattr(player, 'stats') and hasattr(player.stats, 'positioning'):
                pos_stats = player.stats.positioning
                if hasattr(pos_stats, 'average_distance_to_ball'):
                    metrics['avg_distance_to_ball'] = float(pos_stats.average_distance_to_ball)
                else:
                    metrics['avg_distance_to_ball'] = 0.0
            else:
                metrics['avg_distance_to_ball'] = 0.0
            
            # time_behind_ball: Time positioned behind ball
            if hasattr(player, 'stats') and hasattr(player.stats, 'positioning'):
                pos_stats = player.stats.positioning
                if hasattr(pos_stats, 'time_behind_ball'):
                    metrics['time_behind_ball'] = float(pos_stats.time_behind_ball)
                else:
                    metrics['time_behind_ball'] = 0.0
            else:
                metrics['time_behind_ball'] = 0.0
            
            # amount_overfill: Boost wasted through overfill
            if hasattr(player, 'stats') and hasattr(player.stats, 'boost'):
                boost_stats = player.stats.boost
                if hasattr(boost_stats, 'wasted_collection'):
                    metrics['amount_overfill'] = float(boost_stats.wasted_collection)
                else:
                    metrics['amount_overfill'] = 0.0
            else:
                metrics['amount_overfill'] = 0.0
            
            # saves: Total saves
            metrics['saves'] = float(getattr(player, 'saves', 0))
            
        except Exception as e:
            self.logger.warning(
                "Error extracting Tier 2 metrics",
                error=str(e),
                player=player.name if player else "unknown"
            )
        
        return metrics
    
    def _extract_tier_3_metrics(self, proto_game: ProtoGame, player: Player, game_duration: float) -> Dict[str, float]:
        """Extract Tier 3 (correlation only) metrics."""
        metrics = {}
        
        try:
            # time_most_back: Time as last defender
            if hasattr(player, 'stats') and hasattr(player.stats, 'positioning'):
                pos_stats = player.stats.positioning
                if hasattr(pos_stats, 'time_most_back'):
                    metrics['time_most_back'] = float(pos_stats.time_most_back)
                else:
                    metrics['time_most_back'] = 0.0
            else:
                metrics['time_most_back'] = 0.0
            
            # assists: Total assists
            metrics['assists'] = float(getattr(player, 'assists', 0))
            
        except Exception as e:
            self.logger.warning(
                "Error extracting Tier 3 metrics",
                error=str(e),
                player=player.name if player else "unknown"
            )
        
        return metrics
    
    def _clean_metric_values(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """Clean and validate metric values."""
        cleaned = {}
        
        for metric_name, value in metrics.items():
            try:
                # Convert to float and handle invalid values
                if isinstance(value, (int, float)):
                    clean_value = float(value)
                    
                    # Handle NaN and infinity
                    if np.isnan(clean_value) or np.isinf(clean_value):
                        clean_value = 0.0
                    
                    # Apply reasonable bounds
                    if metric_name == 'shooting_percentage':
                        clean_value = max(0.0, min(100.0, clean_value))
                    elif metric_name in ['avg_amount']:
                        clean_value = max(0.0, min(100.0, clean_value))
                    elif 'time_' in metric_name:
                        clean_value = max(0.0, clean_value)
                    else:
                        clean_value = max(0.0, clean_value)
                    
                    cleaned[metric_name] = clean_value
                else:
                    self.logger.warning(
                        "Invalid metric value type",
                        metric=metric_name,
                        value=value,
                        type=type(value).__name__
                    )
                    cleaned[metric_name] = 0.0
            
            except Exception as e:
                self.logger.warning(
                    "Error cleaning metric value",
                    metric=metric_name,
                    value=value,
                    error=str(e)
                )
                cleaned[metric_name] = 0.0
        
        return cleaned
    
    def extract_specific_metrics(
        self,
        proto_game: ProtoGame,
        player_name: str,
        metric_names: List[str]
    ) -> Dict[str, float]:
        """Extract only specific metrics."""
        # Validate metric names
        invalid_metrics = [name for name in metric_names if not is_valid_metric(name)]
        if invalid_metrics:
            raise InvalidMetricException(
                f"Invalid metrics: {invalid_metrics}",
                available_metrics=self.supported_metrics
            )
        
        # Extract all metrics first (more efficient than extracting individually)
        all_metrics = self.extract_mvp_metrics(proto_game, player_name)
        
        # Return only requested metrics
        return {name: all_metrics.get(name, 0.0) for name in metric_names}
    
    def validate_extracted_metrics(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Validate extracted metrics and return validation report."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'metrics_count': len(metrics),
            'missing_metrics': [],
            'invalid_values': []
        }
        
        # Check for missing core metrics
        expected_metrics = set(self.supported_metrics)
        actual_metrics = set(metrics.keys())
        missing = expected_metrics - actual_metrics
        
        if missing:
            validation['missing_metrics'] = list(missing)
            validation['warnings'].append(f"Missing metrics: {missing}")
        
        # Check for invalid values
        for metric_name, value in metrics.items():
            if not isinstance(value, (int, float)):
                validation['invalid_values'].append({
                    'metric': metric_name,
                    'value': value,
                    'issue': 'not_numeric'
                })
                validation['valid'] = False
            elif np.isnan(value) or np.isinf(value):
                validation['invalid_values'].append({
                    'metric': metric_name,
                    'value': value,
                    'issue': 'nan_or_inf'
                })
                validation['valid'] = False
            elif value < 0 and metric_name != 'shooting_percentage':  # Shooting % can be 0
                validation['warnings'].append(f"Negative value for {metric_name}: {value}")
        
        return validation


# Convenience function for creating extractor instances
def create_metrics_extractor() -> MetricsExtractor:
    """Create a configured metrics extractor."""
    return MetricsExtractor()
