$script = @'
Get-Process dllhost -ErrorAction SilentlyContinue |
    Where-Object { $_.CPU -gt 50000 } |
    ForEach-Object {
        $msg = "Killing runaway dllhost PID $($_.Id) CPU=$([int]$_.CPU)"
        Write-EventLog -LogName Application -Source "Application" -EventId 9999 -Message $msg -EntryType Warning -ErrorAction SilentlyContinue
        Stop-Process -Id $_.Id -Force
    }
'@

$scriptPath = "C:\Users\rakej\kill_dllhost.ps1"
$script | Out-File -FilePath $scriptPath -Encoding UTF8

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 30) -Once -At (Get-Date)

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

Register-ScheduledTask -TaskName 'KillRunawayDllhost' `
    -Action $action -Trigger $trigger -Settings $settings `
    -RunLevel Highest -Force

Write-Host "Task 'KillRunawayDllhost' registered - runs every 30 minutes"
