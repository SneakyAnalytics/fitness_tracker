# Beelink Access Guide - Tailscale Configuration

## Overview

The Beelink is a Windows mini-PC running development services accessible via Tailscale VPN mesh network. This provides secure, encrypted remote access without exposing services to the public internet.

## Network Configuration

**Tailscale Network:**

- **Beelink IP:** `<beelink-ip>`
- **Mac Development Machine:** `<beelink-ip>`
- **Network:** Private mesh VPN (no port forwarding required)

**Machine Details:**

- **OS:** Windows 11
- **User:** `<user>`
- **Docker:** Docker Desktop (WSL2 backend)
- **SSH:** OpenSSH server enabled

## Connecting to the Beelink

### SSH Access

```bash
# Basic connection
ssh <user>@<beelink-ip>

# Run a single command
ssh <user>@<beelink-ip> "command here"

# Copy files to Beelink
scp localfile.txt <user>@<beelink-ip>:C:/destination/path/

# Copy files from Beelink
scp <user>@<beelink-ip>:C:/source/file.txt ./local/path/
```

**Note:** Windows paths use `C:/` format in SSH commands (forward slashes work better than backslashes).

### Accessing Services

Services running on the Beelink are accessible via Tailscale IP:

```bash
# Web services
http://<beelink-ip>:8501  # Streamlit UI
http://<beelink-ip>:8000  # FastAPI backend

# Docker containers
ssh <user>@<beelink-ip> "docker ps"
ssh <user>@<beelink-ip> "docker exec container-name command"
```

## Docker Environment

The Beelink runs applications in Docker containers:

```bash
# List running containers
ssh <user>@<beelink-ip> "docker ps"

# View container logs
ssh <user>@<beelink-ip> "docker logs container-name"

# Execute commands in containers
ssh <user>@<beelink-ip> "docker exec container-name python script.py"

# Restart containers
ssh <user>@<beelink-ip> "docker restart container-name"
```

**Current Containers:**

- `fitness-tracker-api` - FastAPI backend (port 8000)
- `fitness-tracker-ui` - Streamlit UI (port 8501)

## File Transfer Methods

### Method 1: SCP (Simple files)

```bash
# Upload single file
scp myfile.py <user>@<beelink-ip>:C:/Users/<user>/project/

# Download single file
scp <user>@<beelink-ip>:C:/Users/<user>/project/file.py ./
```

### Method 2: Tar + SCP (Multiple files)

```bash
# Upload directory
tar -czf archive.tar.gz my_directory/
scp archive.tar.gz <user>@<beelink-ip>:C:/Users/<user>/
ssh <user>@<beelink-ip> "cd C:\\Users\\<user> && tar -xzf archive.tar.gz"

# Download directory
ssh <user>@<beelink-ip> "cd C:\\Users\\<user>\\project && tar -czf archive.tar.gz folder/"
scp <user>@<beelink-ip>:C:/Users/<user>/project/archive.tar.gz ./
tar -xzf archive.tar.gz
```

### Method 3: Docker Copy (For containers)

```bash
# Copy file into running container
scp myfile.py <user>@<beelink-ip>:myfile.py
ssh <user>@<beelink-ip> "docker cp myfile.py container-name:/app/path/"

# Copy from container to local
ssh <user>@<beelink-ip> "docker cp container-name:/app/path/file.txt ."
scp <user>@<beelink-ip>:file.txt ./
```

## Common Workflows

### Deploy Application Updates

```bash
# 1. Copy updated files
scp src/app.py <user>@<beelink-ip>:app.py

# 2. Update container
ssh <user>@<beelink-ip> "docker cp app.py container-name:/app/src/app.py"

# 3. Restart container
ssh <user>@<beelink-ip> "docker restart container-name"
```

### Check Application Status

```bash
# View running services
ssh <user>@<beelink-ip> "docker ps"

# Check container health
ssh <user>@<beelink-ip> "docker logs --tail 50 container-name"

# Test API endpoint
curl -s http://<beelink-ip>:8000/health
```

### Database Operations

```bash
# Access SQLite database in container
ssh <user>@<beelink-ip> "docker exec container-name python -c \"import sqlite3; conn = sqlite3.connect('/app/data/database.db'); print(conn.execute('SELECT * FROM table LIMIT 5').fetchall())\""

# Backup database
ssh <user>@<beelink-ip> "docker cp container-name:/app/data/database.db ."
scp <user>@<beelink-ip>:database.db ./backups/
```

## Important Notes

1. **No Password Authentication:** SSH uses key-based authentication (password prompt means keys not configured)

2. **Windows Path Format:** Use forward slashes in SSH commands: `C:/Users/<user>/` not `C:\Users\<user>\`

3. **WSL2 Integration:** Docker runs in WSL2, but containers are accessible from Windows host

4. **No Port Forwarding:** Tailscale handles all networking - services are only accessible within the VPN mesh

5. **Persistent Services:** Containers auto-restart via Docker Compose `restart: unless-stopped`

## Troubleshooting

### Can't connect via SSH

```bash
# Check Tailscale connection
tailscale status | grep <beelink-ip>

# Test basic connectivity
ping <beelink-ip>
```

### Docker not responding

```bash
# Check Docker status
ssh <user>@<beelink-ip> "docker info"

# Restart Docker Desktop (from Windows)
ssh <user>@<beelink-ip> "powershell -Command \"Restart-Service Docker\""
```

### Service not accessible

```bash
# Check if port is listening
ssh <user>@<beelink-ip> "netstat -an | findstr :8000"

# View container logs
ssh <user>@<beelink-ip> "docker logs container-name"
```

## Security Considerations

- **VPN Only:** All services are only accessible via Tailscale VPN (100.x.x.x addresses)
- **No Public Exposure:** No ports exposed to internet
- **Encrypted Traffic:** Tailscale uses WireGuard for encryption
- **Key-based SSH:** No password authentication allowed

## Project Locations

Current fitness tracker project:

- **Code:** `C:\Users\<user>\fitness_tracker`
- **Data:** Container volume `/app/data` (SQLite database, FIT files)
- **Shareable:** `C:\Users\<user>\fitness_tracker\shareable` (Zwift workouts)

## Additional Resources

- **Tailscale Status:** `tailscale status` (shows all devices on network)
- **Docker Compose:** `C:\Users\<user>\fitness_tracker\docker-compose.yml`
- **Container Logs:** `/var/log/` in containers or `docker logs`

---

**For Development:** Create your own directory under `C:\Users\<user>\` and use Docker containers for services. Follow the same patterns as the fitness tracker for deployment and access.
