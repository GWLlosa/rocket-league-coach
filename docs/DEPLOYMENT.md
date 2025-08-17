# 🚀 Deployment Guide

This guide covers deploying the Rocket League Coach application to a production Ubuntu server.

## 📋 Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ (or similar Linux distribution)
- **RAM**: 4GB minimum, 8GB recommended (carball analysis is memory-intensive)
- **Storage**: 10GB minimum, 50GB recommended (for replay caching)
- **CPU**: 2 cores minimum, 4 cores recommended
- **Network**: Stable internet connection for Ballchasing API access

### Required Software
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    docker.io \
    docker-compose \
    curl \
    htop \
    build-essential

# Start and enable Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group (requires logout/login)
sudo usermod -aG docker $USER
```

### Ballchasing API Token
1. Visit [ballchasing.com](https://ballchasing.com/)
2. Create an account or sign in
3. Navigate to your profile settings
4. Generate an API token
5. Keep this token secure - you'll need it for configuration

## 🏗️ Initial Deployment

### Step 1: Clone Repository
```bash
# Clone the repository
git clone https://github.com/GWLlosa/rocket-league-coach.git
cd rocket-league-coach

# Verify files are present
ls -la
```

### Step 2: Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Environment Variables:**
```bash
# API Configuration (REQUIRED)
BALLCHASING_API_TOKEN=your_ballchasing_api_token_here

# Application Settings
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Directory Settings (auto-created)
REPLAYS_DIR=/app/data/replays
ANALYSIS_CACHE_DIR=/app/data/cache
PLAYER_DATA_DIR=/app/data/players

# Cache Configuration
CACHE_TTL_HOURS=24
MAX_CACHE_SIZE_GB=5

# CORS Settings
ENABLE_CORS=true
CORS_ORIGINS=["*"]
```

### Step 3: Initial Deployment
```bash
# Make deployment script executable
chmod +x scripts/redeploy.sh

# Run comprehensive deployment
./scripts/redeploy.sh
```

The deployment script will:
1. Pull latest changes from GitHub
2. Clean up any previous containers
3. Build Docker images with all dependencies
4. Start the application
5. Run comprehensive health checks
6. Display deployment status and next steps

## 🔄 Updates and Maintenance

### Quick Updates
For fast updates when new features are released:
```bash
./scripts/quick-redeploy.sh
```

### Full Redeployment
For comprehensive updates with full testing:
```bash
./scripts/redeploy.sh
```

### Manual Updates
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# Verify deployment
curl http://localhost:8000/health
```

## 🔍 Verification and Testing

### Health Checks
```bash
# API health check
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "rocket-league-coach",
#   "version": "1.0.0",
#   "environment": "production"
# }
```

### CLI Testing
```bash
# Test CLI inside container
docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli health

# Quick analysis test (replace with real gamertag)
docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli quick YourGamertag

# Cache statistics
docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli cache-stats
```

### Container Status
```bash
# Check running containers
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker-compose.prod.yml logs rocket-league-coach
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BALLCHASING_API_TOKEN` | API token from ballchasing.com | None | ✅ Yes |
| `ENVIRONMENT` | Deployment environment | development | No |
| `DEBUG` | Enable debug mode | false | No |
| `HOST` | Server host | 0.0.0.0 | No |
| `PORT` | Server port | 8000 | No |
| `LOG_LEVEL` | Logging level | INFO | No |
| `CACHE_TTL_HOURS` | Cache expiration hours | 24 | No |
| `MAX_CACHE_SIZE_GB` | Maximum cache size | 5 | No |

### Port Configuration
To change the application port:
```bash
# Edit .env file
PORT=8080

# Redeploy
./scripts/redeploy.sh
```

### Resource Limits
To adjust Docker resource limits, edit `docker-compose.prod.yml`:
```yaml
services:
  rocket-league-coach:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
```

## 🔒 Security Considerations

### API Token Security
- Never commit your API token to version control
- Use environment variables or secure secret management
- Rotate tokens periodically
- Monitor API usage

