.PHONY: help setup dev test lint docker-build docker-run docker-prod deploy clean install update

# Default target
help:
	@echo "Rocket League Coach - Available Commands:"
	@echo ""
	@echo "  setup        - Install dependencies and setup environment"
	@echo "  dev          - Start development server with hot reload"
	@echo "  test         - Run test suite with coverage"
	@echo "  lint         - Run code formatting and quality checks"
	@echo "  docker-build - Build production Docker image"
	@echo "  docker-run   - Run application in Docker (development)"
	@echo "  docker-prod  - Run application in Docker (production)"
	@echo "  deploy       - Deploy to production server"
	@echo "  clean        - Clean up temporary files and caches"
	@echo "  install      - Install/update dependencies"
	@echo "  update       - Update dependencies to latest versions"
	@echo ""

# Environment setup
setup: install
	@echo "🔧 Setting up development environment..."
	@cp .env.example .env || echo "⚠️  .env already exists"
	@mkdir -p logs replays analysis_cache player_data
	@echo "✅ Setup complete! Edit .env file with your configuration."

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@pip install --upgrade pip
	@pip install -r requirements.txt

# Update dependencies
update:
	@echo "🔄 Updating dependencies..."
	@pip install --upgrade pip
	@pip install --upgrade -r requirements.txt

# Development server
dev:
	@echo "🚀 Starting development server..."
	@uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Development with Docker Compose
dev-docker:
	@echo "🐳 Starting development server with Docker Compose..."
	@docker-compose up --build

# Run tests
test:
	@echo "🧪 Running tests with coverage..."
	@pytest --cov=src --cov-report=html --cov-report=term-missing tests/

# Run tests with verbose output
test-verbose:
	@echo "🧪 Running tests with verbose output..."
	@pytest -v --cov=src --cov-report=html --cov-report=term-missing tests/

# Code formatting and linting
lint:
	@echo "🔍 Running code quality checks..."
	@black src/ tests/ --check --diff
	@isort src/ tests/ --check-only --diff
	@flake8 src/ tests/

# Auto-fix code formatting
format:
	@echo "✨ Formatting code..."
	@black src/ tests/
	@isort src/ tests/

# Type checking
typecheck:
	@echo "🔍 Running type checks..."
	@mypy src/

# Docker build
docker-build:
	@echo "🐳 Building Docker image..."
	@docker build -t rocket-league-coach:latest .

# Docker run (development)
docker-run: docker-build
	@echo "🐳 Running Docker container (development)..."
	@docker run -p 8000:8000 --env-file .env rocket-league-coach:latest

# Docker production
docker-prod:
	@echo "🐳 Starting production environment..."
	@docker-compose -f docker-compose.prod.yml up --build -d

# Stop Docker production
docker-stop:
	@echo "🛑 Stopping production environment..."
	@docker-compose -f docker-compose.prod.yml down

# View logs
logs:
	@echo "📋 Viewing application logs..."
	@docker-compose -f docker-compose.prod.yml logs -f app

# Deploy to production
deploy:
	@echo "🚀 Deploying to production..."
	@./deploy/deploy.sh

# Clean temporary files
clean:
	@echo "🧹 Cleaning up..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -rf dist/
	@rm -rf build/
	@echo "✅ Cleanup complete!"

# Database operations (if implemented)
db-init:
	@echo "🗄️ Initializing database..."
	@python -m src.cli db init

db-migrate:
	@echo "🗄️ Running database migrations..."
	@python -m src.cli db migrate

# Analysis commands
analyze:
	@echo "🎮 Running analysis for player: $(PLAYER)"
	@python -m src.cli analyze $(PLAYER)

# Health check
health:
	@echo "🏥 Checking application health..."
	@curl -f http://localhost:8000/health || echo "❌ Application not responding"

# Show environment info
info:
	@echo "ℹ️ Environment Information:"
	@echo "Python: $(shell python --version)"
	@echo "Pip: $(shell pip --version)"
	@echo "Docker: $(shell docker --version)"
	@echo "Docker Compose: $(shell docker-compose --version)"

# Quick start for new developers
quickstart: setup
	@echo "🎯 Quick start complete!"
	@echo "1. Edit .env file with your Ballchasing API key"
	@echo "2. Run 'make dev' to start the development server"
	@echo "3. Visit http://localhost:8000 to use the application"
