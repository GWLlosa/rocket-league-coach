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
- Ballchasing.com API token

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

# Cache Settings
CACHE_TTL_HOURS=24
MAX_CACHE_SIZE_GB=5
```

### 3. Deploy with One Command
```bash
# Make deployment script executable and run
chmod +x scripts/redeploy.sh
./scripts/redeploy.sh
```

The script will:
- Pull latest changes
- Build Docker containers
- Start the application
- Run comprehensive health checks
- Show you exactly how to test and use the system

### 4. Test Your Deployment
```bash
# Check system health
curl http://localhost:8000/health

# Test CLI interface
docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli health

# Analyze a player (replace with real gamertag)
docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli quick YourGamertag
```

## 📱 Usage Examples

### CLI Interface Commands

```bash
# Quick analysis (recommended for first try)
python -m src.cli quick GWLlosa

# Full analysis with custom settings
python -m src.cli analyze GWLlosa --games 15 --force-refresh

# View player's cached game history
python -m src.cli history GWLlosa --limit 20

# Check cache statistics and health
python -m src.cli cache-stats

# System health check
python -m src.cli health

# Clean up expired cache
python -m src.cli cache-cleanup
```

### Inside Docker Container
```bash
# Enter the container
docker-compose -f docker-compose.prod.yml exec rocket-league-coach bash

# Run any CLI command
python -m src.cli quick YourGamertag
```

## 🔄 Deployment & Updates

### Redeploy Scripts

We provide two deployment scripts for easy updates:

#### **Full Redeploy** (Recommended)
```bash
./scripts/redeploy.sh
```
- Pulls latest changes from GitHub
- Comprehensive cleanup and rebuild
- Full health checks and testing
- Detailed status reporting and troubleshooting

#### **Quick Redeploy** (Fast Updates)
```bash
./scripts/quick-redeploy.sh
```
- Fast pull and rebuild
- Basic health check
- Perfect for rapid iteration

### Manual Deployment
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# Check status
docker-compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

## 📊 Example Output

### CLI Analysis Results
```
🎯 Player Analysis Results for GWLlosa
Games Analyzed: 10 | Win Rate: 60.0% | Confidence: 85%

🔥 Top Priority Improvements:
  1. Boost Management Consistency
     In your wins, you maintain 52 boost on average, but in losses only 34.
     💡 Actions: Collect small boost pads, avoid overfill waste

💪 Key Strengths:
  ✅ Strong win rate of 60.0%
  ✅ Excellent shooting accuracy
  ✅ Good defensive positioning

📈 Primary Improvement Areas:
  🎯 Boost management and efficiency
  🎯 Speed and mechanical execution

Recent Trend: 📈 Improving
```

### Analysis Metrics
The system analyzes 12 core performance metrics across 3 tiers:

**Tier 1 (High-Confidence Causal)**
- Average Speed, Supersonic Time, Shooting %, Boost Management

**Tier 2 (Medium-Confidence Tactical)**  
- Ball Distance, Rotation, Boost Efficiency, Saves

**Tier 3 (Advanced Correlation)**
- Defensive Time, Assists

## 🏭 Production Features

### Health Monitoring
- **Health Endpoint**: `GET /health` - Application status
- **Cache Statistics**: Monitor cache performance and storage
- **System Diagnostics**: Memory, disk, and component health

### Caching System
- **Replay Caching**: Automatic replay file caching with TTL
- **Analysis Results**: Cache expensive analysis for 24 hours
- **Player History**: Track game outcomes and trends
- **Automatic Cleanup**: Remove expired cache entries

### Error Handling
- **Graceful Degradation**: Continue analysis even if some replays fail
- **Rate Limit Respect**: Automatic rate limiting for Ballchasing API
- **Retry Logic**: Exponential backoff for transient failures

## 🔧 Development

### Local Development Setup
```bash
# Create virtual environment
python3 -m venv rocket-league-env
source rocket-league-env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run locally
python -m src.main
```

### Development Commands
```bash
# Run tests
pytest tests/

# Code formatting
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Build Docker image
docker build -t rocket-league-coach .
```

### Project Structure
```
rocket-league-coach/
├── src/                          # Main application code
│   ├── main.py                   # FastAPI application entry
│   ├── cli.py                    # Rich CLI interface
│   ├── config.py                 # Configuration management
│   ├── api/                      # Ballchasing API integration
│   │   ├── ballchasing_client.py # API client with rate limiting
│   │   ├── models.py             # API data models
│   │   └── exceptions.py         # API-specific exceptions
│   ├── analysis/                 # Analysis engines
│   │   ├── replay_processor.py   # Carball integration
│   │   ├── metrics_extractor.py  # Performance metrics
│   │   ├── statistical_analyzer.py # Win/loss correlations
│   │   ├── coach.py              # Coaching insights
│   │   └── benchmarks.py         # Rank benchmarks
│   ├── data/                     # Data management
│   │   ├── cache_manager.py      # Caching system
│   │   └── models.py             # Data structures
│   └── services/                 # Main services
│       └── analysis_service.py   # Complete workflow orchestration
├── tests/                        # Test suite
├── scripts/                      # Deployment scripts
│   ├── redeploy.sh              # Full redeploy with testing
│   └── quick-redeploy.sh        # Fast redeploy
├── deploy/                       # Production deployment
├── docker-compose.prod.yml       # Production Docker Compose
├── Dockerfile                    # Container definition
└── requirements.txt              # Python dependencies
```

## 🎯 Key Innovation

### Personalized Correlation Analysis
Instead of generic advice like "improve boost management," the system provides **personalized insights**:

> "In your wins, you maintain 55 boost on average, but in losses only 35. Your winning games show significantly better boost discipline - focus on maintaining that 50+ boost level."

This approach identifies **your specific winning patterns** rather than applying generic advice.

## 📋 System Requirements

### Minimum Requirements
- **RAM**: 4GB (carball analysis is memory-intensive)
- **Storage**: 10GB (for replay caching)
- **CPU**: 2 cores
- **Network**: Stable internet for Ballchasing API

### Recommended Requirements
- **RAM**: 8GB or more
- **Storage**: 50GB (for extensive caching)
- **CPU**: 4 cores or more

## 🔍 Troubleshooting

### Common Issues

**Docker Build Fails**
```bash
# Clean Docker cache
docker system prune -f
./scripts/redeploy.sh
```

**Memory Issues**
```bash
# Check available memory
free -h
# Increase Docker memory limit
```

**API Token Issues**
```bash
# Verify your token in .env
cat .env | grep BALLCHASING_API_TOKEN
# Get token from https://ballchasing.com/
```

**Port Already in Use**
```bash
# Check what's using port 8000
netstat -tlnp | grep 8000
# Change PORT in .env file
```

### Logs and Debugging
```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker-compose.prod.yml logs rocket-league-coach

# Enter container for debugging
docker-compose -f docker-compose.prod.yml exec rocket-league-coach bash
```

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
- **Health Check**: Use `./scripts/redeploy.sh` for comprehensive system testing

---

**Ready to improve your Rocket League game?** 🚀

Get started with: `./scripts/redeploy.sh`
