# Diagnostic Script for Beelink Unexpected Shutdown
# Run this on Beelink to investigate the cause of the shutdown
#
# Usage: .\scripts\diagnose_beelink_shutdown.ps1

Write-Host "🔍 Beelink Shutdown Diagnostic Report" -ForegroundColor Cyan
Write-Host "=" * 80
Write-Host ""

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "Report Time: $timestamp" -ForegroundColor Yellow
Write-Host ""

# 1. Check Windows Event Logs for unexpected shutdowns
Write-Host "📋 Checking Windows Event Logs for shutdown events..." -ForegroundColor Cyan
Write-Host "-" * 80

try {
    # System shutdown events (Event ID 1074, 6006, 6008)
    $shutdownEvents = Get-WinEvent -FilterHashtable @{
        LogName = 'System'
        ID = 1074, 6006, 6008
        StartTime = (Get-Date).AddDays(-1)
    } -MaxEvents 10 -ErrorAction SilentlyContinue

    if ($shutdownEvents) {
        foreach ($event in $shutdownEvents) {
            $eventType = switch ($event.Id) {
                1074 { "Clean Shutdown" }
                6006 { "Event Log Service Stopped" }
                6008 { "UNEXPECTED SHUTDOWN (System not properly shut down)" }
            }
            
            Write-Host "[$($event.TimeCreated)] $eventType" -ForegroundColor $(if ($event.Id -eq 6008) { "Red" } else { "Yellow" })
            Write-Host "  Message: $($event.Message.Split("`n")[0])" -ForegroundColor Gray
        }
    } else {
        Write-Host "No recent shutdown events found" -ForegroundColor Green
    }
} catch {
    Write-Host "Could not read event logs: $_" -ForegroundColor Red
}

Write-Host ""

# 2. Check for thermal/critical events
Write-Host "🌡️  Checking for Thermal/Critical Events..." -ForegroundColor Cyan
Write-Host "-" * 80

try {
    # Kernel-Power events (critical system events including thermal)
    $criticalEvents = Get-WinEvent -FilterHashtable @{
        LogName = 'System'
        ProviderName = 'Microsoft-Windows-Kernel-Power'
        StartTime = (Get-Date).AddDays(-1)
    } -MaxEvents 10 -ErrorAction SilentlyContinue

    if ($criticalEvents) {
        foreach ($event in $criticalEvents) {
            Write-Host "[$($event.TimeCreated)] Event ID $($event.Id): $($event.LevelDisplayName)" -ForegroundColor Yellow
            Write-Host "  $($event.Message.Split("`n")[0])" -ForegroundColor Gray
        }
    } else {
        Write-Host "No critical power events found" -ForegroundColor Green
    }
} catch {
    Write-Host "Could not read kernel-power events: $_" -ForegroundColor Red
}

Write-Host ""

# 3. Check current system temperature (if available)
Write-Host "🌡️  Current System Status..." -ForegroundColor Cyan
Write-Host "-" * 80

try {
    # CPU temperature (requires WMI thermal zone)
    $temps = Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace "root/wmi" -ErrorAction SilentlyContinue
    if ($temps) {
        foreach ($temp in $temps) {
            $celsius = ($temp.CurrentTemperature - 2732) / 10.0
            $fahrenheit = ($celsius * 9/5) + 32
            Write-Host "CPU Temp: $([math]::Round($celsius, 1))°C / $([math]::Round($fahrenheit, 1))°F" -ForegroundColor $(if ($celsius -gt 80) { "Red" } elseif ($celsius -gt 70) { "Yellow" } else { "Green" })
        }
    } else {
        Write-Host "Temperature sensors not accessible via WMI" -ForegroundColor Gray
    }
} catch {
    Write-Host "Could not read temperature: $_" -ForegroundColor Gray
}

Write-Host ""

# 4. Check Docker status
Write-Host "🐳 Docker Status..." -ForegroundColor Cyan
Write-Host "-" * 80

$dockerRunning = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerRunning) {
    Write-Host "Docker Desktop: Running (PID: $($dockerRunning.Id))" -ForegroundColor Green
    
    # Check containers
    try {
        $containers = docker ps -a --format "{{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
        Write-Host ""
        Write-Host "Containers:"
        foreach ($line in $containers) {
            $parts = $line -split '\t'
            $status = $parts[1]
            $color = if ($status -like "*Up*") { "Green" } else { "Red" }
            Write-Host "  $($parts[0]): $status" -ForegroundColor $color
        }
    } catch {
        Write-Host "Could not query Docker containers: $_" -ForegroundColor Red
    }
} else {
    Write-Host "Docker Desktop: NOT RUNNING" -ForegroundColor Red
}

Write-Host ""

# 5. Check WSL resource usage
Write-Host "🖥️  WSL Resource Usage..." -ForegroundColor Cyan
Write-Host "-" * 80

