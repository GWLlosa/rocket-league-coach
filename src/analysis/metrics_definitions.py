"""Metric definitions and benchmarks for Rocket League coaching analysis."""

from typing import Dict, Any, List, NamedTuple
from enum import Enum


class MetricTier(Enum):
    """Metric confidence tiers based on causation evidence."""
    TIER_1 = "high_confidence"  # Strong causation evidence
    TIER_2 = "medium_confidence"  # Moderate causation evidence  
    TIER_3 = "correlation_only"  # Team-dependent, correlation analysis only


class MetricDefinition(NamedTuple):
    """Definition of a performance metric."""
    name: str
    display_name: str
    description: str
    tier: MetricTier
    unit: str
    format_string: str  # For display formatting
    higher_is_better: bool
    calculation_method: str  # Description of how it's calculated


# Core MVP Metrics Framework (12 metrics total)
METRIC_DEFINITIONS = {
    # Tier 1: High-Confidence Causal Metrics (6 metrics)
    "avg_speed": MetricDefinition(
        name="avg_speed",
        display_name="Average Speed",
        description="Average movement speed throughout the game",
        tier=MetricTier.TIER_1,
        unit="uu/s",
        format_string="{:.0f} uu/s",
        higher_is_better=True,
        calculation_method="Mean of all speed values during gameplay"
    ),
    
    "time_supersonic_speed": MetricDefinition(
        name="time_supersonic_speed",
        display_name="Supersonic Time",
        description="Time spent at maximum speed (2300 uu/s)",
        tier=MetricTier.TIER_1,
        unit="seconds",
        format_string="{:.1f}s ({:.1f}%)",
        higher_is_better=True,
        calculation_method="Time at speed >= 2300 uu/s"
    ),
    
    "shooting_percentage": MetricDefinition(
        name="shooting_percentage",
        display_name="Shooting Accuracy",
        description="Goals scored per shot taken",
        tier=MetricTier.TIER_1,
        unit="percentage",
        format_string="{:.1f}%",
        higher_is_better=True,
        calculation_method="(Goals / Shots) * 100, minimum 1 shot"
    ),
    
    "avg_amount": MetricDefinition(
        name="avg_amount",
        display_name="Average Boost",
        description="Average boost level maintained",
        tier=MetricTier.TIER_1,
        unit="boost",
        format_string="{:.0f}",
        higher_is_better=True,
        calculation_method="Mean boost amount throughout game"
    ),
    
    "time_zero_boost": MetricDefinition(
        name="time_zero_boost",
        display_name="Zero Boost Time",
        description="Time spent without boost",
        tier=MetricTier.TIER_1,
        unit="seconds",
        format_string="{:.1f}s ({:.1f}%)",
        higher_is_better=False,
        calculation_method="Time at 0 boost amount"
    ),
    
    "time_defensive_third": MetricDefinition(
        name="time_defensive_third",
        display_name="Defensive Positioning",
        description="Time spent in defensive zone",
        tier=MetricTier.TIER_1,
        unit="seconds",
        format_string="{:.1f}s ({:.1f}%)",
        higher_is_better=True,
        calculation_method="Time in defensive third of field"
    ),
    
    # Tier 2: Medium-Confidence Tactical Metrics (4 metrics)
    "avg_distance_to_ball": MetricDefinition(
        name="avg_distance_to_ball",
        display_name="Ball Proximity",
        description="Average distance from ball",
        tier=MetricTier.TIER_2,
        unit="uu",
        format_string="{:.0f} uu",
        higher_is_better=False,
        calculation_method="Mean distance to ball during gameplay"
    ),
    
    "time_behind_ball": MetricDefinition(
        name="time_behind_ball",
        display_name="Rotation Discipline",
        description="Time spent behind ball (rotation indicator)",
        tier=MetricTier.TIER_2,
        unit="seconds",
        format_string="{:.1f}s ({:.1f}%)",
        higher_is_better=True,
        calculation_method="Time positioned behind ball relative to goal"
    ),
    
    "amount_overfill": MetricDefinition(
        name="amount_overfill",
        display_name="Boost Efficiency",
        description="Boost wasted through overfill",
        tier=MetricTier.TIER_2,
        unit="boost",
        format_string="{:.0f}",
        higher_is_better=False,
        calculation_method="Total boost collected while already at 100"
    ),
    
    "saves": MetricDefinition(
        name="saves",
        display_name="Saves",
        description="Total saves per game",
        tier=MetricTier.TIER_2,
        unit="count",
        format_string="{:.0f}",
        higher_is_better=True,
        calculation_method="Official saves recorded by game"
    ),
    
    # Tier 3: Advanced Correlation Metrics (2 metrics)
    "time_most_back": MetricDefinition(
        name="time_most_back",
        display_name="Last Defender Time",
        description="Time spent as last defender",
        tier=MetricTier.TIER_3,
        unit="seconds",
        format_string="{:.1f}s ({:.1f}%)",
        higher_is_better=None,  # Context-dependent
        calculation_method="Time as furthest back teammate"
    ),
    
    "assists": MetricDefinition(
        name="assists",
        display_name="Assists",
        description="Assists per game",
        tier=MetricTier.TIER_3,
        unit="count",
        format_string="{:.0f}",
        higher_is_better=True,
        calculation_method="Official assists recorded by game"
    ),
}


