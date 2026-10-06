# Windows Task Scheduler Script for Daily Zwift Sync
# This script should be used to create a scheduled task that runs at 5:00 AM PST daily
#
# To setup the scheduled task, run this script as Administrator:
#   .\setup_daily_zwift_sync_task.ps1
#
# Or manually create task with these settings:
#   - Trigger: Daily at 5:00 AM PST
#   - Action: Run PowerShell script: C:\Users\rakej\fitness_tracker\scripts\beelink_sync_zwift_to_mac.ps1
#   - Settings: Run whether user is logged on or not, wake computer to run

param(
    [string]$TaskName = "DailyZwiftSync",
    [string]$ScriptPath = "C:\Users\rakej\fitness_tracker\scripts\beelink_sync_zwift_to_mac.ps1",
    [string]$TriggerTime = "05:00",
    [string]$LogFile = "C:\Users\rakej\fitness_tracker\logs\zwift_sync.log"
)

Write-Host "Setting up Daily Zwift Sync scheduled task..." -ForegroundColor Green
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Verify script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: Script not found: $ScriptPath" -ForegroundColor Red
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

# Create scheduled task action
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" >> `"$LogFile`" 2>&1"

# Create trigger (daily at 5:00 AM PST)
$trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# Create principal (run as current user whether logged on or not)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Highest

# Register the task
try {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Daily sync of Zwift workout files with fresh news content to Mac via Tailscale" | Out-Null
    
    Write-Host "✓ Task created successfully: $TaskName" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Configuration:" -ForegroundColor Cyan
    Write-Host "  Name:        $TaskName"
    Write-Host "  Script:      $ScriptPath"
    Write-Host "  Schedule:    Daily at $TriggerTime (5:00 AM PST)"
    Write-Host "  Log File:    $LogFile"
    Write-Host "  Run As:      $env:USERDOMAIN\$env:USERNAME"
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Verify Tailscale is running on both Beelink and Mac"
    Write-Host "  2. Verify Docker containers are running: docker ps"
    Write-Host "  3. Test the task manually: Get-ScheduledTask -TaskName '$TaskName' | Start-ScheduledTask"
    Write-Host "  4. Check log file after test: Get-Content '$LogFile' -Tail 50"
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
