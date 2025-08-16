"""Tests for the statistical analyzer module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.analysis.statistical_analyzer import StatisticalAnalyzer, CorrelationResult
from src.analysis.exceptions import InsufficientDataException
from src.analysis.metrics_definitions import MetricTier


class TestStatisticalAnalyzer:
    """Test statistical analysis functionality."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a test analyzer instance."""
        return StatisticalAnalyzer()
    
    @pytest.fixture
    def sample_games_data(self):
        """Create sample game data for testing."""
        games = []
        
        # Create 6 wins with higher avg_speed
        for i in range(6):
            games.append({
                'won': True,
                'metrics': {
                    'avg_speed': 1800 + (i * 10),  # 1800-1850
                    'shooting_percentage': 25.0 + (i * 2),  # 25-35%
                    'avg_amount': 70 + i,  # 70-75
                }
            })
        
        # Create 6 losses with lower avg_speed
        for i in range(6):
            games.append({
                'won': False,
                'metrics': {
                    'avg_speed': 1600 + (i * 10),  # 1600-1650
                    'shooting_percentage': 15.0 + (i * 2),  # 15-25%
                    'avg_amount': 50 + i,  # 50-55
                }
            })
        
        return games
    
    def test_separate_wins_losses(self, analyzer, sample_games_data):
        """Test separation of wins and losses."""
        wins, losses = analyzer._separate_wins_losses(sample_games_data)
        
        assert len(wins) == 6
        assert len(losses) == 6
        assert all(game['won'] for game in wins)
        assert all(not game['won'] for game in losses)
    
    def test_insufficient_wins_raises_exception(self, analyzer):
        """Test that insufficient wins raises exception."""
        games_data = [
            {'won': True, 'metrics': {'avg_speed': 1800}},  # Only 1 win
            {'won': False, 'metrics': {'avg_speed': 1600}},
            {'won': False, 'metrics': {'avg_speed': 1650}},
            {'won': False, 'metrics': {'avg_speed': 1700}},
            {'won': False, 'metrics': {'avg_speed': 1750}},
            {'won': False, 'metrics': {'avg_speed': 1800}},
        ]
        
        with pytest.raises(InsufficientDataException) as exc_info:
            analyzer.analyze_win_loss_correlations(games_data)
        
        assert "Insufficient wins" in str(exc_info.value)
    
    def test_insufficient_losses_raises_exception(self, analyzer):
        """Test that insufficient losses raises exception."""
        games_data = [
            {'won': False, 'metrics': {'avg_speed': 1600}},  # Only 1 loss
            {'won': True, 'metrics': {'avg_speed': 1800}},
            {'won': True, 'metrics': {'avg_speed': 1850}},
            {'won': True, 'metrics': {'avg_speed': 1900}},
            {'won': True, 'metrics': {'avg_speed': 1950}},
            {'won': True, 'metrics': {'avg_speed': 2000}},
        ]
        
        with pytest.raises(InsufficientDataException) as exc_info:
            analyzer.analyze_win_loss_correlations(games_data)
        
        assert "Insufficient losses" in str(exc_info.value)
    
    def test_extract_metrics_from_games(self, analyzer, sample_games_data):
        """Test metrics extraction from game data."""
        wins, losses = analyzer._separate_wins_losses(sample_games_data)
        wins_metrics = analyzer._extract_metrics_from_games(wins)
        
        assert 'avg_speed' in wins_metrics
        assert 'shooting_percentage' in wins_metrics
        assert len(wins_metrics['avg_speed']) == 6
        assert all(isinstance(val, float) for val in wins_metrics['avg_speed'])
    
    def test_cohens_d_calculation(self, analyzer):
        """Test Cohen's d effect size calculation."""
        group1 = np.array([20, 22, 24, 26, 28])  # Mean = 24
        group2 = np.array([10, 12, 14, 16, 18])  # Mean = 14
        
        cohens_d = analyzer._calculate_cohens_d(group1, group2)
        
        # Should be positive (group1 > group2) and substantial
        assert cohens_d > 0
        assert cohens_d > 1.0  # Large effect size
    
    def test_cohens_d_with_small_samples(self, analyzer):
        """Test Cohen's d with edge cases."""
        # Test with single values
        group1 = np.array([10])
        group2 = np.array([20])
        
        cohens_d = analyzer._calculate_cohens_d(group1, group2)
        assert cohens_d == 0.0  # Should return 0 for insufficient data
    
    def test_remove_outliers(self, analyzer):
        """Test outlier removal functionality."""
        # Data with outliers
        data = np.array([1, 2, 3, 4, 5, 100])  # 100 is an outlier
        
        clean_data = analyzer._remove_outliers(data)
        
        # Should remove the outlier
        assert 100 not in clean_data
        assert len(clean_data) < len(data)
    
    def test_determine_confidence_level(self, analyzer):
        """Test confidence level determination."""
        assert analyzer._determine_confidence_level(0.005) == "high"  # p < 0.01
        assert analyzer._determine_confidence_level(0.03) == "medium"  # 0.01 < p < 0.05
        assert analyzer._determine_confidence_level(0.1) == "low"  # p > 0.05
    
    def test_analyze_single_metric_significant(self, analyzer):
        """Test analysis of a single metric with significant difference."""
        # Wins have higher values
        wins_values = [1800, 1850, 1900, 1950, 2000]
        losses_values = [1400, 1450, 1500, 1550, 1600]
        
        result = analyzer._analyze_single_metric("avg_speed", wins_values, losses_values, 5)
        
        assert result is not None
        assert result.metric_name == "avg_speed"
        assert result.wins_mean > result.losses_mean
        assert result.effect_size > 0
        assert result.statistically_significant
    
    def test_analyze_single_metric_no_difference(self, analyzer):
        """Test analysis with no significant difference."""
        # Similar values in wins and losses
        wins_values = [1700, 1720, 1740, 1760, 1780]
        losses_values = [1710, 1730, 1750, 1770, 1790]
        
        result = analyzer._analyze_single_metric("avg_speed", wins_values, losses_values, 5)
        
        assert result is not None
        assert result.metric_name == "avg_speed"
        assert not result.statistically_significant
        assert abs(result.effect_size) < 0.5  # Small effect size
    
    def test_full_correlation_analysis(self, analyzer, sample_games_data):
        """Test complete correlation analysis workflow."""
        results = analyzer.analyze_win_loss_correlations(sample_games_data)
        
        assert isinstance(results, dict)
        assert 'avg_speed' in results
        assert 'shooting_percentage' in results
        
        # Check avg_speed result (should show wins > losses)
        avg_speed_result = results['avg_speed']
        assert avg_speed_result.wins_mean > avg_speed_result.losses_mean
        assert avg_speed_result.statistically_significant
        assert avg_speed_result.effect_size > 0
    
    def test_generate_correlation_insights(self, analyzer, sample_games_data):
        """Test insight generation from correlation results."""
        correlation_results = analyzer.analyze_win_loss_correlations(sample_games_data)
        insights = analyzer.generate_correlation_insights(correlation_results)
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        # Check insight structure
        insight = insights[0]
        assert 'metric_name' in insight
        assert 'display_name' in insight
        assert 'tier' in insight
        assert 'insight_message' in insight
        assert 'priority_score' in insight
    
    def test_insight_prioritization(self, analyzer, sample_games_data):
        """Test that insights are properly prioritized."""
        correlation_results = analyzer.analyze_win_loss_correlations(sample_games_data)
        insights = analyzer.generate_correlation_insights(correlation_results)
        
        # Should be sorted by priority score (highest first)
        for i in range(len(insights) - 1):
            assert insights[i]['priority_score'] >= insights[i + 1]['priority_score']
    
    def test_calculate_statistical_significance(self, analyzer):
        """Test statistical significance calculation."""
        wins = [25.0, 27.0, 29.0, 31.0, 33.0]
        losses = [15.0, 17.0, 19.0, 21.0, 23.0]
        
        result = analyzer.calculate_statistical_significance(wins, losses, "shooting_percentage")
        
        assert 'metric_name' in result
        assert 'wins_mean' in result
        assert 'losses_mean' in result
        assert 'p_value' in result
        assert 'effect_size' in result
        assert 'statistically_significant' in result
    
    def test_effect_size_calculation(self, analyzer):
        """Test effect size calculation."""
        wins = [100, 110, 120, 130, 140]
        losses = [60, 70, 80, 90, 100]
        
        effect_size = analyzer.calculate_effect_size(wins, losses)
        
        assert isinstance(effect_size, float)
        assert effect_size > 0  # Wins should be higher
        assert effect_size > 1.0  # Should be a large effect
    
    @patch('src.analysis.statistical_analyzer.get_metric_definition')
    def test_insight_message_generation(self, mock_get_definition, analyzer):
        """Test insight message generation."""
        # Mock metric definition
        mock_definition = Mock()
        mock_definition.display_name = "Average Speed"
        mock_definition.higher_is_better = True
        mock_definition.unit = "uu/s"
        mock_get_definition.return_value = mock_definition
        
        message = analyzer._generate_insight_message(
            "avg_speed", 1800, 1600, 1.2, "high"
        )
        
        assert isinstance(message, str)
        assert "Average Speed" in message or "average speed" in message
        assert "1800" in message
        assert "1600" in message
        assert "High confidence" in message
    
    def test_empty_games_data(self, analyzer):
        """Test behavior with empty games data."""
        with pytest.raises(InsufficientDataException):
            analyzer.analyze_win_loss_correlations([])
    
    def test_invalid_metric_values(self, analyzer):
        """Test handling of invalid metric values."""
        games_data = [
            {'won': True, 'metrics': {'avg_speed': float('nan')}},
            {'won': True, 'metrics': {'avg_speed': float('inf')}},
            {'won': True, 'metrics': {'avg_speed': None}},
            {'won': True, 'metrics': {'avg_speed': "invalid"}},
            {'won': True, 'metrics': {'avg_speed': 1800}},
            {'won': False, 'metrics': {'avg_speed': 1600}},
            {'won': False, 'metrics': {'avg_speed': 1650}},
            {'won': False, 'metrics': {'avg_speed': 1700}},
            {'won': False, 'metrics': {'avg_speed': 1750}},
            {'won': False, 'metrics': {'avg_speed': 1800}},
        ]
        
        # Should handle invalid values gracefully
        try:
            results = analyzer.analyze_win_loss_correlations(games_data)
            # If analysis succeeds, verify it filtered out invalid values
            if 'avg_speed' in results:
                result = results['avg_speed']
                assert not np.isnan(result.wins_mean)
                assert not np.isnan(result.losses_mean)
        except InsufficientDataException:
            # This is also acceptable if too many invalid values
            pass


