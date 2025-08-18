# 🚀 Rocket League Coach

An automated Rocket League coaching system that analyzes player performance using Ballchasing.com API and Carball library to provide personalized improvement suggestions through both rule-based benchmarks and win/loss correlation analysis.

## ✨ Features

### 🎯 **Dual Insight Engine**
- **Rule-Based Coaching**: Compare your metrics against established rank benchmarks
- **Win/Loss Correlation Analysis**: Identify your personal patterns that differentiate winning vs losing performance

### 📊 **Comprehensive Analysis**
- **12 Core Metrics**: Speed, boost management, positioning, shooting accuracy, and more
- **Statistical Confidence**: p-values, effect sizes (Cohen's d), and confidence indicators
- **Personalized Insights**: "In your wins, you maintain 55 boost on average, but in losses only 35"

### 🎮 **Easy to Use**
- **Rich CLI Interface**: Beautiful terminal interface with progress bars and colored output
- **Automatic Caching**: Intelligent replay and result caching for fast repeated analysis
- **Real-time Progress**: Track analysis progress through all processing steps

### 🔧 **Production Ready**
- **Docker Deployment**: Single-command deployment with Docker Compose
- **Health Monitoring**: Built-in health checks and system monitoring
- **Rate Limiting**: Respects Ballchasing.com API limits with automatic rate limiting

## 🏗️ Architecture

```
Gamertag Input → Ballchasing API → Replay Download → Carball Analysis → 
Statistical Engine → Coaching Logic → Rich CLI/Web Interface
```

### Core Components
- **Ballchasing Client**: API integration with rate limiting and caching
- **Carball Processor**: Replay parsing and metric extraction  
- **Statistical Analyzer**: Win/loss correlation analysis with confidence scoring
- **Coaching Engine**: Dual insight generation (rules + correlations)
- **CLI Interface**: Rich terminal interface with progress tracking
- **Cache System**: SQLite-based caching for replays and analysis results

## 🚀 Quick Start

### Prerequisites
- Ubuntu 20.04+ (or similar Linux distribution)
- Docker and Docker Compose
- Git
- Ballchasing.com API token (get one at https://ballchasing.com/)

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/GWLlosa/rocket-league-coach.git
cd rocket-league-coach

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment
Edit `.env` with your settings:
```bash
# Required: Get this from https://ballchasing.com/
BALLCHASING_API_TOKEN=your_ballchasing_api_token_here

# Application Settings
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# CORS Settings (default is fine)
ENABLE_CORS=true
CORS_ORIGINS=*

# Cache Settings (optional)
CACHE_TTL_HOURS=24
MAX_CACHE_SIZE_GB=5
```

### 3. Deploy with Docker
```bash
# Build and start the application
docker-compose -f docker-compose.prod.yml up -d --build
```

**Note:** During the Docker build, you may see red warning messages like:
```
debconf: unable to initialize frontend: Dialog
debconf: falling back to frontend: Readline
```
These are **harmless warnings** about terminal interaction during package installation and can be safely ignored. They do not affect the application functionality.

### 4. Test Your Deployment
```bash
# Check system health
curl http://localhost:8000/health

# Test dependencies are installed
docker-compose -f docker-compose.prod.yml exec rocket-league-coach bash /app/scripts/test-dependencies.sh

# Enter the container for CLI access
docker-compose -f docker-compose.prod.yml exec rocket-league-coach bash

# Inside container, test CLI
python -m src.cli health
```

## 📱 Usage Examples

### Basic Player Analysis

While the full CLI integration is being completed, you can use the analysis scripts directly:

```bash
# Enter the container
docker-compose -f docker-compose.prod.yml exec rocket-league-coach bash

# Run analysis for a player (replace with actual gamertag)
python << 'EOF'
import sys
sys.path.extend(['/app', '/app/src'])
from config import get_settings
import requests
from rich.console import Console
from rich.table import Table

console = Console()
settings = get_settings()

def analyze_player(player_name, num_games=10):
    headers = {'Authorization': settings.ballchasing_api_token}
    url = 'https://ballchasing.com/api/replays'
    params = {'player-name': player_name, 'count': num_games, 'sort-by': 'created', 'sort-dir': 'desc'}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        replays = data.get('list', [])
        
        if replays:
            console.print(f"[bold cyan]Found {len(replays)} replays for {player_name}[/bold cyan]")
            # Process replays here
        else:
            console.print(f"[yellow]No replays found for {player_name}[/yellow]")
    else:
        console.print(f"[red]API Error: {response.status_code}[/red]")

# Run analysis
player = input("Enter player name: ")
analyze_player(player)
EOF
```

### CLI Commands (when fully implemented)

```bash
# Quick analysis (recommended for first try)
python -m src.cli quick YourGamertag

# Full analysis with custom settings
python -m src.cli analyze YourGamertag --games 15 --force-refresh

# View cached game history
python -m src.cli history YourGamertag --limit 20

# Check cache statistics
python -m src.cli cache-stats

# System health check
python -m src.cli health
```

## 🔄 Deployment & Updates

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# Check status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

## 📊 Current Implementation Status

### ✅ Working Components
- Docker container with all dependencies
- FastAPI server with health checks
- Ballchasing.com API integration
- Basic player data fetching
- Configuration management
- Logging system

### 🚧 In Development
- Full CLI command integration
- Carball replay processing pipeline
- Statistical analysis engine
- Win/loss correlation analysis
- Coaching insight generation
- Cache management system

### 📋 Known Issues
- Some CLI commands show import errors (being fixed)
- Full analysis pipeline not yet connected
- Web UI not yet implemented

## 🏭 Production Features

### Health Monitoring
- **Health Endpoint**: `GET /health` - Application status
- **Container Health Checks**: Automatic restart on failure
- **Logging**: Comprehensive application logs in `/app/logs`

### Dependencies Included
- **Core**: FastAPI, Uvicorn, Pydantic
- **Data Processing**: NumPy, Pandas, SciPy
- **Rocket League**: Carball (replay analysis)
- **API**: Requests, aiohttp, aiofiles
- **CLI**: Click, Rich
- **Database**: SQLAlchemy

## 🔧 Development

### Local Development Setup
```bash
# Use development docker-compose
docker-compose up -d

# This mounts source code for live reloading
```

### Running Tests
```bash
# Inside container
python -m pytest tests/
```

### Project Structure
```
rocket-league-coach/
├── src/                          # Main application code
│   ├── main.py                   # FastAPI application
│   ├── cli.py                    # CLI interface
│   ├── config.py                 # Configuration
│   ├── api/                      # Ballchasing API client
│   ├── analysis/                 # Analysis engines
│   ├── data/                     # Data models
│   └── services/                 # Business logic
├── tests/                        # Test suite
├── scripts/                      # Utility scripts
├── docker-compose.yml            # Development compose
├── docker-compose.prod.yml       # Production compose
├── Dockerfile                    # Container definition
└── requirements.txt              # Python dependencies
```

## 🎯 Roadmap

1. **Phase 1** (Current): Basic infrastructure and API integration
2. **Phase 2**: Complete CLI implementation and replay processing
3. **Phase 3**: Statistical analysis and coaching insights
4. **Phase 4**: Web UI and advanced visualizations
5. **Phase 5**: Machine learning predictions and trends

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest tests/`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ballchasing.com** - For providing the comprehensive Rocket League replay API
- **Carball** - For the excellent replay analysis library
- **Rocket League Community** - For the extensive research on performance metrics

## 📞 Support

- **Issues**: Open an issue on GitHub
- **Documentation**: Check this README and code comments
- **Docker Issues**: See the Docker troubleshooting section below

## 🐳 Docker Troubleshooting

### Common Issues

**Red text during build (debconf warnings)**
- These are harmless warnings about terminal interaction
- The build will complete successfully despite these messages

**Container won't start**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs

# Rebuild from scratch
docker-compose -f docker-compose.prod.yml down
docker system prune -f
docker-compose -f docker-compose.prod.yml build --no-cache
```

**Permission errors**
```bash
# The container runs as non-root user 'app'
# Ensure proper permissions on mounted volumes
sudo chown -R 1000:1000 ./data ./logs
```

**Memory issues**
```bash
# Carball can be memory intensive
# Ensure Docker has enough memory (4GB+ recommended)
docker system info | grep Memory
```

---

**Ready to improve your Rocket League game?** 🚀

Get started with: `docker-compose -f docker-compose.prod.yml up -d --build`
