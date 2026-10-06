# Windows Task Scheduler Script for Weekly WSL Reset
# This script should be used to create a scheduled task that runs every Sunday at 3:00 AM
#
# To setup the scheduled task, run this script as Administrator:
#   .\setup_weekly_wsl_reset_task.ps1
#
# This prevents WSL/Docker from accumulating memory and CPU over time

param(
    [string]$TaskName = "WeeklyWSLReset",
    [string]$TriggerTime = "03:00",
    [string]$LogFile = "C:\Users\rakej\fitness_tracker\logs\wsl_reset.log"
)

Write-Host "Setting up Weekly WSL Reset scheduled task..." -ForegroundColor Green
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Create logs directory if it doesn't exist
$LogDir = Split-Path -Parent $LogFile
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task: $TaskName" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create the WSL reset script
$wslResetScript = @"
`$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Host "[`$timestamp] Starting WSL reset..." -ForegroundColor Cyan

# Get current WSL status
Write-Host "Current WSL status:" -ForegroundColor Yellow
wsl -l -v

# Shutdown WSL gracefully
Write-Host "Shutting down WSL..." -ForegroundColor Yellow
wsl --shutdown

# Wait for shutdown to complete
Start-Sleep -Seconds 10

# Verify shutdown
Write-Host "WSL status after shutdown:" -ForegroundColor Yellow
wsl -l -v

`$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Host "[`$timestamp] WSL reset complete. Docker containers will auto-restart." -ForegroundColor Green
Write-Host "Note: Docker containers with 'restart: unless-stopped' will restart automatically." -ForegroundColor Cyan
"@

$wslResetScriptPath = "C:\Users\rakej\fitness_tracker\scripts\wsl_reset.ps1"
$wslResetScript | Out-File -FilePath $wslResetScriptPath -Encoding utf8 -Force

# Create scheduled task action
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wslResetScriptPath`" >> `"$LogFile`" 2>&1"

# Create trigger (weekly on Sunday at 3:00 AM)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $TriggerTime

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# Create principal (run as SYSTEM for WSL shutdown)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

# Register the task
try {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Weekly WSL shutdown to prevent memory/CPU accumulation in vmmemWSL process" | Out-Null
    
    Write-Host "✓ Task created successfully: $TaskName" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Configuration:" -ForegroundColor Cyan
    Write-Host "  Name:        $TaskName"
    Write-Host "  Script:      $wslResetScriptPath"
    Write-Host "  Schedule:    Weekly on Sunday at $TriggerTime (3:00 AM)"
    Write-Host "  Log File:    $LogFile"
    Write-Host "  Run As:      SYSTEM"
    Write-Host ""
    Write-Host "What This Does:" -ForegroundColor Yellow
    Write-Host "  - Gracefully shuts down WSL every Sunday at 3 AM"
    Write-Host "  - Resets vmmemWSL process memory/CPU accumulation"
    Write-Host "  - Docker containers auto-restart due to 'unless-stopped' policy"
    Write-Host "  - Prevents fan running constantly due to CPU creep"
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Test the task manually: Get-ScheduledTask -TaskName '$TaskName' | Start-ScheduledTask"
    Write-Host "  2. Check log file after test: Get-Content '$LogFile' -Tail 50"
    Write-Host "  3. Verify Docker containers restart: docker ps"
    Write-Host ""
    
    # Display task info
    $task = Get-ScheduledTask -TaskName $TaskName
    Write-Host "Task Status:" -ForegroundColor Cyan
    Write-Host "  State:       $($task.State)"
    Write-Host "  Last Run:    $($task.LastRunTime)"
    Write-Host "  Next Run:    $($task.NextRunTime)"
    Write-Host ""
    
} catch {
    Write-Host "ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host "Setup complete!" -ForegroundColor Green
