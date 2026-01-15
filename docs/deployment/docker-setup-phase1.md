# 🚀 Phase 1: Local Docker Setup - Complete Guide

**Status**: Ready to start  
**Time Required**: 2-3 hours  
**Goal**: Get your fitness tracker running in Docker on your Mac

---

## Step 1: Install Docker Desktop

### 1.1 Download Docker Desktop

Visit: https://www.docker.com/products/docker-desktop

- Click "Download for Mac"
- Choose your Mac chip:
  - **Apple Silicon (M1/M2/M3)**: Download "Mac with Apple chip"
  - **Intel Mac**: Download "Mac with Intel chip"

### 1.2 Install Docker Desktop

1. Open the downloaded `.dmg` file
2. Drag Docker icon to Applications folder
3. Open Docker from Applications
4. Follow the setup wizard
5. Grant necessary permissions when prompted

### 1.3 Start Docker

1. Docker Desktop should start automatically
2. Look for Docker whale icon in menu bar
3. Wait until it says "Docker Desktop is running"

### 1.4 Verify Installation

Open Terminal and run:

```bash
docker --version
docker-compose --version
```

Expected output:

```
Docker version 24.x.x, build xxxxx
Docker Compose version v2.x.x
```

---

## Step 2: Prepare Your Project

### 2.1 Check Current Setup

```bash
cd /Users/jacobrobinson/fitness_tracker

# Verify files exist
ls -la Dockerfile docker-compose.yml docker-entrypoint.sh .dockerignore

# Check .env file (don't share output!)
cat .env | head -5

# Check database
ls -lh data/fitness_data.db

# Check Python version
python3 --version  # Should be 3.12.0
```

### 2.2 Stop Your Current App

If your app is currently running:

```bash
./bin/stop_app.sh

# Or manually:
pkill -f "streamlit run"
pkill -f "uvicorn"
```

Verify nothing is using ports 8000 or 8501:

```bash
lsof -i :8000
lsof -i :8501
# Should return nothing
```

---

## Step 3: Build Docker Images

### 3.1 First Build

```bash
cd /Users/jacobrobinson/fitness_tracker

# Build the images (this takes 3-5 minutes)
docker-compose build
```

You'll see output like:

```
[+] Building 180.5s (15/15) FINISHED
 => [internal] load build definition
 => => transferring dockerfile
 => [internal] load .dockerignore
 => [1/8] FROM python:3.12.0-slim
 => [2/8] WORKDIR /app
 ...
```

### 3.2 Verify Images Created

```bash
docker images | grep fitness
```

You should see:

```
fitness_tracker-fastapi    latest    ...
fitness_tracker-streamlit  latest    ...
```

---

## Step 4: Start Services

### 4.1 First Startup (Foreground)

Start in foreground to watch for errors:

```bash
docker-compose up
```

You'll see logs from both services:

```
fitness-tracker-api  | 🚀 Starting Fitness Tracker...
fitness-tracker-api  | ✅ Database found: data/fitness_data.db
fitness-tracker-ui   | 🚀 Starting Fitness Tracker...
...
```

**Keep this terminal open** and proceed to testing in a new terminal window.

### 4.2 Test the Services

In a **new terminal window**:

```bash
# Test FastAPI health endpoint
curl http://localhost:8000/health

# Should return: {"status":"healthy"}

# Test FastAPI docs
open http://localhost:8000/docs

# Test Streamlit UI
open http://localhost:8501
```

---

## Step 5: Verify Everything Works

### 5.1 Streamlit UI Tests

In your browser at http://localhost:8501:

- [ ] Homepage loads without errors
- [ ] Navigate to "Workout Schedule" page
- [ ] Can see your workouts for current week
- [ ] Navigate to "AI Weekly Coaching" page
- [ ] Text box and buttons are visible

### 5.2 FastAPI Tests

In your browser at http://localhost:8000/docs:

- [ ] Swagger UI loads
- [ ] Can expand endpoints
- [ ] Try the `/health` endpoint - click "Try it out" → "Execute"
- [ ] Should return `{"status": "healthy"}`

### 5.3 Database Persistence Test

```bash
# In the terminal where docker-compose is running, press Ctrl+C to stop

# Restart services
docker-compose up -d  # -d runs in background

# Check they're running
docker-compose ps

# Verify data persists
open http://localhost:8501  # Should still show your workouts
```

---

## Step 6: Learn Docker Commands

### Starting Services

```bash
# Foreground (see logs)
docker-compose up

# Background (detached)
docker-compose up -d
```

### Stopping Services

