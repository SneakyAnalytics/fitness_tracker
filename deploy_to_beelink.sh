#!/bin/bash
# Deploy Playwright fix to Beelink
# Run this script from your local machine

set -e

BEELINK_IP="100.117.194.8"
BEELINK_USER="rakej"
PROJECT_DIR="/home/rakej/fitness_tracker"

echo "=================================================="
echo "🚀 Deploying Playwright Fix to Beelink"
echo "=================================================="
echo ""
echo "Target: $BEELINK_USER@$BEELINK_IP"
echo "Project: $PROJECT_DIR"
echo ""

# Check if we can reach Beelink
echo "1️⃣  Testing connection to Beelink..."
if ping -c 1 -W 2 $BEELINK_IP > /dev/null 2>&1; then
    echo "   ✅ Beelink is reachable"
else
    echo "   ❌ Cannot reach Beelink at $BEELINK_IP"
    echo "   Check Tailscale connection and try again"
    exit 1
fi

# SSH into Beelink and run deployment
echo ""
echo "2️⃣  Connecting to Beelink and deploying..."
echo "   (This will take 5-10 minutes for Chromium download)"
echo ""

ssh $BEELINK_USER@$BEELINK_IP << 'ENDSSH'
    set -e
    
    # Navigate to project
    cd /home/rakej/fitness_tracker
    
    echo "📦 Pulling latest changes..."
    git pull origin main
    
    echo ""
    echo "🛑 Stopping containers..."
    docker-compose down
    
    echo ""
    echo "🔨 Rebuilding with Playwright/Chromium..."
    echo "   (Downloading ~200MB Chromium, please wait...)"
    docker-compose build --no-cache
    
    echo ""
    echo "▶️  Starting containers..."
    docker-compose up -d
    
    echo ""
    echo "⏳ Waiting for services to start (30s)..."
    sleep 30
    
    echo ""
    echo "✅ Verifying Playwright installation..."
    docker exec fitness-tracker-ui python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright Python package: OK')" || echo "❌ Playwright check failed"
    
    echo ""
    echo "✅ Checking Chromium browser..."
    docker exec fitness-tracker-ui sh -c "ls -la /root/.cache/ms-playwright/chromium-* 2>/dev/null | head -1" && echo "✅ Chromium browser: Installed" || echo "⚠️  Chromium browser: Not found (rebuild may have failed)"
    
    echo ""
    echo "✅ Checking API health..."
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null && echo "✅ API: Healthy" || echo "⚠️  API: Not responding yet"
    
    echo ""
    echo "📊 Container status:"
    docker-compose ps
    
    echo ""
    echo "=================================================="
    echo "✅ DEPLOYMENT COMPLETE"
    echo "=================================================="
    echo ""
    echo "🌐 Access your application:"
    echo "   Streamlit: http://100.117.194.8:8501"
    echo "   API: http://100.117.194.8:8000"
    echo ""
    echo "🧪 Test TrainingPeaks sync in Streamlit now!"
    echo ""
ENDSSH

echo ""
echo "=================================================="
echo "🎉 Deployment script complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Open http://100.117.194.8:8501 in your browser"
echo "2. Navigate to TrainingPeaks sync page"
echo "3. Click sync button - should work without errors now"
echo ""
echo "If issues persist, check logs:"
echo "  ssh $BEELINK_USER@$BEELINK_IP"
echo "  cd $PROJECT_DIR"
echo "  docker-compose logs -f streamlit"
echo ""
