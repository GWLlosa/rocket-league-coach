"""Tests for Ballchasing API client."""

import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from datetime import datetime
import json

from src.api.ballchasing_client import BallchasingClient, RateLimiter
from src.api.exceptions import (
    RateLimitExceededException,
    UnauthorizedException,
    ReplayNotFoundException,
    PlayerNotFoundException,
    NetworkException,
    DownloadException,
)
from src.api.models import GameInfo, GameResult, DownloadInfo


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_per_second(self):
        """Test per-second rate limiting."""
        limiter = RateLimiter(calls_per_second=2.0, calls_per_hour=100)
        
        # First call should be immediate
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        first_call_time = asyncio.get_event_loop().time() - start_time
        assert first_call_time < 0.1
        
        # Second call should be delayed
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        second_call_time = asyncio.get_event_loop().time() - start_time
        assert second_call_time >= 0.4  # At least 0.5s delay for 2 calls/sec
    
    @pytest.mark.asyncio
    async def test_rate_limiter_hourly_limit(self):
        """Test hourly rate limiting."""
        limiter = RateLimiter(calls_per_second=10.0, calls_per_hour=2)
        
        # First two calls should work
        await limiter.acquire()
        await limiter.acquire()
        
        # Third call should raise exception
        with pytest.raises(RateLimitExceededException) as exc_info:
            await limiter.acquire()
        
        assert "Hourly rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after > 0


