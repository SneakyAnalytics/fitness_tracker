# start_docker_and_containers.ps1 — run after reboot to start Docker Desktop + containers
# Called manually or via a scheduled task after login

Write-Host "Starting Docker services..."
Start-Service com.docker.service -ErrorAction SilentlyContinue
Start-Service vmcompute -ErrorAction SilentlyContinue

Write-Host "Starting Docker Desktop..."
$dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerDesktop) {
    Start-Process $dockerDesktop -WindowStyle Hidden
} else {
    Write-Host "Docker Desktop not found at $dockerDesktop"
    exit 1
}

# Wait for Docker API to become available (up to 3 minutes)
$timeout = 180
$elapsed = 0
Write-Host "Waiting for Docker API..."
while ($elapsed -lt $timeout) {
    $result = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker API ready."
        break
    }
    Start-Sleep 5
    $elapsed += 5
    Write-Host "  ...waiting ($elapsed s)"
}

if ($elapsed -ge $timeout) {
    Write-Host "ERROR: Docker API not ready after $timeout seconds"
    exit 1
}

# Start the fitness tracker containers
Write-Host "Starting fitness-tracker containers..."
Set-Location "C:\Users\rakej\fitness_tracker"
docker-compose up -d
Write-Host "Done. Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
