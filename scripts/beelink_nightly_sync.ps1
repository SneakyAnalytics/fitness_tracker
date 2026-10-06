# Nightly task on the Beelink (Task Scheduler: FitnessTrackerNightlySync, 22:30).
# Pulls the last 3 days from TrainingPeaks, links ride files and analyzes new
# workouts, all inside the API container. Log: logs\nightly_sync.log
$root = "C:\Users\rakej\fitness_tracker"
$log = Join-Path $root "logs\nightly_sync.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') nightly sync starting"
docker exec fitness-tracker-api python -m src.utils.nightly_sync --days 3 2>&1 |
    Where-Object { $_ -notmatch '^\s*DEBUG' } | ForEach-Object { Add-Content $log "  $_" }
$code = $LASTEXITCODE
Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') nightly sync finished (exit $code)"
exit $code
