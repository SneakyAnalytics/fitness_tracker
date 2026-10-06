# check_docker_context.ps1 - Run as dockerauto to diagnose docker context issue
$LogFile = "C:\scripts\docker_context.log"
function Log { param($m); Add-Content $LogFile "$(Get-Date -Format 'HH:mm:ss') $m" }

Log "=== Docker Context Check ==="
$ctx = docker context ls 2>&1
Log "context ls: $ctx"

Log "Switching to desktop-linux context..."
$sw = docker context use desktop-linux 2>&1
Log "context use: $sw"

Log "Testing docker ps..."
$ps = docker ps 2>&1
Log "docker ps exit=$LASTEXITCODE output=$ps"
