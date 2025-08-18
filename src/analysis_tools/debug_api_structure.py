#!/usr/bin/env python3
"""
Debug script to find the correct location of team scores in Ballchasing API response.
Run this in the container to explore the API response structure.
"""

import os
import sys
import json
import requests
from typing import Dict, Any

def explore_replay_structure(username: str):
    """Fetch a replay and explore its structure to find score data."""
    
    api_key = os.environ.get('BALLCHASING_API_KEY')
    if not api_key:
        print("Error: BALLCHASING_API_KEY not found in environment")
        return
    
    headers = {'Authorization': api_key}
    
    # Get recent replays for the player
    search_url = 'https://ballchasing.com/api/replays'
    params = {
        'player-name': username,
        'count': 1  # Just get one replay for exploration
    }
    
    response = requests.get(search_url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"Error fetching replays: {response.status_code}")
        return
    
    data = response.json()
    if not data.get('list'):
        print(f"No replays found for {username}")
        return
    
    replay_id = data['list'][0]['id']
    print(f"Fetching replay: {replay_id}")
    
    # Get full replay details
    replay_url = f'https://ballchasing.com/api/replays/{replay_id}'
    replay_response = requests.get(replay_url, headers=headers)
    
    if replay_response.status_code != 200:
        print(f"Error fetching replay details: {replay_response.status_code}")
        return
    
    replay = replay_response.json()
    
    print("\n" + "="*60)
    print("EXPLORING REPLAY STRUCTURE FOR SCORE DATA")
    print("="*60)
    
    # Look for score in different possible locations
    print("\n1. Top-level fields:")
    for key in replay.keys():
        if 'score' in key.lower() or 'goal' in key.lower():
            print(f"  - {key}: {replay[key]}")
    
    print("\n2. Blue team structure:")
    if 'blue' in replay:
        blue = replay['blue']
        print(f"  Keys in 'blue': {list(blue.keys())}")
        for key in blue.keys():
            if 'score' in key.lower() or 'goal' in key.lower():
                print(f"  - blue['{key}']: {blue[key]}")
    
    print("\n3. Orange team structure:")
    if 'orange' in replay:
        orange = replay['orange']
        print(f"  Keys in 'orange': {list(orange.keys())}")
        for key in orange.keys():
            if 'score' in key.lower() or 'goal' in key.lower():
                print(f"  - orange['{key}']: {orange[key]}")
    
    # Check if scores might be in team stats
    print("\n4. Team stats:")
    if 'blue' in replay and 'stats' in replay['blue']:
        print(f"  Blue team stats: {replay['blue']['stats']}")
    if 'orange' in replay and 'stats' in replay['orange']:
        print(f"  Orange team stats: {replay['orange']['stats']}")
    
    # Look for the actual winner/loser information
    print("\n5. Looking for winner/result fields:")
    def find_keys_with_terms(obj, terms, path=""):
        """Recursively find keys containing specific terms."""
        results = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = str(key).lower()
                if any(term in key_lower for term in terms):
                    results.append(f"{path}.{key}" if path else key)
                    print(f"  Found: {path}.{key} = {value}" if path else f"  Found: {key} = {value}")
                if isinstance(value, dict):
                    results.extend(find_keys_with_terms(value, terms, f"{path}.{key}" if path else key))
        return results
    
    score_terms = ['score', 'goal', 'win', 'winner', 'result']
    found_keys = find_keys_with_terms(replay, score_terms)
    
    # Save full structure for reference
    print("\n6. Saving full replay structure to /tmp/replay_structure.json")
    with open('/tmp/replay_structure.json', 'w') as f:
        json.dump(replay, f, indent=2)
    print("  You can examine the full structure with: cat /tmp/replay_structure.json | less")
    
    # Try to determine the winner based on what we found
    print("\n" + "="*60)
    print("DETERMINING WINNER")
    print("="*60)
    
    # Common patterns in Ballchasing API
    if 'blue' in replay and 'orange' in replay:
        # Method 1: Check for goals in team data
        blue_goals = replay.get('blue', {}).get('goals', None)
        orange_goals = replay.get('orange', {}).get('goals', None)
        
        if blue_goals is not None and orange_goals is not None:
            print(f"Method 1 - Team goals: Blue {blue_goals} - Orange {orange_goals}")
            winner = 'blue' if blue_goals > orange_goals else 'orange' if orange_goals > blue_goals else 'tie'
            print(f"  Winner: {winner}")
        
        # Method 2: Check team stats
        blue_stats_goals = replay.get('blue', {}).get('stats', {}).get('core', {}).get('goals', None)
        orange_stats_goals = replay.get('orange', {}).get('stats', {}).get('core', {}).get('goals', None)
        
        if blue_stats_goals is not None and orange_stats_goals is not None:
            print(f"Method 2 - Team stats.core.goals: Blue {blue_stats_goals} - Orange {orange_stats_goals}")
            winner = 'blue' if blue_stats_goals > orange_stats_goals else 'orange' if orange_stats_goals > orange_stats_goals else 'tie'
            print(f"  Winner: {winner}")
        
        # Method 3: Sum player goals
        blue_player_goals = sum(p.get('stats', {}).get('core', {}).get('goals', 0) 
                              for p in replay.get('blue', {}).get('players', []))
        orange_player_goals = sum(p.get('stats', {}).get('core', {}).get('goals', 0) 
                                for p in replay.get('orange', {}).get('players', []))
        print(f"Method 3 - Sum of player goals: Blue {blue_player_goals} - Orange {orange_player_goals}")
        winner = 'blue' if blue_player_goals > orange_player_goals else 'orange' if orange_player_goals > orange_player_goals else 'tie'
        print(f"  Winner: {winner}")

if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "GWLlosa"
    print(f"Exploring replay structure for player: {username}")
    explore_replay_structure(username)
