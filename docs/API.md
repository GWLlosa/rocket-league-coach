# 📡 API Documentation

This document covers the Rocket League Coach API endpoints and CLI interface.

## 🌐 Current API Endpoints

The application currently provides basic HTTP endpoints with full CLI functionality. The web interface (Phase 5) will expand these endpoints significantly.

### Base URL
```
http://localhost:8000
```

### Authentication
Currently no authentication required for basic endpoints. Future versions will support API keys.

---

## 📋 Available Endpoints

### Health Check
Check application health and status.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "rocket-league-coach", 
  "version": "1.0.0",
  "environment": "production",
  "components": {
    "cache": "healthy",
    "ballchasing_api": "healthy"
  },
  "uptime_seconds": 3600,
  "memory_usage_mb": 256.5
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

### Service Information
Get basic service information and available endpoints.

**Endpoint:** `GET /`

**Response:**
```json
{
  "service": "Rocket League Coach",
  "description": "Automated coaching system with win/loss correlation analysis",
  "version": "1.0.0", 
  "docs": "/docs",
  "health": "/health"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

### API Documentation (Development)
Interactive API documentation (only available when `DEBUG=true`).

**Endpoint:** `GET /docs`

Only available in development/debug mode.

---

## 🖥️ CLI Interface

The CLI provides full functionality for analysis and system management.

### Usage Pattern
```bash
# Inside Docker container
docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli COMMAND

# Local development
python -m src.cli COMMAND
```

### Available Commands

#### Analysis Commands

##### Quick Analysis
Perform quick analysis with default settings.

```bash
python -m src.cli quick GAMERTAG
```

**Options:**
- `GAMERTAG`: Player's gamertag (required)

**Example:**
```bash
python -m src.cli quick GWLlosa
```

**Output:**
```
📊 Quick Summary for GWLlosa
Win Rate: 65.0% (7W-3L)
Confidence: 85%

🎯 Top Recommendation:
   Boost Management Consistency
   In your wins, you maintain 52 boost on average, but in losses only 34.
```

##### Full Analysis
Comprehensive analysis with custom settings.

```bash
python -m src.cli analyze GAMERTAG [OPTIONS]
```

**Options:**
- `GAMERTAG`: Player's gamertag (required)
- `--games, -g`: Number of games to analyze (1-50, default: 10)
- `--force-refresh, -f`: Force refresh of cached data
- `--raw-data`: Include raw analysis data in output  
- `--output, -o`: Save results to file (JSON format)

**Examples:**
```bash
# Analyze 15 games with forced refresh
python -m src.cli analyze GWLlosa --games 15 --force-refresh

# Save results to file
python -m src.cli analyze GWLlosa --output results.json

# Include raw data for debugging
python -m src.cli analyze GWLlosa --raw-data
```

#### Data Management Commands

##### Player History
View cached game history for a player.

```bash
python -m src.cli history GAMERTAG [OPTIONS]
```

**Options:**
- `GAMERTAG`: Player's gamertag (required)
- `--limit, -l`: Number of games to show (default: 20)

**Example:**
```bash
python -m src.cli history GWLlosa --limit 10
```

##### Cache Statistics
View cache health and statistics.

```bash
python -m src.cli cache-stats
```

**Output:**
```
Cache Health
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
┃ Component      ┃ Entries ┃   Size ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
│ Replay Cache   │      25 │ 150 MB │
│ Analysis Cache │       5 │  2.1 MB│
│ Player History │      10 │    N/A │
│ Total          │         │ 152 MB │
└────────────────┴─────────┴────────┘
```

##### Cache Cleanup
Clean up expired cache entries.

```bash
python -m src.cli cache-cleanup
```

**Output:**
```
✅ Cleanup completed!
Removed 3 expired replays
Removed 1 expired analysis results
Removed 4 files total
```

##### Cache Clear
Clear all cached data (with confirmation).

```bash
python -m src.cli cache-clear
```

**Interactive confirmation required for safety.**

#### System Commands

##### Health Check
Check system health and component status.

```bash
python -m src.cli health
```

**Output:**
```
System Health Check
Configuration: ✅ OK
Cache System: ✅ OK
Analysis Service: ✅ OK

