"""Ballchasing API client with rate limiting and async operations."""

import asyncio
import aiohttp
import aiofiles
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import time

from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type
)

import ballchasing
from .exceptions import (
    BallchasingAPIError, 
    RateLimitError, 
    ReplayNotFoundError, 
    AuthenticationError
)
from .models import ReplaySearchResult, ReplayMetadata
from ..config import get_settings
from ..logging_config import get_logger

logger = get_logger(__name__)


class BallchasingClient:
    """Async client for Ballchasing.com API with rate limiting and caching."""
    
    def __init__(self, api_token: Optional[str] = None):
        """Initialize the Ballchasing client.
        
        Args:
            api_token: Optional API token. If None, uses config setting.
        """
        self.settings = get_settings()
        self.api_token = api_token or self.settings.ballchasing_api_token
        
        if not self.api_token:
            raise AuthenticationError("Ballchasing API token is required")
        
        # Initialize the ballchasing API client
        self.api = ballchasing.Api(self.api_token)
        
        # Rate limiting configuration
        self.rate_limit_per_second = 2.0  # 2 requests per second
        self.rate_limit_per_hour = 500    # 500 requests per hour
        self.last_request_time = 0.0
        self.hourly_request_count = 0
        self.hourly_window_start = time.time()
        
        # Session for async requests
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info("Ballchasing client initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'Authorization': self.api_token}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
    
    def _check_rate_limits(self) -> None:
        """Check and enforce rate limits."""
        current_time = time.time()
        
        # Reset hourly counter if needed
        if current_time - self.hourly_window_start >= 3600:
            self.hourly_request_count = 0
            self.hourly_window_start = current_time
        
        # Check hourly limit
        if self.hourly_request_count >= self.rate_limit_per_hour:
            raise RateLimitError("Hourly rate limit exceeded")
        
        # Check per-second limit
        time_since_last_request = current_time - self.last_request_time
        min_interval = 1.0 / self.rate_limit_per_second
        
        if time_since_last_request < min_interval:
            sleep_time = min_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.hourly_request_count += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def search_player_replays(
        self, 
        player_name: str, 
        count: int = 10,
        playlist: Optional[str] = None,
        season: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for replays by player name.
        
        Args:
            player_name: Player's gamertag/name
            count: Number of replays to fetch (max 200 per request)
            playlist: Optional playlist filter
            season: Optional season filter
            
        Returns:
            List of replay metadata dictionaries
            
        Raises:
            BallchasingAPIError: If API request fails
            RateLimitError: If rate limit is exceeded
        """
        logger.info(
            "Searching for player replays",
            player=player_name,
            count=count,
            playlist=playlist,
            season=season
        )
        
        try:
            self._check_rate_limits()
            
            # Use the ballchasing library to search for replays
            # The library handles pagination automatically
            replays = []
            collected = 0
            
            # Build search parameters
            search_params = {
                'player-name': player_name,
                'count': min(count, 200)  # API limit per request
            }
            
            if playlist:
                search_params['playlist'] = playlist
            if season:
                search_params['season'] = season
            
            # Get replays using the library
            replay_results = self.api.get_replays(**search_params)
            
            # Convert to list and limit results
            for replay in replay_results:
                if collected >= count:
                    break
                
                # Convert typed object to dict if needed
                if hasattr(replay, '__dict__'):
                    replay_dict = replay.__dict__
                else:
                    replay_dict = replay
                
                replays.append(replay_dict)
                collected += 1
            
            logger.info(
                "Successfully fetched replays",
                player=player_name,
                found=len(replays),
                requested=count
            )
            
            return replays
            
        except Exception as e:
            logger.error(
                "Failed to search player replays",
                player=player_name,
                error=str(e),
                error_type=type(e).__name__
            )
            
            if "rate limit" in str(e).lower():
                raise RateLimitError(f"Rate limit exceeded: {str(e)}") from e
            elif "not found" in str(e).lower():
                return []  # No replays found is not an error
            else:
                raise BallchasingAPIError(f"Failed to search replays: {str(e)}") from e
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def download_replay(self, replay_id: str) -> bytes:
        """Download a replay file by ID.
        
        Args:
            replay_id: Unique replay identifier
            
        Returns:
            Binary replay file content
            
        Raises:
            ReplayNotFoundError: If replay doesn't exist
            BallchasingAPIError: If download fails
        """
        logger.debug("Downloading replay", replay_id=replay_id)
        
        try:
            self._check_rate_limits()
            
            # Use the ballchasing library to download
            # We need to use the direct HTTP client since the library
            # doesn't have an async download method
            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={'Authorization': self.api_token}
                )
            
            url = f"https://ballchasing.com/api/replays/{replay_id}/file"
            
            async with self._session.get(url) as response:
                if response.status == 404:
                    raise ReplayNotFoundError(f"Replay not found: {replay_id}")
                elif response.status == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status != 200:
                    raise BallchasingAPIError(
                        f"Failed to download replay {replay_id}: HTTP {response.status}"
                    )
                
                content = await response.read()
                
                logger.debug(
                    "Successfully downloaded replay",
                    replay_id=replay_id,
                    size=len(content)
                )
                
                return content
                
        except (ReplayNotFoundError, RateLimitError):
            # Re-raise these as-is
            raise
        except Exception as e:
            logger.error(
                "Failed to download replay",
                replay_id=replay_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise BallchasingAPIError(f"Failed to download replay {replay_id}: {str(e)}") from e
    
    def extract_game_result(self, replay_metadata: Dict[str, Any], player_name: str) -> str:
        """Extract game result (win/loss) for a specific player.
        
        Args:
            replay_metadata: Replay metadata from API
            player_name: Player's name to check result for
            
        Returns:
            'win' or 'loss'
            
        Raises:
            ValueError: If player not found in replay
        """
        try:
            # Look for the player in both teams
            blue_team = replay_metadata.get('blue', {})
            orange_team = replay_metadata.get('orange', {})
            
            player_team = None
            
            # Check blue team
            if 'players' in blue_team:
                for player in blue_team['players']:
                    if player.get('name', '').lower() == player_name.lower():
                        player_team = 'blue'
                        break
            
            # Check orange team if not found in blue
            if player_team is None and 'players' in orange_team:
                for player in orange_team['players']:
                    if player.get('name', '').lower() == player_name.lower():
                        player_team = 'orange'
                        break
            
            if player_team is None:
                raise ValueError(f"Player {player_name} not found in replay")
            
            # Determine winner
            blue_goals = blue_team.get('goals', 0)
            orange_goals = orange_team.get('goals', 0)
            
            if blue_goals > orange_goals:
                winner = 'blue'
            elif orange_goals > blue_goals:
                winner = 'orange'
            else:
                # Tie - this shouldn't happen in normal ranked games
                logger.warning("Game ended in tie", replay_id=replay_metadata.get('id'))
                return 'loss'  # Default to loss for ties
            
            result = 'win' if player_team == winner else 'loss'
            
            logger.debug(
                "Extracted game result",
                player=player_name,
                result=result,
                player_team=player_team,
                winner=winner,
                score=f"{blue_goals}-{orange_goals}"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to extract game result",
                player=player_name,
                error=str(e),
                replay_metadata=replay_metadata
            )
            # Default to loss if we can't determine the result
            return 'loss'
    
    async def get_replay_details(self, replay_id: str) -> Dict[str, Any]:
        """Get detailed replay information.
        
        Args:
            replay_id: Unique replay identifier
            
        Returns:
            Detailed replay metadata
            
        Raises:
            ReplayNotFoundError: If replay doesn't exist
            BallchasingAPIError: If request fails
        """
        logger.debug("Getting replay details", replay_id=replay_id)
        
        try:
            self._check_rate_limits()
            
            # Use the ballchasing library
            replay = self.api.get_replay(replay_id)
            
            # Convert to dict if it's a typed object
            if hasattr(replay, '__dict__'):
                replay_dict = replay.__dict__
            else:
                replay_dict = replay
            
            logger.debug("Successfully got replay details", replay_id=replay_id)
            return replay_dict
            
        except Exception as e:
            logger.error(
                "Failed to get replay details",
                replay_id=replay_id,
                error=str(e)
            )
            
            if "not found" in str(e).lower():
                raise ReplayNotFoundError(f"Replay not found: {replay_id}") from e
            else:
                raise BallchasingAPIError(f"Failed to get replay details: {str(e)}") from e
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status.
        
        Returns:
            Dictionary with rate limit information
        """
        current_time = time.time()
        time_since_window_start = current_time - self.hourly_window_start
        
        return {
            'requests_this_hour': self.hourly_request_count,
            'hourly_limit': self.rate_limit_per_hour,
            'requests_remaining': self.rate_limit_per_hour - self.hourly_request_count,
            'window_reset_in_seconds': 3600 - time_since_window_start,
            'per_second_limit': self.rate_limit_per_second,
            'last_request_seconds_ago': current_time - self.last_request_time
        }


# Convenience function for creating client
def create_ballchasing_client(api_token: Optional[str] = None) -> BallchasingClient:
    """Create a Ballchasing client instance.
    
    Args:
        api_token: Optional API token
        
    Returns:
        Configured BallchasingClient instance
    """
    return BallchasingClient(api_token)