class TestCorrelationResult:
    """Test CorrelationResult named tuple."""
    
    def test_correlation_result_creation(self):
        """Test creating CorrelationResult."""
        result = CorrelationResult(
            metric_name="avg_speed",
            wins_mean=1800.0,
            losses_mean=1600.0,
            wins_std=50.0,
            losses_std=45.0,
            effect_size=1.2,
            p_value=0.01,
            confidence_level="high",
            statistically_significant=True,
            practical_significance=True,
            sample_size_adequate=True,
            insight_message="Test message"
        )
        
        assert result.metric_name == "avg_speed"
        assert result.wins_mean == 1800.0
        assert result.statistically_significant
        assert result.confidence_level == "high"
    
    def test_correlation_result_fields(self):
        """Test all fields are accessible."""
        result = CorrelationResult(
            metric_name="test",
            wins_mean=0.0,
            losses_mean=0.0,
            wins_std=0.0,
            losses_std=0.0,
            effect_size=0.0,
            p_value=1.0,
            confidence_level="low",
            statistically_significant=False,
            practical_significance=False,
            sample_size_adequate=False,
            insight_message=""
        )
        
        # Verify all fields exist
        assert hasattr(result, 'metric_name')
        assert hasattr(result, 'wins_mean')
        assert hasattr(result, 'losses_mean')
        assert hasattr(result, 'wins_std')
        assert hasattr(result, 'losses_std')
        assert hasattr(result, 'effect_size')
        assert hasattr(result, 'p_value')
        assert hasattr(result, 'confidence_level')
        assert hasattr(result, 'statistically_significant')
        assert hasattr(result, 'practical_significance')
        assert hasattr(result, 'sample_size_adequate')
        assert hasattr(result, 'insight_message')


