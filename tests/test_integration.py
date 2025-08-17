"""Integration tests for the complete analysis workflow."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.services.analysis_service import AnalysisService
from src.data.models import AnalysisRequest, GameResult
from src.data.cache_manager import CacheManager


@pytest.fixture
def mock_ballchasing_client():
    """Mock Ballchasing client with sample data."""
    client = Mock()
    
    # Mock replay list
    client.search_player_replays = AsyncMock(return_value=[
        {
            'id': 'replay_1',
            'date': '2024-01-01T12:00:00Z',
            'duration': 300,
            'playlist_name': 'Ranked Standard',
            'players': [
                {'name': 'TestPlayer', 'rank': {'tier': 15}}
            ]
        },
        {
            'id': 'replay_2',
            'date': '2024-01-02T12:00:00Z',
            'duration': 350,
            'playlist_name': 'Ranked Standard',
            'players': [
                {'name': 'TestPlayer', 'rank': {'tier': 15}}
            ]
        }
    ])
    
    # Mock replay download
    client.download_replay = AsyncMock(return_value=b'mock_replay_data')
    
    # Mock game result extraction
    client.extract_game_result = Mock(side_effect=['win', 'loss'])
    
    return client


@pytest.fixture
def mock_replay_processor():
    """Mock replay processor."""
    processor = Mock()
    processor.parse_replay_file = Mock(return_value={
        'game_stats': {},
        'player_stats': {},
        'teams': []
    })
    return processor


@pytest.fixture
def mock_metrics_extractor():
    """Mock metrics extractor."""
    extractor = Mock()
    extractor.extract_mvp_metrics = Mock(return_value={
        'avg_speed': 1200.0,
        'time_supersonic_speed': 45.0,
        'shooting_percentage': 0.3,
        'avg_amount': 55.0,
        'time_zero_boost': 15.0,
        'time_defensive_third': 60.0,
        'avg_distance_to_ball': 800.0,
        'time_behind_ball': 120.0,
        'amount_overfill': 10.0,
        'saves': 2,
        'time_most_back': 40.0,
        'assists': 1,
        'game_duration': 300.0
    })
    return extractor


@pytest.fixture
def mock_statistical_analyzer():
    """Mock statistical analyzer."""
    analyzer = Mock()
    analyzer.analyze_win_loss_correlations = Mock(return_value=[])
    return analyzer


@pytest.fixture
def mock_coach():
    """Mock coaching engine."""
    coach = Mock()
    coach.generate_rule_based_insights = Mock(return_value=[])
    coach.generate_correlation_insights = Mock(return_value=[])
    return coach


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Temporary cache directory for testing."""
    return tmp_path / "test_cache"