$vmmem = Get-Process "vmmem" -ErrorAction SilentlyContinue
if ($vmmem) {
    $cpuSeconds = $vmmem.CPU
    $memoryMB = [math]::Round($vmmem.WorkingSet64 / 1MB, 0)
    
    Write-Host "vmmemWSL Process:"
    Write-Host "  CPU Time: $([math]::Round($cpuSeconds, 2)) seconds" -ForegroundColor $(if ($cpuSeconds -gt 3600) { "Red" } elseif ($cpuSeconds -gt 1800) { "Yellow" } else { "Green" })
    Write-Host "  Memory: $memoryMB MB" -ForegroundColor $(if ($memoryMB -gt 2048) { "Red" } elseif ($memoryMB -gt 1024) { "Yellow" } else { "Green" })
    
    if ($cpuSeconds -gt 3600) {
        Write-Host "  ⚠️  HIGH CPU ACCUMULATION - Consider running 'wsl --shutdown'" -ForegroundColor Red
    }
} else {
    Write-Host "vmmem process not running (WSL not active)" -ForegroundColor Yellow
}

Write-Host ""

# 6. Check Docker resource limits
Write-Host "⚙️  Docker Resource Limits..." -ForegroundColor Cyan
Write-Host "-" * 80

$composeFile = "C:\Users\rakej\fitness_tracker\docker-compose.yml"
if (Test-Path $composeFile) {
    $hasLimits = Select-String -Path $composeFile -Pattern "mem_limit|cpus" -Quiet
    if ($hasLimits) {
        Write-Host "✅ Resource limits configured in docker-compose.yml" -ForegroundColor Green
        Select-String -Path $composeFile -Pattern "mem_limit|cpus" | ForEach-Object {
            Write-Host "  $($_.Line.Trim())" -ForegroundColor Gray
        }
    } else {
        Write-Host "❌ No resource limits found in docker-compose.yml" -ForegroundColor Red
        Write-Host "   Recommendation: Add mem_limit and cpus to prevent runaway resource usage" -ForegroundColor Yellow
    }
} else {
    Write-Host "docker-compose.yml not found at $composeFile" -ForegroundColor Red
}

Write-Host ""

# 7. Check WSL config
Write-Host "⚙️  WSL Configuration..." -ForegroundColor Cyan
Write-Host "-" * 80

$wslConfig = "$env:USERPROFILE\.wslconfig"
if (Test-Path $wslConfig) {
    Write-Host "✅ .wslconfig found:" -ForegroundColor Green
    Get-Content $wslConfig | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '\S' } | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Gray
    }
} else {
    Write-Host "❌ No .wslconfig found" -ForegroundColor Red
    Write-Host "   Recommendation: Create .wslconfig to limit WSL memory/CPU usage" -ForegroundColor Yellow
}

Write-Host ""

# 8. Summary and Recommendations
Write-Host "=" * 80
Write-Host "📊 SUMMARY & RECOMMENDATIONS" -ForegroundColor Cyan
Write-Host "=" * 80

Write-Host ""
Write-Host "Likely Cause Analysis:" -ForegroundColor Yellow

# Check for unexpected shutdown in events
$unexpectedShutdown = Get-WinEvent -FilterHashtable @{
    LogName = 'System'
    ID = 6008
    StartTime = (Get-Date).AddDays(-1)
} -MaxEvents 1 -ErrorAction SilentlyContinue

if ($unexpectedShutdown) {
    Write-Host "  🔴 UNEXPECTED SHUTDOWN DETECTED" -ForegroundColor Red
    Write-Host "     System was not properly shut down - likely thermal shutdown or power loss" -ForegroundColor Red
}

if ($vmmem -and $vmmem.CPU -gt 3600) {
    Write-Host "  🔴 HIGH WSL CPU ACCUMULATION" -ForegroundColor Red
    Write-Host "     vmmemWSL has accumulated significant CPU time" -ForegroundColor Red
}

Write-Host ""
Write-Host "Recommended Actions:" -ForegroundColor Yellow
Write-Host "  1. ✅ Apply WSL memory limits (.wslconfig with memory=2GB)" -ForegroundColor Green
Write-Host "  2. ✅ Apply Docker resource limits (mem_limit, cpus in docker-compose.yml)" -ForegroundColor Green
Write-Host "  3. ✅ Setup weekly WSL reset (wsl --shutdown every Sunday)" -ForegroundColor Green
Write-Host "  4. 🔄 Restart Docker containers: docker-compose up -d" -ForegroundColor Cyan
Write-Host "  5. 📊 Monitor: Run monitor_docker_resources.ps1 for 24-48 hours" -ForegroundColor Cyan
Write-Host ""

Write-Host "Diagnostic complete!" -ForegroundColor Green
Write-Host ""
