# 🐳 Docker Setup for Fitness Tracker

Quick guide to run your fitness tracker in Docker containers.

## Prerequisites

- Docker Desktop installed on Mac
- Your `.env` file with API keys in the project root
- Database file at `data/fitness_data.db`

## Quick Start

### 1. Build the Docker Images

```bash
cd /Users/jacobrobinson/fitness_tracker
docker-compose build
```

This will take 3-5 minutes on first build. Subsequent builds are faster due to caching.

### 2. Start the Services

```bash
docker-compose up
```

Or run in background (detached mode):

```bash
docker-compose up -d
```

### 3. Access the Application

- **Streamlit UI**: http://localhost:8501
- **FastAPI Backend**: http://localhost:8000
- **API Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs

### 4. Stop the Services

If running in foreground, press `Ctrl+C`, then:

```bash
docker-compose down
```

If running in background:

```bash
docker-compose down
```

## Common Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f streamlit
docker-compose logs -f fastapi
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart streamlit
```

### Rebuild After Code Changes

```bash
docker-compose build
docker-compose up -d
```

### Check Service Status

```bash
docker-compose ps
```

### Access Container Shell

```bash
# FastAPI container
docker exec -it fitness-tracker-api bash

# Streamlit container
docker exec -it fitness-tracker-ui bash
```

### Clean Up Everything

```bash
# Stop and remove containers
docker-compose down

# Also remove images
docker-compose down --rmi all

# Remove all Docker data (use with caution!)
docker system prune -a
```

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

```bash
# Check what's using port 8000 or 8501
lsof -i :8000
lsof -i :8501

# Kill your existing app if running
./bin/stop_app.sh

# Or kill specific process
kill -9 <PID>
```

### Database Not Found

Make sure your database exists:

```bash
ls -lh data/fitness_data.db
```

If missing, you may need to restore from backup or recreate it.

### API Keys Not Working

Check your `.env` file is in the project root:

```bash
cat .env | head -5  # Should show your keys (don't share!)
```

### Container Keeps Restarting

Check the logs:

```bash
docker-compose logs -f
```

Common issues:

- Missing dependencies in `requirements.txt`
- Database file permissions
- Invalid `.env` format

### Slow Performance

Docker on Mac can be slower than native. To improve:

1. Open Docker Desktop
2. Settings → Resources
3. Increase CPU/Memory allocation
4. Apply & Restart

## Data Persistence

Your data is preserved in mounted volumes:

- `./data` → `/app/data` (database, analyses, etc.)
- `./logs` → `/app/logs` (log files)

These directories are **not** inside the container, so data persists even when containers are removed.

## Differences from Native Setup

### What's the Same:

- ✅ Same code, same features
- ✅ Same database location
- ✅ Same ports (8000, 8501)
- ✅ Same API keys from `.env`

### What's Different:

- 🐳 Runs in isolated containers
- 🐳 Consistent environment (no venv issues)
- 🐳 Easier deployment to Raspberry Pi
- 🐳 Slightly different startup commands

## Next Steps

Once this works on your Mac:

1. ✅ **Phase 1 Complete**: Docker running locally
2. ➡️ **Phase 2**: Prepare Raspberry Pi (install Docker)
3. ➡️ **Phase 3**: Deploy to Pi with rsync
4. ➡️ **Phase 4**: Set up Cloudflare Tunnel
5. ➡️ **Phase 5**: Mobile UI optimization

See `RASPBERRY_PI_DEPLOYMENT_PLAN.md` for full deployment guide.

## Quick Test Checklist

After starting with `docker-compose up -d`:

- [ ] Visit http://localhost:8501 - Streamlit loads
- [ ] Check http://localhost:8000/health - Returns `{"status": "healthy"}`
- [ ] View workout schedule in Streamlit
- [ ] Generate a test AI analysis
- [ ] Check database persists after `docker-compose down && docker-compose up -d`

If all checks pass, you're ready for Phase 2! 🎉
