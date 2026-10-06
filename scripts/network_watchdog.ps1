# network_watchdog.ps1
# Monitors internet connectivity and auto-recovers when lost.
# Logs to C:\scripts\network_watchdog.log
# Recovery steps:
#   1. Flush DNS + renew DHCP (soft fix)
#   2. Restart WiFi adapter (medium fix)
#   3. OS reboot as last resort (run via Task Scheduler At Startup trigger)
#
# Scheduled to run every 5 minutes via Task Scheduler.

$LogFile = "C:\scripts\network_watchdog.log"
$MaxLogLines = 500

function Write-Log {
    param([string]$msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts  $msg"
    Add-Content -Path $LogFile -Value $line
    # Keep log trimmed
    $lines = Get-Content $LogFile -ErrorAction SilentlyContinue
    if ($lines.Count -gt $MaxLogLines) {
        $lines[-$MaxLogLines..-1] | Set-Content $LogFile
    }
}

function Test-Internet {
    # Ping two targets; if either responds, we're online
    $r1 = Test-Connection -ComputerName "8.8.8.8" -Count 2 -Quiet -ErrorAction SilentlyContinue
    if ($r1) { return $true }
    $r2 = Test-Connection -ComputerName "1.1.1.1" -Count 2 -Quiet -ErrorAction SilentlyContinue
    return $r2
}

# ── Main ──────────────────────────────────────────────────────────────────────

if (Test-Internet) {
    # All good - exit silently (this runs every 5 min, no need to spam the log)
    exit 0
}

Write-Log "WARN  Internet unreachable. Starting recovery..."

# Step 1: Soft fix — flush DNS and renew DHCP
Write-Log "INFO  Step 1: ipconfig /flushdns + /release + /renew"
ipconfig /flushdns | Out-Null
ipconfig /release "Wi-Fi" 2>$null | Out-Null
Start-Sleep 3
ipconfig /renew "Wi-Fi" 2>$null | Out-Null
Start-Sleep 5

if (Test-Internet) {
    Write-Log "OK    Recovered after DHCP renew."
    exit 0
}

# Step 2: Disable/re-enable the WiFi adapter
Write-Log "INFO  Step 2: Restarting WiFi adapter..."
try {
    Disable-NetAdapter -Name "Wi-Fi" -Confirm:$false -ErrorAction Stop
    Start-Sleep 5
    Enable-NetAdapter -Name "Wi-Fi" -Confirm:$false -ErrorAction Stop
    Start-Sleep 10
} catch {
    Write-Log "ERR   Adapter restart failed: $_"
}

if (Test-Internet) {
    Write-Log "OK    Recovered after WiFi adapter restart."
    exit 0
}

# Step 3: Last resort — reboot
Write-Log "CRIT  Still no internet after adapter restart. Scheduling OS reboot in 30s..."
shutdown /r /t 30 /c "network_watchdog: no internet after 2 recovery attempts"
