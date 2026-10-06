# Deployment Guide: Fix Zwift Automation & Docker CPU Issues

**Date:** January 23, 2026  
**Target:** Beelink SER5 Max (Windows 11)

## Overview

This guide implements fixes for:

1. **Non-functioning Zwift sync automation** - Daily news-embedded workout files not syncing to Mac
2. **High CPU usage** - Docker/WSL causing constant fan noise from vmmemWSL process
3. **Deprecated AI models** - Update to Google's new gemini-2.5 model names

## Prerequisites

✅ Ensure the following before starting:

- SSH access to Beelink via Tailscale (100.117.194.8)
- Administrator access on Beelink
- Docker containers running: `docker ps`
- Mac is accessible via Tailscale (100.111.4.32)
- `.env` file configured with EMAIL_TO for notifications

## Deployment Steps

### 1. Deploy Code Changes to Beelink

From your Mac, sync the updated code to Beelink:

```bash
# From fitness_tracker directory on Mac
./sync_to_beelink.sh
```

This syncs:

- Updated AI model names (gemini-2.5-flash, gemini-2.5-pro)
- New resource monitoring in daily_auto_sync_and_analyze.py
- Docker resource limits in docker-compose.yml
- New automation scripts

### 2. Setup WSL Memory Limits (ON BEELINK)

SSH into Beelink and create the WSL configuration:

```powershell
# SSH to Beelink
ssh rakej@100.117.194.8

# Navigate to fitness tracker
cd C:\Users\rakej\fitness_tracker

# Copy the WSL config template to user directory
Copy-Item .wslconfig.template C:\Users\rakej\.wslconfig

# Verify the file
Get-Content C:\Users\rakej\.wslconfig
```

Expected output:

```
[wsl2]
memory=2GB
processors=2
swap=1GB
pageReporting=false
vmIdleTimeout=60000
```

**Apply the changes:**

```powershell
# Shutdown WSL to apply new settings
wsl --shutdown

# Wait 10 seconds
Start-Sleep -Seconds 10

# Start Docker containers (they should auto-restart)
cd C:\Users\rakej\fitness_tracker
docker-compose up -d

# Verify containers are running
docker ps
```

### 3. Rebuild Docker Containers with Resource Limits

Apply the new resource limits from docker-compose.yml:

```powershell
# Still on Beelink
cd C:\Users\rakej\fitness_tracker

# Stop containers
docker-compose down

# Rebuild with new limits (no code changes, just config)
docker-compose up -d

# Verify resource limits are applied
docker inspect fitness-tracker-api | findstr /C:"Memory" /C:"NanoCpus"
docker inspect fitness-tracker-ui | findstr /C:"Memory" /C:"NanoCpus"
```

Expected output:

- API: Memory: 805306368 (768MB), NanoCpus: 1500000000 (1.5 CPUs)
- UI: Memory: 402653184 (384MB), NanoCpus: 500000000 (0.5 CPUs)

### 4. Setup Daily Zwift Sync Task

Create the scheduled task for 5am PST daily sync:

```powershell
# Run as Administrator (right-click PowerShell → Run as Administrator)
cd C:\Users\rakej\fitness_tracker\scripts

# Execute setup script
.\setup_daily_zwift_sync_task.ps1
```

Expected output:

```
✓ Task created successfully: DailyZwiftSync
Task Configuration:
  Name:        DailyZwiftSync
  Script:      C:\Users\rakej\fitness_tracker\scripts\beelink_sync_zwift_to_mac.ps1
  Schedule:    Daily at 05:00 (5:00 AM PST)
  ...
```

**Test the task manually:**

```powershell
# Trigger the task immediately
Get-ScheduledTask -TaskName 'DailyZwiftSync' | Start-ScheduledTask

# Wait 30 seconds, then check logs
Start-Sleep -Seconds 30
Get-Content C:\Users\rakej\fitness_tracker\logs\zwift_sync.log -Tail 30
```

### 5. Setup Weekly WSL Reset Task

Create the scheduled task for Sunday 3am WSL reset:

```powershell
# Still as Administrator
cd C:\Users\rakej\fitness_tracker\scripts

# Execute setup script
.\setup_weekly_wsl_reset_task.ps1
```

Expected output:

```
✓ Task created successfully: WeeklyWSLReset
Task Configuration:
  Name:        WeeklyWSLReset
  Schedule:    Weekly on Sunday at 03:00 (3:00 AM)
  ...
```