```bash
# If running in foreground: Ctrl+C, then:
docker-compose down

# If running in background:
docker-compose down
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Just FastAPI
docker-compose logs -f fastapi

# Just Streamlit
docker-compose logs -f streamlit

# Last 50 lines
docker-compose logs --tail=50
```

### Restarting After Code Changes

```bash
# Rebuild and restart
docker-compose build
docker-compose up -d

# Or in one command
docker-compose up -d --build
```

### Checking Status

```bash
# See running containers
docker-compose ps

# See all Docker containers
docker ps -a

# See Docker images
docker images
```

### Accessing Container Shell

```bash
# Access FastAPI container
docker exec -it fitness-tracker-api bash

# Inside container, you can:
python3 --version
ls -la /app
cat .env | head -5
exit
```

---

## Step 7: Common Issues & Solutions

### Issue: "Port already in use"

**Error**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution**:

```bash
# Find what's using the port
lsof -i :8000  # or :8501

# Kill the process
kill -9 <PID>

# Or stop your native app
./bin/stop_app.sh
```

### Issue: "Cannot connect to the Docker daemon"

**Error**: `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`

**Solution**:

- Open Docker Desktop application
- Wait for it to fully start (whale icon in menu bar)
- Try command again

### Issue: Build fails with "no space left"

**Error**: `no space left on device`

**Solution**:

```bash
# Clean up old Docker data
docker system prune -a

# Remove unused images
docker image prune -a
```

### Issue: Container exits immediately

**Error**: Container shows "Exited (1)" in `docker-compose ps`

**Solution**:

```bash
# Check logs for specific error
docker-compose logs fastapi
docker-compose logs streamlit

# Common causes:
# 1. Missing .env file
# 2. Database file not found
# 3. Syntax error in code
```

### Issue: Streamlit shows "Connection refused"

**Error**: "Oh no. Unable to connect to Streamlit"

**Solution**:

```bash
# Check if FastAPI is healthy
curl http://localhost:8000/health

# If FastAPI is down, check logs:
docker-compose logs fastapi

# Restart services:
docker-compose restart
```

---

## Step 8: Performance Tuning (Optional)

### Allocate More Resources to Docker

If things are slow:

1. Open Docker Desktop
2. Settings (⚙️) → Resources
3. Increase:
   - **CPUs**: 4-6 cores
   - **Memory**: 4-6 GB
   - **Swap**: 1-2 GB
4. Click "Apply & Restart"

### Speed Up Rebuilds

Docker caches layers. To maximize caching:

- Don't modify `requirements.txt` unless adding packages
- Code changes don't require full rebuild
- Use `docker-compose up -d --build` for quick rebuilds

---

## Step 9: Using Docker vs. Native Setup

### When to use Docker:

✅ Testing deployment configuration  
✅ Consistent environment  
✅ Before moving to Raspberry Pi  
✅ Sharing setup with others

### When to use native (venv):

✅ Active development (faster iteration)  
✅ Debugging with IDE  
✅ Running one-off scripts  
✅ Database management

### Switch Between Them:

```bash
# Stop Docker
docker-compose down

# Start native
./bin/start_app.sh

# Or vice versa:
./bin/stop_app.sh
docker-compose up -d
```

---

## Step 10: Final Checklist

Before moving to Phase 2 (Raspberry Pi), verify:

- [ ] Docker Desktop installed and running
- [ ] `docker-compose build` completes without errors
- [ ] `docker-compose up -d` starts services
- [ ] http://localhost:8501 shows Streamlit UI
- [ ] http://localhost:8000/health returns healthy status
- [ ] Can view workout schedule in Streamlit
- [ ] Can navigate between pages
- [ ] Database persists after `docker-compose down && up -d`
- [ ] Logs show no errors: `docker-compose logs`
- [ ] Can stop/start services reliably

---

## Next Steps

Once all checklist items pass:

✅ **Phase 1 COMPLETE** - Docker works locally!

➡️ **Ready for Phase 2**: Prepare Raspberry Pi

- SSH into Pi
- Install Docker on Pi
- Prepare project directory

See the main deployment plan for Phase 2 instructions.

---

## Quick Reference Card

**Start everything:**

```bash
docker-compose up -d
```

**Stop everything:**

```bash
docker-compose down
```

**View logs:**

```bash
docker-compose logs -f
```

**Rebuild after changes:**

```bash
docker-compose up -d --build
```

**Check status:**

```bash
docker-compose ps
```

**Access URLs:**

- Streamlit: http://localhost:8501
- FastAPI: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

**Questions or stuck?** Review the troubleshooting section or ask for help with specific error messages.

**Time to complete**: 2-3 hours (mostly waiting for builds)  
**Difficulty**: ⭐⭐☆☆☆ (Beginner-friendly)
