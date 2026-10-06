# start_containers_after_docker.ps1
# Called 3 minutes after login (via scheduled task) to give Docker Desktop
# time to start before we run docker-compose.

$LogFile = "C:\scripts\startup.log"

function Write-Log {
    param([string]$msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "$ts  $msg"
}

Write-Log "Starting fitness-tracker containers..."

# Wait for Docker API. First-time WSL distro install can take 10-15 min.
$timeout = 900
$elapsed = 0
while ($elapsed -lt $timeout) {
    # Check named pipe exists before calling docker (docker info hangs if pipe is absent)
    $pipeReady = Test-Path "\\.\pipe\dockerDesktopLinuxEngine"
    if ($pipeReady) {
        $info = docker ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker API ready."
            break
        }
        Write-Log "Waiting for Docker... ($elapsed s, pipe=$pipeReady, err=$info)"
    } else {
        Write-Log "Waiting for Docker... ($elapsed s, pipe=$pipeReady)"
    }
    Start-Sleep 10
    $elapsed += 10
}

if ($elapsed -ge $timeout) {
    Write-Log "ERROR: Docker API not ready after $timeout seconds. Aborting."
    exit 1
}

Set-Location "C:\Users\rakej\fitness_tracker"
$result = docker-compose up -d 2>&1
Write-Log "docker-compose up -d: $result"

$ps = docker ps --format "{{.Names}}: {{.Status}}" 2>&1
Write-Log "Containers: $ps"
Write-Log "Done."
