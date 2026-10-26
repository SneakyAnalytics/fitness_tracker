# Every 10 minutes on the Beelink (Task Scheduler: FitnessTrackerDockerWatchdog).
#
# Keeps Docker Desktop and the app containers running:
#   - Docker not responding and Docker Desktop not running -> start it ("Start Docker Desktop" task).
#   - Docker Desktop running but the engine silent for 3 checks in a row -> restart Docker Desktop.
#   - Engine up but the API container not running -> docker compose up -d.
# Disable while working on Docker by hand: schtasks /change /tn FitnessTrackerDockerWatchdog /disable
# Log: %USERPROFILE%\fitness_tracker\logs\docker_watchdog.log (only actions are logged).

$root = "$env:USERPROFILE\fitness_tracker"
$log = Join-Path $root "logs\docker_watchdog.log"
$state = Join-Path $root "logs\docker_watchdog.failures"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
function Log($msg) { Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" }

function Engine-Up {
    # `docker info` can hang on a wedged engine; give it 30 s.
    $job = Start-Job { docker info --format '{{.ServerVersion}}' 2>$null; $LASTEXITCODE }
    if (-not (Wait-Job $job -Timeout 30)) { Remove-Job $job -Force; return $false }
    $out = Receive-Job $job; Remove-Job $job
    return ($out | Select-Object -Last 1) -eq 0
}

function Wait-Engine($seconds) {
    for ($t = 0; $t -lt $seconds; $t += 10) { if (Engine-Up) { return $true }; Start-Sleep 10 }
    return $false
}

if (Engine-Up) {
    Remove-Item $state -ErrorAction SilentlyContinue
    $running = docker ps --filter "name=^fitness-tracker-api$" --filter "status=running" -q 2>$null
    if (-not $running) {
        Log "Engine up but fitness-tracker-api not running; docker compose up -d"
        Set-Location $root
        docker compose up -d 2>&1 | ForEach-Object { Add-Content $log "  $_" }
    }
    exit 0
}

$desktop = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $desktop) {
    Log "Docker not responding and Docker Desktop not running; starting it"
    schtasks /run /tn "Start Docker Desktop" | Out-Null
} else {
    $fails = 1 + [int](Get-Content $state -ErrorAction SilentlyContinue)
    Set-Content $state $fails
    if ($fails -lt 3) { Log "Docker Desktop running but engine not responding (check $fails of 3)"; exit 0 }
    Log "Engine silent for 3 checks; restarting Docker Desktop"
    Get-Process "Docker Desktop", "com.docker.backend" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 15
    schtasks /run /tn "Start Docker Desktop" | Out-Null
}

if (Wait-Engine 300) {
    Remove-Item $state -ErrorAction SilentlyContinue
    Set-Location $root
    docker compose up -d 2>&1 | ForEach-Object { Add-Content $log "  $_" }
    Log "Docker back up"
} else {
    Log "ERROR: Docker still not responding after 5 minutes"
    exit 1
}
