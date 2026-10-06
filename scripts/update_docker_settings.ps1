# update_docker_settings.ps1 - run on Beelink to fix dockerauto Docker Desktop settings
$settingsPath = "C:\Users\dockerauto\AppData\Roaming\Docker\settings-store.json"
$json = '{"AutoDownloadUpdates":true,"AutoStart":false,"DisplayedOnboarding":true,"EnableDockerAI":true,"LastContainerdSnapshotterEnable":1777849441,"LicenseTermsVersion":2,"SettingsVersion":43,"UseContainerdSnapshotter":true}'
[System.IO.File]::WriteAllText($settingsPath, $json, [System.Text.Encoding]::UTF8)
Write-Host "Updated settings:"
Get-Content $settingsPath

# Clean up the incorrectly nested Docker directory
Remove-Item -Path "C:\Users\dockerauto\AppData\Roaming\Docker\Docker" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Cleaned up nested Docker folder"
