# register_context_check_task.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\scripts\check_docker_context.ps1"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(10)
$principal = New-ScheduledTaskPrincipal -UserId "BEELINK\dockerauto" -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName "DockerContextCheck" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Registered - waiting 30s for output..."
Start-Sleep 30
if (Test-Path "C:\scripts\docker_context.log") {
    Get-Content "C:\scripts\docker_context.log"
} else {
    Write-Host "No output yet"
}
