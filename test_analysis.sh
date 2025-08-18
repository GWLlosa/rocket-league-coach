#!/bin/bash
# Test script for the fixed player analysis functionality
# Run this after rebuilding the Docker container

echo "=================================================="
echo "Rocket League Coach - Player Analysis Test"
echo "=================================================="
echo ""

# Check if docker-compose file exists
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "Error: docker-compose.prod.yml not found."
    echo "Please run this script from the repository root."
    exit 1
fi

# Test 1: Quick analysis using the PlayerStatsAnalyzer class
echo "Test 1: Testing PlayerStatsAnalyzer class..."
echo "--------------------------------------------------"
docker-compose -f docker-compose.prod.yml exec -T rocket-league-coach python -c "
import sys
try:
    from src.analysis import PlayerStatsAnalyzer
    analyzer = PlayerStatsAnalyzer()
    stats = analyzer.analyze_player('GWLlosa', 5)
    if stats:
        print(f'✓ Analysis successful!')
        print(f'  Games analyzed: {stats.get(\"games_analyzed\", 0)}')
        print(f'  Win rate: {stats.get(\"win_rate\", 0):.1f}%')
        print(f'  Boost efficiency: {stats.get(\"boost_efficiency\", 0):.2f} actions/100 boost')
        print(f'  Shooting percentage: {stats.get(\"shooting_percentage\", 0):.1f}%')
    else:
        print('✗ No stats returned')
        sys.exit(1)
except Exception as e:
    print(f'✗ Error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✓ Test 1 passed!"
else
    echo "✗ Test 1 failed!"
fi

echo ""

# Test 2: Run the standalone analysis script
echo "Test 2: Testing standalone analysis script..."
echo "--------------------------------------------------"
docker-compose -f docker-compose.prod.yml exec -T rocket-league-coach python /app/src/analysis_tools/player_analysis.py GWLlosa

if [ $? -eq 0 ]; then
    echo "✓ Test 2 passed!"
else
    echo "✗ Test 2 failed!"
fi

echo ""

# Test 3: Check that win/loss detection is working
echo "Test 3: Verifying win/loss detection..."
echo "--------------------------------------------------"
docker-compose -f docker-compose.prod.yml exec -T rocket-league-coach python -c "
from src.analysis import PlayerStatsAnalyzer
analyzer = PlayerStatsAnalyzer()
stats = analyzer.analyze_player('GWLlosa', 10)
if stats and stats.get('games_analyzed', 0) > 0:
    wins = stats.get('wins', 0)
    losses = stats.get('losses', 0)
    ties = stats.get('ties', 0)
    total = wins + losses + ties
    if total > 0:
        print(f'✓ Win/loss detection working!')
        print(f'  Wins: {wins}, Losses: {losses}, Ties: {ties}')
        print(f'  Total games: {total}')
    else:
        print('✗ No wins, losses, or ties detected')
else:
    print('✗ Failed to get stats')
"

echo ""
echo "=================================================="
echo "Test suite complete!"
echo ""
echo "To run more detailed debugging:"
echo "  docker-compose -f docker-compose.prod.yml exec rocket-league-coach python /app/src/analysis_tools/debug_api_structure.py USERNAME"
echo ""
echo "To use in your own code:"
echo "  from src.analysis import PlayerStatsAnalyzer"
echo "  analyzer = PlayerStatsAnalyzer()"
echo "  stats = analyzer.analyze_player('username', num_replays=20)"
echo "=================================================="