Directory Status:
Replays: /app/data/replays
Cache: /app/data/cache
Player Data: /app/data/players
```

---

## 🔮 Future API Endpoints (Phase 5)

The following endpoints will be added in the web interface phase:

### Analysis Endpoints

#### Start Analysis
**Endpoint:** `POST /api/analyze`

**Request Body:**
```json
{
  "gamertag": "GWLlosa",
  "num_games": 10,
  "force_refresh": false,
  "include_raw_data": false
}
```

**Response:**
```json
{
  "analysis_id": "uuid-here",
  "status": "started",
  "estimated_duration_seconds": 120
}
```

#### Get Analysis Status
**Endpoint:** `GET /api/analysis/{analysis_id}/status`

**Response:**
```json
{
  "analysis_id": "uuid-here",
  "status": "processing",
  "progress": 65.0,
  "current_step": "Processing replay 7/10",
  "estimated_completion": "2024-01-01T12:05:00Z"
}
```

#### Get Analysis Results
**Endpoint:** `GET /api/analysis/{analysis_id}`

**Response:**
```json
{
  "analysis_id": "uuid-here",
  "gamertag": "GWLlosa",
  "status": "completed",
  "results": {
    "total_games": 10,
    "win_rate": 65.0,
    "confidence_score": 0.85,
    "top_priority_insights": [...],
    "correlation_insights": [...],
    "rule_based_insights": [...]
  }
}
```

### Data Endpoints

#### Player History
**Endpoint:** `GET /api/players/{gamertag}/history`

**Query Parameters:**
- `limit`: Number of games (default: 20)
- `days_back`: Only return games from this many days back

#### Cache Management
**Endpoint:** `GET /api/cache/stats`
**Endpoint:** `POST /api/cache/cleanup`
**Endpoint:** `DELETE /api/cache` (with confirmation)

---

## 📊 Data Models

### Analysis Request
```json
{
  "gamertag": "string",
  "num_games": "integer (1-50)",
  "force_refresh": "boolean",
  "include_raw_data": "boolean"
}
```

### Player Metrics
```json
{
  "avg_speed": "float",
  "time_supersonic_speed": "float", 
  "shooting_percentage": "float (0-1)",
  "avg_amount": "float (0-100)",
  "time_zero_boost": "float",
  "time_defensive_third": "float",
  "avg_distance_to_ball": "float",
  "time_behind_ball": "float",
  "amount_overfill": "float",
  "saves": "integer",
  "time_most_back": "float",
  "assists": "integer",
  "game_duration": "float"
}
```

### Coaching Insight
```json
{
  "insight_type": "rule_based|correlation",
  "metric_name": "string",
  "metric_tier": "tier_1|tier_2|tier_3",
  "title": "string",
  "message": "string",
  "priority": "integer (1-5)",
  "current_performance": "float",
  "target_performance": "float",
  "improvement_potential": "float",
  "specific_actions": ["string"],
  "practice_drills": ["string"]
}
```

### Statistical Result
```json
{
  "metric_name": "string",
  "metric_tier": "tier_1|tier_2|tier_3",
  "win_mean": "float",
  "win_std": "float", 
  "win_count": "integer",
  "loss_mean": "float",
  "loss_std": "float",
  "loss_count": "integer",
  "p_value": "float (0-1)",
  "effect_size": "float",
  "confidence_level": "high|medium|low",
  "difference": "float",
  "difference_percentage": "float",
  "is_significant": "boolean"
}
```

---

## 🔧 CLI Configuration

### Global Options
Available for all CLI commands:

- `--debug`: Enable debug logging
- `--config-file PATH`: Use specific configuration file

**Example:**
```bash
python -m src.cli --debug analyze GWLlosa
```

### Environment Variables
CLI respects the same environment variables as the web service:

- `BALLCHASING_API_TOKEN`: Required for analysis
- `LOG_LEVEL`: Logging verbosity  
- `CACHE_TTL_HOURS`: Cache expiration
- `DEBUG`: Enable debug mode

---

## 🚨 Error Handling

### Common Error Responses

#### Invalid Gamertag
```json
{
  "error": "Validation Error",
  "message": "No replays found for player: InvalidPlayer",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Rate Limit Exceeded
```json
{
  "error": "Rate Limit Error", 
  "message": "Ballchasing API rate limit exceeded. Please try again later.",
  "retry_after_seconds": 300
}
```

#### Insufficient Data
```json
{
  "error": "Analysis Error",
  "message": "Insufficient data for reliable analysis. Need at least 5 wins and 5 losses.",
  "suggestion": "Try increasing the number of games to analyze."
}
```

### CLI Error Codes
- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: API error
- `4`: Insufficient data

---

## 📈 Usage Examples

### Complete Analysis Workflow
```bash
# 1. Check system health
python -m src.cli health

# 2. Quick analysis to test
python -m src.cli quick GWLlosa

# 3. Full analysis with more games
python -m src.cli analyze GWLlosa --games 20 --output detailed_results.json

# 4. Check what's cached
python -m src.cli cache-stats

# 5. View player history
python -m src.cli history GWLlosa --limit 15
```

### Batch Analysis Script
```bash
#!/bin/bash
# Analyze multiple players

players=("Player1" "Player2" "Player3")

for player in "${players[@]}"; do
    echo "Analyzing $player..."
    python -m src.cli analyze "$player" --output "results_$player.json"
    sleep 5  # Be nice to the API
done
```

### Monitoring Script
```bash
#!/bin/bash
# Check system health and cache status

echo "=== Health Check ==="
python -m src.cli health

echo -e "\n=== Cache Statistics ==="
python -m src.cli cache-stats

echo -e "\n=== Recent Analysis ==="
# Check if any analysis ran recently
python -m src.cli history SomePlayer --limit 5
```

---

## 🔗 Integration Examples

### Webhook Integration (Future)
```python
import requests

# Start analysis
response = requests.post('http://localhost:8000/api/analyze', json={
    'gamertag': 'GWLlosa',
    'num_games': 10
})

analysis_id = response.json()['analysis_id']

# Poll for completion
while True:
    status = requests.get(f'http://localhost:8000/api/analysis/{analysis_id}/status')
    if status.json()['status'] == 'completed':
        break
    time.sleep(10)

# Get results
results = requests.get(f'http://localhost:8000/api/analysis/{analysis_id}')
print(results.json())
```

### Discord Bot Integration (Future)
```python
import discord
import requests

@bot.command()
async def analyze(ctx, gamertag):
    # Start analysis
    response = requests.post('http://localhost:8000/api/analyze', json={
        'gamertag': gamertag,
        'num_games': 10
    })
    
    if response.status_code == 200:
        analysis_id = response.json()['analysis_id']
        await ctx.send(f"Analysis started for {gamertag}. Please wait...")
        
        # Poll and update
        # Implementation details...
```

---

**Documentation Version:** 1.0.0  
**Last Updated:** Phase 4 Implementation  
**Next Update:** Phase 5 - Web Interface
