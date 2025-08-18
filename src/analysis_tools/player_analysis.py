#!/usr/bin/env python3
"""
Fixed player analysis script for Rocket League Coach.
This version includes corrections for win/loss detection and boost efficiency.
"""

import os
import sys
import requests
from typing import Dict, List, Any
from collections import defaultdict

def get_player_stats(username: str, num_replays: int = 20) -> Dict[str, Any]:
    """Fetch and analyze player statistics from recent replays."""
    
    api_key = os.environ.get('BALLCHASING_API_KEY')
    if not api_key:
        raise ValueError("BALLCHASING_API_KEY not found in environment")
    
    headers = {'Authorization': api_key}
    
    # Search for replays with this player
    search_url = 'https://ballchasing.com/api/replays'
    params = {
        'player-name': username,
        'count': num_replays
    }
    
    print(f"Fetching replays for {username}...")
    response = requests.get(search_url, headers=headers, params=params)
    
    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code}")
    
    data = response.json()
    replay_list = data.get('list', [])
    
    if not replay_list:
        print(f"No replays found for {username}")
        return {}
    
    print(f"Found {len(replay_list)} replays, analyzing...")
    
    # Aggregate stats
    stats = defaultdict(lambda: defaultdict(float))
    wins = 0
    losses = 0
    total_games = 0
    
    for replay_summary in replay_list:
        replay_id = replay_summary['id']
        
        # Get full replay details
        replay_url = f'https://ballchasing.com/api/replays/{replay_id}'
        replay_response = requests.get(replay_url, headers=headers)
        
        if replay_response.status_code != 200:
            print(f"  Skipping replay {replay_id} (error fetching details)")
            continue
        
        replay = replay_response.json()
        
        # Find which team the player is on and their stats
        player_team = None
        player_stats = None
        
        # Check blue team
        for player in replay.get('blue', {}).get('players', []):
            if player.get('name', '').lower() == username.lower():
                player_team = 'blue'
                player_stats = player.get('stats', {})
                break
        
        # Check orange team if not found in blue
        if not player_team:
            for player in replay.get('orange', {}).get('players', []):
                if player.get('name', '').lower() == username.lower():
                    player_team = 'orange'
                    player_stats = player.get('stats', {})
                    break
        
        if not player_stats:
            print(f"  Player not found in replay {replay_id}")
            continue
        
        total_games += 1
        
        # Determine winner - try multiple methods
        blue_goals = None
        orange_goals = None
        
        # Method 1: Direct team goals field
        if 'blue' in replay and 'goals' in replay['blue']:
            blue_goals = replay['blue']['goals']
        if 'orange' in replay and 'goals' in replay['orange']:
            orange_goals = replay['orange']['goals']
        
        # Method 2: Team stats
        if blue_goals is None and 'blue' in replay and 'stats' in replay['blue']:
            blue_goals = replay['blue']['stats'].get('core', {}).get('goals', None)
        if orange_goals is None and 'orange' in replay and 'stats' in replay['orange']:
            orange_goals = replay['orange']['stats'].get('core', {}).get('goals', None)
        
        # Method 3: Sum of player goals
        if blue_goals is None:
            blue_goals = sum(p.get('stats', {}).get('core', {}).get('goals', 0) 
                           for p in replay.get('blue', {}).get('players', []))
        if orange_goals is None:
            orange_goals = sum(p.get('stats', {}).get('core', {}).get('goals', 0) 
                             for p in replay.get('orange', {}).get('players', []))
        
        # Determine if player won
        if blue_goals is not None and orange_goals is not None:
            if player_team == 'blue':
                if blue_goals > orange_goals:
                    wins += 1
                elif blue_goals < orange_goals:
                    losses += 1
            else:  # player_team == 'orange'
                if orange_goals > blue_goals:
                    wins += 1
                elif orange_goals < blue_goals:
                    losses += 1
        
        # Aggregate core stats
        core_stats = player_stats.get('core', {})
        for stat, value in core_stats.items():
            stats['core'][stat] += value
        
        # Aggregate boost stats
        boost_stats = player_stats.get('boost', {})
        for stat, value in boost_stats.items():
            stats['boost'][stat] += value
        
        # Aggregate movement stats
        movement_stats = player_stats.get('movement', {})
        for stat, value in movement_stats.items():
            stats['movement'][stat] += value
        
        # Aggregate positioning stats
        positioning_stats = player_stats.get('positioning', {})
        for stat, value in positioning_stats.items():
            stats['positioning'][stat] += value
    
    # Calculate averages
    if total_games > 0:
        for category in stats:
            for stat in stats[category]:
                stats[category][stat] /= total_games
    
    # Calculate boost efficiency
    boost_efficiency = 0
    if stats['boost'].get('amount_used', 0) > 0:
        # Boost efficiency = useful boost actions / total boost used
        # Useful = amount collected + amount stolen
        useful_boost = stats['boost'].get('amount_collected', 0) + stats['boost'].get('amount_stolen', 0)
        boost_used = stats['boost'].get('amount_used', 0)
        
        # Alternative calculation: goals+assists+saves per 100 boost used
        useful_actions = stats['core'].get('goals', 0) + stats['core'].get('assists', 0) + stats['core'].get('saves', 0)
        if boost_used > 0:
            boost_efficiency = (useful_actions / boost_used) * 100
    
    return {
        'username': username,
        'games_analyzed': total_games,
        'wins': wins,
        'losses': losses,
        'win_rate': (wins / total_games * 100) if total_games > 0 else 0,
        'stats': dict(stats),
        'boost_efficiency': boost_efficiency
    }

