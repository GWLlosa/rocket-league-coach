"""Player statistics analyzer using Ballchasing API."""

import os
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import requests
import logging

logger = logging.getLogger(__name__)

class PlayerStatsAnalyzer:
    """Analyzes player statistics from Ballchasing API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the analyzer with API key."""
        self.api_key = api_key or os.environ.get('BALLCHASING_API_KEY')
        if not self.api_key:
            raise ValueError("Ballchasing API key not provided")
        self.headers = {'Authorization': self.api_key}
    
    def get_player_replays(self, username: str, count: int = 20) -> List[Dict]:
        """Fetch recent replays for a player."""
        search_url = 'https://ballchasing.com/api/replays'
        params = {
            'player-name': username,
            'count': count
        }
        
        response = requests.get(search_url, headers=self.headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        return data.get('list', [])
    
    def get_replay_details(self, replay_id: str) -> Dict:
        """Fetch detailed information for a specific replay."""
        replay_url = f'https://ballchasing.com/api/replays/{replay_id}'
        response = requests.get(replay_url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def find_player_in_replay(self, replay: Dict, username: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Find which team a player is on and their stats.
        
        Returns:
            Tuple of (team_color, player_stats) or (None, None) if not found
        """
        username_lower = username.lower()
        
        # Check blue team
        for player in replay.get('blue', {}).get('players', []):
            if player.get('name', '').lower() == username_lower:
                return 'blue', player.get('stats', {})
        
        # Check orange team
        for player in replay.get('orange', {}).get('players', []):
            if player.get('name', '').lower() == username_lower:
                return 'orange', player.get('stats', {})
        
        return None, None
    
    def determine_match_winner(self, replay: Dict) -> Tuple[int, int]:
        """Determine the final score of a match.
        
        Returns:
            Tuple of (blue_goals, orange_goals)
        """
        blue_goals = None
        orange_goals = None
        
        # Try multiple methods to find scores
        # Method 1: Direct team goals field
        if 'blue' in replay and 'goals' in replay['blue']:
            blue_goals = replay['blue']['goals']
        if 'orange' in replay and 'goals' in replay['orange']:
            orange_goals = replay['orange']['goals']
        
        # Method 2: Team stats
        if blue_goals is None:
            blue_goals = replay.get('blue', {}).get('stats', {}).get('core', {}).get('goals', 0)
        if orange_goals is None:
            orange_goals = replay.get('orange', {}).get('stats', {}).get('core', {}).get('goals', 0)
        
        # Method 3: Sum of player goals
        if blue_goals is None:
            blue_goals = sum(
                p.get('stats', {}).get('core', {}).get('goals', 0) 
                for p in replay.get('blue', {}).get('players', [])
            )
        if orange_goals is None:
            orange_goals = sum(
                p.get('stats', {}).get('core', {}).get('goals', 0) 
                for p in replay.get('orange', {}).get('players', [])
            )
        
        return blue_goals or 0, orange_goals or 0
    
    def calculate_boost_efficiency(self, stats: Dict) -> float:
        """Calculate boost efficiency metric.
        
        Returns actions (goals + assists + saves) per 100 boost used.
        """
        boost_stats = stats.get('boost', {})
        core_stats = stats.get('core', {})
        
        boost_used = boost_stats.get('amount_used', 0)
        if boost_used == 0:
            return 0
        
        # Calculate as useful actions per 100 boost
        useful_actions = (
            core_stats.get('goals', 0) + 
            core_stats.get('assists', 0) + 
            core_stats.get('saves', 0)
        )
        
        return (useful_actions / boost_used) * 100
    
    def calculate_shooting_percentage(self, core_stats: Dict) -> float:
        """Calculate shooting percentage."""
        shots = core_stats.get('shots', 0)
        if shots == 0:
            return 0
        goals = core_stats.get('goals', 0)
        return (goals / shots) * 100
    
    def calculate_steal_ratio(self, boost_stats: Dict) -> float:
        """Calculate percentage of collected boost that was stolen."""
        collected = boost_stats.get('amount_collected', 0)
        if collected == 0:
            return 0
        stolen = boost_stats.get('amount_stolen', 0)
        return (stolen / collected) * 100
    
    def analyze_player(self, username: str, num_replays: int = 20) -> Dict[str, Any]:
        """Perform complete analysis of a player's recent performance.
        
        Args:
            username: Player username to analyze
            num_replays: Number of recent replays to analyze
            
        Returns:
            Dictionary containing comprehensive player statistics
        """
        logger.info(f"Analyzing player: {username}")
        
        replays = self.get_player_replays(username, num_replays)
        if not replays:
            logger.warning(f"No replays found for {username}")
            return {}
        
        # Initialize aggregation
        stats = defaultdict(lambda: defaultdict(float))
        wins = losses = ties = total_games = 0
        
        for replay_summary in replays:
            try:
                replay = self.get_replay_details(replay_summary['id'])
                player_team, player_stats = self.find_player_in_replay(replay, username)
                
                if not player_stats:
                    logger.debug(f"Player not found in replay {replay_summary['id']}")
                    continue
                
                total_games += 1
                
                # Determine win/loss
                blue_goals, orange_goals = self.determine_match_winner(replay)
                
                if blue_goals == orange_goals:
                    ties += 1
                elif player_team == 'blue':
                    if blue_goals > orange_goals:
                        wins += 1
                    else:
                        losses += 1
                else:  # orange team
                    if orange_goals > blue_goals:
                        wins += 1
                    else:
                        losses += 1
                
                # Aggregate stats by category
                for category in ['core', 'boost', 'movement', 'positioning', 'demo']:
                    category_stats = player_stats.get(category, {})
                    for stat, value in category_stats.items():
                        stats[category][stat] += value
                
            except Exception as e:
                logger.error(f"Error processing replay {replay_summary['id']}: {e}")
                continue
        
        # Calculate averages
        if total_games > 0:
            for category in stats:
                for stat in stats[category]:
                    stats[category][stat] /= total_games
        
        # Calculate derived metrics
        stats_dict = dict(stats)
        boost_efficiency = self.calculate_boost_efficiency(stats_dict)
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        # Calculate additional metrics
        shooting_percentage = 0
        steal_ratio = 0
        
        if 'core' in stats_dict:
            shooting_percentage = self.calculate_shooting_percentage(stats_dict['core'])
        
        if 'boost' in stats_dict:
            steal_ratio = self.calculate_steal_ratio(stats_dict['boost'])
        
        return {
            'username': username,
            'games_analyzed': total_games,
            'wins': wins,
            'losses': losses,
            'ties': ties,
            'win_rate': win_rate,
            'stats': stats_dict,
            'boost_efficiency': boost_efficiency,
            'shooting_percentage': shooting_percentage,
            'steal_ratio': steal_ratio
        }
    
    def format_stats_display(self, stats: Dict[str, Any]) -> str:
        """Format statistics for display.
        
        Args:
            stats: Statistics dictionary from analyze_player
            
        Returns:
            Formatted string for display
        """
        if not stats:
            return "No statistics available"
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"PLAYER ANALYSIS: {stats['username']}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Games Analyzed: {stats['games_analyzed']}")
        lines.append(f"Record: {stats['wins']}W - {stats['losses']}L - {stats['ties']}T")
        lines.append(f"Win Rate: {stats['win_rate']:.1f}%")
        
        if 'core' in stats['stats']:
            lines.append("")
            lines.append("--- Core Stats (per game) ---")
            core = stats['stats']['core']
            lines.append(f"Goals: {core.get('goals', 0):.2f}")
            lines.append(f"Assists: {core.get('assists', 0):.2f}")
            lines.append(f"Saves: {core.get('saves', 0):.2f}")
            lines.append(f"Shots: {core.get('shots', 0):.2f}")
            lines.append(f"Score: {core.get('score', 0):.0f}")
            lines.append(f"MVPs: {core.get('mvp', 0):.2f}")
            lines.append(f"Shooting %: {stats['shooting_percentage']:.1f}%")
        
        if 'boost' in stats['stats']:
            lines.append("")
            lines.append("--- Boost Stats (per game) ---")
            boost = stats['stats']['boost']
            lines.append(f"Boost Used: {boost.get('amount_used', 0):.0f}")
            lines.append(f"Boost Collected: {boost.get('amount_collected', 0):.0f}")
            lines.append(f"Boost Stolen: {boost.get('amount_stolen', 0):.0f}")
            lines.append(f"Boost Efficiency: {stats['boost_efficiency']:.2f} actions/100 boost")
            lines.append(f"Steal Ratio: {stats['steal_ratio']:.1f}% of collected boost was stolen")
        
        if 'movement' in stats['stats']:
            lines.append("")
            lines.append("--- Movement Stats (per game) ---")
            movement = stats['stats']['movement']
            lines.append(f"Total Distance: {movement.get('total_distance', 0):.0f}")
            lines.append(f"Time Supersonic Speed: {movement.get('time_supersonic_speed', 0):.1f}s")
            lines.append(f"Time Boost Speed: {movement.get('time_boost_speed', 0):.1f}s")
            lines.append(f"Time Slow Speed: {movement.get('time_slow_speed', 0):.1f}s")
            lines.append(f"Time on Ground: {movement.get('time_ground', 0):.1f}s")
            lines.append(f"Time in Air (Low): {movement.get('time_low_air', 0):.1f}s")
            lines.append(f"Time in Air (High): {movement.get('time_high_air', 0):.1f}s")
        
        if 'positioning' in stats['stats']:
            lines.append("")
            lines.append("--- Positioning Stats (per game) ---")
            positioning = stats['stats']['positioning']
            lines.append(f"Time Defensive Third: {positioning.get('time_defensive_third', 0):.1f}s")
            lines.append(f"Time Neutral Third: {positioning.get('time_neutral_third', 0):.1f}s")
            lines.append(f"Time Offensive Third: {positioning.get('time_offensive_third', 0):.1f}s")
            lines.append(f"Time Behind Ball: {positioning.get('time_behind_ball', 0):.1f}s")
            lines.append(f"Time In Front of Ball: {positioning.get('time_infront_ball', 0):.1f}s")
        
        if 'demo' in stats['stats']:
            lines.append("")
            lines.append("--- Demolition Stats (per game) ---")
            demo = stats['stats']['demo']
            lines.append(f"Demolitions Inflicted: {demo.get('inflicted', 0):.2f}")
            lines.append(f"Demolitions Taken: {demo.get('taken', 0):.2f}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
