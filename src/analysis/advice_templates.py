"""Coaching message templates for generating personalized advice."""

from typing import Dict, Any, List
from .metrics_definitions import get_metric_definition


# Rule-based coaching templates
RULE_BASED_TEMPLATES = {
    # Tier 1 Metrics
    "avg_speed": {
        "below_rank": "Your movement speed ({value}) is below average for {rank}. Focus on maintaining momentum and avoiding unnecessary stops. Practice powerslide cuts and boost management to maintain speed.",
        "at_rank": "Your movement speed ({value}) is typical for {rank}. Consider working on advanced movement techniques to gain an edge.",
        "above_rank": "Excellent movement speed ({value}) for {rank}! This mechanical advantage should help in challenges and rotations."
    },
    
    "time_supersonic_speed": {
        "below_rank": "You're spending less time at supersonic speed ({value}s) than typical {rank} players. Work on boost efficiency and momentum conservation to maintain maximum speed.",
        "at_rank": "Your supersonic time ({value}s) is appropriate for {rank}. Focus on using this speed effectively for rotation and challenges.",
        "above_rank": "Great supersonic time ({value}s) for {rank}! Make sure you're using this speed strategically, not just for ball chasing."
    },
    
    "shooting_percentage": {
        "below_rank": "Your shooting accuracy ({value}%) needs improvement for {rank}. Focus on shot placement over power, and only shoot when you have a clear angle.",
        "at_rank": "Your shooting accuracy ({value}%) is solid for {rank}. Work on more advanced shot techniques and placement.",
        "above_rank": "Excellent shooting accuracy ({value}%) for {rank}! Your shot selection and execution are strong assets."
    },
    
    "avg_amount": {
        "below_rank": "Your average boost level ({value}) is low for {rank}. Focus on collecting boost more efficiently and avoiding wasteful supersonic driving.",
        "at_rank": "Your boost management ({value} average) is typical for {rank}. Look for opportunities to optimize collection routes.",
        "above_rank": "Great boost management ({value} average) for {rank}! This should give you more options in challenging situations."
    },
    
    "time_zero_boost": {
        "below_rank": "You're managing boost well (only {value}s at zero). Continue this discipline to maintain your options.",
        "at_rank": "Your zero boost time ({value}s) is reasonable for {rank}. Look for small optimizations in boost usage.",
        "above_rank": "You're spending too much time without boost ({value}s). This limits your options - focus on better boost collection and conservation."
    },
    
    "time_defensive_third": {
        "below_rank": "You're not spending enough time in defense ({value}s). Work on rotation discipline and getting back to goal when appropriate.",
        "at_rank": "Your defensive positioning time ({value}s) is balanced for {rank}. Focus on quality over quantity in defensive plays.",
        "above_rank": "Good defensive awareness ({value}s spent defending) for {rank}. Make sure you're also contributing to offense when opportunities arise."
    },
    
    # Tier 2 Metrics
    "avg_distance_to_ball": {
        "below_rank": "You're staying very close to the ball ({value} units). Consider giving more space for better touches and rotation.",
        "at_rank": "Your ball distance ({value} units) is reasonable for {rank}. Focus on positioning for quality touches.",
        "above_rank": "You might be too far from plays ({value} units). Look for opportunities to get involved while maintaining good rotation."
    },
    
    "saves": {
        "below_rank": "Few saves ({value}) might indicate positioning issues or teammates covering for you. Work on defensive awareness.",
        "at_rank": "Your save count ({value}) is typical for {rank}. Focus on making clean saves that start counterattacks.",
        "above_rank": "High save count ({value}) shows good defensive involvement. Make sure your saves are leading to clear advantages."
    },
    
    # Training pack recommendations
    "training_packs": {
        "shooting_percentage": [
            "Ultimate Shooting by Poquito",
            "Ground Shots by Wayprotein", 
            "Redirects by IP Joker"
        ],
        "avg_speed": [
            "Speed Jump Reset by Musty",
            "Air Roll Shots by CBell",
            "Fast Aerial Practice"
        ],
        "saves": [
            "Saves Pack by Browser",
            "Defensive Training by Sunless",
            "Awkward Saves by Poquito"
        ]
    }
}


# Correlation insight templates
CORRELATION_TEMPLATES = {
    "positive_correlation": "In your wins, you average {wins_value} vs {losses_value} in losses. This {metric_name} advantage in wins suggests maintaining this level is key to your success.",
    
    "negative_correlation": "Your {metric_name} is actually lower in wins ({wins_value}) than losses ({losses_value}). This suggests less is more for your playstyle.",
    
    "unexpected_pattern": "Interesting pattern: your {metric_name} shows {wins_value} in wins vs {losses_value} in losses. This unexpected correlation may reveal something unique about your playstyle.",
    
    "minimal_difference": "Your {metric_name} is consistent between wins and losses ({wins_value} vs {losses_value}). This metric might not be a key factor for your improvement.",
}


