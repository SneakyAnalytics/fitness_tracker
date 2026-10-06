# 🔧 Fix TrainingPeaks Sync on Beelink

**Issue:** TrainingPeaks sync fails immediately because Playwright/Chromium is not installed in Docker containers.

## Quick Fix (Recommended)

### Option 1: Use Automated Script

```bash
# SSH into Beelink
ssh user@beelink

# Navigate to project
cd /path/to/fitness_tracker

# Run fix script
./deploy_playwright_fix.sh
```

This script will:

1. Stop containers
2. Rebuild with Playwright/Chromium
3. Start containers
4. Verify installation
5. Display status

**Time:** 5-10 minutes (downloading Chromium takes time)

---

## Option 2: Manual Fix

If the script doesn't work or you prefer manual steps:

### Step 1: Stop Containers

```bash
cd /path/to/fitness_tracker
docker-compose down
```

### Step 2: Verify Dockerfile Updates

The Dockerfile should now include:

```dockerfile
# Install Playwright browsers (after pip install)
RUN playwright install chromium
RUN playwright install-deps chromium
```

And system dependencies:

```dockerfile
RUN apt-get update && apt-get install -y \
    # ... existing packages ...
    # Playwright/Chromium dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    # ... more dependencies ...
```

### Step 3: Rebuild Containers (No Cache)

```bash
# This is CRITICAL - use --no-cache
docker-compose build --no-cache
```

**Why `--no-cache`?**

- Ensures fresh installation of Playwright
- Prevents using cached layers without Chromium

**Expected output:**

```
...
#12 [5/7] RUN playwright install chromium
#12 0.523 Downloading Chromium 123.0.6312.4 (playwright build v1140)
#12 12.34 Chromium 123.0.6312.4 downloaded successfully
#12 DONE 15.2s
...
```

### Step 4: Start Containers

```bash
docker-compose up -d
```

### Step 5: Verify Playwright Installation

```bash
# Should print "✅ Playwright installed"
docker exec fitness-tracker-ui python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright installed')"

# Check Chromium browser exists
docker exec fitness-tracker-ui sh -c "ls -la /root/.cache/ms-playwright/chromium-*/" | head -5
```

**Expected output:**

```
drwxr-xr-x 4 root root 4096 Jan 14 10:30 chromium-1140
```

### Step 6: Test in Streamlit

1. Open http://beelink-ip:8501
2. Go to TrainingPeaks sync page
3. Click sync button
4. Should now work without immediate error

---

## What Was Wrong?

**Before:**

```dockerfile
# Dockerfile only installed Python package
RUN pip install --no-cache-dir -r requirements.txt
# ❌ Missing: playwright install chromium
```

**After:**

```dockerfile
# Install Python package
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Install Chromium browser binaries
RUN playwright install chromium
RUN playwright install-deps chromium
```

**Key insight:** The `playwright` Python package is just a wrapper. The actual Chromium browser (200+ MB) must be downloaded separately via `playwright install`.

---

## Troubleshooting

### "Executable doesn't exist" still appears

**Solution 1: Check cache layers**

```bash
# Rebuild again with --no-cache
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Solution 2: Verify system dependencies**

```bash
# Check if libraries are installed
docker exec fitness-tracker-ui dpkg -l | grep libnss3
docker exec fitness-tracker-ui dpkg -l | grep libgbm1
```

If missing, the Dockerfile needs more system packages.

### "Permission denied" when running script

```bash
chmod +x deploy_playwright_fix.sh
```

### Docker build runs out of space

```bash
# Clean up old images/containers
docker system prune -a

# Then rebuild
docker-compose build --no-cache
```

### Build takes forever (> 15 minutes)

This is normal for first Playwright install:

- Chromium download: ~200 MB
- System dependencies: ~100 MB
- Total build time: 5-15 minutes depending on internet speed

---

## Verification Checklist

After fix, verify:

- [ ] Containers are running: `docker-compose ps`
- [ ] API is healthy: `curl http://localhost:8000/health`
- [ ] Streamlit loads: `curl http://localhost:8501`
- [ ] Playwright installed: `docker exec fitness-tracker-ui python -c "from playwright.sync_api import sync_playwright; print('OK')"`
- [ ] Chromium exists: `docker exec fitness-tracker-ui sh -c "ls /root/.cache/ms-playwright/chromium-*"`
- [ ] TrainingPeaks sync works in UI (no immediate error)

---

## Need Help?

If issues persist:

1. **Check container logs:**

   ```bash
   docker-compose logs -f streamlit
   ```

2. **Get shell in container:**

   ```bash
   docker exec -it fitness-tracker-ui bash
   # Then try: playwright --version
   ```

3. **Verify environment variables:**
   ```bash
   docker exec fitness-tracker-ui env | grep TRAININGPEAKS
   ```

---

## Summary

**Root cause:** Playwright Python package installed, but Chromium browser binaries were not.

**Fix:** Add `playwright install chromium` to Dockerfile and rebuild containers with `--no-cache`.

**Time to fix:** 5-10 minutes (mostly waiting for Chromium download).

**Files changed:**

- `Dockerfile` - Added Playwright browser installation
- `docs/architecture/automation-and-sync.md` - Added Docker/Playwright troubleshooting
- `deploy_playwright_fix.sh` - Automated deployment script (new)
