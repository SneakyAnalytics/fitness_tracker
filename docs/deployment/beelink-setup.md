# Beelink Permanent Access Setup Guide

## Current Status: Mac Ready ✅

Your Mac is configured with:

- ✅ Tailscale installed and running
- ✅ Tailscale IP: 100.111.4.32
- ✅ SSH keys generated
- ✅ Sync script ready

## When TV is Available - Run on Beelink (5 minutes)

### Method 1: Automated Setup (Recommended)

1. **Copy the setup script to Beelink**

   - Use USB drive: Copy `beelink_setup.ps1` to USB
   - Or download: Open PowerShell on Beelink and run:
     ```powershell
     Invoke-WebRequest -Uri "https://raw.githubusercontent.com/YOUR_REPO/beelink_setup.ps1" -OutFile "$env:TEMP\beelink_setup.ps1"
     ```

2. **Run the setup script as Administrator**

   ```powershell
   # Right-click PowerShell → Run as Administrator
   Set-ExecutionPolicy Bypass -Scope Process -Force
   & "$env:TEMP\beelink_setup.ps1"
   ```

3. **Follow the prompts**
   - Tailscale will open browser for authentication (use same account as Mac)
   - Script will automatically configure everything
   - Note the Tailscale IP shown at the end

### Method 2: Manual Setup

If you prefer to understand each step:

```powershell
# 1. Install Tailscale
Invoke-WebRequest -Uri "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe" -OutFile "$env:TEMP\tailscale-setup.exe"
Start-Process "$env:TEMP\tailscale-setup.exe" -ArgumentList "/silent" -Wait
& "C:\Program Files\Tailscale\tailscale.exe" up

# 2. Install OpenSSH Server
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# 3. Configure Firewall
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22

# 4. Set up SSH key authentication
New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force
Set-Content -Path "$env:USERPROFILE\.ssh\authorized_keys" -Value "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEh61yhIbl2g4NJUTAT/Fx/4F9AaYL++1++9PWB0X9qq ljacobrobinsonl@gmail.com"
icacls "$env:USERPROFILE\.ssh\authorized_keys" /inheritance:r
icacls "$env:USERPROFILE\.ssh\authorized_keys" /grant:r "$($env:USERNAME):(R)"

# 5. Get your Tailscale IP
& "C:\Program Files\Tailscale\tailscale.exe" ip -4

# 6. Optional: Optimize for 24/7 operation
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```

## After Beelink Setup - Using from Mac

### Connect via SSH (Password-less!)

```bash
# Replace with your Beelink's Tailscale IP from setup
ssh jrobinson@BEELINK_TAILSCALE_IP
```

### Sync Files to Beelink

```bash
cd /Users/jacobrobinson/fitness_tracker
./sync_to_beelink.sh BEELINK_TAILSCALE_IP
```

### Quick Commands from Mac

```bash
# Check if Beelink is online
ssh jrobinson@BEELINK_IP "echo 'Online'"

# Check Docker status
ssh jrobinson@BEELINK_IP "docker ps"

# Restart fitness tracker
ssh jrobinson@BEELINK_IP "cd C:\Users\jrobinson\fitness_tracker && docker compose restart"

# View logs
ssh jrobinson@BEELINK_IP "docker logs fitness-tracker-ui"

# Copy single file
scp local_file.py jrobinson@BEELINK_IP:/c/Users/jrobinson/fitness_tracker/
```

## Installing Docker on Beelink (After SSH is working)

### Via SSH from Mac:

```bash
ssh jrobinson@BEELINK_IP

# On Beelink, run:
# Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Docker Desktop
choco install -y docker-desktop

# Restart required after Docker installation
Restart-Computer
```

### After restart:

```bash
ssh jrobinson@BEELINK_IP
cd C:\Users\jrobinson\fitness_tracker
docker compose up -d
```

## Troubleshooting

### Can't connect via SSH?

1. Check Tailscale is running on both devices:

   - Mac: `tailscale status`
   - Beelink: `& "C:\Program Files\Tailscale\tailscale.exe" status`

2. Verify IP address:

   - Beelink: `& "C:\Program Files\Tailscale\tailscale.exe" ip -4`

3. Test SSH service on Beelink:
   - `Get-Service sshd`

### Permission denied?

- Re-run SSH key setup steps on Beelink (step 4 in manual setup)
- Verify file permissions on authorized_keys

### Tailscale authentication issues?

- Use same account on both devices
- Check: https://login.tailscale.com/admin/machines

## Benefits of This Setup

✅ **No repeated authentication** - SSH keys handle it
✅ **Works anywhere** - Tailscale works over internet, not just local network
✅ **Secure** - Encrypted VPN mesh network
✅ **Easy file transfers** - rsync, scp, or Tailscale's Taildrop
✅ **Access services** - Can access fitness tracker UI through Tailscale
✅ **Simple management** - One command to sync, restart, check logs

## Next Steps After Migration

1. Set up Docker auto-restart for fitness tracker
2. Configure Cloudflare tunnel (or use Tailscale URL)
3. Set up automated backups of database
4. Create Windows Task Scheduler job to start containers on boot

---

**Your Mac's SSH Public Key (for reference):**

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEh61yhIbl2g4NJUTAT/Fx/4F9AaYL++1++9PWB0X9qq ljacobrobinsonl@gmail.com
```
