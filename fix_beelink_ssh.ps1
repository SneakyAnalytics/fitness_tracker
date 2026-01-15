# Fix SSH Key Authentication on Beelink
# Run this as Administrator on the Beelink

Write-Host "Fixing SSH key authentication..." -ForegroundColor Cyan

# Mac's public key
$macPublicKey = "ssh-ed25519 <your-public-key>

# Check if current user is in Administrators group
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    Write-Host "User is Administrator - using administrators_authorized_keys" -ForegroundColor Yellow
    
    # For admin users, must use the special administrators_authorized_keys file
    $keyFile = "C:\ProgramData\ssh\administrators_authorized_keys"
    
    # Create directory
    New-Item -ItemType Directory -Path "C:\ProgramData\ssh" -Force | Out-Null
    
    # Write the key
    Set-Content -Path $keyFile -Value $macPublicKey
    
    # CRITICAL: Set proper permissions (only SYSTEM and Administrators)
    icacls $keyFile /inheritance:r
    icacls $keyFile /grant SYSTEM:F
    icacls $keyFile /grant Administrators:F
    
    Write-Host "✓ Configured: $keyFile" -ForegroundColor Green
    
} else {
    Write-Host "User is regular user - using ~/.ssh/authorized_keys" -ForegroundColor Yellow
    
    # For regular users, use the user's .ssh folder
    $keyFile = "$env:USERPROFILE\.ssh\authorized_keys"
    
    # Create directory
    New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force | Out-Null
    
    # Write the key
    Set-Content -Path $keyFile -Value $macPublicKey
    
    # Set permissions (only the user)
    icacls $keyFile /inheritance:r
    icacls $keyFile /grant:r "$env:USERNAME:(R)"
    
    Write-Host "✓ Configured: $keyFile" -ForegroundColor Green
}

# Restart SSH service
Write-Host "Restarting SSH service..." -ForegroundColor Yellow
Restart-Service sshd

Write-Host ""
Write-Host "SSH key authentication configured!" -ForegroundColor Green
Write-Host ""
Write-Host "Test from Mac with: ssh <user>@<lan-ip> hostname" -ForegroundColor Cyan
Write-Host "Should work without password" -ForegroundColor Cyan
