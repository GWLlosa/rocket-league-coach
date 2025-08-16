"""Main coaching engine that combines rule-based insights with correlation analysis."""

from typing import Dict, Any, List, Optional, Tuple
import asyncio

from ..logging_config import get_logger, log_performance, LoggingMixin
from .exceptions import InsufficientDataException
from .metrics_definitions import (
    get_rank_benchmark,
    get_metric_definition,
    get_all_metric_names,
    MetricTier,
)
from .statistical_analyzer import StatisticalAnalyzer, CorrelationResult
from .advice_templates import (
    format_rule_based_message,
    format_correlation_message,
    get_priority_phrase,
    format_insight_summary,
)


class CoachingInsight:
    """Represents a single coaching insight."""
    
    def __init__(
        self,
        insight_type: str,  # "rule_based" or "correlation"
        metric_name: str,
        title: str,
        message: str,
        priority_score: float,
        confidence_level: str = "medium",
        actionable_advice: str = "",
        training_recommendations: List[str] = None
    ):
        self.insight_type = insight_type
        self.metric_name = metric_name
        self.title = title
        self.message = message
        self.priority_score = priority_score
        self.confidence_level = confidence_level
        self.actionable_advice = actionable_advice
        self.training_recommendations = training_recommendations or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert insight to dictionary."""
        return {
            'type': self.insight_type,
            'metric_name': self.metric_name,
            'title': self.title,
            'message': self.message,
            'priority_score': self.priority_score,
            'confidence_level': self.confidence_level,
            'actionable_advice': self.actionable_advice,
            'training_recommendations': self.training_recommendations,
        }


class CoachingEngine(LoggingMixin):
    """Main coaching engine that generates personalized insights."""
    
    def __init__(self):
        self.statistical_analyzer = StatisticalAnalyzer()
    
    async def generate_coaching_insights(
        self,
        player_metrics: Dict[str, float],
        games_data: List[Dict[str, Any]],
        player_rank: str = "platinum"
    ) -> Dict[str, Any]:
        """Generate complete coaching analysis with both rule-based and correlation insights."""
        with log_performance(f"coaching_analysis_{len(games_data)}_games"):
            self.logger.info(
                "Starting coaching analysis",
                player_rank=player_rank,
                games_count=len(games_data),
                metrics_count=len(player_metrics)
            )
            
            # Generate rule-based insights
            rule_based_insights = self.generate_rule_based_insights(player_metrics, player_rank)
            
            # Generate correlation insights (if sufficient data)
            correlation_insights = []
            correlation_summary = {}
            
            try:
                correlation_results = self.statistical_analyzer.analyze_win_loss_correlations(games_data)
                correlation_insights = self._convert_correlations_to_insights(correlation_results)
                correlation_summary = self._generate_correlation_summary(correlation_results)
            except InsufficientDataException as e:
                self.logger.info(
                    "Insufficient data for correlation analysis",
                    error=str(e)
                )
                correlation_summary = {
                    'insufficient_data': True,
                    'message': str(e),
                    'recommendations': self._get_data_collection_advice(games_data)
                }
            except Exception as e:
                self.logger.error(
                    "Correlation analysis failed",
                    error=str(e)
                )
                correlation_summary = {
                    'error': True,
                    'message': "Correlation analysis encountered an error"
                }
            
            # Combine and prioritize all insights
            all_insights = rule_based_insights + correlation_insights
            prioritized_insights = self.prioritize_insights(all_insights)
            
            # Generate final coaching report
            coaching_report = {
                'player_rank': player_rank,
                'games_analyzed': len(games_data),
                'metrics_analyzed': len(player_metrics),
                'insights': {
                    'rule_based': [insight.to_dict() for insight in rule_based_insights],
                    'correlation': [insight.to_dict() for insight in correlation_insights],
                    'prioritized': [insight.to_dict() for insight in prioritized_insights[:10]]  # Top 10
                },
                'summary': {
                    'total_insights': len(all_insights),
                    'high_confidence': len([i for i in all_insights if i.confidence_level == 'high']),
                    'actionable_items': len([i for i in all_insights if i.actionable_advice]),
                    'correlation_analysis': correlation_summary,
                    'overview': self._generate_overview(prioritized_insights)
                },
                'recommendations': {
                    'immediate_focus': self._get_immediate_focus_areas(prioritized_insights[:3]),
                    'training_packs': self._consolidate_training_recommendations(all_insights),
                    'next_steps': self._generate_next_steps(games_data, all_insights)
                }
            }
            
            self.logger.info(
                "Coaching analysis completed",
                total_insights=len(all_insights),
                rule_based=len(rule_based_insights),
                correlation=len(correlation_insights),
                high_confidence=coaching_report['summary']['high_confidence']
            )
            
            return coaching_report
    
    def generate_rule_based_insights(
        self,
        player_metrics: Dict[str, float],
        player_rank: str
    ) -> List[CoachingInsight]:
        """Generate insights based on rank benchmarks."""
        insights = []
        
        for metric_name, value in player_metrics.items():
            try:
                if not value or value < 0:  # Skip invalid values
                    continue
                
                # Get rank benchmark
                benchmark = get_rank_benchmark(player_rank, metric_name)
                if not benchmark:
                    continue
                
                # Determine comparison level
                comparison = self._compare_to_benchmark(value, benchmark)
                
                # Generate insight
                insight = self._create_rule_based_insight(
                    metric_name, value, player_rank, comparison, benchmark
                )
                
                if insight:
                    insights.append(insight)
            
            except Exception as e:
                self.logger.warning(
                    "Failed to generate rule-based insight",
                    metric=metric_name,
                    error=str(e)
                )
        
        return insights
    
    def _compare_to_benchmark(self, value: float, benchmark: Dict[str, float]) -> str:
        """Compare metric value to rank benchmark."""
        min_val = benchmark.get('min', 0)
        avg_val = benchmark.get('avg', 0)
        good_val = benchmark.get('good', 0)
        
        if value < min_val:
            return "below_rank"
        elif value >= good_val:
            return "above_rank"
        else:
            return "at_rank"
    
    def _create_rule_based_insight(
        self,
        metric_name: str,
        value: float,
        rank: str,
        comparison: str,
        benchmark: Dict[str, float]
    ) -> Optional[CoachingInsight]:
        """Create a rule-based coaching insight."""
        try:
            definition = get_metric_definition(metric_name)
            
            # Calculate priority score based on deviation from benchmark
            priority_score = self._calculate_rule_based_priority(value, benchmark, comparison)
            
            # Generate message
            message = format_rule_based_message(metric_name, value, rank, comparison)
            
            # Determine confidence level (rule-based insights are generally medium confidence)
            confidence_level = "medium"
            
            # Generate actionable advice
            actionable_advice = self._generate_rule_based_advice(metric_name, comparison)
            
            # Create title
            priority_phrase = get_priority_phrase(priority_score)
            title = f"{priority_phrase}: {definition.display_name}"
            
            insight = CoachingInsight(
                insight_type="rule_based",
                metric_name=metric_name,
                title=title,
                message=message,
                priority_score=priority_score,
                confidence_level=confidence_level,
                actionable_advice=actionable_advice
            )
            
            return insight
        
        except Exception as e:
            self.logger.warning(
                "Failed to create rule-based insight",
                metric=metric_name,
                error=str(e)
            )
            return None
    
    def _calculate_rule_based_priority(
        self,
        value: float,
        benchmark: Dict[str, float],
        comparison: str
    ) -> float:
        """Calculate priority score for rule-based insight."""
        if comparison == "below_rank":
            # Higher priority for metrics significantly below rank
            min_val = benchmark.get('min', 0)
            if min_val > 0:
                deviation = (min_val - value) / min_val
                return min(70 + (deviation * 30), 100)  # 70-100 range
            return 70
        elif comparison == "above_rank":
            return 30  # Lower priority for things already good
        else:
            return 50  # Medium priority for at-rank performance
    
    def _generate_rule_based_advice(self, metric_name: str, comparison: str) -> str:
        """Generate actionable advice for rule-based insights."""
        if comparison == "below_rank":
            advice_map = {
                "avg_speed": "Focus on maintaining momentum through powerslide turns and efficient boost usage.",
                "shooting_percentage": "Practice shot accuracy in training packs and be more selective with shot attempts.",
                "avg_amount": "Improve boost collection routes and avoid wasteful supersonic driving.",
                "time_zero_boost": "Better boost management - collect boost more frequently and use it efficiently.",
                "saves": "Work on defensive positioning and anticipation to make more saves.",
            }
            return advice_map.get(metric_name, f"Focus on improving your {metric_name} through targeted practice.")
        elif comparison == "above_rank":
            return f"Maintain your strong {metric_name} performance while working on other areas."
        else:
            return f"Look for small optimizations in {metric_name} to gain an edge."
    
    def _convert_correlations_to_insights(
        self,
        correlation_results: Dict[str, CorrelationResult]
    ) -> List[CoachingInsight]:
        """Convert correlation results to coaching insights."""
        insights = []
        
        for result in correlation_results.values():
            try:
                if not result.statistically_significant:
                    continue
                
                definition = get_metric_definition(result.metric_name)
                
                # Calculate priority score
                priority_score = self._calculate_correlation_priority(result)
                
                # Generate message
                message = format_correlation_message(
                    result.metric_name,
                    result.wins_mean,
                    result.losses_mean,
                    result.confidence_level,
                    result.effect_size
                )
                
                # Create title
                priority_phrase = get_priority_phrase(priority_score)
                title = f"{priority_phrase}: {definition.display_name} Pattern"
                
                # Generate actionable advice
                actionable_advice = self._generate_correlation_advice(result)
                
                insight = CoachingInsight(
                    insight_type="correlation",
                    metric_name=result.metric_name,
                    title=title,
                    message=message,
                    priority_score=priority_score,
                    confidence_level=result.confidence_level,
                    actionable_advice=actionable_advice
                )
                
                insights.append(insight)
            
            except Exception as e:
                self.logger.warning(
                    "Failed to convert correlation to insight",
                    metric=result.metric_name,
                    error=str(e)
                )
        
        return insights
    
    def _calculate_correlation_priority(self, result: CorrelationResult) -> float:
        """Calculate priority score for correlation insight."""
        score = 0.0
        
        # Effect size contribution (0-40 points)
        score += min(abs(result.effect_size) * 20, 40)
        
        # Confidence contribution (0-30 points)
        if result.confidence_level == "high":
            score += 30
        elif result.confidence_level == "medium":
            score += 20
        else:
            score += 10
        
        # Tier contribution (0-20 points)
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
    
    def _generate_correlation_advice(self, result: CorrelationResult) -> str:
        """Generate actionable advice for correlation insights."""
        try:
            definition = get_metric_definition(result.metric_name)
            
            # Determine if the correlation is positive (wins are better)
            if definition.higher_is_better is True:
                wins_better = result.wins_mean > result.losses_mean
            elif definition.higher_is_better is False:
                wins_better = result.wins_mean < result.losses_mean
            else:
                wins_better = True  # Assume the pattern is meaningful
            
            if wins_better:
                return f"Maintain the {definition.display_name.lower()} level shown in your winning games."
            else:
                return f"Analyze what's different about your {definition.display_name.lower()} in winning vs losing games."
        
        except Exception:
            return "Review this metric's patterns between wins and losses."
    
    def prioritize_insights(self, insights: List[CoachingInsight]) -> List[CoachingInsight]:
        """Prioritize and sort insights by importance."""
        # Sort by priority score (highest first)
        sorted_insights = sorted(insights, key=lambda x: x.priority_score, reverse=True)
        
        # Boost correlation insights slightly if they're high confidence
        for insight in sorted_insights:
            if (insight.insight_type == "correlation" and 
                insight.confidence_level == "high" and
                insight.priority_score > 70):
                insight.priority_score = min(insight.priority_score + 5, 100)
        
        # Re-sort after adjustment
        return sorted(sorted_insights, key=lambda x: x.priority_score, reverse=True)
    
    def format_actionable_advice(self, insights: List[CoachingInsight]) -> Dict[str, Any]:
        """Format insights into actionable advice structure."""
        return {
            'immediate_focus': [
                insight.to_dict() for insight in insights[:3]
                if insight.priority_score >= 70
            ],
            'improvement_areas': [
                insight.to_dict() for insight in insights[3:8]
                if insight.priority_score >= 50
            ],
            'optimization_opportunities': [
                insight.to_dict() for insight in insights
                if 30 <= insight.priority_score < 50
            ]
        }
    
    def _generate_correlation_summary(self, correlation_results: Dict[str, CorrelationResult]) -> Dict[str, Any]:
        """Generate summary of correlation analysis."""
        if not correlation_results:
            return {'no_correlations': True}
        
        significant_count = sum(1 for r in correlation_results.values() if r.statistically_significant)
        high_confidence_count = sum(1 for r in correlation_results.values() if r.confidence_level == 'high')
        
        return {
            'total_analyzed': len(correlation_results),
            'significant_correlations': significant_count,
            'high_confidence_findings': high_confidence_count,
            'sample_size_adequate': all(r.sample_size_adequate for r in correlation_results.values()),
            'strongest_correlation': self._find_strongest_correlation(correlation_results)
        }
    
    def _find_strongest_correlation(self, correlation_results: Dict[str, CorrelationResult]) -> Dict[str, Any]:
        """Find the strongest correlation result."""
        if not correlation_results:
            return {}
        
        strongest = max(correlation_results.values(), key=lambda x: abs(x.effect_size))
        
        return {
            'metric_name': strongest.metric_name,
            'effect_size': strongest.effect_size,
            'p_value': strongest.p_value,
            'confidence_level': strongest.confidence_level
        }
    
    def _get_data_collection_advice(self, games_data: List[Dict[str, Any]]) -> List[str]:
        """Generate advice for collecting more data."""
        wins = len([g for g in games_data if g.get('won', False)])
        losses = len(games_data) - wins
        
        advice = []
        
        if wins < 5:
            advice.append(f"Play more ranked games to get at least 5 wins (currently have {wins})")
        
        if losses < 5:
            advice.append(f"Need at least 5 losses for analysis (currently have {losses})")
        
        if len(games_data) < 10:
            advice.append(f"Analyze more games for better insights (currently have {len(games_data)})")
        
        return advice
    
    def _generate_overview(self, prioritized_insights: List[CoachingInsight]) -> str:
        """Generate an overview of the analysis."""
        if not prioritized_insights:
            return "No significant insights found. Continue playing to gather more data."
        
        top_insight = prioritized_insights[0]
        correlation_count = len([i for i in prioritized_insights if i.insight_type == "correlation"])
        
        overview = f"Your strongest improvement opportunity is {top_insight.metric_name}."
        
        if correlation_count > 0:
            overview += f" Found {correlation_count} significant win/loss patterns."
        
        return overview
    
    def _get_immediate_focus_areas(self, top_insights: List[CoachingInsight]) -> List[str]:
        """Get immediate focus areas from top insights."""
        return [insight.actionable_advice for insight in top_insights if insight.actionable_advice]
    
    def _consolidate_training_recommendations(self, insights: List[CoachingInsight]) -> List[str]:
        """Consolidate training pack recommendations."""
        recommendations = set()
        for insight in insights:
            recommendations.update(insight.training_recommendations)
        return list(recommendations)[:5]  # Top 5
    
    def _generate_next_steps(self, games_data: List[Dict[str, Any]], insights: List[CoachingInsight]) -> List[str]:
        """Generate next steps for the player."""
        steps = []
        
        # Data collection steps
        if len(games_data) < 20:
            steps.append("Continue playing ranked games to improve analysis accuracy")
        
        # Focus area steps
        high_priority = [i for i in insights if i.priority_score >= 70]
        if high_priority:
            steps.append(f"Focus on improving {high_priority[0].metric_name}")
        
        # Training steps
        steps.append("Practice in training packs for 15-20 minutes before ranked sessions")
        
        return steps


# Convenience function for creating coach instances
def create_coaching_engine() -> CoachingEngine:
    """Create a configured coaching engine."""
    return CoachingEngine()
