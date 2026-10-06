# register_docker_startup.ps1
# Creates a scheduled task that starts Docker Desktop at user logon.
# More reliable than the HKCU\Run registry entry for headless reboots.

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

$action = New-ScheduledTaskAction `
    -Execute "C:\Program Files\Docker\Docker\Docker Desktop.exe" `
    -Argument "--background"

$trigger = New-ScheduledTaskTrigger -AtLogOn -User "rakej"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId "rakej" `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName "DockerDesktopAutoStart" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "DockerDesktopAutoStart task registered OK"
schtasks /query /tn DockerDesktopAutoStart /fo LIST
