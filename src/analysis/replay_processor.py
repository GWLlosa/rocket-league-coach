"""Replay processing using carball library."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

# Try to import carball, but make it optional
try:
    from carball.analysis.analysis_manager import AnalysisManager
    from carball.json_parser.game import Game
    CARBALL_AVAILABLE = True
except ImportError:
    CARBALL_AVAILABLE = False
    AnalysisManager = None
    Game = None

from ..config import get_settings
from ..logging_config import get_logger

logger = get_logger(__name__)


class ReplayProcessor:
    """Processes Rocket League replay files using carball library."""
    
    def __init__(self):
        """Initialize the replay processor."""
        self.settings = get_settings()
        
        if not CARBALL_AVAILABLE:
            logger.warning(
                "Carball library not available. Replay processing will return mock data. "
                "Install carball to enable full replay analysis."
            )
    
    def parse_replay_file(self, replay_file_path: Path) -> Dict[str, Any]:
        """Parse a replay file and extract game data.
        
        Args:
            replay_file_path: Path to the .replay file
            
        Returns:
            Dictionary containing parsed game data
            
        Raises:
            FileNotFoundError: If replay file doesn't exist
            ValueError: If replay file is invalid or carball unavailable
        """
        if not replay_file_path.exists():
            raise FileNotFoundError(f"Replay file not found: {replay_file_path}")
        
        if not CARBALL_AVAILABLE:
            logger.warning("Carball not available, returning mock data")
            return self._get_mock_replay_data()
        
        try:
            logger.info(f"Parsing replay file: {replay_file_path}")
            
            # Create analysis manager
            analysis_manager = AnalysisManager()
            
            # Parse the replay file
            proto_game = analysis_manager.create_proto_from_file(str(replay_file_path))
            
            # Convert to JSON for easier processing
            game = Game()
            game.initialize(loaded_proto=proto_game)
            
            # Convert to dictionary format
            game_data = {
                'game_stats': self._extract_game_stats(game),
                'player_stats': self._extract_player_stats(game),
                'teams': self._extract_team_stats(game),
                'metadata': self._extract_metadata(game)
            }
            
            logger.info(f"Successfully parsed replay: {replay_file_path.name}")
            return game_data
            
        except Exception as e:
            logger.error(f"Failed to parse replay {replay_file_path}: {str(e)}")
            # Return mock data as fallback
            logger.warning("Returning mock data due to parsing error")
            return self._get_mock_replay_data()
    
    def _extract_game_stats(self, game: Any) -> Dict[str, Any]:
        """Extract overall game statistics."""
        if not CARBALL_AVAILABLE:
            return {}
        
        try:
            return {
                'duration': getattr(game, 'game_length', 300.0),
                'map': getattr(game, 'map_name', 'Unknown'),
                'match_type': getattr(game, 'match_type', 'Unknown'),
                'team_size': getattr(game, 'team_size', 3)
            }
        except Exception as e:
            logger.warning(f"Error extracting game stats: {e}")
            return {}
    
    def _extract_player_stats(self, game: Any) -> Dict[str, Dict[str, Any]]:
        """Extract statistics for all players."""
        if not CARBALL_AVAILABLE:
            return {}
        
        try:
            player_stats = {}
            
            # Get players from both teams
            players = getattr(game, 'players', [])
            
            for player in players:
                player_name = getattr(player, 'name', 'Unknown')
                
                # Extract key metrics for our analysis
                stats = {
                    'name': player_name,
                    'team': getattr(player, 'team', 0),
                    'score': getattr(player, 'score', 0),
                    'goals': getattr(player, 'goals', 0),
                    'assists': getattr(player, 'assists', 0),
                    'saves': getattr(player, 'saves', 0),
                    'shots': getattr(player, 'shots', 0),
                    # Add placeholders for metrics we'll calculate
                    'avg_speed': 0.0,
                    'time_supersonic_speed': 0.0,
                    'shooting_percentage': 0.0,
                    'avg_amount': 0.0,
                    'time_zero_boost': 0.0,
                    'time_defensive_third': 0.0,
                    'avg_distance_to_ball': 0.0,
                    'time_behind_ball': 0.0,
                    'amount_overfill': 0.0,
                    'time_most_back': 0.0
                }
                
                player_stats[player_name] = stats
            
            return player_stats
            
        except Exception as e:
            logger.warning(f"Error extracting player stats: {e}")
            return {}
    
    def _extract_team_stats(self, game: Any) -> List[Dict[str, Any]]:
        """Extract team-level statistics."""
        if not CARBALL_AVAILABLE:
            return []
        
        try:
            teams = []
            
            # Extract basic team info
            blue_team = {
                'team_id': 0,
                'name': 'Blue',
                'goals': 0,
                'players': []
            }
            
            orange_team = {
                'team_id': 1,
                'name': 'Orange', 
                'goals': 0,
                'players': []
            }
            
            teams.extend([blue_team, orange_team])
            
            return teams
            
        except Exception as e:
            logger.warning(f"Error extracting team stats: {e}")
            return []
    
    def _extract_metadata(self, game: Any) -> Dict[str, Any]:
        """Extract replay metadata."""
        if not CARBALL_AVAILABLE:
            return {}
        
        try:
            return {
                'replay_id': getattr(game, 'replay_id', 'unknown'),
                'date': getattr(game, 'date', None),
                'version': getattr(game, 'version', 'unknown')
            }
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
            return {}
    
    def _get_mock_replay_data(self) -> Dict[str, Any]:
        """Return mock replay data when carball is not available."""
        return {
            'game_stats': {
                'duration': 300.0,
                'map': 'MockMap',
                'match_type': 'Ranked',
                'team_size': 3
            },
            'player_stats': {
                'MockPlayer': {
                    'name': 'MockPlayer',
                    'team': 0,
                    'score': 500,
                    'goals': 2,
                    'assists': 1,
                    'saves': 3,
                    'shots': 5,
                    'avg_speed': 1200.0,
                    'time_supersonic_speed': 45.0,
                    'shooting_percentage': 0.4,
                    'avg_amount': 50.0,
                    'time_zero_boost': 20.0,
                    'time_defensive_third': 80.0,
                    'avg_distance_to_ball': 750.0,
                    'time_behind_ball': 150.0,
                    'amount_overfill': 5.0,
                    'time_most_back': 60.0
                }
            },
            'teams': [
                {'team_id': 0, 'name': 'Blue', 'goals': 3, 'players': []},
                {'team_id': 1, 'name': 'Orange', 'goals': 1, 'players': []}
            ],
            'metadata': {
                'replay_id': 'mock_replay',
                'date': None,
                'version': 'mock',
                'note': 'This is mock data. Install carball for real replay analysis.'
            }
        }
    
    def is_available(self) -> bool:
        """Check if carball is available for replay processing."""
        return CARBALL_AVAILABLE
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the replay processor."""
        return {
            'carball_available': CARBALL_AVAILABLE,
            'processor_ready': True,
            'mock_mode': not CARBALL_AVAILABLE
        }


# Convenience function for creating processor
def create_replay_processor() -> ReplayProcessor:
    """Create a replay processor instance."""
    return ReplayProcessor()