# Confidence level modifiers
CONFIDENCE_MODIFIERS = {
    "high": " (High confidence - strong statistical evidence)",
    "medium": " (Medium confidence - moderate evidence)", 
    "low": " (Low confidence - more data needed for certainty)"
}


# Priority phrases for organizing insights
PRIORITY_PHRASES = {
    "critical": "🔥 Critical Focus Area",
    "important": "⚡ Important Improvement", 
    "moderate": "📈 Growth Opportunity",
    "minor": "💡 Minor Optimization"
}


def get_training_pack_recommendations(metric_name: str) -> List[str]:
    """Get training pack recommendations for a specific metric."""
    return RULE_BASED_TEMPLATES.get("training_packs", {}).get(metric_name, [])


def format_rule_based_message(
    metric_name: str, 
    value: float, 
    rank: str, 
    comparison: str,
    include_training: bool = True
) -> str:
    """Format a rule-based coaching message."""
    templates = RULE_BASED_TEMPLATES.get(metric_name, {})
    
    if comparison not in templates:
        return f"Your {metric_name} is {value}. Continue monitoring this metric."
    
    # Get the base message template
    message = templates[comparison].format(value=value, rank=rank)
    
    # Add training recommendations if requested and available
    if include_training and comparison == "below_rank":
        training_packs = get_training_pack_recommendations(metric_name)
        if training_packs:
            message += f"\n\nRecommended training: {', '.join(training_packs[:2])}"
    
    return message


def format_correlation_message(
    metric_name: str,
    wins_value: float,
    losses_value: float,
    confidence_level: str,
    effect_size: float
) -> str:
    """Format a correlation-based coaching message."""
    try:
        definition = get_metric_definition(metric_name)
        display_name = definition.display_name
        
        # Determine template based on correlation direction and magnitude
        if abs(effect_size) < 0.2:
            template_key = "minimal_difference"
        elif (definition.higher_is_better and wins_value > losses_value) or \
             (not definition.higher_is_better and wins_value < losses_value):
            template_key = "positive_correlation"
        elif (definition.higher_is_better and wins_value < losses_value) or \
             (not definition.higher_is_better and wins_value > losses_value):
            template_key = "negative_correlation"
        else:
            template_key = "unexpected_pattern"
        
        # Format values appropriately
        if 'percentage' in definition.unit:
            wins_formatted = f"{wins_value:.1f}%"
            losses_formatted = f"{losses_value:.1f}%"
        elif 'time' in metric_name:
            wins_formatted = f"{wins_value:.1f}s"
            losses_formatted = f"{losses_value:.1f}s"
        else:
            wins_formatted = f"{wins_value:.0f}"
            losses_formatted = f"{losses_value:.0f}"
        
        # Generate message
        message = CORRELATION_TEMPLATES[template_key].format(
            metric_name=display_name.lower(),
            wins_value=wins_formatted,
            losses_value=losses_formatted
        )
        
        # Add confidence modifier
        message += CONFIDENCE_MODIFIERS.get(confidence_level, "")
        
        return message
    
    except Exception:
        return f"Correlation found for {metric_name}: wins avg {wins_value:.1f}, losses avg {losses_value:.1f}"


def get_priority_phrase(priority_score: float) -> str:
    """Get priority phrase based on score."""
    if priority_score >= 80:
        return PRIORITY_PHRASES["critical"]
    elif priority_score >= 60:
        return PRIORITY_PHRASES["important"]
    elif priority_score >= 40:
        return PRIORITY_PHRASES["moderate"]
    else:
        return PRIORITY_PHRASES["minor"]


def format_insight_summary(insights: List[Dict[str, Any]]) -> str:
    """Format a summary of all insights."""
    if not insights:
        return "No significant insights found. Continue playing and gathering data."
    
    high_confidence = [i for i in insights if i.get('confidence_level') == 'high']
    medium_confidence = [i for i in insights if i.get('confidence_level') == 'medium']
    
    summary = f"📊 Found {len(insights)} insights"
    
    if high_confidence:
        summary += f" ({len(high_confidence)} high confidence"
        if medium_confidence:
            summary += f", {len(medium_confidence)} medium confidence)"
        else:
            summary += ")"
    elif medium_confidence:
        summary += f" ({len(medium_confidence)} medium confidence)"
    
    return summary
