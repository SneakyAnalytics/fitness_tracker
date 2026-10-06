# check_driver_updates.ps1
$Session = New-Object -ComObject Microsoft.Update.Session
$Searcher = $Session.CreateUpdateSearcher()
Write-Host "Searching for driver updates (this may take a minute)..."
try {
    $Results = $Searcher.Search("IsInstalled=0 AND Type=Driver")
    Write-Host "Driver updates available: $($Results.Updates.Count)"
    foreach ($u in $Results.Updates) {
        Write-Host "  - $($u.Title)"
    }
} catch {
    Write-Host "Error: $_"
}