**Test the task manually (OPTIONAL - will restart containers):**

```powershell
# Trigger the task immediately
Get-ScheduledTask -TaskName 'WeeklyWSLReset' | Start-ScheduledTask

# Wait for completion, then verify containers restarted
Start-Sleep -Seconds 15
docker ps
```

### 6. Start Docker Baseline Monitoring (OPTIONAL)

To establish performance baselines, run the monitoring script for 24-48 hours:

```powershell
# Run in background
cd C:\Users\rakej\fitness_tracker\scripts

# Start monitoring (48 hours, sample every 60 seconds)
Start-Process PowerShell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File .\monitor_docker_resources.ps1 -DurationHours 48 -IntervalSeconds 60" -WindowStyle Hidden
```

After 48 hours, analyze the results:

```powershell
# Analyze baseline (back on Mac or via SSH)
python scripts/analyze_docker_baseline.py logs/docker_baseline.log
```

This will provide recommendations for adjusting resource limits if needed.

### 7. Update Google AI Models Cache

Refresh the Gemini models cache to use new model names:

```powershell
# On Beelink (via Docker)
docker exec fitness-tracker-api python scripts/utilities/refresh_gemini_models.py
```

Expected output:

```
🔄 Refreshing Gemini models cache...
✅ Found 35 available models
Top 10 Free Models:
  1. gemini-2.5-flash (score: 245)
  2. gemini-2.0-flash (score: 240)
  ...
Cache saved to: data/gemini_models_cache.json
```

## Verification

### Test Daily Sync Workflow

```powershell
# On Beelink - Manual test
cd C:\Users\rakej\fitness_tracker\scripts
.\beelink_sync_zwift_to_mac.ps1

# Check logs
Get-Content ..\logs\zwift_sync.log -Tail 30
```

Expected output:

```
Refreshing today's Zwift files with fresh news...
Syncing Zwift workouts to macOS...
Source: C:\Users\rakej\fitness_tracker\shareable\zwift_workouts
Target: jacobrobinson@100.111.4.32:~/Documents/Zwift/Workouts/6870291/
```

Check email for success notification (if EMAIL_TO is set).

### Verify Resource Limits

```powershell
# Check Docker stats in real-time
docker stats

# Should show:
# fitness-tracker-api: CPU <150%, MEM <768MB
# fitness-tracker-ui:  CPU <50%,  MEM <384MB
```

### Verify Scheduled Tasks

```powershell
# List all fitness tracker tasks
Get-ScheduledTask | Where-Object {$_.TaskName -match "Zwift|WSL"}

# Check next run times
Get-ScheduledTask -TaskName 'DailyZwiftSync' | Select-Object TaskName, State, @{Name='NextRun';Expression={$_.NextRunTime}}
Get-ScheduledTask -TaskName 'WeeklyWSLReset' | Select-Object TaskName, State, @{Name='NextRun';Expression={$_.NextRunTime}}
```

Expected output:

```
TaskName         State   NextRun
--------         -----   -------
DailyZwiftSync   Ready   1/24/2026 5:00:00 AM
WeeklyWSLReset   Ready   1/26/2026 3:00:00 AM (next Sunday)
```

## Monitoring & Maintenance

### Daily Monitoring

Check these logs regularly:

```powershell
# Zwift sync log (updated daily at 5am)
Get-Content C:\Users\rakej\fitness_tracker\logs\zwift_sync.log -Tail 50

# Resource usage log (updated during daily automation)
Get-Content C:\Users\rakej\fitness_tracker\logs\daily_resource_usage.log -Tail 50

# Daily automation log (TrainingPeaks sync)
Get-Content C:\Users\rakej\fitness_tracker\logs\daily_automation.err -Tail 50
```

### Weekly Monitoring

Check WSL reset log every Monday:

```powershell
# WSL reset log (updated Sunday 3am)
Get-Content C:\Users\rakej\fitness_tracker\logs\wsl_reset.log -Tail 20
```

### Container Health Check

```powershell
# Check container health status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}"

# Check container logs if issues
docker logs fitness-tracker-api --tail 50
docker logs fitness-tracker-ui --tail 50
```

## Troubleshooting

### Issue: Task Not Running

**Symptom:** Scheduled task doesn't execute at scheduled time

**Solution:**