@pytest.mark.integration
class TestStatisticalAnalyzerIntegration:
    """Integration tests with real-like data."""
    
    def test_realistic_data_analysis(self):
        """Test with realistic Rocket League data."""
        analyzer = StatisticalAnalyzer()
        
        # Create realistic game data
        games_data = []
        
        # Wins: Higher speed, better shooting, more boost
        for i in range(8):
            games_data.append({
                'won': True,
                'metrics': {
                    'avg_speed': np.random.normal(1850, 50),
                    'shooting_percentage': np.random.normal(28, 5),
                    'avg_amount': np.random.normal(75, 8),
                    'time_zero_boost': np.random.normal(15, 5),
                    'saves': np.random.poisson(2),
                }
            })
        
        # Losses: Lower performance
        for i in range(7):
            games_data.append({
                'won': False,
                'metrics': {
                    'avg_speed': np.random.normal(1650, 50),
                    'shooting_percentage': np.random.normal(18, 5),
                    'avg_amount': np.random.normal(60, 8),
                    'time_zero_boost': np.random.normal(25, 5),
                    'saves': np.random.poisson(3),
                }
            })
        
        # Analyze
        results = analyzer.analyze_win_loss_correlations(games_data)
        
        # Should find some significant correlations
        assert len(results) > 0
        
        # Check that results have proper structure
        for metric_name, result in results.items():
            assert isinstance(result, CorrelationResult)
            assert result.metric_name == metric_name
            assert isinstance(result.p_value, float)
            assert isinstance(result.effect_size, float)
            assert isinstance(result.confidence_level, str)
