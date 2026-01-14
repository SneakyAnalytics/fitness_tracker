#!/bin/bash
# Fix Playwright in Docker containers on Beelink
# This script rebuilds containers with Playwright/Chromium support

set -e  # Exit on error

echo "=================================================="
echo "🔧 Fixing TrainingPeaks Sync - Playwright Install"
echo "=================================================="
echo ""

# Check if running on Beelink (optional - can run anywhere)
if [ "$(hostname)" != "beelink" ]; then
    echo "⚠️  Warning: Not running on 'beelink' hostname"
    echo "   Current hostname: $(hostname)"
    echo "   Continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        echo "❌ Aborted"
        exit 1
    fi
fi

# Stop existing containers
echo "1️⃣  Stopping existing containers..."
docker-compose down

# Rebuild with new Dockerfile (includes Playwright)
echo ""
echo "2️⃣  Rebuilding Docker images (this will take 5-10 minutes)..."
echo "   Installing Chromium browser for TrainingPeaks automation..."
docker-compose build --no-cache

# Start containers
echo ""
echo "3️⃣  Starting containers..."
docker-compose up -d

# Wait for health checks
echo ""
echo "4️⃣  Waiting for services to be healthy..."
sleep 10

# Check container status
echo ""
echo "5️⃣  Container Status:"
docker-compose ps

# Test API health
echo ""
echo "6️⃣  Testing API health..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ API is healthy"
        break
    else
        echo "   ⏳ Waiting for API... (attempt $i/10)"
        sleep 3
    fi
done

# Test Streamlit
echo ""
echo "7️⃣  Testing Streamlit UI..."
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo "   ✅ Streamlit is running"
else
    echo "   ⚠️  Streamlit may still be starting up"
fi

# Verify Playwright is installed
echo ""
echo "8️⃣  Verifying Playwright installation in container..."
docker exec fitness-tracker-ui python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright is installed')" 2>&1 || echo "   ❌ Playwright not found"
docker exec fitness-tracker-ui sh -c "playwright --version" 2>&1 || echo "   ⚠️  Playwright CLI not found (this is OK if Python package works)"

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "🌐 Access your application:"
echo "   API:       http://localhost:8000"
echo "   Streamlit: http://localhost:8501"
echo ""
echo "📋 Useful commands:"
echo "   View logs:     docker-compose logs -f"
echo "   Stop:          docker-compose down"
echo "   Restart:       docker-compose restart"
echo ""
echo "🧪 Test TrainingPeaks sync in Streamlit UI now!"
echo ""
