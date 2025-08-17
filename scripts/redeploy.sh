#!/bin/bash

# Rocket League Coach - Redeploy Script
# This script pulls the latest changes and redeploys the application

set -e  # Exit on any error

echo "🚀 Rocket League Coach - Redeploy Script"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Error: docker-compose.prod.yml not found!"
    echo "   Please run this script from the rocket-league-coach directory"
    exit 1
fi

# Step 1: Pull latest changes
echo ""
echo "📥 Step 1: Pulling latest changes from GitHub..."
git pull origin main

if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Git pull failed. Continuing with current code..."
fi

# Step 2: Clean up previous build
echo ""
echo "🧹 Step 2: Cleaning up previous deployment..."
echo "   Stopping containers..."
docker-compose -f docker-compose.prod.yml down

echo "   Removing old images and containers..."
docker system prune -f

# Step 3: Build and deploy
echo ""
echo "🔨 Step 3: Building and deploying application..."
echo "   This may take a few minutes..."
docker-compose -f docker-compose.prod.yml up -d --build

# Step 4: Wait for startup
echo ""
echo "⏳ Step 4: Waiting for application to start..."
sleep 10

# Step 5: Check deployment status
echo ""
echo "🔍 Step 5: Checking deployment status..."

# Check if containers are running
echo "   Container status:"
docker-compose -f docker-compose.prod.yml ps

# Test health endpoint
echo ""
echo "   Testing health endpoint..."
HEALTH_CHECK=$(curl -s -w "%{http_code}" -o /tmp/health_response http://localhost:8000/health)

if [ "$HEALTH_CHECK" = "200" ]; then
    echo "   ✅ Health check passed!"
    echo "   Response: $(cat /tmp/health_response)"
    rm -f /tmp/health_response
else
    echo "   ❌ Health check failed (HTTP $HEALTH_CHECK)"
    echo "   Checking application logs..."
    docker-compose -f docker-compose.prod.yml logs --tail=20 rocket-league-coach
fi

# Test CLI
echo ""
echo "   Testing CLI interface..."
CLI_TEST=$(docker-compose -f docker-compose.prod.yml exec -T rocket-league-coach python -m src.cli health 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "   ✅ CLI interface working!"
else
    echo "   ❌ CLI interface test failed"
    echo "   Checking logs..."
    docker-compose -f docker-compose.prod.yml logs --tail=10 rocket-league-coach
fi

# Final status
echo ""
echo "🎯 Deployment Summary:"
echo "======================"

# Check if main service is running
MAIN_STATUS=$(docker-compose -f docker-compose.prod.yml ps -q rocket-league-coach)
if [ -n "$MAIN_STATUS" ]; then
    echo "✅ Application is running"
    echo "📍 Access points:"
    echo "   • Health check: http://localhost:8000/health"
    echo "   • API docs: http://localhost:8000/docs (if debug enabled)"
    echo "   • CLI: docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli --help"
    
    echo ""
    echo "🔧 Quick test commands:"
    echo "   • Check health: curl http://localhost:8000/health"
    echo "   • CLI health: docker-compose -f docker-compose.prod.yml exec rocket-league-coach python -m src.cli health"
    echo "   • View logs: docker-compose -f docker-compose.prod.yml logs -f"
    
    if [ -f ".env" ]; then
        if grep -q "BALLCHASING_API_TOKEN=your_ballchasing" .env; then
            echo ""
            echo "⚠️  Don't forget to set your BALLCHASING_API_TOKEN in .env file!"
        fi
    else
        echo ""
        echo "⚠️  Don't forget to create .env file with your configuration!"
    fi
    
else
    echo "❌ Application failed to start"
    echo "📋 Troubleshooting steps:"
    echo "   1. Check logs: docker-compose -f docker-compose.prod.yml logs"
    echo "   2. Check .env file exists and has correct values"
    echo "   3. Ensure Docker has enough memory (recommended: 4GB+)"
    echo "   4. Check if port 8000 is already in use: netstat -tlnp | grep 8000"
fi

echo ""
echo "🏁 Redeploy script completed!"
