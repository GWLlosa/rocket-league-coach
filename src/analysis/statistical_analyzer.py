"""Statistical analysis engine for win/loss correlation analysis."""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional, NamedTuple
from scipy import stats
from scipy.stats import ttest_ind
import warnings

from ..config import get_settings
from ..logging_config import get_logger, log_performance, LoggingMixin
from .exceptions import (
    StatisticalAnalysisException,
    InsufficientDataException,
)
from .metrics_definitions import (
    get_metric_definition,
    is_valid_metric,
    MetricTier,
)


class CorrelationResult(NamedTuple):
    """Result of win/loss correlation analysis for a single metric."""
    metric_name: str
    wins_mean: float
    losses_mean: float
    wins_std: float
    losses_std: float
    effect_size: float  # Cohen's d
    p_value: float
    confidence_level: str  # "high", "medium", "low"
    statistically_significant: bool
    practical_significance: bool
    sample_size_adequate: bool
    insight_message: str


class StatisticalAnalyzer(LoggingMixin):
    """Performs statistical analysis on game metrics for coaching insights."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Statistical thresholds
        self.min_sample_size = self.settings.min_sample_size_for_correlation
        self.significance_threshold = self.settings.statistical_significance_threshold
        self.effect_size_threshold = self.settings.effect_size_threshold
        
        # Confidence levels
        self.high_confidence_p = self.settings.confidence_level_high  # 0.01
        self.medium_confidence_p = self.settings.confidence_level_medium  # 0.05
        
        # Suppress scipy warnings for small samples
        warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    def analyze_win_loss_correlations(
        self,
        games_data: List[Dict[str, Any]],
        min_sample_size: Optional[int] = None
    ) -> Dict[str, CorrelationResult]:
        """Analyze win/loss correlations for all metrics."""
        min_size = min_sample_size or self.min_sample_size
        
        with log_performance("win_loss_correlation_analysis"):
            # Separate wins and losses
            wins_data, losses_data = self._separate_wins_losses(games_data)
            
            # Validate sample sizes
            self._validate_sample_sizes(wins_data, losses_data, min_size)
            
            # Extract metrics from game data
            wins_metrics = self._extract_metrics_from_games(wins_data)
            losses_metrics = self._extract_metrics_from_games(losses_data)
            
            # Analyze each metric
            results = {}
            available_metrics = set(wins_metrics.keys()) & set(losses_metrics.keys())
            
            self.logger.info(
                "Starting correlation analysis",
                wins_count=len(wins_data),
                losses_count=len(losses_data),
                metrics_count=len(available_metrics)
            )
            
            for metric_name in available_metrics:
                try:
                    if not is_valid_metric(metric_name):
                        continue
                    
                    wins_values = wins_metrics[metric_name]
                    losses_values = losses_metrics[metric_name]
                    
                    result = self._analyze_single_metric(
                        metric_name, wins_values, losses_values, min_size
                    )
                    
                    if result:
                        results[metric_name] = result
                
                except Exception as e:
                    self.logger.warning(
                        "Failed to analyze metric",
                        metric=metric_name,
                        error=str(e)
                    )
            
            self.logger.info(
                "Correlation analysis completed",
                analyzed_metrics=len(results),
                significant_findings=sum(1 for r in results.values() if r.statistically_significant)
            )
            
            return results
    
    def _separate_wins_losses(self, games_data: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """Separate games into wins and losses."""
        wins = []
        losses = []
        
        for game in games_data:
            if game.get('won', False):
                wins.append(game)
            else:
                losses.append(game)
        
        return wins, losses
    
    def _validate_sample_sizes(
        self,
        wins_data: List[Dict],
        losses_data: List[Dict],
        min_sample_size: int
    ):
        """Validate that sample sizes are adequate for analysis."""
        wins_count = len(wins_data)
        losses_count = len(losses_data)
        
        if wins_count < min_sample_size:
            raise InsufficientDataException(
                f"Insufficient wins for analysis. Need {min_sample_size}, have {wins_count}",
                required_count=min_sample_size,
                actual_count=wins_count
            )
        
        if losses_count < min_sample_size:
            raise InsufficientDataException(
                f"Insufficient losses for analysis. Need {min_sample_size}, have {losses_count}",
                required_count=min_sample_size,
                actual_count=losses_count
            )
    
    def _extract_metrics_from_games(self, games_data: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Extract metrics from list of games."""
        metrics = {}
        
        for game in games_data:
            game_metrics = game.get('metrics', {})
            
            for metric_name, value in game_metrics.items():
                if metric_name not in metrics:
                    metrics[metric_name] = []
                
                # Convert to float and handle invalid values
                try:
                    float_value = float(value)
                    if not (np.isnan(float_value) or np.isinf(float_value)):
                        metrics[metric_name].append(float_value)
                except (ValueError, TypeError):
                    continue
        
        return metrics
    
    def _analyze_single_metric(
        self,
        metric_name: str,
        wins_values: List[float],
        losses_values: List[float],
        min_sample_size: int
    ) -> Optional[CorrelationResult]:
        """Analyze a single metric for win/loss correlation."""
        try:
            # Check sample sizes
            if len(wins_values) < min_sample_size or len(losses_values) < min_sample_size:
                return None
            
            # Convert to numpy arrays
            wins_array = np.array(wins_values)
            losses_array = np.array(losses_values)
            
            # Remove outliers (beyond 3 standard deviations)
            wins_clean = self._remove_outliers(wins_array)
            losses_clean = self._remove_outliers(losses_array)
            
            # Recalculate means and standard deviations
            wins_mean = np.mean(wins_clean)
            losses_mean = np.mean(losses_clean)
            wins_std = np.std(wins_clean, ddof=1) if len(wins_clean) > 1 else 0
            losses_std = np.std(losses_clean, ddof=1) if len(losses_clean) > 1 else 0
            
            # Perform t-test (Welch's t-test for unequal variances)
            try:
                t_stat, p_value = ttest_ind(wins_clean, losses_clean, equal_var=False)
            except Exception:
                # Fallback for edge cases
                p_value = 1.0
                t_stat = 0.0
            
            # Calculate effect size (Cohen's d)
            effect_size = self._calculate_cohens_d(wins_clean, losses_clean)
            
            # Determine confidence level
            confidence_level = self._determine_confidence_level(p_value)
            
            # Check statistical significance
            statistically_significant = p_value < self.significance_threshold
            
            # Check practical significance
            practical_significance = abs(effect_size) >= self.effect_size_threshold
            
            # Check sample size adequacy
            sample_size_adequate = (
                len(wins_clean) >= min_sample_size and 
                len(losses_clean) >= min_sample_size
            )
            
            # Generate insight message
            insight_message = self._generate_insight_message(
                metric_name, wins_mean, losses_mean, effect_size, confidence_level
            )
            
            result = CorrelationResult(
                metric_name=metric_name,
                wins_mean=wins_mean,
                losses_mean=losses_mean,
                wins_std=wins_std,
                losses_std=losses_std,
                effect_size=effect_size,
                p_value=p_value,
                confidence_level=confidence_level,
                statistically_significant=statistically_significant,
                practical_significance=practical_significance,
                sample_size_adequate=sample_size_adequate,
                insight_message=insight_message
            )
            
            self.logger.debug(
                "Metric analysis completed",
                metric=metric_name,
                wins_mean=wins_mean,
                losses_mean=losses_mean,
                effect_size=effect_size,
                p_value=p_value,
                significant=statistically_significant
            )
            
            return result
        
        except Exception as e:
            self.logger.error(
                "Error analyzing metric",
                metric=metric_name,
                error=str(e)
            )
            return None
    
    def _remove_outliers(self, data: np.ndarray, z_threshold: float = 3.0) -> np.ndarray:
        """Remove outliers beyond z_threshold standard deviations."""
        if len(data) < 3:  # Need at least 3 points for meaningful outlier detection
            return data
        
        z_scores = np.abs(stats.zscore(data))
        return data[z_scores < z_threshold]
    
    def _calculate_cohens_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """Calculate Cohen's d effect size."""
        try:
            n1, n2 = len(group1), len(group2)
            
            if n1 < 2 or n2 < 2:
                return 0.0
            
            # Calculate means
            mean1, mean2 = np.mean(group1), np.mean(group2)
            
            # Calculate pooled standard deviation
            var1 = np.var(group1, ddof=1)
            var2 = np.var(group2, ddof=1)
            pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
            
            if pooled_std == 0:
                return 0.0
            
            # Cohen's d
            cohens_d = (mean1 - mean2) / pooled_std
            return cohens_d
        
        except Exception:
            return 0.0
    
    def _determine_confidence_level(self, p_value: float) -> str:
        """Determine confidence level based on p-value."""
        if p_value < self.high_confidence_p:
            return "high"
        elif p_value < self.medium_confidence_p:
            return "medium"
        else:
            return "low"
    
    def _generate_insight_message(
        self,
        metric_name: str,
        wins_mean: float,
        losses_mean: float,
        effect_size: float,
        confidence_level: str
    ) -> str:
        """Generate human-readable insight message."""
        try:
            definition = get_metric_definition(metric_name)
            display_name = definition.display_name
            higher_is_better = definition.higher_is_better
            
            # Calculate percentage difference
            if losses_mean != 0:
                pct_diff = abs((wins_mean - losses_mean) / losses_mean) * 100
            else:
                pct_diff = 0
            
            # Determine if the difference is in the expected direction
            if higher_is_better is True:
                good_direction = wins_mean > losses_mean
                direction_word = "higher" if good_direction else "lower"
            elif higher_is_better is False:
                good_direction = wins_mean < losses_mean
                direction_word = "lower" if good_direction else "higher"
            else:
                # Context-dependent metric
                good_direction = True
                direction_word = "different"
            
            # Format values for display
            if 'percentage' in definition.unit:
                wins_formatted = f"{wins_mean:.1f}%"
                losses_formatted = f"{losses_mean:.1f}%"
            elif 'time' in metric_name or 'speed' in metric_name:
                wins_formatted = f"{wins_mean:.1f}"
                losses_formatted = f"{losses_mean:.1f}"
            else:
                wins_formatted = f"{wins_mean:.0f}"
                losses_formatted = f"{losses_mean:.0f}"
            
            # Generate message based on significance
            if good_direction and pct_diff > 5:  # Meaningful difference in right direction
                message = (
                    f"In wins, your {display_name.lower()} averages {wins_formatted} "
                    f"vs {losses_formatted} in losses. "
                    f"This {direction_word} performance in wins suggests focusing on "
                    f"maintaining this level."
                )
            elif not good_direction and pct_diff > 5:  # Concerning pattern
                message = (
                    f"Your {display_name.lower()} is {direction_word} in wins "
                    f"({wins_formatted}) than losses ({losses_formatted}). "
                    f"This unexpected pattern may warrant investigation."
                )
            else:  # Small or no difference
                message = (
                    f"Your {display_name.lower()} shows minimal difference between "
                    f"wins ({wins_formatted}) and losses ({losses_formatted})."
                )
            
            # Add confidence qualifier
            if confidence_level == "high":
                message += " (High confidence)"
            elif confidence_level == "medium":
                message += " (Medium confidence)"
            else:
                message += " (Low confidence - more data needed)"
            
            return message
        
        except Exception as e:
            self.logger.warning(
                "Failed to generate insight message",
                metric=metric_name,
                error=str(e)
            )
            return f"Analysis available for {metric_name}"
    
    def calculate_statistical_significance(
        self,
        wins: List[float],
        losses: List[float],
        metric_name: str
    ) -> Dict[str, Any]:
        """Calculate statistical significance for a metric."""
        try:
            wins_array = np.array(wins)
            losses_array = np.array(losses)
            
            # Basic statistics
            wins_mean = np.mean(wins_array)
            losses_mean = np.mean(losses_array)
            wins_std = np.std(wins_array, ddof=1) if len(wins_array) > 1 else 0
            losses_std = np.std(losses_array, ddof=1) if len(losses_array) > 1 else 0
            
            # T-test
            t_stat, p_value = ttest_ind(wins_array, losses_array, equal_var=False)
            
            # Effect size
            effect_size = self._calculate_cohens_d(wins_array, losses_array)
            
            return {
                'metric_name': metric_name,
                'wins_mean': wins_mean,
                'losses_mean': losses_mean,
                'wins_std': wins_std,
                'losses_std': losses_std,
                't_statistic': t_stat,
                'p_value': p_value,
                'effect_size': effect_size,
                'statistically_significant': p_value < self.significance_threshold,
                'practical_significance': abs(effect_size) >= self.effect_size_threshold,
                'confidence_level': self._determine_confidence_level(p_value)
            }
        
        except Exception as e:
            raise StatisticalAnalysisException(
                f"Failed to calculate significance for {metric_name}: {e}",
                analysis_type="significance_test"
            )
    
    def calculate_effect_size(self, wins: List[float], losses: List[float]) -> float:
        """Calculate Cohen's d effect size between wins and losses."""
        wins_array = np.array(wins)
        losses_array = np.array(losses)
        return self._calculate_cohens_d(wins_array, losses_array)
    
    def generate_correlation_insights(
        self,
        correlations: Dict[str, CorrelationResult],
        confidence_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Generate prioritized list of correlation insights."""
        threshold = confidence_threshold or self.settings.correlation_threshold
        
        insights = []
        
        # Filter for significant and meaningful results
        significant_results = [
            result for result in correlations.values()
            if result.statistically_significant and result.practical_significance
        ]
        
        # Sort by effect size (strongest correlations first)
        significant_results.sort(key=lambda x: abs(x.effect_size), reverse=True)
        
        for result in significant_results:
            try:
                definition = get_metric_definition(result.metric_name)
                
                insight = {
                    'metric_name': result.metric_name,
                    'display_name': definition.display_name,
                    'tier': definition.tier.value,
                    'wins_mean': result.wins_mean,
                    'losses_mean': result.losses_mean,
                    'effect_size': result.effect_size,
                    'p_value': result.p_value,
                    'confidence_level': result.confidence_level,
                    'insight_message': result.insight_message,
                    'priority_score': self._calculate_priority_score(result),
                    'actionable_advice': self._generate_actionable_advice(result)
                }
                
                insights.append(insight)
            
            except Exception as e:
                self.logger.warning(
                    "Failed to generate insight",
                    metric=result.metric_name,
                    error=str(e)
                )
        
        # Sort by priority score
        insights.sort(key=lambda x: x['priority_score'], reverse=True)
        
        self.logger.info(
            "Generated correlation insights",
            total_insights=len(insights),
            high_confidence=sum(1 for i in insights if i['confidence_level'] == 'high')
        )
        
        return insights
    
    def _calculate_priority_score(self, result: CorrelationResult) -> float:
        """Calculate priority score for an insight (0-100)."""
        score = 0.0
        
        # Effect size contribution (0-40 points)
        effect_size_score = min(abs(result.effect_size) * 20, 40)
        score += effect_size_score
        
        # Confidence contribution (0-30 points)
        if result.confidence_level == "high":
            score += 30
        elif result.confidence_level == "medium":
            score += 20
        else:
            score += 10
        
        # Tier contribution (0-20 points) - higher tier = higher priority
        try:
            definition = get_metric_definition(result.metric_name)
            if definition.tier == MetricTier.TIER_1:
                score += 20
            elif definition.tier == MetricTier.TIER_2:
                score += 15
            else:
                score += 10
        except:
            score += 10
        
        # Practical significance bonus (0-10 points)
        if result.practical_significance:
            score += 10
        
        return min(score, 100)
    
    def _generate_actionable_advice(self, result: CorrelationResult) -> str:
        """Generate specific actionable advice based on correlation result."""
        try:
            definition = get_metric_definition(result.metric_name)
            display_name = definition.display_name.lower()
            
            # Determine if wins are better than losses
            if definition.higher_is_better is True:
                wins_better = result.wins_mean > result.losses_mean
            elif definition.higher_is_better is False:
                wins_better = result.wins_mean < result.losses_mean
            else:
                wins_better = True  # Assume pattern in wins is good
            
            if wins_better:
                advice = f"Focus on maintaining your winning {display_name} patterns. "
                
                # Specific advice based on metric
                if 'boost' in result.metric_name:
                    advice += "Practice boost management drills and avoid wasteful collection."
                elif 'speed' in result.metric_name:
                    advice += "Work on maintaining momentum and efficient movement."
                elif 'shooting' in result.metric_name:
                    advice += "Continue your shot selection discipline from winning games."
                elif 'positioning' in result.metric_name or 'defensive' in result.metric_name:
                    advice += "Maintain the defensive awareness shown in your wins."
                else:
                    advice += "Analyze your winning game replays to understand this pattern."
            else:
                advice = f"Your {display_name} pattern needs attention. "
                advice += "Review losing games to identify and correct this trend."
            
            return advice
        
        except Exception:
            return "Continue monitoring this metric for improvement opportunities."


# Convenience function for creating analyzer instances
def create_statistical_analyzer() -> StatisticalAnalyzer:
    """Create a configured statistical analyzer."""
    return StatisticalAnalyzer()
