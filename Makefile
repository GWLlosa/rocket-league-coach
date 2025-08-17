# Makefile for Rocket League Coach
# Provides convenient commands for development and deployment

.PHONY: help setup dev test lint docker-build docker-run deploy clean install check-env

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

# Default target
help: ## Show this help message
	@echo "$(BLUE)🚀 Rocket League Coach - Development Commands$(NC)"
	@echo "================================================"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Quick Start:$(NC)"
	@echo "  make setup    # Install dependencies and setup environment"
	@echo "  make dev      # Start development server"
	@echo "  make deploy   # Deploy to production with Docker"

# Environment setup
setup: check-env install ## Install dependencies and setup environment
	@echo "$(GREEN)✅ Setup complete!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run 'make dev' to start development server"

check-env: ## Check if required tools are installed
	@echo "$(BLUE)Checking environment...$(NC)"
	@command -v python3 >/dev/null 2>&1 || { echo "$(RED)❌ Python 3 is required$(NC)"; exit 1; }
	@command -v pip >/dev/null 2>&1 || { echo "$(RED)❌ pip is required$(NC)"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)❌ Docker is required for deployment$(NC)"; exit 1; }
	@echo "$(GREEN)✅ Environment check passed$(NC)"

install: ## Install Python dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate && pip install -r requirements.txt
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

# Development commands
dev: ## Start development server with hot reload
	@echo "$(BLUE)Starting development server...$(NC)"
	@if [ ! -f ".env" ]; then \
		echo "$(YELLOW)⚠️  .env file not found. Copying from .env.example$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)📝 Please edit .env with your settings$(NC)"; \
	fi
	@. venv/bin/activate && python -m src.main

cli: ## Access CLI interface (requires COMMAND argument)
	@echo "$(BLUE)Rocket League Coach CLI$(NC)"
	@. venv/bin/activate && python -m src.cli $(COMMAND)

# Example CLI commands for documentation
cli-help: ## Show CLI help
	@make cli COMMAND="--help"

cli-health: ## Check CLI health
	@make cli COMMAND="health"

cli-quick: ## Quick analysis (requires GAMERTAG argument)
	@if [ -z "$(GAMERTAG)" ]; then \
		echo "$(RED)❌ Usage: make cli-quick GAMERTAG=YourGamertag$(NC)"; \
		exit 1; \
	fi
	@make cli COMMAND="quick $(GAMERTAG)"

# Testing
test: ## Run test suite
	@echo "$(BLUE)Running tests...$(NC)"
	@. venv/bin/activate && pytest tests/ -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	@. venv/bin/activate && pytest tests/ --cov=src --cov-report=html --cov-report=term

integration-test: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	@. venv/bin/activate && python tests/test_integration.py

# Code quality
lint: ## Run code formatting and quality checks
	@echo "$(BLUE)Running code quality checks...$(NC)"
	@. venv/bin/activate && black src/ tests/ --check
	@. venv/bin/activate && isort src/ tests/ --check-only
	@. venv/bin/activate && flake8 src/ tests/

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	@. venv/bin/activate && black src/ tests/
	@. venv/bin/activate && isort src/ tests/
	@echo "$(GREEN)✅ Code formatted$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	@. venv/bin/activate && mypy src/ --ignore-missing-imports

# Docker commands
docker-build: ## Build production Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	@docker build -t rocket-league-coach .
	@echo "$(GREEN)✅ Docker image built$(NC)"

docker-build-dev: ## Build development Docker image
	@echo "$(BLUE)Building development Docker image...$(NC)"
	@docker build -t rocket-league-coach:dev -f Dockerfile.dev .
	@echo "$(GREEN)✅ Development Docker image built$(NC)"

docker-run: ## Run application in Docker (development)
	@echo "$(BLUE)Starting Docker container...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)✅ Container started at http://localhost:8000$(NC)"

docker-run-prod: ## Run application in Docker (production)
	@echo "$(BLUE)Starting production Docker containers...$(NC)"
	@docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✅ Production containers started$(NC)"

docker-stop: ## Stop Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	@docker-compose down
	@docker-compose -f docker-compose.prod.yml down
	@echo "$(GREEN)✅ Containers stopped$(NC)"

docker-logs: ## View Docker container logs
	@docker-compose -f docker-compose.prod.yml logs -f

docker-shell: ## Access shell in running container
	@docker-compose -f docker-compose.prod.yml exec rocket-league-coach bash

# Deployment commands
deploy: ## Deploy to production using redeploy script
	@echo "$(BLUE)🚀 Deploying to production...$(NC)"
	@chmod +x scripts/redeploy.sh
	@./scripts/redeploy.sh

quick-deploy: ## Quick deployment update
	@echo "$(BLUE)⚡ Quick deployment...$(NC)"
	@chmod +x scripts/quick-redeploy.sh
	@./scripts/quick-redeploy.sh

deploy-check: ## Check deployment health
	@echo "$(BLUE)Checking deployment...$(NC)"
	@curl -f http://localhost:8000/health || echo "$(RED)❌ Health check failed$(NC)"
	@docker-compose -f docker-compose.prod.yml ps