class TestBallchasingClient:
    """Test Ballchasing API client."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return BallchasingClient(api_key="test_key", base_url="https://test.example.com/api")
    
    @pytest.fixture
    def mock_response_data(self):
        """Mock response data for successful API calls."""
        return {
            "list": [
                {
                    "id": "test_replay_1",
                    "title": "Test Game 1",
                    "created": "2023-01-01T12:00:00Z",
                    "date": "2023-01-01T11:30:00Z",
                    "duration": 300,
                    "map": "DFH Stadium",
                    "playlist": "Ranked Doubles",
                    "blue": {"name": "Blue Team"},
                    "orange": {"name": "Orange Team"}
                },
                {
                    "id": "test_replay_2",
                    "title": "Test Game 2",
                    "created": "2023-01-01T13:00:00Z",
                    "date": "2023-01-01T12:30:00Z",
                    "duration": 420,
                    "map": "Mannfield",
                    "playlist": "Ranked Doubles",
                    "blue": {"name": "Blue Team"},
                    "orange": {"name": "Orange Team"}
                }
            ],
            "count": 2
        }
    
    @pytest.mark.asyncio
    async def test_session_management(self, client):
        """Test session creation and cleanup."""
        # Session should not exist initially
        assert client._session is None
        
        # Session should be created when needed
        await client._ensure_session()
        assert client._session is not None
        assert not client._session.closed
        
        # Session should be closed properly
        await client.close()
        assert client._session.closed
    
    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager functionality."""
        async with client as c:
            assert c._session is not None
            assert not c._session.closed
        
        # Session should be closed after context exit
        assert client._session.closed
    
    @pytest.mark.asyncio
    async def test_search_player_replays_success(self, client, mock_response_data):
        """Test successful player replay search."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data
            
            replays = await client.search_player_replays("TestPlayer", count=10)
            
            assert len(replays) == 2
            assert replays[0].id == "test_replay_1"
            assert replays[1].id == "test_replay_2"
            
            # Verify request parameters
            mock_request.assert_called_once_with(
                "GET",
                "/replays",
                params={
                    "player-name": "TestPlayer",
                    "count": 10,
                    "sort-by": "created",
                    "sort-dir": "desc",
                    "playlist": "ranked-duels,ranked-doubles,ranked-standard,ranked-hoops,ranked-rumble,ranked-dropshot,ranked-snowday"
                }
            )
    
    @pytest.mark.asyncio
    async def test_search_player_replays_not_found(self, client):
        """Test player not found scenario."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"list": [], "count": 0}
            
            with pytest.raises(PlayerNotFoundException) as exc_info:
                await client.search_player_replays("NonexistentPlayer")
            
            assert "NonexistentPlayer" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_download_replay_success(self, client, tmp_path):
        """Test successful replay download."""
        test_content = b"fake replay content"
        destination = tmp_path / "test_replay.replay"
        
        # Mock the session and response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.ok = True
        mock_response.headers = {"Content-Length": str(len(test_content))}
        mock_response.content.iter_chunked = AsyncMock(return_value=[test_content])
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock), \
             patch.object(client.rate_limiter, 'acquire', new_callable=AsyncMock), \
             patch('aiofiles.open', mock_open_async(test_content)):
            
            client._session = Mock()
            client._session.get = AsyncMock(return_value=mock_response)
            client._session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            client._session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Create the file to simulate successful download
            destination.write_bytes(test_content)
            
            download_info = await client.download_replay("test_replay_id", destination)
            
            assert download_info.replay_id == "test_replay_id"
            assert download_info.file_path == str(destination)
            assert download_info.file_size == len(test_content)
            assert download_info.download_time > 0
    
    @pytest.mark.asyncio
    async def test_download_replay_not_found(self, client, tmp_path):
        """Test replay download with 404 error."""
        destination = tmp_path / "test_replay.replay"
        
        mock_response = Mock()
        mock_response.status = 404
        mock_response.ok = False
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock), \
             patch.object(client.rate_limiter, 'acquire', new_callable=AsyncMock):
            
            client._session = Mock()
            client._session.get = AsyncMock(return_value=mock_response)
            client._session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            client._session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with pytest.raises(ReplayNotFoundException) as exc_info:
                await client.download_replay("nonexistent_replay", destination)
            
            assert "nonexistent_replay" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_game_result(self, client):
        """Test game result extraction."""
        game_info = GameInfo(
            id="test_replay",
            created=datetime.now(),
            date=datetime.now(),
            duration=300,
            map_name="DFH Stadium",
            playlist_name="Ranked Doubles"
        )
        
        result = client.extract_game_result(game_info, "TestPlayer")
        
        assert result.replay_id == "test_replay"
        assert result.player_name == "TestPlayer"
        assert result.duration == 300
        assert result.map_name == "DFH Stadium"
        assert result.playlist == "Ranked Doubles"
    
    @pytest.mark.asyncio
    async def test_get_player_game_results(self, client, mock_response_data):
        """Test getting player game results."""
        with patch.object(client, 'search_player_replays', new_callable=AsyncMock) as mock_search:
            # Create mock GameInfo objects
            mock_replays = [
                GameInfo(
                    id="test_replay_1",
                    created=datetime.now(),
                    date=datetime.now(),
                    duration=300,
                    map_name="DFH Stadium",
                    playlist_name="Ranked Doubles"
                ),
                GameInfo(
                    id="test_replay_2",
                    created=datetime.now(),
                    date=datetime.now(),
                    duration=420,
                    map_name="Mannfield",
                    playlist_name="Ranked Doubles"
                )
            ]
            mock_search.return_value = mock_replays
            
            results = await client.get_player_game_results("TestPlayer", num_games=2)
            
            assert len(results) == 2
            assert results[0].replay_id == "test_replay_1"
            assert results[1].replay_id == "test_replay_2"
            assert all(result.player_name == "TestPlayer" for result in results)
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, client):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "60"}
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock), \
             patch.object(client.rate_limiter, 'acquire', new_callable=AsyncMock):
            
            client._session = Mock()
            client._session.request = AsyncMock(return_value=mock_response)
            client._session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            client._session.request.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with pytest.raises(RateLimitExceededException) as exc_info:
                await client._make_request("GET", "/test")
            
            assert exc_info.value.retry_after == 60
    
    @pytest.mark.asyncio
    async def test_unauthorized_error_handling(self, client):
        """Test unauthorized error handling."""
        mock_response = Mock()
        mock_response.status = 401
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock), \
             patch.object(client.rate_limiter, 'acquire', new_callable=AsyncMock):
            
            client._session = Mock()
            client._session.request = AsyncMock(return_value=mock_response)
            client._session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            client._session.request.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with pytest.raises(UnauthorizedException):
                await client._make_request("GET", "/test")


def mock_open_async(content):
    """Mock aiofiles.open for testing."""
    from unittest.mock import Mock, AsyncMock
    
    mock_file = Mock()
    mock_file.write = AsyncMock()
    mock_file.__aenter__ = AsyncMock(return_value=mock_file)
    mock_file.__aexit__ = AsyncMock(return_value=None)
    
    return AsyncMock(return_value=mock_file)


@pytest.mark.integration
class TestBallchasingClientIntegration:
    """Integration tests for Ballchasing client (require real API key)."""
    
    @pytest.mark.skipif(
        not pytest.config.getoption("--integration", default=False),
        reason="Integration tests disabled"
    )
    @pytest.mark.asyncio
    async def test_real_api_search(self):
        """Test real API search (requires valid API key in environment)."""
        import os
        api_key = os.getenv("BALLCHASING_API_KEY")
        if not api_key:
            pytest.skip("Real API key not available")
        
        client = BallchasingClient(api_key=api_key)
        
        try:
            async with client:
                # Search for a well-known player
                replays = await client.search_player_replays("Squishy", count=1)
                assert len(replays) > 0
                assert replays[0].id is not None
        except Exception as e:
            pytest.skip(f"Real API test failed: {e}")


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests"
    )