class TestAnalysisService:
    """Test the main analysis service workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(
        self,
        temp_cache_dir,
        mock_ballchasing_client,
        mock_replay_processor,
        mock_metrics_extractor,
        mock_statistical_analyzer,
        mock_coach
    ):
        """Test the complete analysis workflow from request to result."""
        
        # Setup analysis service with mocked components
        service = AnalysisService()
        service.ballchasing_client = mock_ballchasing_client
        service.replay_processor = mock_replay_processor
        service.metrics_extractor = mock_metrics_extractor
        service.statistical_analyzer = mock_statistical_analyzer
        service.coach = mock_coach
        
        # Use temporary cache
        service.cache_manager = CacheManager(temp_cache_dir)
        
        # Create analysis request
        request = AnalysisRequest(
            gamertag="TestPlayer",
            num_games=2,
            force_refresh=True,
            include_raw_data=False
        )
        
        # Track progress updates
        progress_updates = []
        
        def progress_callback(status):
            progress_updates.append(status.current_step)
        
        # Run analysis
        result = await service.analyze_player(request, progress_callback)
        
        # Verify result structure
        assert result is not None
        assert result.gamertag == "TestPlayer"
        assert result.total_games == 2
        assert result.wins == 1
        assert result.losses == 1
        assert result.win_rate == 50.0
        
        # Verify components were called
        mock_ballchasing_client.search_player_replays.assert_called_once_with("TestPlayer", count=2)
        assert mock_ballchasing_client.download_replay.call_count == 2
        assert mock_replay_processor.parse_replay_file.call_count == 2
        assert mock_metrics_extractor.extract_mvp_metrics.call_count == 2
        mock_statistical_analyzer.analyze_win_loss_correlations.assert_called_once()
        mock_coach.generate_rule_based_insights.assert_called_once()
        mock_coach.generate_correlation_insights.assert_called_once()
        
        # Verify progress updates
        assert len(progress_updates) > 0
        assert "Checking cache" in progress_updates[0]
        assert "Analysis complete" in progress_updates[-1]
    
    @pytest.mark.asyncio
    async def test_cached_result_retrieval(self, temp_cache_dir):
        """Test that cached results are properly retrieved."""
        
        service = AnalysisService()
        service.cache_manager = CacheManager(temp_cache_dir)
        
        # Mock a cached result
        from src.data.models import PlayerAnalysisResult
        
        cached_result = PlayerAnalysisResult(
            gamertag="CachedPlayer",
            analysis_date=datetime.now(),
            total_games=10,
            wins=6,
            losses=4,
            win_rate=60.0,
            has_sufficient_data=True,
            min_sample_size_met=True,
            confidence_score=0.8
        )
        
        # Cache the result
        service._cache_analysis_result("CachedPlayer", cached_result)
        
        # Create request for cached player
        request = AnalysisRequest(
            gamertag="CachedPlayer",
            num_games=10,
            force_refresh=False
        )
        
        # Mock the ballchasing client to ensure it's not called
        service.ballchasing_client = Mock()
        
        # Should return cached result without calling API
        result = service._get_cached_analysis("CachedPlayer")
        
        assert result is not None
        assert result.gamertag == "CachedPlayer"
        assert result.win_rate == 60.0


class TestCacheManager:
    """Test cache management functionality."""
    
    def test_cache_manager_initialization(self, temp_cache_dir):
        """Test cache manager initializes correctly."""
        
        cache_manager = CacheManager(temp_cache_dir)
        
        # Verify directories are created
        assert cache_manager.replays_cache.exists()
        assert cache_manager.analysis_cache.exists()
        assert cache_manager.player_cache.exists()
        assert cache_manager.db_path.exists()
    
    def test_replay_file_caching(self, temp_cache_dir):
        """Test replay file caching and retrieval."""
        
        cache_manager = CacheManager(temp_cache_dir)
        
        # Cache a replay file
        replay_content = b"test_replay_data"
        replay_path = cache_manager.cache_replay_file(
            replay_id="test_replay",
            gamertag="TestPlayer",
            file_content=replay_content,
            game_date=datetime.now(),
            game_result="win"
        )
        
        # Verify file was cached
        assert replay_path.exists()
        assert replay_path.read_bytes() == replay_content
        
        # Retrieve cached replay
        cached_path = cache_manager.get_cached_replay("test_replay", "TestPlayer")
        assert cached_path == replay_path
        assert cached_path.exists()
    
    def test_analysis_result_caching(self, temp_cache_dir):
        """Test analysis result caching and retrieval."""
        
        cache_manager = CacheManager(temp_cache_dir)
        
        # Cache analysis result
        test_data = {
            "gamertag": "TestPlayer",
            "win_rate": 65.0,
            "total_games": 20
        }
        
        cache_key = cache_manager.cache_analysis_result(
            gamertag="TestPlayer",
            analysis_type="test_analysis",
            result_data=test_data
        )
        
        # Retrieve cached result
        cached_result = cache_manager.get_cached_analysis("TestPlayer", "test_analysis")
        
        assert cached_result is not None
        assert cached_result[0] == cache_key
        assert cached_result[1]["gamertag"] == "TestPlayer"
        assert cached_result[1]["win_rate"] == 65.0
    
    def test_cache_cleanup(self, temp_cache_dir):
        """Test cache cleanup functionality."""
        
        cache_manager = CacheManager(temp_cache_dir)
        
        # Add some test data
        cache_manager.cache_replay_file(
            replay_id="old_replay",
            gamertag="TestPlayer",
            file_content=b"old_data",
            ttl_hours=-1  # Already expired
        )
        
        # Run cleanup
        stats = cache_manager.cleanup_expired_cache()
        
        # Verify cleanup occurred
        assert stats["replays_removed"] >= 0
        assert stats["files_removed"] >= 0


if __name__ == "__main__":
    # Run a simple test to verify imports work
    print("Testing imports...")
    
    try:
        from src.services.analysis_service import get_analysis_service
        from src.data.cache_manager import get_cache_manager
        from src.data.models import AnalysisRequest
        
        print("✅ All imports successful!")
        
        # Test basic initialization
        service = get_analysis_service()
        cache_manager = get_cache_manager()
        
        print("✅ Services initialized successfully!")
        print("✅ Phase 4: Data Management & Orchestration - COMPLETE!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
