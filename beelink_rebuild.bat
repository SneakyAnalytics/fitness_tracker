@echo off
REM Windows PowerShell script to rebuild Docker containers on Beelink
REM Run this ON the Beelink machine directly

echo ==================================================
echo Rebuilding Docker with Playwright/Chromium Fix
echo ==================================================
echo.

cd C:\Users\rakej\fitness_tracker

echo 1. Pulling latest changes from GitHub...
git pull origin main
echo.

echo 2. Stopping containers...
docker compose down
echo.

echo 3. Rebuilding containers (this takes 5-10 minutes)...
echo    Downloading Chromium (~200MB)...
docker compose build --no-cache
echo.

echo 4. Starting containers...
docker compose up -d
echo.

echo 5. Waiting for containers to start (30 seconds)...
timeout /t 30 /nobreak
echo.

echo 6. Checking container status...
docker ps
echo.

echo 7. Verifying Playwright installation...
docker exec fitness-tracker-ui python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
echo.

echo 8. Checking API health...
curl http://localhost:8000/health
echo.

echo ==================================================
echo Deployment Complete!
echo ==================================================
echo.
echo Test at: http://localhost:8501
echo.

pause
