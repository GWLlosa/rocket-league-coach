# Rocket League Coach 🚀⚽

> Automated Rocket League coaching system with personalized win/loss correlation analysis

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What Makes This Different

Unlike generic coaching advice, Rocket League Coach analyzes **your specific playing patterns** to identify what separates your wins from your losses. Instead of telling you to "improve boost management," it might say:

> "In your wins, you maintain 55 boost on average, but in losses only 35. Your winning games show significantly better boost discipline - focus on maintaining that 50+ boost level."

## ✨ Key Features

- **🧠 Dual Insight Engine**: Rule-based benchmarks + personalized win/loss correlations
- **📊 Statistical Analysis**: Confidence intervals and effect size calculations
- **⚡ Fast Processing**: Analyze 10 games in under 5 minutes
- **🎮 Ballchasing Integration**: Automatic replay fetching and parsing
- **📈 12 Core Metrics**: From mechanical skills to tactical awareness
- **🌐 Web Interface**: Clean, responsive UI with real-time progress
- **🐳 Docker Ready**: One-command deployment

## 🏁 Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- [Ballchasing.com API key](https://ballchasing.com/upload)

### Local Development

```bash
# Clone the repository
git clone https://github.com/GWLlosa/rocket-league-coach.git
cd rocket-league-coach

# Quick setup
make quickstart

# Edit .env with your Ballchasing API key
cp .env.example .env
# Edit BALLCHASING_API_KEY=your_key_here

# Start development server
make dev
```

Visit `http://localhost:8000` and enter a gamertag to get started!

### Docker Development

```bash
# Start with Docker Compose
make dev-docker

# Or manually
docker-compose up --build
```

### Production Deployment

```bash
# Deploy to production
cp .env.example production.env
# Edit production.env with production settings
make docker-prod
```

## 📋 How It Works

### 1. Data Collection
- Fetches last 10 ranked games from Ballchasing.com
- Parses replays using Carball library
- Extracts 12 performance metrics per game

### 2. Statistical Analysis
- **Rule-Based Insights**: Compare against rank benchmarks
- **Correlation Analysis**: Identify winning vs losing patterns
- **Significance Testing**: Only report statistically significant findings

### 3. Personalized Coaching
- Prioritizes insights by confidence and impact
- Provides specific, actionable recommendations
- Shows statistical confidence for each insight

## 📊 Analyzed Metrics

### Tier 1: High-Confidence Mechanical Skills
- `avg_speed` - Average movement speed
- `time_supersonic_speed` - Time at maximum speed
- `shooting_percentage` - Goals per shot
- `avg_amount` - Average boost level
- `time_zero_boost` - Time without boost
- `time_defensive_third` - Defensive positioning

### Tier 2: Medium-Confidence Tactical Skills
- `avg_distance_to_ball` - Ball proximity
- `time_behind_ball` - Rotation discipline
- `amount_overfill` - Boost efficiency
- `saves` - Defensive actions

### Tier 3: Advanced Team-Dependent Metrics
- `time_most_back` - Last defender time
- `assists` - Team play contribution

## 🔧 Development Commands

```bash
make help           # Show all available commands
make setup          # Install dependencies and setup environment
make dev            # Start development server with hot reload
make test           # Run test suite with coverage
make lint           # Code formatting and quality checks
make docker-build   # Build production Docker image
make deploy         # Deploy to production
make clean          # Clean up temporary files
```

## 🏗️ Architecture

```
Input (Gamertag) → Ballchasing API → Carball Analysis → Statistical Engine → Coaching Logic → Web Interface
```

### Core Components
- **Ballchasing Client**: Rate-limited API integration
- **Carball Processor**: Replay parsing and metric extraction
- **Statistical Analyzer**: Win/loss correlation analysis
- **Coaching Engine**: Dual insight generation
- **Web Interface**: FastAPI backend + responsive frontend

## 📁 Project Structure

```
rocket-league-coach/
├── src/
│   ├── api/              # External API integrations
│   ├── analysis/         # Replay processing and statistics
│   ├── data/             # Data management and caching
│   ├── services/         # Business logic orchestration
│   ├── web/              # Web interface and API endpoints
│   └── main.py           # Application entry point
├── tests/                # Test suite
├── deploy/               # Deployment scripts
├── scripts/              # Utility scripts
├── docker-compose.yml    # Development environment
├── docker-compose.prod.yml # Production environment
└── Makefile              # Development commands
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run with verbose output
make test-verbose

# Run specific test file
pytest tests/test_statistical_analyzer.py -v

# Check code coverage
pytest --cov=src --cov-report=html
```

