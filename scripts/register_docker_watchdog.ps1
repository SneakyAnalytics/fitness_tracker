# One-time setup on the Beelink (run in the logged-in user's session or over SSH as <user>).
#
# 1. Docker start tasks: no execution time limit. Docker Desktop runs as the task's own
#    process, and the default 72-hour limit made Task Scheduler kill Docker three days
#    after it was started (2026-10-09).
# 2. FitnessTrackerDockerWatchdog: every 10 minutes, scripts\beelink_docker_watchdog.ps1.
#    Interactive logon type: it must run in the console session to start Docker Desktop.

foreach ($name in "Start Docker Desktop", "DockerDesktopAutoStart") {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) {
        $task.Settings.ExecutionTimeLimit = "PT0S"
        Set-ScheduledTask -InputObject $task | Out-Null
        "$name : no time limit"
    }
}

$script = "C:\Users\<user>\fitness_tracker\scripts\beelink_docker_watchdog.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 9) -MultipleInstances IgnoreNew `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "<user>" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "FitnessTrackerDockerWatchdog" -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null
"FitnessTrackerDockerWatchdog registered (every 10 minutes)"
