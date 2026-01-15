# Beelink Windows Setup Script
# Run this as Administrator in PowerShell on the Beelink

Write-Host "=== Beelink Permanent Access Setup ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Install Tailscale
Write-Host "[1/7] Installing Tailscale..." -ForegroundColor Yellow
$tailscaleInstaller = "$env:TEMP\tailscale-setup.exe"
Invoke-WebRequest -Uri "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe" -OutFile $tailscaleInstaller
Start-Process -FilePath $tailscaleInstaller -ArgumentList "/silent" -Wait
Write-Host "✓ Tailscale installed" -ForegroundColor Green

# Wait for installation to complete
Start-Sleep -Seconds 5

# Step 2: Start Tailscale and authenticate
Write-Host "[2/7] Starting Tailscale..." -ForegroundColor Yellow
Write-Host "Opening browser for authentication..." -ForegroundColor Cyan
& "C:\Program Files\Tailscale\tailscale.exe" up
Write-Host "✓ Tailscale configured" -ForegroundColor Green

# Step 3: Enable OpenSSH Server
Write-Host "[3/7] Installing OpenSSH Server..." -ForegroundColor Yellow
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Write-Host "✓ OpenSSH Server installed" -ForegroundColor Green

# Step 4: Start and configure SSH service
Write-Host "[4/7] Configuring SSH service..." -ForegroundColor Yellow
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
Write-Host "✓ SSH service configured" -ForegroundColor Green

# Step 5: Configure firewall
Write-Host "[5/7] Configuring firewall..." -ForegroundColor Yellow
if (!(Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
}
Write-Host "✓ Firewall configured" -ForegroundColor Green

# Step 6: Create .ssh directory and authorized_keys
Write-Host "[6/7] Setting up SSH keys..." -ForegroundColor Yellow
$sshDir = "$env:USERPROFILE\.ssh"
if (!(Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
}

# Create authorized_keys file with Mac's public key
$authorizedKeysFile = "$sshDir\authorized_keys"
$macPublicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEh61yhIbl2g4NJUTAT/Fx/4F9AaYL++1++9PWB0X9qq ljacobrobinsonl@gmail.com"
Set-Content -Path $authorizedKeysFile -Value $macPublicKey

# Set proper permissions (crucial for Windows SSH)
icacls $authorizedKeysFile /inheritance:r
icacls $authorizedKeysFile /grant:r "$($env:USERNAME):(R)"
Write-Host "✓ SSH keys configured" -ForegroundColor Green

# Step 7: Display connection info
Write-Host "[7/7] Getting connection information..." -ForegroundColor Yellow
$tailscaleIP = & "C:\Program Files\Tailscale\tailscale.exe" ip -4
Write-Host ""
Write-Host "=== SETUP COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Connection Information:" -ForegroundColor Cyan
Write-Host "  Tailscale IP: $tailscaleIP" -ForegroundColor White
Write-Host "  Username: $env:USERNAME" -ForegroundColor White
Write-Host ""
Write-Host "From your Mac, connect with:" -ForegroundColor Cyan
Write-Host "  ssh $env:USERNAME@$tailscaleIP" -ForegroundColor Yellow
Write-Host ""
Write-Host "No password needed - SSH key authentication is configured!" -ForegroundColor Green
Write-Host ""

# Optional: Configure Windows for 24/7 operation
Write-Host "Applying 24/7 server optimizations..." -ForegroundColor Yellow
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 15
Write-Host "✓ Power settings optimized" -ForegroundColor Green

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