# Rank-based performance benchmarks
RANK_BENCHMARKS = {
    "bronze": {
        "avg_speed": {"min": 800, "avg": 1000, "good": 1200},
        "time_supersonic_speed": {"min": 10, "avg": 25, "good": 40},
        "shooting_percentage": {"min": 8, "avg": 12, "good": 18},
        "avg_amount": {"min": 20, "avg": 35, "good": 50},
        "time_zero_boost": {"min": 80, "avg": 60, "good": 40},
        "time_defensive_third": {"min": 60, "avg": 80, "good": 100},
        "avg_distance_to_ball": {"min": 2500, "avg": 2200, "good": 1900},
        "saves": {"min": 0, "avg": 1, "good": 2},
    },
    "silver": {
        "avg_speed": {"min": 1000, "avg": 1200, "good": 1400},
        "time_supersonic_speed": {"min": 25, "avg": 40, "good": 60},
        "shooting_percentage": {"min": 10, "avg": 15, "good": 22},
        "avg_amount": {"min": 30, "avg": 45, "good": 60},
        "time_zero_boost": {"min": 60, "avg": 45, "good": 30},
        "time_defensive_third": {"min": 70, "avg": 90, "good": 110},
        "avg_distance_to_ball": {"min": 2200, "avg": 1900, "good": 1600},
        "saves": {"min": 0, "avg": 1, "good": 3},
    },
    "gold": {
        "avg_speed": {"min": 1200, "avg": 1400, "good": 1600},
        "time_supersonic_speed": {"min": 40, "avg": 60, "good": 80},
        "shooting_percentage": {"min": 12, "avg": 18, "good": 25},
        "avg_amount": {"min": 40, "avg": 55, "good": 70},
        "time_zero_boost": {"min": 45, "avg": 30, "good": 20},
        "time_defensive_third": {"min": 80, "avg": 100, "good": 120},
        "avg_distance_to_ball": {"min": 1900, "avg": 1600, "good": 1400},
        "saves": {"min": 1, "avg": 2, "good": 3},
    },
    "platinum": {
        "avg_speed": {"min": 1400, "avg": 1600, "good": 1800},
        "time_supersonic_speed": {"min": 60, "avg": 80, "good": 100},
        "shooting_percentage": {"min": 15, "avg": 22, "good": 30},
        "avg_amount": {"min": 50, "avg": 65, "good": 80},
        "time_zero_boost": {"min": 30, "avg": 20, "good": 15},
        "time_defensive_third": {"min": 90, "avg": 110, "good": 130},
        "avg_distance_to_ball": {"min": 1600, "avg": 1400, "good": 1200},
        "saves": {"min": 1, "avg": 2, "good": 4},
    },
    "diamond": {
        "avg_speed": {"min": 1600, "avg": 1800, "good": 2000},
        "time_supersonic_speed": {"min": 80, "avg": 100, "good": 120},
        "shooting_percentage": {"min": 18, "avg": 25, "good": 35},
        "avg_amount": {"min": 60, "avg": 75, "good": 90},
        "time_zero_boost": {"min": 20, "avg": 15, "good": 10},
        "time_defensive_third": {"min": 100, "avg": 120, "good": 140},
        "avg_distance_to_ball": {"min": 1400, "avg": 1200, "good": 1000},
        "saves": {"min": 1, "avg": 3, "good": 5},
    },
    "champion": {
        "avg_speed": {"min": 1800, "avg": 2000, "good": 2200},
        "time_supersonic_speed": {"min": 100, "avg": 120, "good": 140},
        "shooting_percentage": {"min": 22, "avg": 30, "good": 40},
        "avg_amount": {"min": 70, "avg": 85, "good": 95},
        "time_zero_boost": {"min": 15, "avg": 10, "good": 7},
        "time_defensive_third": {"min": 110, "avg": 130, "good": 150},
        "avg_distance_to_ball": {"min": 1200, "avg": 1000, "good": 850},
        "saves": {"min": 2, "avg": 3, "good": 5},
    },
    "grand_champion": {
        "avg_speed": {"min": 2000, "avg": 2200, "good": 2400},
        "time_supersonic_speed": {"min": 120, "avg": 140, "good": 160},
        "shooting_percentage": {"min": 25, "avg": 35, "good": 45},
        "avg_amount": {"min": 80, "avg": 90, "good": 95},
        "time_zero_boost": {"min": 10, "avg": 7, "good": 5},
        "time_defensive_third": {"min": 120, "avg": 140, "good": 160},
        "avg_distance_to_ball": {"min": 1000, "avg": 850, "good": 700},
        "saves": {"min": 2, "avg": 4, "good": 6},
    },
}


