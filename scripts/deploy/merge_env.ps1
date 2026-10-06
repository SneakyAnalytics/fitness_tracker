# Merge KEY=VALUE lines from $Updates into the Beelink's .env, replacing keys that
# already exist and keeping every other line as-is. Values come from a file so
# characters like $ & ! never pass through a command line.
param([Parameter(Mandatory)][string]$EnvFile, [Parameter(Mandatory)][string]$Updates)
$new = @(Get-Content $Updates | Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=' })
$keys = $new | ForEach-Object { ($_ -split '=', 2)[0] }
$kept = @()
if (Test-Path $EnvFile) {
  $kept = @(Get-Content $EnvFile | Where-Object { $k = ($_ -split '=', 2)[0]; $keys -notcontains $k })
}
@($kept) + @($new) | Set-Content -Encoding ascii $EnvFile
Remove-Item $Updates
Write-Output ("updated: " + ($keys -join ', '))
