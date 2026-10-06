# Daily 05:00 task on the Beelink (Task Scheduler: ZwiftSyncToMac).
#
# 1. Regenerate today's Zwift workout with fresh news text (inside the container).
# 2. Copy this plan week's Week_<n> folder out of the Docker volume and scp it to the Mac.
# 3. Optionally email the daily news (inside the container).
#
# Everything runs through the container: the Beelink has no host Python, and the
# Zwift files live in the fitness_tracker_shareable volume (not the host folder).
# Output goes to C:\Users\rakej\fitness_tracker\logs\zwift_sync.log.

$ErrorActionPreference = "Continue"
$root = "C:\Users\rakej\fitness_tracker"
$log = Join-Path $root "logs\zwift_sync.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
function Log($msg) { $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"; Write-Host $line; Add-Content $log $line }

# .env values (quotes stripped) for the Mac target
Get-Content (Join-Path $root ".env") | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        Set-Item -Path "Env:$($matches[1])" -Value ($matches[2].Trim().Trim('"').Trim("'"))
    }
}
$MacHost = $env:MAC_TAILSCALE_IP; $MacUser = $env:MAC_USER; $MacZwiftDir = $env:MAC_ZWIFT_DIR
if (-not ($MacHost -and $MacUser -and $MacZwiftDir)) { Log "ERROR: MAC_TAILSCALE_IP / MAC_USER / MAC_ZWIFT_DIR missing from .env"; exit 1 }

$container = "fitness-tracker-api"
$failed = $false

Log "Refreshing today's Zwift files with fresh news..."
docker exec $container python -m src.utils.refresh_daily_zwift_news 2>&1 | ForEach-Object { Add-Content $log "  $_" }
if ($LASTEXITCODE -ne 0) { Log "WARNING: news refresh failed (exit $LASTEXITCODE); syncing existing files"; $failed = $true }

$week = (docker exec $container python -m src.utils.refresh_daily_zwift_news --week-dir | Select-Object -Last 1).Trim()
if (-not $week) { Log "No saved plan covers today; nothing to sync."; exit 0 }

$staging = Join-Path $env:TEMP "zwift_sync"
Remove-Item -Recurse -Force $staging -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $staging | Out-Null
docker cp "${container}:/app/shareable/zwift_workouts/$week" "$staging\$week"
if ($LASTEXITCODE -ne 0) { Log "ERROR: could not copy $week out of the container"; exit 1 }

Log "Syncing $week to ${MacUser}@${MacHost}:$MacZwiftDir"
ssh -o BatchMode=yes -o ConnectTimeout=15 "${MacUser}@${MacHost}" "mkdir -p '$MacZwiftDir' && rm -rf '$MacZwiftDir/$week'"
# Windows scp is happiest with forward slashes; capture its output in the log.
$src = ("$staging\$week") -replace '\\', '/'
scp -r -o BatchMode=yes -o ConnectTimeout=15 "$src" "${MacUser}@${MacHost}:$MacZwiftDir/" 2>&1 | ForEach-Object { Add-Content $log "  scp: $_" }
if ($LASTEXITCODE -eq 0) { Log "Synced $week ($((Get-ChildItem "$staging\$week").Count) files)" }
else { Log "ERROR: scp failed (exit $LASTEXITCODE) - is the Mac awake and on Tailscale?"; $failed = $true }

# Daily news email only if SMTP is configured in .env (SMTP_HOST etc.).
if ($env:EMAIL_TO -and $env:SMTP_HOST) {
    docker exec $container python scripts/email_daily_news.py 2>&1 | ForEach-Object { Add-Content $log "  $_" }
}

if ($failed) { exit 1 }