def get_metric_definition(metric_name: str) -> MetricDefinition:
    """Get metric definition by name."""
    if metric_name not in METRIC_DEFINITIONS:
        raise ValueError(f"Unknown metric: {metric_name}")
    return METRIC_DEFINITIONS[metric_name]


def get_metrics_by_tier(tier: MetricTier) -> List[MetricDefinition]:
    """Get all metrics for a specific tier."""
    return [metric for metric in METRIC_DEFINITIONS.values() if metric.tier == tier]


def get_rank_benchmark(rank: str, metric_name: str) -> Dict[str, float]:
    """Get benchmark values for a specific rank and metric."""
    rank = rank.lower().replace(" ", "_")
    if rank not in RANK_BENCHMARKS:
        # Default to platinum if rank not found
        rank = "platinum"
    
    if metric_name not in RANK_BENCHMARKS[rank]:
        return {"min": 0, "avg": 0, "good": 0}
    
    return RANK_BENCHMARKS[rank][metric_name]


def format_metric_value(metric_name: str, value: float, game_duration: float = None) -> str:
    """Format a metric value for display."""
    definition = get_metric_definition(metric_name)
    
    if "%" in definition.format_string and game_duration:
        # Calculate percentage for time-based metrics
        percentage = (value / game_duration) * 100 if game_duration > 0 else 0
        return definition.format_string.format(value, percentage)
    else:
        return definition.format_string.format(value)


def get_all_metric_names() -> List[str]:
    """Get list of all available metric names."""
    return list(METRIC_DEFINITIONS.keys())


def get_tier_1_metrics() -> List[str]:
    """Get list of Tier 1 (high confidence) metric names."""
    return [name for name, defn in METRIC_DEFINITIONS.items() if defn.tier == MetricTier.TIER_1]


def get_tier_2_metrics() -> List[str]:
    """Get list of Tier 2 (medium confidence) metric names."""
    return [name for name, defn in METRIC_DEFINITIONS.items() if defn.tier == MetricTier.TIER_2]


def get_tier_3_metrics() -> List[str]:
    """Get list of Tier 3 (correlation only) metric names."""
    return [name for name, defn in METRIC_DEFINITIONS.items() if defn.tier == MetricTier.TIER_3]


def is_valid_metric(metric_name: str) -> bool:
    """Check if a metric name is valid."""
    return metric_name in METRIC_DEFINITIONS


def get_metric_display_info(metric_name: str) -> Dict[str, Any]:
    """Get display information for a metric."""
    if not is_valid_metric(metric_name):
        return {}
    
    definition = get_metric_definition(metric_name)
    return {
        "name": definition.name,
        "display_name": definition.display_name,
        "description": definition.description,
        "tier": definition.tier.value,
        "unit": definition.unit,
        "higher_is_better": definition.higher_is_better,
        "calculation_method": definition.calculation_method,
    }
