param(
    [string]$MacHost = $env:MAC_TAILSCALE_IP,
    [string]$MacUser = $env:MAC_USER,
    [string]$MacZwiftDir = $env:MAC_ZWIFT_DIR,
    [string]$SourceDir = $env:ZWIFT_WORKOUTS_DIR
)

$envPath = "C:\\Users\\rakej\\fitness_tracker\\.env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        $parts = $_ -split '=', 2
        if ($parts.Length -eq 2) {
            $key = $parts[0].Trim()
            $value = $parts[1].Trim().Trim('"').Trim("'")
            if ($key -and $value) {
                $env:$key = $value
            }
        }
    }
}

if (-not $MacHost) { throw "MAC_TAILSCALE_IP is required" }
if (-not $MacUser) { throw "MAC_USER is required" }
if (-not $MacZwiftDir) { throw "MAC_ZWIFT_DIR is required" }
if (-not $SourceDir) { $SourceDir = "C:\\Users\\rakej\\fitness_tracker\\shareable\\zwift_workouts" }

Write-Host "Syncing Zwift workouts to macOS..." -ForegroundColor Cyan
Write-Host "Source: $SourceDir"
Write-Host "Target: $MacUser@$MacHost:$MacZwiftDir" -ForegroundColor Cyan

$scpSource = $SourceDir -replace '^C:\\', '/c/' -replace '\\', '/'

$success = $true
try {
    scp -r "$scpSource/*" "$MacUser@$MacHost:$MacZwiftDir/"
} catch {
    $success = $false
    Write-Host "SCP failed: $_" -ForegroundColor Red
}

if ($env:EMAIL_TO) {
    $status = if ($success) { "SUCCESS" } else { "FAILURE" }
    $env:EMAIL_SUBJECT = "Zwift Sync $status"
    $env:EMAIL_BODY = "Zwift sync to Mac completed with status: $status. Source: $SourceDir"
    python C:\Users\rakej\fitness_tracker\scripts\notify_email.py
}

if (-not $success) { exit 1 }
