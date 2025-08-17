#!/bin/bash

# Quick redeploy script - pulls latest and rebuilds
# For when you just want to get the latest version fast

set -e

echo "🚀 Quick Redeploy - Rocket League Coach"
echo "======================================"

# Pull latest
echo "📥 Pulling latest changes..."
git pull origin main

# Redeploy
echo "🔨 Rebuilding and restarting..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# Quick test
echo "⏳ Waiting for startup..."
sleep 5

echo "🔍 Testing..."
curl -s http://localhost:8000/health || echo "❌ Health check failed"

echo "✅ Quick redeploy complete!"
echo "📋 Check logs with: docker-compose -f docker-compose.prod.yml logs -f"