### Network Security
```bash
# Configure firewall (optional)
sudo ufw allow 22    # SSH
sudo ufw allow 8000  # Application port
sudo ufw enable

# For reverse proxy with SSL
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
```

### Container Security
- The application runs as non-root user inside container
- Only necessary ports are exposed
- No privileged mode required

## 🔍 Monitoring and Maintenance

### Log Management
```bash
# View real-time logs
docker-compose -f docker-compose.prod.yml logs -f

# View logs for specific time period
docker-compose -f docker-compose.prod.yml logs --since="1h"

# Save logs to file
docker-compose -f docker-compose.prod.yml logs > deployment.log
```

### System Monitoring
```bash
# Check system resources
htop

# Check disk usage
df -h

# Check Docker resource usage
docker stats

# Check cache directory size
du -sh data/cache/
```

### Cache Management
```bash
# View cache statistics
docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli cache-stats

# Clean expired cache
docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli cache-cleanup

# Clear all cache (WARNING: removes all cached data)
docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli cache-clear
```

## 🚨 Troubleshooting

### Common Issues

#### Build Failures
```bash
# Clean Docker cache and rebuild
docker system prune -f
./scripts/redeploy.sh
```

#### Memory Issues
```bash
# Check available memory
free -h

# Increase Docker memory limit
# Edit /etc/docker/daemon.json (create if doesn't exist):
{
  "default-runtime": "runc",
  "default-ulimits": {
    "memlock": {
      "hard": -1,
      "soft": -1
    }
  }
}

# Restart Docker
sudo systemctl restart docker
```

#### Port Already in Use
```bash
# Find what's using the port
netstat -tlnp | grep 8000

# Kill the process or change port in .env
PORT=8080
```

#### API Connection Issues
```bash
# Test API token
curl -H "Authorization: YOUR_TOKEN_HERE" https://ballchasing.com/api/

# Check network connectivity
ping ballchasing.com

# Verify DNS resolution
nslookup ballchasing.com
```

#### Permission Issues
```bash
# Ensure user is in docker group
groups $USER

# If not in docker group:
sudo usermod -aG docker $USER
# Log out and back in
```

### Debug Mode
To enable debug mode for troubleshooting:
```bash
# Edit .env
DEBUG=true
LOG_LEVEL=DEBUG

# Redeploy
./scripts/redeploy.sh

# View detailed logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Container Shell Access
```bash
# Enter running container
docker-compose -f docker-compose.prod.yml exec rocket-league-coach bash

# Run commands inside container
python -m src.cli --help
python -m src.cli health
```

## 🔄 Backup and Recovery

### Data Backup
```bash
# Backup cache and data
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Backup configuration
cp .env .env.backup
```

### Recovery
```bash
# Restore from backup
tar -xzf backup-YYYYMMDD.tar.gz

# Restore configuration
cp .env.backup .env

# Redeploy
./scripts/redeploy.sh
```

## 📊 Performance Optimization

### Cache Optimization
- Monitor cache hit rates with `cache-stats`
- Adjust `CACHE_TTL_HOURS` based on usage patterns
- Clean expired cache regularly

### Resource Optimization
- Monitor memory usage during analysis
- Adjust Docker resource limits as needed
- Consider SSD storage for better I/O performance

### API Optimization
- The client automatically handles rate limiting
- Monitor API usage in logs
- Consider upgrading Ballchasing account for higher limits

## 🆘 Getting Help

### Logs to Collect
When reporting issues, include:
```bash
# Application logs
docker-compose -f docker-compose.prod.yml logs rocket-league-coach > app.log

# System information
docker-compose -f docker-compose.prod.yml ps > containers.log
docker system df > docker-info.log
free -h > memory.log
df -h > disk.log
```

### Support Channels
- **GitHub Issues**: For bugs and feature requests
- **Documentation**: This guide and README.md
- **Health Checks**: Use `./scripts/redeploy.sh` for comprehensive diagnostics

---

**Need help?** Run `./scripts/redeploy.sh` for comprehensive system testing and diagnostics!