```powershell
# Check task history
Get-ScheduledTask -TaskName 'DailyZwiftSync' | Get-ScheduledTaskInfo

# Check last result (0 = success, non-zero = error)
Get-ScheduledTask -TaskName 'DailyZwiftSync' | Select-Object -ExpandProperty LastTaskResult

# View task event logs
Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational -MaxEvents 10 | Where-Object {$_.Message -match 'DailyZwiftSync'}
```

### Issue: Docker Containers Not Restarting After WSL Shutdown

**Symptom:** Containers stopped after WSL reset

**Solution:**

```powershell
# Verify restart policy
docker inspect fitness-tracker-api | findstr /C:"RestartPolicy"

# Should show: "Name": "unless-stopped"

# Manually restart if needed
docker-compose up -d
```

### Issue: High CPU Usage Persists

**Symptom:** Fan still running constantly after changes

**Solution:**

```powershell
# Check vmmemWSL CPU usage
tasklist /FI "IMAGENAME eq vmmem.exe" /V

# If CPU seconds are accumulating rapidly (>500 in a day):
# 1. Check Docker stats for runaway process
docker stats

# 2. Force WSL shutdown
wsl --shutdown

# 3. Review baseline monitoring logs
python scripts/analyze_docker_baseline.py logs/docker_baseline.log

# 4. Consider tightening resource limits in docker-compose.yml
```

### Issue: Sync Fails with SCP Error

**Symptom:** `SCP failed: connection refused`

**Solution:**

```powershell
# Verify Tailscale is running on both devices
tailscale status

# Test SSH connection to Mac
ssh jacobrobinson@100.111.4.32 "echo 'Connection successful'"

# Verify SSH keys are configured
ssh-keygen -F 100.111.4.32

# If keys not configured, run:
ssh-copy-id jacobrobinson@100.111.4.32
```

### Issue: AI Model Errors

**Symptom:** `Model not found` errors in logs

**Solution:**

```powershell
# Refresh Gemini models cache
docker exec fitness-tracker-api python scripts/utilities/refresh_gemini_models.py

# Verify .env has correct API key
docker exec fitness-tracker-api printenv | findstr GEMINI_API_KEY

# Check API quota (visit console.cloud.google.com)
```

## Success Metrics

After deployment, you should observe:

✅ **Automation Working:**

- Daily email at 5am PST with sync status
- Fresh Zwift workouts with today's news in Mac Zwift folder
- No manual intervention required

✅ **CPU Usage Normal:**

- Beelink fan quiet during idle periods
- vmmemWSL process <100 CPU seconds per day
- Docker containers <25% CPU average

✅ **Resource Usage Stable:**

- Memory growth <10% over 24 hours
- No OOM (Out of Memory) errors
- Containers restart successfully after WSL reset

✅ **AI Models Updated:**

- No deprecation warnings in logs
- All AI features working (coach, content generation, analysis)
- Gemini models cache shows gemini-2.5-\* models

## Rollback Plan

If issues occur, rollback using:

```powershell
# On Beelink

# 1. Remove scheduled tasks
Unregister-ScheduledTask -TaskName 'DailyZwiftSync' -Confirm:$false
Unregister-ScheduledTask -TaskName 'WeeklyWSLReset' -Confirm:$false

# 2. Remove WSL config (restores defaults)
Remove-Item C:\Users\rakej\.wslconfig
wsl --shutdown

# 3. Restore old docker-compose.yml (remove resource limits)
# Edit docker-compose.yml and remove mem_limit and cpus lines

# 4. Restart containers
docker-compose down
docker-compose up -d

# 5. Revert code changes (from Mac)
git checkout HEAD~1  # or specific commit
./sync_to_beelink.sh
```

## Next Steps

After successful deployment:

1. **Monitor for 1 week** - Verify automation runs daily without issues
2. **Review baseline** - Analyze 48hr Docker monitoring data
3. **Fine-tune limits** - Adjust mem_limit/cpus based on actual usage
4. **Consider isolation** - Move Playwright/TrainingPeaks sync to separate container (future enhancement)

## Contact

For issues or questions:

- Check logs in `C:\Users\rakej\fitness_tracker\logs\`
- Email notifications will be sent to EMAIL_TO address
- Review this guide's Troubleshooting section

---

**Deployment Status:** Ready for execution  
**Estimated Time:** 30-45 minutes  
**Risk Level:** Low (rollback available)
