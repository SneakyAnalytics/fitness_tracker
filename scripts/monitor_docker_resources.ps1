# Docker Resource Monitoring Script
# Run this on Beelink for 24-48 hours to establish performance baseline
# Usage: .\monitor_docker_resources.ps1 -DurationHours 48 -LogFile "logs\docker_baseline.log"

param(
    [int]$DurationHours = 48,
    [string]$LogFile = "logs\docker_baseline.log",
    [int]$IntervalSeconds = 60
)

Write-Host "Starting Docker resource monitoring for $DurationHours hours..." -ForegroundColor Green
Write-Host "Logging to: $LogFile" -ForegroundColor Cyan
Write-Host "Sampling every $IntervalSeconds seconds" -ForegroundColor Cyan
Write-Host ""

# Create logs directory if it doesn't exist
$LogDir = Split-Path -Parent $LogFile
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Initialize log file with header
$Header = "Timestamp,Container,CPU%,MemUsage,MemLimit,MemPercent,NetIn,NetOut,BlockIn,BlockOut,PIDs"
$Header | Out-File -FilePath $LogFile -Encoding utf8

$EndTime = (Get-Date).AddHours($DurationHours)
$IterationCount = 0

Write-Host "Monitoring will end at: $EndTime" -ForegroundColor Yellow
Write-Host ""

try {
    while ((Get-Date) -lt $EndTime) {
        $IterationCount++
        $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        
        # Get docker stats (one-time snapshot)
        $StatsOutput = docker stats --no-stream --format "{{.Container}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}"
        
        if ($LASTEXITCODE -eq 0) {
            foreach ($Line in $StatsOutput) {
                if ($Line) {
                    # Parse the stats output
                    $Parts = $Line -split ','
                    $Container = $Parts[0]
                    $CPU = $Parts[1] -replace '%', ''
                    $MemUsageFull = $Parts[2]  # e.g., "95.5MiB / 512MiB"
                    $MemPercent = $Parts[3] -replace '%', ''
                    $NetIO = $Parts[4]  # e.g., "1.2MB / 3.4MB"
                    $BlockIO = $Parts[5]  # e.g., "0B / 4.5MB"
                    $PIDs = $Parts[6]
                    
                    # Parse memory usage
                    if ($MemUsageFull -match '([\d\.]+\w+)\s*/\s*([\d\.]+\w+)') {
                        $MemUsage = $Matches[1]
                        $MemLimit = $Matches[2]
                    } else {
                        $MemUsage = $MemUsageFull
                        $MemLimit = "N/A"
                    }
                    
                    # Parse network I/O
                    if ($NetIO -match '([\d\.]+\w+)\s*/\s*([\d\.]+\w+)') {
                        $NetIn = $Matches[1]
                        $NetOut = $Matches[2]
                    } else {
                        $NetIn = "N/A"
                        $NetOut = "N/A"
                    }
                    
                    # Parse block I/O
                    if ($BlockIO -match '([\d\.]+\w+)\s*/\s*([\d\.]+\w+)') {
                        $BlockIn = $Matches[1]
                        $BlockOut = $Matches[2]
                    } else {
                        $BlockIn = "N/A"
                        $BlockOut = "N/A"
                    }
                    
                    # Log to file
                    $LogEntry = "$Timestamp,$Container,$CPU,$MemUsage,$MemLimit,$MemPercent,$NetIn,$NetOut,$BlockIn,$BlockOut,$PIDs"
                    $LogEntry | Out-File -FilePath $LogFile -Append -Encoding utf8
                }
            }
            
            # Display progress
            $HoursRemaining = [math]::Round(($EndTime - (Get-Date)).TotalHours, 2)
            Write-Host "[$Timestamp] Iteration $IterationCount - $HoursRemaining hours remaining" -ForegroundColor Gray
            
        } else {
            Write-Host "[$Timestamp] ERROR: Docker stats command failed" -ForegroundColor Red
        }
        
        # Wait for next interval
        Start-Sleep -Seconds $IntervalSeconds
    }
    
    Write-Host ""
    Write-Host "Monitoring complete!" -ForegroundColor Green
    Write-Host "Log file: $LogFile" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To analyze the results, run:" -ForegroundColor Yellow
    Write-Host "  python scripts/analyze_docker_baseline.py $LogFile" -ForegroundColor White
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Monitoring interrupted" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
