# 🚀 Beelink Deployment - Quick Commands

## Fix TrainingPeaks Sync (Playwright Issue)

### One-Command Fix

```bash
./deploy_playwright_fix.sh
```

### Manual Steps

```bash
# 1. Stop containers
docker-compose down

# 2. Rebuild (MUST use --no-cache)
docker-compose build --no-cache

# 3. Start containers
docker-compose up -d

# 4. Verify Playwright
docker exec fitness-tracker-ui python -c "from playwright.sync_api import sync_playwright; print('✅ OK')"
```

---

## Regular Deployment (Code Updates)

### Quick Restart (no Dockerfile changes)

```bash
docker-compose restart
```

### Full Rebuild (Dockerfile/requirements changed)

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

---

## Monitoring

### Check Status

```bash
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f streamlit
docker-compose logs -f fastapi

# Last 50 lines
docker-compose logs --tail=50 streamlit
```

### Check Health

```bash
# API
curl http://localhost:8000/health

# Streamlit (returns HTML)
curl -I http://localhost:8501
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs streamlit | tail -50

# Get shell in container
docker exec -it fitness-tracker-ui bash
```

### Port already in use

```bash
# Find what's using port 8501
sudo lsof -i :8501

# Kill process
sudo kill <PID>

# Or use different port in docker-compose.yml
```

### Out of disk space

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a
docker volume prune
```

### Environment variables not working

```bash
# Check .env file exists
ls -la .env

# Check variables in container
docker exec fitness-tracker-ui env | grep TRAININGPEAKS

# Restart to reload .env
docker-compose restart
```

---

## Accessing Services

### From Beelink (localhost)

- API: http://localhost:8000
- Streamlit: http://localhost:8501

### From other devices (Tailscale)

- API: http://100.117.194.8:8000
- Streamlit: http://100.117.194.8:8501

### API Documentation

- Swagger UI: http://100.117.194.8:8000/docs
- ReDoc: http://100.117.194.8:8000/redoc

---

## Database

### Backup

```bash
# Stop containers first
docker-compose down

# Copy database
cp data/fitness_data.db data/fitness_data.db.backup_$(date +%Y%m%d_%H%M%S)

# Restart
docker-compose up -d
```

### Restore

```bash
docker-compose down
cp data/fitness_data.db.backup_YYYYMMDD_HHMMSS data/fitness_data.db
docker-compose up -d
```

### Direct Access

```bash
# SQLite CLI in container
docker exec -it fitness-tracker-api sqlite3 data/fitness_data.db

# From host
sqlite3 data/fitness_data.db
```

---

## Git Updates

### Pull Latest Changes

```bash
# Save local changes
git stash

# Pull updates
git pull origin main

# Reapply local changes
git stash pop

# Rebuild if needed
docker-compose build
docker-compose up -d
```

### Check What Changed

```bash
git status
git diff
git log --oneline -10
```

---

## Performance

### Check Resource Usage

```bash
# Docker stats
docker stats

# Disk space
docker system df

# Container size
docker-compose ps -a --format "table {{.Name}}\t{{.Size}}"
```

### Clean Up

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Nuclear option (removes everything)
docker system prune -a --volumes
```

---

## Emergency Procedures

### Complete Reset

```bash
# WARNING: This deletes everything except database
docker-compose down
docker system prune -a --volumes
docker-compose build --no-cache
docker-compose up -d
```

### Rollback to Previous Version

```bash
# Stop containers
docker-compose down

# Checkout previous commit
git log --oneline -10  # Find commit hash
git checkout <commit-hash>

# Rebuild
docker-compose build
docker-compose up -d
```

### Can't Access Beelink Remotely

```bash
# Check Tailscale is running
sudo systemctl status tailscaled

# Restart Tailscale
sudo systemctl restart tailscaled

# Check IP
ip addr show tailscale0
```

---

## Useful Aliases (Add to ~/.bashrc)

```bash
# Fitness tracker aliases
alias ft-logs='docker-compose logs -f'
alias ft-restart='docker-compose restart'
alias ft-rebuild='docker-compose down && docker-compose build && docker-compose up -d'
alias ft-status='docker-compose ps'
alias ft-shell='docker exec -it fitness-tracker-ui bash'
```

Then run: `source ~/.bashrc`

---

## Quick Health Check Script

Save as `health_check.sh`:

```bash
#!/bin/bash
echo "🔍 Fitness Tracker Health Check"
echo "================================"
echo ""
echo "1. Container Status:"
docker-compose ps
echo ""
echo "2. API Health:"
curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "❌ API not responding"
echo ""
echo "3. Disk Space:"
df -h | grep -E "(Filesystem|/dev/root)"
echo ""
echo "4. Memory Usage:"
free -h
echo ""
echo "5. Recent Errors (last 10):"
docker-compose logs --tail=10 2>&1 | grep -i error || echo "No errors found"
```

Make executable: `chmod +x health_check.sh`

Run: `./health_check.sh`
