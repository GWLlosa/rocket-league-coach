"""Ballchasing.com API client with rate limiting and error handling."""

import asyncio
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncIterator
from urllib.parse import urljoin
import aiohttp
import aiofiles
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import get_settings
from ..logging_config import get_logger, log_performance
from .exceptions import (
    BallchasingAPIException,
    RateLimitExceededException,
    UnauthorizedException,
    ReplayNotFoundException,
    PlayerNotFoundException,
    InvalidResponseException,
    NetworkException,
    DownloadException,
)
from .models import (
    ReplaySearchResponse,
    GameInfo,
    GameResult,
    DownloadInfo,
    BallchasingError,
)


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 2.0, calls_per_hour: int = 500):
        self.calls_per_second = calls_per_second
        self.calls_per_hour = calls_per_hour
        self.last_call_time = 0.0
        self.hourly_calls = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make an API call."""
        async with self._lock:
            now = time.time()
            
            # Remove calls older than 1 hour
            self.hourly_calls = [call_time for call_time in self.hourly_calls if now - call_time < 3600]
            
            # Check hourly limit
            if len(self.hourly_calls) >= self.calls_per_hour:
                oldest_call = min(self.hourly_calls)
                sleep_time = 3600 - (now - oldest_call)
                raise RateLimitExceededException(
                    f"Hourly rate limit exceeded. Try again in {sleep_time:.0f} seconds.",
                    retry_after=int(sleep_time)
                )
            
            # Check per-second limit
            time_since_last_call = now - self.last_call_time
            min_interval = 1.0 / self.calls_per_second
            
            if time_since_last_call < min_interval:
                sleep_time = min_interval - time_since_last_call
                await asyncio.sleep(sleep_time)
                now = time.time()
            
            # Record the call
            self.last_call_time = now
            self.hourly_calls.append(now)


class BallchasingClient:
    """Async client for Ballchasing.com API."""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        self.api_key = api_key or self.settings.ballchasing_api_key
        self.base_url = base_url or self.settings.ballchasing_base_url
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            calls_per_second=self.settings.ballchasing_rate_limit_per_second,
            calls_per_hour=self.settings.ballchasing_rate_limit_per_hour
        )
        
        # Session will be created when needed
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds)
            headers = {
                "Authorization": self.api_key,
                "User-Agent": "RocketLeagueCoach/1.0.0"
            }
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                raise_for_status=False
            )
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, NetworkException))
    )
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to the Ballchasing API."""
        await self._ensure_session()
        await self.rate_limiter.acquire()
        
        url = urljoin(self.base_url, endpoint)
        
        self.logger.debug(
            "Making API request",
            method=method,
            url=url,
            params=kwargs.get('params')
        )
        
        try:
            async with self._session.request(method, url, **kwargs) as response:
                # Handle rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    raise RateLimitExceededException(
                        "Rate limit exceeded",
                        retry_after=retry_after
                    )
                
                # Handle authentication errors
                if response.status == 401:
                    raise UnauthorizedException("Invalid API key")
                
                # Handle not found
                if response.status == 404:
                    raise ReplayNotFoundException("Resource not found")
                
                # Read response content
                try:
                    response_data = await response.json()
                except aiohttp.ContentTypeError:
                    response_text = await response.text()
                    self.logger.error(
                        "Invalid JSON response",
                        status=response.status,
                        response=response_text[:500]
                    )
                    raise InvalidResponseException("Invalid JSON response from API")
                
                # Handle API errors
                if not response.ok:
                    error_msg = response_data.get('error', f"HTTP {response.status}")
                    raise BallchasingAPIException(
                        error_msg,
                        status_code=response.status,
                        response_data=response_data
                    )
                
                self.logger.debug(
                    "API request successful",
                    status=response.status,
                    response_size=len(str(response_data))
                )
                
                return response_data
        
        except aiohttp.ClientError as e:
            self.logger.error(
                "Network error during API request",
                error=str(e),
                url=url
            )
            raise NetworkException(f"Network error: {e}", e)
    
    async def search_player_replays(
        self,
        player_name: str,
        count: int = 10,
        ranked_only: bool = True,
        sort_by: str = "created",
        sort_order: str = "desc"
    ) -> List[GameInfo]:
        """Search for replays by player name."""
        self.logger.info(
            "Searching for player replays",
            player=player_name,
            count=count,
            ranked_only=ranked_only
        )
        
        params = {
            "player-name": player_name,
            "count": min(count, 200),  # API limit
            "sort-by": sort_by,
            "sort-dir": sort_order,
        }
        
        if ranked_only:
            params["playlist"] = "ranked-duels,ranked-doubles,ranked-standard,ranked-hoops,ranked-rumble,ranked-dropshot,ranked-snowday"
        
        with log_performance(f"search_replays_for_{player_name}"):
            response_data = await self._make_request("GET", "/replays", params=params)
        
        try:
            search_response = ReplaySearchResponse(**response_data)
        except Exception as e:
            self.logger.error(
                "Failed to parse search response",
                error=str(e),
                response_data=response_data
            )
            raise InvalidResponseException(f"Failed to parse search response: {e}")
        
        if not search_response.list:
            raise PlayerNotFoundException(player_name)
        
        self.logger.info(
            "Found replays for player",
            player=player_name,
            count=len(search_response.list),
            total_available=search_response.count
        )
        
        return search_response.list
    
    async def download_replay(self, replay_id: str, destination: Path) -> DownloadInfo:
        """Download a replay file to the specified destination."""
        await self._ensure_session()
        
        self.logger.debug(
            "Downloading replay",
            replay_id=replay_id,
            destination=str(destination)
        )
        
        download_url = f"/replays/{replay_id}/file"
        
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        try:
            await self.rate_limiter.acquire()
            
            async with self._session.get(urljoin(self.base_url, download_url)) as response:
                if response.status == 404:
                    raise ReplayNotFoundException(replay_id)
                
                if response.status == 401:
                    raise UnauthorizedException("Invalid API key for download")
                
                if not response.ok:
                    raise DownloadException(
                        replay_id,
                        f"HTTP {response.status}: {await response.text()}"
                    )
                
                # Get file size from headers
                file_size = int(response.headers.get('Content-Length', 0))
                
                # Download file
                async with aiofiles.open(destination, 'wb') as file:
                    async for chunk in response.content.iter_chunked(8192):
                        await file.write(chunk)
                
                download_time = time.time() - start_time
                actual_size = destination.stat().st_size
                
                download_info = DownloadInfo(
                    replay_id=replay_id,
                    file_path=str(destination),
                    file_size=actual_size,
                    download_time=download_time
                )
                
                self.logger.info(
                    "Replay downloaded successfully",
                    replay_id=replay_id,
                    file_size=actual_size,
                    download_time=download_time
                )
                
                return download_info
        
        except Exception as e:
            if destination.exists():
                destination.unlink()  # Clean up partial download
            
            if isinstance(e, (ReplayNotFoundException, UnauthorizedException, DownloadException)):
                raise
            
            self.logger.error(
                "Failed to download replay",
                replay_id=replay_id,
                error=str(e)
            )
            raise DownloadException(replay_id, str(e))
    
    def extract_game_result(self, game_info: GameInfo, player_name: str) -> GameResult:
        """Extract game result information for a specific player."""
        # This is a placeholder - in a real implementation, we would need
        # to download and parse the replay to get detailed team information
        # For now, we'll create a basic result structure
        
        # Note: The actual team assignment and scores would come from
        # parsing the replay file with carball
        result = GameResult(
            replay_id=game_info.id,
            player_name=player_name,
            team_color="unknown",  # Will be determined by carball
            team_score=0,  # Will be determined by carball
            opponent_score=0,  # Will be determined by carball
            won=False,  # Will be determined by carball
            duration=game_info.duration,
            date=game_info.date,
            playlist=game_info.playlist_name,
            map_name=game_info.map_name
        )
        
        self.logger.debug(
            "Extracted basic game result",
            replay_id=game_info.id,
            player=player_name
        )
        
        return result
    
    async def get_player_game_results(
        self,
        player_name: str,
        num_games: int = 10
    ) -> List[GameResult]:
        """Get game results for a player."""
        self.logger.info(
            "Getting game results for player",
            player=player_name,
            num_games=num_games
        )
        
        # Search for replays
        replays = await self.search_player_replays(player_name, count=num_games)
        
        # Extract game results
        results = []
        for replay in replays:
            try:
                result = self.extract_game_result(replay, player_name)
                results.append(result)
            except Exception as e:
                self.logger.warning(
                    "Failed to extract game result",
                    replay_id=replay.id,
                    error=str(e)
                )
        
        self.logger.info(
            "Extracted game results",
            player=player_name,
            results_count=len(results),
            requested=num_games
        )
        
        return results
    
    async def download_player_replays(
        self,
        player_name: str,
        num_games: int = 10,
        download_dir: Path = None
    ) -> List[DownloadInfo]:
        """Download replay files for a player's recent games."""
        if download_dir is None:
            download_dir = self.settings.replays_dir
        
        self.logger.info(
            "Downloading replays for player",
            player=player_name,
            num_games=num_games,
            download_dir=str(download_dir)
        )
        
        # Search for replays
        replays = await self.search_player_replays(player_name, count=num_games)
        
        # Download replays concurrently (but respecting rate limits)
        download_tasks = []
        for replay in replays:
            filename = f"{replay.id}.replay"
            destination = download_dir / filename
            
            # Skip if file already exists and is valid
            if destination.exists() and destination.stat().st_size > 0:
                self.logger.debug(
                    "Replay already exists, skipping download",
                    replay_id=replay.id,
                    file=str(destination)
                )
                continue
            
            task = self.download_replay(replay.id, destination)
            download_tasks.append(task)
        
        # Execute downloads with concurrency limit
        download_infos = []
        semaphore = asyncio.Semaphore(self.settings.max_concurrent_downloads)
        
        async def download_with_semaphore(task):
            async with semaphore:
                return await task
        
        if download_tasks:
            results = await asyncio.gather(
                *[download_with_semaphore(task) for task in download_tasks],
                return_exceptions=True
            )
            
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(
                        "Download failed",
                        error=str(result)
                    )
                else:
                    download_infos.append(result)
        
        self.logger.info(
            "Completed replay downloads",
            player=player_name,
            successful=len(download_infos),
            requested=num_games
        )
        
        return download_infos


# Convenience function for creating client instances
def create_ballchasing_client() -> BallchasingClient:
    """Create a configured Ballchasing API client."""
    return BallchasingClient()
