# register_pipe_test.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$a = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\scripts\check_docker_both_pipes.ps1"
$t = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(5)
$p = New-ScheduledTaskPrincipal -UserId "BEELINK\dockerauto" -LogonType Interactive -RunLevel Highest
$s = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName "DockerPipeTest" -Action $a -Trigger $t -Settings $s -Principal $p -Force | Out-Null
Write-Host "Registered - waiting..."
Start-Sleep 40
Get-Content C:\scripts\docker_pipe_test.log -ErrorAction SilentlyContinue