## 📈 Example Output

```
🎮 Analysis for GWLlosa (Diamond 2)

🏆 YOUR WINNING PATTERNS
• Boost Management: In wins, you maintain 52 boost avg vs 34 in losses (High confidence)
• Speed Control: 15% more supersonic time in wins - maintain momentum! (Medium confidence)
• Positioning: 23% more time in defensive third during wins (High confidence)

⚡ GENERAL IMPROVEMENTS
• Shooting accuracy below Diamond average (12% vs 18%)
• Consider training packs: "Ultimate Shooting" by Poquito
• Boost efficiency could improve - avoid overfill waste

📊 Statistical Confidence: 8/10 insights have p < 0.05
```

## 🔒 Environment Variables

Key configuration options (see `.env.example` for full list):

```env
BALLCHASING_API_KEY=your_api_key_here
ENVIRONMENT=development
LOG_LEVEL=INFO
DEFAULT_GAMES_COUNT=10
MIN_SAMPLE_SIZE_FOR_CORRELATION=5
STATISTICAL_SIGNIFICANCE_THRESHOLD=0.05
```

## 🚀 Deployment

### Ubuntu Server Setup

```bash
# Clone repository
git clone https://github.com/GWLlosa/rocket-league-coach.git
cd rocket-league-coach

# Setup production environment
cp production.env.example .env
# Edit .env with production settings

# Run setup script
./scripts/production-setup.sh

# Deploy
./deploy/deploy.sh
```

### Health Monitoring

```bash
# Check application health
curl http://localhost:8000/health

# View logs
make logs

# Monitor with Docker
docker-compose -f docker-compose.prod.yml logs -f
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `make test`
5. Submit a pull request

## 📝 API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Core Endpoints

```
POST /api/analyze
GET  /api/analysis/{analysis_id}
GET  /api/analysis/{analysis_id}/status
GET  /health
```

## 🔬 Statistical Methodology

### Correlation Analysis
- Uses Welch's t-test for unequal variances
- Cohen's d for effect size calculation
- Bonferroni correction for multiple comparisons
- Minimum sample size: 5 wins AND 5 losses

### Confidence Levels
- **High**: p < 0.01, Cohen's d > 0.8
- **Medium**: p < 0.05, Cohen's d > 0.5
- **Low**: p < 0.1 (displayed with warning)

## 🐛 Troubleshooting

### Common Issues

**"No replays found"**
- Check gamertag spelling
- Ensure recent ranked games are uploaded to Ballchasing
- Verify API key is valid

**"Analysis failed"**
- Check internet connection
- Verify Ballchasing API status
- Ensure sufficient disk space for replay downloads

**"Statistical analysis inconclusive"**
- Need more games (minimum 5 wins + 5 losses)
- Try increasing game count in analysis

### Logs and Debugging

```bash
# View application logs
make logs

# Enable debug logging
export LOG_LEVEL=DEBUG
make dev

# Check Docker container logs
docker-compose logs app
```

## 📊 Performance Metrics

- **Processing Time**: ~30 seconds per 10 games
- **Memory Usage**: ~500MB peak during analysis
- **Storage**: ~50MB per 100 replays cached
- **Rate Limits**: 2 API calls/second, 500/hour

## 🔄 Roadmap

### Version 1.1
- [ ] Historical tracking and progress visualization
- [ ] Team analysis for group coaching
- [ ] Advanced mechanical metrics (aerial time, dribble distance)
- [ ] Integration with more replay platforms

### Version 1.2
- [ ] Machine learning prediction models
- [ ] Custom training pack recommendations
- [ ] Discord bot integration
- [ ] Mobile app

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Carball](https://github.com/SaltieRL/carball) for replay parsing
- [Ballchasing.com](https://ballchasing.com) for API and replay hosting
- [FastAPI](https://fastapi.tiangolo.com) for the web framework
- Rocket League community for inspiration and feedback

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/GWLlosa/rocket-league-coach/issues)
- **Email**: gwllosa@gmail.com
- **Discord**: Join the [Rocket League Coach Community](https://discord.gg/rocketleague)

---

**Made with ❤️ for the Rocket League community**

*Boost your game with data-driven insights!*
