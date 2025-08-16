"""Replay processing using carball library for Rocket League replay analysis."""

import asyncio
import gc
import os
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor
import tempfile

from carball.analysis.analysis_manager import AnalysisManager
from carball.json_parser.game import Game
from carball.generated.api.player_pb2 import Player
from carball.generated.api.game_pb2 import Game as ProtoGame

from ..config import get_settings
from ..logging_config import get_logger, log_performance, LoggingMixin
from .exceptions import (
    ReplayParsingException,
    CorruptedReplayException,
    UnsupportedReplayVersionException,
    PlayerNotFoundException,
    CarballException,
    MemoryException,
    AnalysisTimeoutException,
)


class ReplayProcessor(LoggingMixin):
    """Processes Rocket League replay files using carball."""
    
    def __init__(self):
        self.settings = get_settings()
        self.executor = ThreadPoolExecutor(
            max_workers=self.settings.max_concurrent_analysis,
            thread_name_prefix="replay_processor"
        )
        self._memory_threshold_mb = 1000  # 1GB memory threshold
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Clean up resources."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
    
    def _check_memory_usage(self, operation: str = "analysis"):
        """Check current memory usage and raise exception if too high."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > self._memory_threshold_mb:
                raise MemoryException(
                    f"Memory usage ({memory_mb:.1f}MB) exceeds threshold ({self._memory_threshold_mb}MB) during {operation}",
                    memory_usage_mb=memory_mb
                )
            
            self.logger.debug(
                "Memory usage check",
                operation=operation,
                memory_mb=memory_mb,
                threshold_mb=self._memory_threshold_mb
            )
        except psutil.NoSuchProcess:
            # Process monitoring not available, continue
            pass
    
    def _parse_replay_sync(self, file_path: Path) -> ProtoGame:
        """Synchronous replay parsing (runs in thread pool)."""
        try:
            self._check_memory_usage("replay_parsing_start")
            
            # Validate file exists and is readable
            if not file_path.exists():
                raise ReplayParsingException(f"Replay file not found: {file_path}")
            
            if file_path.stat().st_size == 0:
                raise CorruptedReplayException(file_path=str(file_path))
            
            self.logger.debug(
                "Starting replay parsing",
                file_path=str(file_path),
                file_size=file_path.stat().st_size
            )
            
            # Use temporary directory for carball processing
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    # Parse the replay file
                    analysis_manager = AnalysisManager()
                    
                    # Parse replay to get game object
                    game: Game = analysis_manager.get_game_object(str(file_path))
                    
                    if not game:
                        raise CorruptedReplayException(file_path=str(file_path))
                    
                    # Convert to protobuf format for analysis
                    proto_game = analysis_manager.get_protobuf_data_from_game(game)
                    
                    if not proto_game:
                        raise ReplayParsingException(
                            f"Failed to convert game to protobuf format: {file_path}"
                        )
                    
                    self._check_memory_usage("replay_parsing_complete")
                    
                    self.logger.info(
                        "Replay parsed successfully",
                        file_path=str(file_path),
                        players_count=len(proto_game.players),
                        game_duration=getattr(proto_game.game_info, 'length', 'unknown')
                    )
                    
                    return proto_game
                
                except Exception as e:
                    if isinstance(e, (ReplayParsingException, CorruptedReplayException)):
                        raise
                    
                    # Handle carball-specific errors
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in ['corrupt', 'invalid', 'malformed']):
                        raise CorruptedReplayException(file_path=str(file_path))
                    elif 'version' in error_msg:
                        raise UnsupportedReplayVersionException(replay_id=file_path.stem)
                    else:
                        raise CarballException(
                            f"Carball parsing failed: {e}",
                            original_exception=e
                        )
        
        finally:
            # Force garbage collection to free memory
            gc.collect()
    
    async def parse_replay_file(self, file_path: Path) -> ProtoGame:
        """Parse a replay file and return the protobuf game data."""
        with log_performance(f"parse_replay_{file_path.stem}"):
            try:
                # Run parsing in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                
                # Set timeout for parsing
                timeout = self.settings.analysis_timeout_seconds
                
                proto_game = await asyncio.wait_for(
                    loop.run_in_executor(
                        self.executor,
                        self._parse_replay_sync,
                        file_path
                    ),
                    timeout=timeout
                )
                
                return proto_game
            
            except asyncio.TimeoutError:
                raise AnalysisTimeoutException(
                    timeout_seconds=self.settings.analysis_timeout_seconds,
                    operation="replay_parsing"
                )
            except Exception as e:
                if isinstance(e, (
                    ReplayParsingException, 
                    CorruptedReplayException, 
                    UnsupportedReplayVersionException,
                    CarballException,
                    MemoryException
                )):
                    raise
                
                self.logger.error(
                    "Unexpected error during replay parsing",
                    file_path=str(file_path),
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise ReplayParsingException(
                    f"Unexpected error parsing replay: {e}",
                    file_path=str(file_path)
                )
    
    def find_player_in_game(self, proto_game: ProtoGame, player_name: str) -> Optional[Player]:
        """Find a player by name in the game data."""
        if not proto_game or not proto_game.players:
            return None
        
        # Normalize player name for comparison
        normalized_target = player_name.lower().strip()
        
        for player in proto_game.players:
            if not player or not player.name:
                continue
            
            normalized_player = player.name.lower().strip()
            
            # Exact match
            if normalized_player == normalized_target:
                return player
            
            # Partial match (for cases with platform prefixes/suffixes)
            if normalized_target in normalized_player or normalized_player in normalized_target:
                self.logger.debug(
                    "Player found with partial match",
                    target=player_name,
                    found=player.name
                )
                return player
        
        return None
    
    def extract_basic_game_info(self, proto_game: ProtoGame) -> Dict[str, Any]:
        """Extract basic game information from protobuf data."""
        try:
            game_info = {}
            
            if hasattr(proto_game, 'game_info') and proto_game.game_info:
                info = proto_game.game_info
                game_info.update({
                    'duration': getattr(info, 'length', 0),
                    'map_name': getattr(info, 'map', 'Unknown'),
                    'date': getattr(info, 'time', None),
                    'version': getattr(info, 'build_version', 'Unknown'),
                })
            
            if hasattr(proto_game, 'teams') and proto_game.teams:
                teams = proto_game.teams
                if len(teams) >= 2:
                    game_info.update({
                        'blue_score': getattr(teams[0], 'score', 0),
                        'orange_score': getattr(teams[1], 'score', 0),
                    })
            
            # Player information
            players = []
            if hasattr(proto_game, 'players') and proto_game.players:
                for player in proto_game.players:
                    if player and hasattr(player, 'name'):
                        players.append({
                            'name': player.name,
                            'team': getattr(player, 'is_orange', False),
                            'score': getattr(player, 'score', 0),
                        })
            
            game_info['players'] = players
            game_info['player_count'] = len(players)
            
            return game_info
        
        except Exception as e:
            self.logger.warning(
                "Failed to extract basic game info",
                error=str(e)
            )
            return {}
    
    async def validate_replay_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate a replay file and return basic information."""
        try:
            proto_game = await self.parse_replay_file(file_path)
            game_info = self.extract_basic_game_info(proto_game)
            
            validation_result = {
                'valid': True,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'game_info': game_info,
                'error': None
            }
            
            self.logger.info(
                "Replay validation successful",
                file_path=str(file_path),
                players=game_info.get('player_count', 0),
                duration=game_info.get('duration', 0)
            )
            
            return validation_result
        
        except Exception as e:
            validation_result = {
                'valid': False,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size if file_path.exists() else 0,
                'game_info': {},
                'error': str(e),
                'error_type': type(e).__name__
            }
            
            self.logger.warning(
                "Replay validation failed",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__
            )
            
            return validation_result
    
    async def batch_validate_replays(
        self,
        file_paths: List[Path],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Validate multiple replay files with progress tracking."""
        results = []
        total = len(file_paths)
        
        self.logger.info(
            "Starting batch replay validation",
            total_files=total
        )
        
        for i, file_path in enumerate(file_paths):
            try:
                result = await self.validate_replay_file(file_path)
                results.append(result)
                
                if progress_callback:
                    progress = (i + 1) / total * 100
                    progress_callback(progress, f"Validated {file_path.name}")
                
            except Exception as e:
                self.logger.error(
                    "Batch validation error",
                    file_path=str(file_path),
                    error=str(e)
                )
                results.append({
                    'valid': False,
                    'file_path': str(file_path),
                    'error': str(e),
                    'error_type': type(e).__name__
                })
        
        valid_count = sum(1 for r in results if r['valid'])
        self.logger.info(
            "Batch validation complete",
            total=total,
            valid=valid_count,
            invalid=total - valid_count
        )
        
        return results


# Convenience function for creating processor instances
def create_replay_processor() -> ReplayProcessor:
    """Create a configured replay processor."""
    return ReplayProcessor()
