# check_docker_both_pipes.ps1 - test both Docker named pipes
$LogFile = "C:\scripts\docker_pipe_test.log"
function Log { param($m); Add-Content $LogFile "$(Get-Date -Format 'HH:mm:ss') $m" }

Log "=== Docker Pipe Test ==="

# Test docker_engine pipe first
$pipeEngine = Test-Path "\\.\pipe\docker_engine"
Log "docker_engine pipe exists: $pipeEngine"

if ($pipeEngine) {
    $env:DOCKER_HOST = "npipe:////./pipe/docker_engine"
    $r = docker ps 2>&1
    Log "docker ps via docker_engine: exit=$LASTEXITCODE output=$r"
    $env:DOCKER_HOST = ""
}

# Test dockerDesktopLinuxEngine  
$pipeDesktop = Test-Path "\\.\pipe\dockerDesktopLinuxEngine"
Log "dockerDesktopLinuxEngine pipe exists: $pipeDesktop"

if ($pipeDesktop) {
    $env:DOCKER_HOST = "npipe:////./pipe/dockerDesktopLinuxEngine"
    $r2 = docker ps 2>&1
    Log "docker ps via dockerDesktopLinuxEngine: exit=$LASTEXITCODE output=$r2"
    $env:DOCKER_HOST = ""
}