def display_stats(stats: Dict[str, Any]):
    """Display player statistics in a formatted way."""
    
    if not stats:
        return
    
    print("\n" + "="*60)
    print(f"PLAYER ANALYSIS: {stats['username']}")
    print("="*60)
    
    print(f"\nGames Analyzed: {stats['games_analyzed']}")
    print(f"Record: {stats['wins']}W - {stats['losses']}L")
    print(f"Win Rate: {stats['win_rate']:.1f}%")
    
    if 'core' in stats['stats']:
        print("\n--- Core Stats (per game) ---")
        core = stats['stats']['core']
        print(f"Goals: {core.get('goals', 0):.2f}")
        print(f"Assists: {core.get('assists', 0):.2f}")
        print(f"Saves: {core.get('saves', 0):.2f}")
        print(f"Shots: {core.get('shots', 0):.2f}")
        print(f"Score: {core.get('score', 0):.0f}")
        print(f"MVPs: {core.get('mvp', 0):.2f}")
        
        shooting_percentage = 0
        if core.get('shots', 0) > 0:
            shooting_percentage = (core.get('goals', 0) / core.get('shots', 0)) * 100
        print(f"Shooting %: {shooting_percentage:.1f}%")
    
    if 'boost' in stats['stats']:
        print("\n--- Boost Stats (per game) ---")
        boost = stats['stats']['boost']
        print(f"Boost Used: {boost.get('amount_used', 0):.0f}")
        print(f"Boost Collected: {boost.get('amount_collected', 0):.0f}")
        print(f"Boost Stolen: {boost.get('amount_stolen', 0):.0f}")
        print(f"Boost Efficiency: {stats['boost_efficiency']:.2f} actions/100 boost")
        
        # Additional boost metrics
        if boost.get('amount_collected', 0) > 0:
            steal_ratio = (boost.get('amount_stolen', 0) / boost.get('amount_collected', 0)) * 100
            print(f"Steal Ratio: {steal_ratio:.1f}% of collected boost was stolen")
    
    if 'movement' in stats['stats']:
        print("\n--- Movement Stats (per game) ---")
        movement = stats['stats']['movement']
        print(f"Total Distance: {movement.get('total_distance', 0):.0f}")
        print(f"Time Supersonic Speed: {movement.get('time_supersonic_speed', 0):.1f}s")
        print(f"Time Boost Speed: {movement.get('time_boost_speed', 0):.1f}s")
        print(f"Time Slow Speed: {movement.get('time_slow_speed', 0):.1f}s")
        print(f"Time on Ground: {movement.get('time_ground', 0):.1f}s")
        print(f"Time in Air (Low): {movement.get('time_low_air', 0):.1f}s")
        print(f"Time in Air (High): {movement.get('time_high_air', 0):.1f}s")
    
    if 'positioning' in stats['stats']:
        print("\n--- Positioning Stats (per game) ---")
        positioning = stats['stats']['positioning']
        print(f"Time Defensive Third: {positioning.get('time_defensive_third', 0):.1f}s")
        print(f"Time Neutral Third: {positioning.get('time_neutral_third', 0):.1f}s")
        print(f"Time Offensive Third: {positioning.get('time_offensive_third', 0):.1f}s")
        print(f"Time Behind Ball: {positioning.get('time_behind_ball', 0):.1f}s")
        print(f"Time In Front of Ball: {positioning.get('time_infront_ball', 0):.1f}s")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "GWLlosa"
    
    try:
        stats = get_player_stats(username, num_replays=20)
        display_stats(stats)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