# Cache management
cache-stats: ## Show cache statistics
	@echo "$(BLUE)Cache Statistics:$(NC)"
	@docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli cache-stats

cache-cleanup: ## Clean up expired cache
	@echo "$(BLUE)Cleaning up cache...$(NC)"
	@docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli cache-cleanup

cache-clear: ## Clear all cache (interactive confirmation)
	@echo "$(YELLOW)⚠️  This will clear ALL cached data!$(NC)"
	@docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli cache-clear

# Maintenance
clean: ## Clean up build artifacts and caches
	@echo "$(BLUE)Cleaning up...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

clean-docker: ## Clean up Docker images and containers
	@echo "$(BLUE)Cleaning Docker resources...$(NC)"
	@docker system prune -f
	@echo "$(GREEN)✅ Docker cleanup complete$(NC)"

# Backup and restore
backup: ## Backup application data and config
	@echo "$(BLUE)Creating backup...$(NC)"
	@mkdir -p backups
	@tar -czf backups/backup-$(shell date +%Y%m%d-%H%M%S).tar.gz data/ .env 2>/dev/null || echo "$(YELLOW)⚠️  Some files may not exist yet$(NC)"
	@echo "$(GREEN)✅ Backup created in backups/$(NC)"

# Development helpers
logs: ## View application logs
	@docker-compose -f docker-compose.prod.yml logs -f rocket-league-coach

status: ## Show current system status
	@echo "$(BLUE)System Status:$(NC)"
	@echo "$(YELLOW)Containers:$(NC)"
	@docker-compose -f docker-compose.prod.yml ps 2>/dev/null || echo "No containers running"
	@echo ""
	@echo "$(YELLOW)Health Check:$(NC)"
	@curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "Service not responding"
	@echo ""
	@echo "$(YELLOW)Disk Usage:$(NC)"
	@du -sh data/ 2>/dev/null || echo "No data directory yet"

# Analysis examples
analyze-example: ## Run example analysis (requires real gamertag)
	@if [ -z "$(GAMERTAG)" ]; then \
		echo "$(RED)❌ Usage: make analyze-example GAMERTAG=YourGamertag$(NC)"; \
		echo "$(YELLOW)Example: make analyze-example GAMERTAG=GWLlosa$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running example analysis for $(GAMERTAG)...$(NC)"
	@docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli analyze "$(GAMERTAG)" --games 5

# Documentation
docs: ## Generate/update documentation
	@echo "$(BLUE)Documentation is maintained in:$(NC)"
	@echo "  📖 README.md - Main documentation"
	@echo "  🚀 docs/DEPLOYMENT.md - Deployment guide"
	@echo "  📡 docs/API.md - API documentation"
	@echo ""
	@echo "$(YELLOW)API docs available at:$(NC) http://localhost:8000/docs (when DEBUG=true)"

# Database/cache inspection
db-shell: ## Access SQLite cache database
	@echo "$(BLUE)Accessing cache database...$(NC)"
	@docker-compose -f docker-compose.prod.yml exec rocket-league-coach sqlite3 /app/data/cache/cache.db

# Security
security-check: ## Run basic security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	@echo "$(YELLOW)Checking .env file permissions...$(NC)"
	@ls -la .env 2>/dev/null || echo "No .env file found"
	@echo "$(YELLOW)Checking for exposed secrets...$(NC)"
	@grep -r "api.*token" . --exclude-dir=.git --exclude-dir=venv --exclude="*.pyc" --exclude="Makefile" || echo "No exposed tokens found"

# Performance testing
perf-test: ## Run performance tests
	@echo "$(BLUE)Performance testing...$(NC)"
	@echo "$(YELLOW)Memory usage:$(NC)"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "No containers running"

# Environment info
env-info: ## Show environment information
	@echo "$(BLUE)Environment Information:$(NC)"
	@echo "$(YELLOW)Python Version:$(NC)"
	@python3 --version
	@echo "$(YELLOW)Docker Version:$(NC)"
	@docker --version
	@echo "$(YELLOW)Docker Compose Version:$(NC)"
	@docker-compose --version
	@echo "$(YELLOW)Git Version:$(NC)"
	@git --version
	@echo "$(YELLOW)Available Memory:$(NC)"
	@free -h 2>/dev/null || echo "Not available on this system"
	@echo "$(YELLOW)Disk Space:$(NC)"
	@df -h . 2>/dev/null || echo "Not available on this system"

# Complete workflow
all: setup test lint docker-build deploy ## Complete setup, test, and deploy workflow
	@echo "$(GREEN)🎉 Complete workflow finished!$(NC)"

# Development workflow
dev-setup: setup ## Setup for development
	@echo "$(GREEN)🔧 Development environment ready!$(NC)"
	@echo "$(YELLOW)Run 'make dev' to start the development server$(NC)"

# Production workflow  
prod-deploy: docker-build deploy deploy-check ## Complete production deployment
	@echo "$(GREEN)🚀 Production deployment complete!$(NC)"
